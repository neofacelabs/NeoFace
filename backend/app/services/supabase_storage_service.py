"""
NeoFace — Supabase Storage Service
Wraps the synchronous supabase-py client in asyncio-compatible helpers
so it can be consumed naturally from async FastAPI route handlers.

Bucket layout (create these in Supabase Dashboard → Storage):
  face-images          — enrollment face crops, access-controlled
  verification-images  — live verification frames, short-lived
  logs                 — audit artefacts, admin-only

All public methods are async; heavy I/O is offloaded to a thread-pool
executor so the event loop is never blocked.

Usage:
    storage = SupabaseStorageService()
    url = await storage.upload_image("face-images", "users/abc/1.jpg", data)
    signed = await storage.get_signed_url("face-images", "users/abc/1.jpg", 3600)
    ok = await storage.delete_image("face-images", "users/abc/1.jpg")
    files = await storage.list_images("face-images", prefix="users/abc/")
"""

from __future__ import annotations

import asyncio
import mimetypes
from functools import lru_cache
from typing import Any

from app.core.config import settings
from app.core.logging import logger

# ── Valid bucket constants ─────────────────────────────────────────────────────
BUCKET_FACE_IMAGES: str = settings.SUPABASE_BUCKET_FACE_IMAGES          # "face-images"
BUCKET_VERIFICATION_IMAGES: str = settings.SUPABASE_BUCKET_VERIFICATION_IMAGES  # "verification-images"
BUCKET_LOGS: str = settings.SUPABASE_BUCKET_LOGS                        # "logs"

VALID_BUCKETS: frozenset[str] = frozenset(
    {BUCKET_FACE_IMAGES, BUCKET_VERIFICATION_IMAGES, BUCKET_LOGS}
)


# ── Internal helper ────────────────────────────────────────────────────────────
def _get_supabase_client():  # type: ignore[return]
    """
    Lazily create and cache a supabase-py client.

    The client is created with the service role key so the backend can read/write
    any storage object regardless of RLS policies.  Never expose this client or
    its key to client-side code.

    Raises:
        ImportError:  If supabase-py is not installed.
        ValueError:   If SUPABASE_URL or SUPABASE_SERVICE_KEY is not configured.
    """
    try:
        from supabase import Client, create_client  # type: ignore[import]
    except ImportError as err:
        raise ImportError(
            "supabase-py is required for Supabase Storage. "
            "Install it: pip install supabase"
        ) from err

    if not settings.SUPABASE_URL:
        raise ValueError(
            "SUPABASE_URL is not configured. "
            "Set it in your .env file: SUPABASE_URL=https://<ref>.supabase.co"
        )
    if not settings.SUPABASE_SERVICE_KEY:
        raise ValueError(
            "SUPABASE_SERVICE_KEY is not configured. "
            "Set it in your .env file (keep this secret, never expose to clients)."
        )

    client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    return client


