"""
NeoFace AaaS — Analytics Service
Aggregates usage data for customer-facing and admin analytics endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.usage_repository import UsageRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.identity_repository import IdentityRepository
from app.schemas.aaas import AnalyticsOverview


class AnalyticsService:
    def __init__(self, db: AsyncSession) -> None:
        self.usage_repo = UsageRepository(db)
        self.session_repo = SessionRepository(db)
        self.identity_repo = IdentityRepository(db)

    async def get_overview(
        self, org_id: uuid.UUID, days: int = 30
    ) -> AnalyticsOverview:
        usage = await self.usage_repo.get_overview(org_id, days=days)
        avg_latency = await self.session_repo.get_avg_latency_by_org(org_id)

        # Daily active identities: count distinct identities with sessions in last 24h
        # For now derive from sessions repo — exact DAI requires a dedicated query
        dai = await self._count_distinct_active_identities(org_id, days=1)
        mai = await self._count_distinct_active_identities(org_id, days=30)

        return AnalyticsOverview(
            org_id=org_id,
            period_days=days,
            total_requests=usage["total_requests"],
            success_rate=usage["success_rate"],
            avg_latency_ms=avg_latency,
            daily_active_identities=dai,
            monthly_active_identities=mai,
            as_of=datetime.now(timezone.utc),
        )

    async def _count_distinct_active_identities(
        self, org_id: uuid.UUID, days: int
    ) -> int:
        from datetime import timedelta
        from sqlalchemy import func, select
        from app.models.auth_session import AuthenticationSession

        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session_repo.db.execute(
            select(func.count(AuthenticationSession.identity_id.distinct())).where(
                AuthenticationSession.organization_id == org_id,
                AuthenticationSession.identity_id.isnot(None),
                AuthenticationSession.created_at >= since,
            )
        )
        return result.scalar_one() or 0

    async def get_daily_usage(
        self, org_id: uuid.UUID, days: int = 30, app_id: uuid.UUID | None = None
    ) -> list[dict]:
        return await self.usage_repo.get_daily_stats(org_id, days=days, app_id=app_id)

    async def get_by_application(
        self, org_id: uuid.UUID, days: int = 30
    ) -> list[dict]:
        return await self.usage_repo.get_by_application(org_id, days=days)

    async def get_authentication_stats(
        self, org_id: uuid.UUID, days: int = 30
    ) -> dict:
        """Stats breakdown by event_type and status for the authentication panel."""
        from datetime import timedelta
        from sqlalchemy import func, select
        from app.models.auth_session import AuthenticationSession

        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.session_repo.db.execute(
            select(
                AuthenticationSession.event_type,
                AuthenticationSession.status,
                func.count(AuthenticationSession.id).label("count"),
            )
            .where(
                AuthenticationSession.organization_id == org_id,
                AuthenticationSession.created_at >= since,
            )
            .group_by(
                AuthenticationSession.event_type,
                AuthenticationSession.status,
            )
        )
        rows = result.all()
        breakdown: dict = {}
        for row in rows:
            et = row.event_type
            if et not in breakdown:
                breakdown[et] = {"total": 0, "success": 0, "failure": 0}
            breakdown[et]["total"] += row.count
            if row.status == "success":
                breakdown[et]["success"] += row.count
            else:
                breakdown[et]["failure"] += row.count
        return {"period_days": days, "by_event_type": breakdown}
