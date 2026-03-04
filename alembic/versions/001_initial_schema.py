"""Create canonical schema – users, alerts, price_snapshots,
notification_events, provider_quota_usage.

Revision ID: 001
Revises:
Create Date: 2026-03-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Enum type names used in PostgreSQL; for SQLite these are no-ops.
ALERT_STATUS = sa.Enum(
    "active", "paused", "triggered", "archived",
    name="alertstatus",
    create_type=False,
)
NOTIFICATION_STATUS = sa.Enum(
    "queued", "sent", "failed", "dead",
    name="notificationstatus",
    create_type=False,
)


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Create enum types (PostgreSQL only; SQLite ignores this).
    # ------------------------------------------------------------------
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(
            "active", "paused", "triggered", "archived",
            name="alertstatus",
        ).create(bind, checkfirst=True)
        sa.Enum(
            "queued", "sent", "failed", "dead",
            name="notificationstatus",
        ).create(bind, checkfirst=True)

    # ------------------------------------------------------------------
    # 1. users  (no FK dependencies)
    # ------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("telegram_chat_id", sa.String(), nullable=False),
        sa.Column("timezone", sa.String(), nullable=False, server_default="UTC"),
        sa.Column("locale", sa.String(), nullable=False, server_default="en"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_chat_id"),
    )

    # ------------------------------------------------------------------
    # 2. alerts  (FK → users)
    # ------------------------------------------------------------------
    op.create_table(
        "alerts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("origin_iata", sa.String(3), nullable=False),
        sa.Column("destination_iata", sa.String(3), nullable=False),
        sa.Column("depart_date_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("depart_date_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("max_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("check_interval_min", sa.Integer(), nullable=False, server_default="60"),
        sa.Column(
            "status",
            ALERT_STATUS if bind.dialect.name == "postgresql" else sa.String(),
            nullable=False,
            server_default="active",
        ),
        sa.Column("last_checked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("ix_alerts_user_id", "alerts", ["user_id"])

    # ------------------------------------------------------------------
    # 3. price_snapshots  (FK → alerts)
    # ------------------------------------------------------------------
    op.create_table(
        "price_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("alert_id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("itinerary_hash", sa.String(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column(
            "observed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"]),
    )
    op.create_index("ix_price_snapshots_alert_id", "price_snapshots", ["alert_id"])

    # ------------------------------------------------------------------
    # 4. notification_events  (FK → alerts, price_snapshots)
    # ------------------------------------------------------------------
    op.create_table(
        "notification_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("alert_id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column(
            "status",
            NOTIFICATION_STATUS if bind.dialect.name == "postgresql" else sa.String(),
            nullable=False,
            server_default="queued",
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["alert_id"], ["alerts.id"]),
        sa.ForeignKeyConstraint(["snapshot_id"], ["price_snapshots.id"]),
        sa.UniqueConstraint("idempotency_key"),
    )
    op.create_index("ix_notification_events_alert_id", "notification_events", ["alert_id"])

    # ------------------------------------------------------------------
    # 5. provider_quota_usage  (no FK dependencies)
    # ------------------------------------------------------------------
    op.create_table(
        "provider_quota_usage",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("provider", sa.String(), nullable=False),
        sa.Column("window_start", sa.DateTime(timezone=True), nullable=False),
        sa.Column("window_end", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requests_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requests_limit", sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    op.drop_table("provider_quota_usage")
    op.drop_table("notification_events")
    op.drop_table("price_snapshots")
    op.drop_table("alerts")
    op.drop_table("users")

    # Drop enum types on PostgreSQL.
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="notificationstatus").drop(bind, checkfirst=True)
        sa.Enum(name="alertstatus").drop(bind, checkfirst=True)
