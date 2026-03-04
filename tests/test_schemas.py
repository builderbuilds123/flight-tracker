"""Tests for API schema contracts (S1-03).

Validates:
- Field alignment with canonical domain models
- Custom validators (IATA, currency, date ranges, price thresholds)
- Strict input rejection (extra fields forbidden)
- Round-trip serialization (domain -> schema -> JSON -> schema)
- Cursor pagination structure
- Error envelope structure
"""
import uuid
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.api.schemas.alerts import (
    AlertCreate,
    AlertUpdate,
    AlertResponse,
    AlertListResponse,
)
from src.api.schemas.common import (
    CursorPage,
    ErrorDetail,
    ErrorResponse,
)
from src.api.schemas.prices import (
    PriceSnapshotResponse,
    PriceHistoryResponse,
)
from src.api.schemas.health import (
    HealthResponse,
    ReadinessResponse,
)
from src.domain.enums import AlertStatus


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
def _valid_alert_create() -> dict:
    return {
        "user_id": str(uuid.uuid4()),
        "origin_iata": "JFK",
        "destination_iata": "LHR",
        "depart_date_start": "2026-06-01T00:00:00Z",
        "depart_date_end": "2026-06-15T00:00:00Z",
        "max_price": "450.00",
        "currency": "USD",
        "check_interval_min": 60,
    }


def _valid_alert_response() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "id": str(uuid.uuid4()),
        "user_id": str(uuid.uuid4()),
        "origin_iata": "JFK",
        "destination_iata": "LHR",
        "depart_date_start": "2026-06-01T00:00:00Z",
        "depart_date_end": "2026-06-15T00:00:00Z",
        "max_price": "450.00",
        "currency": "USD",
        "check_interval_min": 60,
        "status": "active",
        "last_checked_at": None,
        "created_at": now,
        "updated_at": now,
    }


# ===================================================================
# AlertCreate Tests
# ===================================================================
class TestAlertCreate:
    def test_valid_payload(self):
        data = _valid_alert_create()
        schema = AlertCreate(**data)
        assert schema.origin_iata == "JFK"
        assert schema.destination_iata == "LHR"
        assert schema.max_price == Decimal("450.00")
        assert schema.currency == "USD"
        assert schema.check_interval_min == 60

    def test_iata_must_be_3_uppercase_alpha(self):
        for bad in ["jfk", "JFKX", "12", "J K", "", "J1K"]:
            data = _valid_alert_create()
            data["origin_iata"] = bad
            with pytest.raises(ValidationError) as exc_info:
                AlertCreate(**data)
            errors = exc_info.value.errors()
            assert any("origin_iata" in str(e["loc"]) for e in errors)

    def test_destination_iata_validated(self):
        data = _valid_alert_create()
        data["destination_iata"] = "xx"
        with pytest.raises(ValidationError):
            AlertCreate(**data)

    def test_same_origin_destination_rejected(self):
        data = _valid_alert_create()
        data["destination_iata"] = data["origin_iata"]
        with pytest.raises(ValidationError):
            AlertCreate(**data)

    def test_currency_must_be_3_uppercase_alpha(self):
        for bad in ["usd", "US", "USDD", "U1D", ""]:
            data = _valid_alert_create()
            data["currency"] = bad
            with pytest.raises(ValidationError):
                AlertCreate(**data)

    def test_valid_currencies(self):
        for code in ["USD", "EUR", "GBP", "JPY"]:
            data = _valid_alert_create()
            data["currency"] = code
            schema = AlertCreate(**data)
            assert schema.currency == code

    def test_max_price_must_be_positive(self):
        for bad in [0, -1, "-10.00"]:
            data = _valid_alert_create()
            data["max_price"] = bad
            with pytest.raises(ValidationError):
                AlertCreate(**data)

    def test_max_price_accepts_decimal_string(self):
        data = _valid_alert_create()
        data["max_price"] = "199.99"
        schema = AlertCreate(**data)
        assert schema.max_price == Decimal("199.99")

    def test_date_end_must_be_after_start(self):
        data = _valid_alert_create()
        data["depart_date_start"] = "2026-06-15T00:00:00Z"
        data["depart_date_end"] = "2026-06-01T00:00:00Z"
        with pytest.raises(ValidationError):
            AlertCreate(**data)

    def test_check_interval_min_bounds(self):
        data = _valid_alert_create()
        data["check_interval_min"] = 0
        with pytest.raises(ValidationError):
            AlertCreate(**data)

        data["check_interval_min"] = 10081  # > 7 days in minutes
        with pytest.raises(ValidationError):
            AlertCreate(**data)

    def test_extra_fields_forbidden(self):
        data = _valid_alert_create()
        data["rogue_field"] = "should fail"
        with pytest.raises(ValidationError):
            AlertCreate(**data)

    def test_user_id_must_be_valid_uuid(self):
        data = _valid_alert_create()
        data["user_id"] = "not-a-uuid"
        with pytest.raises(ValidationError):
            AlertCreate(**data)


# ===================================================================
# AlertUpdate Tests
# ===================================================================
class TestAlertUpdate:
    def test_partial_update_max_price(self):
        schema = AlertUpdate(max_price="500.00")
        assert schema.max_price == Decimal("500.00")
        assert schema.currency is None
        assert schema.check_interval_min is None

    def test_all_fields_optional(self):
        schema = AlertUpdate()
        assert schema.max_price is None

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            AlertUpdate(rogue="nope")

    def test_max_price_must_be_positive_if_provided(self):
        with pytest.raises(ValidationError):
            AlertUpdate(max_price="-5.00")

    def test_update_currency_validated(self):
        with pytest.raises(ValidationError):
            AlertUpdate(currency="bad")


