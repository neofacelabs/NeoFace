"""
NeoFace Trust Engine — Risk Scoring API (Module 11)

POST /api/v1/risk/score    — Compute NeoFace Trust Score
GET  /api/v1/risk/history  — Risk score history for authenticated user
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.core.database import get_db
from app.core.security import TokenData, get_current_user
from app.core.logging import logger
from app.models.trust_engine import RiskScore as RiskScoreModel
from app.services.risk_scoring_service import RiskScoreInput, RiskScoringService

router = APIRouter(prefix="/risk", tags=["Risk Scoring"])

_risk_svc = RiskScoringService()


# ── Request/Response schemas ──────────────────────────────────────────────────

class RiskScoreRequest(BaseModel):
    """Input signals for the NeoFace Trust Score engine."""

    # Core biometric scores (all 0–100, all optional)
    face_score: float | None = Field(default=None, ge=0, le=100, description="ArcFace match confidence 0–100")
    liveness_score: float | None = Field(default=None, ge=0, le=100, description="Passive liveness score 0–100")
    deepfake_score: float | None = Field(default=None, ge=0, le=100, description="Anti-deepfake score 0–100 (100=safe)")
    behavior_score: float | None = Field(default=None, ge=0, le=100, description="Behavioral biometrics score 0–100")
    device_trust_score: float | None = Field(default=None, ge=0, le=100, description="Device integrity score 0–100")
    location_trust: float | None = Field(default=None, ge=0, le=100, description="Geo/IP trust score 0–100")
    fingerprint_trust: float | None = Field(default=None, ge=0, le=100, description="Fingerprint/WebAuthn trust 0–100")

    # Context
    session_id: str | None = None
    transaction_id: str | None = None
    transaction_amount: float | None = Field(default=None, ge=0)

    # Weight overrides (optional)
    custom_weights: dict[str, float] | None = None


class ComponentScoresResponse(BaseModel):
    face_score: float | None = None
    liveness_score: float | None = None
    deepfake_score: float | None = None
    behavior_score: float | None = None
    device_trust_score: float | None = None
    location_trust: float | None = None
    fingerprint_trust: float | None = None


class RiskScoreResponse(BaseModel):
    final_trust_score: float
    decision: str                   # approve | step_up | reject
    component_scores: ComponentScoresResponse
    weights_used: dict[str, float]
    contributing_factors: int
    hard_blocked: bool
    hard_block_reason: str | None
    risk_flags: list[str]
    explanation: str
    score_id: str | None = None


class RiskScoreHistoryItem(BaseModel):
    id: str
    final_trust_score: float
    decision: str
    component_scores: dict
    created_at: datetime


class RiskScoreHistoryResponse(BaseModel):
    total: int
    items: list[RiskScoreHistoryItem]


# ─────────────────────────────────────────────────────────────────────────────
# COMPUTE RISK SCORE
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/score",
    response_model=RiskScoreResponse,
    summary="Compute NeoFace Trust Score",
    status_code=status.HTTP_200_OK,
)
async def compute_risk_score(
    body: RiskScoreRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RiskScoreResponse:
    """
    Compute the NeoFace Trust Score — a composite biometric risk assessment.

    **Input:** One or more component scores (0–100 each). All inputs are optional;
    the engine will re-normalize weights for any missing signals.

    **Decision Rules:**
    - **90–100** → `approve` — High confidence, allow the action
    - **70–89**  → `step_up` — Request additional authentication factor
    - **< 70**   → `reject`  — Block the transaction or session

    **Hard Block Conditions** (override score regardless of value):
    - Deepfake probability > 95% → immediate reject
    - Liveness score < 10% → immediate reject
    - Device trust = 0 (rooted/compromised device) → immediate reject
    """
    inp = RiskScoreInput(
        face_score=body.face_score,
        liveness_score=body.liveness_score,
        deepfake_score=body.deepfake_score,
        behavior_score=body.behavior_score,
        device_trust_score=body.device_trust_score,
        location_trust=body.location_trust,
        fingerprint_trust=body.fingerprint_trust,
        session_id=body.session_id,
        user_id=str(current_user.user_uuid),
        ip_address=request.client.host if request.client else None,
        device_id=request.headers.get("x-device-id"),
        transaction_amount=body.transaction_amount,
    )

    result = _risk_svc.compute(inp, custom_weights=body.custom_weights)

    # Resolve transaction_id
    txn_id = None
    if body.transaction_id:
        try:
            txn_id = uuid.UUID(body.transaction_id)
        except ValueError:
            pass

    # Persist to risk_scores table
    score_id = None
    try:
        score_record = RiskScoreModel(
            user_id=current_user.user_uuid,
            session_id=body.session_id,
            transaction_id=txn_id,
            face_score=body.face_score,
            liveness_score=body.liveness_score,
            deepfake_score=body.deepfake_score,
            behavior_score=body.behavior_score,
            device_trust_score=body.device_trust_score,
            location_trust=body.location_trust,
            fingerprint_trust_score=body.fingerprint_trust,
            final_trust_score=result.final_trust_score,
            decision=result.decision,
            weights_snapshot=result.weights_used,
            ip_address=request.client.host if request.client else None,
            device_id=request.headers.get("x-device-id"),
        )
        db.add(score_record)
        await db.commit()
        await db.refresh(score_record)
        score_id = str(score_record.id)
    except Exception as exc:
        logger.warning("risk.score: persist failed", error=str(exc))

    return RiskScoreResponse(
        final_trust_score=result.final_trust_score,
        decision=result.decision,
        component_scores=ComponentScoresResponse(
            face_score=body.face_score,
            liveness_score=body.liveness_score,
            deepfake_score=body.deepfake_score,
            behavior_score=body.behavior_score,
            device_trust_score=body.device_trust_score,
            location_trust=body.location_trust,
            fingerprint_trust=body.fingerprint_trust,
        ),
        weights_used=result.weights_used,
        contributing_factors=result.contributing_factors,
        hard_blocked=result.hard_blocked,
        hard_block_reason=result.hard_block_reason,
        risk_flags=result.risk_flags,
        explanation=result.explanation,
        score_id=score_id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# RISK SCORE HISTORY
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/history",
    response_model=RiskScoreHistoryResponse,
    summary="Risk score history for authenticated user",
)
async def get_risk_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RiskScoreHistoryResponse:
    """Retrieve paginated risk score history for the authenticated user."""
    offset = (page - 1) * page_size

    count_q = select(RiskScoreModel).where(RiskScoreModel.user_id == current_user.user_uuid)
    from sqlalchemy import func as sqlfunc
    total_q = select(sqlfunc.count()).select_from(count_q.subquery())
    total_result = await db.execute(total_q)
    total = total_result.scalar_one_or_none() or 0

    items_q = (
        select(RiskScoreModel)
        .where(RiskScoreModel.user_id == current_user.user_uuid)
        .order_by(desc(RiskScoreModel.created_at))
        .offset(offset)
        .limit(page_size)
    )
    items_result = await db.execute(items_q)
    items = items_result.scalars().all()

    return RiskScoreHistoryResponse(
        total=total,
        items=[
            RiskScoreHistoryItem(
                id=str(s.id),
                final_trust_score=s.final_trust_score,
                decision=s.decision,
                component_scores={
                    "face": s.face_score,
                    "liveness": s.liveness_score,
                    "deepfake": s.deepfake_score,
                    "behavior": s.behavior_score,
                    "device": s.device_trust_score,
                },
                created_at=s.created_at,
            )
            for s in items
        ],
    )
