"""
NeoFace Verification API
Endpoints:
- POST /api/v1/verify — Verify identity against enrolled users
"""

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status

from app.core.config import settings
from app.core.logging import logger
from app.schemas.verification import VerificationResponse
from app.services.verification_service import VerificationService
from app.utils.dependencies import get_client_ip, get_verification_service

router = APIRouter(prefix="/verify", tags=["Face Verification"])

SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE_BYTES = int(settings.MAX_IMAGE_SIZE_MB * 1024 * 1024)


@router.post(
    "",
    response_model=VerificationResponse,
    summary="Verify a face against enrolled users",
    description="""
    Upload a live face image to authenticate against enrolled users.

    **Pipeline (default — `use_pipeline=true`):**

    | Stage | Check | Notes |
    |---|---|---|
    | 1 | Face Detection | InsightFace buffalo_l |
    | 2 | Quality Validation | Blur, resolution, detection score |
    | 3 | Blink Detection | MediaPipe EAR |
    | 4 | Head Movement | Yaw angle ≥ 15° |
    | 5 | Passive Anti-Spoof | MiniFASNet ONNX (heuristic fallback) |
    | 6 | Score Composition | Weighted aggregation |

    **Decision rule:**
    `is_live = anti_spoof_passed AND (blink OR head_turn) AND score ≥ threshold`

    **Authentication threshold:** configurable via `threshold` query param (default 0.65).

    All attempts — success and failure — are written to the audit log.
    """,
    responses={
        200: {"description": "Verification result (authenticated may be false)"},
        400: {"description": "Invalid image or parameters"},
        429: {"description": "Rate limit exceeded"},
    },
)
async def verify_face(
    request: Request,
    image: UploadFile = File(
        ...,
        description="Live face image (JPEG, PNG, or WebP). Max 10 MB.",
    ),
    threshold: float | None = Query(
        default=None,
        ge=0.0,
        le=1.0,
        description="Override cosine similarity threshold (0.0–1.0). Defaults to SIMILARITY_THRESHOLD env var.",
    ),
    use_pipeline: bool = Query(
        default=True,
        description=(
            "Use the full 6-stage pipeline with anti-spoofing (recommended). "
            "Set false to use the lighter single-stage MediaPipe check."
        ),
    ),
    verification_service: VerificationService = Depends(get_verification_service),
) -> VerificationResponse:
    """
    Verify a face image against all enrolled users.

    Always returns 200 with a VerificationResponse — HTTP errors are only raised
    for malformed requests (bad image format, size exceeded, invalid params).
    Authentication failures are expressed via `authenticated: false` in the body.
    """
    # ── Validate content type ─────────────────────────────────────────────────
    if image.content_type and image.content_type not in SUPPORTED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Unsupported image type '{image.content_type}'. "
                "Accepted: image/jpeg, image/png, image/webp"
            ),
        )

    # ── Read and validate size ────────────────────────────────────────────────
    image_data = await image.read()

    if len(image_data) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Image file is empty",
        )

    if len(image_data) > MAX_IMAGE_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Image exceeds maximum size of {settings.MAX_IMAGE_SIZE_MB} MB",
        )

    # ── Run verification ──────────────────────────────────────────────────────
    ip_address = get_client_ip(request)
    user_agent = request.headers.get("User-Agent")

    return await verification_service.verify(
        image_bytes=image_data,
        ip_address=ip_address,
        user_agent=user_agent,
        threshold=threshold,
        use_pipeline=use_pipeline,
    )
