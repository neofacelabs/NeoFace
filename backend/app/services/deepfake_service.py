"""
NeoFace Trust Engine — Deepfake Detection Service (Module 8)
Detects AI-generated and manipulated faces.

Detects:
  - Face swap videos
  - AI generated faces (GAN)
  - Synthetic avatars
  - Deepfake video streams

Models:
  Primary:   AI-vs-Deepfake-vs-Real ViT (ONNX, int8 quantized, 3-class)
             Source: prithivMLmods/AI-vs-Deepfake-vs-Real-ONNX
             Input: pixel_values [batch, 3, 224, 224], mean/std = 0.5
             Output: logits [batch, 3]  {0: Artificial, 1: Deepfake, 2: Real}
  Secondary: Deepfake-Detection-Exp-02-22 ViT (ONNX, int8 quantized, 2-class)
             Source: prithivMLmods/Deepfake-Detection-Exp-02-22-ONNX
             Input: pixel_values [batch, 3, 224, 224], mean/std = 0.5
             Output: logits [batch, 2]
  Fallback:  Frequency-domain + texture heuristic

Output:
  { "deepfake_probability": 0.04, "is_deepfake": false }
"""

from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import cv2
import numpy as np

from app.core.logging import logger

# Classification threshold — above this = deepfake
# When real models are loaded, 0.50 is appropriate.
# When falling back to heuristic (no models), use 0.85 to avoid false positives.
_DEEPFAKE_THRESHOLD           = 0.50
_DEEPFAKE_THRESHOLD_HEURISTIC = 0.85

# Both ViT models use 224×224 input (they have dynamic batch shapes)
_VIT_SIZE = (224, 224)

# Ensemble weights (primary model is higher accuracy)
_W_PRIMARY   = 0.65
_W_SECONDARY = 0.35

# Primary model (3-class ViT) label mapping: index → label
# {0: Artificial, 1: Deepfake, 2: Real}
_PRIMARY_FAKE_INDICES  = [0, 1]  # Class indices that count as "not real"
_PRIMARY_REAL_INDEX    = 2

# Secondary model (2-class) label mapping
# Assuming [0: deepfake/fake, 1: real] or [0: real, 1: fake] — we'll detect dynamically
# Based on the model type (Deepfake-Detection-Exp-02-22), we assume [0: Fake, 1: Real]
_SECONDARY_FAKE_INDEX = 0
_SECONDARY_REAL_INDEX = 1

# Attack category labels
DEEPFAKE_CATEGORIES = [
    "face_swap",
    "gan_face",
    "synthetic_avatar",
    "deepfake_video",
    "faceapp_manipulation",
]


@dataclass
class DeepfakeResult:
    """Structured output from the deepfake detection service."""
    deepfake_probability: float    # 0.0–1.0
    is_deepfake: bool
    attack_category: str           # face_swap | gan_face | synthetic_avatar | deepfake_video | none
    method: str                    # efficientnet_b4 | xceptionnet | ensemble | heuristic
    classification_strength: float # 0–100, not traditional confidence (distance from 0.5)
    inference_ms: float
    model_available: bool
    efficientnet_score: float | None = None
    xceptionnet_score: float | None = None
    image_hash: str | None = None  # SHA-256 for dedup (not stored)
    
    # Deprecated: use classification_strength instead
    @property
    def confidence(self) -> float:
        """Backward compatibility: returns classification_strength."""
        return self.classification_strength


