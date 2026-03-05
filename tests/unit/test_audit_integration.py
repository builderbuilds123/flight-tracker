"""Integration tests for audit emission within the notification dispatcher (S6-05)."""
import uuid
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import AsyncMock

import pytest

from src.domain.enums import AuditAction, NotificationStatus
from src.domain.models.audit_event import AuditEvent
from src.domain.models.notification_event import NotificationEvent
from src.services.audit_emitter import AuditEmitter
from src.services.notification_dispatcher import (
    DuplicateIdempotencyKeyError,
    NotificationDispatcher,
)


class FakeNotificationEventsRepo:
    """In-memory notification events repo for testing."""

    def __init__(self):
        self._events: dict[uuid.UUID, NotificationEvent] = {}
        self._by_key: dict[str, uuid.UUID] = {}

    async def create(self, event: NotificationEvent) -> NotificationEvent:
        if event.idempotency_key in self._by_key:
            raise DuplicateIdempotencyKeyError(event.idempotency_key)
        self._events[event.id] = event
        self._by_key[event.idempotency_key] = event.id
        return event

    async def get_by_id(self, event_id: uuid.UUID) -> Optional[NotificationEvent]:
        return self._events.get(event_id)

    async def get_by_idempotency_key(self, key: str) -> Optional[NotificationEvent]:
        eid = self._by_key.get(key)
        return self._events.get(eid) if eid else None

    async def update(self, event: NotificationEvent) -> NotificationEvent:
        self._events[event.id] = event
        return event

    async def list_by_alert_id(self, alert_id: uuid.UUID) -> list[NotificationEvent]:
        return [e for e in self._events.values() if e.alert_id == alert_id]


class FakeAuditRepo:
    def __init__(self):
        self.events: list[AuditEvent] = []

    async def create(self, event: AuditEvent) -> AuditEvent:
        self.events.append(event)
        return event


def _make_notification_event(**overrides) -> NotificationEvent:
    defaults = dict(
        id=uuid.uuid4(),
        alert_id=uuid.uuid4(),
        snapshot_id=uuid.uuid4(),
        channel="telegram",
        idempotency_key=f"idem-{uuid.uuid4().hex[:8]}",
        status=NotificationStatus.QUEUED,
        attempt_count=0,
        last_error=None,
        sent_at=None,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return NotificationEvent(**defaults)


class TestDispatcherAuditIntegration:
    @pytest.fixture
    def notification_repo(self):
        return FakeNotificationEventsRepo()

    @pytest.fixture
    def audit_repo(self):
        return FakeAuditRepo()

    @pytest.fixture
    def audit_emitter(self, audit_repo):
        return AuditEmitter(repo=audit_repo)

    @pytest.fixture
    def sender(self):
        return AsyncMock(return_value=None)

    @pytest.fixture
    def dispatcher(self, notification_repo, sender, audit_emitter):
        return NotificationDispatcher(
            repo=notification_repo,
            sender=sender,
            max_retries=3,
            audit=audit_emitter,
        )

    @pytest.mark.asyncio
    async def test_deliver_success_emits_sent_audit(self, dispatcher, notification_repo, audit_repo):
        event = _make_notification_event()
        await notification_repo.create(event)

        result = await dispatcher.deliver(event.id)

        assert result.status == NotificationStatus.SENT
        assert len(audit_repo.events) == 1
        audit = audit_repo.events[0]
        assert audit.action == AuditAction.NOTIFICATION_SENT
        assert audit.entity_type == "NotificationEvent"
        assert audit.new_state["status"] == "sent"

    @pytest.mark.asyncio
    async def test_deliver_failure_emits_failed_audit(self, notification_repo, audit_repo, audit_emitter):
        sender = AsyncMock(side_effect=RuntimeError("connection timeout"))
        dispatcher = NotificationDispatcher(
            repo=notification_repo,
            sender=sender,
            max_retries=3,
            audit=audit_emitter,
        )
        event = _make_notification_event()
        await notification_repo.create(event)

        result = await dispatcher.deliver(event.id)

        assert result.status == NotificationStatus.FAILED
        assert len(audit_repo.events) == 1
        audit = audit_repo.events[0]
        assert audit.action == AuditAction.NOTIFICATION_FAILED
        assert audit.new_state["status"] == "failed"
        assert audit.new_state["last_error"] == "connection timeout"

    @pytest.mark.asyncio
    async def test_dispatcher_without_audit_still_works(self, notification_repo, sender):
        dispatcher = NotificationDispatcher(
            repo=notification_repo,
            sender=sender,
            max_retries=3,
            audit=None,
        )
        event = _make_notification_event()
        await notification_repo.create(event)

        result = await dispatcher.deliver(event.id)
        assert result.status == NotificationStatus.SENT
