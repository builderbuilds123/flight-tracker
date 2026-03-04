"""API schema contracts – single import boundary.

All request/response schemas for the /api/v1 surface are defined here.
Import from this package rather than individual modules.
"""
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

__all__ = [
    "AlertCreate",
    "AlertUpdate",
    "AlertResponse",
    "AlertListResponse",
    "CursorPage",
    "ErrorDetail",
    "ErrorResponse",
    "PriceSnapshotResponse",
    "PriceHistoryResponse",
    "HealthResponse",
    "ReadinessResponse",
]