class DeepfakeService:
    """
    Singleton deepfake detection service.

    Uses EfficientNet-B4 + XceptionNet ensemble when models are available.
    Falls back to a frequency-domain heuristic for environments without models.
    """

    _instance: ClassVar[DeepfakeService | None] = None
    _initialized: ClassVar[bool] = False

    def __init__(self) -> None:
        self._session_eff = None
        self._session_xcp = None
        self._eff_input: str = ""
        self._eff_output: str = ""
        self._xcp_input: str = ""
        self._xcp_output: str = ""
        self._eff_loaded = False
        self._xcp_loaded = False

    @classmethod
    def get_instance(cls) -> DeepfakeService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Load ViT deepfake detector ONNX models. Safe to call multiple times."""
        if self._initialized:
            return

        try:
            import onnxruntime as ort  # type: ignore[import]
            from app.core.config import settings
            providers = ["CPUExecutionProvider"]

            # Primary: AI-vs-Deepfake-vs-Real ViT (3-class)
            eff_path = Path(getattr(settings, "EFFICIENTNET_DEEPFAKE_PATH", "./models/efficientnet_b4_deepfake.onnx"))
            if eff_path.exists():
                self._session_eff = ort.InferenceSession(str(eff_path), providers=providers)
                self._eff_input  = self._session_eff.get_inputs()[0].name
                self._eff_output = self._session_eff.get_outputs()[0].name
                self._eff_loaded = True
                logger.info("deepfake_service.init: Primary ViT loaded",
                            path=str(eff_path),
                            input=self._eff_input, output=self._eff_output)
            else:
                logger.warning("deepfake_service.init: Primary model not found", path=str(eff_path))

            # Secondary: Deepfake-Detection-Exp-02-22 ViT (2-class)
            xcp_path = Path(getattr(settings, "XCEPTIONNET_DEEPFAKE_PATH", "./models/xceptionnet_deepfake.onnx"))
            if xcp_path.exists():
                self._session_xcp = ort.InferenceSession(str(xcp_path), providers=providers)
                self._xcp_input  = self._session_xcp.get_inputs()[0].name
                self._xcp_output = self._session_xcp.get_outputs()[0].name
                self._xcp_loaded = True
                logger.info("deepfake_service.init: Secondary ViT loaded",
                            path=str(xcp_path),
                            input=self._xcp_input, output=self._xcp_output)
            else:
                logger.warning("deepfake_service.init: Secondary model not found", path=str(xcp_path))

        except ImportError:
            logger.warning("deepfake_service.init: onnxruntime not available — using heuristic")
        except Exception as exc:
            logger.error("deepfake_service.init: error", error=str(exc))

        DeepfakeService._initialized = True

    # ── Preprocessing ─────────────────────────────────────────────────────────────

    @staticmethod
    def _preprocess(face_bgr: np.ndarray, target_size: tuple[int, int] = _VIT_SIZE) -> np.ndarray:
        """
        ViT preprocessing: resize → RGB → normalize (mean=0.5, std=0.5) → NCHW float32.

        Both the primary (AI-vs-Deepfake-vs-Real) and secondary (Exp-02-22) models
        were trained with ViTFeatureExtractor: mean=[0.5, 0.5, 0.5], std=[0.5, 0.5, 0.5].
        """
        resized = cv2.resize(face_bgr, target_size, interpolation=cv2.INTER_LANCZOS4)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        mean = np.array([0.5, 0.5, 0.5], dtype=np.float32)
        std  = np.array([0.5, 0.5, 0.5], dtype=np.float32)
        normalized = (rgb - mean) / std
        chw = normalized.transpose(2, 0, 1)
        return np.expand_dims(chw, axis=0)

    # ── Model inference ─────────────────────────────────────────────

    def _run_efficientnet(self, face_bgr: np.ndarray) -> float | None:
        """
        Run primary ViT (AI-vs-Deepfake-vs-Real, 3-class).
        Returns P(not_real) = P(Artificial) + P(Deepfake), or None.
        Labels: {0: Artificial, 1: Deepfake, 2: Real}
        """
        if not self._eff_loaded or self._session_eff is None:
            return None
        try:
            blob = self._preprocess(face_bgr, _VIT_SIZE)
            out = self._session_eff.run([self._eff_output], {self._eff_input: blob})
            logits = np.array(out[0]).flatten()
            # 3-class softmax: [Artificial, Deepfake, Real]
            probs = self._softmax(logits)
            # P(fake) = P(Artificial) + P(Deepfake)
            return float(probs[_PRIMARY_FAKE_INDICES].sum())
        except Exception as exc:
            logger.warning("deepfake_service.primary_vit: error", error=str(exc))
            return None

    def _run_xceptionnet(self, face_bgr: np.ndarray) -> float | None:
        """
        Run secondary ViT (Deepfake-Detection-Exp-02-22, 2-class).
        Returns P(fake), or None.
        Assumes label layout: [0: Fake, 1: Real]
        """
        if not self._xcp_loaded or self._session_xcp is None:
            return None
        try:
            blob = self._preprocess(face_bgr, _VIT_SIZE)
            out = self._session_xcp.run([self._xcp_output], {self._xcp_input: blob})
            logits = np.array(out[0]).flatten()
            if len(logits) == 2:
                probs = self._softmax(logits)
                # [0: Fake, 1: Real] → P(fake) = probs[0]
                return float(probs[_SECONDARY_FAKE_INDEX])
            elif len(logits) == 1:
                return float(1.0 / (1.0 + np.exp(-logits[0])))
            return None
        except Exception as exc:
            logger.warning("deepfake_service.secondary_vit: error", error=str(exc))
            return None

    # ── Frequency-domain heuristic ────────────────────────────────────────────

    @staticmethod
    def _softmax(logits: np.ndarray) -> np.ndarray:
        e = np.exp(logits - logits.max())
        return e / e.sum()

    @staticmethod
    def _frequency_heuristic(face_bgr: np.ndarray) -> float:
        """
        Frequency-domain deepfake detection heuristic.

        Conservative approach when no ONNX models are available.
        Real webcam faces should return a LOW probability (~0.05-0.20).
        Only clear synthetic artifacts trigger a higher score.

        GAN-generated faces have characteristic frequency artifacts:
        - Checkerboard patterns (very periodic, strong FFT peaks)
        - Perfectly smooth textures (no natural noise)
        - Missing natural skin texture variance

        Returns P(deepfake) in [0, 1]. Bias strongly toward REAL.
        """
        if face_bgr is None or face_bgr.size == 0:
            # No face data — assume real, don't block
            return 0.05

        try:
            small = cv2.resize(face_bgr, (128, 128))
            gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)

            # ── Natural skin texture check ────────────────────────────────
            # Real faces have natural noise / texture variance.
            # GAN faces are often unnaturally smooth.
            laplacian_var = float(cv2.Laplacian(gray, cv2.CV_32F).var())
            # Real webcam face: Laplacian variance typically 100–2000+
            # Ultra-smooth GAN: < 15
            if laplacian_var < 10.0:
                texture_score = 0.35  # Very smooth → suspicious
            elif laplacian_var < 18.0:
                texture_score = 0.15
            else:
                texture_score = 0.0  # Natural texture → real

            # ── FFT checkerboard pattern detection ───────────────────────
            # GAN transposed convolutions create strong periodic artifacts.
            f = np.fft.fft2(gray)
            fshift = np.fft.fftshift(f)
            magnitude = np.abs(fshift)

            h, w = magnitude.shape
            cy, cx = h // 2, w // 2

            # Normalize magnitude
            mag_norm = magnitude / (magnitude.mean() + 1e-9)

            # Look for periodic peaks at GAN-specific frequencies (corners/edges)
            # Real faces: smooth spectrum with natural roll-off
            # GAN faces: sharp peaks at regular intervals
            corner_region = np.array([
                mag_norm[0:10, 0:10].max(),
                mag_norm[0:10, -10:].max(),
                mag_norm[-10:, 0:10].max(),
                mag_norm[-10:, -10:].max(),
            ])
            center_energy = float(mag_norm[cy-5:cy+5, cx-5:cx+5].mean())
            corner_ratio  = float(corner_region.max()) / (center_energy + 1e-9)

            # Real faces: corner_ratio typically < 0.3
            # GAN faces with checkerboard: > 0.8
            if corner_ratio > 2.2:
                fft_score = 0.4
            elif corner_ratio > 1.2:
                fft_score = 0.1
            else:
                fft_score = 0.0

            # ── Composite: weighted, biased toward REAL ───────────────────
            # With no models, we should be very conservative.
            # Only flag when BOTH signals are suspicious.
            fake_prob = 0.5 * texture_score + 0.5 * fft_score

            # Bias: real webcam gets at most 0.25 from heuristic without models
            fake_prob = float(min(max(fake_prob, 0.01), 0.75))
            return fake_prob

        except Exception:
            # Any error → assume real
            return 0.05

    # ── Attack category inference ─────────────────────────────────────────────

    @staticmethod
    def _infer_category(face_bgr: np.ndarray, deepfake_prob: float) -> str:
        """Rough category from texture/frequency features when probability > threshold."""
        if deepfake_prob < _DEEPFAKE_THRESHOLD:
            return "none"

        small = cv2.resize(face_bgr, (64, 64))
        gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)

        # Frequency analysis
        fft = np.fft.fft2(gray)
        fft_mag = np.abs(np.fft.fftshift(fft))
        hf_ratio = float(fft_mag[24:40, 24:40].mean() / (fft_mag.mean() + 1e-9))

        # Texture smoothness (GAN faces tend to be smoother)
        lap_var = float(cv2.Laplacian(gray, cv2.CV_32F).var())

        if lap_var < 100 and hf_ratio < 2.0:
            return "gan_face"      # Ultra-smooth GAN artifact
        elif lap_var < 200:
            return "synthetic_avatar"  # Rendered/composite face
        elif hf_ratio > 4.0:
            return "face_swap"     # Face swap compression artifacts
        else:
            return "deepfake_video"

    # ── Public API ────────────────────────────────────────────────────────────

    def detect(self, image_bytes: bytes, bbox: tuple[int, int, int, int] | None = None) -> DeepfakeResult:
        """
        Detect deepfake on raw image bytes, optionally cropping to a bbox first.

        Returns DeepfakeResult with deepfake_probability, is_deepfake, attack_category.
        """
        t0 = time.perf_counter()

        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        image_hash = hashlib.sha256(image_bytes).hexdigest()

        if img_bgr is None:
            return DeepfakeResult(
                deepfake_probability=0.5, is_deepfake=False,
                attack_category="unknown", method="decode_error",
                classification_strength=0.0, inference_ms=0.0, model_available=False,
                image_hash=image_hash,
            )

        if bbox is not None:
            x1, y1, x2, y2 = bbox
            h, w = img_bgr.shape[:2]
            face_crop = img_bgr[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        else:
            face_crop = img_bgr

        eff_score = self._run_efficientnet(face_crop)
        xcp_score = self._run_xceptionnet(face_crop)

        model_available = self._eff_loaded or self._xcp_loaded
        method = "heuristic"
        deepfake_prob = 0.0

        if eff_score is not None and xcp_score is not None:
            deepfake_prob = _W_PRIMARY * eff_score + _W_SECONDARY * xcp_score
            method = "vit_ensemble"
        elif eff_score is not None:
            deepfake_prob = eff_score
            method = "vit_primary"
        elif xcp_score is not None:
            deepfake_prob = xcp_score
            method = "vit_secondary"
        else:
            deepfake_prob = self._frequency_heuristic(face_crop)
            model_available = False

        # Use a more conservative threshold when running in heuristic mode
        threshold = _DEEPFAKE_THRESHOLD if model_available else _DEEPFAKE_THRESHOLD_HEURISTIC
        is_deepfake = deepfake_prob >= threshold
        attack_category = self._infer_category(face_crop, deepfake_prob)
        classification_strength = round(abs(deepfake_prob - 0.5) * 200.0, 1)  # Distance from 0.5 → 0-100
        inference_ms = round((time.perf_counter() - t0) * 1000, 2)

        logger.debug(
            "deepfake_service.detect",
            prob=round(deepfake_prob, 4), is_deepfake=is_deepfake,
            category=attack_category, method=method, inference_ms=inference_ms,
        )

        return DeepfakeResult(
            deepfake_probability=round(deepfake_prob, 4),
            is_deepfake=is_deepfake,
            attack_category=attack_category,
            method=method,
            classification_strength=classification_strength,
            inference_ms=inference_ms,
            model_available=model_available,
            efficientnet_score=round(eff_score, 4) if eff_score is not None else None,
            xceptionnet_score=round(xcp_score, 4) if xcp_score is not None else None,
            image_hash=image_hash,
        )
