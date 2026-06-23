"""
NeoFace AaaS — Session Service
Records and queries authentication sessions.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.session_repository import SessionRepository
from app.schemas.aaas import SessionResponse


class SessionService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = SessionRepository(db)

    async def record(
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
    ) -> SessionResponse:
        session = await self.repo.create(
            org_id=org_id,
            app_id=app_id,
            event_type=event_type,
            status=status,
            identity_id=identity_id,
            confidence_score=confidence_score,
            risk_score=risk_score,
            ip_address=ip_address,
            device_fingerprint=device_fingerprint,
            latency_ms=latency_ms,
        )
        return SessionResponse.model_validate(session)

    async def get(
        self, session_id: uuid.UUID, org_id: uuid.UUID
    ) -> SessionResponse:
        from fastapi import HTTPException, status as http_status
        session = await self.repo.get_by_id(session_id)
        if not session or session.organization_id != org_id:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        return SessionResponse.model_validate(session)

    async def list(
        self,
        org_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
        app_id: uuid.UUID | None = None,
        event_type: str | None = None,
        status: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> tuple[list[SessionResponse], int]:
        sessions, total = await self.repo.list_by_org(
            org_id,
            page=page,
            page_size=page_size,
            app_id=app_id,
            event_type=event_type,
            status=status,
            from_date=from_date,
            to_date=to_date,
        )
        return [SessionResponse.model_validate(s) for s in sessions], total
