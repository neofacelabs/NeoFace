"""
NeoFace Biometric Fusion Engine
Score-level fusion combining face, iris, and fingerprint match scores
into a single authorization decision for biometric payments.

Fusion formula:
    S_fusion = w_face * S_face + w_iris * S_iris + w_fingerprint * S_fingerprint

Where all weights sum to 1.0. Missing modalities are excluded and
weights are re-normalized automatically.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# ── Default modality weights ───────────────────────────────────────────────────
DEFAULT_WEIGHTS = {
    "face": 0.45,
    "iris": 0.35,
    "fingerprint": 0.20,
}

# ── Fusion authorization threshold ────────────────────────────────────────────
DEFAULT_FUSION_THRESHOLD = 0.60  # Fusion score >= 0.60 → authorize payment

# ── Single-modality thresholds (for fallback decisions) ───────────────────────
FACE_SCORE_THRESHOLD = 0.65       # ArcFace cosine similarity (0–1)
IRIS_MATCH_THRESHOLD = 0.68       # Iris match_score (0–1, derived from HD)
FINGERPRINT_MATCH_THRESHOLD = 0.40


@dataclass
class BiometricSignals:
    """
    Container for all available biometric match signals for a single
    payment authorization attempt. Any field left as None means that
    modality was not presented or not enrolled.
    """
    # ── Face ──────────────────────────────────────────────────────────────────
    face_similarity_score: float | None = None     # 0.0–1.0 (ArcFace cosine)
    face_liveness_score: float | None = None       # 0.0–100.0
    face_liveness_passed: bool = False
    face_anti_spoof_passed: bool = False
    face_blink_detected: bool = False
    face_head_turn_detected: bool = False

    # ── Iris ──────────────────────────────────────────────────────────────────
    iris_match_score: float | None = None          # 0.0–1.0 (derived from HD)
    iris_hamming_distance: float | None = None     # 0.0–1.0 (lower = better)
    iris_quality_score: float | None = None        # 0.0–100.0
    iris_matched_user_id: str | None = None

    # ── Fingerprint ───────────────────────────────────────────────────────────
    fingerprint_match_score: float | None = None   # 0.0–1.0
    fingerprint_minutiae_pairs: int = 0
    fingerprint_matched_user_id: str | None = None

    # ── Context ───────────────────────────────────────────────────────────────
    requested_modality: str = "face"               # face | iris | fingerprint | multi_modal
    face_user_id: str | None = None                # User resolved from face match


@dataclass
class FusionDecision:
    """
    Final authorization decision from the biometric fusion engine.
    """
    authorized: bool
    fusion_score: float            # 0.0–1.0 composite score
    threshold_used: float
    resolved_user_id: str | None   # Confirmed user ID after cross-modal consistency check
    modalities_used: list[str]     # Which modalities contributed to the decision
    failure_reason: str | None     # Human-readable reason if not authorized
    is_liveness_passed: bool

    # Per-modality normalized scores (for audit log)
    face_score_normalized: float | None = None
    iris_score_normalized: float | None = None
    fingerprint_score_normalized: float | None = None


class BiometricFusionEngine:
    """
    Score-level biometric fusion engine.

    Supports flexible modality combinations:
    - Face only (existing behavior)
    - Iris only
    - Fingerprint only
    - Face + Iris (2-factor)
    - Face + Fingerprint (2-factor)
    - Face + Iris + Fingerprint (3-factor, maximum security)
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        fusion_threshold: float = DEFAULT_FUSION_THRESHOLD,
    ) -> None:
        self.weights = weights or DEFAULT_WEIGHTS.copy()
        self.fusion_threshold = fusion_threshold
        self._validate_weights()

    def _validate_weights(self) -> None:
        total = sum(self.weights.values())
        if abs(total - 1.0) > 1e-6:
            # Normalize to sum to 1.0
            self.weights = {k: v / total for k, v in self.weights.items()}

    # ── Score normalization ────────────────────────────────────────────────────

    @staticmethod
    def _normalize_face_score(raw: float) -> float:
        """Normalize ArcFace cosine similarity (0–1) to fusion score range (0–1)."""
        return float(max(0.0, min(1.0, raw)))

    @staticmethod
    def _normalize_iris_score(raw: float) -> float:
        """Normalize iris match score (already 0–1) to fusion range."""
        return float(max(0.0, min(1.0, raw)))

    @staticmethod
    def _normalize_fingerprint_score(raw: float) -> float:
        """Normalize fingerprint match score (0–1) to fusion range."""
        return float(max(0.0, min(1.0, raw)))

    # ── Consistency check ─────────────────────────────────────────────────────

    @staticmethod
    def _check_user_consistency(signals: BiometricSignals) -> tuple[str | None, str | None]:
        """
        Verify that multiple modalities resolved to the same user.
        Returns (resolved_user_id, failure_reason).
        If identities are inconsistent → block the payment.
        """
        ids = []
        if signals.face_user_id:
            ids.append(signals.face_user_id)
        if signals.iris_matched_user_id:
            ids.append(signals.iris_matched_user_id)
        if signals.fingerprint_matched_user_id:
            ids.append(signals.fingerprint_matched_user_id)

        if not ids:
            return None, "no_biometric_match"

        unique_ids = set(ids)
        if len(unique_ids) > 1:
            return None, "identity_mismatch_across_modalities"

        return ids[0], None

    # ── Main fusion logic ─────────────────────────────────────────────────────

    def evaluate(self, signals: BiometricSignals) -> FusionDecision:
        """
        Evaluate all available biometric signals and return an authorization decision.

        Pipeline:
        1. Liveness gate — at least one modality must pass anti-spoofing
        2. Score normalization for each available modality
        3. Weight re-normalization for missing modalities
        4. Compute weighted fusion score
        5. Cross-modal identity consistency check (if >1 modality)
        6. Apply fusion threshold
        """
        modalities_used: list[str] = []
        normalized_scores: dict[str, float] = {}

        # ── Step 1: Collect available scores ──────────────────────────────────
        if signals.face_similarity_score is not None:
            n = self._normalize_face_score(signals.face_similarity_score)
            normalized_scores["face"] = n
            modalities_used.append("face")

        if signals.iris_match_score is not None:
            n = self._normalize_iris_score(signals.iris_match_score)
            normalized_scores["iris"] = n
            modalities_used.append("iris")

        if signals.fingerprint_match_score is not None:
            n = self._normalize_fingerprint_score(signals.fingerprint_match_score)
            normalized_scores["fingerprint"] = n
            modalities_used.append("fingerprint")

        if not modalities_used:
            return FusionDecision(
                authorized=False,
                fusion_score=0.0,
                threshold_used=self.fusion_threshold,
                resolved_user_id=None,
                modalities_used=[],
                failure_reason="no_biometric_signals",
                is_liveness_passed=False,
            )

        # ── Step 2: Liveness gate ─────────────────────────────────────────────
        liveness_ok = False
        if "face" in modalities_used:
            liveness_ok = signals.face_liveness_passed or signals.face_anti_spoof_passed

        # If only iris/fingerprint (no face liveness), treat as hardware-captured (trusted)
        if not liveness_ok and "face" not in modalities_used:
            liveness_ok = True  # hardware scanner is treated as live

        # ── Step 3: Re-normalize weights for present modalities ───────────────
        active_weights = {m: self.weights.get(m, 0.0) for m in modalities_used}
        total_w = sum(active_weights.values())
        if total_w == 0:
            return FusionDecision(
                authorized=False, fusion_score=0.0,
                threshold_used=self.fusion_threshold,
                resolved_user_id=None, modalities_used=modalities_used,
                failure_reason="no_weights_configured",
                is_liveness_passed=liveness_ok,
            )
        active_weights = {m: w / total_w for m, w in active_weights.items()}

        # ── Step 4: Compute fusion score ──────────────────────────────────────
        fusion_score = sum(
            normalized_scores[m] * active_weights[m]
            for m in modalities_used
        )
        fusion_score = round(float(fusion_score), 4)

        # ── Step 5: Identity consistency check ────────────────────────────────
        resolved_user_id, consistency_failure = self._check_user_consistency(signals)
        if consistency_failure:
            return FusionDecision(
                authorized=False,
                fusion_score=fusion_score,
                threshold_used=self.fusion_threshold,
                resolved_user_id=None,
                modalities_used=modalities_used,
                failure_reason=consistency_failure,
                is_liveness_passed=liveness_ok,
                face_score_normalized=normalized_scores.get("face"),
                iris_score_normalized=normalized_scores.get("iris"),
                fingerprint_score_normalized=normalized_scores.get("fingerprint"),
            )

        # ── Step 6: Threshold decision ────────────────────────────────────────
        authorized = fusion_score >= self.fusion_threshold and liveness_ok

        failure_reason: str | None = None
        if not authorized:
            if not liveness_ok:
                failure_reason = "liveness_check_failed"
            elif fusion_score < self.fusion_threshold:
                failure_reason = f"fusion_score_below_threshold ({fusion_score:.3f} < {self.fusion_threshold})"

        logger.info(
            "BiometricFusion.evaluate",
            authorized=authorized,
            fusion_score=fusion_score,
            modalities=modalities_used,
            resolved_user=resolved_user_id,
        )

        return FusionDecision(
            authorized=authorized,
            fusion_score=fusion_score,
            threshold_used=self.fusion_threshold,
            resolved_user_id=resolved_user_id,
            modalities_used=modalities_used,
            failure_reason=failure_reason,
            is_liveness_passed=liveness_ok,
            face_score_normalized=normalized_scores.get("face"),
            iris_score_normalized=normalized_scores.get("iris"),
            fingerprint_score_normalized=normalized_scores.get("fingerprint"),
        )

    # ── Singleton ─────────────────────────────────────────────────────────────
    _instance: "BiometricFusionEngine | None" = None

    @classmethod
    def get_instance(cls) -> "BiometricFusionEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
