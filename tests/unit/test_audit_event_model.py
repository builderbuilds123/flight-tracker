"""Unit tests for AuditEvent domain model (S6-05)."""
import uuid
from datetime import datetime, timezone

import pytest

from src.domain.enums import ActorType, AuditAction
from src.domain.models.audit_event import AuditEvent


def _make_audit_event(**overrides) -> AuditEvent:
    defaults = dict(
        id=uuid.uuid4(),
        actor_id="user-123",
        actor_type=ActorType.USER,
        action=AuditAction.ALERT_CREATED,
        entity_type="Alert",
        entity_id=str(uuid.uuid4()),
        prior_state=None,
        new_state={"status": "active"},
        redacted_fields=[],
        trace_id=None,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return AuditEvent(**defaults)


class TestAuditEventCreation:
    def test_valid_creation(self):
        event = _make_audit_event()
        assert event.actor_type == ActorType.USER
        assert event.action == AuditAction.ALERT_CREATED
        assert event.entity_type == "Alert"

    def test_frozen(self):
        event = _make_audit_event()
        with pytest.raises(AttributeError):
            event.action = AuditAction.ALERT_UPDATED  # type: ignore[misc]

    def test_invalid_actor_type_raises(self):
        with pytest.raises(TypeError, match="actor_type must be ActorType"):
            _make_audit_event(actor_type="bad")

    def test_invalid_action_raises(self):
        with pytest.raises(TypeError, match="action must be AuditAction"):
            _make_audit_event(action="bad")

    def test_all_actions(self):
        for action in AuditAction:
            event = _make_audit_event(action=action)
            assert event.action == action

    def test_all_actor_types(self):
        for at in ActorType:
            event = _make_audit_event(actor_type=at)
            assert event.actor_type == at

    def test_prior_and_new_state(self):
        event = _make_audit_event(
            prior_state={"status": "active"},
            new_state={"status": "paused"},
        )
        assert event.prior_state == {"status": "active"}
        assert event.new_state == {"status": "paused"}

    def test_redacted_fields_stored(self):
        event = _make_audit_event(redacted_fields=["email", "api_key"])
        assert event.redacted_fields == ["email", "api_key"]

    def test_trace_id(self):
        event = _make_audit_event(trace_id="trace-abc-123")
        assert event.trace_id == "trace-abc-123"
