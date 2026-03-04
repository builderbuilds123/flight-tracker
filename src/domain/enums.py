"""Canonical domain enums for the flight-tracker platform.

These enums are the single source of truth for lifecycle states.
Both API and worker layers must import from this module.
"""
from enum import Enum


class AlertStatus(str, Enum):
    """Alert lifecycle states.

    Transition graph:
        active  -> paused, triggered, archived
        paused  -> active, archived
        triggered -> archived
        archived  -> (terminal)
    """

    ACTIVE = "active"
    PAUSED = "paused"
    TRIGGERED = "triggered"
    ARCHIVED = "archived"

    def allowed_transitions(self) -> frozenset["AlertStatus"]:
        return _ALERT_TRANSITIONS.get(self, frozenset())

    def can_transition_to(self, target: "AlertStatus") -> bool:
        return target in self.allowed_transitions()


_ALERT_TRANSITIONS: dict[AlertStatus, frozenset[AlertStatus]] = {
    AlertStatus.ACTIVE: frozenset({AlertStatus.PAUSED, AlertStatus.TRIGGERED, AlertStatus.ARCHIVED}),
    AlertStatus.PAUSED: frozenset({AlertStatus.ACTIVE, AlertStatus.ARCHIVED}),
    AlertStatus.TRIGGERED: frozenset({AlertStatus.ARCHIVED}),
    AlertStatus.ARCHIVED: frozenset(),
}


class NotificationStatus(str, Enum):
    """Notification delivery lifecycle states.

    Transition graph:
        queued -> sent, failed
        failed -> queued (retry), dead
        sent   -> (terminal)
        dead   -> (terminal)
    """

    QUEUED = "queued"
    SENT = "sent"
    FAILED = "failed"
    DEAD = "dead"

    def allowed_transitions(self) -> frozenset["NotificationStatus"]:
        return _NOTIFICATION_TRANSITIONS.get(self, frozenset())

    def can_transition_to(self, target: "NotificationStatus") -> bool:
        return target in self.allowed_transitions()


_NOTIFICATION_TRANSITIONS: dict[NotificationStatus, frozenset[NotificationStatus]] = {
    NotificationStatus.QUEUED: frozenset({NotificationStatus.SENT, NotificationStatus.FAILED}),
    NotificationStatus.FAILED: frozenset({NotificationStatus.QUEUED, NotificationStatus.DEAD}),
    NotificationStatus.SENT: frozenset(),
    NotificationStatus.DEAD: frozenset(),
}
