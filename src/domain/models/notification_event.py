"""NotificationEvent domain entity."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Optional

from src.domain.enums import NotificationStatus


@dataclass(frozen=True, slots=True)
class NotificationEvent:
    """Canonical notification event entity – maps to the ``notification_events`` table."""

    id: uuid.UUID
    alert_id: uuid.UUID
    snapshot_id: uuid.UUID
    channel: str
    idempotency_key: str
    status: NotificationStatus
    attempt_count: int
    last_error: Optional[str]
    sent_at: Optional[datetime]
    created_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.status, NotificationStatus):
            raise TypeError(f"status must be NotificationStatus, got {type(self.status).__name__}")

    def transition_to(self, target: NotificationStatus) -> NotificationEvent:
        """Return a new NotificationEvent with *target* status after validating the transition.

        Raises:
            InvalidTransitionError: if the transition is not allowed.
        """
        from src.domain.state_machines import NotificationStateMachine

        NotificationStateMachine.transition(self.status, target)
        return replace(self, status=target)

    def record_attempt(self, error: Optional[str] = None) -> NotificationEvent:
        """Return a new NotificationEvent with incremented attempt_count and optional error."""
        return replace(self, attempt_count=self.attempt_count + 1, last_error=error)

    def mark_sent(self, sent_at: datetime) -> NotificationEvent:
        """Transition to SENT and record the sent timestamp."""
        new = self.transition_to(NotificationStatus.SENT)
        return replace(new, sent_at=sent_at)
