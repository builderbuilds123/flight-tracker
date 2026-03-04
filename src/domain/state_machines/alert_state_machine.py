"""Alert lifecycle state machine."""
from __future__ import annotations

from src.domain.enums import AlertStatus
from src.domain.state_machines.errors import InvalidTransitionError


class AlertStateMachine:
    """Validates and executes alert lifecycle transitions.

    Transition graph::

        active  --> paused | triggered | archived
        paused  --> active | archived
        triggered --> archived
        archived  --> (terminal)
    """

    @staticmethod
    def transition(current: AlertStatus, target: AlertStatus) -> AlertStatus:
        """Validate *current* -> *target* and return *target* on success.

        Raises:
            InvalidTransitionError: if the transition is not allowed.
        """
        if not current.can_transition_to(target):
            raise InvalidTransitionError(
                entity_type="Alert",
                from_state=current,
                to_state=target,
                allowed=current.allowed_transitions(),
            )
        return target
