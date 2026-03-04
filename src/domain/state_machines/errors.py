"""Typed error for invalid lifecycle transitions."""
from __future__ import annotations

from enum import Enum


class InvalidTransitionError(Exception):
    """Raised when an entity lifecycle transition is not allowed.

    Attributes:
        entity_type: "Alert" or "Notification".
        from_state:  Current state enum member.
        to_state:    Requested target state enum member.
        allowed:     frozenset of valid target states from *from_state*.
        error_code:  Stable machine-readable code for API error envelopes.
    """

    def __init__(
        self,
        *,
        entity_type: str,
        from_state: Enum,
        to_state: Enum,
        allowed: frozenset,
    ) -> None:
        self.entity_type = entity_type
        self.from_state = from_state
        self.to_state = to_state
        self.allowed = allowed
        self.error_code = f"INVALID_{entity_type.upper()}_TRANSITION"

        if allowed:
            targets = ", ".join(sorted(s.value for s in allowed))
            hint = f"Valid transitions from '{from_state.value}': [{targets}]."
        else:
            hint = f"'{from_state.value}' is terminal — no valid transitions."

        msg = (
            f"{entity_type} transition from '{from_state.value}' to "
            f"'{to_state.value}' is not allowed. {hint}"
        )
        super().__init__(msg)
