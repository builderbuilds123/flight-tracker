"""User service for database operations."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, Column, Integer, String, Boolean, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from typing import Optional
from datetime import datetime
import enum

from app.core.database import Base


class NotificationFrequency(enum.Enum):
    INSTANT = "instant"
    DAILY = "daily"
    WEEKLY = "weekly"


class User(Base):
    """Telegram user model."""
    __tablename__ = "telegram_users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, index=True, nullable=False)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    language_code = Column(String(10), default="en")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    preferences = relationship("UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan")


class UserPreference(Base):
    """User preferences model."""
    __tablename__ = "user_preferences"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("telegram_users.id"), unique=True, nullable=False)
    currency = Column(String(3), default="USD")
    timezone = Column(String(50), default="UTC")
    notification_frequency = Column(String(20), default="daily")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="preferences")


class UserService:
    """Service for user-related database operations."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def get_or_create_user(self, telegram_id: int, username: str = None, first_name: str = None, last_name: str = None, language_code: str = "en") -> User:
        """Get existing user or create a new one."""
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        user = result.scalar_one_or_none()
        
        if not user:
            user = User(telegram_id=telegram_id, username=username, first_name=first_name, last_name=last_name, language_code=language_code)
            self.session.add(user)
            await self.session.flush()
            
            pref = UserPreference(user_id=user.id)
            self.session.add(pref)
        else:
            if username:
                user.username = username
            if first_name:
                user.first_name = first_name
            if last_name:
                user.last_name = last_name
            user.updated_at = datetime.utcnow()
        
        return user
    
    async def get_user_preferences(self, telegram_id: int) -> Optional[UserPreference]:
        """Get user preferences."""
        result = await self.session.execute(select(UserPreference).join(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()
    
    async def update_preferences(self, telegram_id: int, currency: str = None, timezone: str = None, notification_frequency: NotificationFrequency = None) -> Optional[UserPreference]:
        """Update user preferences."""
        preferences = await self.get_user_preferences(telegram_id)
        if not preferences:
            return None
        
        if currency:
            preferences.currency = currency
        if timezone:
            preferences.timezone = timezone
        if notification_frequency:
            preferences.notification_frequency = notification_frequency.value
        
        preferences.updated_at = datetime.utcnow()
        await self.session.flush()
        return preferences
