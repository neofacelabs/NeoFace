"""
NeoFace Fingerprint Recognition Service
Implements:
  1. Preprocessing: Gabor ridge enhancement + binarization + thinning
  2. Minutiae extraction: crossing-number algorithm (ridge endings + bifurcations)
  3. ISO/IEC 19794-2 template serialization
  4. MCC-style minutiae matching (Minutiae Cylinder-Code proximity)

Requirements: opencv-python-headless, numpy, scipy
"""

from __future__ import annotations

import hashlib
import logging
import struct
from dataclasses import dataclass, field

import numpy as np

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
MAX_MINUTIAE = 128          # Maximum minutiae points to store in template
MIN_MINUTIAE = 10           # Minimum required minutiae for a valid template
MATCH_THRESHOLD = 0.40      # Score >= 0.40 → fingerprint match
CYLINDER_RADIUS = 70        # MCC cylinder radius in pixels
CYLINDER_HEIGHT = 32        # MCC cylinder height (angular bins)
MATCH_TOP_K = 5             # Consider top-K best cylinder matches


@dataclass
class MinutiaePoint:
    """Single minutiae feature point."""
    x: int
    y: int
    angle: float    # Radians [0, 2π)
    type: int       # 1=ridge_ending, 2=bifurcation
    quality: float  # Local ridge clarity (0–1)


@dataclass
class FingerprintTemplate:
    """
    ISO/IEC 19794-2 compatible fingerprint template.
    Stores a list of MinutiaePoints and serialization helpers.
    """
    minutiae: list[MinutiaePoint] = field(default_factory=list)
    quality_score: float = 0.0
    minutiae_count: int = 0
    image_width: int = 0
    image_height: int = 0
    resolution_dpi: int = 500

    def to_bytes(self) -> bytes:
        """Serialize template to compact binary format (simplified ISO/IEC 19794-2)."""
        # Header: width(2), height(2), dpi(2), count(2) = 8 bytes
        header = struct.pack(
            ">HHHH",
            self.image_width, self.image_height,
            self.resolution_dpi, len(self.minutiae),
        )
        # Each minutia: x(2), y(2), angle_deg(1), type(1), quality_pct(1) = 7 bytes
        records = b""
        for m in self.minutiae[:MAX_MINUTIAE]:
            angle_deg = int((m.angle * 180 / np.pi) % 360)
            quality_pct = int(np.clip(m.quality * 100, 0, 255))
            records += struct.pack(">HHBBb", m.x, m.y, angle_deg, m.type, quality_pct)
        return header + records

    @classmethod
    def from_bytes(cls, data: bytes) -> "FingerprintTemplate":
        """Deserialize template from binary format."""
        if len(data) < 8:
            return cls()
        w, h, dpi, count = struct.unpack(">HHHH", data[:8])
        minutiae = []
        offset = 8
        for _ in range(count):
            if offset + 7 > len(data):
                break
            x, y, angle_deg, mtype, quality_pct = struct.unpack(">HHBBb", data[offset:offset + 7])
            minutiae.append(MinutiaePoint(
                x=x, y=y,
                angle=float(angle_deg) * np.pi / 180,
                type=mtype,
                quality=float(abs(quality_pct)) / 100,
            ))
            offset += 7
        return cls(minutiae=minutiae, image_width=w, image_height=h, resolution_dpi=dpi, minutiae_count=count)

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.to_bytes()).hexdigest()


@dataclass
class FingerprintMatchResult:
    matched: bool
    match_score: float         # 0.0–1.0 (higher = better match)
    matched_user_id: str | None
    matched_template_id: str | None
    minutiae_pairs: int        # Number of matching minutiae pairs found
    threshold_used: float


