"""Notification mutation service with explicit audit emission."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Protocol

from src.domain.enums import AuditAction, NotificationStatus
from src.domain.models.audit_event import ActorContext, AuditEvent
from src.domain.models.notification_event import NotificationEvent
from src.observability.redaction import redact_payload


class NotificationRepoProtocol(Protocol):
    async def get_by_id(self, event_id: uuid.UUID) -> NotificationEvent | None: ...
    async def update(self, event: NotificationEvent) -> NotificationEvent: ...


class AuditRepoProtocol(Protocol):
    async def create(self, event: AuditEvent) -> AuditEvent: ...


class NotificationService:
    def __init__(self, notifications_repo: NotificationRepoProtocol, audit_repo: AuditRepoProtocol) -> None:
        self._notifications_repo = notifications_repo
        self._audit_repo = audit_repo

    async def mark_sent(self, *, event_id: uuid.UUID, actor: ActorContext) -> NotificationEvent:
        event = await self._notifications_repo.get_by_id(event_id)
        if event is None:
            raise ValueError(f"NotificationEvent {event_id} not found")

        now = datetime.now(timezone.utc)
        updated = await self._notifications_repo.update(event.record_attempt().mark_sent(sent_at=now))
        await self._emit_audit(
            actor=actor,
            action=AuditAction.NOTIFICATION_SENT,
            old_state={"status": event.status.value},
            new_state={"status": updated.status.value, "attempt_count": updated.attempt_count},
            entity_id=updated.id,
        )
        return updated

    async def mark_failed(
        self,
        *,
        event_id: uuid.UUID,
        error: str,
        actor: ActorContext,
    ) -> NotificationEvent:
        event = await self._notifications_repo.get_by_id(event_id)
        if event is None:
            raise ValueError(f"NotificationEvent {event_id} not found")

        updated = await self._notifications_repo.update(
            event.record_attempt(error=error).transition_to(NotificationStatus.FAILED)
        )
        await self._emit_audit(
            actor=actor,
            action=AuditAction.NOTIFICATION_FAILED,
            old_state={"status": event.status.value},
            new_state={
                "status": updated.status.value,
                "attempt_count": updated.attempt_count,
                "last_error": updated.last_error,
            },
            entity_id=updated.id,
        )
        return updated

    async def _emit_audit(
        self,
        *,
        actor: ActorContext,
        action: AuditAction,
        old_state: dict,
        new_state: dict,
        entity_id: uuid.UUID,
    ) -> None:
        event = AuditEvent(
            id=uuid.uuid4(),
            actor_id=actor.actor_id,
            actor_type=actor.actor_type,
            action=action,
            entity_type="NotificationEvent",
            entity_id=entity_id,
            old_state=redact_payload(old_state),
            new_state=redact_payload(new_state),
            metadata={},
            created_at=datetime.now(timezone.utc),
        )
        await self._audit_repo.create(event)
