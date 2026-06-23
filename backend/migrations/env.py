"""
Alembic Migration Environment
Configured for async SQLAlchemy with auto-migration support.
"""

import os
import sys

# ── CRITICAL: Ensure /app is on sys.path BEFORE any app.* imports ────────────
# We do this unconditionally because alembic's prepend_sys_path ini setting
# fires AFTER env.py starts loading, which is too late.
# The container WORKDIR is /app and all source lives there.
if "/app" not in sys.path:
    sys.path.insert(0, "/app")

# Also insert anything from PYTHONPATH to handle non-Docker invocations
for _p in os.environ.get("PYTHONPATH", "").split(os.pathsep):
    if _p and _p not in sys.path:
        sys.path.insert(0, _p)

from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.core.database import Base

# Import all models so Alembic can detect changes
from app.models import *  # noqa: F401, F403

config = context.config

# Override URL from application settings
# Alembic migrations must use the synchronous psycopg2 driver.
# The app uses asyncpg (+asyncpg), so we swap it out here.
db_url = settings.DATABASE_URL
# Swap async driver variants to psycopg2
db_url = db_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
db_url = db_url.replace("postgresql+aiopg://", "postgresql+psycopg2://")
# Escape % for ConfigParser interpolation
safe_url = db_url.replace("%", "%%")
config.set_main_option("sqlalchemy.url", safe_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in offline mode (generates SQL without connecting)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using async engine."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations using synchronous (psycopg2) engine."""
    from sqlalchemy import create_engine
    url = config.get_main_option("sqlalchemy.url")
    connectable = create_engine(url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
