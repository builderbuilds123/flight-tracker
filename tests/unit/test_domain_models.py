"""Contract tests for canonical domain entities.

Assert that required fields exist with correct types, matching the
architecture data-model spec (04-architecture.md §3).
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from src.domain.models.user import User
from src.domain.models.alert import Alert
from src.domain.models.price_snapshot import PriceSnapshot
from src.domain.models.notification_event import NotificationEvent
from src.domain.models.provider_quota_usage import ProviderQuotaUsage
from src.domain.enums import AlertStatus, NotificationStatus


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------
class TestUserEntity:
    def _make_user(self, **overrides):
        defaults = dict(
            id=uuid.uuid4(),
            telegram_chat_id="123456",
            timezone="UTC",
            locale="en",
            created_at=datetime.now(timezone.utc),
        )
        defaults.update(overrides)
        return User(**defaults)

    def test_required_fields_present(self):
        u = self._make_user()
        assert isinstance(u.id, uuid.UUID)
        assert isinstance(u.telegram_chat_id, str)
        assert isinstance(u.timezone, str)
        assert isinstance(u.locale, str)
        assert isinstance(u.created_at, datetime)

    def test_telegram_chat_id_required(self):
        with pytest.raises((TypeError, ValueError)):
            User(id=uuid.uuid4(), timezone="UTC", locale="en",
                 created_at=datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Alert
# ---------------------------------------------------------------------------
class TestAlertEntity:
    def _make_alert(self, **overrides):
        defaults = dict(
            id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            origin_iata="JFK",
            destination_iata="LHR",
            depart_date_start=datetime(2026, 6, 1, tzinfo=timezone.utc),
            depart_date_end=datetime(2026, 6, 15, tzinfo=timezone.utc),
            max_price=Decimal("500.00"),
            currency="USD",
            check_interval_min=60,
            status=AlertStatus.ACTIVE,
            last_checked_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        defaults.update(overrides)
        return Alert(**defaults)

    def test_required_fields_present(self):
        a = self._make_alert()
        assert isinstance(a.id, uuid.UUID)
        assert isinstance(a.user_id, uuid.UUID)
        assert isinstance(a.origin_iata, str)
        assert isinstance(a.destination_iata, str)
        assert isinstance(a.max_price, Decimal)
        assert isinstance(a.currency, str)
        assert isinstance(a.check_interval_min, int)
        assert isinstance(a.status, AlertStatus)
        assert isinstance(a.created_at, datetime)
        assert isinstance(a.updated_at, datetime)

    def test_status_is_alert_enum(self):
        a = self._make_alert()
        assert a.status is AlertStatus.ACTIVE

    def test_last_checked_at_nullable(self):
        a = self._make_alert(last_checked_at=None)
        assert a.last_checked_at is None

    def test_iata_codes_three_chars(self):
        a = self._make_alert(origin_iata="JFK", destination_iata="LHR")
        assert len(a.origin_iata) == 3
        assert len(a.destination_iata) == 3

    def test_rejects_invalid_status_type(self):
        with pytest.raises((TypeError, ValueError)):
            self._make_alert(status="not_an_enum")


# ---------------------------------------------------------------------------
# PriceSnapshot
# ---------------------------------------------------------------------------
class TestPriceSnapshotEntity:
    def _make_snapshot(self, **overrides):
        defaults = dict(
            id=uuid.uuid4(),
            alert_id=uuid.uuid4(),
            provider="amadeus",
            price=Decimal("349.99"),
            currency="USD",
            itinerary_hash="abc123hash",
            raw_payload={"flights": []},
            observed_at=datetime.now(timezone.utc),
        )
        defaults.update(overrides)
        return PriceSnapshot(**defaults)

    def test_required_fields_present(self):
        s = self._make_snapshot()
        assert isinstance(s.id, uuid.UUID)
        assert isinstance(s.alert_id, uuid.UUID)
        assert isinstance(s.provider, str)
        assert isinstance(s.price, Decimal)
        assert isinstance(s.currency, str)
        assert isinstance(s.observed_at, datetime)

    def test_raw_payload_is_dict(self):
        s = self._make_snapshot()
        assert isinstance(s.raw_payload, dict)

    def test_itinerary_hash_is_string(self):
        s = self._make_snapshot()
        assert isinstance(s.itinerary_hash, str)


# ---------------------------------------------------------------------------
# NotificationEvent
# ---------------------------------------------------------------------------
class TestNotificationEventEntity:
    def _make_event(self, **overrides):
        defaults = dict(
            id=uuid.uuid4(),
            alert_id=uuid.uuid4(),
            snapshot_id=uuid.uuid4(),
            channel="telegram",
            idempotency_key="idem-key-001",
            status=NotificationStatus.QUEUED,
            attempt_count=0,
            last_error=None,
            sent_at=None,
            created_at=datetime.now(timezone.utc),
        )
        defaults.update(overrides)
        return NotificationEvent(**defaults)

    def test_required_fields_present(self):
        e = self._make_event()
        assert isinstance(e.id, uuid.UUID)
        assert isinstance(e.alert_id, uuid.UUID)
        assert isinstance(e.snapshot_id, uuid.UUID)
        assert isinstance(e.channel, str)
        assert isinstance(e.idempotency_key, str)
        assert isinstance(e.status, NotificationStatus)
        assert isinstance(e.attempt_count, int)

    def test_status_is_notification_enum(self):
        e = self._make_event()
        assert e.status is NotificationStatus.QUEUED

    def test_nullable_fields(self):
        e = self._make_event(last_error=None, sent_at=None)
        assert e.last_error is None
        assert e.sent_at is None

    def test_rejects_invalid_status_type(self):
        with pytest.raises((TypeError, ValueError)):
            self._make_event(status="bogus")


# ---------------------------------------------------------------------------
# ProviderQuotaUsage
# ---------------------------------------------------------------------------
class TestProviderQuotaUsageEntity:
    def _make_quota(self, **overrides):
        defaults = dict(
            id=uuid.uuid4(),
            provider="amadeus",
            window_start=datetime(2026, 3, 1, tzinfo=timezone.utc),
            window_end=datetime(2026, 3, 2, tzinfo=timezone.utc),
            requests_used=42,
            requests_limit=1000,
        )
        defaults.update(overrides)
        return ProviderQuotaUsage(**defaults)

    def test_required_fields_present(self):
        q = self._make_quota()
        assert isinstance(q.id, uuid.UUID)
        assert isinstance(q.provider, str)
        assert isinstance(q.window_start, datetime)
        assert isinstance(q.window_end, datetime)
        assert isinstance(q.requests_used, int)
        assert isinstance(q.requests_limit, int)
