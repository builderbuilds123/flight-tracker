"""Tests for NotificationEvent domain model transition methods."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

from src.domain.enums import NotificationStatus
from src.domain.models.notification_event import NotificationEvent
from src.domain.state_machines.errors import InvalidTransitionError


def _make_event(**overrides) -> NotificationEvent:
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
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return NotificationEvent(**defaults)


class TestNotificationEventTransitionTo:
    def test_queued_to_sent(self):
        event = _make_event(status=NotificationStatus.QUEUED)
        result = event.transition_to(NotificationStatus.SENT)
        assert result.status is NotificationStatus.SENT
        assert result.id == event.id

    def test_queued_to_failed(self):
        event = _make_event(status=NotificationStatus.QUEUED)
        result = event.transition_to(NotificationStatus.FAILED)
        assert result.status is NotificationStatus.FAILED

    def test_failed_to_queued_retry(self):
        event = _make_event(status=NotificationStatus.FAILED)
        result = event.transition_to(NotificationStatus.QUEUED)
        assert result.status is NotificationStatus.QUEUED

    def test_failed_to_dead(self):
        event = _make_event(status=NotificationStatus.FAILED)
        result = event.transition_to(NotificationStatus.DEAD)
        assert result.status is NotificationStatus.DEAD

    def test_invalid_transition_raises(self):
        event = _make_event(status=NotificationStatus.SENT)
        with pytest.raises(InvalidTransitionError):
            event.transition_to(NotificationStatus.QUEUED)

    def test_transition_returns_new_instance(self):
        event = _make_event(status=NotificationStatus.QUEUED)
        result = event.transition_to(NotificationStatus.FAILED)
        assert result is not event
        assert event.status is NotificationStatus.QUEUED


class TestNotificationEventRecordAttempt:
    def test_increments_attempt_count(self):
        event = _make_event(attempt_count=0)
        result = event.record_attempt()
        assert result.attempt_count == 1

    def test_records_error(self):
        event = _make_event(attempt_count=1)
        result = event.record_attempt(error="Connection timeout")
        assert result.attempt_count == 2
        assert result.last_error == "Connection timeout"

    def test_clears_previous_error(self):
        event = _make_event(attempt_count=1, last_error="old error")
        result = event.record_attempt(error=None)
        assert result.last_error is None


class TestNotificationEventMarkSent:
    def test_mark_sent_transitions_and_records_timestamp(self):
        now = datetime.now(timezone.utc)
        event = _make_event(status=NotificationStatus.QUEUED)
        result = event.mark_sent(sent_at=now)
        assert result.status is NotificationStatus.SENT
        assert result.sent_at == now

    def test_mark_sent_from_invalid_state_raises(self):
        now = datetime.now(timezone.utc)
        event = _make_event(status=NotificationStatus.DEAD)
        with pytest.raises(InvalidTransitionError):
            event.mark_sent(sent_at=now)
