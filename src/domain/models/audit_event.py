"""Immutable audit event domain entity."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from src.domain.enums import ActorType, AuditAction


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """An immutable record of a state-changing action."""

    id: uuid.UUID
    actor_id: str
    actor_type: ActorType
    action: AuditAction
    entity_type: str
    entity_id: str
    prior_state: Optional[dict[str, Any]]
    new_state: Optional[dict[str, Any]]
    redacted_fields: list[str]
    trace_id: Optional[str]
    created_at: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.actor_type, ActorType):
            raise TypeError(f"actor_type must be ActorType, got {type(self.actor_type).__name__}")
        if not isinstance(self.action, AuditAction):
            raise TypeError(f"action must be AuditAction, got {type(self.action).__name__}")
