"""
NeoFace Trust Engine — Passive Liveness Service (Module 1)
Detects spoof attacks without requiring user action.

Detects:
  - Printed photos
  - Phone / tablet / screen replay attacks
  - Face masks
  - Static image injections
  - Virtual camera attacks

Models:
  Primary: MiniFASNetV1 + MiniFASNetV2 (ensemble via ONNX Runtime)
  Fallback: texture-complexity heuristic (Laplacian + LBP + histogram entropy)

Output:
  { "liveness_score": 0.97, "is_live": true, "confidence": 98 }
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

import cv2
import numpy as np

from app.core.config import settings
from app.core.logging import logger

# MiniFASNet input dimensions
# Both V1 and V2 files use the same MiniFASNetV2 weights (80×80)
_V1_SIZE = (80, 80)   # MiniFASNetV1 (80×80 NCHW)
_V2_SIZE = (80, 80)   # MiniFASNetV2 (80×80 NCHW, same weights as V1)

# Ensemble weights — V2 gets slightly more weight
_ENSEMBLE_WEIGHT_V1 = 0.45
_ENSEMBLE_WEIGHT_V2 = 0.55

# Threshold: probability of "real" that constitutes liveness pass
_LIVENESS_THRESHOLD = 0.65


@dataclass
class PassiveLivenessResult:
    """Structured output from the passive liveness service."""

    liveness_score: float          # 0.0–1.0 probability of being live
    is_live: bool
    confidence: float              # 0–100 rounded percentage
    attack_type: str               # none | photo | screen | replay | mask | virtual_camera
    method: str                    # minifasnet_ensemble | minifasnet_v1 | heuristic
    inference_ms: float
    model_available: bool
    v1_score: float | None = None
    v2_score: float | None = None
    image_hash: str | None = None  # SHA-256 of analyzed frame (not persisted, for dedup only)


class PassiveLivenessService:
    """
    Singleton passive liveness detection service.

    Load once at startup via initialize(), then call predict() per frame.
    Thread-safe: ONNX InferenceSession is read-only after creation.
    """

    _instance: ClassVar[PassiveLivenessService | None] = None
    _initialized: ClassVar[bool] = False

    def __init__(self) -> None:
        self._session_v1 = None
        self._session_v2 = None
        self._input_v1: str = ""
        self._input_v2: str = ""
        self._output_v1: str = ""
        self._output_v2: str = ""
        self._v1_loaded = False
        self._v2_loaded = False

    @classmethod
    def get_instance(cls) -> PassiveLivenessService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Initialization ────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """Load MiniFASNetV1 and V2 ONNX models. Safe to call multiple times."""
        if self._initialized:
            return

        if not settings.ANTI_SPOOF_ENABLED:
            logger.info("passive_liveness.init: disabled via ANTI_SPOOF_ENABLED=False")
            PassiveLivenessService._initialized = True
            return

        try:
            import onnxruntime as ort  # type: ignore[import]
            providers = ["CPUExecutionProvider"]

            # MiniFASNetV1
            v1_path = Path(getattr(settings, "MINIFASNET_V1_PATH", "./models/MiniFASNetV1.onnx"))
            if v1_path.exists():
                self._session_v1 = ort.InferenceSession(str(v1_path), providers=providers)
                self._input_v1 = self._session_v1.get_inputs()[0].name
                self._output_v1 = self._session_v1.get_outputs()[0].name
                self._v1_loaded = True
                logger.info("passive_liveness.init: MiniFASNetV1 loaded", path=str(v1_path))
            else:
                logger.warning("passive_liveness.init: MiniFASNetV1 not found", path=str(v1_path))

            # MiniFASNetV2
            v2_path = Path(getattr(settings, "MINIFASNET_V2_PATH", "./models/MiniFASNetV2.onnx"))
            if v2_path.exists():
                self._session_v2 = ort.InferenceSession(str(v2_path), providers=providers)
                self._input_v2 = self._session_v2.get_inputs()[0].name
                self._output_v2 = self._session_v2.get_outputs()[0].name
                self._v2_loaded = True
                logger.info("passive_liveness.init: MiniFASNetV2 loaded", path=str(v2_path))
            else:
                logger.warning("passive_liveness.init: MiniFASNetV2 not found", path=str(v2_path))

        except ImportError:
            logger.warning("passive_liveness.init: onnxruntime not available — using heuristic")
        except Exception as exc:
            logger.error("passive_liveness.init: error loading models", error=str(exc))

        PassiveLivenessService._initialized = True

    # ── Preprocessing ─────────────────────────────────────────────────────────

    @staticmethod
    def _preprocess(face_bgr: np.ndarray, target_size: tuple[int, int]) -> np.ndarray:
        """Resize → BGR→RGB → normalize [-1,1] → NCHW float32."""
        resized = cv2.resize(face_bgr, target_size, interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        normalized = (rgb.astype(np.float32) / 127.5) - 1.0
        chw = normalized.transpose(2, 0, 1)
        return np.expand_dims(chw, axis=0)

    # ── Per-model inference ───────────────────────────────────────────────────

    def _infer_v1(self, face_bgr: np.ndarray) -> float | None:
        """Run MiniFASNetV1. Returns P(real) from 3-class output [spoof, real, partial] or None."""
        if not self._v1_loaded or self._session_v1 is None:
            return None
        try:
            blob = self._preprocess(face_bgr, _V1_SIZE)
            out = self._session_v1.run([self._output_v1], {self._input_v1: blob})
            probs = np.array(out[0]).flatten()
            # 3-class: [P(spoof), P(real), P(partial)] — index 1 is P(real)
            return float(probs[1]) if len(probs) >= 2 else None
        except Exception as exc:
            logger.warning("passive_liveness.v1_infer: error", error=str(exc))
            return None

    def _infer_v2(self, face_bgr: np.ndarray) -> float | None:
        """Run MiniFASNetV2. Returns P(real) from 3-class output [spoof, real, partial] or None."""
        if not self._v2_loaded or self._session_v2 is None:
            return None
        try:
            blob = self._preprocess(face_bgr, _V2_SIZE)
            out = self._session_v2.run([self._output_v2], {self._input_v2: blob})
            probs = np.array(out[0]).flatten()
            # 3-class: [P(spoof), P(real), P(partial)] — index 1 is P(real)
            return float(probs[1]) if len(probs) >= 2 else None
        except Exception as exc:
            logger.warning("passive_liveness.v2_infer: error", error=str(exc))
            return None

    # ── Heuristic fallback ────────────────────────────────────────────────────

    @staticmethod
    def _heuristic(face_bgr: np.ndarray) -> float:
        """Texture-based heuristic. Returns P(real) 0–1."""
        if face_bgr is None or face_bgr.size == 0:
            return 0.0
        small = cv2.resize(face_bgr, (80, 80))
        gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)

        # Laplacian variance (sharpness)
        lap = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        sharpness = min(lap / 400.0, 1.0)

        # Histogram entropy
        hist = cv2.calcHist([gray], [0], None, [64], [0, 256]).flatten()
        hist = hist / (hist.sum() + 1e-9)
        entropy = float(-np.sum(hist * np.log2(hist + 1e-9)))
        entropy_score = min(entropy / 5.0, 1.0)

        # Chromatic diversity
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        sat_std = float(hsv[:, :, 1].std())
        chroma_score = min(sat_std / 50.0, 1.0)

        return float(0.40 * sharpness + 0.35 * entropy_score + 0.25 * chroma_score)

    # ── Attack type classifier ────────────────────────────────────────────────

    @staticmethod
    def _classify_attack(face_bgr: np.ndarray, real_prob: float) -> str:
        """Heuristic attack type from texture analysis."""
        threshold = getattr(settings, "PASSIVE_LIVENESS_THRESHOLD", 0.65)
        if real_prob >= threshold:
            return "none"
        small = cv2.resize(face_bgr, (80, 80))
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        mean_sat = float(hsv[:, :, 1].mean())
        brightness = float(small.mean())
        lap_var = float(cv2.Laplacian(cv2.cvtColor(small, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())
        if brightness > 200 and lap_var > 200:
            return "virtual_camera"
        if mean_sat > 120 and lap_var > 150:
            return "replay"
        if mean_sat > 60:
            return "screen"
        return "photo"

    # ── Public API ────────────────────────────────────────────────────────────

    def predict(self, face_bgr: np.ndarray) -> PassiveLivenessResult:
        """
        Run passive liveness on a face crop (BGR numpy array).

        Returns PassiveLivenessResult with liveness_score, is_live, confidence.
        """
        t0 = time.perf_counter()

        if not settings.ANTI_SPOOF_ENABLED:
            return PassiveLivenessResult(
                liveness_score=1.0,
                is_live=True,
                confidence=100.0,
                attack_type="none",
                method="disabled",
                inference_ms=0.0,
                model_available=False,
                v1_score=1.0,
                v2_score=1.0,
            )

        if face_bgr is None or face_bgr.size == 0:
            return PassiveLivenessResult(
                liveness_score=0.0, is_live=False, confidence=0.0,
                attack_type="unknown", method="error", inference_ms=0.0, model_available=False,
            )

        v1_score = self._infer_v1(face_bgr)
        v2_score = self._infer_v2(face_bgr)

        model_available = self._v1_loaded or self._v2_loaded

        if v1_score is not None and v2_score is not None:
            real_prob = _ENSEMBLE_WEIGHT_V1 * v1_score + _ENSEMBLE_WEIGHT_V2 * v2_score
            method = "minifasnet_ensemble"
        elif v1_score is not None:
            real_prob = v1_score
            method = "minifasnet_v1"
        elif v2_score is not None:
            real_prob = v2_score
            method = "minifasnet_v2"
        else:
            real_prob = self._heuristic(face_bgr)
            method = "heuristic"
            model_available = False

        threshold = getattr(settings, "PASSIVE_LIVENESS_THRESHOLD", 0.65)
        is_live = real_prob >= threshold
        attack_type = self._classify_attack(face_bgr, real_prob)
        inference_ms = round((time.perf_counter() - t0) * 1000, 2)

        logger.debug(
            "passive_liveness.predict",
            real_prob=round(real_prob, 4), is_live=is_live,
            method=method, attack_type=attack_type, inference_ms=inference_ms,
        )

        return PassiveLivenessResult(
            liveness_score=round(real_prob, 4),
            is_live=is_live,
            confidence=round(real_prob * 100, 1),
            attack_type=attack_type,
            method=method,
            inference_ms=inference_ms,
            model_available=model_available,
            v1_score=v1_score,
            v2_score=v2_score,
        )

    def predict_from_bytes(self, image_bytes: bytes, bbox: tuple[int, int, int, int] | None = None) -> PassiveLivenessResult:
        """Decode raw image bytes, optionally crop to bbox, and run passive liveness."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_bgr is None:
            return PassiveLivenessResult(
                liveness_score=0.0, is_live=False, confidence=0.0,
                attack_type="unknown", method="decode_error", inference_ms=0.0, model_available=False,
            )

        # Compute image hash for dedup (hash bytes, not array)
        image_hash = hashlib.sha256(image_bytes).hexdigest()

        if bbox is not None:
            x1, y1, x2, y2 = bbox
            h, w = img_bgr.shape[:2]
            face_crop = img_bgr[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        else:
            face_crop = img_bgr

        result = self.predict(face_crop)
        result.image_hash = image_hash
        return result
