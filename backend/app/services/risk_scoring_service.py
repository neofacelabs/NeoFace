"""
NeoFace Trust Engine — Risk Scoring Engine (Module 11)
Computes the NeoFace Trust Score — a composite 0–100 risk assessment.

Inputs:
  face_score         — ArcFace similarity (0–100)
  liveness_score     — Passive liveness probability (0–100)
  deepfake_score     — Inverted deepfake probability (0–100, higher = safer)
  behavior_score     — Behavioral biometrics score (0–100)
  device_trust_score — Device integrity score (0–100)
  location_trust     — IP/geo trust score (0–100)
  fingerprint_trust  — Fingerprint/WebAuthn score (0–100)

Decision Rules:
  90–100: approve         — High confidence, no friction
  70–89:  step_up         — Request additional authentication factor
  <70:    reject          — Block the transaction/session

API: POST /api/risk/score
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.logging import logger

# ── Default component weights (must sum to 1.0) ───────────────────────────────
DEFAULT_WEIGHTS: dict[str, float] = {
    "face_score":          0.25,
    "liveness_score":      0.20,
    "deepfake_score":      0.15,
    "behavior_score":      0.15,
    "device_trust_score":  0.15,
    "location_trust":      0.05,
    "fingerprint_trust":   0.05,
}

# ── Decision thresholds ────────────────────────────────────────────────────────
THRESHOLD_APPROVE  = 90.0
THRESHOLD_STEP_UP  = 70.0

# ── Hard-block conditions (immediately reject regardless of score) ─────────────
HARD_BLOCK_CONDITIONS = {
    "deepfake_score":       5.0,   # Deepfake probability > 95% → always reject
    "liveness_score":       10.0,  # Liveness clearly failed → reject
    "device_trust_score":   0.0,   # Zero device trust → reject
}


@dataclass
class RiskScoreInput:
    """
    All biometric and contextual signals fed into the risk engine.
    Each component is on a 0–100 scale. None = not available.
    """
    # Core biometric signals
    face_score: float | None = None           # ArcFace match confidence 0–100
    liveness_score: float | None = None       # Passive liveness 0–100
    deepfake_score: float | None = None       # 100 - (deepfake_prob * 100) — higher=safer
    behavior_score: float | None = None       # Behavioral biometrics 0–100
    device_trust_score: float | None = None   # Device integrity 0–100
    location_trust: float | None = None       # Geo/IP trust 0–100
    fingerprint_trust: float | None = None    # WebAuthn/fingerprint 0–100

    # Additional context (not scored, used for flagging)
    session_id: str | None = None
    user_id: str | None = None
    ip_address: str | None = None
    device_id: str | None = None
    transaction_amount: float | None = None


@dataclass
class RiskScoreResult:
    """Final NeoFace Trust Score and decision."""
    final_trust_score: float       # 0–100
    decision: str                  # approve | step_up | reject
    component_scores: dict[str, float | None]
    weights_used: dict[str, float]
    contributing_factors: int      # Number of signals that contributed
    hard_blocked: bool = False
    hard_block_reason: str | None = None
    risk_flags: list[str] = field(default_factory=list)
    explanation: str = ""


class RiskScoringService:
    """
    Stateless NeoFace Trust Score engine.

    Combines biometric, behavioral, device, and contextual signals into
    a single trust score. Supports dynamic weight configuration.

    Usage:
        service = RiskScoringService()
        result = service.compute(RiskScoreInput(...))
    """

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self._validate_weights()

    def _validate_weights(self) -> None:
        """Normalize weights to sum to 1.0."""
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-6 and total > 0:
            self.weights = {k: v / total for k, v in self.weights.items()}

    # ── Hard-block check ──────────────────────────────────────────────────────

    def _check_hard_blocks(self, inp: RiskScoreInput) -> tuple[bool, str | None]:
        """
        Check for immediate rejection conditions regardless of composite score.
        Returns (should_block, reason).
        """
        # Deepfake detected
        if inp.deepfake_score is not None and inp.deepfake_score <= HARD_BLOCK_CONDITIONS["deepfake_score"]:
            return True, "deepfake_detected"

        # Liveness clearly failed
        if inp.liveness_score is not None and inp.liveness_score <= HARD_BLOCK_CONDITIONS["liveness_score"]:
            return True, "liveness_failed"

        # Zero device trust (rooted/compromised device)
        if inp.device_trust_score is not None and inp.device_trust_score <= HARD_BLOCK_CONDITIONS["device_trust_score"]:
            return True, "compromised_device"

        return False, None

    # ── Score computation ─────────────────────────────────────────────────────

    def compute(
        self,
        inp: RiskScoreInput,
        custom_weights: dict[str, float] | None = None,
    ) -> RiskScoreResult:
        """
        Compute the NeoFace Trust Score from all available signals.

        Args:
            inp:            RiskScoreInput with component scores.
            custom_weights: Optional per-request weight override.

        Returns:
            RiskScoreResult with final_trust_score and decision.
        """
        weights = custom_weights or self.weights
        if custom_weights:
            total = sum(weights.values())
            if abs(total - 1.0) > 1e-6 and total > 0:
                weights = {k: v / total for k, v in weights.items()}

        # Component score dict (raw values from input)
        raw_scores: dict[str, float | None] = {
            "face_score":          inp.face_score,
            "liveness_score":      inp.liveness_score,
            "deepfake_score":      inp.deepfake_score,
            "behavior_score":      inp.behavior_score,
            "device_trust_score":  inp.device_trust_score,
            "location_trust":      inp.location_trust,
            "fingerprint_trust":   inp.fingerprint_trust,
        }

        risk_flags: list[str] = []

        # ── Hard block check ──────────────────────────────────────────────────
        blocked, block_reason = self._check_hard_blocks(inp)
        if blocked:
            logger.warning(
                "risk_scoring.hard_block",
                reason=block_reason,
                user_id=inp.user_id,
                session_id=inp.session_id,
            )
            return RiskScoreResult(
                final_trust_score=0.0,
                decision="reject",
                component_scores=raw_scores,
                weights_used=weights,
                contributing_factors=0,
                hard_blocked=True,
                hard_block_reason=block_reason,
                risk_flags=[f"hard_block:{block_reason}"],
                explanation=f"Hard block: {block_reason}",
            )

        # ── Collect available (non-None) signals ──────────────────────────────
        available: dict[str, float] = {}
        for key, value in raw_scores.items():
            if value is not None:
                # Clamp to [0, 100]
                clamped = float(max(0.0, min(100.0, value)))
                available[key] = clamped

                # Flag low individual scores
                if clamped < 50.0:
                    risk_flags.append(f"low_{key}:{clamped:.0f}")

        if not available:
            return RiskScoreResult(
                final_trust_score=50.0,
                decision="step_up",
                component_scores=raw_scores,
                weights_used=weights,
                contributing_factors=0,
                risk_flags=["no_signals_available"],
                explanation="No biometric signals provided",
            )

        # ── Re-normalize weights for present components ───────────────────────
        active_weights = {k: weights.get(k, 0.0) for k in available}
        total_w = sum(active_weights.values())
        if total_w < 1e-9:
            # All present components have zero weight — equal weighting
            active_weights = {k: 1.0 / len(available) for k in available}
            total_w = 1.0
        else:
            active_weights = {k: v / total_w for k, v in active_weights.items()}

        # ── Compute weighted composite ────────────────────────────────────────
        final_score = sum(available[k] * active_weights[k] for k in available)
        final_score = round(float(final_score), 2)

        # ── Amount-based adjustment (high-value transactions require higher score) ─
        if inp.transaction_amount is not None and inp.transaction_amount > 1000:
            # For transactions over $1000, increase threshold by 5 points effectively
            # by boosting minimum required score
            if final_score < 85.0:
                risk_flags.append(f"high_value_transaction:{inp.transaction_amount:.2f}")
                final_score = max(0.0, final_score - 5.0)  # Penalize slightly

        # ── Decision ──────────────────────────────────────────────────────────
        if final_score >= THRESHOLD_APPROVE:
            decision = "approve"
        elif final_score >= THRESHOLD_STEP_UP:
            decision = "step_up"
        else:
            decision = "reject"

        # ── Build explanation ─────────────────────────────────────────────────
        top_contributors = sorted(
            [(k, available[k] * active_weights[k]) for k in available],
            key=lambda x: x[1], reverse=True,
        )[:3]
        explanation = (
            f"Trust score {final_score:.1f} ({decision}). "
            f"Top factors: {', '.join(f'{k}={available[k]:.0f}' for k, _ in top_contributors)}"
        )

        logger.info(
            "risk_scoring.compute",
            score=final_score,
            decision=decision,
            user_id=inp.user_id,
            contributing=len(available),
            flags=risk_flags[:3],
        )

        return RiskScoreResult(
            final_trust_score=final_score,
            decision=decision,
            component_scores=raw_scores,
            weights_used=active_weights,
            contributing_factors=len(available),
            hard_blocked=False,
            risk_flags=risk_flags,
            explanation=explanation,
        )
