"""Tests for migration 002 – audit_events schema."""
import os

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


PROJECT_ROOT = os.path.realpath(os.path.join(os.path.dirname(__file__), "..", ".."))
ALEMBIC_INI = os.path.join(PROJECT_ROOT, "alembic.ini")


def _alembic_config(db_url: str) -> Config:
    cfg = Config(ALEMBIC_INI)
    cfg.set_main_option("sqlalchemy.url", db_url)
    cfg.set_main_option("script_location", os.path.join(PROJECT_ROOT, "alembic"))
    return cfg


def _make_engine(tmp_path):
    db_path = os.path.join(str(tmp_path), "test.db")
    url = f"sqlite:///{db_path}"
    return create_engine(url), url


def test_upgrade_002_creates_expected_columns(tmp_path):
    engine, url = _make_engine(tmp_path)
    cfg = _alembic_config(url)
    command.upgrade(cfg, "002")

    inspector = inspect(engine)
    cols = {c["name"] for c in inspector.get_columns("audit_events")}
    expected = {
        "id",
        "actor_id",
        "actor_type",
        "action",
        "entity_type",
        "entity_id",
        "old_state",
        "new_state",
        "metadata",
        "created_at",
    }
    assert cols == expected


def test_upgrade_002_creates_indexes(tmp_path):
    engine, url = _make_engine(tmp_path)
    cfg = _alembic_config(url)
    command.upgrade(cfg, "002")

    inspector = inspect(engine)
    indexes = {idx["name"] for idx in inspector.get_indexes("audit_events")}
    assert "ix_audit_events_entity" in indexes
    assert "ix_audit_events_actor_id" in indexes
    assert "ix_audit_events_action" in indexes
    assert "ix_audit_events_created_at" in indexes
