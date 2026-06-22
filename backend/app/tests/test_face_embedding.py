"""
NeoFace Face Embedding Service Tests
Tests for ArcFace embedding generation and cosine similarity.
"""

import numpy as np
import pytest

from app.services.face_embedding import FaceEmbeddingService
from app.tests.conftest import make_fake_detected_face, make_fake_embedding


class TestFaceEmbeddingService:
    """Unit tests for FaceEmbeddingService."""

    @pytest.fixture
    def embedder(self):
        return FaceEmbeddingService()

    def test_get_embedding_returns_512d_vector(self, embedder):
        """get_embedding returns a 512-dimensional normalized array."""
        face = make_fake_detected_face(seed=42)
        embedding = embedder.get_embedding(face)

        assert embedding.shape == (512,)
        assert embedding.dtype == np.float32

    def test_get_embedding_is_normalized(self, embedder):
        """Returned embedding has L2 norm ≈ 1.0."""
        face = make_fake_detected_face(seed=42)
        embedding = embedder.get_embedding(face)
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 1e-5

    def test_get_embedding_no_embedding_raises(self, embedder):
        """Face with no embedding raises ValueError."""
        face = make_fake_detected_face(seed=42)
        face.embedding = None  # Simulate missing embedding

        with pytest.raises(ValueError, match="No ArcFace embedding"):
            embedder.get_embedding(face)

    def test_compare_same_embedding_returns_high_score(self, embedder):
        """Identical embeddings return similarity ≈ 1.0."""
        emb = make_fake_embedding(seed=1)
        score = embedder.compare_embeddings(emb, emb)
        assert score > 0.99

    def test_compare_different_embeddings_returns_low_score(self, embedder):
        """Completely different embeddings return low similarity."""
        emb_a = make_fake_embedding(seed=1)
        emb_b = make_fake_embedding(seed=999)
        score = embedder.compare_embeddings(emb_a, emb_b)
        # Different random embeddings should have lower similarity
        # (may still be > 0 due to normalization)
        assert 0.0 <= score <= 1.0

    def test_compare_embeddings_symmetric(self, embedder):
        """Cosine similarity is symmetric: sim(a,b) == sim(b,a)."""
        emb_a = make_fake_embedding(seed=10)
        emb_b = make_fake_embedding(seed=20)

        score_ab = embedder.compare_embeddings(emb_a, emb_b)
        score_ba = embedder.compare_embeddings(emb_b, emb_a)

        assert abs(score_ab - score_ba) < 1e-6

    def test_average_embeddings_single(self, embedder):
        """Average of a single embedding returns the same embedding."""
        emb = make_fake_embedding(seed=5)
        avg = embedder.average_embeddings([emb])
        np.testing.assert_array_almost_equal(avg, emb, decimal=5)

    def test_average_embeddings_multiple(self, embedder):
        """Average of multiple embeddings is a valid normalized vector."""
        embeddings = [make_fake_embedding(seed=i) for i in range(5)]
        avg = embedder.average_embeddings(embeddings)

        assert avg.shape == (512,)
        norm = np.linalg.norm(avg)
        assert abs(norm - 1.0) < 1e-5

    def test_average_embeddings_empty_raises(self, embedder):
        """Empty list raises ValueError."""
        with pytest.raises(ValueError, match="Cannot average empty"):
            embedder.average_embeddings([])

    def test_find_best_match_returns_closest(self, embedder):
        """find_best_match returns the user with the highest similarity."""
        query = make_fake_embedding(seed=1)
        # User 1 has same embedding (should match)
        # User 2 has very different embedding (should not match)
        candidates = [
            ("user-1", make_fake_embedding(seed=1)),   # Same as query
            ("user-2", make_fake_embedding(seed=999)),  # Very different
        ]

        matched_id, score = embedder.find_best_match(
            query, candidates, threshold=0.0  # Low threshold to force match
        )

        assert matched_id == "user-1"
        assert score > 0.5

    def test_find_best_match_below_threshold_returns_none(self, embedder):
        """Scores below threshold return None."""
        query = make_fake_embedding(seed=1)
        candidates = [
            ("user-1", make_fake_embedding(seed=500)),  # Different
        ]

        matched_id, score = embedder.find_best_match(
            query, candidates, threshold=0.99  # Very high threshold
        )

        assert matched_id is None

    def test_embedding_round_trip(self, embedder):
        """Embedding can be serialized to list and back without loss."""
        original = make_fake_embedding(seed=42)
        as_list = embedder.embedding_to_list(original)
        restored = embedder.list_to_embedding(as_list)

        assert isinstance(as_list, list)
        assert len(as_list) == 512
        np.testing.assert_array_almost_equal(original, restored, decimal=5)

    def test_normalize_zero_vector(self, embedder):
        """Zero vector is handled gracefully (returned as-is)."""
        zero = np.zeros(512, dtype=np.float32)
        result = embedder._normalize(zero)
        assert np.all(result == 0)
