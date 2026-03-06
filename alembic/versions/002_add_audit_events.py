"""Add audit_events table for immutable mutation auditing.

Revision ID: 002
Revises: 001
Create Date: 2026-03-06
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    actor_type = sa.Enum("user", "system", "api_key", name="actortype")
    action_type = sa.Enum(
        "ALERT_CREATED",
        "ALERT_UPDATED",
        "ALERT_PAUSED",
        "ALERT_RESUMED",
        "ALERT_ARCHIVED",
        "NOTIFICATION_SENT",
        "NOTIFICATION_FAILED",
        name="auditaction",
    )

    if bind.dialect.name == "postgresql":
        actor_type.create(bind, checkfirst=True)
        action_type.create(bind, checkfirst=True)
        from sqlalchemy.dialects.postgresql import JSONB

        json_type = JSONB()
        actor_col_type = actor_type
        action_col_type = action_type
    else:
        json_type = sa.JSON()
        actor_col_type = sa.String()
        action_col_type = sa.String()

    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("actor_type", actor_col_type, nullable=False),
        sa.Column("action", action_col_type, nullable=False),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=False),
        sa.Column("old_state", json_type, nullable=True),
        sa.Column("new_state", json_type, nullable=True),
        sa.Column("metadata", json_type, nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("(CURRENT_TIMESTAMP)")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index("ix_audit_events_entity", "audit_events", ["entity_type", "entity_id"])
    op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_events_created_at", table_name="audit_events")
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_id", table_name="audit_events")
    op.drop_index("ix_audit_events_entity", table_name="audit_events")
    op.drop_table("audit_events")

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="auditaction").drop(bind, checkfirst=True)
        sa.Enum(name="actortype").drop(bind, checkfirst=True)
