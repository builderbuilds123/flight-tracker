"""Audit trail query endpoint (S6-05)."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query

from src.api.schemas.audit import AuditEventListResponse, AuditEventResponse
from src.domain.enums import AuditAction

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])


@router.get("", response_model=AuditEventListResponse)
async def list_audit_events(
    entity_type: Optional[str] = Query(None, description="Filter by entity type (e.g. 'Alert')"),
    entity_id: Optional[str] = Query(None, description="Filter by entity ID"),
    actor_id: Optional[str] = Query(None, description="Filter by actor ID"),
    action: Optional[AuditAction] = Query(None, description="Filter by audit action"),
    start_date: Optional[datetime] = Query(None, description="Start of date range (inclusive)"),
    end_date: Optional[datetime] = Query(None, description="End of date range (inclusive)"),
    cursor: Optional[str] = Query(None, description="Pagination cursor (ISO datetime of last item)"),
    limit: int = Query(50, ge=1, le=200, description="Max items to return"),
) -> AuditEventListResponse:
    """Retrieve audit events with optional filters and cursor pagination.

    This endpoint is read-only and intended for operators reviewing
    state-change history for alerts and notifications.

    NOTE: This handler currently returns a stub. Full wiring to the
    repository requires dependency-injection of AsyncSession which
    will be connected when the FastAPI app wires up the session middleware.
    """
    # Placeholder: wired via DI when session middleware is available.
    # The actual query logic lives in AuditEventsRepo.query().
    return AuditEventListResponse(items=[], cursor=None, has_more=False)
