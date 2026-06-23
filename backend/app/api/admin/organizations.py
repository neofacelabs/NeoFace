"""
NeoFace AaaS — Admin: Organizations Router
GET   /api/admin/organizations
GET   /api/admin/organizations/{id}
PATCH /api/admin/organizations/{id}
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_admin
from app.repositories.organization_repository import OrganizationRepository
from app.schemas.aaas import (
    OrganizationDetail,
    OrganizationResponse,
    OrganizationUpdate,
    PagedResponse,
)

router = APIRouter(prefix="/organizations", tags=["Admin — Organizations"])


@router.get(
    "",
    response_model=PagedResponse[OrganizationResponse],
    summary="[Admin] List all organizations",
)
async def list_organizations(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    status: str | None = Query(default=None),
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PagedResponse[OrganizationResponse]:
    repo = OrganizationRepository(db)
    orgs, total = await repo.list_all(page=page, page_size=page_size, status=status)
    items = [OrganizationResponse.model_validate(o) for o in orgs]
    return PagedResponse(total=total, page=page, page_size=page_size, items=items)


@router.get(
    "/{org_id}",
    response_model=OrganizationDetail,
    summary="[Admin] Get organization details with aggregated stats",
)
async def get_organization(
    org_id: uuid.UUID,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> OrganizationDetail:
    from fastapi import HTTPException
    repo = OrganizationRepository(db)
    org = await repo.get_by_id(org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    app_count = await repo.count_applications(org_id)
    identity_count = await repo.count_identities(org_id)

    base = OrganizationResponse.model_validate(org)
    return OrganizationDetail(
        **base.model_dump(),
        application_count=app_count,
        identity_count=identity_count,
        session_count_30d=0,
        api_call_count_30d=0,
    )


@router.patch(
    "/{org_id}",
    response_model=OrganizationResponse,
    summary="[Admin] Update organization plan or status",
)
async def update_organization(
    org_id: uuid.UUID,
    schema: OrganizationUpdate,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> OrganizationResponse:
    from fastapi import HTTPException
    repo = OrganizationRepository(db)
    org = await repo.update(org_id, schema)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return OrganizationResponse.model_validate(org)
