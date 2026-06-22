"""
NeoFace WebAuthn Credential Repository
Async CRUD operations for biometric_credentials table.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.biometric_credential import BiometricCredential


class CredentialRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        credential_id: bytes,
        public_key: bytes,
        sign_count: int,
        aaguid: str | None,
        device_name: str,
        device_metadata: dict | None = None,
    ) -> BiometricCredential:
        cred = BiometricCredential(
            user_id=user_id,
            credential_id=credential_id,
            public_key=public_key,
            sign_count=sign_count,
            aaguid=aaguid,
            device_name=device_name,
            device_metadata=device_metadata or {},
        )
        self.db.add(cred)
        await self.db.commit()
        await self.db.refresh(cred)
        return cred

    async def get_by_credential_id(self, credential_id: bytes) -> BiometricCredential | None:
        result = await self.db.execute(
            select(BiometricCredential).where(
                BiometricCredential.credential_id == credential_id,
                BiometricCredential.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: uuid.UUID) -> list[BiometricCredential]:
        result = await self.db.execute(
            select(BiometricCredential)
            .where(BiometricCredential.user_id == user_id)
            .order_by(BiometricCredential.enrolled_at.desc())
        )
        return list(result.scalars().all())

    async def update_sign_count(self, credential_id: bytes, new_count: int) -> None:
        await self.db.execute(
            update(BiometricCredential)
            .where(BiometricCredential.credential_id == credential_id)
            .values(sign_count=new_count, last_used_at=datetime.now(timezone.utc))
        )
        await self.db.commit()

    async def update_device_name(self, cred_id: uuid.UUID, user_id: uuid.UUID, name: str) -> bool:
        result = await self.db.execute(
            update(BiometricCredential)
            .where(BiometricCredential.id == cred_id, BiometricCredential.user_id == user_id)
            .values(device_name=name)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def revoke(self, cred_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        result = await self.db.execute(
            update(BiometricCredential)
            .where(BiometricCredential.id == cred_id, BiometricCredential.user_id == user_id)
            .values(is_active=False)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def set_payment_enabled(self, cred_id: uuid.UUID, user_id: uuid.UUID, enabled: bool) -> bool:
        result = await self.db.execute(
            update(BiometricCredential)
            .where(BiometricCredential.id == cred_id, BiometricCredential.user_id == user_id)
            .values(fingerprint_payments_enabled=enabled)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def count_active(self, user_id: uuid.UUID) -> int:
        result = await self.db.execute(
            select(BiometricCredential).where(
                BiometricCredential.user_id == user_id,
                BiometricCredential.is_active == True,  # noqa: E712
            )
        )
        return len(result.scalars().all())
