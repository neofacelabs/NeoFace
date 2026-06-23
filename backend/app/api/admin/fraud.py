"""
NeoFace AaaS — Admin: Fraud Center Router
GET /api/admin/fraud/overview
GET /api/admin/fraud/timeline
GET /api/admin/fraud/events
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_admin
from app.schemas.aaas import FraudEventResponse, FraudOverviewResponse, FraudTimelinePoint, PagedResponse
from app.services.fraud_service import FraudService

router = APIRouter(prefix="/fraud", tags=["Admin — Fraud Center"])


@router.get(
    "/overview",
    response_model=FraudOverviewResponse,
    summary="[Admin] Fraud KPI overview (last 24h)",
)
async def get_fraud_overview(
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> FraudOverviewResponse:
    svc = FraudService(db)
    return await svc.get_overview()


@router.get(
    "/timeline",
    response_model=list[FraudTimelinePoint],
    summary="[Admin] Daily threat event counts",
)
async def get_fraud_timeline(
    days: int = Query(default=14, ge=1, le=90),
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[FraudTimelinePoint]:
    svc = FraudService(db)
    return await svc.get_timeline(days=days)


@router.get(
    "/events",
    response_model=PagedResponse[FraudEventResponse],
    summary="[Admin] Recent threat events",
)
async def get_fraud_events(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> PagedResponse[FraudEventResponse]:
    svc = FraudService(db)
    events, total = await svc.get_events(page=page, page_size=page_size)
    return PagedResponse(total=total, page=page, page_size=page_size, items=events)
