"""
NeoFace AaaS — Audit Event Repository
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_event import AuditEvent


class AuditEventRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def emit(
        self,
        org_id: uuid.UUID,
        event_type: str,
        app_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> AuditEvent:
        event = AuditEvent(
            organization_id=org_id,
            application_id=app_id,
            actor_id=actor_id,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata_=metadata,
            ip_address=ip_address,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def list_by_org(
        self,
        org_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
        app_id: uuid.UUID | None = None,
        event_type: str | None = None,
        actor_id: uuid.UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> tuple[list[AuditEvent], int]:
        q = select(AuditEvent).where(AuditEvent.organization_id == org_id)
        if app_id:
            q = q.where(AuditEvent.application_id == app_id)
        if event_type:
            q = q.where(AuditEvent.event_type == event_type)
        if actor_id:
            q = q.where(AuditEvent.actor_id == actor_id)
        if from_date:
            q = q.where(AuditEvent.created_at >= from_date)
        if to_date:
            q = q.where(AuditEvent.created_at <= to_date)

        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        q = q.order_by(AuditEvent.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        events = (await self.db.execute(q)).scalars().all()
        return list(events), total

    async def list_all_for_export(
        self,
        org_id: uuid.UUID,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> list[AuditEvent]:
        q = select(AuditEvent).where(AuditEvent.organization_id == org_id)
        if from_date:
            q = q.where(AuditEvent.created_at >= from_date)
        if to_date:
            q = q.where(AuditEvent.created_at <= to_date)
        q = q.order_by(AuditEvent.created_at.asc())
        events = (await self.db.execute(q)).scalars().all()
        return list(events)
