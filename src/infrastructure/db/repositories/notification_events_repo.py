"""Repository for NotificationEvent persistence (S5-04).

Implements NotificationEventsRepoProtocol from the dispatcher service layer.
"""
from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.domain.mappers.entity_mappers import (
    notification_event_from_orm,
    notification_event_to_orm,
)
from src.domain.models.notification_event import NotificationEvent
from src.infrastructure.db.models import NotificationEventORM
from src.services.notification_dispatcher import DuplicateIdempotencyKeyError


class NotificationEventsRepo:
    """Async SQLAlchemy repository for notification events."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, event: NotificationEvent) -> NotificationEvent:
        orm = notification_event_to_orm(event)
        self._session.add(orm)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            raise DuplicateIdempotencyKeyError(event.idempotency_key)
        return notification_event_from_orm(orm)

    async def get_by_id(self, event_id: uuid.UUID) -> Optional[NotificationEvent]:
        stmt = select(NotificationEventORM).where(NotificationEventORM.id == event_id)
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return notification_event_from_orm(orm) if orm else None

    async def get_by_idempotency_key(self, key: str) -> Optional[NotificationEvent]:
        stmt = select(NotificationEventORM).where(
            NotificationEventORM.idempotency_key == key
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        return notification_event_from_orm(orm) if orm else None

    async def update(self, event: NotificationEvent) -> NotificationEvent:
        stmt = select(NotificationEventORM).where(
            NotificationEventORM.id == event.id
        )
        result = await self._session.execute(stmt)
        orm = result.scalar_one_or_none()
        if orm is None:
            raise ValueError(f"NotificationEvent {event.id} not found")

        orm.status = event.status
        orm.attempt_count = event.attempt_count
        orm.last_error = event.last_error
        orm.sent_at = event.sent_at
        await self._session.flush()
        return notification_event_from_orm(orm)

    async def list_by_alert_id(self, alert_id: uuid.UUID) -> list[NotificationEvent]:
        stmt = (
            select(NotificationEventORM)
            .where(NotificationEventORM.alert_id == alert_id)
            .order_by(NotificationEventORM.created_at)
        )
        result = await self._session.execute(stmt)
        return [notification_event_from_orm(orm) for orm in result.scalars().all()]
