"""
NeoFace AaaS — Admin: Infrastructure Monitoring Router
GET /api/admin/infrastructure
GET /api/admin/infrastructure/services
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_admin
from app.schemas.aaas import InfraMetrics, ServiceHealth
from app.services.infra_service import InfraService

router = APIRouter(prefix="/infrastructure", tags=["Admin — Infrastructure"])


@router.get(
    "",
    response_model=InfraMetrics,
    summary="[Admin] Full system snapshot (CPU, memory, GPU, queues, services)",
)
async def get_infrastructure(
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> InfraMetrics:
    svc = InfraService()
    return await svc.get_metrics()


@router.get(
    "/services",
    response_model=list[ServiceHealth],
    summary="[Admin] Service-level health check (DB, Redis, Celery)",
)
async def get_services(
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[ServiceHealth]:
    svc = InfraService()
    return await svc.get_services()
