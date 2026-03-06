"""Core ORM models excluding audit events."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.orm import relationship

from src.domain.enums import AlertStatus, NotificationStatus
from src.infrastructure.db.models.base import Base


class UserORM(Base):
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    telegram_chat_id = Column(String, nullable=False, unique=True)
    timezone = Column(String, nullable=False, default="UTC")
    locale = Column(String, nullable=False, default="en")
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    alerts = relationship("AlertORM", back_populates="user")

    status_enum = None


class AlertORM(Base):
    __tablename__ = "alerts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(Uuid, ForeignKey("users.id"), nullable=False)
    origin_iata = Column(String(3), nullable=False)
    destination_iata = Column(String(3), nullable=False)
    depart_date_start = Column(DateTime(timezone=True), nullable=False)
    depart_date_end = Column(DateTime(timezone=True), nullable=False)
    max_price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False, default="USD")
    check_interval_min = Column(Integer, nullable=False, default=60)
    status = Column(
        Enum(AlertStatus, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=AlertStatus.ACTIVE,
    )
    last_checked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    user = relationship("UserORM", back_populates="alerts")
    price_snapshots = relationship("PriceSnapshotORM", back_populates="alert")
    notification_events = relationship("NotificationEventORM", back_populates="alert")

    status_enum = AlertStatus


class PriceSnapshotORM(Base):
    __tablename__ = "price_snapshots"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    alert_id = Column(Uuid, ForeignKey("alerts.id"), nullable=False)
    provider = Column(String, nullable=False)
    price = Column(Numeric(10, 2), nullable=False)
    currency = Column(String(3), nullable=False)
    itinerary_hash = Column(String, nullable=True)
    raw_payload = Column(JSON, nullable=True)
    observed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    alert = relationship("AlertORM", back_populates="price_snapshots")
    notification_events = relationship("NotificationEventORM", back_populates="snapshot")

    status_enum = None


class NotificationEventORM(Base):
    __tablename__ = "notification_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    alert_id = Column(Uuid, ForeignKey("alerts.id"), nullable=False)
    snapshot_id = Column(Uuid, ForeignKey("price_snapshots.id"), nullable=False)
    channel = Column(String, nullable=False)
    idempotency_key = Column(String, nullable=False, unique=True)
    status = Column(
        Enum(NotificationStatus, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
        default=NotificationStatus.QUEUED,
    )
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    sent_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    alert = relationship("AlertORM", back_populates="notification_events")
    snapshot = relationship("PriceSnapshotORM", back_populates="notification_events")

    status_enum = NotificationStatus


class ProviderQuotaUsageORM(Base):
    __tablename__ = "provider_quota_usage"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    provider = Column(String, nullable=False)
    window_start = Column(DateTime(timezone=True), nullable=False)
    window_end = Column(DateTime(timezone=True), nullable=False)
    requests_used = Column(Integer, nullable=False, default=0)
    requests_limit = Column(Integer, nullable=False)

    status_enum = None
