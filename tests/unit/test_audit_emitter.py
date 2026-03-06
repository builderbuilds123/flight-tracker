"""Unit tests for AuditEmitter service (S6-05)."""
import uuid
from datetime import datetime, timezone

import pytest

from src.domain.enums import ActorType, AuditAction
from src.domain.models.audit_event import ActorContext, AuditEvent
from src.services.audit_emitter import AuditEmitter


class FakeAuditRepo:
    """In-memory audit repository for unit tests."""

    def __init__(self):
        self.events: list[AuditEvent] = []

    async def create(self, event: AuditEvent) -> AuditEvent:
        self.events.append(event)
        return event


class TestAuditEmitter:
    @pytest.fixture
    def repo(self):
        return FakeAuditRepo()

    @pytest.fixture
    def emitter(self, repo):
        return AuditEmitter(repo=repo)

    @pytest.mark.asyncio
    async def test_emit_persists_event(self, emitter, repo):
        event = await emitter.emit(
            actor=ActorContext(actor_type=ActorType.USER, actor_id=uuid.uuid4()),
            action=AuditAction.ALERT_CREATED,
            entity_type="Alert",
            entity_id=uuid.uuid4(),
            new_state={"status": "active"},
        )
        assert len(repo.events) == 1
        assert repo.events[0].id == event.id
        assert event.action == AuditAction.ALERT_CREATED
        assert event.entity_type == "Alert"

    @pytest.mark.asyncio
    async def test_emit_redacts_sensitive_fields(self, emitter, repo):
        event = await emitter.emit(
            actor=ActorContext(actor_type=ActorType.SYSTEM, actor_id=None),
            action=AuditAction.NOTIFICATION_SENT,
            entity_type="Notification",
            entity_id=uuid.uuid4(),
            new_state={
                "channel": "telegram",
                "telegram_chat_id": "12345",
                "user_id": "some-user-id",
            },
        )
        assert event.new_state["telegram_chat_id"] == "***REDACTED***"
        assert event.new_state["user_id"] == "***REDACTED***"
        assert event.new_state["channel"] == "telegram"

    @pytest.mark.asyncio
    async def test_emit_redacts_prior_state(self, emitter, repo):
        event = await emitter.emit(
            actor=ActorContext(actor_type=ActorType.USER, actor_id=uuid.uuid4()),
            action=AuditAction.ALERT_UPDATED,
            entity_type="Alert",
            entity_id=uuid.uuid4(),
            old_state={"telegram_chat_id": "111", "status": "active"},
            new_state={"telegram_chat_id": "222", "status": "paused"},
        )
        assert event.old_state["telegram_chat_id"] == "***REDACTED***"
        assert event.new_state["telegram_chat_id"] == "***REDACTED***"

    @pytest.mark.asyncio
    async def test_emit_with_no_state(self, emitter, repo):
        event = await emitter.emit(
            actor=ActorContext(actor_type=ActorType.USER, actor_id=uuid.uuid4()),
            action=AuditAction.ALERT_ARCHIVED,
            entity_type="Alert",
            entity_id=uuid.uuid4(),
        )
        assert event.old_state is None
        assert event.new_state is None

    @pytest.mark.asyncio
    async def test_emit_sets_created_at(self, emitter, repo):
        before = datetime.now(timezone.utc)
        event = await emitter.emit(
            actor=ActorContext(actor_type=ActorType.USER, actor_id=uuid.uuid4()),
            action=AuditAction.ALERT_PAUSED,
            entity_type="Alert",
            entity_id=uuid.uuid4(),
        )
        assert event.created_at >= before

    @pytest.mark.asyncio
    async def test_emit_assigns_uuid(self, emitter, repo):
        event = await emitter.emit(
            actor=ActorContext(actor_type=ActorType.USER, actor_id=uuid.uuid4()),
            action=AuditAction.ALERT_RESUMED,
            entity_type="Alert",
            entity_id=uuid.uuid4(),
        )
        assert isinstance(event.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_emit_with_metadata(self, emitter, repo):
        event = await emitter.emit(
            actor=ActorContext(actor_type=ActorType.API_KEY, actor_id=None),
            action=AuditAction.ALERT_UPDATED,
            entity_type="Alert",
            entity_id=uuid.uuid4(),
            metadata={"trace_id": "req-trace-42"},
        )
        assert event.metadata == {"trace_id": "req-trace-42"}
