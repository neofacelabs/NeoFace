"""
NeoFace Trust Engine — Active Liveness Service (Module 2)
Randomized human interaction challenge-response liveness detection.

Supported challenge actions:
  blink, smile, open_mouth, turn_left, turn_right,
  raise_eyebrows, look_up, look_down

Challenge Engine generates multi-step sequences like:
  - blink_twice
  - turn_left + smile
  - open_mouth + blink
  - look_up + smile
  - raise_eyebrows + turn_right

Uses MediaPipe FaceMesh (468 landmarks) for real-time verification.

Output:
  { "challenge_completed": true, "challenge_type": "blink_twice" }
"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import ClassVar

import cv2
import mediapipe as mp
import numpy as np

from app.core.logging import logger

# ── Landmark indices ──────────────────────────────────────────────────────────
_LEFT_EYE  = [362, 385, 387, 263, 373, 380]
_RIGHT_EYE = [33,  160, 158, 133, 153, 144]
_MOUTH_TOP, _MOUTH_BOTTOM = 13, 14
_MOUTH_LEFT, _MOUTH_RIGHT = 78, 308
_NOSE_TIP = 1

# Left eyebrow: 276, 283, 282, 295, 285; right: 46, 53, 52, 65, 55
_LEFT_BROW_TOP    = [285, 295, 282, 283, 276]
_LEFT_BROW_BOTTOM = [386, 374, 380, 373, 390]
_RIGHT_BROW_TOP   = [55, 65, 52, 53, 46]
_RIGHT_BROW_BOTTOM = [159, 145, 153, 144, 163]

# ── Detection thresholds ──────────────────────────────────────────────────────
_EAR_BLINK_THRESHOLD    = 0.20   # EAR below this = blink
_SMILE_THRESHOLD        = 0.28   # Mouth width-to-height ratio
_MOUTH_OPEN_THRESHOLD   = 0.05   # Mouth opening ratio
_YAW_TURN_THRESHOLD     = 18.0   # Degrees for head turn
_PITCH_LOOKUP_THRESHOLD = 12.0   # Degrees for look up/down
_BROW_RAISE_THRESHOLD   = 0.03   # Normalized brow lift

# ── Challenge catalog ─────────────────────────────────────────────────────────
CHALLENGE_CATALOG: list[tuple[str, list[str]]] = [
    ("blink_twice",           ["blink", "blink"]),
    ("turn_left_smile",       ["turn_left", "smile"]),
    ("open_mouth_blink",      ["open_mouth", "blink"]),
    ("look_up_smile",         ["look_up", "smile"]),
    ("raise_eyebrows_turn_right", ["raise_eyebrows", "turn_right"]),
    ("smile_blink",           ["smile", "blink"]),
    ("turn_right_open_mouth", ["turn_right", "open_mouth"]),
    ("look_down_blink",       ["look_down", "blink"]),
    ("raise_eyebrows_smile",  ["raise_eyebrows", "smile"]),
    ("turn_left_open_mouth",  ["turn_left", "open_mouth"]),
]

ACTION_DESCRIPTIONS: dict[str, str] = {
    "blink":          "Blink your eyes",
    "smile":          "Smile",
    "open_mouth":     "Open your mouth",
    "turn_left":      "Turn your head left",
    "turn_right":     "Turn your head right",
    "raise_eyebrows": "Raise your eyebrows",
    "look_up":        "Look up",
    "look_down":      "Look down",
}


@dataclass
class ActiveChallenge:
    """A generated challenge sent to the client."""
    challenge_id: str
    challenge_type: str           # e.g. "blink_twice"
    steps: list[str]              # Ordered list of required actions
    descriptions: list[str]       # Human-readable instructions
    nonce: str
    expires_at: float             # Unix timestamp


@dataclass
class ActiveLivenessResult:
    """Result of verifying one or more challenge frames."""
    challenge_completed: bool
    challenge_type: str
    steps_completed: list[str] = field(default_factory=list)
    steps_pending: list[str] = field(default_factory=list)
    confidence: float = 0.0
    inference_ms: float = 0.0
    failure_reason: str | None = None

    # Per-action landmark data (for audit)
    landmark_signals: dict | None = None


@dataclass
class FrameSignals:
    """MediaPipe-derived signals from a single frame."""
    ear_avg: float = 0.0
    blink_detected: bool = False
    mouth_open: bool = False
    mouth_smile: bool = False
    yaw: float = 0.0
    pitch: float = 0.0
    turn_left: bool = False
    turn_right: bool = False
    look_up: bool = False
    look_down: bool = False
    brow_raised: bool = False


class ActiveLivenessService:
    """
    Singleton service for active liveness challenge generation and verification.

    Usage:
        service = ActiveLivenessService.get_instance()
        challenge = service.generate_challenge(user_id="...", last_challenge_type="blink_twice")
        result = service.verify_frame(image_bytes, challenge)
    """

    _instance: ClassVar[ActiveLivenessService | None] = None

    def __init__(self) -> None:
        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    @classmethod
    def get_instance(cls) -> ActiveLivenessService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Challenge generation ──────────────────────────────────────────────────

    def generate_challenge(
        self,
        last_challenge_type: str | None = None,
    ) -> dict:
        """
        Generate a random challenge, never repeating the last one.

        Returns a dict suitable for JSON serialization and Redis storage.
        """
        import secrets
        import time as time_mod

        available = [
            (ct, steps) for ct, steps in CHALLENGE_CATALOG
            if ct != last_challenge_type
        ]
        if not available:
            # Fallback if somehow all are excluded
            available = CHALLENGE_CATALOG

        challenge_type, steps = random.choice(available)

        nonce = secrets.token_hex(16)
        challenge_id = secrets.token_urlsafe(12)

        return {
            "challenge_id": challenge_id,
            "challenge_type": challenge_type,
            "steps": steps,
            "descriptions": [ACTION_DESCRIPTIONS[s] for s in steps],
            "nonce": nonce,
            "expires_at": time_mod.time() + 60,  # 60 second window
            "created_at": time_mod.time(),
        }

    # ── Frame analysis ────────────────────────────────────────────────────────

    def _extract_signals(self, image_bytes: bytes) -> FrameSignals | None:
        """Decode image and extract MediaPipe landmark signals."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img_bgr is None:
            return None

        h, w = img_bgr.shape[:2]
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        result = self._face_mesh.process(img_rgb)

        if not result or not result.multi_face_landmarks:
            return None

        lms = result.multi_face_landmarks[0].landmark

        def pt(i: int) -> np.ndarray:
            lm = lms[i]
            return np.array([lm.x * w, lm.y * h])

        # EAR
        def ear(indices: list[int]) -> float:
            p1, p2, p3, p4, p5, p6 = [pt(i) for i in indices]
            h_dist = np.linalg.norm(p1 - p4)
            if h_dist < 1e-9:
                return 0.0
            return float((np.linalg.norm(p2 - p6) + np.linalg.norm(p3 - p5)) / (2 * h_dist))

        ear_l = ear(_LEFT_EYE)
        ear_r = ear(_RIGHT_EYE)
        ear_avg = (ear_l + ear_r) / 2.0

        # Mouth
        mouth_top = pt(_MOUTH_TOP)
        mouth_bot = pt(_MOUTH_BOTTOM)
        mouth_left = pt(_MOUTH_LEFT)
        mouth_right_pt = pt(_MOUTH_RIGHT)
        v_mouth = np.linalg.norm(mouth_top - mouth_bot)
        h_mouth = np.linalg.norm(mouth_left - mouth_right_pt)
        mouth_open_ratio = float(v_mouth / h_mouth) if h_mouth > 0 else 0.0
        smile_ratio = float(h_mouth / (v_mouth + 1e-9))

        # Yaw / Pitch from nose tip offset
        nose = lms[_NOSE_TIP]
        yaw = float((nose.x - 0.5) * 90.0)
        pitch = float((nose.y - 0.5) * -60.0)

        # Eyebrow raise
        def brow_lift(top_ids: list[int], bottom_ids: list[int]) -> float:
            top_y = np.mean([lms[i].y for i in top_ids])
            bot_y = np.mean([lms[i].y for i in bottom_ids])
            return float(bot_y - top_y)  # positive = brow above eye

        brow_l = brow_lift(_LEFT_BROW_TOP, _LEFT_BROW_BOTTOM)
        brow_r = brow_lift(_RIGHT_BROW_TOP, _RIGHT_BROW_BOTTOM)
        brow_avg = (brow_l + brow_r) / 2.0

        return FrameSignals(
            ear_avg=ear_avg,
            blink_detected=ear_avg < _EAR_BLINK_THRESHOLD,
            mouth_open=mouth_open_ratio > _MOUTH_OPEN_THRESHOLD,
            mouth_smile=smile_ratio > _SMILE_THRESHOLD,
            yaw=yaw,
            pitch=pitch,
            turn_left=yaw < -_YAW_TURN_THRESHOLD,
            turn_right=yaw > _YAW_TURN_THRESHOLD,
            look_up=pitch > _PITCH_LOOKUP_THRESHOLD,
            look_down=pitch < -_PITCH_LOOKUP_THRESHOLD,
            brow_raised=brow_avg > _BROW_RAISE_THRESHOLD,
        )

    # ── Action verification ───────────────────────────────────────────────────

    def _check_action(self, action: str, signals: FrameSignals) -> bool:
        """Return True if the action is detected in the given frame signals."""
        return {
            "blink":          signals.blink_detected,
            "smile":          signals.mouth_smile,
            "open_mouth":     signals.mouth_open,
            "turn_left":      signals.turn_left,
            "turn_right":     signals.turn_right,
            "raise_eyebrows": signals.brow_raised,
            "look_up":        signals.look_up,
            "look_down":      signals.look_down,
        }.get(action, False)

    # ── Public verify API ─────────────────────────────────────────────────────

    def verify_frame(
        self,
        image_bytes: bytes,
        challenge: dict,
        completed_steps: list[str] | None = None,
    ) -> ActiveLivenessResult:
        """
        Verify a single frame against the active challenge.

        Args:
            image_bytes:     Raw JPEG/PNG frame from the client.
            challenge:       The challenge dict from generate_challenge().
            completed_steps: Steps already verified in previous frames.

        Returns:
            ActiveLivenessResult indicating current completion state.
        """
        t0 = time.perf_counter()
        completed_steps = completed_steps or []
        steps: list[str] = challenge.get("steps", [])
        challenge_type: str = challenge.get("challenge_type", "unknown")

        # Check expiry
        import time as time_mod
        if time_mod.time() > challenge.get("expires_at", 0):
            return ActiveLivenessResult(
                challenge_completed=False,
                challenge_type=challenge_type,
                steps_completed=completed_steps,
                steps_pending=steps,
                failure_reason="challenge_expired",
                inference_ms=0.0,
            )

        # Determine which step to verify next (slice based on count to handle repeats correctly)
        pending = steps[len(completed_steps):]
        if not pending:
            return ActiveLivenessResult(
                challenge_completed=True,
                challenge_type=challenge_type,
                steps_completed=completed_steps,
                steps_pending=[],
                confidence=100.0,
                inference_ms=0.0,
            )

        current_action = pending[0]

        # Extract signals
        signals = self._extract_signals(image_bytes)
        inference_ms = round((time.perf_counter() - t0) * 1000, 2)

        if signals is None:
            return ActiveLivenessResult(
                challenge_completed=False,
                challenge_type=challenge_type,
                steps_completed=completed_steps,
                steps_pending=pending,
                failure_reason="no_face_detected",
                inference_ms=inference_ms,
            )

        action_passed = self._check_action(current_action, signals)
        new_completed = completed_steps + ([current_action] if action_passed else [])
        new_pending = steps[len(new_completed):]

        all_done = len(new_pending) == 0
        confidence = round((len(new_completed) / max(len(steps), 1)) * 100.0, 1)

        logger.debug(
            "active_liveness.verify_frame",
            action=current_action,
            passed=action_passed,
            completed=new_completed,
            pending=new_pending,
            challenge_type=challenge_type,
        )

        return ActiveLivenessResult(
            challenge_completed=all_done,
            challenge_type=challenge_type,
            steps_completed=new_completed,
            steps_pending=new_pending,
            confidence=confidence,
            inference_ms=inference_ms,
            landmark_signals={
                "ear_avg": round(signals.ear_avg, 4),
                "mouth_open": signals.mouth_open,
                "mouth_smile": signals.mouth_smile,
                "yaw": round(signals.yaw, 2),
                "pitch": round(signals.pitch, 2),
                "brow_raised": signals.brow_raised,
            },
        )
