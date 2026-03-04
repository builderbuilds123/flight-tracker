"""Tests for notification delivery state machine persistence (S5-04).

Tests the NotificationDispatcher service which orchestrates:
- State-guarded transitions
- Attempt count and error tracking
- Retry logic with max retries -> dead letter
- Idempotency key dedup
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional
from unittest.mock import AsyncMock

import pytest

from src.domain.enums import NotificationStatus
from src.domain.models.notification_event import NotificationEvent
from src.domain.state_machines.errors import InvalidTransitionError


# ---------------------------------------------------------------------------
# In-memory fake repository for unit testing
# ---------------------------------------------------------------------------
class FakeNotificationEventsRepo:
    """In-memory repository for unit tests."""

    def __init__(self):
        self._events: dict[uuid.UUID, NotificationEvent] = {}
        self._by_idempotency_key: dict[str, uuid.UUID] = {}

    async def create(self, event: NotificationEvent) -> NotificationEvent:
        if event.idempotency_key in self._by_idempotency_key:
            raise DuplicateIdempotencyKeyError(event.idempotency_key)
        self._events[event.id] = event
        self._by_idempotency_key[event.idempotency_key] = event.id
        return event

    async def get_by_id(self, event_id: uuid.UUID) -> Optional[NotificationEvent]:
        return self._events.get(event_id)

    async def get_by_idempotency_key(self, key: str) -> Optional[NotificationEvent]:
        eid = self._by_idempotency_key.get(key)
        return self._events.get(eid) if eid else None

    async def update(self, event: NotificationEvent) -> NotificationEvent:
        self._events[event.id] = event
        return event

    async def list_by_alert_id(self, alert_id: uuid.UUID) -> list[NotificationEvent]:
        return [e for e in self._events.values() if e.alert_id == alert_id]


# We import the real service after defining the fake
from src.services.notification_dispatcher import (
    NotificationDispatcher,
    DuplicateIdempotencyKeyError,
)


def _make_event(**overrides) -> NotificationEvent:
    defaults = dict(
        id=uuid.uuid4(),
        alert_id=uuid.uuid4(),
        snapshot_id=uuid.uuid4(),
        channel="telegram",
        idempotency_key=f"key-{uuid.uuid4().hex[:8]}",
        status=NotificationStatus.QUEUED,
        attempt_count=0,
        last_error=None,
        sent_at=None,
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return NotificationEvent(**defaults)


# ---------------------------------------------------------------------------
# Delivery success path
# ---------------------------------------------------------------------------
class TestDeliverySuccess:
    @pytest.fixture
    def repo(self):
        return FakeNotificationEventsRepo()

    @pytest.fixture
    def sender(self):
        return AsyncMock(return_value=None)

    @pytest.fixture
    def dispatcher(self, repo, sender):
        return NotificationDispatcher(repo=repo, sender=sender, max_retries=3)

    @pytest.mark.asyncio
    async def test_successful_delivery_transitions_to_sent(self, dispatcher, repo, sender):
        event = _make_event()
        await repo.create(event)

        result = await dispatcher.deliver(event.id)

        assert result.status is NotificationStatus.SENT
        assert result.sent_at is not None
        assert result.attempt_count == 1
        sender.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_successful_delivery_persists_state(self, dispatcher, repo, sender):
        event = _make_event()
        await repo.create(event)

        await dispatcher.deliver(event.id)

        persisted = await repo.get_by_id(event.id)
        assert persisted.status is NotificationStatus.SENT


# ---------------------------------------------------------------------------
# Delivery failure + retry path
# ---------------------------------------------------------------------------
class TestDeliveryFailureAndRetry:
    @pytest.fixture
    def repo(self):
        return FakeNotificationEventsRepo()

    @pytest.fixture
    def failing_sender(self):
        return AsyncMock(side_effect=RuntimeError("Telegram API error"))

    @pytest.fixture
    def dispatcher(self, repo, failing_sender):
        return NotificationDispatcher(repo=repo, sender=failing_sender, max_retries=3)

    @pytest.mark.asyncio
    async def test_failure_transitions_to_failed(self, dispatcher, repo):
        event = _make_event()
        await repo.create(event)

        result = await dispatcher.deliver(event.id)

        assert result.status is NotificationStatus.FAILED
        assert result.attempt_count == 1
        assert "Telegram API error" in result.last_error

    @pytest.mark.asyncio
    async def test_retry_requeues_failed_event(self, dispatcher, repo):
        event = _make_event(status=NotificationStatus.FAILED, attempt_count=1)
        await repo.create(event)

        result = await dispatcher.retry(event.id)

        assert result.status is NotificationStatus.QUEUED

    @pytest.mark.asyncio
    async def test_dead_letter_after_max_retries(self, dispatcher, repo):
        event = _make_event(
            status=NotificationStatus.FAILED,
            attempt_count=3,
            last_error="repeated failure",
        )
        await repo.create(event)

        result = await dispatcher.retry(event.id)

        assert result.status is NotificationStatus.DEAD


# ---------------------------------------------------------------------------
# Dead letter terminal state
# ---------------------------------------------------------------------------
class TestDeadLetterTerminal:
    @pytest.fixture
    def repo(self):
        return FakeNotificationEventsRepo()

    @pytest.fixture
    def dispatcher(self, repo):
        return NotificationDispatcher(repo=repo, sender=AsyncMock(), max_retries=3)

    @pytest.mark.asyncio
    async def test_cannot_deliver_dead_event(self, dispatcher, repo):
        event = _make_event(status=NotificationStatus.DEAD)
        await repo.create(event)

        with pytest.raises(InvalidTransitionError):
            await dispatcher.deliver(event.id)

    @pytest.mark.asyncio
    async def test_cannot_retry_dead_event(self, dispatcher, repo):
        event = _make_event(status=NotificationStatus.DEAD, attempt_count=5)
        await repo.create(event)

        with pytest.raises(InvalidTransitionError):
            await dispatcher.retry(event.id)


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------
class TestIdempotency:
    @pytest.fixture
    def repo(self):
        return FakeNotificationEventsRepo()

    @pytest.fixture
    def dispatcher(self, repo):
        return NotificationDispatcher(repo=repo, sender=AsyncMock(), max_retries=3)

    @pytest.mark.asyncio
    async def test_duplicate_idempotency_key_raises(self, repo):
        key = "dedup-key-123"
        event1 = _make_event(idempotency_key=key)
        await repo.create(event1)

        event2 = _make_event(idempotency_key=key)
        with pytest.raises(DuplicateIdempotencyKeyError):
            await repo.create(event2)

    @pytest.mark.asyncio
    async def test_enqueue_with_dedup_returns_existing(self, dispatcher, repo):
        key = "dedup-key-456"
        event = _make_event(idempotency_key=key)
        await repo.create(event)

        result = await dispatcher.enqueue(
            alert_id=event.alert_id,
            snapshot_id=event.snapshot_id,
            channel="telegram",
            idempotency_key=key,
        )

        assert result.id == event.id  # returned existing, not created new


# ---------------------------------------------------------------------------
# Event timeline query
# ---------------------------------------------------------------------------
class TestEventTimeline:
    @pytest.fixture
    def repo(self):
        return FakeNotificationEventsRepo()

    @pytest.fixture
    def dispatcher(self, repo):
        return NotificationDispatcher(repo=repo, sender=AsyncMock(), max_retries=3)

    @pytest.mark.asyncio
    async def test_list_events_by_alert_id(self, dispatcher, repo):
        alert_id = uuid.uuid4()
        e1 = _make_event(alert_id=alert_id, idempotency_key="k1")
        e2 = _make_event(alert_id=alert_id, idempotency_key="k2")
        e3 = _make_event(alert_id=uuid.uuid4(), idempotency_key="k3")  # different alert
        await repo.create(e1)
        await repo.create(e2)
        await repo.create(e3)

        events = await dispatcher.get_timeline(alert_id)

        assert len(events) == 2
        assert all(e.alert_id == alert_id for e in events)
