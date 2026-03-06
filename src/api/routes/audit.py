"""Audit trail query endpoint (S6-05)."""
from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from src.api.dependencies import get_current_user
from src.api.schemas.audit import AuditEventListResponse, AuditEventResponse
from src.domain.enums import AuditAction
from src.infrastructure.db.repositories.audit_repo import AuditEventsRepo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("", response_model=AuditEventListResponse)
async def list_audit_events(
    current_user: dict = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    entity_type: Optional[str] = Query(None, description="Filter by entity type (e.g. 'Alert')"),
    entity_id: Optional[uuid.UUID] = Query(None, description="Filter by entity ID"),
    actor_id: Optional[uuid.UUID] = Query(None, description="Filter by actor ID"),
    action: Optional[AuditAction] = Query(None, description="Filter by audit action"),
    start_date: Optional[datetime] = Query(None, description="Start of date range (inclusive)"),
    end_date: Optional[datetime] = Query(None, description="End of date range (inclusive)"),
    cursor: Optional[str] = Query(None, description="Pagination cursor (ISO datetime|id of last item)"),
    limit: int = Query(50, ge=1, le=200, description="Max items to return"),
) -> AuditEventListResponse:
    """Retrieve audit events with optional filters and cursor pagination.

    This endpoint is read-only and intended for operators reviewing
    state-change history for alerts and notifications.
    """
    repo = AuditEventsRepo(session)
    items = await repo.query(
        entity_type=entity_type,
        entity_id=entity_id,
        actor_id=actor_id,
        action=action,
        start_date=start_date,
        end_date=end_date,
        cursor=cursor,
        limit=limit + 1,
    )

    has_more = len(items) > limit
    if has_more:
        items = items[:limit]

    next_cursor = None
    if items:
        last = items[-1]
        next_cursor = f"{last.created_at.isoformat()}|{last.id}"

    return AuditEventListResponse(items=items, cursor=next_cursor, has_more=has_more)
