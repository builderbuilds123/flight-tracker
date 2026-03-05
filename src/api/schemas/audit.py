"""Audit event API response schemas."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from src.api.schemas.common import CursorPage
from src.domain.enums import ActorType, AuditAction


class AuditEventResponse(BaseModel):
    """Single audit event representation."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: uuid.UUID
    actor_id: str
    actor_type: ActorType
    action: AuditAction
    entity_type: str
    entity_id: str
    prior_state: Optional[dict[str, Any]] = None
    new_state: Optional[dict[str, Any]] = None
    redacted_fields: list[str]
    trace_id: Optional[str] = None
    created_at: datetime


class AuditEventListResponse(CursorPage[AuditEventResponse]):
    """Paginated list of audit events with stable cursor."""

    pass
