"""Tests for lifecycle state machine transition guards.

Covers every valid transition (succeeds) and every invalid transition
(raises InvalidTransitionError with descriptive message) for both
AlertStateMachine and NotificationStateMachine.
"""
import pytest

from src.domain.enums import AlertStatus, NotificationStatus
from src.domain.state_machines import (
    AlertStateMachine,
    InvalidTransitionError,
    NotificationStateMachine,
)


# ---------------------------------------------------------------------------
# AlertStateMachine – valid transitions
# ---------------------------------------------------------------------------
class TestAlertStateMachineValidTransitions:
    """Every edge in the alert transition graph must succeed."""

    @pytest.mark.parametrize(
        "from_state, to_state",
        [
            (AlertStatus.ACTIVE, AlertStatus.PAUSED),
            (AlertStatus.ACTIVE, AlertStatus.TRIGGERED),
            (AlertStatus.ACTIVE, AlertStatus.ARCHIVED),
            (AlertStatus.PAUSED, AlertStatus.ACTIVE),
            (AlertStatus.PAUSED, AlertStatus.ARCHIVED),
            (AlertStatus.TRIGGERED, AlertStatus.ARCHIVED),
        ],
    )
    def test_valid_transition(self, from_state: AlertStatus, to_state: AlertStatus):
        result = AlertStateMachine.transition(from_state, to_state)
        assert result is to_state


# ---------------------------------------------------------------------------
# AlertStateMachine – invalid transitions
# ---------------------------------------------------------------------------
class TestAlertStateMachineInvalidTransitions:
    """Every non-edge in the alert transition graph must fail."""

    @pytest.mark.parametrize(
        "from_state, to_state",
        [
            # archived is terminal
            (AlertStatus.ARCHIVED, AlertStatus.ACTIVE),
            (AlertStatus.ARCHIVED, AlertStatus.PAUSED),
            (AlertStatus.ARCHIVED, AlertStatus.TRIGGERED),
            # triggered cannot go back
            (AlertStatus.TRIGGERED, AlertStatus.ACTIVE),
            (AlertStatus.TRIGGERED, AlertStatus.PAUSED),
            # paused cannot trigger
            (AlertStatus.PAUSED, AlertStatus.TRIGGERED),
            # self-transitions are invalid
            (AlertStatus.ACTIVE, AlertStatus.ACTIVE),
            (AlertStatus.PAUSED, AlertStatus.PAUSED),
            (AlertStatus.TRIGGERED, AlertStatus.TRIGGERED),
            (AlertStatus.ARCHIVED, AlertStatus.ARCHIVED),
        ],
    )
    def test_invalid_transition_raises(
        self, from_state: AlertStatus, to_state: AlertStatus
    ):
        with pytest.raises(InvalidTransitionError) as exc_info:
            AlertStateMachine.transition(from_state, to_state)
        err = exc_info.value
        assert err.entity_type == "Alert"
        assert err.from_state == from_state
        assert err.to_state == to_state
        assert from_state.value in str(err)
        assert to_state.value in str(err)

    def test_error_includes_allowed_targets(self):
        with pytest.raises(InvalidTransitionError) as exc_info:
            AlertStateMachine.transition(AlertStatus.ARCHIVED, AlertStatus.ACTIVE)
        msg = str(exc_info.value)
        assert "terminal" in msg.lower() or "no valid" in msg.lower()

    def test_error_code_is_stable(self):
        with pytest.raises(InvalidTransitionError) as exc_info:
            AlertStateMachine.transition(AlertStatus.ARCHIVED, AlertStatus.ACTIVE)
        assert exc_info.value.error_code == "INVALID_ALERT_TRANSITION"


# ---------------------------------------------------------------------------
# AlertStateMachine – edge cases
# ---------------------------------------------------------------------------
class TestAlertStateMachineEdgeCases:
    def test_double_pause_raises(self):
        """Pausing an already-paused alert is invalid."""
        with pytest.raises(InvalidTransitionError):
            AlertStateMachine.transition(AlertStatus.PAUSED, AlertStatus.PAUSED)

    def test_archive_from_active(self):
        """Archiving a live alert is valid (user cancellation)."""
        result = AlertStateMachine.transition(AlertStatus.ACTIVE, AlertStatus.ARCHIVED)
        assert result is AlertStatus.ARCHIVED

    def test_resume_archived_alert_raises(self):
        """Cannot resume an archived alert."""
        with pytest.raises(InvalidTransitionError) as exc_info:
            AlertStateMachine.transition(AlertStatus.ARCHIVED, AlertStatus.ACTIVE)
        assert "archived" in str(exc_info.value).lower()


