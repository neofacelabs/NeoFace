"""
NeoFace AaaS — API Key Service
Handles key generation, rotation, and revocation.

Security:
- Full key format: nf_live_<12-char-prefix><32-char-random>
  Example: nf_live_k3f9m2xq7rtz8bwnpyh4djeasolciuv
- Only key_prefix (12 chars) stored in DB for lookup
- Full key bcrypt-hashed and stored as hashed_secret
- Plaintext key returned ONCE at creation time — never stored
"""

from __future__ import annotations

import secrets
import uuid

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_key import AaaSApiKey
from app.repositories.api_key_repository import ApiKeyRepository
from app.schemas.aaas import ApiKeyCreate, ApiKeyCreatedResponse, ApiKeyResponse

_KEY_PREFIX_LEN = 12
_KEY_RANDOM_LEN = 32
_KEY_FORMAT = "nf_live_"


def _generate_raw_key() -> tuple[str, str]:
    """
    Generate a new API key.
    Returns (full_plaintext_key, prefix).
    """
    random_part = secrets.token_urlsafe(_KEY_RANDOM_LEN)[:_KEY_PREFIX_LEN + _KEY_RANDOM_LEN]
    prefix = random_part[:_KEY_PREFIX_LEN]
    full_key = f"{_KEY_FORMAT}{random_part}"
    return full_key, prefix


def _hash_key(plaintext: str) -> str:
    salt = bcrypt.gensalt(rounds=10)
    return bcrypt.hashpw(plaintext.encode("utf-8"), salt).decode("utf-8")


class ApiKeyService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = ApiKeyRepository(db)

    async def create_key(
        self,
        org_id: uuid.UUID,
        schema: ApiKeyCreate,
    ) -> ApiKeyCreatedResponse:
        """
        Generate and persist a new API key.
        The plaintext key is returned in ApiKeyCreatedResponse.plaintext_key
        and will never be available again.
        """
        plaintext, prefix = _generate_raw_key()
        hashed = _hash_key(plaintext)

        key_record = await self.repo.create(
            org_id=org_id,
            name=schema.name,
            key_prefix=prefix,
            hashed_secret=hashed,
            scopes=schema.scopes,
            app_id=schema.application_id,
        )

        return ApiKeyCreatedResponse(
            id=key_record.id,
            organization_id=key_record.organization_id,
            application_id=key_record.application_id,
            name=key_record.name,
            key_prefix=key_record.key_prefix,
            scopes=key_record.scopes,
            last_used_at=key_record.last_used_at,
            status=key_record.status,
            created_at=key_record.created_at,
            plaintext_key=plaintext,
        )

    async def rotate_key(
        self, key_id: uuid.UUID, org_id: uuid.UUID
    ) -> ApiKeyCreatedResponse:
        """
        Revoke the existing key and create a new one with the same settings.
        Returns the new key's plaintext.
        """
        old_key = await self.repo.get_by_id_and_org(key_id, org_id)
        if not old_key:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")

        # Mark old key as rotated
        await self.repo.update_status(key_id, "rotated")

        # Generate new key with same settings
        plaintext, prefix = _generate_raw_key()
        hashed = _hash_key(plaintext)

        new_key = await self.repo.create(
            org_id=org_id,
            name=f"{old_key.name} (rotated)",
            key_prefix=prefix,
            hashed_secret=hashed,
            scopes=old_key.scopes or [],
            app_id=old_key.application_id,
        )

        return ApiKeyCreatedResponse(
            id=new_key.id,
            organization_id=new_key.organization_id,
            application_id=new_key.application_id,
            name=new_key.name,
            key_prefix=new_key.key_prefix,
            scopes=new_key.scopes,
            last_used_at=new_key.last_used_at,
            status=new_key.status,
            created_at=new_key.created_at,
            plaintext_key=plaintext,
        )

    async def revoke_key(self, key_id: uuid.UUID, org_id: uuid.UUID) -> ApiKeyResponse:
        key = await self.repo.get_by_id_and_org(key_id, org_id)
        if not key:
            from fastapi import HTTPException, status
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
        updated = await self.repo.update_status(key_id, "revoked")
        return ApiKeyResponse.model_validate(updated)

    async def list_keys(
        self,
        org_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ApiKeyResponse], int]:
        keys, total = await self.repo.list_by_org(org_id, page=page, page_size=page_size)
        return [ApiKeyResponse.model_validate(k) for k in keys], total
