"""
NeoFace AaaS — Identities Router
GET    /api/v1/identities
GET    /api/v1/identities/{id}
POST   /api/v1/identities
DELETE /api/v1/identities/{id}
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.api_key_auth import OrgContext, get_org_context
from app.schemas.aaas import IdentityCreate, IdentityResponse, PagedResponse
from app.services.identity_service import IdentityService

router = APIRouter(prefix="/identities", tags=["Identities"])


@router.get(
    "",
    response_model=PagedResponse[IdentityResponse],
    summary="List identities in your organization",
)
async def list_identities(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    application_id: uuid.UUID | None = Query(default=None),
    status: str | None = Query(default=None, description="Filter by enrollment_status"),
    search: str | None = Query(default=None, description="Search by external_user_id"),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> PagedResponse[IdentityResponse]:
    svc = IdentityService(db)
    identities, total = await svc.list(
        ctx.org_id,
        page=page,
        page_size=page_size,
        app_id=application_id,
        status_filter=status,
        search=search,
    )
    return PagedResponse(total=total, page=page, page_size=page_size, items=identities)


@router.get(
    "/{identity_id}",
    response_model=IdentityResponse,
    summary="Get a single identity",
)
async def get_identity(
    identity_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> IdentityResponse:
    svc = IdentityService(db)
    return await svc.get(identity_id, ctx.org_id)


@router.post(
    "",
    response_model=IdentityResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new identity",
)
async def create_identity(
    schema: IdentityCreate,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> IdentityResponse:
    svc = IdentityService(db)
    return await svc.create(ctx.org_id, schema)


@router.delete(
    "/{identity_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete an identity",
)
async def delete_identity(
    identity_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    svc = IdentityService(db)
    return await svc.delete(identity_id, ctx.org_id)
