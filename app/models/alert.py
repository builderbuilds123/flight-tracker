"""
Alert and Notification Models
"""
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class AlertStatus(enum.Enum):
    """Alert status enumeration"""
    ACTIVE = "active"
    TRIGGERED = "triggered"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class Alert(Base):
    """Price alert created by users"""
    __tablename__ = "alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Route information
    origin_airport = Column(String(3), nullable=False, index=True)
    destination_airport = Column(String(3), nullable=False, index=True)
    
    # Alert criteria
    target_price = Column(Float, nullable=False)
    currency = Column(String(3), default="USD")
    
    # Travel dates
    departure_date_start = Column(DateTime, nullable=True)
    departure_date_end = Column(DateTime, nullable=True)
    
    # Status
    status = Column(String(20), default=AlertStatus.ACTIVE.value, index=True)
    is_active = Column(Boolean, default=True, index=True)
    
    # User information (optional - can be anonymous)
    user_email = Column(String(255), nullable=True, index=True)
    user_id = Column(String(100), nullable=True)  # For authenticated users
    
    # Notification preferences
    notify_email = Column(Boolean, default=True)
    notify_push = Column(Boolean, default=False)
    
    # Tracking
    triggered_at = Column(DateTime, nullable=True)
    triggered_price = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    
    # Relationships
    notifications = relationship("UserNotification", back_populates="alert", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Alert {self.origin_airport}->{self.destination_airport} target={self.target_price}>"


class UserNotification(Base):
    """Notification sent to users"""
    __tablename__ = "user_notifications"
    
    id = Column(Integer, primary_key=True, index=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False, index=True)
    
    # Notification type
    notification_type = Column(String(50), default="price_drop")  # price_drop, digest, etc.
    
    # Content
    subject = Column(String(255), nullable=True)
    message = Column(String(2000), nullable=True)
    
    # Delivery status
    sent = Column(Boolean, default=False, index=True)
    sent_at = Column(DateTime, nullable=True)
    delivered = Column(Boolean, default=False)
    delivered_at = Column(DateTime, nullable=True)
    read = Column(Boolean, default=False)
    read_at = Column(DateTime, nullable=True)
    
    # Delivery method
    channel = Column(String(20), default="email")  # email, push, sms
    
    # Error tracking
    error_message = Column(String(500), nullable=True)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationships
    alert = relationship("Alert", back_populates="notifications")
    
    def __repr__(self):
        return f"<Notification alert={self.alert_id} type={self.notification_type} sent={self.sent}>"
