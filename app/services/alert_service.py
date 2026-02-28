"""Alert service for database operations on flight alerts."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from typing import Optional, List
from datetime import datetime
import enum

from app.core.database import Base


class AlertStatus(enum.Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    TRIGGERED = "triggered"
    EXPIRED = "expired"


class FlightAlert(Base):
    """Flight price alert model for Telegram users."""
    __tablename__ = "flight_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("telegram_users.id"), nullable=False)
    
    origin_airport = Column(String(3), nullable=False)
    destination_airport = Column(String(3), nullable=False)
    origin_city = Column(String(100), nullable=True)
    destination_city = Column(String(100), nullable=True)
    
    departure_date = Column(DateTime, nullable=True)
    return_date = Column(DateTime, nullable=True)
    is_flexible_dates = Column(Boolean, default=False)
    flexible_days = Column(Integer, default=3)
    is_one_way = Column(Boolean, default=False)
    
    target_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    last_checked_price = Column(Float, nullable=True)
    lowest_price_found = Column(Float, nullable=True)
    currency = Column(String(3), default="USD")
    
    status = Column(SQLEnum(AlertStatus), default=AlertStatus.ACTIVE)
    
    last_checked_at = Column(DateTime, nullable=True)
    last_notified_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="alerts")
    
    def is_price_drop(self) -> bool:
        if self.current_price is None or self.last_checked_price is None:
            return False
        return self.current_price < self.last_checked_price
    
    def get_price_difference(self) -> Optional[float]:
        if self.current_price is None or self.last_checked_price is None:
            return None
        return self.last_checked_price - self.current_price


# Add alerts relationship to User
from app.services.user_service import User
User.alerts = relationship("FlightAlert", back_populates="user", cascade="all, delete-orphan")


class AlertService:
    """Service for flight alert-related database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_alert(self, user_id: int, origin_airport: str, destination_airport: str, target_price: float,
                          origin_city: str = None, destination_city: str = None, departure_date: datetime = None,
                          return_date: datetime = None, is_flexible_dates: bool = False, flexible_days: int = 3,
                          currency: str = "USD", is_one_way: bool = False) -> FlightAlert:
        """Create a new flight alert."""
        alert = FlightAlert(
            user_id=user_id,
            origin_airport=origin_airport.upper()[:3],
            destination_airport=destination_airport.upper()[:3],
            origin_city=origin_city,
            destination_city=destination_city,
            departure_date=departure_date,
            return_date=return_date,
            is_flexible_dates=is_flexible_dates,
            flexible_days=flexible_days,
            target_price=target_price,
            currency=currency,
            is_one_way=is_one_way,
        )
        self.session.add(alert)
        await self.session.flush()
        return alert
    
    async def get_alert(self, alert_id: int, user_id: int) -> Optional[FlightAlert]:
        """Get a specific alert by ID for a user."""
        result = await self.session.execute(select(FlightAlert).where(FlightAlert.id == alert_id, FlightAlert.user_id == user_id))
        return result.scalar_one_or_none()
    
    async def get_user_alerts(self, user_id: int, status: AlertStatus = None) -> List[FlightAlert]:
        """Get all alerts for a user."""
        query = select(FlightAlert).where(FlightAlert.user_id == user_id).order_by(FlightAlert.created_at.desc())
        if status:
            query = query.where(FlightAlert.status == status)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_alert_status(self, alert_id: int, user_id: int, status: AlertStatus) -> Optional[FlightAlert]:
        """Update alert status."""
        alert = await self.get_alert(alert_id, user_id)
        if alert:
            alert.status = status
            alert.updated_at = datetime.utcnow()
            await self.session.flush()
        return alert
    
    async def pause_alert(self, alert_id: int, user_id: int) -> Optional[FlightAlert]:
        """Pause an alert."""
        return await self.update_alert_status(alert_id, user_id, AlertStatus.PAUSED)
    
    async def resume_alert(self, alert_id: int, user_id: int) -> Optional[FlightAlert]:
        """Resume a paused alert."""
        return await self.update_alert_status(alert_id, user_id, AlertStatus.ACTIVE)
    
    async def delete_alert(self, alert_id: int, user_id: int) -> bool:
        """Delete an alert."""
        alert = await self.get_alert(alert_id, user_id)
        if alert:
            await self.session.delete(alert)
            await self.session.flush()
            return True
        return False
    
    async def get_alert_count(self, user_id: int) -> int:
        """Get count of alerts for a user."""
        from sqlalchemy import func
        result = await self.session.execute(select(func.count(FlightAlert.id)).where(FlightAlert.user_id == user_id))
        return result.scalar() or 0
