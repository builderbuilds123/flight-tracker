"""Immutable audit event domain entity."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from src.domain.enums import ActorType, AuditAction


@dataclass(frozen=True, slots=True)
class ActorContext:
    """Identity of the actor performing a state mutation."""

    actor_type: ActorType
    actor_id: uuid.UUID | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.actor_type, ActorType):
            raise TypeError(f"actor_type must be ActorType, got {type(self.actor_type).__name__}")
        if self.actor_id is not None and not isinstance(self.actor_id, uuid.UUID):
            raise TypeError("actor_id must be UUID or None")


@dataclass(frozen=True, slots=True)
class AuditEvent:
    """An immutable record of a state-changing action."""

    id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_type: ActorType
    action: AuditAction
    entity_type: str
    entity_id: uuid.UUID
    old_state: dict[str, Any] | None
    new_state: dict[str, Any] | None
    metadata: dict[str, Any]
    created_at: datetime

    def __post_init__(self) -> None:
        if self.actor_id is not None and not isinstance(self.actor_id, uuid.UUID):
            raise TypeError("actor_id must be UUID or None")
        if not isinstance(self.actor_type, ActorType):
            raise TypeError(f"actor_type must be ActorType, got {type(self.actor_type).__name__}")
        if not isinstance(self.action, AuditAction):
            raise TypeError(f"action must be AuditAction, got {type(self.action).__name__}")
        if not isinstance(self.entity_id, uuid.UUID):
            raise TypeError("entity_id must be UUID")
