"""Alert domain entity."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from typing import Optional

from src.domain.enums import AlertStatus


@dataclass(frozen=True, slots=True)
class Alert:
    """Canonical alert entity – maps to the ``alerts`` table."""

    id: uuid.UUID
    user_id: uuid.UUID
    origin_iata: str
    destination_iata: str
    depart_date_start: datetime
    depart_date_end: datetime
    max_price: Decimal
    currency: str
    check_interval_min: int
    status: AlertStatus
    last_checked_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.status, AlertStatus):
            raise TypeError(f"status must be AlertStatus, got {type(self.status).__name__}")

    def transition_to(self, target: AlertStatus) -> Alert:
        """Return a new Alert with *target* status after validating the transition.

        Raises:
            InvalidTransitionError: if the transition is not allowed.
        """
        from src.domain.state_machines import AlertStateMachine

        AlertStateMachine.transition(self.status, target)
        return replace(self, status=target)
