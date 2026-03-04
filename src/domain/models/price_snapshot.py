"""PriceSnapshot domain entity."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional


@dataclass(frozen=True, slots=True)
class PriceSnapshot:
    """Canonical price snapshot entity – maps to the ``price_snapshots`` table."""

    id: uuid.UUID
    alert_id: uuid.UUID
    provider: str
    price: Decimal
    currency: str
    itinerary_hash: Optional[str]
    raw_payload: Optional[dict[str, Any]]
    observed_at: datetime
