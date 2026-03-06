"""Dependency health probes used by /health and /health/ready endpoints."""
from __future__ import annotations

import asyncio
import importlib
import sys
import time
from typing import Callable, Awaitable

from src.config.health_settings import (
    DB_PROBE_TIMEOUT,
    REDIS_PROBE_TIMEOUT,
    CELERY_PROBE_TIMEOUT,
    READINESS_TIMEOUT,
)

_health_schema = importlib.import_module("src.api.schemas.health")
DependencyStatus = _health_schema.DependencyStatus


async def _timed_probe(
    name: str,
    coro: Callable[[], Awaitable[None]],
    timeout: float,
) -> DependencyStatus:
    """Run *coro* with a wall-clock *timeout* and return a DependencyStatus."""
    start = time.monotonic()
    try:
        await asyncio.wait_for(coro(), timeout=timeout)
        elapsed = (time.monotonic() - start) * 1000
        return DependencyStatus(name=name, status="healthy", latency_ms=round(elapsed, 2))
    except asyncio.TimeoutError:
        elapsed = (time.monotonic() - start) * 1000
        return DependencyStatus(
            name=name, status="unhealthy", latency_ms=round(elapsed, 2), detail="timeout"
        )
    except Exception as exc:  # noqa: BLE001
        elapsed = (time.monotonic() - start) * 1000
        return DependencyStatus(
            name=name, status="unhealthy", latency_ms=round(elapsed, 2), detail=str(exc)
        )


# ------------------------------------------------------------------
# Individual probes
# ------------------------------------------------------------------

async def check_db() -> DependencyStatus:
    """Probe PostgreSQL via SQLAlchemy async engine."""
    from sqlalchemy import text
    from app.core.database import engine

    async def _probe() -> None:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

    return await _timed_probe("database", _probe, DB_PROBE_TIMEOUT)


async def check_redis() -> DependencyStatus:
    """Probe Redis with PING."""
    aioredis = sys.modules.get("redis.asyncio")
    if aioredis is None:
        aioredis = importlib.import_module("redis.asyncio")

    app_config = sys.modules.get("app.core.config")
    if app_config is None:
        app_config = importlib.import_module("app.core.config")
    settings = app_config.settings

    async def _probe() -> None:
        r = aioredis.from_url(settings.REDIS_URL)
        try:
            await r.ping()
        finally:
            await r.aclose()

    return await _timed_probe("redis", _probe, REDIS_PROBE_TIMEOUT)


async def check_celery() -> DependencyStatus:
    """Probe Celery by inspecting worker availability."""
    async def _probe() -> None:
        from app.tasks.price_checker import celery_app

        loop = asyncio.get_running_loop()
        inspector = celery_app.control.inspect(timeout=CELERY_PROBE_TIMEOUT)
        pong = await loop.run_in_executor(None, inspector.ping)
        if not pong:
            raise RuntimeError("no workers responded")

    return await _timed_probe("celery", _probe, CELERY_PROBE_TIMEOUT)


# ------------------------------------------------------------------
# Aggregate
# ------------------------------------------------------------------

async def run_all_probes() -> list[DependencyStatus]:
    """Run every dependency probe concurrently within *READINESS_TIMEOUT*."""
    probes = [check_db(), check_redis(), check_celery()]
    results: list[DependencyStatus] = list(
        await asyncio.wait_for(
            asyncio.gather(*probes, return_exceptions=False),
            timeout=READINESS_TIMEOUT,
        )
    )
    return results
