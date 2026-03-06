"""Audit event API response schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.api.schemas.common import CursorPage
from src.domain.enums import ActorType, AuditAction


class AuditEventResponse(BaseModel):
    """Single audit event representation."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: uuid.UUID
    actor_id: uuid.UUID | None
    actor_type: ActorType
    action: AuditAction
    entity_type: str
    entity_id: uuid.UUID
    old_state: dict[str, Any] | None = None
    new_state: dict[str, Any] | None = None
    metadata: dict[str, Any]
    created_at: datetime


class AuditEventListResponse(CursorPage[AuditEventResponse]):
    """Paginated list of audit events with stable cursor."""

    pass
