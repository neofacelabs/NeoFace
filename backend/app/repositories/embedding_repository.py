"""
NeoFace Face Embedding Repository
Data access layer for FaceEmbedding model.
Manages storage and retrieval of ArcFace embedding vectors.
"""

import uuid
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.face_embedding import FaceEmbedding


class EmbeddingRepository:
    """
    Repository for face embedding CRUD operations.
    Designed for bulk reads (verification scans all enrolled embeddings).
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_by_id(self, embedding_id: uuid.UUID) -> FaceEmbedding | None:
        result = await self.db.execute(
            select(FaceEmbedding).where(FaceEmbedding.id == embedding_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user_id(self, user_id: uuid.UUID) -> list[FaceEmbedding]:
        """Fetch all embeddings for a specific user."""
        result = await self.db.execute(
            select(FaceEmbedding)
            .where(FaceEmbedding.user_id == user_id)
            .order_by(FaceEmbedding.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_by_user(self, user_id: uuid.UUID) -> list[FaceEmbedding]:
        """Alias for get_by_user_id."""
        return await self.get_by_user_id(user_id)

    async def get_all_active(self) -> list[FaceEmbedding]:
        """
        Fetch all embeddings for enrolled users.
        Used during 1:N verification scan.

        NOTE: For large deployments (>100k users), this should be replaced
        with approximate nearest neighbor (ANN) search using pgvector or Faiss.
        """
        result = await self.db.execute(
            select(FaceEmbedding)
            .join(FaceEmbedding.user)
            .where(
                FaceEmbedding.embedding_vector.isnot(None),
            )
        )
        return list(result.scalars().all())

    async def find_nearest_neighbors(
        self,
        query_vector: list[float],
        limit: int = 5,
    ) -> list[tuple[FaceEmbedding, float]]:
        """
        Perform 1:N search using pgvector when on PostgreSQL, or fall back to Python
        computation when using SQLite. Returns list of (FaceEmbedding, similarity).
        """
        from sqlalchemy import text
        import numpy as np

        dialect = self.db.bind.dialect.name if self.db.bind else "postgresql"
        if dialect == "postgresql":
            # pgvector cosine similarity = 1.0 - (a <=> b)
            # Both sides must be cast to vector because embedding_vector is defined as ARRAY(Float) (double precision[])
            stmt = (
                select(
                    FaceEmbedding,
                    text("1.0 - (CAST(face_embeddings.embedding_vector AS vector) <=> CAST(:query_vector AS vector)) AS similarity")
                )
                .join(FaceEmbedding.user)
                .order_by(text("CAST(face_embeddings.embedding_vector AS vector) <=> CAST(:query_vector AS vector)"))
                .params(query_vector=str(query_vector))
                .limit(limit)
            )
            res = await self.db.execute(stmt)
            return [(row[0], float(row[1])) for row in res.all()]
        else:
            # Fallback for SQLite / unit tests
            all_active = await self.get_all_active()
            q_arr = np.array(query_vector, dtype=np.float32)
            q_norm = np.linalg.norm(q_arr)

            candidates = []
            for emb in all_active:
                emb_arr = np.array(emb.embedding_vector, dtype=np.float32)
                emb_norm = np.linalg.norm(emb_arr)
                if q_norm == 0.0 or emb_norm == 0.0:
                    sim = 0.0
                else:
                    sim = float(np.dot(q_arr, emb_arr) / (q_norm * emb_norm))
                candidates.append((emb, sim))

            # Sort by similarity descending
            candidates.sort(key=lambda x: x[1], reverse=True)
            return candidates[:limit]

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        """Count how many embeddings a user has."""
        result = await self.db.execute(
            select(func.count(FaceEmbedding.id)).where(
                FaceEmbedding.user_id == user_id
            )
        )
        return result.scalar_one()

    async def get_latest_by_user(self, user_id: uuid.UUID) -> FaceEmbedding | None:
        """Get the most recently created embedding for a user."""
        result = await self.db.execute(
            select(FaceEmbedding)
            .where(FaceEmbedding.user_id == user_id)
            .order_by(FaceEmbedding.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ── Write ─────────────────────────────────────────────────────────────────

    async def create(
        self,
        user_id: uuid.UUID,
        embedding_vector: list[float],
        quality_score: float | None = None,
        source_image_path: str | None = None,
        source_image_bytes: bytes | None = None,
        embedding_version: str = "arcface_r100_v1",
    ) -> FaceEmbedding:
        """Persist a new embedding record."""
        embedding = FaceEmbedding(
            user_id=user_id,
            embedding_vector=embedding_vector,
            embedding_version=embedding_version,
            embedding_dimension=len(embedding_vector),
            quality_score=quality_score,
            source_image_path=source_image_path,
            source_image_bytes=source_image_bytes,
        )
        self.db.add(embedding)
        await self.db.flush()
        await self.db.refresh(embedding)
        return embedding

    async def delete_by_user(self, user_id: uuid.UUID) -> int:
        """Delete all embeddings for a user. Returns count deleted."""
        result = await self.db.execute(
            delete(FaceEmbedding).where(FaceEmbedding.user_id == user_id)
        )
        return result.rowcount

    async def delete_by_id(self, embedding_id: uuid.UUID) -> bool:
        """Delete a single embedding record."""
        result = await self.db.execute(
            delete(FaceEmbedding).where(FaceEmbedding.id == embedding_id)
        )
        return result.rowcount > 0
