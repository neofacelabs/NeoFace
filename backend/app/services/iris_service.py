"""
NeoFace Iris Recognition Service
Implements the complete iris biometric pipeline:
  1. Iris localization via Hough Circle Transform (OpenCV)
  2. Daugman Rubber Sheet normalization
  3. 2D Gabor wavelet phase extraction → binary IrisCode
  4. Hamming Distance matching across enrolled IrisCodes

Requirements: opencv-python-headless, numpy, scipy
"""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)

# ── Constants ──────────────────────────────────────────────────────────────────
IRIS_CODE_BYTES = 256          # 2048 bits = 256 bytes
IRIS_CODE_BITS = IRIS_CODE_BYTES * 8
GABOR_SCALES = 8               # Number of Gabor filter scales
GABOR_ORIENTATIONS = 8         # Number of Gabor filter orientations
RUBBER_SHEET_RADIAL = 20       # Radial resolution for rubber sheet model
RUBBER_SHEET_ANGULAR = 240     # Angular resolution for rubber sheet model
HAMMING_THRESHOLD = 0.32       # HD < 0.32 → match (Daugman's criterion)
MIN_USABLE_BITS_RATIO = 0.5    # Reject IrisCode if <50% bits are usable


@dataclass
class IrisLocalization:
    """Result of iris and pupil boundary detection."""
    iris_x: int
    iris_y: int
    iris_radius: int
    pupil_x: int
    pupil_y: int
    pupil_radius: int
    quality_score: float


@dataclass
class IrisCode:
    """Binary IrisCode with its occlusion mask."""
    code: bytes                # 256 bytes (2048 bits) of phase information
    mask: bytes                # 256 bytes: 1=reliable, 0=occluded
    usable_bits_ratio: float   # Fraction of reliable bits
    quality_score: float

    @property
    def sha256(self) -> str:
        """SHA-256 of this IrisCode for audit logging (not biometric storage)."""
        return hashlib.sha256(self.code).hexdigest()


@dataclass
class IrisMatchResult:
    """Result of a 1:N iris match scan."""
    matched: bool
    hamming_distance: float     # 0.0 = perfect match, 1.0 = no match
    match_score: float          # 1.0 - hamming_distance, normalized (0–1)
    matched_user_id: str | None
    matched_iris_id: str | None
    threshold_used: float


