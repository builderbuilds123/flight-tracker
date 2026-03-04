"""Price snapshot API response schemas.

Aligned with ``src.domain.models.PriceSnapshot``.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from src.api.schemas.common import CursorPage


class PriceSnapshotResponse(BaseModel):
    """Single price snapshot resource."""

    model_config = ConfigDict(from_attributes=True, frozen=True)

    id: uuid.UUID
    alert_id: uuid.UUID
    provider: str
    price: Decimal
    currency: str
    itinerary_hash: Optional[str]
    observed_at: datetime


class PriceHistoryResponse(CursorPage[PriceSnapshotResponse]):
    """Paginated list of price snapshots for an alert."""

    pass
