"""Notification delivery state machine dispatcher (S5-04).

Orchestrates notification lifecycle: enqueue -> deliver -> retry/dead-letter.
All state transitions are guarded by NotificationStateMachine.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional, Protocol

logger = logging.getLogger(__name__)

from src.domain.enums import ActorType, AuditAction, NotificationStatus
from src.domain.models.notification_event import NotificationEvent


class DuplicateIdempotencyKeyError(Exception):
    """Raised when a notification with the same idempotency key already exists."""

    def __init__(self, key: str) -> None:
        self.key = key
        super().__init__(f"Duplicate idempotency key: {key}")


class NotificationEventsRepoProtocol(Protocol):
    """Repository interface for notification events."""

    async def create(self, event: NotificationEvent) -> NotificationEvent: ...
    async def get_by_id(self, event_id: uuid.UUID) -> Optional[NotificationEvent]: ...
    async def get_by_idempotency_key(self, key: str) -> Optional[NotificationEvent]: ...
    async def update(self, event: NotificationEvent) -> NotificationEvent: ...
    async def list_by_alert_id(self, alert_id: uuid.UUID) -> list[NotificationEvent]: ...


class NotificationDispatcher:
    """Drives the notification delivery lifecycle with state-guarded transitions."""

    def __init__(
        self,
        repo: NotificationEventsRepoProtocol,
        sender,
        max_retries: int = 3,
        audit=None,
    ) -> None:
        self._repo = repo
        self._sender = sender
        self._max_retries = max_retries
        self._audit = audit

    async def enqueue(
        self,
        alert_id: uuid.UUID,
        snapshot_id: uuid.UUID,
        channel: str,
        idempotency_key: str,
    ) -> NotificationEvent:
        """Create a new queued notification, or return existing if idempotency key matches."""
        existing = await self._repo.get_by_idempotency_key(idempotency_key)
        if existing is not None:
            return existing

        event = NotificationEvent(
            id=uuid.uuid4(),
            alert_id=alert_id,
            snapshot_id=snapshot_id,
            channel=channel,
            idempotency_key=idempotency_key,
            status=NotificationStatus.QUEUED,
            attempt_count=0,
            last_error=None,
            sent_at=None,
            created_at=datetime.now(timezone.utc),
        )
        return await self._repo.create(event)

    async def deliver(self, event_id: uuid.UUID) -> NotificationEvent:
        """Attempt to deliver a notification. Transitions queued->sent or queued->failed."""
        event = await self._repo.get_by_id(event_id)
        if event is None:
            raise ValueError(f"NotificationEvent {event_id} not found")

        try:
            await self._sender(event)
            now = datetime.now(timezone.utc)
            updated = event.record_attempt().mark_sent(sent_at=now)
        except Exception as exc:
            # Transition to failed (will raise InvalidTransitionError if not allowed)
            updated = event.record_attempt(error=str(exc)).transition_to(
                NotificationStatus.FAILED
            )

        result = await self._repo.update(updated)
        if self._audit:
            action = (
                AuditAction.NOTIFICATION_SENT
                if result.status == NotificationStatus.SENT
                else AuditAction.NOTIFICATION_FAILED
            )
            try:
                await self._audit.emit(
                    actor_id="system",
                    actor_type=ActorType.SYSTEM,
                    action=action,
                    entity_type="NotificationEvent",
                    entity_id=str(result.id),
                    prior_state={"status": event.status.value},
                    new_state={
                        "status": result.status.value,
                        "attempt_count": result.attempt_count,
                        "last_error": result.last_error,
                    },
                )
            except Exception as e:
                logger.warning("Audit emission failed for %s %s: %s", action, result.id, e)
        return result

    async def retry(self, event_id: uuid.UUID) -> NotificationEvent:
        """Retry a failed notification or move to dead letter if max retries exceeded."""
        event = await self._repo.get_by_id(event_id)
        if event is None:
            raise ValueError(f"NotificationEvent {event_id} not found")

        if event.attempt_count >= self._max_retries:
            # Exhausted retries -> dead letter
            updated = event.transition_to(NotificationStatus.DEAD)
        else:
            # Re-queue for retry
            updated = event.transition_to(NotificationStatus.QUEUED)

        return await self._repo.update(updated)

    async def get_timeline(self, alert_id: uuid.UUID) -> list[NotificationEvent]:
        """Retrieve notification event timeline for an alert."""
        return await self._repo.list_by_alert_id(alert_id)
