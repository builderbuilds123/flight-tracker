"""Tests for migration 001 – canonical schema creation.

Validates:
  - upgrade creates all 5 tables with correct columns
  - foreign key constraints exist
  - unique constraints exist
  - downgrade removes all tables cleanly
  - full upgrade → downgrade → upgrade cycle is idempotent
"""
import os
import uuid
from datetime import datetime, timezone

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
ALEMBIC_INI = os.path.join(PROJECT_ROOT, "alembic.ini")


def _alembic_config(db_url: str) -> Config:
    """Build an Alembic Config pointing at a specific database URL."""
    cfg = Config(ALEMBIC_INI)
    cfg.set_main_option("sqlalchemy.url", db_url)
    cfg.set_main_option("script_location", os.path.join(PROJECT_ROOT, "alembic"))
    return cfg


def _make_engine(tmp_path):
    """Create a SQLite engine in a temporary directory."""
    db_path = os.path.join(str(tmp_path), "test.db")
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    return engine, url


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture()
def migration_env(tmp_path):
    """Provide a fresh SQLite database with Alembic config."""
    engine, url = _make_engine(tmp_path)
    cfg = _alembic_config(url)
    return engine, cfg


# ---------------------------------------------------------------------------
# Tests – Upgrade
# ---------------------------------------------------------------------------
class TestUpgrade001:
    """Verify that 'alembic upgrade 001' creates the expected schema."""

    def test_upgrade_creates_all_tables(self, migration_env):
        engine, cfg = migration_env
        command.upgrade(cfg, "001")

        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        expected = {"users", "alerts", "price_snapshots", "notification_events", "provider_quota_usage"}
        assert expected.issubset(tables), f"Missing tables: {expected - tables}"

    def test_users_columns(self, migration_env):
        engine, cfg = migration_env
        command.upgrade(cfg, "001")

        inspector = inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("users")}
        expected = {"id", "telegram_chat_id", "timezone", "locale", "created_at"}
        assert expected == cols

    def test_alerts_columns(self, migration_env):
        engine, cfg = migration_env
        command.upgrade(cfg, "001")

        inspector = inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("alerts")}
        expected = {
            "id", "user_id", "origin_iata", "destination_iata",
            "depart_date_start", "depart_date_end", "max_price", "currency",
            "check_interval_min", "status", "last_checked_at",
            "created_at", "updated_at",
        }
        assert expected == cols

    def test_price_snapshots_columns(self, migration_env):
        engine, cfg = migration_env
        command.upgrade(cfg, "001")

        inspector = inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("price_snapshots")}
        expected = {
            "id", "alert_id", "provider", "price", "currency",
            "itinerary_hash", "raw_payload", "observed_at",
        }
        assert expected == cols

    def test_notification_events_columns(self, migration_env):
        engine, cfg = migration_env
        command.upgrade(cfg, "001")

        inspector = inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("notification_events")}
        expected = {
            "id", "alert_id", "snapshot_id", "channel", "idempotency_key",
            "status", "attempt_count", "last_error", "sent_at", "created_at",
        }
        assert expected == cols

    def test_provider_quota_usage_columns(self, migration_env):
        engine, cfg = migration_env
        command.upgrade(cfg, "001")

        inspector = inspect(engine)
        cols = {c["name"] for c in inspector.get_columns("provider_quota_usage")}
        expected = {
            "id", "provider", "window_start", "window_end",
            "requests_used", "requests_limit",
        }
        assert expected == cols

    def test_users_unique_telegram_chat_id(self, migration_env):
        """telegram_chat_id must have a unique constraint."""
        engine, cfg = migration_env
        command.upgrade(cfg, "001")

        inspector = inspect(engine)
        uniques = inspector.get_unique_constraints("users")
        unique_cols = {frozenset(u["column_names"]) for u in uniques}
        assert frozenset({"telegram_chat_id"}) in unique_cols

    def test_notification_events_unique_idempotency_key(self, migration_env):
        """idempotency_key must have a unique constraint."""
        engine, cfg = migration_env
        command.upgrade(cfg, "001")

        inspector = inspect(engine)
        uniques = inspector.get_unique_constraints("notification_events")
        unique_cols = {frozenset(u["column_names"]) for u in uniques}
        assert frozenset({"idempotency_key"}) in unique_cols

    def test_alerts_fk_to_users(self, migration_env):
        engine, cfg = migration_env
        command.upgrade(cfg, "001")

        inspector = inspect(engine)
        fks = inspector.get_foreign_keys("alerts")
        referred_tables = {fk["referred_table"] for fk in fks}
        assert "users" in referred_tables

    def test_price_snapshots_fk_to_alerts(self, migration_env):
        engine, cfg = migration_env
        command.upgrade(cfg, "001")

        inspector = inspect(engine)
        fks = inspector.get_foreign_keys("price_snapshots")
        referred_tables = {fk["referred_table"] for fk in fks}
        assert "alerts" in referred_tables

    def test_notification_events_fks(self, migration_env):
        engine, cfg = migration_env
        command.upgrade(cfg, "001")

        inspector = inspect(engine)
        fks = inspector.get_foreign_keys("notification_events")
        referred_tables = {fk["referred_table"] for fk in fks}
        assert {"alerts", "price_snapshots"} == referred_tables

    def test_fk_enforcement_alerts_requires_user(self, migration_env):
        """Inserting an alert with a non-existent user_id must fail."""
        engine, cfg = migration_env
        command.upgrade(cfg, "001")

        with engine.connect() as conn:
            # Enable FK enforcement for SQLite.
            conn.execute(text("PRAGMA foreign_keys = ON"))

            fake_uid = str(uuid.uuid4())
            fake_aid = str(uuid.uuid4())
            with pytest.raises(Exception):
                conn.execute(
                    text(
                        "INSERT INTO alerts (id, user_id, origin_iata, destination_iata, "
                        "depart_date_start, depart_date_end, max_price, currency, "
                        "check_interval_min, status, created_at, updated_at) "
                        "VALUES (:id, :uid, 'JFK', 'LAX', :d, :d, 100, 'USD', "
                        "60, 'active', :d, :d)"
                    ),
                    {"id": fake_aid, "uid": fake_uid, "d": datetime.now(timezone.utc).isoformat()},
                )
                conn.commit()


