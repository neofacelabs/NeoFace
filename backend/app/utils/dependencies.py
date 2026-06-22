"""
NeoFace Dependency Injection
Centralized FastAPI dependency providers.
All services are instantiated here and injected into route handlers.
"""

from functools import lru_cache

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.services.face_detector import FaceDetectorService
from app.services.face_embedding import FaceEmbeddingService
from app.services.liveness_service import LivenessService
from app.services.enrollment_service import EnrollmentService
from app.services.verification_service import VerificationService
from app.utils.storage import StorageService


# ── Singleton services (initialized once at startup) ──────────────────────────

@lru_cache(maxsize=1)
def get_face_detector() -> FaceDetectorService:
    """Return global FaceDetectorService singleton."""
    return FaceDetectorService.get_instance()


@lru_cache(maxsize=1)
def get_face_embedder() -> FaceEmbeddingService:
    """Return global FaceEmbeddingService singleton."""
    return FaceEmbeddingService()


@lru_cache(maxsize=1)
def get_storage() -> StorageService:
    """Return global StorageService singleton."""
    return StorageService()


# ── Per-request services (depend on DB session) ───────────────────────────────

def get_liveness_service() -> LivenessService:
    """Create per-request LivenessService (MediaPipe is lightweight)."""
    return LivenessService()


async def get_enrollment_service(
    db: AsyncSession = Depends(get_db),
    detector: FaceDetectorService = Depends(get_face_detector),
    embedder: FaceEmbeddingService = Depends(get_face_embedder),
    storage: StorageService = Depends(get_storage),
) -> EnrollmentService:
    """Create per-request EnrollmentService with injected dependencies."""
    return EnrollmentService(
        db=db,
        detector=detector,
        embedder=embedder,
        storage=storage,
    )


async def get_verification_service(
    db: AsyncSession = Depends(get_db),
    detector: FaceDetectorService = Depends(get_face_detector),
    embedder: FaceEmbeddingService = Depends(get_face_embedder),
    liveness: LivenessService = Depends(get_liveness_service),
) -> VerificationService:
    """Create per-request VerificationService with injected dependencies."""
    return VerificationService(
        db=db,
        detector=detector,
        embedder=embedder,
        liveness=liveness,
    )


def get_client_ip(request: Request) -> str:
    """Extract real client IP, handling reverse proxy headers."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"
