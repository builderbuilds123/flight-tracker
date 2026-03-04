"""Alert API request/response schemas.

Field names are aligned 1-to-1 with the canonical ``src.domain.models.Alert``
entity to prevent drift.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.api.schemas.common import CursorPage, validate_currency, validate_iata
from src.domain.enums import AlertStatus


# ---------------------------------------------------------------------------
# Request schemas (extra='forbid' for strict input)
# ---------------------------------------------------------------------------
class AlertCreate(BaseModel):
    """POST /api/v1/alerts — create a new price alert."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: uuid.UUID
    origin_iata: str = Field(..., min_length=3, max_length=3)
    destination_iata: str = Field(..., min_length=3, max_length=3)
    depart_date_start: datetime
    depart_date_end: datetime
    max_price: Decimal = Field(..., gt=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    check_interval_min: int = Field(default=60, ge=1, le=10080)

    @field_validator("origin_iata", "destination_iata")
    @classmethod
    def _validate_iata(cls, v: str) -> str:
        return validate_iata(v)

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, v: str) -> str:
        return validate_currency(v)

    @model_validator(mode="after")
    def _validate_dates_and_route(self) -> AlertCreate:
        if self.depart_date_end <= self.depart_date_start:
            raise ValueError("depart_date_end must be after depart_date_start")
        if self.origin_iata == self.destination_iata:
            raise ValueError("origin_iata and destination_iata must differ")
        return self


class AlertUpdate(BaseModel):
    """PATCH /api/v1/alerts/{id} — update mutable alert fields."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_price: Optional[Decimal] = Field(None, gt=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    depart_date_start: Optional[datetime] = None
    depart_date_end: Optional[datetime] = None
    check_interval_min: Optional[int] = Field(None, ge=1, le=10080)

    @field_validator("currency")
    @classmethod
    def _validate_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is not None:
            return validate_currency(v)
        return v


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------
class AlertResponse(BaseModel):
    """Single alert resource representation."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: uuid.UUID
    user_id: uuid.UUID
    origin_iata: str
    destination_iata: str
    depart_date_start: datetime
    depart_date_end: datetime
    max_price: Decimal
    currency: str
    check_interval_min: int
    status: AlertStatus
    last_checked_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class AlertListResponse(CursorPage[AlertResponse]):
    """Paginated list of alerts with stable cursor."""

    pass
