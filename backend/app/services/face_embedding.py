"""
NeoFace Face Embedding Service
Generates ArcFace 512-dimensional embeddings and handles similarity comparison.

Relies on InsightFace's built-in ArcFace recognition module (buffalo_l includes it).
Provides:
- get_embedding(): extract 512-d vector from a DetectedFace
- compare_embeddings(): cosine similarity between two vectors
- average_embeddings(): merge multiple enrollment embeddings
"""

from __future__ import annotations

import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.services.face_detector import DetectedFace


class FaceEmbeddingService:
    """
    ArcFace embedding generation and comparison service.

    Embeddings are L2-normalized 512-d float32 vectors.
    Similarity is measured as cosine similarity (dot product of normalized vectors).
    """

    EMBEDDING_DIM: int = 512

    @staticmethod
    def calibrate_similarity_score(raw_similarity: float) -> float:
        """
        Calibrate raw ArcFace cosine similarity [-1, 1] to a user-friendly 0-100 score.
        Matches (cosine >= 0.65) map to 90-100% (e.g. 0.75 maps to ~94%, 0.85 maps to ~98%).
        """
        # Clamp raw_similarity to [-1.0, 1.0]
        x = max(-1.0, min(1.0, float(raw_similarity)))

        if x >= 0.85:
            # Strong match: [0.85, 1.0] -> [98.0%, 100.0%]
            normalized = (x - 0.85) / 0.15
            score = 98.0 + normalized * 2.0
        elif x >= 0.65:
            # Standard match: [0.65, 0.85] -> [90.0%, 98.0%]
            normalized = (x - 0.65) / 0.20
            score = 90.0 + normalized * 8.0
        elif x >= 0.50:
            # Weak match / lenient boundary: [0.50, 0.65] -> [65.0%, 90.0%]
            normalized = (x - 0.50) / 0.15
            score = 65.0 + normalized * 25.0
        elif x >= 0.0:
            # Non-match but face-like: [0.0, 0.50] -> [0.0%, 65.0%]
            normalized = x / 0.50
            score = normalized * 65.0
        else:
            score = 0.0

        return round(min(100.0, max(0.0, score)), 2)

    def get_embedding(self, face: DetectedFace) -> np.ndarray:
        """
        Extract ArcFace embedding from a DetectedFace.

        The InsightFace buffalo_l pipeline produces the embedding during detection.
        This method validates and normalizes it.

        Args:
            face: DetectedFace result from FaceDetectorService

        Returns:
            L2-normalized float32 numpy array of shape (512,)

        Raises:
            ValueError: if no embedding is available on the face object
        """
        if face.embedding is None:
            raise ValueError(
                "No ArcFace embedding found on detected face. "
                "Ensure the recognition module is loaded in FaceAnalysis."
            )

        embedding = np.array(face.embedding, dtype=np.float32)

        if embedding.shape[0] != self.EMBEDDING_DIM:
            raise ValueError(
                f"Unexpected embedding dimension {embedding.shape[0]}, "
                f"expected {self.EMBEDDING_DIM}"
            )

        return self._normalize(embedding)

    def get_embedding_from_array(self, raw: list[float]) -> np.ndarray:
        """Normalize a raw embedding loaded from the database."""
        embedding = np.array(raw, dtype=np.float32)
        return self._normalize(embedding)

    def _normalize(self, embedding: np.ndarray) -> np.ndarray:
        """L2 normalization. Zero vectors are returned as-is."""
        norm = np.linalg.norm(embedding)
        if norm == 0:
            logger.warning("Zero-norm embedding encountered — skipping normalization")
            return embedding
        return embedding / norm

    def compare_embeddings(
        self,
        embedding_a: np.ndarray,
        embedding_b: np.ndarray,
    ) -> float:
        """
        Compute cosine similarity between two L2-normalized embeddings.

        Args:
            embedding_a: Query embedding (512,) float32
            embedding_b: Stored enrollment embedding (512,) float32

        Returns:
            Similarity score in [0.0, 1.0] — higher = more similar.
            Threshold from settings.SIMILARITY_THRESHOLD (default 0.65).
        """
        a = self._normalize(np.array(embedding_a, dtype=np.float32))
        b = self._normalize(np.array(embedding_b, dtype=np.float32))

        # Cosine similarity = dot product of unit vectors
        similarity = float(np.dot(a, b))

        # Clamp to [0, 1] to handle floating point edge cases
        return max(0.0, min(1.0, (similarity + 1.0) / 2.0))

    def compare_raw_score(
        self,
        embedding_a: np.ndarray,
        embedding_b: np.ndarray,
    ) -> float:
        """
        Raw dot product similarity (range -1 to 1) as used by ArcFace natively.
        Values > threshold indicate same identity.
        """
        a = self._normalize(np.array(embedding_a, dtype=np.float32))
        b = self._normalize(np.array(embedding_b, dtype=np.float32))
        return float(np.dot(a, b))

    def average_embeddings(self, embeddings: list[np.ndarray]) -> np.ndarray:
        """
        Compute the average of multiple enrollment embeddings.
        Used to create a robust representative embedding from N images.

        Args:
            embeddings: List of 512-d normalized embeddings

        Returns:
            Single 512-d normalized average embedding
        """
        if not embeddings:
            raise ValueError("Cannot average empty embedding list")

        if len(embeddings) == 1:
            return embeddings[0]

        stacked = np.stack(embeddings, axis=0)
        avg = np.mean(stacked, axis=0)
        return self._normalize(avg)

    def find_best_match(
        self,
        query_embedding: np.ndarray,
        candidates: list[tuple[str, np.ndarray]],
        threshold: float | None = None,
    ) -> tuple[str | None, float]:
        """
        1:N identity search against a list of candidate embeddings.

        Args:
            query_embedding: 512-d embedding to search for
            candidates: List of (user_id_str, embedding_array)
            threshold: Similarity threshold (default from settings)

        Returns:
            (matched_user_id, confidence_score) — user_id is None if no match.
        """
        if threshold is None:
            threshold = settings.SIMILARITY_THRESHOLD

        best_user_id: str | None = None
        best_score: float = 0.0

        for user_id_str, stored_embedding in candidates:
            score = self.compare_raw_score(query_embedding, stored_embedding)
            if score > best_score:
                best_score = score
                best_user_id = user_id_str

        # Apply threshold check
        if best_score < threshold:
            return None, best_score

        return best_user_id, best_score

    def embedding_to_list(self, embedding: np.ndarray) -> list[float]:
        """Convert numpy array to Python list for database storage."""
        return embedding.tolist()

    def list_to_embedding(self, raw: list[float]) -> np.ndarray:
        """Convert stored list back to normalized numpy array."""
        return self._normalize(np.array(raw, dtype=np.float32))
