"""
NeoFace AaaS — Identity Repository
CRUD + pagination + search for Identity records.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.identity import Identity


class IdentityRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        org_id: uuid.UUID,
        app_id: uuid.UUID,
        external_user_id: str,
    ) -> Identity:
        identity = Identity(
            organization_id=org_id,
            application_id=app_id,
            external_user_id=external_user_id,
            enrollment_status="pending",
        )
        self.db.add(identity)
        await self.db.flush()
        await self.db.refresh(identity)
        return identity

    async def get_by_id(self, identity_id: uuid.UUID) -> Identity | None:
        result = await self.db.execute(
            select(Identity).where(Identity.id == identity_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_org(
        self, identity_id: uuid.UUID, org_id: uuid.UUID
    ) -> Identity | None:
        result = await self.db.execute(
            select(Identity).where(
                Identity.id == identity_id,
                Identity.organization_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_external_id(
        self, org_id: uuid.UUID, app_id: uuid.UUID, external_user_id: str
    ) -> Identity | None:
        result = await self.db.execute(
            select(Identity).where(
                Identity.organization_id == org_id,
                Identity.application_id == app_id,
                Identity.external_user_id == external_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        org_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
        app_id: uuid.UUID | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> tuple[list[Identity], int]:
        q = select(Identity).where(Identity.organization_id == org_id)
        if app_id:
            q = q.where(Identity.application_id == app_id)
        if status:
            q = q.where(Identity.enrollment_status == status)
        if search:
            q = q.where(
                Identity.external_user_id.ilike(f"%{search}%")
            )
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        q = q.order_by(Identity.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        identities = (await self.db.execute(q)).scalars().all()
        return list(identities), total

    async def update_status(
        self,
        identity_id: uuid.UUID,
        status: str,
        face_embedding_id: uuid.UUID | None = None,
    ) -> Identity | None:
        identity = await self.get_by_id(identity_id)
        if identity:
            identity.enrollment_status = status
            if face_embedding_id is not None:
                identity.face_embedding_id = face_embedding_id
            await self.db.flush()
            await self.db.refresh(identity)
        return identity

    async def delete(self, identity_id: uuid.UUID) -> bool:
        identity = await self.get_by_id(identity_id)
        if not identity:
            return False
        await self.db.delete(identity)
        await self.db.flush()
        return True

    async def count_total(self) -> int:
        result = await self.db.execute(select(func.count(Identity.id)))
        return result.scalar_one()

    async def count_by_org(self, org_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(Identity.id)).where(Identity.organization_id == org_id)
        )
        return result.scalar_one()
