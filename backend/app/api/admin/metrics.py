"""
NeoFace AaaS — Admin: Global Metrics Router
GET /api/admin/metrics
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_admin
from app.repositories.organization_repository import OrganizationRepository
from app.repositories.identity_repository import IdentityRepository
from app.repositories.session_repository import SessionRepository
from app.repositories.usage_repository import UsageRepository
from app.schemas.aaas import GlobalMetricsResponse

router = APIRouter(prefix="/metrics", tags=["Admin — Metrics"])


@router.get(
    "",
    response_model=GlobalMetricsResponse,
    summary="[Admin] Global platform KPIs",
)
async def get_global_metrics(
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> GlobalMetricsResponse:
    org_repo = OrganizationRepository(db)
    identity_repo = IdentityRepository(db)
    session_repo = SessionRepository(db)
    usage_repo = UsageRepository(db)

    org_count = await org_repo.count_all()
    app_count = await org_repo.count_applications_total()
    identity_count = await identity_repo.count_total()
    session_count = await session_repo.count_total()
    api_calls_today = await usage_repo.get_api_calls_today()

    # Avg latency across all sessions
    from sqlalchemy import func, select
    from app.models.auth_session import AuthenticationSession
    lat_result = await db.execute(
        select(func.avg(AuthenticationSession.latency_ms)).where(
            AuthenticationSession.latency_ms.isnot(None)
        )
    )
    avg_latency = float(lat_result.scalar_one_or_none() or 0.0)

    # Threat events in last 24h from fraud service
    from app.services.fraud_service import FraudService
    fraud_svc = FraudService(db)
    fraud_overview = await fraud_svc.get_overview()

    return GlobalMetricsResponse(
        organization_count=org_count,
        application_count=app_count,
        identity_count=identity_count,
        session_count=session_count,
        api_calls_today=api_calls_today,
        avg_latency_ms=round(avg_latency, 2),
        threat_events_24h=fraud_overview.total_threat_events_24h,
        as_of=datetime.now(timezone.utc),
    )