# ---------------------------------------------------------------------------
# NotificationStateMachine – valid transitions
# ---------------------------------------------------------------------------
class TestNotificationStateMachineValidTransitions:
    @pytest.mark.parametrize(
        "from_state, to_state",
        [
            (NotificationStatus.QUEUED, NotificationStatus.SENT),
            (NotificationStatus.QUEUED, NotificationStatus.FAILED),
            (NotificationStatus.FAILED, NotificationStatus.QUEUED),
            (NotificationStatus.FAILED, NotificationStatus.DEAD),
        ],
    )
    def test_valid_transition(
        self, from_state: NotificationStatus, to_state: NotificationStatus
    ):
        result = NotificationStateMachine.transition(from_state, to_state)
        assert result is to_state


# ---------------------------------------------------------------------------
# NotificationStateMachine – invalid transitions
# ---------------------------------------------------------------------------
class TestNotificationStateMachineInvalidTransitions:
    @pytest.mark.parametrize(
        "from_state, to_state",
        [
            # sent is terminal
            (NotificationStatus.SENT, NotificationStatus.QUEUED),
            (NotificationStatus.SENT, NotificationStatus.FAILED),
            (NotificationStatus.SENT, NotificationStatus.DEAD),
            # dead is terminal
            (NotificationStatus.DEAD, NotificationStatus.QUEUED),
            (NotificationStatus.DEAD, NotificationStatus.SENT),
            (NotificationStatus.DEAD, NotificationStatus.FAILED),
            # queued cannot go directly to dead
            (NotificationStatus.QUEUED, NotificationStatus.DEAD),
            # failed cannot go directly to sent
            (NotificationStatus.FAILED, NotificationStatus.SENT),
            # self-transitions
            (NotificationStatus.QUEUED, NotificationStatus.QUEUED),
            (NotificationStatus.SENT, NotificationStatus.SENT),
            (NotificationStatus.FAILED, NotificationStatus.FAILED),
            (NotificationStatus.DEAD, NotificationStatus.DEAD),
        ],
    )
    def test_invalid_transition_raises(
        self, from_state: NotificationStatus, to_state: NotificationStatus
    ):
        with pytest.raises(InvalidTransitionError) as exc_info:
            NotificationStateMachine.transition(from_state, to_state)
        err = exc_info.value
        assert err.entity_type == "Notification"
        assert err.from_state == from_state
        assert err.to_state == to_state

    def test_error_code_is_stable(self):
        with pytest.raises(InvalidTransitionError) as exc_info:
            NotificationStateMachine.transition(
                NotificationStatus.SENT, NotificationStatus.QUEUED
            )
        assert exc_info.value.error_code == "INVALID_NOTIFICATION_TRANSITION"


# ---------------------------------------------------------------------------
# NotificationStateMachine – edge cases
# ---------------------------------------------------------------------------
class TestNotificationStateMachineEdgeCases:
    def test_retry_from_failed_to_queued(self):
        """Failed notification can be retried (back to queued)."""
        result = NotificationStateMachine.transition(
            NotificationStatus.FAILED, NotificationStatus.QUEUED
        )
        assert result is NotificationStatus.QUEUED

    def test_dead_is_truly_terminal(self):
        """Dead notification cannot transition anywhere."""
        for target in NotificationStatus:
            with pytest.raises(InvalidTransitionError):
                NotificationStateMachine.transition(NotificationStatus.DEAD, target)

    def test_sent_is_truly_terminal(self):
        """Sent notification cannot transition anywhere."""
        for target in NotificationStatus:
            with pytest.raises(InvalidTransitionError):
                NotificationStateMachine.transition(NotificationStatus.SENT, target)


# ---------------------------------------------------------------------------
# InvalidTransitionError
# ---------------------------------------------------------------------------
class TestInvalidTransitionError:
    def test_is_exception(self):
        err = InvalidTransitionError(
            entity_type="Alert",
            from_state=AlertStatus.ARCHIVED,
            to_state=AlertStatus.ACTIVE,
            allowed=frozenset(),
        )
        assert isinstance(err, Exception)

    def test_message_is_descriptive(self):
        err = InvalidTransitionError(
            entity_type="Alert",
            from_state=AlertStatus.ARCHIVED,
            to_state=AlertStatus.ACTIVE,
            allowed=frozenset(),
        )
        msg = str(err)
        assert "Alert" in msg
        assert "archived" in msg
        assert "active" in msg

    def test_attributes_are_set(self):
        err = InvalidTransitionError(
            entity_type="Notification",
            from_state=NotificationStatus.SENT,
            to_state=NotificationStatus.QUEUED,
            allowed=frozenset(),
        )
        assert err.entity_type == "Notification"
        assert err.from_state == NotificationStatus.SENT
        assert err.to_state == NotificationStatus.QUEUED
        assert err.allowed == frozenset()
        assert err.error_code == "INVALID_NOTIFICATION_TRANSITION"

    def test_allowed_transitions_in_message(self):
        allowed = frozenset({AlertStatus.PAUSED, AlertStatus.ARCHIVED})
        err = InvalidTransitionError(
            entity_type="Alert",
            from_state=AlertStatus.ACTIVE,
            to_state=AlertStatus.ACTIVE,
            allowed=allowed,
        )
        msg = str(err)
        # The message should mention what transitions ARE allowed
        assert "paused" in msg or "archived" in msg
