"""
NeoFace Trust Engine — Head Pose Estimation Service (Module 4)
Verifies 3D face movement using MediaPipe FaceMesh + OpenCV solvePnP.

Calculates:
  - Pitch  (nodding up/down)
  - Roll   (tilting sideways)
  - Yaw    (turning left/right)

Output:
  { "pitch": 12, "yaw": -17, "roll": 4 }
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import ClassVar

import cv2
import mediapipe as mp
import numpy as np

from app.core.logging import logger


@dataclass
class HeadPoseResult:
    """Structured output from the head pose estimation service."""
    pitch: float       # Degrees — positive = looking up
    yaw: float         # Degrees — positive = facing right
    roll: float        # Degrees — positive = tilting clockwise
    is_frontal: bool   # True if pose is within acceptable range for face auth
    is_extreme: bool   # True if pose is suspiciously extreme (beyond ±45°)
    inference_ms: float
    method: str        # mediapipe_solvepnp | mediapipe_geometry


# 3D model points of key facial landmarks in object space (generic face model)
# Landmarks: nose tip, chin, left eye outer, right eye outer, left mouth, right mouth
_MODEL_3D_POINTS = np.array([
    (0.0,    0.0,    0.0),     # Nose tip (landmark 1)
    (0.0,   -63.6,  -12.5),    # Chin (landmark 152)
    (-43.3,  32.7,  -26.0),    # Left eye outer corner (landmark 263)
    (43.3,   32.7,  -26.0),    # Right eye outer corner (landmark 33)
    (-28.9, -28.9,  -24.1),    # Left mouth corner (landmark 287)
    (28.9,  -28.9,  -24.1),    # Right mouth corner (landmark 57)
], dtype=np.float64)

# Corresponding 2D landmark indices in MediaPipe FaceMesh
_LANDMARK_2D_IDS = [1, 152, 263, 33, 287, 57]

# Frontal threshold (degrees)
_FRONTAL_YAW_MAX   = 30.0
_FRONTAL_PITCH_MAX = 25.0
_FRONTAL_ROLL_MAX  = 20.0
_EXTREME_THRESHOLD = 45.0


class HeadPoseService:
    """
    Singleton head pose estimation service.
    Uses MediaPipe FaceMesh for landmark detection and OpenCV solvePnP for pose.
    """

    _instance: ClassVar[HeadPoseService | None] = None

    def __init__(self) -> None:
        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.4,
            min_tracking_confidence=0.4,
        )

    @classmethod
    def get_instance(cls) -> HeadPoseService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── solvePnP pose estimation ──────────────────────────────────────────────

    def _estimate_pose_pnp(
        self,
        landmarks,
        h: int,
        w: int,
    ) -> tuple[float, float, float] | None:
        """
        Use OpenCV solvePnP to estimate rotation from 6 facial landmarks.
        Returns (pitch, yaw, roll) in degrees or None on failure.
        """
        # Build 2D image points from MediaPipe landmarks
        image_2d = np.array([
            (landmarks[idx].x * w, landmarks[idx].y * h)
            for idx in _LANDMARK_2D_IDS
        ], dtype=np.float64)

        # Camera intrinsics (approximate for unknown camera)
        focal_length = w
        center = (w / 2, h / 2)
        camera_matrix = np.array([
            [focal_length, 0,            center[0]],
            [0,            focal_length, center[1]],
            [0,            0,            1],
        ], dtype=np.float64)

        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        success, rvec, tvec = cv2.solvePnP(
            _MODEL_3D_POINTS,
            image_2d,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )

        if not success:
            return None

        # Convert rotation vector to rotation matrix
        rmat, _ = cv2.Rodrigues(rvec)

        # Decompose rotation matrix to Euler angles
        # Using standard decomposition: yaw(y), pitch(x), roll(z)
        sy = float(np.sqrt(rmat[0, 0] ** 2 + rmat[1, 0] ** 2))
        singular = sy < 1e-6

        if not singular:
            pitch_r = float(np.arctan2(rmat[2, 1], rmat[2, 2]))
            yaw_r   = float(np.arctan2(-rmat[2, 0], sy))
            roll_r  = float(np.arctan2(rmat[1, 0], rmat[0, 0]))
        else:
            pitch_r = float(np.arctan2(-rmat[1, 2], rmat[1, 1]))
            yaw_r   = float(np.arctan2(-rmat[2, 0], sy))
            roll_r  = 0.0

        pitch_deg = float(np.degrees(pitch_r))
        yaw_deg   = float(np.degrees(yaw_r))
        roll_deg  = float(np.degrees(roll_r))

        return pitch_deg, yaw_deg, roll_deg

    # ── Geometric fallback ────────────────────────────────────────────────────

    @staticmethod
    def _estimate_pose_geometry(landmarks, h: int, w: int) -> tuple[float, float, float]:
        """
        Simpler geometry-based pose estimation from nose tip position.
        Less accurate than solvePnP but always succeeds.
        """
        nose = landmarks[1]  # Nose tip
        yaw   = float((nose.x - 0.5) * 90.0)
        pitch = float((nose.y - 0.5) * -60.0)

        # Roll from eye alignment
        left_eye  = np.array([landmarks[263].x * w, landmarks[263].y * h])
        right_eye = np.array([landmarks[33].x * w,  landmarks[33].y * h])
        delta = right_eye - left_eye
        roll = float(np.degrees(np.arctan2(delta[1], delta[0])))

        return pitch, yaw, roll

    # ── Public API ────────────────────────────────────────────────────────────

    def estimate(self, image_bytes: bytes) -> HeadPoseResult:
        """
        Estimate head pose from raw JPEG/PNG image bytes.

        Returns HeadPoseResult with pitch, roll, yaw in degrees.
        """
        t0 = time.perf_counter()

        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_bgr is None:
            return HeadPoseResult(pitch=0.0, yaw=0.0, roll=0.0,
                                  is_frontal=False, is_extreme=False,
                                  inference_ms=0.0, method="decode_error")

        h, w = img_bgr.shape[:2]
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        result = self._face_mesh.process(img_rgb)

        inference_ms = round((time.perf_counter() - t0) * 1000, 2)

        if not result or not result.multi_face_landmarks:
            return HeadPoseResult(pitch=0.0, yaw=0.0, roll=0.0,
                                  is_frontal=False, is_extreme=False,
                                  inference_ms=inference_ms, method="no_face")

        landmarks = result.multi_face_landmarks[0].landmark

        # Try solvePnP first, fall back to geometry
        pnp_result = self._estimate_pose_pnp(landmarks, h, w)
        if pnp_result is not None:
            pitch, yaw, roll = pnp_result
            method = "mediapipe_solvepnp"
        else:
            pitch, yaw, roll = self._estimate_pose_geometry(landmarks, h, w)
            method = "mediapipe_geometry"

        pitch = round(pitch, 2)
        yaw   = round(yaw, 2)
        roll  = round(roll, 2)

        is_frontal = (
            abs(yaw)   <= _FRONTAL_YAW_MAX
            and abs(pitch) <= _FRONTAL_PITCH_MAX
            and abs(roll)  <= _FRONTAL_ROLL_MAX
        )
        is_extreme = (
            abs(yaw) > _EXTREME_THRESHOLD
            or abs(pitch) > _EXTREME_THRESHOLD
            or abs(roll) > _EXTREME_THRESHOLD
        )

        logger.debug(
            "headpose.estimate",
            pitch=pitch, yaw=yaw, roll=roll,
            is_frontal=is_frontal, method=method,
        )

        return HeadPoseResult(
            pitch=pitch, yaw=yaw, roll=roll,
            is_frontal=is_frontal, is_extreme=is_extreme,
            inference_ms=inference_ms, method=method,
        )
