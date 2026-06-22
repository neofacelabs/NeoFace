"""
NeoFace Storage Utility
Unified async storage abstraction with three pluggable backends:

  local     — filesystem, for development and MVP deployments
  s3        — AWS S3, for standalone cloud deployments
  supabase  — Supabase Storage, primary backend for the Supabase-integrated stack

Switch backends by setting STORAGE_BACKEND in your .env file.
No application code changes required — the StorageService interface is identical
across all backends.

Public API (StorageService):
    save_face_image(user_id, image_bytes, suffix)     -> str  (storage path)
    get_face_image(path)                              -> bytes | None
    delete_face_image(path)                           -> bool
    get_signed_url(path, expires_in)                  -> str  (Supabase/S3 only)
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import logger


# ── Abstract backend interface ─────────────────────────────────────────────────

class BaseStorageBackend:
    """Defines the contract every storage backend must implement."""

    async def put(self, key: str, data: bytes) -> None:
        raise NotImplementedError

    async def get(self, key: str) -> bytes | None:
        raise NotImplementedError

    async def delete(self, key: str) -> bool:
        raise NotImplementedError

    async def signed_url(self, key: str, expires_in: int = 3600) -> str:
        """
        Return a pre-signed / time-limited URL for the object.
        Default implementation raises NotImplementedError; backends that do not
        support signing (e.g. local) should override and raise a clear error.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} does not support signed URLs."
        )


# ── Local filesystem backend ───────────────────────────────────────────────────

class LocalStorageBackend(BaseStorageBackend):
    """
    Filesystem backend for local development and self-hosted deployments.
    Files are stored at LOCAL_STORAGE_PATH/{key}.
    """

    def __init__(self) -> None:
        self.base_path = Path(settings.LOCAL_STORAGE_PATH)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def put(self, key: str, data: bytes) -> None:
        file_path = self.base_path / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)

    async def get(self, key: str) -> bytes | None:
        file_path = self.base_path / key
        if not file_path.exists():
            return None
        return file_path.read_bytes()

    async def delete(self, key: str) -> bool:
        file_path = self.base_path / key
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def signed_url(self, key: str, expires_in: int = 3600) -> str:
        # Local backend cannot generate signed URLs; return a local file URI instead.
        file_path = self.base_path / key
        return file_path.as_uri()


# ── AWS S3 backend ─────────────────────────────────────────────────────────────

class S3StorageBackend(BaseStorageBackend):
    """
    AWS S3 backend for standalone cloud deployments.
    Requires: pip install boto3
    Configured via AWS_* environment variables.
    """

    def __init__(self) -> None:
        try:
            import boto3  # noqa: F401
        except ImportError as err:
            raise ImportError(
                "boto3 is required for S3 storage. Install it: pip install boto3"
            ) from err

        import boto3

        self._client = boto3.client(
            "s3",
            region_name=settings.AWS_S3_REGION,
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY or None,
        )
        self._bucket = settings.AWS_S3_BUCKET

    async def put(self, key: str, data: bytes) -> None:
        import asyncio

        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._client.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType="image/jpeg",
                ServerSideEncryption="AES256",
            ),
        )

    async def get(self, key: str) -> bytes | None:
        import asyncio

        try:
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.get_object(Bucket=self._bucket, Key=key),
            )
            return response["Body"].read()
        except Exception:
            return None

    async def delete(self, key: str) -> bool:
        import asyncio

        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._client.delete_object(Bucket=self._bucket, Key=key),
            )
            return True
        except Exception:
            return False

    async def signed_url(self, key: str, expires_in: int = 3600) -> str:
        import asyncio

        url: str = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self._bucket, "Key": key},
                ExpiresIn=expires_in,
            ),
        )
        return url


# ── Supabase Storage backend ───────────────────────────────────────────────────

