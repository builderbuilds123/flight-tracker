"""Tests for domain enums – allowed values and transition guards."""
import pytest

from src.domain.enums import AlertStatus, NotificationStatus


class TestAlertStatus:
    """Alert lifecycle enum: active, paused, triggered, archived."""

    def test_allowed_values(self):
        expected = {"active", "paused", "triggered", "archived"}
        actual = {s.value for s in AlertStatus}
        assert actual == expected

    def test_member_count(self):
        assert len(AlertStatus) == 4

    def test_construct_from_value(self):
        assert AlertStatus("active") is AlertStatus.ACTIVE
        assert AlertStatus("paused") is AlertStatus.PAUSED
        assert AlertStatus("triggered") is AlertStatus.TRIGGERED
        assert AlertStatus("archived") is AlertStatus.ARCHIVED

    def test_reject_invalid_value(self):
        with pytest.raises(ValueError):
            AlertStatus("expired")
        with pytest.raises(ValueError):
            AlertStatus("cancelled")

    # --- Transition guards ---

    def test_active_can_transition_to_paused(self):
        assert AlertStatus.PAUSED in AlertStatus.ACTIVE.allowed_transitions()

    def test_active_can_transition_to_triggered(self):
        assert AlertStatus.TRIGGERED in AlertStatus.ACTIVE.allowed_transitions()

    def test_active_can_transition_to_archived(self):
        assert AlertStatus.ARCHIVED in AlertStatus.ACTIVE.allowed_transitions()

    def test_paused_can_resume_to_active(self):
        assert AlertStatus.ACTIVE in AlertStatus.PAUSED.allowed_transitions()

    def test_paused_can_archive(self):
        assert AlertStatus.ARCHIVED in AlertStatus.PAUSED.allowed_transitions()

    def test_triggered_can_archive(self):
        assert AlertStatus.ARCHIVED in AlertStatus.TRIGGERED.allowed_transitions()

    def test_archived_is_terminal(self):
        assert AlertStatus.ARCHIVED.allowed_transitions() == frozenset()

    def test_can_transition_to_returns_true_for_valid(self):
        assert AlertStatus.ACTIVE.can_transition_to(AlertStatus.PAUSED) is True

    def test_can_transition_to_returns_false_for_invalid(self):
        assert AlertStatus.ARCHIVED.can_transition_to(AlertStatus.ACTIVE) is False

    def test_triggered_cannot_go_back_to_active(self):
        assert AlertStatus.ACTIVE not in AlertStatus.TRIGGERED.allowed_transitions()


class TestNotificationStatus:
    """Notification lifecycle enum: queued, sent, failed, dead."""

    def test_allowed_values(self):
        expected = {"queued", "sent", "failed", "dead"}
        actual = {s.value for s in NotificationStatus}
        assert actual == expected

    def test_member_count(self):
        assert len(NotificationStatus) == 4

    def test_construct_from_value(self):
        assert NotificationStatus("queued") is NotificationStatus.QUEUED
        assert NotificationStatus("sent") is NotificationStatus.SENT
        assert NotificationStatus("failed") is NotificationStatus.FAILED
        assert NotificationStatus("dead") is NotificationStatus.DEAD

    def test_reject_invalid_value(self):
        with pytest.raises(ValueError):
            NotificationStatus("pending")

    # --- Transition guards ---

    def test_queued_can_transition_to_sent(self):
        assert NotificationStatus.SENT in NotificationStatus.QUEUED.allowed_transitions()

    def test_queued_can_transition_to_failed(self):
        assert NotificationStatus.FAILED in NotificationStatus.QUEUED.allowed_transitions()

    def test_failed_can_retry_to_queued(self):
        assert NotificationStatus.QUEUED in NotificationStatus.FAILED.allowed_transitions()

    def test_failed_can_go_dead(self):
        assert NotificationStatus.DEAD in NotificationStatus.FAILED.allowed_transitions()

    def test_sent_is_terminal(self):
        assert NotificationStatus.SENT.allowed_transitions() == frozenset()

    def test_dead_is_terminal(self):
        assert NotificationStatus.DEAD.allowed_transitions() == frozenset()
