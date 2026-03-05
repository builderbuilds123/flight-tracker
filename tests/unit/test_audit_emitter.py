"""Unit tests for AuditEmitter service (S6-05)."""
import uuid
from datetime import datetime, timezone

import pytest

from src.domain.enums import ActorType, AuditAction
from src.domain.models.audit_event import AuditEvent
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
            actor_id="user-1",
            actor_type=ActorType.USER,
            action=AuditAction.ALERT_CREATED,
            entity_type="Alert",
            entity_id="alert-abc",
            new_state={"status": "active"},
        )
        assert len(repo.events) == 1
        assert repo.events[0].id == event.id
        assert event.action == AuditAction.ALERT_CREATED
        assert event.entity_type == "Alert"

    @pytest.mark.asyncio
    async def test_emit_redacts_sensitive_fields(self, emitter, repo):
        event = await emitter.emit(
            actor_id="system",
            actor_type=ActorType.SYSTEM,
            action=AuditAction.NOTIFICATION_SENT,
            entity_type="Notification",
            entity_id="notif-1",
            new_state={
                "channel": "telegram",
                "telegram_chat_id": "12345",
                "api_key": "secret-key",
            },
        )
        assert event.new_state["telegram_chat_id"] == "***REDACTED***"
        assert event.new_state["api_key"] == "***REDACTED***"
        assert event.new_state["channel"] == "telegram"
        assert "api_key" in event.redacted_fields
        assert "telegram_chat_id" in event.redacted_fields

    @pytest.mark.asyncio
    async def test_emit_redacts_prior_state(self, emitter, repo):
        event = await emitter.emit(
            actor_id="user-1",
            actor_type=ActorType.USER,
            action=AuditAction.ALERT_UPDATED,
            entity_type="Alert",
            entity_id="alert-1",
            prior_state={"email": "old@example.com", "status": "active"},
            new_state={"email": "new@example.com", "status": "paused"},
        )
        assert event.prior_state["email"] == "***REDACTED***"
        assert event.new_state["email"] == "***REDACTED***"
        assert "email" in event.redacted_fields

    @pytest.mark.asyncio
    async def test_emit_with_no_state(self, emitter, repo):
        event = await emitter.emit(
            actor_id="user-1",
            actor_type=ActorType.USER,
            action=AuditAction.ALERT_ARCHIVED,
            entity_type="Alert",
            entity_id="alert-1",
        )
        assert event.prior_state is None
        assert event.new_state is None
        assert event.redacted_fields == []

    @pytest.mark.asyncio
    async def test_emit_sets_created_at(self, emitter, repo):
        before = datetime.now(timezone.utc)
        event = await emitter.emit(
            actor_id="user-1",
            actor_type=ActorType.USER,
            action=AuditAction.ALERT_PAUSED,
            entity_type="Alert",
            entity_id="alert-1",
        )
        assert event.created_at >= before

    @pytest.mark.asyncio
    async def test_emit_assigns_uuid(self, emitter, repo):
        event = await emitter.emit(
            actor_id="user-1",
            actor_type=ActorType.USER,
            action=AuditAction.ALERT_RESUMED,
            entity_type="Alert",
            entity_id="alert-1",
        )
        assert isinstance(event.id, uuid.UUID)

    @pytest.mark.asyncio
    async def test_emit_with_trace_id(self, emitter, repo):
        event = await emitter.emit(
            actor_id="api-key-xyz",
            actor_type=ActorType.API_KEY,
            action=AuditAction.ALERT_UPDATED,
            entity_type="Alert",
            entity_id="alert-1",
            trace_id="req-trace-42",
        )
        assert event.trace_id == "req-trace-42"
