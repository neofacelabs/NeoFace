"""
NeoFace AaaS — API Keys Router
GET  /api/v1/api-keys
POST /api/v1/api-keys
POST /api/v1/api-keys/{id}/rotate
POST /api/v1/api-keys/{id}/revoke
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.api_key_auth import OrgContext, get_org_context
from app.schemas.aaas import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse, PagedResponse
from app.services.api_key_service import ApiKeyService

router = APIRouter(prefix="/api-keys", tags=["API Keys"])


@router.get(
    "",
    response_model=PagedResponse[ApiKeyResponse],
    summary="List API keys for your organization",
)
async def list_api_keys(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> PagedResponse[ApiKeyResponse]:
    svc = ApiKeyService(db)
    keys, total = await svc.list_keys(ctx.org_id, page=page, page_size=page_size)
    return PagedResponse(total=total, page=page, page_size=page_size, items=keys)


@router.post(
    "",
    response_model=ApiKeyCreatedResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new API key",
    description=(
        "Returns the full plaintext key **once only**. "
        "Store it securely — it cannot be retrieved again."
    ),
)
async def create_api_key(
    schema: ApiKeyCreate,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreatedResponse:
    svc = ApiKeyService(db)
    return await svc.create_key(ctx.org_id, schema)


@router.post(
    "/{key_id}/rotate",
    response_model=ApiKeyCreatedResponse,
    summary="Rotate an API key",
    description="Revokes the existing key and issues a new one. Old key is invalidated immediately.",
)
async def rotate_api_key(
    key_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyCreatedResponse:
    svc = ApiKeyService(db)
    return await svc.rotate_key(key_id, ctx.org_id)


@router.post(
    "/{key_id}/revoke",
    response_model=ApiKeyResponse,
    summary="Revoke an API key",
)
async def revoke_api_key(
    key_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> ApiKeyResponse:
    svc = ApiKeyService(db)
    return await svc.revoke_key(key_id, ctx.org_id)
