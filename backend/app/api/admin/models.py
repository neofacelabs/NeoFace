"""
NeoFace AaaS — Admin: Model Monitoring Router
GET /api/admin/models
GET /api/admin/models/{id}
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_admin
from app.schemas.aaas import ModelVersionResponse
from app.services.model_registry_service import ModelRegistryService

router = APIRouter(prefix="/models", tags=["Admin — Model Monitoring"])


@router.get(
    "",
    response_model=list[ModelVersionResponse],
    summary="[Admin] List all ML model versions",
)
async def list_models(
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> list[ModelVersionResponse]:
    svc = ModelRegistryService(db)
    await svc.seed_if_empty()
    return await svc.list_all()


@router.get(
    "/{model_id}",
    response_model=ModelVersionResponse,
    summary="[Admin] Get a specific model version",
)
async def get_model(
    model_id: uuid.UUID,
    _=Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> ModelVersionResponse:
    svc = ModelRegistryService(db)
    mv = await svc.get_by_id(model_id)
    if not mv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model version not found",
        )
    return mv
