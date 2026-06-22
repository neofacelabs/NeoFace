"""
NeoFace Trust Engine — Biometric Trust Engine (Module 7)

Combines all biometric signals into a single trust assessment:
  - Face similarity (ArcFace, 0–100)
  - Liveness score (Passive liveness, 0–100)
  - Deepfake score (Anti-deepfake, 0–100 where 100=safe)

Outputs comprehensive biometric trust assessment with quality levels and recommendations.

Design: Production-grade multimodal biometric fusion with clear recommendations.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from app.core.logging import logger


class BiometricQualityLevel(str, Enum):
    """Quality assessment of biometric signals."""
    
    EXCELLENT = "excellent"      # > 90%
    ACCEPTABLE = "acceptable"    # 80–90%
    MARGINAL = "marginal"        # 60–80%
    POOR = "poor"                # < 60%


class BiometricRecommendation(str, Enum):
    """Recommended action based on biometric signals."""
    
    APPROVE = "approve"          # High confidence, approve immediately
    STEP_UP = "step_up"          # Request additional factor (OTP, etc.)
    CHALLENGE = "challenge"      # Require liveness challenge or re-scan
    REJECT = "reject"            # Reject due to poor/no biometric match


@dataclass
class BiometricSignals:
    """Individual biometric signal scores."""
    
    face_similarity: float | None      # 0–100, ArcFace confidence
    liveness_score: float | None       # 0–100, passive liveness
    deepfake_score: float | None       # 0–100, anti-deepfake (100=safe)
    
    # Optional multi-modal signals
    iris_similarity: float | None = None      # 0–100
    fingerprint_similarity: float | None = None  # 0–100
    voice_similarity: float | None = None     # 0–100


@dataclass
class BiometricTrustResult:
    """Output from biometric trust assessment."""
    
    overall_trust_score: float                   # 0.0–1.0 normalized
    overall_trust_percentage: float              # 0–100%
    biometric_decision: str                      # approve | step_up | challenge | reject
    recommendation: BiometricRecommendation
    
    # Component assessments
    face_quality: BiometricQualityLevel
    liveness_quality: BiometricQualityLevel
    deepfake_quality: BiometricQualityLevel
    
    # Detailed scores
    face_score: float                            # 0–100
    liveness_score: float                        # 0–100
    deepfake_confidence: float                   # 0–100
    
    # Explanation and flags
    explanation: str
    risk_factors: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    
    # Thresholds applied
    face_threshold_met: bool = False
    liveness_threshold_met: bool = False
    deepfake_threshold_met: bool = False
    
    # Confidence in decision
    decision_confidence: float = 0.0             # 0–1.0


class BiometricTrustEngine:
    """
    Comprehensive biometric trust assessment.
    
    Combines face recognition, liveness detection, and deepfake detection
    into a single trust decision suitable for:
      - Payment authentication
      - Identity verification
      - Access control
      - Enterprise authentication
    
    Stateless service — all signals are inputs.
    """

    # Decision thresholds (0–100 scale)
    FACE_THRESHOLD_STRICT = 85.0      # High confidence
    FACE_THRESHOLD_MODERATE = 75.0    # Acceptable
    LIVENESS_THRESHOLD = 70.0         # Minimum passive liveness
    DEEPFAKE_THRESHOLD = 80.0         # Minimum anti-deepfake (100=safe)

    # Quality level cutoffs
    QUALITY_EXCELLENT = 90.0
    QUALITY_ACCEPTABLE = 80.0
    QUALITY_MARGINAL = 60.0

    # Weights for composite scoring (must sum to 1.0)
    WEIGHT_FACE = 0.50
    WEIGHT_LIVENESS = 0.30
    WEIGHT_DEEPFAKE = 0.20

    @staticmethod
    def assess_biometric_trust(signals: BiometricSignals) -> BiometricTrustResult:
        """
        Assess overall biometric trust from component signals.
        
        Args:
            signals: Individual biometric signal scores (any may be None).
            
        Returns:
            BiometricTrustResult with trust score and recommendation.
        """
        # Normalize all signals to 0–100 range (with None handling)
        face_score = max(0.0, min(100.0, signals.face_similarity or 0.0))
        liveness_score = max(0.0, min(100.0, signals.liveness_score or 0.0))
        deepfake_score = max(0.0, min(100.0, signals.deepfake_score or 0.0))

        # Collect available signals
        available_signals = []
        if signals.face_similarity is not None:
            available_signals.append("face")
        if signals.liveness_score is not None:
            available_signals.append("liveness")
        if signals.deepfake_score is not None:
            available_signals.append("deepfake")

        if not available_signals:
            return BiometricTrustEngine._no_signals_result()

        # ── Assess individual signal quality ──────────────────────────────────
        face_quality = BiometricTrustEngine._assess_quality(face_score)
        liveness_quality = BiometricTrustEngine._assess_quality(liveness_score)
        deepfake_quality = BiometricTrustEngine._assess_quality(deepfake_score)

        # ── Check threshold compliance ─────────────────────────────────────────
        face_passed = signals.face_similarity is not None and face_score >= BiometricTrustEngine.FACE_THRESHOLD_MODERATE
        liveness_passed = signals.liveness_score is not None and liveness_score >= BiometricTrustEngine.LIVENESS_THRESHOLD
        deepfake_passed = signals.deepfake_score is not None and deepfake_score >= BiometricTrustEngine.DEEPFAKE_THRESHOLD

        # ── Collect risk factors and strengths ────────────────────────────────
        risk_factors: list[str] = []
        strengths: list[str] = []

        if signals.face_similarity is not None:
            if face_score > BiometricTrustEngine.FACE_THRESHOLD_STRICT:
                strengths.append(f"excellent_face_match:{face_score:.0f}%")
            elif face_score >= BiometricTrustEngine.FACE_THRESHOLD_MODERATE:
                strengths.append(f"acceptable_face_match:{face_score:.0f}%")
            else:
                risk_factors.append(f"poor_face_match:{face_score:.0f}%")

        if signals.liveness_score is not None:
            if liveness_score >= 85.0:
                strengths.append(f"high_liveness_confidence:{liveness_score:.0f}%")
            elif liveness_score >= BiometricTrustEngine.LIVENESS_THRESHOLD:
                strengths.append(f"acceptable_liveness:{liveness_score:.0f}%")
            else:
                risk_factors.append(f"liveness_concern:{liveness_score:.0f}%")

        if signals.deepfake_score is not None:
            if deepfake_score > 95.0:
                strengths.append("high_deepfake_confidence")
            elif deepfake_score >= BiometricTrustEngine.DEEPFAKE_THRESHOLD:
                strengths.append("acceptable_deepfake_check")
            else:
                risk_factors.append(f"deepfake_concern:{deepfake_score:.0f}%")

        # ── Compute composite trust score ──────────────────────────────────────
        # Only weight available signals
        weighted_sum = 0.0
        total_weight = 0.0

        if signals.face_similarity is not None:
            weighted_sum += BiometricTrustEngine.WEIGHT_FACE * (face_score / 100.0)
            total_weight += BiometricTrustEngine.WEIGHT_FACE
        if signals.liveness_score is not None:
            weighted_sum += BiometricTrustEngine.WEIGHT_LIVENESS * (liveness_score / 100.0)
            total_weight += BiometricTrustEngine.WEIGHT_LIVENESS
        if signals.deepfake_score is not None:
            weighted_sum += BiometricTrustEngine.WEIGHT_DEEPFAKE * (deepfake_score / 100.0)
            total_weight += BiometricTrustEngine.WEIGHT_DEEPFAKE

        # Normalize by available weights
        if total_weight > 0:
            overall_trust_normalized = weighted_sum / total_weight
        else:
            overall_trust_normalized = 0.0

        overall_trust_percentage = overall_trust_normalized * 100.0

        # ── Make decision ───────────────────────────────────────────────────────
        decision, recommendation = BiometricTrustEngine._make_decision(
            overall_trust_percentage,
            face_passed,
            liveness_passed,
            deepfake_passed,
            available_signals,
            risk_factors,
        )

        # ── Compute decision confidence (how certain are we) ──────────────────
        decision_confidence = BiometricTrustEngine._calculate_confidence(
            overall_trust_percentage, available_signals
        )

        # ── Build explanation ────────────────────────────────────────────────
        explanation = BiometricTrustEngine._build_explanation(
            decision, overall_trust_percentage, available_signals, risk_factors
        )

        logger.info(
            "biometric_trust.assess",
            overall_score=round(overall_trust_percentage, 1),
            decision=decision,
            available_signals=available_signals,
            risk_factors=risk_factors[:3],
            strengths=strengths[:3],
        )

        return BiometricTrustResult(
            overall_trust_score=overall_trust_normalized,
            overall_trust_percentage=round(overall_trust_percentage, 2),
            biometric_decision=decision,
            recommendation=recommendation,
            face_quality=face_quality,
            liveness_quality=liveness_quality,
            deepfake_quality=deepfake_quality,
            face_score=round(face_score, 2),
            liveness_score=round(liveness_score, 2),
            deepfake_confidence=round(deepfake_score, 2),
            explanation=explanation,
            risk_factors=risk_factors,
            strengths=strengths,
            face_threshold_met=face_passed,
            liveness_threshold_met=liveness_passed,
            deepfake_threshold_met=deepfake_passed,
            decision_confidence=decision_confidence,
        )

    @staticmethod
    def _assess_quality(score: float) -> BiometricQualityLevel:
        """Classify signal quality based on score."""
        if score >= BiometricTrustEngine.QUALITY_EXCELLENT:
            return BiometricQualityLevel.EXCELLENT
        elif score >= BiometricTrustEngine.QUALITY_ACCEPTABLE:
            return BiometricQualityLevel.ACCEPTABLE
        elif score >= BiometricTrustEngine.QUALITY_MARGINAL:
            return BiometricQualityLevel.MARGINAL
        else:
            return BiometricQualityLevel.POOR

    @staticmethod
    def _make_decision(
        trust_score: float,
        face_passed: bool,
        liveness_passed: bool,
        deepfake_passed: bool,
        available_signals: list[str],
        risk_factors: list[str],
    ) -> tuple[str, BiometricRecommendation]:
        """Determine accept/reject decision and recommendation."""
        
        # Hard rejection conditions
        if trust_score < 30.0:
            return "reject", BiometricRecommendation.REJECT
        
        # If only one signal available and it's insufficient
        if len(available_signals) == 1:
            if "face" in available_signals and not face_passed:
                return "reject", BiometricRecommendation.REJECT
            if "liveness" in available_signals and not liveness_passed:
                return "challenge", BiometricRecommendation.CHALLENGE

        # Multi-signal decision
        if trust_score >= 85.0 and face_passed and deepfake_passed:
            return "approve", BiometricRecommendation.APPROVE
        elif trust_score >= 75.0 and face_passed:
            return "step_up", BiometricRecommendation.STEP_UP
        elif trust_score >= 60.0:
            if not liveness_passed:
                return "challenge", BiometricRecommendation.CHALLENGE
            else:
                return "step_up", BiometricRecommendation.STEP_UP
        else:
            return "reject", BiometricRecommendation.REJECT

    @staticmethod
    def _calculate_confidence(trust_score: float, available_signals: list[str]) -> float:
        """Calculate confidence in the decision (0–1.0)."""
        # Base confidence on score
        base_confidence = min(trust_score / 100.0, 1.0)
        
        # Boost confidence if multiple signals available
        signal_multiplier = 0.8 + (0.2 * (len(available_signals) - 1) / 2.0)
        
        return min(base_confidence * signal_multiplier, 1.0)

    @staticmethod
    def _build_explanation(
        decision: str,
        trust_score: float,
        available_signals: list[str],
        risk_factors: list[str],
    ) -> str:
        """Build human-readable explanation."""
        signal_desc = ", ".join(available_signals) if available_signals else "none"
        
        reason = ""
        if trust_score >= 85.0:
            reason = "high confidence biometric match"
        elif trust_score >= 75.0:
            reason = "acceptable biometric match, additional verification recommended"
        elif trust_score >= 60.0:
            reason = "marginal biometric quality, additional factors required"
        else:
            reason = "insufficient biometric confidence"
        
        if risk_factors:
            risk_desc = "; ".join(risk_factors[:2])
            return f"{decision.upper()}: {reason} (signals: {signal_desc}, concerns: {risk_desc})"
        else:
            return f"{decision.upper()}: {reason} (signals: {signal_desc})"

    @staticmethod
    def _no_signals_result() -> BiometricTrustResult:
        """Result when no biometric signals are available."""
        return BiometricTrustResult(
            overall_trust_score=0.0,
            overall_trust_percentage=0.0,
            biometric_decision="reject",
            recommendation=BiometricRecommendation.REJECT,
            face_quality=BiometricQualityLevel.POOR,
            liveness_quality=BiometricQualityLevel.POOR,
            deepfake_quality=BiometricQualityLevel.POOR,
            face_score=0.0,
            liveness_score=0.0,
            deepfake_confidence=0.0,
            explanation="REJECT: No biometric signals provided",
            risk_factors=["no_biometric_signals"],
            decision_confidence=1.0,
        )
