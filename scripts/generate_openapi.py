"""Generate the OpenAPI v1 contract snapshot.

Run:  python scripts/generate_openapi.py
Output: contracts/openapi-v1.json
"""
import json
import sys
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import FastAPI, Query

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.api.schemas import (
    AlertCreate,
    AlertListResponse,
    AlertResponse,
    AlertUpdate,
    ErrorResponse,
    HealthResponse,
    PriceHistoryResponse,
    ReadinessResponse,
)
from src.api.schemas.health import FullHealthResponse

app = FastAPI(title="Flight Price Tracker", version="1.0.0")


@app.post("/api/v1/alerts", response_model=AlertResponse, status_code=201,
          responses={422: {"model": ErrorResponse}})
async def create_alert(body: AlertCreate) -> AlertResponse: ...


@app.get("/api/v1/alerts", response_model=AlertListResponse)
async def list_alerts(
    status: Optional[str] = None,
    cursor: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
) -> AlertListResponse: ...


@app.get("/api/v1/alerts/{alert_id}", response_model=AlertResponse,
         responses={404: {"model": ErrorResponse}})
async def get_alert(alert_id: UUID) -> AlertResponse: ...


@app.patch("/api/v1/alerts/{alert_id}", response_model=AlertResponse,
           responses={404: {"model": ErrorResponse}, 422: {"model": ErrorResponse}})
async def update_alert(alert_id: UUID, body: AlertUpdate) -> AlertResponse: ...


@app.post("/api/v1/alerts/{alert_id}/pause", response_model=AlertResponse,
          responses={404: {"model": ErrorResponse}})
async def pause_alert(alert_id: UUID) -> AlertResponse: ...


@app.post("/api/v1/alerts/{alert_id}/resume", response_model=AlertResponse,
          responses={404: {"model": ErrorResponse}})
async def resume_alert(alert_id: UUID) -> AlertResponse: ...


@app.delete("/api/v1/alerts/{alert_id}", status_code=204,
            responses={404: {"model": ErrorResponse}})
async def delete_alert(alert_id: UUID) -> None: ...


@app.get("/api/v1/alerts/{alert_id}/history", response_model=PriceHistoryResponse)
async def get_alert_history(
    alert_id: UUID,
    cursor: Optional[str] = None,
    limit: int = Query(50, ge=1, le=100),
) -> PriceHistoryResponse: ...


@app.get("/api/v1/health", response_model=FullHealthResponse)
async def health() -> FullHealthResponse: ...


@app.get("/api/v1/health/ready", response_model=ReadinessResponse)
async def readiness() -> ReadinessResponse: ...


@app.get("/api/v1/health/live")
async def liveness() -> dict: ...


def main() -> None:
    spec = app.openapi()
    out = Path(__file__).resolve().parent.parent / "contracts" / "openapi-v1.json"
    out.write_text(json.dumps(spec, indent=2, default=str) + "\n")
    print(f"Written to {out}")


if __name__ == "__main__":
    main()
