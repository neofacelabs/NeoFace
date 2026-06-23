"""
NeoFace Database Configuration
Async SQLAlchemy 2.0 engine backed by Supabase PostgreSQL (asyncpg driver).

Features:
  - asyncpg connection pool with configurable size and overflow
  - Exponential backoff retry logic on engine creation and health checks
  - Pool health probe (pool_pre_ping) to discard stale connections
  - Explicit lifecycle helpers: init_db(), close_db(), check_db_health()
  - Compatible with Alembic async migrations via database_url_sync property
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy import MetaData, text
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings
from app.core.logging import logger

# ── Naming convention for Alembic auto-migrations ─────────────────────────────
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# ── Retry configuration ────────────────────────────────────────────────────────
_RETRY_ATTEMPTS: int = 5          # Maximum connection attempts
_RETRY_BASE_DELAY: float = 1.0    # Base delay in seconds (doubles each attempt)
_RETRY_MAX_DELAY: float = 30.0    # Cap on retry delay


class Base(DeclarativeBase):
    """
    Declarative base for all ORM models.
    All SQLAlchemy models must inherit from this class.
    The shared metadata carries naming conventions used by Alembic.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)

    def to_dict(self) -> dict[str, Any]:
        """Serialize a model instance to a plain dictionary (column values only)."""
        return {c.name: getattr(self, c.name) for c in self.__table__.columns}


# ── Engine factory ─────────────────────────────────────────────────────────────
def _build_engine() -> AsyncEngine:
    """
    Construct the async SQLAlchemy engine pointed at Supabase PostgreSQL.

    Pool settings explained:
      pool_size        — number of persistent connections kept alive
      max_overflow     — extra connections allowed above pool_size (transient)
      pool_pre_ping    — execute 'SELECT 1' before handing out a connection
                         to detect and discard stale/closed connections
      pool_recycle     — forcibly recycle connections after N seconds to avoid
                         hitting Supabase's idle connection timeout (~600 s)
      pool_timeout     — seconds to wait for a free connection before raising
      echo             — log all SQL statements in DEBUG mode only
    """
    db_url = settings.DATABASE_URL

    # asyncpg does NOT support the psycopg2-style ?sslmode= query parameter.
    # SSL is configured via connect_args["ssl"] below instead.
    # Strip all sslmode variants so asyncpg doesn't choke on them.
    db_url = db_url.replace("?sslmode=require", "").replace("&sslmode=require", "")
    db_url = db_url.replace("?sslmode=verify-full", "").replace("&sslmode=verify-full", "")
    db_url = db_url.replace("?sslmode=disable", "").replace("&sslmode=disable", "")

    is_supabase = "supabase.co" in db_url or "supabase.com" in db_url

    connect_args: dict[str, Any] = {
        # Supabase (both direct and pooler) require SSL; asyncpg uses this natively
        "ssl": "require" if is_supabase else "prefer",
        # Required when using PgBouncer / Supabase Pooler in transaction mode
        # (prepared statements are not supported across pooled connections)
        "statement_cache_size": 0,
    }

    engine = create_async_engine(
        db_url,
        pool_size=settings.DATABASE_POOL_SIZE,
        max_overflow=settings.DATABASE_MAX_OVERFLOW,
        pool_pre_ping=True,
        pool_recycle=300,        # 5 minutes — well within Supabase's idle timeout
        pool_timeout=30,         # Wait up to 30 s for a pool slot
        echo=settings.DEBUG,
        future=True,
        connect_args=connect_args,
    )
    return engine


# Module-level engine and session factory — lazily initialized on first use.
# Lazy init prevents import-time crashes during Alembic migrations, which only
# need Base.metadata and don't require an actual database connection.
_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def _get_engine() -> AsyncEngine:
    """Return the singleton async engine, creating it on first call."""
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def _get_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the singleton session factory, creating it on first call."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _session_factory


# Convenience module-level aliases — these are properties so they stay lazy
class _LazyEngine:
    """Descriptor that forwards attribute access to the real engine."""
    def __getattr__(self, name: str):
        return getattr(_get_engine(), name)
    def begin(self):
        return _get_engine().begin()
    async def dispose(self):
        return await _get_engine().dispose()


engine: AsyncEngine = _LazyEngine()  # type: ignore[assignment]


class AsyncSessionLocal:
    """Callable that returns an AsyncSession from the lazy session factory."""
    def __new__(cls, **kwargs):
        return _get_session_factory()(**kwargs)

    def __class_getitem__(cls, item):
        return _get_session_factory()


# ── FastAPI dependency ─────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields a transactional async database session.
    """
    async with _get_session_factory()() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Lifecycle helpers ─────────────────────────────────────────────────────────
async def init_db() -> None:
    """
    Create all tables on startup (development / first-run convenience).

    In production, Alembic migrations have already created the schema, so this
    function only ensures tables exist without dropping existing data.
    CREATE EXTENSION requires superuser — skipped when using Supabase pooler.
    """
    from app.core.config import settings as _s
    is_production = _s.ENVIRONMENT in ("production", "staging")

    async with _get_engine().begin() as conn:
        if not is_production:
            # Only attempt extension creation in dev (requires superuser)
            try:
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
                await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
            except Exception as e:
                logger.warning(f"database.init_db: could not create extensions (non-fatal): {e}")
        # checkfirst=True means it won't error if tables already exist
        await conn.run_sync(lambda c: Base.metadata.create_all(c, checkfirst=True))
    logger.info("database.init_db: schema verified")


async def close_db() -> None:
    """
    Dispose the connection pool on application shutdown.
    """
    await _get_engine().dispose()
    logger.info("database.close_db: connection pool disposed")


async def check_db_health() -> bool:
    """
    Lightweight health probe — verifies database connectivity.
    """
    try:
        async with _get_session_factory()() as session:
            await session.execute(text("SELECT 1"))
        return True
    except SQLAlchemyError as exc:
        logger.error("database.health_check: failed", error=str(exc))
        return False


async def wait_for_db(
    attempts: int = _RETRY_ATTEMPTS,
    base_delay: float = _RETRY_BASE_DELAY,
    max_delay: float = _RETRY_MAX_DELAY,
) -> None:
    """
    Block until the database is reachable, using exponential backoff.

    This is called during application startup to handle transient network
    delays when the service comes up before the database is ready (common
    in Docker Compose and cloud environments).

    Args:
        attempts:   Maximum number of connection attempts before raising.
        base_delay: Initial sleep between attempts in seconds.
        max_delay:  Maximum sleep cap between attempts in seconds.

    Raises:
        RuntimeError: If all attempts are exhausted without a successful ping.
    """
    delay = base_delay
    for attempt in range(1, attempts + 1):
        if await check_db_health():
            logger.info(
                "database.wait_for_db: connected",
                attempt=attempt,
            )
            return

        if attempt == attempts:
            raise RuntimeError(
                f"database.wait_for_db: could not reach database after "
                f"{attempts} attempts. Check DATABASE_URL and Supabase status."
            )

        logger.warning(
            "database.wait_for_db: connection failed, retrying",
            attempt=attempt,
            next_delay=delay,
        )
        await asyncio.sleep(delay)
        # Exponential backoff with jitter cap
        delay = min(delay * 2, max_delay)