class SupabaseStorageService:
    """
    Async façade over the supabase-py Storage API.

    All public methods accept and return Python-native types.
    The supabase-py client is synchronous, so each call is wrapped with
    asyncio.get_event_loop().run_in_executor() to avoid blocking the event loop.
    """

    def __init__(self) -> None:
        # Defer client construction to first use so that missing env vars
        # surface as clear errors at call-time rather than import time.
        self._client = None

    def _storage(self):
        """Return the supabase-py storage client, initialising it on first call."""
        if self._client is None:
            self._client = _get_supabase_client()
        return self._client.storage

    async def _run_sync(self, func, *args, **kwargs) -> Any:
        """
        Run a synchronous callable in the default thread-pool executor so the
        async event loop is not blocked during network I/O.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: func(*args, **kwargs))

    def _validate_bucket(self, bucket: str) -> None:
        """Raise ValueError if the bucket name is not one of the known buckets."""
        if bucket not in VALID_BUCKETS:
            raise ValueError(
                f"Unknown bucket '{bucket}'. "
                f"Valid buckets: {sorted(VALID_BUCKETS)}"
            )

    # ── Core operations ────────────────────────────────────────────────────────

    async def upload_image(
        self,
        bucket: str,
        path: str,
        data: bytes,
        content_type: str | None = None,
    ) -> str:
        """
        Upload binary image data to a Supabase Storage bucket.

        Args:
            bucket:       Target bucket name (use BUCKET_* constants).
            path:         Object key inside the bucket, e.g. "users/{uuid}/frame.jpg".
            data:         Raw image bytes.
            content_type: MIME type; auto-detected from path extension if omitted.

        Returns:
            The full storage path "{bucket}/{path}" that can be used with
            get_signed_url() or delete_image().

        Raises:
            ValueError:   Unknown bucket.
            RuntimeError: Supabase returned an error response.
        """
        self._validate_bucket(bucket)

        # Auto-detect content type from file extension if not provided
        if content_type is None:
            guessed, _ = mimetypes.guess_type(path)
            content_type = guessed or "image/jpeg"

        file_options = {"content-type": content_type, "upsert": "true"}

        logger.debug(
            "supabase_storage.upload: starting",
            bucket=bucket,
            path=path,
            size_bytes=len(data),
        )

        response = await self._run_sync(
            self._storage().from_(bucket).upload,
            path,
            data,
            file_options,
        )

        # supabase-py raises on HTTP error but we double-check for safety
        if hasattr(response, "error") and response.error:
            logger.error(
                "supabase_storage.upload: failed",
                bucket=bucket,
                path=path,
                error=str(response.error),
            )
            raise RuntimeError(
                f"Supabase Storage upload failed for {bucket}/{path}: {response.error}"
            )

        full_path = f"{bucket}/{path}"
        logger.info(
            "supabase_storage.upload: success",
            bucket=bucket,
            path=path,
            full_path=full_path,
        )
        return full_path

    async def get_signed_url(
        self,
        bucket: str,
        path: str,
        expires_in: int = 3600,
    ) -> str:
        """
        Generate a time-limited signed URL for private bucket objects.

        Args:
            bucket:     Bucket containing the object.
            path:       Object key inside the bucket.
            expires_in: URL validity in seconds (default 1 hour; max 7 days = 604800).

        Returns:
            HTTPS signed URL string.

        Raises:
            ValueError:   Unknown bucket or invalid expiry.
            RuntimeError: Supabase returned an error response.
        """
        self._validate_bucket(bucket)

        if expires_in <= 0:
            raise ValueError("expires_in must be a positive integer (seconds).")

        logger.debug(
            "supabase_storage.signed_url: generating",
            bucket=bucket,
            path=path,
            expires_in=expires_in,
        )

        response = await self._run_sync(
            self._storage().from_(bucket).create_signed_url,
            path,
            expires_in,
        )

        if hasattr(response, "error") and response.error:
            logger.error(
                "supabase_storage.signed_url: failed",
                bucket=bucket,
                path=path,
                error=str(response.error),
            )
            raise RuntimeError(
                f"Supabase Storage signed URL failed for {bucket}/{path}: {response.error}"
            )

        # supabase-py returns {"signedURL": "..."} or {"signed_url": "..."}
        # depending on SDK version — handle both.
        signed_url: str = (
            response.get("signedURL")
            or response.get("signed_url")
            or (response if isinstance(response, str) else "")
        )

        if not signed_url:
            raise RuntimeError(
                f"Supabase Storage returned empty signed URL for {bucket}/{path}. "
                f"Raw response: {response}"
            )

        logger.debug(
            "supabase_storage.signed_url: success",
            bucket=bucket,
            path=path,
        )
        return signed_url

    async def delete_image(
        self,
        bucket: str,
        path: str,
    ) -> bool:
        """
        Delete an object from a Supabase Storage bucket.

        Args:
            bucket: Bucket containing the object.
            path:   Object key inside the bucket.

        Returns:
            True if the object was deleted (or did not exist), False on error.
        """
        self._validate_bucket(bucket)

        logger.debug(
            "supabase_storage.delete: starting",
            bucket=bucket,
            path=path,
        )

        try:
            response = await self._run_sync(
                self._storage().from_(bucket).remove,
                [path],  # The API accepts a list of paths
            )

            if hasattr(response, "error") and response.error:
                logger.error(
                    "supabase_storage.delete: failed",
                    bucket=bucket,
                    path=path,
                    error=str(response.error),
                )
                return False

            logger.info(
                "supabase_storage.delete: success",
                bucket=bucket,
                path=path,
            )
            return True

        except Exception as exc:
            logger.error(
                "supabase_storage.delete: exception",
                bucket=bucket,
                path=path,
                error=str(exc),
            )
            return False

    async def list_images(
        self,
        bucket: str,
        prefix: str = "",
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """
        List objects in a Supabase Storage bucket under a given prefix.

        Args:
            bucket: Bucket to list.
            prefix: Folder prefix to filter results (e.g. "users/abc/").
                    Pass empty string to list the bucket root.
            limit:  Maximum number of objects to return (default 100).
            offset: Pagination offset (default 0).

        Returns:
            List of dicts with keys: name, id, metadata, created_at, updated_at.
            Returns an empty list on error.
        """
        self._validate_bucket(bucket)

        logger.debug(
            "supabase_storage.list: starting",
            bucket=bucket,
            prefix=prefix,
            limit=limit,
        )

        try:
            response = await self._run_sync(
                self._storage().from_(bucket).list,
                prefix,
                {"limit": limit, "offset": offset},
            )

            if hasattr(response, "error") and response.error:
                logger.error(
                    "supabase_storage.list: failed",
                    bucket=bucket,
                    prefix=prefix,
                    error=str(response.error),
                )
                return []

            # Normalise: response is a list[dict] in supabase-py
            items: list[dict[str, Any]] = response if isinstance(response, list) else []
            logger.debug(
                "supabase_storage.list: success",
                bucket=bucket,
                prefix=prefix,
                count=len(items),
            )
            return items

        except Exception as exc:
            logger.error(
                "supabase_storage.list: exception",
                bucket=bucket,
                prefix=prefix,
                error=str(exc),
            )
            return []

    # ── Convenience helpers ────────────────────────────────────────────────────

    async def upload_face_image(self, user_id: str, image_bytes: bytes, filename: str) -> str:
        """
        Upload an enrollment face image to the face-images bucket.

        Args:
            user_id:     User UUID string (used as the folder name).
            image_bytes: Raw JPEG/PNG bytes.
            filename:    Filename including extension, e.g. "frame_001.jpg".

        Returns:
            Full storage path "face-images/users/{user_id}/{filename}".
        """
        path = f"users/{user_id}/{filename}"
        return await self.upload_image(BUCKET_FACE_IMAGES, path, image_bytes)

    async def upload_verification_image(
        self, session_id: str, image_bytes: bytes, filename: str
    ) -> str:
        """
        Upload a live-verification frame to the verification-images bucket.

        Args:
            session_id:  Verification session UUID (folder name).
            image_bytes: Raw image bytes.
            filename:    Filename including extension.

        Returns:
            Full storage path "verification-images/sessions/{session_id}/{filename}".
        """
        path = f"sessions/{session_id}/{filename}"
        return await self.upload_image(BUCKET_VERIFICATION_IMAGES, path, image_bytes)

    async def get_face_image_url(self, user_id: str, filename: str, expires_in: int = 3600) -> str:
        """Return a signed URL for a stored face image."""
        path = f"users/{user_id}/{filename}"
        return await self.get_signed_url(BUCKET_FACE_IMAGES, path, expires_in)
