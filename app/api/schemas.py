"""
Pydantic schemas for API request/response validation
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AlertCreate(BaseModel):
    """Schema for creating a new alert"""
    user_id: str = Field(..., description="Telegram user ID or external user ID")
    origin: str = Field(..., min_length=3, max_length=3, description="Origin airport IATA code")
    destination: str = Field(..., min_length=3, max_length=3, description="Destination airport IATA code")
    departure_date: Optional[datetime] = Field(None, description="Preferred departure date")
    return_date: Optional[datetime] = Field(None, description="Return date for round trips")
    max_price: float = Field(..., gt=0, description="Maximum price threshold for alert")
    currency: str = Field(default="USD", max_length=3)
    check_frequency_hours: int = Field(default=6, ge=1, le=168)


class AlertUpdate(BaseModel):
    """Schema for updating an alert"""
    max_price: Optional[float] = Field(None, gt=0)
    is_active: Optional[bool] = None
    check_frequency_hours: Optional[int] = Field(None, ge=1, le=168)


class AlertResponse(BaseModel):
    """Schema for alert response"""
    id: int
    user_id: str
    origin: str
    destination: str
    departure_date: Optional[datetime]
    return_date: Optional[datetime]
    max_price: float
    currency: str
    is_active: bool
    check_frequency_hours: int
    last_checked: Optional[datetime]
    last_price: Optional[float]
    created_at: datetime
    
    class Config:
        from_attributes = True


class PriceHistoryResponse(BaseModel):
    """Schema for price history response"""
    id: int
    alert_id: int
    price: float
    currency: str
    found_at: datetime
    
    class Config:
        from_attributes = True


class PriceCheckResponse(BaseModel):
    """Schema for price check result"""
    alert_id: int
    current_price: float
    previous_price: Optional[float]
    price_dropped: bool
    drop_percentage: Optional[float]
    currency: str
    flight_data: Optional[dict]


class HealthResponse(BaseModel):
    """Schema for health check response"""
    status: str
    database: str
    redis: str
    kiwi_api: str
