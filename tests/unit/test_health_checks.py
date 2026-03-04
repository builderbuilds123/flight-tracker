"""Unit tests for health probes – healthy, degraded, and failed states."""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.observability.health_checks import (
    _timed_probe,
    check_db,
    check_redis,
    check_celery,
    run_all_probes,
)
from src.api.schemas.health import DependencyStatus


# -------------------------------------------------------------------
# _timed_probe
# -------------------------------------------------------------------

class TestTimedProbe:
    @pytest.mark.asyncio
    async def test_healthy_probe(self):
        async def _ok() -> None:
            pass

        result = await _timed_probe("test", _ok, timeout=2.0)
        assert result.status == "healthy"
        assert result.name == "test"
        assert result.latency_ms is not None
        assert result.detail is None

    @pytest.mark.asyncio
    async def test_probe_timeout(self):
        async def _slow() -> None:
            await asyncio.sleep(10)

        result = await _timed_probe("test", _slow, timeout=0.05)
        assert result.status == "unhealthy"
        assert result.detail == "timeout"
        assert result.latency_ms is not None

    @pytest.mark.asyncio
    async def test_probe_exception(self):
        async def _fail() -> None:
            raise ConnectionError("refused")

        result = await _timed_probe("test", _fail, timeout=2.0)
        assert result.status == "unhealthy"
        assert "refused" in result.detail


# -------------------------------------------------------------------
# check_db
# -------------------------------------------------------------------

class TestCheckDb:
    @pytest.mark.asyncio
    async def test_healthy_db(self):
        mock_conn = AsyncMock()
        mock_conn.execute = AsyncMock()

        mock_engine = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_engine.connect.return_value = mock_ctx

        with patch("src.observability.health_checks.engine", mock_engine, create=True), \
             patch.dict("sys.modules", {"app.core.database": MagicMock(engine=mock_engine)}):
            # Re-import to pick up mock
            from src.observability import health_checks
            # Patch at module level after import
            with patch.object(health_checks, "check_db", wraps=health_checks.check_db):
                result = await check_db()

        assert result.name == "database"
        assert result.status == "healthy"

    @pytest.mark.asyncio
    async def test_unhealthy_db(self):
        mock_engine = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(side_effect=ConnectionError("db down"))
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_engine.connect.return_value = mock_ctx

        with patch.dict("sys.modules", {"app.core.database": MagicMock(engine=mock_engine)}):
            result = await check_db()

        assert result.name == "database"
        assert result.status == "unhealthy"
        assert "db down" in result.detail


# -------------------------------------------------------------------
# check_redis
# -------------------------------------------------------------------

class TestCheckRedis:
    @pytest.mark.asyncio
    async def test_healthy_redis(self):
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(return_value=True)
        mock_client.aclose = AsyncMock()

        mock_aioredis = MagicMock()
        mock_aioredis.from_url.return_value = mock_client

        mock_settings = MagicMock()
        mock_settings.REDIS_URL = "redis://localhost:6379/0"

        with patch.dict("sys.modules", {
            "redis.asyncio": mock_aioredis,
            "app.core.config": MagicMock(settings=mock_settings),
            "app.core": MagicMock(),
            "app": MagicMock(),
        }):
            result = await check_redis()

        assert result.name == "redis"
        assert result.status == "healthy"

    @pytest.mark.asyncio
    async def test_unhealthy_redis(self):
        mock_client = AsyncMock()
        mock_client.ping = AsyncMock(side_effect=ConnectionError("redis down"))
        mock_client.aclose = AsyncMock()

        mock_aioredis = MagicMock()
        mock_aioredis.from_url.return_value = mock_client

        mock_settings = MagicMock()
        mock_settings.REDIS_URL = "redis://localhost:6379/0"

        with patch.dict("sys.modules", {
            "redis.asyncio": mock_aioredis,
            "app.core.config": MagicMock(settings=mock_settings),
            "app.core": MagicMock(),
            "app": MagicMock(),
        }):
            result = await check_redis()

        assert result.name == "redis"
        assert result.status == "unhealthy"
        assert "redis down" in result.detail


# -------------------------------------------------------------------
# check_celery
# -------------------------------------------------------------------

class TestCheckCelery:
    @pytest.mark.asyncio
    async def test_healthy_celery(self):
        mock_inspector = MagicMock()
        mock_inspector.ping.return_value = {"worker1": {"ok": "pong"}}

        mock_celery = MagicMock()
        mock_celery.control.inspect.return_value = mock_inspector

        mock_module = MagicMock()
        mock_module.celery_app = mock_celery

        with patch.dict("sys.modules", {"app.tasks.price_checker": mock_module}):
            result = await check_celery()

        assert result.name == "celery"
        assert result.status == "healthy"

    @pytest.mark.asyncio
    async def test_no_workers(self):
        mock_inspector = MagicMock()
        mock_inspector.ping.return_value = None

        mock_celery = MagicMock()
        mock_celery.control.inspect.return_value = mock_inspector

        mock_module = MagicMock()
        mock_module.celery_app = mock_celery

        with patch.dict("sys.modules", {"app.tasks.price_checker": mock_module}):
            result = await check_celery()

        assert result.name == "celery"
        assert result.status == "unhealthy"
        assert "no workers" in result.detail


# -------------------------------------------------------------------
# run_all_probes
# -------------------------------------------------------------------

class TestRunAllProbes:
    @pytest.mark.asyncio
    async def test_all_healthy(self):
        healthy = DependencyStatus(name="x", status="healthy", latency_ms=1.0)

        with patch("src.observability.health_checks.check_db", return_value=healthy), \
             patch("src.observability.health_checks.check_redis", return_value=healthy), \
             patch("src.observability.health_checks.check_celery", return_value=healthy):
            results = await run_all_probes()

        assert len(results) == 3
        assert all(r.status == "healthy" for r in results)

    @pytest.mark.asyncio
    async def test_partial_failure(self):
        healthy = DependencyStatus(name="ok", status="healthy", latency_ms=1.0)
        unhealthy = DependencyStatus(name="bad", status="unhealthy", detail="down")

        with patch("src.observability.health_checks.check_db", return_value=healthy), \
             patch("src.observability.health_checks.check_redis", return_value=unhealthy), \
             patch("src.observability.health_checks.check_celery", return_value=healthy):
            results = await run_all_probes()

        assert len(results) == 3
        statuses = {r.name: r.status for r in results}
        assert statuses["bad"] == "unhealthy"
