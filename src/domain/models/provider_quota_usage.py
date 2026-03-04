"""ProviderQuotaUsage domain entity."""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ProviderQuotaUsage:
    """Canonical provider quota usage entity – maps to the ``provider_quota_usage`` table."""

    id: uuid.UUID
    provider: str
    window_start: datetime
    window_end: datetime
    requests_used: int
    requests_limit: int