# ---------------------------------------------------------------------------
# Tests – Downgrade
# ---------------------------------------------------------------------------
class TestDowngrade001:
    """Verify that downgrade from 001 removes all tables."""

    def test_downgrade_removes_all_tables(self, migration_env):
        engine, cfg = migration_env
        command.upgrade(cfg, "001")
        command.downgrade(cfg, "base")

        inspector = inspect(engine)
        tables = set(inspector.get_table_names()) - {"alembic_version"}
        assert tables == set(), f"Tables remain after downgrade: {tables}"


# ---------------------------------------------------------------------------
# Tests – Round-trip
# ---------------------------------------------------------------------------
class TestRoundTrip:
    """Verify upgrade → downgrade → upgrade idempotency."""

    def test_upgrade_downgrade_upgrade_is_idempotent(self, migration_env):
        engine, cfg = migration_env

        command.upgrade(cfg, "001")
        command.downgrade(cfg, "base")
        command.upgrade(cfg, "001")

        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        expected = {"users", "alerts", "price_snapshots", "notification_events", "provider_quota_usage"}
        assert expected.issubset(tables)

    def test_upgrade_head_from_empty_db(self, migration_env):
        """'alembic upgrade head' must work from an empty database."""
        engine, cfg = migration_env
        command.upgrade(cfg, "head")

        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        expected = {"users", "alerts", "price_snapshots", "notification_events", "provider_quota_usage"}
        assert expected.issubset(tables)

    def test_downgrade_base_from_head(self, migration_env):
        """'alembic downgrade base' must leave no application tables."""
        engine, cfg = migration_env
        command.upgrade(cfg, "head")
        command.downgrade(cfg, "base")

        inspector = inspect(engine)
        tables = set(inspector.get_table_names()) - {"alembic_version"}
        assert tables == set()
