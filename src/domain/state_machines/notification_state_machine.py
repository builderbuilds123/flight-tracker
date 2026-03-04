"""Notification delivery lifecycle state machine."""
from __future__ import annotations

from src.domain.enums import NotificationStatus
from src.domain.state_machines.errors import InvalidTransitionError


class NotificationStateMachine:
    """Validates and executes notification delivery transitions.

    Transition graph::

        queued  --> sent | failed
        failed  --> queued (retry) | dead
        sent    --> (terminal)
        dead    --> (terminal)
    """

    @staticmethod
    def transition(
        current: NotificationStatus, target: NotificationStatus
    ) -> NotificationStatus:
        """Validate *current* -> *target* and return *target* on success.

        Raises:
            InvalidTransitionError: if the transition is not allowed.
        """
        if not current.can_transition_to(target):
            raise InvalidTransitionError(
                entity_type="Notification",
                from_state=current,
                to_state=target,
                allowed=current.allowed_transitions(),
            )
        return target
