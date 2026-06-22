"""
NeoFace Trust Engine — Emotion Recognition Service (Module 3)
Secondary liveness signal via facial emotion classification.

NOT used for identity verification. Used as a behavioral liveness indicator.

Detects: neutral | happy | surprise | fear | disgust | angry | contempt | sad

Models:
  Primary: FER+ Emotion Classifier (ONNX, emotion-ferplus-8 from ONNX Model Zoo)
           Input: [1, 1, 64, 64] grayscale float32, range [0, 1]
           Output: [1, 8] logits over 8 FER+ emotion classes
  Fallback: rule-based facial geometry heuristic

Output:
  { "emotion": "happy", "confidence": 96 }
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar

import cv2
import numpy as np

from app.core.logging import logger

# FER+ emotion class order (MUST match model training order)
# https://huggingface.co/onnxmodelzoo/emotion-ferplus-8
EMOTION_CLASSES = ["neutral", "happy", "surprise", "fear", "disgust", "angry", "contempt", "sad"]

# FER+ model input: grayscale 64×64
_INPUT_SIZE = (64, 64)


@dataclass
class EmotionResult:
    """Structured output from the emotion recognition service."""
    emotion: str               # Dominant emotion label
    confidence: float          # 0–100
    all_scores: dict[str, float]   # Per-class probabilities (0–100)
    method: str                # ferplus | heuristic | fallback
    inference_ms: float
    model_available: bool


class EmotionService:
    """
    Singleton emotion recognition service.

    Initialize once at app startup, call analyze() per frame.
    """

    _instance: ClassVar[EmotionService | None] = None
    _initialized: ClassVar[bool] = False
    _face_mesh: ClassVar[any] = None  # Cached FaceMesh instance (shared across calls)

    def __init__(self) -> None:
        self._session = None
        self._input_name: str = ""
        self._output_name: str = ""
        self._model_loaded = False

    @classmethod
    def get_instance(cls) -> EmotionService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """Load FER+ emotion ONNX model. Safe to call multiple times."""
        if self._initialized:
            return

        try:
            import onnxruntime as ort  # type: ignore[import]
            from app.core.config import settings

            model_path = Path(getattr(settings, "EMOTION_MODEL_PATH", "./models/emotion_mobilenetv3.onnx"))
            if model_path.exists():
                providers = ["CPUExecutionProvider"]
                self._session = ort.InferenceSession(str(model_path), providers=providers)
                self._input_name = self._session.get_inputs()[0].name
                self._output_name = self._session.get_outputs()[0].name
                self._model_loaded = True
                logger.info("emotion_service.init: FER+ model loaded",
                            path=str(model_path),
                            input_name=self._input_name,
                            output_name=self._output_name)
            else:
                logger.warning("emotion_service.init: model not found — using heuristic", path=str(model_path))
        except ImportError:
            logger.warning("emotion_service.init: onnxruntime not available — using heuristic")
        except Exception as exc:
            logger.error("emotion_service.init: error", error=str(exc))

        EmotionService._initialized = True

    # ── Preprocessing ─────────────────────────────────────────────────────────

    @staticmethod
    def _preprocess(face_bgr: np.ndarray) -> np.ndarray:
        """
        FER+ preprocessing: grayscale → resize 64×64 → normalize [0,1] → NCHW float32.

        Input:  face_bgr  numpy array (any size, BGR)
        Output: [1, 1, 64, 64] float32 tensor in [0, 1]
        """
        resized = cv2.resize(face_bgr, _INPUT_SIZE, interpolation=cv2.INTER_LINEAR)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)  # shape: (64, 64)
        normalized = gray.astype(np.float32) / 255.0      # [0, 1]
        # Shape: [1, 1, 64, 64] (batch, channel, height, width)
        return normalized[np.newaxis, np.newaxis, :, :]

    # ── Geometric heuristic fallback ──────────────────────────────────────────

    @classmethod
    def _get_face_mesh(cls):
        """Return the cached FaceMesh instance, initializing it on first use."""
        if cls._face_mesh is None:
            import mediapipe as mp
            cls._face_mesh = mp.solutions.face_mesh.FaceMesh(
                static_image_mode=False,   # False = optimized for video/streaming
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.4,
                min_tracking_confidence=0.4,
            )
        return cls._face_mesh

    @classmethod
    def _heuristic_emotion(cls, face_bgr: np.ndarray) -> "EmotionResult":
        """
        Geometry-based emotion guess using mouth, eye, and brow aspect ratios.

        Calibrated thresholds for real webcam faces:
          - Neutral: smile_ratio 1.5 – 4.5 (mouth wider than tall)
          - Happy:   smile_ratio > 5.0  (wide open smile / stretched mouth corners)
          - Surprise: mouth_ratio > 0.12 (mouth drops open vertically) + wide eyes
          - Angry:   brow depressed below eye (brow_delta < -0.02)
          - Sad:     brow slightly depressed + mouth corner droop
          - Fear:    wide eyes + raised brows + mouth slightly open
          - Disgust: slight nose/lip curl (approx via face symmetry)

        Only used when no ONNX model is loaded.
        """
        face_mesh = cls._get_face_mesh()
        rgb = cv2.cvtColor(face_bgr, cv2.COLOR_BGR2RGB)
        result = face_mesh.process(rgb)

        if not result or not result.multi_face_landmarks:
            scores = {e: round(1.0 / len(EMOTION_CLASSES) * 100, 1) for e in EMOTION_CLASSES}
            return EmotionResult(
                emotion="neutral", confidence=scores["neutral"],
                all_scores=scores, method="heuristic",
                inference_ms=0.0, model_available=False,
            )

        lms = result.multi_face_landmarks[0].landmark
        h, w = face_bgr.shape[:2]

        def pt(i: int) -> np.ndarray:
            lm = lms[i]
            return np.array([lm.x * w, lm.y * h])

        def dist(i: int, j: int) -> float:
            return float(np.linalg.norm(pt(i) - pt(j)))

        # ── Mouth geometry ────────────────────────────────────────────────────
        # Vertical mouth opening (lips apart): landmark 13 (upper) vs 14 (lower)
        mouth_v = dist(13, 14)
        # Horizontal mouth width: 78 (left corner) vs 308 (right corner)
        mouth_h = dist(78, 308)
        mouth_ratio = float(mouth_v / (mouth_h + 1e-9))   # Openness: 0=closed, 0.3=wide open
        smile_ratio = float(mouth_h / (mouth_v + 1e-9))   # Width/height: high = wide smile

        # ── Eye openness (Eye Aspect Ratio) ───────────────────────────────────
        # Left eye: top=386, bottom=374, left=362, right=263
        left_eye_v  = dist(386, 374)
        left_eye_h  = dist(362, 263)
        left_ear    = left_eye_v / (left_eye_h + 1e-9)

        # Right eye: top=159, bottom=145, left=33, right=133
        right_eye_v = dist(159, 145)
        right_eye_h = dist(33, 133)
        right_ear   = right_eye_v / (right_eye_h + 1e-9)

        eye_open = (left_ear + right_ear) / 2.0   # Typical: 0.15–0.35 open; > 0.35 = wide

        # ── Eyebrow height relative to eye ───────────────────────────────────
        # Left brow top: 285, left eye ref: 386
        # Right brow top: 55, right eye ref: 159
        left_brow_delta  = float(lms[386].y - lms[285].y)   # + = brow above eye (raised)
        right_brow_delta = float(lms[159].y - lms[55].y)
        brow_delta = (left_brow_delta + right_brow_delta) / 2.0

        # ── Mouth corner height (for sad vs happy) ────────────────────────────
        # Compare mouth corner height relative to the mouth center (average of upper & lower inner lips 13, 14).
        # Since y increases downwards, if corners are higher than center, smile_indicator is positive.
        mouth_center_y = (lms[13].y + lms[14].y) / 2.0
        mouth_corners_y = (lms[78].y + lms[308].y) / 2.0
        smile_indicator = mouth_center_y - mouth_corners_y

        # ── Classify emotion from geometry ────────────────────────────────────
        scores: dict[str, float] = {e: 5.0 for e in EMOTION_CLASSES}

        if mouth_ratio > 0.18 and eye_open > 0.30 and brow_delta > 0.02:
            # Wide open mouth + wide eyes + raised brows = surprise
            scores["surprise"] = 72.0
            scores["fear"]     = 18.0
        elif mouth_ratio > 0.22 and smile_ratio < 4.0:
            # Mouth hanging open, not wide smile = surprise/fear
            scores["surprise"] = 55.0
            scores["fear"]     = 25.0
        elif smile_indicator > 0.008:
            # Corners pulled up significantly relative to center = happy
            scores["happy"]   = 78.0
            scores["neutral"] = 10.0
        elif smile_indicator > 0.003 and smile_ratio > 4.0:
            # Mild smile = happy
            scores["happy"]   = 60.0
            scores["neutral"] = 20.0
        elif brow_delta < -0.025 and mouth_ratio < 0.08:
            # Brows pushed DOWN + closed mouth = angry
            scores["angry"]   = 62.0
            scores["disgust"] = 22.0
        elif smile_indicator < -0.008 or (brow_delta < -0.01 and smile_indicator < -0.003):
            # Drooping corners = sad
            scores["sad"]     = 58.0
            scores["neutral"] = 22.0
        elif brow_delta > 0.03 and eye_open > 0.28:
            # Raised brows + wide eyes (without open mouth) = mild surprise or fear
            scores["fear"]     = 45.0
            scores["surprise"] = 25.0
            scores["neutral"]  = 20.0
        else:
            # Default: neutral
            scores["neutral"] = 72.0

        # Normalize
        total = sum(scores.values())
        scores = {k: round(v / total * 100, 1) for k, v in scores.items()}
        dominant = max(scores, key=lambda k: scores[k])

        return EmotionResult(
            emotion=dominant,
            confidence=scores[dominant],
            all_scores=scores,
            method="heuristic",
            inference_ms=0.0,
            model_available=False,
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze(self, face_bgr: np.ndarray) -> EmotionResult:
        """
        Run emotion recognition on a face crop (BGR numpy array).

        Returns EmotionResult with dominant emotion and per-class scores.
        """
        t0 = time.perf_counter()

        if face_bgr is None or face_bgr.size == 0:
            return EmotionResult(
                emotion="neutral", confidence=0.0, all_scores={},
                method="error", inference_ms=0.0, model_available=False,
            )

        if not self._model_loaded or self._session is None:
            result = self._heuristic_emotion(face_bgr)
            result.inference_ms = round((time.perf_counter() - t0) * 1000, 2)
            return result

        try:
            blob = self._preprocess(face_bgr)
            outputs = self._session.run([self._output_name], {self._input_name: blob})
            logits = np.array(outputs[0]).flatten()

            # Softmax
            logits = logits - logits.max()
            exp_logits = np.exp(logits)
            probs = exp_logits / (exp_logits.sum() + 1e-9)

            all_scores = {
                EMOTION_CLASSES[i]: round(float(probs[i]) * 100, 1)
                for i in range(min(len(EMOTION_CLASSES), len(probs)))
            }
            dominant = max(all_scores, key=lambda k: all_scores[k])
            inference_ms = round((time.perf_counter() - t0) * 1000, 2)

            logger.debug(
                "emotion_service.analyze",
                dominant=dominant,
                confidence=all_scores[dominant],
                inference_ms=inference_ms,
            )

            return EmotionResult(
                emotion=dominant,
                confidence=all_scores[dominant],
                all_scores=all_scores,
                method="ferplus",
                inference_ms=inference_ms,
                model_available=True,
            )

        except Exception as exc:
            logger.warning("emotion_service.analyze: ONNX error — using heuristic", error=str(exc))
            result = self._heuristic_emotion(face_bgr)
            result.inference_ms = round((time.perf_counter() - t0) * 1000, 2)
            return result

    def analyze_from_bytes(self, image_bytes: bytes, bbox: tuple[int, int, int, int] | None = None) -> EmotionResult:
        """Decode raw image bytes, optionally crop to bbox, and analyze emotion."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            return EmotionResult(
                emotion="neutral", confidence=0.0, all_scores={},
                method="decode_error", inference_ms=0.0, model_available=False,
            )
        if bbox is not None:
            x1, y1, x2, y2 = bbox
            h, w = img_bgr.shape[:2]
            face_crop = img_bgr[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
        else:
            face_crop = img_bgr
        return self.analyze(face_crop)
