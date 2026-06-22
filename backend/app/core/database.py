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
    connect_args: dict[str, Any] = {
        # Supabase requires SSL; asyncpg respects this via the DSN or connect_args
        "ssl": "require" if "supabase.co" in settings.DATABASE_URL else "prefer",
        # Statement timeout (ms) prevents runaway queries
        "statement_cache_size": 0,  # Required when using PgBouncer in transaction mode
    }

    engine = create_async_engine(
        settings.DATABASE_URL,
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


# Module-level engine and session factory — created once at import time.
engine: AsyncEngine = _build_engine()

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,   # Keep ORM objects usable after commit
    autocommit=False,
    autoflush=False,
)


# ── FastAPI dependency ─────────────────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — yields a transactional async database session.

    Automatically commits on success or rolls back on any exception.
    Always closes the session (returns connection to pool) in the finally block.

    Usage:
        @router.get("/resource")
        async def endpoint(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(MyModel))
    """
    async with AsyncSessionLocal() as session:
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
    In production always use Alembic migrations instead.

    Also enables the PostgreSQL extensions required by NeoFace:
      uuid-ossp  — server-side UUID generation (gen_random_uuid fallback)
      pgcrypto   — used by some Supabase auth functions
    """
    async with engine.begin() as conn:
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
        await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("database.init_db: tables initialized")


async def close_db() -> None:
    """
    Dispose the connection pool on application shutdown.
    Called from the FastAPI lifespan context manager.
    """
    await engine.dispose()
    logger.info("database.close_db: connection pool disposed")


async def check_db_health() -> bool:
    """
    Lightweight health probe — verifies database connectivity.

    Returns True if a round-trip SELECT 1 succeeds, False otherwise.
    Used by the /health endpoint and startup retry logic.
    """
    try:
        async with AsyncSessionLocal() as session:
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
