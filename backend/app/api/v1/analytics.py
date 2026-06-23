"""
NeoFace AaaS — Analytics Router
GET /api/v1/analytics/overview
GET /api/v1/analytics/usage
GET /api/v1/analytics/applications
GET /api/v1/analytics/authentication
"""

import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.api_key_auth import OrgContext, get_org_context
from app.schemas.aaas import AnalyticsOverview
from app.services.analytics_service import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/overview",
    response_model=AnalyticsOverview,
    summary="Get analytics overview for your organization",
)
async def get_overview(
    days: int = Query(default=30, ge=1, le=365),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> AnalyticsOverview:
    svc = AnalyticsService(db)
    return await svc.get_overview(ctx.org_id, days=days)


@router.get(
    "/usage",
    summary="Get daily request usage breakdown",
)
async def get_usage(
    days: int = Query(default=30, ge=1, le=365),
    application_id: uuid.UUID | None = Query(default=None),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    svc = AnalyticsService(db)
    return await svc.get_daily_usage(ctx.org_id, days=days, app_id=application_id)


@router.get(
    "/applications",
    summary="Get request volume per application",
)
async def get_by_application(
    days: int = Query(default=30, ge=1, le=365),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    svc = AnalyticsService(db)
    return await svc.get_by_application(ctx.org_id, days=days)


@router.get(
    "/authentication",
    summary="Get authentication event breakdown by type and status",
)
async def get_authentication_stats(
    days: int = Query(default=30, ge=1, le=365),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> dict:
    svc = AnalyticsService(db)
    return await svc.get_authentication_stats(ctx.org_id, days=days)
