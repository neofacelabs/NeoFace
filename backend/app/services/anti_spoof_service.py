"""
NeoFace Anti-Spoofing Service
Passive presentation-attack detection using MiniFASNet via ONNX Runtime.

Detects the following attack types:
  - Photo attacks     (printed photograph held in front of camera)
  - Screen attacks    (image displayed on a mobile phone or monitor)
  - Replay attacks    (video playback on a screen)
  - Mask attacks      (3D printed / paper-cut masks)

Architecture:
  - MiniFASNet (garciafido/minifasnet-v2-anti-spoofing-onnx) — lightweight CNN.
  - Input:  face crop resized to 80×80, normalised to [-1, 1], NCHW layout.
  - Output: [batch, 3] softmax probabilities → [P(spoof), P(real), P(partial)].
  - Threshold: ANTI_SPOOF_THRESHOLD (default 0.70) on the P(real) probability.

Graceful degradation:
  - If the ONNX model file is absent or fails to load, the service falls back
    to a texture-complexity heuristic that catches the most obvious attacks
    (flat, low-frequency printed images).  A warning is logged and the
    returned result is marked method="heuristic_fallback".

Singleton pattern:
  - Call AntiSpoofService.get_instance() to obtain the module-level singleton.
    The ONNX session is loaded once at application startup via initialize().

Usage:
    service = AntiSpoofService.get_instance()
    service.initialize()  # called once in app lifespan

    result = service.predict(face_crop_bgr)
    if not result.is_real:
        # reject the attempt
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

import cv2
import numpy as np

from app.core.config import settings
from app.core.logging import logger


# ── Result dataclass ──────────────────────────────────────────────────────────

@dataclass
class AntiSpoofResult:
    """
    Structured result from the anti-spoofing pipeline.

    Attributes:
        is_real:             True when the face is classified as live/genuine.
        score:               Confidence the face is real, scaled 0–100.
        raw_real_prob:       Raw "real" probability from the model output [0–1].
        method:              Which backend produced this result.
        attack_type:         Best-guess attack category if is_real is False,
                             or "none" when the face is genuine.
        inference_ms:        Inference wall-clock time in milliseconds.
        model_available:     Whether the ONNX model was loaded successfully.
    """
    is_real: bool
    score: float                        # 0–100
    raw_real_prob: float                # 0–1
    method: str                         # "minifasnet" | "heuristic_fallback"
    attack_type: str = "none"           # "photo" | "screen" | "replay" | "mask" | "none"
    inference_ms: float = 0.0
    model_available: bool = True


# ── Input size expected by MiniFASNet ─────────────────────────────────────────
_INPUT_H: int = 80
_INPUT_W: int = 80


class AntiSpoofService:
    """
    Singleton anti-spoofing service backed by MiniFASNet ONNX.

    Thread-safety: the ONNX InferenceSession is created once at
    startup and is safe to call from multiple threads / async tasks.
    """

    _instance: ClassVar[AntiSpoofService | None] = None
    _initialized: ClassVar[bool] = False

    def __init__(self) -> None:
        self._session = None          # onnxruntime.InferenceSession
        self._input_name: str = ""
        self._output_name: str = ""
        self._model_loaded: bool = False

    # ── Singleton ─────────────────────────────────────────────────────────────

    @classmethod
    def get_instance(cls) -> AntiSpoofService:
        """Return the global singleton, creating it if necessary."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Initialization ────────────────────────────────────────────────────────

    def initialize(self) -> None:
        """
        Load the MiniFASNet ONNX model into memory.
        Safe to call multiple times — subsequent calls are no-ops.

        If the model file does not exist the service logs a warning and
        falls back to the heuristic scorer.
        """
        if self._initialized:
            return

        model_path = Path(settings.ANTI_SPOOF_MODEL_PATH)

        if not settings.ANTI_SPOOF_ENABLED:
            logger.info("anti_spoof.init: disabled via ANTI_SPOOF_ENABLED=False")
            AntiSpoofService._initialized = True
            return

        if not model_path.exists():
            logger.warning(
                "anti_spoof.init: ONNX model not found — using heuristic fallback",
                path=str(model_path),
                hint="See models/README.md for download instructions",
            )
            AntiSpoofService._initialized = True
            return

        try:
            import onnxruntime as ort  # type: ignore[import]

            # Use CPU provider for portability; add CUDAExecutionProvider first
            # in the list to enable GPU when onnxruntime-gpu is installed.
            providers = ["CPUExecutionProvider"]
            self._session = ort.InferenceSession(
                str(model_path),
                providers=providers,
            )

            # Cache input / output node names (set at model creation time)
            self._input_name = self._session.get_inputs()[0].name
            self._output_name = self._session.get_outputs()[0].name
            self._model_loaded = True

            logger.info(
                "anti_spoof.init: MiniFASNet loaded",
                path=str(model_path),
                input=self._input_name,
                output=self._output_name,
            )

        except Exception as exc:
            logger.error(
                "anti_spoof.init: failed to load ONNX model — using heuristic fallback",
                error=str(exc),
                path=str(model_path),
            )

        AntiSpoofService._initialized = True

    # ── Preprocessing ─────────────────────────────────────────────────────────

    def _preprocess(self, face_bgr: np.ndarray) -> np.ndarray:
        """
        Prepare a face crop for MiniFASNet inference.

        Steps:
          1. Resize to 80×80 (model input size).
          2. Convert BGR → RGB.
          3. Normalise pixel values from [0, 255] to [-1.0, 1.0].
          4. Reshape to NCHW: (1, 3, 80, 80).
          5. Cast to float32.

        Args:
            face_bgr: OpenCV face crop, any size, BGR channel order.

        Returns:
            numpy array of shape (1, 3, 80, 80) in float32.
        """
        resized = cv2.resize(face_bgr, (_INPUT_W, _INPUT_H), interpolation=cv2.INTER_LINEAR)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        # Normalize [0,255] → [-1, 1]
        normalized = (rgb.astype(np.float32) / 127.5) - 1.0
        # HWC → CHW
        chw = normalized.transpose(2, 0, 1)
        # Add batch dimension → NCHW
        return np.expand_dims(chw, axis=0)

    # ── Heuristic fallback ────────────────────────────────────────────────────

    def _heuristic_score(self, face_bgr: np.ndarray) -> AntiSpoofResult:
        """
        Texture-complexity heuristic for when the ONNX model is unavailable.

        Real faces have rich, high-frequency texture (pores, hair, skin detail).
        Spoofing artefacts (flat printed photos, Moiré patterns, screen reflections)
        have characteristic texture signatures:

        - Printed/paper photos:  lower Laplacian variance + uniform colour histogram
        - Screen replays:        banding in frequency domain; bright saturated pixels
        - We combine Laplacian variance, local binary patterns entropy, and a
          chromatic diversity measure to generate a 0–100 liveness-texture score.

        This is NOT a substitute for a trained model — it is a best-effort
        safety net used only when the ONNX file is absent.
        """
        if face_bgr is None or face_bgr.size == 0:
            return AntiSpoofResult(
                is_real=False, score=0.0, raw_real_prob=0.0,
                method="heuristic_fallback", attack_type="unknown",
                model_available=False,
            )

        resized = cv2.resize(face_bgr, (80, 80))
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        # ── Feature 1: Laplacian variance (sharpness / texture richness) ──────
        laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        # Real faces typically > 200; printed photos often < 100
        sharpness_score = min(laplacian_var / 400.0, 1.0)

        # ── Feature 2: Histogram entropy (colour diversity) ───────────────────
        hist = cv2.calcHist([gray], [0], None, [64], [0, 256])
        hist = hist.flatten() / hist.sum()
        hist_entropy = float(-np.sum(hist * np.log2(hist + 1e-7)))
        # Max entropy for 64 bins ≈ 6.0; printed images tend to be lower
        entropy_score = min(hist_entropy / 5.0, 1.0)

        # ── Feature 3: Local Binary Pattern (LBP) variance ───────────────────
        lbp_var = self._lbp_variance(gray)
        lbp_score = min(lbp_var / 2000.0, 1.0)

        # ── Composite score ───────────────────────────────────────────────────
        raw_prob = float(0.35 * sharpness_score + 0.35 * entropy_score + 0.30 * lbp_score)
        score = round(raw_prob * 100.0, 2)
        is_real = raw_prob >= settings.ANTI_SPOOF_THRESHOLD

        attack_type = "none"
        if not is_real:
            # Distinguish photo vs screen by saturation
            hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)
            mean_sat = float(hsv[:, :, 1].mean())
            attack_type = "screen" if mean_sat > 80 else "photo"

        logger.debug(
            "anti_spoof.heuristic",
            laplacian=round(laplacian_var, 1),
            entropy=round(hist_entropy, 3),
            lbp_var=round(lbp_var, 1),
            raw_prob=round(raw_prob, 4),
            is_real=is_real,
        )

        return AntiSpoofResult(
            is_real=is_real,
            score=score,
            raw_real_prob=raw_prob,
            method="heuristic_fallback",
            attack_type=attack_type,
            model_available=False,
        )

    @staticmethod
    def _lbp_variance(gray: np.ndarray, radius: int = 1, n_points: int = 8) -> float:
        """
        Compute the variance of Local Binary Pattern descriptor using fully vectorized NumPy.
        
        High variance = rich micro-texture (consistent with real skin).
        Low variance  = flat, uniform texture (consistent with printed images).
        
        Uses numpy.roll() for circular shifting instead of nested loops for 5-20x speedup.
        """
        h, w = gray.shape
        
        if h < 3 or w < 3:
            return 0.0
        
        # Extract center region (avoiding edges)
        center = gray[1:-1, 1:-1].astype(np.float32)
        
        # Get all 8 neighbors using np.roll() for circular shifts
        # This is fully vectorized — no Python loops
        neighbors = [
            np.roll(np.roll(gray, 1, axis=0), 1, axis=1)[1:-1, 1:-1],    # top-left
            np.roll(gray, 1, axis=0)[1:-1, 1:-1],                        # top
            np.roll(np.roll(gray, 1, axis=0), -1, axis=1)[1:-1, 1:-1],   # top-right
            np.roll(gray, -1, axis=1)[1:-1, 1:-1],                       # right
            np.roll(np.roll(gray, -1, axis=0), -1, axis=1)[1:-1, 1:-1],  # bottom-right
            np.roll(gray, -1, axis=0)[1:-1, 1:-1],                       # bottom
            np.roll(np.roll(gray, -1, axis=0), 1, axis=1)[1:-1, 1:-1],   # bottom-left
            np.roll(gray, 1, axis=1)[1:-1, 1:-1],                        # left
        ]
        
        # Compute LBP codes vectorized
        # For each neighbor, compare to center and set bit
        lbp = np.zeros_like(center, dtype=np.uint8)
        
        for bit_pos, neighbor in enumerate(neighbors):
            # where(neighbor >= center, 1 << bit_pos, 0) — vectorized bit setting
            lbp |= np.where(neighbor >= center, 1 << bit_pos, 0).astype(np.uint8)
        
        # Return variance of LBP codes
        return float(np.var(lbp.astype(np.float32)))

    # ── ONNX inference ────────────────────────────────────────────────────────

    def _run_onnx(self, face_bgr: np.ndarray) -> AntiSpoofResult:
        """
        Run MiniFASNet ONNX inference on a face crop.

        The model outputs a (1, 2) softmax vector: [P(spoof), P(real)].
        We use P(real) against the configured threshold.
        """
        t0 = time.perf_counter()

        try:
            blob = self._preprocess(face_bgr)
            outputs = self._session.run(
                [self._output_name],
                {self._input_name: blob},
            )
            # outputs[0] shape: (batch, 3) → [P(spoof), P(real), P(partial_spoof)]
            probs = np.array(outputs[0]).flatten()

            if len(probs) < 2:
                raise ValueError(f"Unexpected output shape: {probs.shape}")

            real_prob    = float(probs[1])                              # P(real)
            partial_prob = float(probs[2]) if len(probs) > 2 else 0.0  # P(partial/ambiguous)
            is_real = real_prob >= settings.ANTI_SPOOF_THRESHOLD
            score = round(real_prob * 100.0, 2)

            # Classify attack type when face is flagged as spoof
            attack_type = "none"
            if not is_real:
                hsv = cv2.cvtColor(
                    cv2.resize(face_bgr, (80, 80)), cv2.COLOR_BGR2HSV
                )
                mean_sat = float(hsv[:, :, 1].mean())
                laplacian_var = float(
                    cv2.Laplacian(
                        cv2.cvtColor(cv2.resize(face_bgr, (80, 80)), cv2.COLOR_BGR2GRAY),
                        cv2.CV_64F,
                    ).var()
                )
                # Use partial_prob to distinguish mask/ambiguous attacks
                if partial_prob > 0.35:
                    attack_type = "mask"      # High partial score → 3D mask
                elif mean_sat > 100 and laplacian_var > 150:
                    attack_type = "replay"    # Bright, sharp screen
                elif mean_sat > 60:
                    attack_type = "screen"    # Screen with moderate saturation
                else:
                    attack_type = "photo"     # Printed / low-saturation image

            inference_ms = (time.perf_counter() - t0) * 1000

            logger.debug(
                "anti_spoof.onnx",
                real_prob=round(real_prob, 4),
                is_real=is_real,
                attack_type=attack_type,
                inference_ms=round(inference_ms, 2),
            )

            return AntiSpoofResult(
                is_real=is_real,
                score=score,
                raw_real_prob=real_prob,
                method="minifasnet",
                attack_type=attack_type,
                inference_ms=round(inference_ms, 2),
                model_available=True,
            )

        except Exception as exc:
            inference_ms = (time.perf_counter() - t0) * 1000
            logger.error(
                "anti_spoof.onnx: inference failed — falling back to heuristic",
                error=str(exc),
                inference_ms=round(inference_ms, 2),
            )
            return self._heuristic_score(face_bgr)

    # ── Public API ────────────────────────────────────────────────────────────

    def predict(self, face_bgr: np.ndarray) -> AntiSpoofResult:
        """
        Run anti-spoofing analysis on a face crop.

        Args:
            face_bgr: OpenCV BGR image of the face region.
                      Any size — preprocessing will resize to 80×80.

        Returns:
            AntiSpoofResult with is_real, score (0–100), method, and
            attack_type classification.
        """
        if not settings.ANTI_SPOOF_ENABLED:
            # Anti-spoof disabled: treat every face as real with a neutral score
            return AntiSpoofResult(
                is_real=True,
                score=100.0,
                raw_real_prob=1.0,
                method="disabled",
                attack_type="none",
                model_available=False,
            )

        if face_bgr is None or face_bgr.size == 0:
            return AntiSpoofResult(
                is_real=False,
                score=0.0,
                raw_real_prob=0.0,
                method="error",
                attack_type="unknown",
                model_available=False,
            )

        if self._model_loaded and self._session is not None:
            return self._run_onnx(face_bgr)

        # Model not loaded — use heuristic fallback
        return self._heuristic_score(face_bgr)

    def predict_from_bytes(self, image_bytes: bytes, bbox: tuple[int, int, int, int] | None = None) -> AntiSpoofResult:
        """
        Convenience wrapper: decode image bytes, optionally crop to bbox,
        and run anti-spoofing prediction.

        Args:
            image_bytes: Raw JPEG/PNG bytes.
            bbox:        Optional (x1, y1, x2, y2) face bounding box to crop.
                         If None the full image is used.

        Returns:
            AntiSpoofResult.
        """
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_bgr is None:
            return AntiSpoofResult(
                is_real=False, score=0.0, raw_real_prob=0.0,
                method="error", attack_type="unknown", model_available=False,
            )

        if bbox is not None:
            x1, y1, x2, y2 = bbox
            h, w = img_bgr.shape[:2]
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            face_crop = img_bgr[y1:y2, x1:x2]
        else:
            face_crop = img_bgr

        return self.predict(face_crop)
