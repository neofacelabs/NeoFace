"""
NeoFace Trust Engine — Depth Estimation Service (Module 6)
Differentiates real faces (3D) from flat images and screen replays.

Models:
  Primary:   MiDaS Small v2.1 (ONNX)
             Source: Heliosoph/midas-small-onnx
             Input:  input_image [1, 3, 256, 256], ImageNet stats
             Output: output_depth [1, 256, 256]
  Secondary: DPT Hybrid (ONNX, HuggingFace Transformers)
             Source: lquint/dpt-hybrid-midas-onnx
             Input:  pixel_values [batch, 3, H, W], ImageNet stats, 384×384
             Output: predicted_depth [batch, H, W]
  Fallback: gradient-based depth heuristic

Output:
  { "depth_score": 0.94, "is_3d_face": true }
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import cv2
import numpy as np

from app.core.logging import logger

# Thresholds
_DEPTH_VARIANCE_THRESHOLD = 0.15   # Minimum normalized variance to be "3D"
_IS_3D_SCORE_THRESHOLD    = 0.60   # depth_score above which face is 3D

# MiDaS / DPT input sizes
_MIDAS_SMALL_SIZE = (256, 256)   # MiDaS Small: fixed 256×256
_DPT_HYBRID_SIZE  = (384, 384)   # DPT Hybrid: 384×384 (HF Transformers format)


@dataclass
class DepthResult:
    """Structured output from the depth estimation service."""
    depth_score: float       # 0.0–1.0 — higher = more 3D depth variation
    is_3d_face: bool
    depth_variance: float    # Variance of depth map in face region
    depth_map_shape: tuple | None   # Shape of generated depth map
    method: str              # midas_small | dpt_hybrid | gradient_heuristic
    inference_ms: float
    model_available: bool


class DepthEstimationService:
    """
    Singleton depth estimation service.

    Uses MiDaS Small as primary model for <200ms inference on CPU.
    Falls back to gradient/Laplacian heuristic when models are unavailable.
    """

    _instance: ClassVar[DepthEstimationService | None] = None
    _initialized: ClassVar[bool] = False

    def __init__(self) -> None:
        self._session_small = None
        self._session_dpt   = None
        self._small_input:  str = ""
        self._small_output: str = ""
        self._dpt_input:    str = ""
        self._dpt_output:   str = ""
        self._small_loaded = False
        self._dpt_loaded   = False

    @classmethod
    def get_instance(cls) -> DepthEstimationService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Load MiDaS Small + DPT Hybrid ONNX models. Safe to call multiple times."""
        if self._initialized:
            return

        try:
            import onnxruntime as ort  # type: ignore[import]
            from app.core.config import settings
            providers = ["CPUExecutionProvider"]

            # MiDaS Small (primary — fast)
            small_path = Path(getattr(settings, "MIDAS_SMALL_PATH", "./models/midas_small.onnx"))
            if small_path.exists():
                self._session_small = ort.InferenceSession(str(small_path), providers=providers)
                self._small_input  = self._session_small.get_inputs()[0].name
                self._small_output = self._session_small.get_outputs()[0].name
                self._small_loaded = True
                logger.info("depth_service.init: MiDaS Small loaded",
                            path=str(small_path),
                            input=self._small_input, output=self._small_output)
            else:
                logger.warning("depth_service.init: MiDaS Small not found — using heuristic", path=str(small_path))

            # DPT Hybrid (secondary — higher accuracy, ~508 MB)
            dpt_path = Path(getattr(settings, "DPT_HYBRID_PATH", "./models/dpt_hybrid.onnx"))
            if dpt_path.exists():
                self._session_dpt = ort.InferenceSession(str(dpt_path), providers=providers)
                self._dpt_input  = self._session_dpt.get_inputs()[0].name
                self._dpt_output = self._session_dpt.get_outputs()[0].name
                self._dpt_loaded = True
                logger.info("depth_service.init: DPT Hybrid loaded",
                            path=str(dpt_path),
                            input=self._dpt_input, output=self._dpt_output)

        except ImportError:
            logger.warning("depth_service.init: onnxruntime not available")
        except Exception as exc:
            logger.error("depth_service.init: error", error=str(exc))

        DepthEstimationService._initialized = True

    # ── MiDaS preprocessing ───────────────────────────────────────────────────

    @staticmethod
    def _preprocess_midas(img_bgr: np.ndarray, target_size: tuple[int, int]) -> np.ndarray:
        """MiDaS expects RGB, normalized, NCHW float32."""
        resized = cv2.resize(img_bgr, target_size, interpolation=cv2.INTER_CUBIC)
        rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std  = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        normalized = (rgb - mean) / std
        chw = normalized.transpose(2, 0, 1)
        return np.expand_dims(chw, axis=0)

    # ── ONNX inference ────────────────────────────────────────────────────────

    def _run_midas_small(self, img_bgr: np.ndarray) -> np.ndarray | None:
        """Run MiDaS Small inference. Returns depth map or None."""
        if not self._small_loaded or self._session_small is None:
            return None
        try:
            blob = self._preprocess_midas(img_bgr, _MIDAS_SMALL_SIZE)
            out = self._session_small.run([self._small_output], {self._small_input: blob})
            return np.array(out[0]).squeeze()
        except Exception as exc:
            logger.warning("depth_service.midas_small: error", error=str(exc))
            return None

    def _run_dpt_hybrid(self, img_bgr: np.ndarray) -> np.ndarray | None:
        """Run DPT Hybrid inference. Returns depth map or None."""
        if not self._dpt_loaded or self._session_dpt is None:
            return None
        try:
            blob = self._preprocess_midas(img_bgr, _DPT_HYBRID_SIZE)
            out = self._session_dpt.run([self._dpt_output], {self._dpt_input: blob})
            return np.array(out[0]).squeeze()
        except Exception as exc:
            logger.warning("depth_service.dpt_hybrid: error", error=str(exc))
            return None

    # ── Gradient heuristic fallback ───────────────────────────────────────────

    @staticmethod
    def _gradient_depth_heuristic(img_bgr: np.ndarray) -> float:
        """
        Approximate depth variation using gradient magnitude variance.

        Real 3D faces have high gradient variance in the face region
        (shadows, nose bridge, eye sockets create strong depth cues).
        Flat printed images or screen replays have more uniform gradients.
        """
        small = cv2.resize(img_bgr, (128, 128))
        gray  = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY).astype(np.float32)

        gx = cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3)
        magnitude = np.sqrt(gx**2 + gy**2)

        # Focus on central face region
        h, w = magnitude.shape
        center = magnitude[h//4:3*h//4, w//4:3*w//4]
        variance = float(center.var())

        # Normalize: real faces typically > 500, photos < 200
        normalized = float(min(variance / 1500.0, 1.0))
        return normalized

    # ── Depth score computation ───────────────────────────────────────────────

    @staticmethod
    def _compute_depth_score(depth_map: np.ndarray) -> float:
        """
        Compute a 0–1 score indicating depth variation (3D-ness) from a depth map.

        Higher variance in the central face region = more 3D structure.
        """
        if depth_map is None or depth_map.size == 0:
            return 0.0

        # Normalize depth map to [0, 1]
        dmin, dmax = depth_map.min(), depth_map.max()
        if dmax - dmin < 1e-9:
            return 0.0
        normalized = (depth_map - dmin) / (dmax - dmin)

        # Focus on central 60% of the depth map (the face region)
        h, w = normalized.shape[:2] if len(normalized.shape) >= 2 else (normalized.shape[0], 1)
        if h <= 2 or w <= 2:
            return float(normalized.std())

        cy, cx = h // 2, w // 2
        margin_y, margin_x = int(h * 0.3), int(w * 0.3)
        face_region = normalized[
            max(0, cy - margin_y): min(h, cy + margin_y),
            max(0, cx - margin_x): min(w, cx + margin_x),
        ]

        variance = float(face_region.var())
        # Map variance to 0–1 score
        return float(min(variance / 0.03, 1.0))

    # ── Public API ────────────────────────────────────────────────────────────

    def estimate(self, image_bytes: bytes) -> DepthResult:
        """
        Estimate face depth from raw image bytes.

        Returns DepthResult with depth_score and is_3d_face flag.
        """
        t0 = time.perf_counter()

        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_bgr is None:
            return DepthResult(
                depth_score=0.0, is_3d_face=False, depth_variance=0.0,
                depth_map_shape=None, method="decode_error",
                inference_ms=0.0, model_available=False,
            )

        # Try DPT Hybrid (most accurate), then MiDaS Small, then heuristic
        depth_map = self._run_dpt_hybrid(img_bgr)
        method = "dpt_hybrid"
        model_available = True

        if depth_map is None:
            depth_map = self._run_midas_small(img_bgr)
            method = "midas_small"

        if depth_map is None:
            # Heuristic fallback
            score = self._gradient_depth_heuristic(img_bgr)
            model_available = False
            method = "gradient_heuristic"
            depth_variance = score
            is_3d_face = score >= _IS_3D_SCORE_THRESHOLD
            inference_ms = round((time.perf_counter() - t0) * 1000, 2)

            logger.debug(
                "depth_service.estimate",
                score=round(score, 4), is_3d=is_3d_face, method=method,
            )

            return DepthResult(
                depth_score=round(score, 4),
                is_3d_face=is_3d_face,
                depth_variance=round(depth_variance, 4),
                depth_map_shape=None,
                method=method,
                inference_ms=inference_ms,
                model_available=model_available,
            )

        depth_score = self._compute_depth_score(depth_map)
        depth_variance = float(depth_map.var()) if depth_map is not None else 0.0
        is_3d_face = depth_score >= _IS_3D_SCORE_THRESHOLD
        inference_ms = round((time.perf_counter() - t0) * 1000, 2)

        logger.debug(
            "depth_service.estimate",
            score=round(depth_score, 4), is_3d=is_3d_face,
            method=method, inference_ms=inference_ms,
        )

        return DepthResult(
            depth_score=round(depth_score, 4),
            is_3d_face=is_3d_face,
            depth_variance=round(depth_variance, 6),
            depth_map_shape=tuple(depth_map.shape) if depth_map is not None else None,
            method=method,
            inference_ms=inference_ms,
            model_available=model_available,
        )
