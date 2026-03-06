"""Repository for AuditEvent persistence (S6-05)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, tuple_
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.enums import AuditAction
from src.domain.mappers.entity_mappers import audit_event_from_orm, audit_event_to_orm
from src.domain.models.audit_event import AuditEvent
from src.infrastructure.db.models import AuditEventORM


class AuditEventsRepo:
    """Async SQLAlchemy repository for audit events."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, event: AuditEvent) -> AuditEvent:
        orm = audit_event_to_orm(event)
        self._session.add(orm)
        await self._session.flush()
        return audit_event_from_orm(orm)

    async def get_by_id(self, event_id: uuid.UUID) -> Optional[AuditEvent]:
        stmt = select(AuditEventORM).where(AuditEventORM.id == event_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return audit_event_from_orm(orm) if orm else None

    async def query(
        self,
        *,
        entity_type: Optional[str] = None,
        entity_id: Optional[uuid.UUID] = None,
        actor_id: Optional[uuid.UUID] = None,
        action: Optional[AuditAction] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        cursor: Optional[str] = None,
        limit: int = 50,
    ) -> list[AuditEvent]:
        """Query audit events with optional filters and cursor-based pagination.

        Events are returned in reverse-chronological order (newest first).
        The cursor is ``created_at|id`` of the last item in the previous page,
        using (created_at, id) as a tie-breaker for stable ordering.
        """
        stmt = select(AuditEventORM)

        if entity_type is not None:
            stmt = stmt.where(AuditEventORM.entity_type == entity_type)
        if entity_id is not None:
            stmt = stmt.where(AuditEventORM.entity_id == entity_id)
        if actor_id is not None:
            stmt = stmt.where(AuditEventORM.actor_id == actor_id)
        if action is not None:
            stmt = stmt.where(AuditEventORM.action == action)
        if start_date is not None:
            stmt = stmt.where(AuditEventORM.created_at >= start_date)
        if end_date is not None:
            stmt = stmt.where(AuditEventORM.created_at <= end_date)
        if cursor is not None:
            try:
                parts = cursor.split("|", 1)
                if len(parts) == 2:
                    cursor_ts = datetime.fromisoformat(parts[0])
                    cursor_id = uuid.UUID(parts[1])
                    stmt = stmt.where(
                        tuple_(AuditEventORM.created_at, AuditEventORM.id)
                        < tuple_(cursor_ts, cursor_id)
                    )
            except (ValueError, TypeError):
                pass  # Invalid cursor — treat as no cursor

        stmt = stmt.order_by(
            AuditEventORM.created_at.desc(),
            AuditEventORM.id.desc(),
        ).limit(limit)

        result = await self._session.execute(stmt)
        return [audit_event_from_orm(orm) for orm in result.scalars().all()]