class SupabaseStorageBackend(BaseStorageBackend):
    """
    Supabase Storage backend — primary backend for the Supabase-integrated stack.

    Delegates to SupabaseStorageService for all operations so the upload,
    signing, and deletion logic lives in one place.

    The face images bucket (BUCKET_FACE_IMAGES) is used by default for
    operations that go through StorageService.save_face_image().

    Keys are stored as-is inside the bucket, so the caller is responsible for
    namespacing (e.g. "faces/{user_id}/{filename}").
    """

    def __init__(self) -> None:
        from app.services.supabase_storage_service import (
            BUCKET_FACE_IMAGES,
            SupabaseStorageService,
        )

        self._service = SupabaseStorageService()
        self._default_bucket = BUCKET_FACE_IMAGES

    async def put(self, key: str, data: bytes) -> None:
        await self._service.upload_image(self._default_bucket, key, data)

    async def get(self, key: str) -> bytes | None:
        """
        Download an object from Supabase Storage.

        Note: supabase-py's download() is used here; it returns raw bytes.
        """
        try:
            import asyncio

            response: bytes = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._service._storage().from_(self._default_bucket).download(key),
            )
            return response
        except Exception as exc:
            logger.error("supabase_storage_backend.get: failed", key=key, error=str(exc))
            return None

    async def delete(self, key: str) -> bool:
        return await self._service.delete_image(self._default_bucket, key)

    async def signed_url(self, key: str, expires_in: int = 3600) -> str:
        return await self._service.get_signed_url(self._default_bucket, key, expires_in)


# ── Public StorageService façade ───────────────────────────────────────────────

class StorageService:
    """
    High-level storage façade used across the NeoFace application.

    Selects the appropriate backend at construction time based on
    the STORAGE_BACKEND environment variable:

        "local"    → LocalStorageBackend  (default for development)
        "s3"       → S3StorageBackend
        "supabase" → SupabaseStorageBackend  (recommended for production)

    All methods are async-compatible regardless of the backend.
    """

    def __init__(self) -> None:
        backend_name = settings.STORAGE_BACKEND.lower()

        if backend_name == "supabase":
            # Check if supabase config is missing or placeholder
            is_placeholder = (
                not settings.SUPABASE_URL
                or not settings.SUPABASE_SERVICE_KEY
                or "placeholder" in settings.SUPABASE_SERVICE_KEY.lower()
                or "your-supabase" in settings.SUPABASE_SERVICE_KEY.lower()
                or settings.SUPABASE_SERVICE_KEY == ""
            )
            if is_placeholder:
                logger.warning(
                    "storage.init: Supabase credentials are not configured or are placeholders. "
                    "Falling back to local storage backend."
                )
                self._backend = LocalStorageBackend()
                backend_name = "local (fallback)"
            else:
                try:
                    self._backend = SupabaseStorageBackend()
                except Exception as exc:
                    logger.warning(
                        "storage.init: Failed to initialize Supabase storage backend. "
                        f"Error: {exc}. Falling back to local storage backend."
                    )
                    self._backend = LocalStorageBackend()
                    backend_name = "local (fallback)"
        elif backend_name == "s3":
            self._backend = S3StorageBackend()
        else:
            self._backend = LocalStorageBackend()

        logger.info("storage.init: backend selected", backend=backend_name)

    async def save_face_image(
        self,
        user_id: str,
        image_bytes: bytes,
        suffix: str = ".jpg",
    ) -> str:
        """
        Persist a face image and return its storage key/path.

        Args:
            user_id:     UUID string for the user; becomes the folder name.
            image_bytes: Raw image bytes (JPEG or PNG).
            suffix:      File extension including the dot (default ".jpg").

        Returns:
            Storage key that can be passed to get_face_image() or delete_face_image().
        """
        filename = f"{uuid.uuid4().hex}{suffix}"
        key = f"faces/{user_id}/{filename}"
        await self._backend.put(key, image_bytes)
        logger.debug("storage.save_face_image: saved", user_id=user_id, key=key)
        return key

    async def get_face_image(self, path: str) -> bytes | None:
        """
        Retrieve raw bytes for a stored face image.

        Returns None if the object does not exist.
        """
        return await self._backend.get(path)

    async def delete_face_image(self, path: str) -> bool:
        """
        Delete a stored face image.

        Returns True on success, False if the object was not found or deletion failed.
        """
        return await self._backend.delete(path)

    async def get_signed_url(self, path: str, expires_in: int = 3600) -> str:
        """
        Return a time-limited URL for the stored object.

        Args:
            path:       Storage key as returned by save_face_image().
            expires_in: URL validity in seconds (default 1 hour).

        Returns:
            Signed HTTPS URL (Supabase / S3) or file:// URI (local backend).
        """
        return await self._backend.signed_url(path, expires_in)
