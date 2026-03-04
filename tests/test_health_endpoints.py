"""Integration tests for health API endpoints.

Tests cover:
- Liveness always returns 200
- Readiness returns 200 when all deps healthy, 503 when degraded
- Full health returns dependency-level detail

Uses a minimal FastAPI app with only the health router to avoid
pulling in unrelated app dependencies.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from src.api.schemas.health import DependencyStatus

# Import health module directly to avoid app.api.__init__ pulling in
# unrelated routers that need extra dependencies (email-validator, etc.).
import importlib
_health_mod = importlib.import_module("app.api.health")
health_router = _health_mod.router

# Build a minimal app with just the health router.
_app = FastAPI()
_app.include_router(health_router, prefix="/api/v1/health", tags=["health"])


def _healthy(name: str) -> DependencyStatus:
    return DependencyStatus(name=name, status="healthy", latency_ms=1.0)


def _unhealthy(name: str, detail: str = "down") -> DependencyStatus:
    return DependencyStatus(name=name, status="unhealthy", latency_ms=1.0, detail=detail)


@pytest.fixture
async def client():
    transport = ASGITransport(app=_app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


# -------------------------------------------------------------------
# GET /api/v1/health/live — Liveness
# -------------------------------------------------------------------

class TestLiveness:
    @pytest.mark.asyncio
    async def test_liveness_returns_200(self, client):
        resp = await client.get("/api/v1/health/live")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "alive"

    @pytest.mark.asyncio
    async def test_liveness_always_up(self, client):
        """Liveness is unconditional — no dependency checks."""
        resp = await client.get("/api/v1/health/live")
        assert resp.status_code == 200


# -------------------------------------------------------------------
# GET /api/v1/health/ready — Readiness
# -------------------------------------------------------------------

class TestReadiness:
    @pytest.mark.asyncio
    async def test_ready_all_healthy(self, client):
        deps = [_healthy("database"), _healthy("redis"), _healthy("celery")]
        with patch("app.api.health.run_all_probes", return_value=deps):
            resp = await client.get("/api/v1/health/ready")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert len(body["dependencies"]) == 3

    @pytest.mark.asyncio
    async def test_ready_degraded_returns_503(self, client):
        deps = [_healthy("database"), _unhealthy("redis"), _healthy("celery")]
        with patch("app.api.health.run_all_probes", return_value=deps):
            resp = await client.get("/api/v1/health/ready")

        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_ready_includes_dependency_detail(self, client):
        deps = [_healthy("database"), _unhealthy("redis", "connection refused"), _healthy("celery")]
        with patch("app.api.health.run_all_probes", return_value=deps):
            resp = await client.get("/api/v1/health/ready")

        body = resp.json()
        redis_dep = next(d for d in body["dependencies"] if d["name"] == "redis")
        assert redis_dep["status"] == "unhealthy"
        assert redis_dep["detail"] == "connection refused"


# -------------------------------------------------------------------
# GET /api/v1/health — Full Health
# -------------------------------------------------------------------

class TestFullHealth:
    @pytest.mark.asyncio
    async def test_full_health_all_up(self, client):
        deps = [_healthy("database"), _healthy("redis"), _healthy("celery")]
        with patch("app.api.health.run_all_probes", return_value=deps):
            resp = await client.get("/api/v1/health")

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert "dependencies" in body
        assert "version" in body
        assert "timestamp" in body

    @pytest.mark.asyncio
    async def test_full_health_degraded(self, client):
        deps = [_unhealthy("database", "timeout"), _healthy("redis"), _healthy("celery")]
        with patch("app.api.health.run_all_probes", return_value=deps):
            resp = await client.get("/api/v1/health")

        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"

    @pytest.mark.asyncio
    async def test_full_health_has_latency(self, client):
        deps = [_healthy("database"), _healthy("redis"), _healthy("celery")]
        with patch("app.api.health.run_all_probes", return_value=deps):
            resp = await client.get("/api/v1/health")

        body = resp.json()
        for dep in body["dependencies"]:
            assert "latency_ms" in dep

    @pytest.mark.asyncio
    async def test_all_deps_down(self, client):
        deps = [
            _unhealthy("database", "connection refused"),
            _unhealthy("redis", "timeout"),
            _unhealthy("celery", "no workers"),
        ]
        with patch("app.api.health.run_all_probes", return_value=deps):
            resp = await client.get("/api/v1/health")

        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert all(d["status"] == "unhealthy" for d in body["dependencies"])
