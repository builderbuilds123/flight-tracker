"""Audit event ORM model."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Enum, Index, String, Uuid
from sqlalchemy.dialects.postgresql import JSON, JSONB

from src.domain.enums import ActorType, AuditAction
from src.infrastructure.db.models.base import Base


class AuditEventORM(Base):
    __tablename__ = "audit_events"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    actor_id = Column(Uuid, nullable=True)
    actor_type = Column(
        Enum(ActorType, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    action = Column(
        Enum(AuditAction, values_callable=lambda e: [m.value for m in e]),
        nullable=False,
    )
    entity_type = Column(String, nullable=False)
    entity_id = Column(Uuid, nullable=False)
    old_state = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    new_state = Column(JSON().with_variant(JSONB(), "postgresql"), nullable=True)
    metadata_ = Column(
        "metadata",
        JSON().with_variant(JSONB(), "postgresql"),
        key="metadata",
        nullable=False,
        default=dict,
    )
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_audit_events_entity", "entity_type", "entity_id"),
        Index("ix_audit_events_actor_id", "actor_id"),
        Index("ix_audit_events_action", "action"),
        Index("ix_audit_events_created_at", "created_at"),
    )

    status_enum = None
