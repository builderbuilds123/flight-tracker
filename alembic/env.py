"""Alembic environment configuration.

Points at the canonical ORM models in src.infrastructure.db.models
so that autogenerate and migrations track the single source of truth.
"""
import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context

# Ensure project root is on sys.path so src.* imports resolve.
sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), "..")))

# Canonical ORM models – this import registers all tables with Base.metadata.
from src.infrastructure.db.models import (  # noqa: F401, E402
    Base,
    UserORM,
    AlertORM,
    PriceSnapshotORM,
    NotificationEventORM,
    ProviderQuotaUsageORM,
    AuditEventORM,
)

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Allow DATABASE_URL env var to override alembic.ini for default runtime config,
# but do not clobber explicit per-test URLs set by test fixtures.
url_override = os.environ.get("DATABASE_URL")
configured_url = config.get_main_option("sqlalchemy.url")
default_ini_url = "postgresql://postgres:postgres@db:5432/flight_tracker"
if url_override and (not configured_url or configured_url == default_ini_url):
    config.set_main_option("sqlalchemy.url", url_override)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
