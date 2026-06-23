"""
NeoFace AaaS — Webhooks Router
GET  /api/v1/webhooks
POST /api/v1/webhooks
POST /api/v1/webhooks/{id}/test
GET  /api/v1/webhooks/{id}/deliveries
"""

import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.api_key_auth import OrgContext, get_org_context
from app.schemas.aaas import PagedResponse, WebhookCreate, WebhookDeliveryResponse, WebhookResponse
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.get(
    "",
    response_model=PagedResponse[WebhookResponse],
    summary="List registered webhook endpoints",
)
async def list_webhooks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> PagedResponse[WebhookResponse]:
    svc = WebhookService(db)
    endpoints, total = await svc.list_endpoints(ctx.org_id, page=page, page_size=page_size)
    return PagedResponse(total=total, page=page, page_size=page_size, items=endpoints)


@router.post(
    "",
    response_model=WebhookResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new webhook endpoint",
)
async def create_webhook(
    schema: WebhookCreate,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> WebhookResponse:
    svc = WebhookService(db)
    return await svc.create_endpoint(ctx.org_id, schema)


@router.post(
    "/{endpoint_id}/test",
    summary="Send a test event to a webhook endpoint",
)
async def test_webhook(
    endpoint_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    svc = WebhookService(db)
    return await svc.send_test(endpoint_id, ctx.org_id)


@router.get(
    "/{endpoint_id}/deliveries",
    response_model=PagedResponse[WebhookDeliveryResponse],
    summary="List delivery attempts for a webhook endpoint",
)
async def list_deliveries(
    endpoint_id: uuid.UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> PagedResponse[WebhookDeliveryResponse]:
    svc = WebhookService(db)
    deliveries, total = await svc.list_deliveries(endpoint_id, ctx.org_id, page=page, page_size=page_size)
    return PagedResponse(total=total, page=page, page_size=page_size, items=deliveries)
