"""Notification event history read model (S5-04).

Provides audit/timeline queries for notification events by alert ID.
"""
from __future__ import annotations

import uuid

from src.domain.models.notification_event import NotificationEvent
from src.services.notification_dispatcher import NotificationEventsRepoProtocol


class NotificationHistoryService:
    """Read model for notification event timelines."""

    def __init__(self, repo: NotificationEventsRepoProtocol) -> None:
        self._repo = repo

    async def get_timeline(self, alert_id: uuid.UUID) -> list[NotificationEvent]:
        """Retrieve the full notification event timeline for an alert, ordered by created_at."""
        return await self._repo.list_by_alert_id(alert_id)

    async def get_event(self, event_id: uuid.UUID) -> NotificationEvent | None:
        """Retrieve a single notification event by ID."""
        return await self._repo.get_by_id(event_id)
