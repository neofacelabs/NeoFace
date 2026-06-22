"""
NeoFace Trust Engine — Per-User Face Match API

POST /api/v1/trust-engine/verify-face
  Extracts ArcFace embedding from the submitted image and compares it against
  **only the authenticated user's** enrolled embeddings.

  Returns a 0-100 face match score that feeds into the Trust Score.
  Data is completely isolated — users never see each other's data.
"""

from __future__ import annotations

import time

import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.logging import logger
from app.core.security import TokenData, get_current_user
from app.repositories.embedding_repository import EmbeddingRepository
from app.services.face_embedding import FaceEmbeddingService
from app.utils.dependencies import get_face_detector

router = APIRouter(prefix="/trust-engine", tags=["Trust Engine"])


@router.post(
    "/verify-face",
    summary="Match current frame against logged-in user's enrolled face embeddings",
)
async def trust_engine_verify_face(
    image: UploadFile = File(..., description="Live camera frame (JPEG/PNG/WebP)"),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Per-user face match for the Trust Engine.

    - Extracts a 512-d ArcFace embedding from the submitted frame.
    - Compares it ONLY against the current user's enrolled embeddings.
    - Returns face_match_score (0–100) and whether the face matches.

    This endpoint is completely user-scoped — no cross-user data is ever accessed.
    """
    t0 = time.perf_counter()

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=422, detail="Empty image file")

    # ── Check user has enrolled face embeddings ───────────────────────────────
    emb_repo = EmbeddingRepository(db)
    user_embeddings = await emb_repo.get_by_user(current_user.user_uuid)

    if not user_embeddings:
        return {
            "face_enrolled": False,
            "face_match": False,
            "face_match_score": 0.0,
            "embedding_count": 0,
            "message": "No face enrolled. Please enroll your face first.",
            "inference_ms": 0.0,
        }

    # ── Extract embedding from live frame ────────────────────────────────────
    detector = get_face_detector()
    detection, face = detector.detect_single(image_bytes)

    if not detection.success or face is None:
        inference_ms = round((time.perf_counter() - t0) * 1000, 2)
        err_msg = detection.error or "No face detected in frame. Please position your face in the oval."
        logger.warning(f"trust_engine.verify_face: detection failed: {err_msg}")
        return {
            "face_enrolled": True,
            "face_match": False,
            "face_match_score": 0.0,
            "embedding_count": len(user_embeddings),
            "message": err_msg,
            "inference_ms": inference_ms,
        }

    if face.embedding is None or len(face.embedding) == 0:
        inference_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "face_enrolled": True,
            "face_match": False,
            "face_match_score": 0.0,
            "embedding_count": len(user_embeddings),
            "message": "Could not extract face embedding. Ensure good lighting.",
            "inference_ms": inference_ms,
        }

    query_emb = np.array(face.embedding, dtype=np.float32)
    query_norm = np.linalg.norm(query_emb)

    # ── Compare against all of this user's enrolled embeddings ────────────────
    best_similarity = 0.0
    for enrolled in user_embeddings:
        if enrolled.embedding_vector is None:
            continue
        enrolled_emb = np.array(enrolled.embedding_vector, dtype=np.float32)
        enrolled_norm = np.linalg.norm(enrolled_emb)

        if query_norm == 0.0 or enrolled_norm == 0.0:
            continue

        cosine_sim = float(np.dot(query_emb, enrolled_emb) / (query_norm * enrolled_norm))
        # Clamp to [0, 1] — cosine similarity can be negative for very different faces
        cosine_sim = max(0.0, cosine_sim)
        best_similarity = max(best_similarity, cosine_sim)

    # Convert cosine similarity to 0-100 score
    # ArcFace: same person typically 0.65-0.99 cosine sim
    # Threshold: 0.50 cosine = we consider it a match
    MATCH_THRESHOLD = 0.50
    face_match = best_similarity >= MATCH_THRESHOLD

    # Map cosine similarity to 0-100 score using a calibrated curve
    face_match_score = FaceEmbeddingService.calibrate_similarity_score(best_similarity)
    inference_ms = round((time.perf_counter() - t0) * 1000, 2)

    logger.debug(
        "trust_engine.verify_face",
        user_id=str(current_user.user_uuid),
        best_similarity=round(best_similarity, 4),
        face_match=face_match,
        face_match_score=face_match_score,
        enrolled_count=len(user_embeddings),
        inference_ms=inference_ms,
    )

    return {
        "face_enrolled": True,
        "face_match": face_match,
        "face_match_score": face_match_score,
        "cosine_similarity": round(best_similarity, 4),
        "embedding_count": len(user_embeddings),
        "detection_score": round(float(face.detection_score or 0), 3),
        "message": "Face matched successfully." if face_match else "Face does not match enrolled identity.",
        "inference_ms": inference_ms,
    }


@router.get(
    "/enrollment-status",
    summary="Get Trust Engine enrollment status for logged-in user",
)
async def trust_engine_enrollment_status(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns whether the logged-in user has enrolled face data for the Trust Engine.
    Used by the frontend to decide whether to show the enrollment gate or the scanner.
    """
    emb_repo = EmbeddingRepository(db)
    face_count = await emb_repo.count_by_user(current_user.user_uuid)

    return {
        "user_id": str(current_user.user_uuid),
        "face_enrolled": face_count > 0,
        "face_embedding_count": face_count,
        "ready_for_trust_engine": face_count > 0,
    }
