"""Lifecycle state machines for domain entities.

Public API:
    AlertStateMachine          – validates alert lifecycle transitions
    NotificationStateMachine   – validates notification delivery transitions
    InvalidTransitionError     – raised when a transition is not allowed
"""

from src.domain.state_machines.errors import InvalidTransitionError
from src.domain.state_machines.alert_state_machine import AlertStateMachine
from src.domain.state_machines.notification_state_machine import NotificationStateMachine

__all__ = [
    "AlertStateMachine",
    "NotificationStateMachine",
    "InvalidTransitionError",
]
