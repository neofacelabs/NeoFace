"""
NeoFace AaaS — Identity Service
Wraps the Identity repository and delegates enrollment to the existing
EnrollmentService when biometric data is provided.
"""

from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.identity_repository import IdentityRepository
from app.schemas.aaas import IdentityCreate, IdentityResponse


class IdentityService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = IdentityRepository(db)

    async def create(
        self,
        org_id: uuid.UUID,
        schema: IdentityCreate,
    ) -> IdentityResponse:
        # Check for duplicate external_user_id within same org+app
        existing = await self.repo.get_by_external_id(
            org_id, schema.application_id, schema.external_user_id
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Identity with external_user_id '{schema.external_user_id}' already exists in this application.",
            )
        identity = await self.repo.create(
            org_id=org_id,
            app_id=schema.application_id,
            external_user_id=schema.external_user_id,
        )
        return IdentityResponse.model_validate(identity)

    async def get(
        self, identity_id: uuid.UUID, org_id: uuid.UUID
    ) -> IdentityResponse:
        identity = await self.repo.get_by_id_and_org(identity_id, org_id)
        if not identity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Identity not found",
            )
        return IdentityResponse.model_validate(identity)

    async def list(
        self,
        org_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
        app_id: uuid.UUID | None = None,
        status_filter: str | None = None,
        search: str | None = None,
    ) -> tuple[list[IdentityResponse], int]:
        identities, total = await self.repo.list_by_org(
            org_id,
            page=page,
            page_size=page_size,
            app_id=app_id,
            status=status_filter,
            search=search,
        )
        return [IdentityResponse.model_validate(i) for i in identities], total

    async def delete(
        self, identity_id: uuid.UUID, org_id: uuid.UUID
    ) -> dict:
        identity = await self.repo.get_by_id_and_org(identity_id, org_id)
        if not identity:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Identity not found",
            )
        await self.repo.delete(identity_id)
        return {"deleted": True, "id": str(identity_id)}
