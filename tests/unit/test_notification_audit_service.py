"""Unit tests for notification service audit emission with explicit ActorContext."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from src.domain.enums import ActorType, AuditAction, NotificationStatus
from src.domain.models.audit_event import ActorContext, AuditEvent
from src.domain.models.notification_event import NotificationEvent
from src.services.notification_service import NotificationService


def _make_event(**overrides) -> NotificationEvent:
    now = datetime.now(timezone.utc)
    defaults = dict(
        id=uuid.uuid4(),
        alert_id=uuid.uuid4(),
        snapshot_id=uuid.uuid4(),
        channel="telegram",
        idempotency_key=f"key-{uuid.uuid4().hex[:8]}",
        status=NotificationStatus.QUEUED,
        attempt_count=0,
        last_error=None,
        sent_at=None,
        created_at=now,
    )
    defaults.update(overrides)
    return NotificationEvent(**defaults)


class _NotificationsRepo:
    def __init__(self) -> None:
        self.data: dict[uuid.UUID, NotificationEvent] = {}

    async def get_by_id(self, event_id: uuid.UUID) -> NotificationEvent | None:
        return self.data.get(event_id)

    async def update(self, event: NotificationEvent) -> NotificationEvent:
        self.data[event.id] = event
        return event


class _AuditRepo:
    def __init__(self) -> None:
        self.events: list[AuditEvent] = []

    async def create(self, event: AuditEvent) -> AuditEvent:
        self.events.append(event)
        return event


@pytest.mark.asyncio
async def test_mark_sent_emits_notification_sent_audit():
    notifications_repo = _NotificationsRepo()
    audit_repo = _AuditRepo()
    service = NotificationService(
        notifications_repo=notifications_repo,
        audit_repo=audit_repo,
    )
    event = _make_event(status=NotificationStatus.QUEUED)
    notifications_repo.data[event.id] = event
    actor = ActorContext(actor_type=ActorType.SYSTEM, actor_id=None)

    updated = await service.mark_sent(event_id=event.id, actor=actor)

    assert updated.status == NotificationStatus.SENT
    assert len(audit_repo.events) == 1
    audit = audit_repo.events[0]
    assert audit.action == AuditAction.NOTIFICATION_SENT
    assert audit.old_state == {"status": "queued"}
    assert audit.new_state["status"] == "sent"


@pytest.mark.asyncio
async def test_mark_failed_emits_notification_failed_audit():
    notifications_repo = _NotificationsRepo()
    audit_repo = _AuditRepo()
    service = NotificationService(
        notifications_repo=notifications_repo,
        audit_repo=audit_repo,
    )
    event = _make_event(status=NotificationStatus.QUEUED)
    notifications_repo.data[event.id] = event
    actor = ActorContext(actor_type=ActorType.SYSTEM, actor_id=None)

    updated = await service.mark_failed(
        event_id=event.id,
        error="telegram timeout",
        actor=actor,
    )

    assert updated.status == NotificationStatus.FAILED
    audit = audit_repo.events[0]
    assert audit.action == AuditAction.NOTIFICATION_FAILED
    assert audit.new_state["last_error"] == "telegram timeout"
