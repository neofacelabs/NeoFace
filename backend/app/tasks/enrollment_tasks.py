"""
NeoFace Enrollment Celery Tasks
Async background processing for face enrollment.

Tasks:
- process_enrollment_async: Generate and store embeddings asynchronously
"""

import asyncio
import uuid

from app.core.logging import logger
from app.tasks.celery_app import celery_app


@celery_app.task(
    name="app.tasks.enrollment_tasks.process_enrollment_async",
    bind=True,
    max_retries=3,
    default_retry_delay=30,
)
def process_enrollment_async(
    self,
    user_id: str,
    image_paths: list[str],
) -> dict:
    """
    Asynchronously process face enrollment for a user.
    Reads stored images, generates embeddings, and updates the database.

    This task is dispatched after the initial enrollment API call stores
    the raw images, allowing the HTTP response to return immediately.

    Args:
        user_id: UUID string of the user to enroll
        image_paths: List of storage paths to face images

    Returns:
        Dict with status and processed count
    """
    logger.info(
        "Async enrollment task started",
        task_id=self.request.id,
        user_id=user_id,
        image_count=len(image_paths),
    )

    try:
        # Run the async enrollment logic in a new event loop
        result = asyncio.get_event_loop().run_until_complete(
            _process_enrollment_async(user_id, image_paths)
        )
        logger.info(
            "Async enrollment task completed",
            task_id=self.request.id,
            user_id=user_id,
            result=result,
        )
        return result

    except Exception as exc:
        logger.error(
            "Async enrollment task failed",
            task_id=self.request.id,
            user_id=user_id,
            error=str(exc),
        )
        raise self.retry(exc=exc)


async def _process_enrollment_async(user_id: str, image_paths: list[str]) -> dict:
    """
    Inner async logic for enrollment processing.
    Reads images from storage, generates embeddings, updates database.
    """
    from app.core.database import AsyncSessionLocal
    from app.repositories.embedding_repository import EmbeddingRepository
    from app.repositories.user_repository import UserRepository
    from app.services.face_detector import FaceDetectorService
    from app.services.face_embedding import FaceEmbeddingService
    from app.utils.storage import StorageService

    detector = FaceDetectorService.get_instance()
    embedder = FaceEmbeddingService()
    storage = StorageService()

    embeddings = []
    processed = 0

    for path in image_paths:
        image_bytes = await storage.get_face_image(path)
        if not image_bytes:
            logger.warning("Image not found in storage", path=path)
            continue

        _, face = detector.detect_single(image_bytes)
        if face is None:
            logger.warning("No face detected in stored image", path=path)
            continue

        try:
            embedding = embedder.get_embedding(face)
            embeddings.append(embedding)
            processed += 1
        except ValueError as exc:
            logger.warning("Embedding failed", path=path, error=str(exc))

    if not embeddings:
        return {"status": "failed", "reason": "No valid embeddings generated", "processed": 0}

    avg_embedding = embedder.average_embeddings(embeddings)

    async with AsyncSessionLocal() as session:
        user_uuid = uuid.UUID(user_id)
        user_repo = UserRepository(session)
        embedding_repo = EmbeddingRepository(session)

        # Replace existing embeddings
        await embedding_repo.delete_by_user(user_uuid)
        await embedding_repo.create(
            user_id=user_uuid,
            embedding_vector=embedder.embedding_to_list(avg_embedding),
            source_image_path=image_paths[0] if image_paths else None,
        )
        await user_repo.mark_enrolled(user_uuid)
        await session.commit()

    return {"status": "enrolled", "processed": processed}
