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

# Import all models so Alembic can detect table changes.
# Wrap in a try/except so the REAL error (not "No module named app.models")
# is printed if any sub-import fails.
try:
    from app.models import *  # noqa: F401, F403
except Exception as _model_import_err:
    import traceback
    print("=" * 72, file=sys.stderr)
    print("[alembic/env.py] FATAL: failed to import app.models", file=sys.stderr)
    print("Real cause:", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)
    print("=" * 72, file=sys.stderr)
    raise

config = context.config

# ── Build the synchronous migration URL ───────────────────────────────────────
# Read DATABASE_URL DIRECTLY from os.environ to bypass any pydantic-settings
# caching / ordering issue. Falls back to settings as a last resort.
_raw_url = (
    os.environ.get("DATABASE_URL")
    or os.environ.get("database_url")
    or settings.DATABASE_URL
)

# Fail fast with a clear message instead of silently using localhost
if "localhost" in _raw_url or "127.0.0.1" in _raw_url:
    _host = _raw_url.split("@")[-1].split("/")[0] if "@" in _raw_url else _raw_url
    print(
        f"\n[alembic/env.py] ERROR: DATABASE_URL resolves to '{_host}'.\n"
        "The DATABASE_URL environment variable is not set or is using the\n"
        "development default. Set DATABASE_URL in Render → Environment Variables\n"
        "to your Supabase connection string before running migrations.\n",
        file=sys.stderr,
    )
    sys.exit(1)

# Swap async driver → sync psycopg2 for Alembic
db_url = _raw_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
db_url = db_url.replace("postgresql+aiopg://", "postgresql+psycopg2://")
db_url = db_url.replace("postgres://", "postgresql+psycopg2://")  # Heroku-style

# Escape % for ConfigParser interpolation (ConfigParser uses %% → %)
safe_url = db_url.replace("%", "%%")
config.set_main_option("sqlalchemy.url", safe_url)

# Log the host we're connecting to (never log passwords)
_db_host = db_url.split("@")[-1].split("/")[0] if "@" in db_url else "unknown"
print(f"[alembic/env.py] Connecting to DB host: {_db_host}", file=sys.stderr)

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
