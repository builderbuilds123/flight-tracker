"""
Alert Management API Endpoints
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field, field_validator

router = APIRouter()


class AlertCreate(BaseModel):
    """Create a new alert (legacy app-layer contract used by tests)."""

    user_id: str
    origin: str
    destination: str
    max_price: float = Field(gt=0)
    currency: str = "USD"
    check_frequency_hours: int = Field(default=24, ge=1)

    @field_validator("origin", "destination")
    @classmethod
    def validate_iata(cls, value: str) -> str:
        value = value.upper()
        if len(value) != 3 or not value.isalpha():
            raise ValueError("IATA codes must be 3 letters")
        return value


class AlertResponse(BaseModel):
    """Alert response model for legacy app-layer endpoints."""

    id: int
    user_id: str
    origin: str
    destination: str
    max_price: float
    currency: str
    is_active: bool
    created_at: datetime


class AlertUpdate(BaseModel):
    max_price: Optional[float] = Field(default=None, gt=0)
    is_active: Optional[bool] = None


_alerts_store: Dict[int, AlertResponse] = {}
_next_alert_id = 1


def reset_alert_store() -> None:
    """Reset in-memory alert state (used by test app startup)."""
    global _next_alert_id
    _alerts_store.clear()
    _next_alert_id = 1


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(alert: AlertCreate) -> AlertResponse:
    """Create an alert in an in-memory store used by legacy tests."""
    global _next_alert_id
    stored = AlertResponse(
        id=_next_alert_id,
        user_id=alert.user_id,
        origin=alert.origin,
        destination=alert.destination,
        max_price=alert.max_price,
        currency=alert.currency,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    _alerts_store[stored.id] = stored
    _next_alert_id += 1
    return stored


@router.get("", response_model=List[AlertResponse])
async def list_alerts(
    user_id: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> List[AlertResponse]:
    """List alerts with simple in-memory filtering."""
    items = list(_alerts_store.values())
    if user_id is not None:
        items = [item for item in items if item.user_id == user_id]
    if status_filter is not None:
        wanted = status_filter.lower()
        items = [
            item
            for item in items
            if ("active" if item.is_active else "paused") == wanted
        ]
    return items[offset : offset + limit]


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(alert_id: int) -> AlertResponse:
    """Get a specific alert by ID"""
    alert = _alerts_store.get(alert_id)
    if alert is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
        )
    return alert


@router.put("/{alert_id}", response_model=AlertResponse)
async def update_alert(alert_id: int, payload: AlertUpdate) -> AlertResponse:
    """Update an alert."""
    current = _alerts_store.get(alert_id)
    if current is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
        )

    updated_data = current.model_dump()
    if payload.max_price is not None:
        updated_data["max_price"] = payload.max_price
    if payload.is_active is not None:
        updated_data["is_active"] = payload.is_active

    updated = AlertResponse(**updated_data)
    _alerts_store[alert_id] = updated
    return updated


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(alert_id: int) -> None:
    """Delete an alert."""
    if alert_id not in _alerts_store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Alert not found"
        )
    del _alerts_store[alert_id]
