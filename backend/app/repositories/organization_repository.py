"""
NeoFace AaaS — Organization Repository
CRUD + pagination for Organization and Application models.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.application import Application
from app.models.identity import Identity
from app.models.auth_session import AuthenticationSession
from app.models.organization import Organization
from app.models.org_membership import OrgMembership
from app.schemas.aaas import OrganizationCreate, OrganizationUpdate


class OrganizationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Organization CRUD ─────────────────────────────────────────────────────

    async def create(self, schema: OrganizationCreate) -> Organization:
        org = Organization(
            name=schema.name,
            slug=schema.slug,
            plan=schema.plan,
        )
        self.db.add(org)
        await self.db.flush()
        await self.db.refresh(org)
        return org

    async def get_by_id(self, org_id: uuid.UUID) -> Organization | None:
        result = await self.db.execute(
            select(Organization).where(Organization.id == org_id)
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Organization | None:
        result = await self.db.execute(
            select(Organization).where(Organization.slug == slug)
        )
        return result.scalar_one_or_none()

    async def get_default(self) -> Organization | None:
        """Return the seeded default organization (slug='neoface-default')."""
        return await self.get_by_slug("neoface-default")

    async def update(
        self, org_id: uuid.UUID, schema: OrganizationUpdate
    ) -> Organization | None:
        org = await self.get_by_id(org_id)
        if not org:
            return None
        data = schema.model_dump(exclude_none=True)
        for key, val in data.items():
            setattr(org, key, val)
        await self.db.flush()
        await self.db.refresh(org)
        return org

    async def list_all(
        self,
        page: int = 1,
        page_size: int = 50,
        status: str | None = None,
    ) -> tuple[list[Organization], int]:
        q = select(Organization)
        if status:
            q = q.where(Organization.status == status)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        q = q.order_by(Organization.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        orgs = (await self.db.execute(q)).scalars().all()
        return list(orgs), total

    async def count_all(self) -> int:
        result = await self.db.execute(select(func.count(Organization.id)))
        return result.scalar_one()

    # ── Per-org stats ─────────────────────────────────────────────────────────

    async def count_applications(self, org_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(Application.id)).where(Application.organization_id == org_id)
        )
        return result.scalar_one()

    async def count_identities(self, org_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(func.count(Identity.id)).where(Identity.organization_id == org_id)
        )
        return result.scalar_one()

    # ── Application CRUD ──────────────────────────────────────────────────────

    async def create_application(
        self, org_id: uuid.UUID, name: str, environment: str = "production",
        description: str | None = None
    ) -> Application:
        app = Application(
            organization_id=org_id,
            name=name,
            environment=environment,
            description=description,
        )
        self.db.add(app)
        await self.db.flush()
        await self.db.refresh(app)
        return app

    async def get_application(self, app_id: uuid.UUID) -> Application | None:
        result = await self.db.execute(
            select(Application).where(Application.id == app_id)
        )
        return result.scalar_one_or_none()

    async def list_applications(
        self, org_id: uuid.UUID, page: int = 1, page_size: int = 50
    ) -> tuple[list[Application], int]:
        q = select(Application).where(Application.organization_id == org_id)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        q = q.order_by(Application.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        apps = (await self.db.execute(q)).scalars().all()
        return list(apps), total

    async def count_applications_total(self) -> int:
        result = await self.db.execute(select(func.count(Application.id)))
        return result.scalar_one()

    # ── Membership ────────────────────────────────────────────────────────────

    async def add_member(
        self, org_id: uuid.UUID, user_id: uuid.UUID, role: str = "member"
    ) -> OrgMembership:
        membership = OrgMembership(
            organization_id=org_id,
            user_id=user_id,
            role=role,
        )
        self.db.add(membership)
        await self.db.flush()
        await self.db.refresh(membership)
        return membership

    async def get_user_org(self, user_id: uuid.UUID) -> Organization | None:
        """Return the primary org for a user (first by creation date)."""
        result = await self.db.execute(
            select(Organization)
            .join(OrgMembership, OrgMembership.organization_id == Organization.id)
            .where(OrgMembership.user_id == user_id)
            .order_by(OrgMembership.created_at.asc())
            .limit(1)
        )
        return result.scalar_one_or_none()
