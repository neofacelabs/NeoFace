"""
NeoFace AaaS — Session Repository
Queries for AuthenticationSession records.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.auth_session import AuthenticationSession


class SessionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        org_id: uuid.UUID,
        app_id: uuid.UUID,
        event_type: str,
        status: str,
        identity_id: uuid.UUID | None = None,
        confidence_score: float | None = None,
        risk_score: float | None = None,
        ip_address: str | None = None,
        device_fingerprint: str | None = None,
        latency_ms: int | None = None,
    ) -> AuthenticationSession:
        session = AuthenticationSession(
            organization_id=org_id,
            application_id=app_id,
            identity_id=identity_id,
            event_type=event_type,
            status=status,
            confidence_score=confidence_score,
            risk_score=risk_score,
            ip_address=ip_address,
            device_fingerprint=device_fingerprint,
            latency_ms=latency_ms,
        )
        self.db.add(session)
        await self.db.flush()
        await self.db.refresh(session)
        return session

    async def get_by_id(self, session_id: uuid.UUID) -> AuthenticationSession | None:
        result = await self.db.execute(
            select(AuthenticationSession).where(AuthenticationSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        org_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
        app_id: uuid.UUID | None = None,
        event_type: str | None = None,
        status: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> tuple[list[AuthenticationSession], int]:
        q = select(AuthenticationSession).where(
            AuthenticationSession.organization_id == org_id
        )
        if app_id:
            q = q.where(AuthenticationSession.application_id == app_id)
        if event_type:
            q = q.where(AuthenticationSession.event_type == event_type)
        if status:
            q = q.where(AuthenticationSession.status == status)
        if from_date:
            q = q.where(AuthenticationSession.created_at >= from_date)
        if to_date:
            q = q.where(AuthenticationSession.created_at <= to_date)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        q = q.order_by(AuthenticationSession.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        sessions = (await self.db.execute(q)).scalars().all()
        return list(sessions), total

    async def count_total(self) -> int:
        result = await self.db.execute(select(func.count(AuthenticationSession.id)))
        return result.scalar_one()

    async def count_by_org(self, org_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(AuthenticationSession.id)).where(
                AuthenticationSession.organization_id == org_id
            )
        )
        return result.scalar_one()

    async def get_success_rate_by_org(self, org_id: uuid.UUID) -> float:
        total_q = select(func.count(AuthenticationSession.id)).where(
            AuthenticationSession.organization_id == org_id
        )
        success_q = select(func.count(AuthenticationSession.id)).where(
            AuthenticationSession.organization_id == org_id,
            AuthenticationSession.status == "success",
        )
        total = (await self.db.execute(total_q)).scalar_one() or 0
        success = (await self.db.execute(success_q)).scalar_one() or 0
        if total == 0:
            return 0.0
        return round((success / total) * 100, 2)

    async def get_avg_latency_by_org(self, org_id: uuid.UUID) -> float:
        result = await self.db.execute(
            select(func.avg(AuthenticationSession.latency_ms)).where(
                AuthenticationSession.organization_id == org_id,
                AuthenticationSession.latency_ms.isnot(None),
            )
        )
        val = result.scalar_one_or_none()
        return round(float(val), 2) if val else 0.0