class IrisService:
    """
    Complete iris biometric pipeline for enrollment and verification.

    Usage:
        service = IrisService()
        iris_code = service.process_image(image_bytes)
        result = service.match(iris_code, enrolled_records)
    """

    def __init__(self, hamming_threshold: float = HAMMING_THRESHOLD) -> None:
        self.hamming_threshold = hamming_threshold
        self._gabor_filters: list | None = None

    # ── Step 1: Iris Localization ─────────────────────────────────────────────

    def localize_iris(self, image: np.ndarray) -> IrisLocalization | None:
        """
        Detect iris and pupil boundaries using Hough Circle Transform.
        Returns None if no valid iris is found.
        """
        try:
            import cv2
        except ImportError:
            logger.error("opencv-python-headless not installed. Run: pip install opencv-python-headless")
            return None

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
        gray = cv2.GaussianBlur(gray, (7, 7), 1.5)

        h, w = gray.shape
        min_iris_radius = int(min(h, w) * 0.15)
        max_iris_radius = int(min(h, w) * 0.45)
        min_pupil_radius = int(min_iris_radius * 0.2)
        max_pupil_radius = int(max_iris_radius * 0.6)

        # Detect iris boundary (larger, lighter circle)
        iris_circles = cv2.HoughCircles(
            gray,
            cv2.HOUGH_GRADIENT,
            dp=1.2,
            minDist=min(h, w) * 0.4,
            param1=60,
            param2=35,
            minRadius=min_iris_radius,
            maxRadius=max_iris_radius,
        )
        if iris_circles is None:
            logger.debug("IrisService: no iris boundary detected")
            return None
        iris = np.round(iris_circles[0][0]).astype(int)
        ix, iy, ir = iris[0], iris[1], iris[2]

        # Detect pupil boundary (smaller, darker circle near iris center)
        roi_size = ir + 30
        x1 = max(0, ix - roi_size)
        y1 = max(0, iy - roi_size)
        x2 = min(w, ix + roi_size)
        y2 = min(h, iy + roi_size)
        roi = gray[y1:y2, x1:x2]

        pupil_circles = cv2.HoughCircles(
            roi,
            cv2.HOUGH_GRADIENT,
            dp=1.0,
            minDist=roi.shape[0] * 0.3,
            param1=70,
            param2=25,
            minRadius=min_pupil_radius,
            maxRadius=min(max_pupil_radius, ir - 5),
        )
        if pupil_circles is None:
            # Fallback: assume pupil is 30% of iris
            px, py, pr = ix, iy, int(ir * 0.3)
        else:
            pupil = np.round(pupil_circles[0][0]).astype(int)
            px = x1 + pupil[0]
            py = y1 + pupil[1]
            pr = pupil[2]

        quality = min(100.0, float(ir) / max_iris_radius * 100)
        return IrisLocalization(
            iris_x=ix, iris_y=iy, iris_radius=ir,
            pupil_x=px, pupil_y=py, pupil_radius=pr,
            quality_score=quality,
        )

    # ── Step 2: Rubber Sheet Normalization ────────────────────────────────────

    def rubber_sheet_normalize(
        self,
        image: np.ndarray,
        loc: IrisLocalization,
        radial_res: int = RUBBER_SHEET_RADIAL,
        angular_res: int = RUBBER_SHEET_ANGULAR,
    ) -> np.ndarray:
        """
        Map the iris annular region to a rectangular strip using Daugman's
        Rubber Sheet Model. Returns a (radial_res × angular_res) normalized band.
        """
        normalized = np.zeros((radial_res, angular_res), dtype=np.uint8)
        gray = image if len(image.shape) == 2 else image[:, :, 0]
        h, w = gray.shape

        for r_idx in range(radial_res):
            r = r_idx / radial_res  # normalized radius 0–1 from pupil to iris
            for theta_idx in range(angular_res):
                theta = 2 * np.pi * theta_idx / angular_res

                # Bilinear interpolation between pupil and iris boundaries
                xi = (1 - r) * (loc.pupil_x + loc.pupil_radius * np.cos(theta)) + \
                     r * (loc.iris_x + loc.iris_radius * np.cos(theta))
                yi = (1 - r) * (loc.pupil_y + loc.pupil_radius * np.sin(theta)) + \
                     r * (loc.iris_y + loc.iris_radius * np.sin(theta))

                xi_i, yi_i = int(np.clip(xi, 0, w - 1)), int(np.clip(yi, 0, h - 1))
                normalized[r_idx, theta_idx] = gray[yi_i, xi_i]

        return normalized

    # ── Step 3: Gabor Feature Extraction → IrisCode ───────────────────────────

    def _build_gabor_filters(self) -> list:
        """Pre-compute 2D Gabor filter bank for IrisCode extraction."""
        try:
            import cv2
        except ImportError:
            return []

        filters = []
        for scale in range(1, GABOR_SCALES + 1):
            for orientation in range(GABOR_ORIENTATIONS):
                theta = orientation * np.pi / GABOR_ORIENTATIONS
                sigma = scale * 2.0
                lambd = sigma * 1.5
                kernel = cv2.getGaborKernel(
                    ksize=(int(sigma * 6) | 1, int(sigma * 6) | 1),
                    sigma=sigma,
                    theta=theta,
                    lambd=lambd,
                    gamma=0.5,
                    psi=0,
                    ktype=cv2.CV_64F,
                )
                filters.append(kernel)
        return filters

    def extract_iris_code(self, normalized_band: np.ndarray) -> IrisCode:
        """
        Apply 2D Gabor wavelets to extract phase bits and build the IrisCode.
        Each Gabor response is thresholded at zero to produce 1-bit phase data.
        """
        try:
            import cv2
        except ImportError:
            # Fallback: random bits (for testing without OpenCV)
            rng = np.random.default_rng(42)
            code_bits = rng.integers(0, 2, IRIS_CODE_BITS, dtype=np.uint8)
            mask_bits = np.ones(IRIS_CODE_BITS, dtype=np.uint8)
            return IrisCode(
                code=np.packbits(code_bits).tobytes(),
                mask=np.packbits(mask_bits).tobytes(),
                usable_bits_ratio=1.0,
                quality_score=50.0,
            )

        if self._gabor_filters is None:
            self._gabor_filters = self._build_gabor_filters()

        band_f64 = normalized_band.astype(np.float64)
        bits_per_filter = IRIS_CODE_BITS // len(self._gabor_filters)
        code_bits = np.zeros(IRIS_CODE_BITS, dtype=np.uint8)
        mask_bits = np.ones(IRIS_CODE_BITS, dtype=np.uint8)

        for i, kernel in enumerate(self._gabor_filters):
            response = cv2.filter2D(band_f64, cv2.CV_64F, kernel)
            flat = response.flatten()

            start = i * bits_per_filter
            end = start + bits_per_filter
            samples = np.linspace(0, len(flat) - 1, bits_per_filter, dtype=int)
            code_bits[start:end] = (flat[samples] >= 0).astype(np.uint8)

            # Mark low-energy regions as occluded
            energy = np.abs(flat[samples])
            threshold = np.percentile(energy, 15)
            mask_bits[start:end] = (energy >= threshold).astype(np.uint8)

        usable_ratio = float(np.mean(mask_bits))
        quality = min(100.0, usable_ratio * 100)

        return IrisCode(
            code=np.packbits(code_bits).tobytes(),
            mask=np.packbits(mask_bits).tobytes(),
            usable_bits_ratio=usable_ratio,
            quality_score=quality,
        )

    # ── Step 4: Hamming Distance Matching ─────────────────────────────────────

    @staticmethod
    def hamming_distance(
        code1: bytes,
        mask1: bytes | None,
        code2: bytes,
        mask2: bytes | None,
    ) -> float:
        """
        Compute normalized Hamming Distance between two IrisCodes.
        Bits masked as unreliable in either code are excluded from comparison.
        Returns HD in [0.0, 1.0] — lower = more similar.
        """
        c1 = np.frombuffer(code1, dtype=np.uint8)
        c2 = np.frombuffer(code2, dtype=np.uint8)

        # Unpack to bit arrays
        b1 = np.unpackbits(c1)
        b2 = np.unpackbits(c2)

        # Combined mask: only compare reliable bits in BOTH codes
        if mask1 and mask2:
            m1 = np.unpackbits(np.frombuffer(mask1, dtype=np.uint8))
            m2 = np.unpackbits(np.frombuffer(mask2, dtype=np.uint8))
            combined_mask = m1 & m2
        else:
            combined_mask = np.ones(len(b1), dtype=np.uint8)

        usable = np.sum(combined_mask)
        if usable < 100:
            # Too few reliable bits — return high distance (no match)
            return 1.0

        xor_bits = np.bitwise_xor(b1[:len(b2)], b2)
        hd = float(np.sum(xor_bits & combined_mask)) / float(usable)
        return hd

    def match(
        self,
        query_code: IrisCode,
        enrolled_records: list,  # list of IrisEmbedding ORM objects
    ) -> IrisMatchResult:
        """
        1:N iris matching. Scans all enrolled IrisCodes and returns the best match.
        """
        if not enrolled_records:
            return IrisMatchResult(
                matched=False,
                hamming_distance=1.0,
                match_score=0.0,
                matched_user_id=None,
                matched_iris_id=None,
                threshold_used=self.hamming_threshold,
            )

        if query_code.usable_bits_ratio < MIN_USABLE_BITS_RATIO:
            return IrisMatchResult(
                matched=False,
                hamming_distance=1.0,
                match_score=0.0,
                matched_user_id=None,
                matched_iris_id=None,
                threshold_used=self.hamming_threshold,
            )

        best_hd = 1.0
        best_record = None

        for record in enrolled_records:
            hd = self.hamming_distance(
                query_code.code, query_code.mask,
                record.iris_code, record.iris_mask,
            )
            if hd < best_hd:
                best_hd = hd
                best_record = record

        matched = best_hd < self.hamming_threshold
        match_score = max(0.0, 1.0 - (best_hd / self.hamming_threshold)) if matched else 0.0

        return IrisMatchResult(
            matched=matched,
            hamming_distance=best_hd,
            match_score=round(match_score, 4),
            matched_user_id=str(best_record.user_id) if (matched and best_record) else None,
            matched_iris_id=str(best_record.id) if (matched and best_record) else None,
            threshold_used=self.hamming_threshold,
        )

    # ── Full Pipeline ─────────────────────────────────────────────────────────

    def process_image(self, image_bytes: bytes) -> IrisCode | None:
        """
        Full pipeline: bytes → IrisCode.
        Returns None if no valid iris can be extracted.
        """
        try:
            import cv2
        except ImportError:
            logger.error("opencv-python-headless required for iris processing")
            return None

        nparr = np.frombuffer(image_bytes, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if image is None:
            logger.warning("IrisService: could not decode image")
            return None

        loc = self.localize_iris(image)
        if loc is None:
            logger.warning("IrisService: iris not detected in image")
            return None

        if loc.quality_score < 20:
            logger.warning("IrisService: iris quality too low", quality=loc.quality_score)
            return None

        normalized = self.rubber_sheet_normalize(image, loc)
        iris_code = self.extract_iris_code(normalized)
        iris_code.quality_score = loc.quality_score
        return iris_code

    # ── Singleton ─────────────────────────────────────────────────────────────
    _instance: "IrisService | None" = None

    @classmethod
    def get_instance(cls) -> "IrisService":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
