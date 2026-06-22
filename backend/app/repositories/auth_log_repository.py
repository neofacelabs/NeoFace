"""
NeoFace Auth Log Repository
Data access layer for authentication event logs.
Provides analytics aggregations for the dashboard.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, case, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_log import AuthLog


class AuthLogRepository:
    """Repository for authentication log operations."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Write ─────────────────────────────────────────────────────────────────

    async def create(
        self,
        authentication_result: bool,
        user_id: uuid.UUID | None = None,
        confidence_score: float | None = None,
        liveness_score: float | None = None,
        failure_reason: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuthLog:
        """Append a new authentication event to the audit trail."""
        log = AuthLog(
            user_id=user_id,
            confidence_score=confidence_score,
            liveness_score=liveness_score,
            authentication_result=authentication_result,
            failure_reason=failure_reason,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        self.db.add(log)
        await self.db.flush()
        await self.db.refresh(log)
        return log

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_recent(
        self,
        page: int = 1,
        page_size: int = 50,
        user_id: uuid.UUID | None = None,
    ) -> tuple[list[AuthLog], int]:
        """
        Paginated recent logs, optionally filtered by user.
        Returns (logs, total_count).
        """
        query = select(AuthLog)
        count_query = select(func.count(AuthLog.id))

        if user_id:
            query = query.where(AuthLog.user_id == user_id)
            count_query = count_query.where(AuthLog.user_id == user_id)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        offset = (page - 1) * page_size
        result = await self.db.execute(
            query.order_by(AuthLog.timestamp.desc())
            .offset(offset)
            .limit(page_size)
        )
        return list(result.scalars().all()), total

    # ── Analytics ─────────────────────────────────────────────────────────────

    async def count_total(self) -> int:
        result = await self.db.execute(select(func.count(AuthLog.id)))
        return result.scalar_one()

    async def count_successful(self) -> int:
        result = await self.db.execute(
            select(func.count(AuthLog.id)).where(
                AuthLog.authentication_result == True  # noqa: E712
            )
        )
        return result.scalar_one()

    async def get_success_rate(self) -> float:
        """Returns success percentage (0.0–100.0)."""
        total = await self.count_total()
        if total == 0:
            return 0.0
        successful = await self.count_successful()
        return round((successful / total) * 100, 2)

    async def get_daily_stats(self, days: int = 7) -> list[dict]:
        """
        Returns daily enrollment/verification counts for the last N days.
        Used by the dashboard analytics chart.
        """
        since = datetime.now(timezone.utc) - timedelta(days=days)

        result = await self.db.execute(
            select(
                cast(AuthLog.timestamp, type_=AuthLog.timestamp.type).label("date"),
                func.count(AuthLog.id).label("total"),
                func.sum(
                    case((AuthLog.authentication_result == True, 1), else_=0)  # noqa: E712
                ).label("successful"),
            )
            .where(AuthLog.timestamp >= since)
            .group_by(func.date(AuthLog.timestamp))
            .order_by(func.date(AuthLog.timestamp))
        )
        rows = result.fetchall()
        return [
            {
                "date": str(row.date)[:10],
                "total": row.total,
                "successful": int(row.successful or 0),
            }
            for row in rows
        ]

    async def delete_older_than(self, days: int = 90) -> int:
        """
        Cleanup job: delete logs older than N days.
        Called by the Celery cleanup task.
        Returns number of deleted records.
        """
        from sqlalchemy import delete

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.db.execute(
            delete(AuthLog).where(AuthLog.timestamp < cutoff)
        )
        return result.rowcount
