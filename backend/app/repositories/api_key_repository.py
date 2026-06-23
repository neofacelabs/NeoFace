"""
NeoFace AaaS — API Key Repository
Prefix-based O(1) lookup + CRUD for AaaSApiKey.
"""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import AaaSApiKey


class ApiKeyRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        org_id: uuid.UUID,
        name: str,
        key_prefix: str,
        hashed_secret: str,
        scopes: list[str],
        app_id: uuid.UUID | None = None,
    ) -> AaaSApiKey:
        key = AaaSApiKey(
            organization_id=org_id,
            application_id=app_id,
            name=name,
            key_prefix=key_prefix,
            hashed_secret=hashed_secret,
            scopes=scopes,
        )
        self.db.add(key)
        await self.db.flush()
        await self.db.refresh(key)
        return key

    async def get_by_id(self, key_id: uuid.UUID) -> AaaSApiKey | None:
        result = await self.db.execute(
            select(AaaSApiKey).where(AaaSApiKey.id == key_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_org(
        self, key_id: uuid.UUID, org_id: uuid.UUID
    ) -> AaaSApiKey | None:
        result = await self.db.execute(
            select(AaaSApiKey).where(
                AaaSApiKey.id == key_id,
                AaaSApiKey.organization_id == org_id,
            )
        )
        return result.scalar_one_or_none()

    async def find_by_prefix(self, prefix: str) -> AaaSApiKey | None:
        """O(1) indexed lookup by key_prefix — first step of validation."""
        result = await self.db.execute(
            select(AaaSApiKey).where(
                AaaSApiKey.key_prefix == prefix,
                AaaSApiKey.status == "active",
            )
        )
        return result.scalar_one_or_none()

    async def list_by_org(
        self,
        org_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
        include_revoked: bool = False,
    ) -> tuple[list[AaaSApiKey], int]:
        q = select(AaaSApiKey).where(AaaSApiKey.organization_id == org_id)
        if not include_revoked:
            q = q.where(AaaSApiKey.status == "active")
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        q = q.order_by(AaaSApiKey.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        keys = (await self.db.execute(q)).scalars().all()
        return list(keys), total

    async def update_status(self, key_id: uuid.UUID, status: str) -> AaaSApiKey | None:
        key = await self.get_by_id(key_id)
        if key:
            key.status = status
            await self.db.flush()
            await self.db.refresh(key)
        return key

    async def touch_last_used(self, key_id: uuid.UUID) -> None:
        """Update last_used_at to now."""
        from datetime import datetime, timezone
        key = await self.get_by_id(key_id)
        if key:
            key.last_used_at = datetime.now(timezone.utc)
            await self.db.flush()
