"""Add audit_events table for S6-05.

Revision ID: 002
Revises: 001
Create Date: 2026-03-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ACTOR_TYPE = sa.Enum(
    "user", "system", "api_key",
    name="actortype",
    create_type=False,
)
AUDIT_ACTION = sa.Enum(
    "ALERT_CREATED", "ALERT_UPDATED", "ALERT_PAUSED", "ALERT_RESUMED",
    "ALERT_ARCHIVED", "NOTIFICATION_SENT", "NOTIFICATION_FAILED",
    name="auditaction",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()

    # Create enum types for PostgreSQL.
    if bind.dialect.name == "postgresql":
        sa.Enum(
            "user", "system", "api_key",
            name="actortype",
        ).create(bind, checkfirst=True)
        sa.Enum(
            "ALERT_CREATED", "ALERT_UPDATED", "ALERT_PAUSED", "ALERT_RESUMED",
            "ALERT_ARCHIVED", "NOTIFICATION_SENT", "NOTIFICATION_FAILED",
            name="auditaction",
        ).create(bind, checkfirst=True)

    # Use JSONB on PostgreSQL, JSON on SQLite.
    json_type = sa.JSON()
    if bind.dialect.name == "postgresql":
        from sqlalchemy.dialects.postgresql import JSONB
        json_type = JSONB()

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column(
            "actor_type",
            ACTOR_TYPE if bind.dialect.name == "postgresql" else sa.String(),
            nullable=False,
        ),
        sa.Column(
            "action",
            AUDIT_ACTION if bind.dialect.name == "postgresql" else sa.String(),
            nullable=False,
        ),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.String(), nullable=False),
        sa.Column("prior_state", json_type, nullable=True),
        sa.Column("new_state", json_type, nullable=True),
        sa.Column("redacted_fields", json_type, nullable=False, server_default="[]"),
        sa.Column("trace_id", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_entity", "audit_events", ["entity_type", "entity_id"])
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("audit_events")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="auditaction").drop(bind, checkfirst=True)
        sa.Enum(name="actortype").drop(bind, checkfirst=True)