# ===================================================================
# AlertResponse Tests
# ===================================================================
class TestAlertResponse:
    def test_valid_response(self):
        data = _valid_alert_response()
        schema = AlertResponse(**data)
        assert isinstance(schema.id, uuid.UUID)
        assert schema.status == AlertStatus.ACTIVE

    def test_status_is_alert_enum(self):
        data = _valid_alert_response()
        schema = AlertResponse(**data)
        assert isinstance(schema.status, AlertStatus)

    def test_invalid_status_rejected(self):
        data = _valid_alert_response()
        data["status"] = "nonexistent"
        with pytest.raises(ValidationError):
            AlertResponse(**data)

    def test_round_trip_json_serialization(self):
        data = _valid_alert_response()
        schema = AlertResponse(**data)
        json_str = schema.model_dump_json()
        restored = AlertResponse.model_validate_json(json_str)
        assert restored.id == schema.id
        assert restored.origin_iata == schema.origin_iata
        assert restored.max_price == schema.max_price
        assert restored.status == schema.status


# ===================================================================
# AlertListResponse / Cursor Pagination Tests
# ===================================================================
class TestAlertListResponse:
    def test_empty_list(self):
        schema = AlertListResponse(items=[], cursor=None, has_more=False)
        assert schema.items == []
        assert schema.cursor is None
        assert schema.has_more is False

    def test_with_items_and_cursor(self):
        items = [_valid_alert_response() for _ in range(3)]
        schema = AlertListResponse(items=items, cursor="abc123", has_more=True)
        assert len(schema.items) == 3
        assert schema.cursor == "abc123"
        assert schema.has_more is True


# ===================================================================
# ErrorResponse Tests
# ===================================================================
class TestErrorResponse:
    def test_error_envelope(self):
        schema = ErrorResponse(
            error=ErrorDetail(
                code="VALIDATION_ERROR",
                message="Invalid input",
                details=[{"field": "origin_iata", "message": "Must be 3 uppercase letters"}],
            )
        )
        assert schema.error.code == "VALIDATION_ERROR"
        assert len(schema.error.details) == 1

    def test_error_without_details(self):
        schema = ErrorResponse(
            error=ErrorDetail(code="NOT_FOUND", message="Alert not found")
        )
        assert schema.error.details is None


# ===================================================================
# PriceSnapshotResponse Tests
# ===================================================================
class TestPriceSnapshotResponse:
    def test_valid_snapshot(self):
        data = {
            "id": str(uuid.uuid4()),
            "alert_id": str(uuid.uuid4()),
            "provider": "amadeus",
            "price": "350.00",
            "currency": "USD",
            "itinerary_hash": "abc123def456",
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
        schema = PriceSnapshotResponse(**data)
        assert schema.provider == "amadeus"
        assert schema.price == Decimal("350.00")

    def test_optional_itinerary_hash(self):
        data = {
            "id": str(uuid.uuid4()),
            "alert_id": str(uuid.uuid4()),
            "provider": "serpapi",
            "price": "200.00",
            "currency": "EUR",
            "itinerary_hash": None,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
        schema = PriceSnapshotResponse(**data)
        assert schema.itinerary_hash is None


class TestPriceHistoryResponse:
    def test_valid_history(self):
        snapshot = {
            "id": str(uuid.uuid4()),
            "alert_id": str(uuid.uuid4()),
            "provider": "amadeus",
            "price": "350.00",
            "currency": "USD",
            "itinerary_hash": None,
            "observed_at": datetime.now(timezone.utc).isoformat(),
        }
        schema = PriceHistoryResponse(
            items=[snapshot],
            cursor=None,
            has_more=False,
        )
        assert len(schema.items) == 1


# ===================================================================
# HealthResponse Tests
# ===================================================================
class TestHealthResponse:
    def test_healthy(self):
        schema = HealthResponse(
            status="healthy",
            timestamp=datetime.now(timezone.utc),
            version="1.0.0",
        )
        assert schema.status == "healthy"

    def test_readiness(self):
        from src.api.schemas.health import DependencyStatus
        schema = ReadinessResponse(
            status="healthy",
            timestamp=datetime.now(timezone.utc),
            version="1.0.0",
            dependencies=[
                DependencyStatus(name="database", status="healthy", latency_ms=1.0),
                DependencyStatus(name="redis", status="healthy", latency_ms=1.0),
                DependencyStatus(name="celery", status="healthy", latency_ms=1.0),
            ],
        )
        assert len(schema.dependencies) == 3
        assert all(d.status == "healthy" for d in schema.dependencies)


# ===================================================================
# Domain Model Field Alignment Tests
# ===================================================================
class TestDomainAlignment:
    """Verify schema fields align with canonical domain entity fields."""

    def test_alert_create_fields_subset_of_domain(self):
        """All AlertCreate fields must exist on the domain Alert entity."""
        from src.domain.models.alert import Alert
        import dataclasses

        domain_fields = {f.name for f in dataclasses.fields(Alert)}
        # AlertCreate fields that map to domain (excluding computed/auto fields)
        schema_fields = set(AlertCreate.model_fields.keys())
        unmapped = schema_fields - domain_fields
        # user_id is on domain, all others should map
        assert unmapped == set(), f"Schema fields not in domain: {unmapped}"

    def test_alert_response_covers_domain_fields(self):
        """AlertResponse must expose all domain Alert fields."""
        from src.domain.models.alert import Alert
        import dataclasses

        domain_fields = {f.name for f in dataclasses.fields(Alert)}
        response_fields = set(AlertResponse.model_fields.keys())
        missing = domain_fields - response_fields
        assert missing == set(), f"Domain fields missing from response: {missing}"