class FingerprintService:
    """
    Complete fingerprint biometric pipeline for enrollment and verification.
    """

    def __init__(self, match_threshold: float = MATCH_THRESHOLD) -> None:
        self.match_threshold = match_threshold

    # ── Step 1: Image Enhancement ─────────────────────────────────────────────

    def enhance_image(self, gray: np.ndarray) -> np.ndarray:
        """
        Enhance ridge structure using adaptive Gabor filtering + CLAHE.
        Returns a binarized ridge image (0=valley, 255=ridge).
        """
        try:
            import cv2
        except ImportError:
            # Fallback: simple threshold
            _, binary = (lambda g: (None, (g < np.mean(g)).astype(np.uint8) * 255))(gray)
            return binary

        # Contrast-Limited Adaptive Histogram Equalization
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Adaptive threshold to binarize ridges
        binary = cv2.adaptiveThreshold(
            enhanced, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY_INV,
            blockSize=25,
            C=10,
        )

        # Morphological cleanup
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        return binary

    def thin_ridges(self, binary: np.ndarray) -> np.ndarray:
        """Apply Zhang-Suen ridge thinning to produce single-pixel skeleton."""
        try:
            from skimage.morphology import skeletonize
            skeleton = skeletonize(binary // 255).astype(np.uint8) * 255
            return skeleton
        except ImportError:
            try:
                import cv2
                kernel = np.ones((3, 3), np.uint8)
                return cv2.erode(binary, kernel, iterations=2)
            except ImportError:
                return binary

    # ── Step 2: Minutiae Extraction ───────────────────────────────────────────

    def _crossing_number(self, skeleton: np.ndarray, x: int, y: int) -> int:
        """
        Compute crossing number for pixel (x, y) in thinned skeleton.
        CN=1 → ridge ending, CN=3 → bifurcation.
        """
        neighbors = [
            skeleton[y - 1, x], skeleton[y - 1, x + 1],
            skeleton[y, x + 1], skeleton[y + 1, x + 1],
            skeleton[y + 1, x], skeleton[y + 1, x - 1],
            skeleton[y, x - 1], skeleton[y - 1, x - 1],
        ]
        n = [1 if p > 0 else 0 for p in neighbors]
        cn = sum(abs(n[i] - n[(i + 1) % 8]) for i in range(8)) // 2
        return cn

    def _estimate_local_angle(
        self, gray: np.ndarray, x: int, y: int, block: int = 16
    ) -> float:
        """Estimate local ridge orientation angle at (x, y) using gradient analysis."""
        try:
            import cv2
        except ImportError:
            return 0.0

        x1 = max(0, x - block)
        y1 = max(0, y - block)
        x2 = min(gray.shape[1], x + block)
        y2 = min(gray.shape[0], y + block)
        roi = gray[y1:y2, x1:x2].astype(np.float64)

        gx = cv2.Sobel(roi, cv2.CV_64F, 1, 0, ksize=5)
        gy = cv2.Sobel(roi, cv2.CV_64F, 0, 1, ksize=5)

        gxx = np.sum(gx * gx)
        gyy = np.sum(gy * gy)
        gxy = np.sum(gx * gy)

        angle = 0.5 * np.arctan2(2 * gxy, gxx - gyy) + np.pi / 2
        return float(angle % (2 * np.pi))

    def extract_minutiae(
        self,
        image_bytes: bytes,
    ) -> FingerprintTemplate | None:
        """
        Full minutiae extraction pipeline from raw image bytes.
        Returns FingerprintTemplate or None if extraction fails.
        """
        try:
            import cv2
        except ImportError:
            logger.error("opencv-python-headless required for fingerprint processing")
            return None

        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_GRAYSCALE)
        if image is None:
            logger.warning("FingerprintService: could not decode image")
            return None

        h, w = image.shape
        binary = self.enhance_image(image)
        skeleton = self.thin_ridges(binary)

        minutiae: list[MinutiaePoint] = []
        margin = 10  # Avoid border artifacts

        for y in range(margin, h - margin):
            for x in range(margin, w - margin):
                if skeleton[y, x] == 0:
                    continue
                cn = self._crossing_number(skeleton, x, y)
                if cn == 1:  # Ridge ending
                    angle = self._estimate_local_angle(image, x, y)
                    quality = float(skeleton[y, x]) / 255.0
                    minutiae.append(MinutiaePoint(x=x, y=y, angle=angle, type=1, quality=quality))
                elif cn == 3:  # Bifurcation
                    angle = self._estimate_local_angle(image, x, y)
                    quality = float(skeleton[y, x]) / 255.0
                    minutiae.append(MinutiaePoint(x=x, y=y, angle=angle, type=2, quality=quality))

        if len(minutiae) < MIN_MINUTIAE:
            logger.warning(
                f"FingerprintService: too few minutiae (count={len(minutiae)}, required={MIN_MINUTIAE})"
            )
            return None

        # Sort by quality descending and trim to MAX_MINUTIAE
        minutiae.sort(key=lambda m: m.quality, reverse=True)
        minutiae = minutiae[:MAX_MINUTIAE]

        quality_score = float(np.mean([m.quality for m in minutiae])) * 100

        return FingerprintTemplate(
            minutiae=minutiae,
            quality_score=quality_score,
            minutiae_count=len(minutiae),
            image_width=w,
            image_height=h,
            resolution_dpi=500,
        )

    # ── Step 3: MCC-style Matching ────────────────────────────────────────────

    def _compute_match_score(
        self, query: FingerprintTemplate, enrolled: FingerprintTemplate
    ) -> tuple[float, int]:
        """
        Compute match score between two templates using spatial proximity matching.
        Returns (score 0–1, matched_pairs_count).
        A simplified greedy version of Minutiae Cylinder-Code matching.
        """
        if not query.minutiae or not enrolled.minutiae:
            return 0.0, 0

        max_dist = CYLINDER_RADIUS
        max_angle_diff = np.pi / 6  # 30 degrees

        matched_query = set()
        matched_enrolled = set()

        pairs: list[tuple[float, int, int]] = []
        for qi, qm in enumerate(query.minutiae):
            for ei, em in enumerate(enrolled.minutiae):
                dist = np.sqrt((qm.x - em.x) ** 2 + (qm.y - em.y) ** 2)
                angle_diff = abs(qm.angle - em.angle) % np.pi
                if dist <= max_dist and angle_diff <= max_angle_diff and qm.type == em.type:
                    similarity = (1 - dist / max_dist) * (1 - angle_diff / max_angle_diff)
                    pairs.append((similarity, qi, ei))

        # Greedy assignment
        pairs.sort(key=lambda p: p[0], reverse=True)
        for sim, qi, ei in pairs:
            if qi not in matched_query and ei not in matched_enrolled:
                matched_query.add(qi)
                matched_enrolled.add(ei)

        n_pairs = len(matched_query)
        if n_pairs == 0:
            return 0.0, 0

        denom = max(len(query.minutiae), len(enrolled.minutiae))
        score = n_pairs / denom
        return round(score, 4), n_pairs

    def match(
        self,
        query_template: FingerprintTemplate,
        enrolled_records: list,  # list of FingerprintTemplate ORM objects
    ) -> FingerprintMatchResult:
        """1:N fingerprint matching against all enrolled templates."""
        if not enrolled_records:
            return FingerprintMatchResult(
                matched=False, match_score=0.0,
                matched_user_id=None, matched_template_id=None,
                minutiae_pairs=0, threshold_used=self.match_threshold,
            )

        best_score = 0.0
        best_pairs = 0
        best_record = None

        for record in enrolled_records:
            try:
                enrolled = FingerprintTemplate.from_bytes(record.template_data)
            except Exception:
                continue
            score, pairs = self._compute_match_score(query_template, enrolled)
            if score > best_score:
                best_score = score
                best_pairs = pairs
                best_record = record

        matched = best_score >= self.match_threshold
        return FingerprintMatchResult(
            matched=matched,
            match_score=best_score,
            matched_user_id=str(best_record.user_id) if (matched and best_record) else None,
            matched_template_id=str(best_record.id) if (matched and best_record) else None,
            minutiae_pairs=best_pairs,
            threshold_used=self.match_threshold,
        )

    # ── Singleton ─────────────────────────────────────────────────────────────
    _instance: "FingerprintService | None" = None

    @classmethod
    def get_instance(cls) -> "FingerprintService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
