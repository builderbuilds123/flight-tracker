"""Health Check API Endpoints.

- GET /live  — Liveness probe (always 200 if process running)
- GET /ready — Readiness probe (503 when any dependency unhealthy)
- GET /      — Full health with per-dependency detail
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Response, status

from src.api.schemas.health import (
    DependencyStatus,
    FullHealthResponse,
    HealthResponse,
    ReadinessResponse,
)
from src.observability.health_checks import run_all_probes

router = APIRouter()

_VERSION = "1.0.0"


# ------------------------------------------------------------------
# GET /api/v1/health/live
# ------------------------------------------------------------------


@router.get("/live")
async def liveness_check() -> dict:
    """Kubernetes liveness probe — always returns 200."""
    return {"status": "alive"}


# ------------------------------------------------------------------
# GET /api/v1/health/ready
# ------------------------------------------------------------------


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check(response: Response) -> ReadinessResponse:
    """Readiness probe — returns 503 if any dependency is unhealthy."""
    deps = await run_all_probes()
    all_healthy = all(d.status == "healthy" for d in deps)
    overall = "healthy" if all_healthy else "degraded"

    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return ReadinessResponse(
        status=overall,
        timestamp=datetime.now(timezone.utc),
        version=_VERSION,
        dependencies=deps,
    )


# ------------------------------------------------------------------
# GET /api/v1/health
# ------------------------------------------------------------------


@router.get("", response_model=FullHealthResponse)
async def full_health(response: Response) -> FullHealthResponse:
    """Full health endpoint with per-dependency status detail."""
    deps = await run_all_probes()
    all_healthy = all(d.status == "healthy" for d in deps)
    overall = "healthy" if all_healthy else "degraded"

    if not all_healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return FullHealthResponse(
        status=overall,
        timestamp=datetime.now(timezone.utc),
        version=_VERSION,
        dependencies=deps,
    )
