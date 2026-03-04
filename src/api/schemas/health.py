"""Health check response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict


class DependencyStatus(BaseModel):
    """Status of a single dependency probe."""

    model_config = ConfigDict(frozen=True)

    name: str
    status: Literal["healthy", "unhealthy"]
    latency_ms: float | None = None
    detail: str | None = None


class HealthResponse(BaseModel):
    """GET /api/v1/health/live — liveness."""

    model_config = ConfigDict(frozen=True)

    status: str
    timestamp: datetime
    version: str


class ReadinessResponse(HealthResponse):
    """GET /api/v1/health/ready — readiness with dependency status."""

    dependencies: list[DependencyStatus]


class FullHealthResponse(ReadinessResponse):
    """GET /api/v1/health — full health with dependency detail."""

    pass
