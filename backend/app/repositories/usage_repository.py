"""
NeoFace AaaS — Usage Repository
UPSERT-based daily aggregation + analytics queries.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage_record import UsageRecord
from app.models.auth_session import AuthenticationSession


class UsageRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def upsert_increment(
        self,
        org_id: uuid.UUID,
        endpoint: str,
        success: bool,
        latency_ms: float,
        app_id: uuid.UUID | None = None,
    ) -> None:
        """
        Upsert a usage record for the current UTC day.
        Atomically increments counts using PostgreSQL ON CONFLICT DO UPDATE.
        """
        today = datetime.now(timezone.utc).date()
        stmt = pg_insert(UsageRecord).values(
            organization_id=org_id,
            application_id=app_id,
            endpoint=endpoint,
            bucket_date=today,
            request_count=1,
            success_count=1 if success else 0,
            failure_count=0 if success else 1,
            avg_latency_ms=latency_ms,
        ).on_conflict_do_update(
            constraint="uq_usage_org_app_endpoint_date",
            set_={
                "request_count": UsageRecord.request_count + 1,
                "success_count": UsageRecord.success_count + (1 if success else 0),
                "failure_count": UsageRecord.failure_count + (0 if success else 1),
                # Running average approximation
                "avg_latency_ms": (
                    (UsageRecord.avg_latency_ms * UsageRecord.request_count + latency_ms)
                    / (UsageRecord.request_count + 1)
                ),
            },
        )
        await self.db.execute(stmt)

    async def get_daily_stats(
        self,
        org_id: uuid.UUID,
        days: int = 30,
        app_id: uuid.UUID | None = None,
    ) -> list[dict]:
        since = datetime.now(timezone.utc).date() - timedelta(days=days)
        q = (
            select(
                UsageRecord.bucket_date,
                func.sum(UsageRecord.request_count).label("request_count"),
                func.sum(UsageRecord.success_count).label("success_count"),
                func.sum(UsageRecord.failure_count).label("failure_count"),
                func.avg(UsageRecord.avg_latency_ms).label("avg_latency_ms"),
            )
            .where(
                UsageRecord.organization_id == org_id,
                UsageRecord.bucket_date >= since,
            )
            .group_by(UsageRecord.bucket_date)
            .order_by(UsageRecord.bucket_date.asc())
        )
        if app_id:
            q = q.where(UsageRecord.application_id == app_id)
        rows = (await self.db.execute(q)).all()
        return [
            {
                "date": str(r.bucket_date),
                "request_count": int(r.request_count or 0),
                "success_count": int(r.success_count or 0),
                "failure_count": int(r.failure_count or 0),
                "avg_latency_ms": round(float(r.avg_latency_ms or 0), 2),
            }
            for r in rows
        ]

    async def get_overview(self, org_id: uuid.UUID, days: int = 30) -> dict:
        since = datetime.now(timezone.utc).date() - timedelta(days=days)
        result = await self.db.execute(
            select(
                func.sum(UsageRecord.request_count).label("total"),
                func.sum(UsageRecord.success_count).label("success"),
                func.avg(UsageRecord.avg_latency_ms).label("avg_latency"),
            ).where(
                UsageRecord.organization_id == org_id,
                UsageRecord.bucket_date >= since,
            )
        )
        row = result.one_or_none()
        total = int(row.total or 0) if row else 0
        success = int(row.success or 0) if row else 0
        avg_latency = round(float(row.avg_latency or 0), 2) if row else 0.0
        return {
            "total_requests": total,
            "success_rate": round((success / total * 100), 2) if total > 0 else 0.0,
            "avg_latency_ms": avg_latency,
        }

    async def get_by_application(self, org_id: uuid.UUID, days: int = 30) -> list[dict]:
        since = datetime.now(timezone.utc).date() - timedelta(days=days)
        q = (
            select(
                UsageRecord.application_id,
                func.sum(UsageRecord.request_count).label("request_count"),
                func.sum(UsageRecord.success_count).label("success_count"),
            )
            .where(
                UsageRecord.organization_id == org_id,
                UsageRecord.bucket_date >= since,
                UsageRecord.application_id.isnot(None),
            )
            .group_by(UsageRecord.application_id)
            .order_by(func.sum(UsageRecord.request_count).desc())
        )
        rows = (await self.db.execute(q)).all()
        return [
            {
                "application_id": str(r.application_id),
                "request_count": int(r.request_count or 0),
                "success_rate": round(
                    (int(r.success_count or 0) / int(r.request_count or 1)) * 100, 2
                ),
            }
            for r in rows
        ]

    async def get_api_calls_today(self) -> int:
        today = datetime.now(timezone.utc).date()
        result = await self.db.execute(
            select(func.sum(UsageRecord.request_count)).where(
                UsageRecord.bucket_date == today
            )
        )
        val = result.scalar_one_or_none()
        return int(val or 0)
