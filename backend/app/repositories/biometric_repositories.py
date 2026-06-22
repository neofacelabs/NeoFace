"""
NeoFace Iris Repository
Data access layer for iris embedding storage and IrisCode matching.
"""

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.iris_embedding import IrisEmbedding


class IrisRepository:
    """Repository for iris enrollment operations and IrisCode retrieval."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        iris_code: bytes,
        eye_side: str = "right",
        iris_mask: bytes | None = None,
        iris_radius_px: int | None = None,
        pupil_radius_px: int | None = None,
        quality_score: float | None = None,
        usable_bits_ratio: float | None = None,
        algorithm_version: str = "gabor_v1",
        source_image_path: str | None = None,
        source_image_bytes: bytes | None = None,
    ) -> IrisEmbedding:
        """Store a new iris enrollment record."""
        record = IrisEmbedding(
            user_id=user_id,
            iris_code=iris_code,
            iris_mask=iris_mask,
            eye_side=eye_side,
            iris_radius_px=iris_radius_px,
            pupil_radius_px=pupil_radius_px,
            quality_score=quality_score,
            usable_bits_ratio=usable_bits_ratio,
            algorithm_version=algorithm_version,
            source_image_path=source_image_path,
            source_image_bytes=source_image_bytes,
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def get_by_user(self, user_id: uuid.UUID) -> list[IrisEmbedding]:
        """Retrieve all iris enrollments for a user."""
        result = await self.db.execute(
            select(IrisEmbedding).where(IrisEmbedding.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_all(self) -> list[IrisEmbedding]:
        """Load all iris records for 1:N matching scan."""
        result = await self.db.execute(select(IrisEmbedding))
        return list(result.scalars().all())

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        from sqlalchemy import func
        result = await self.db.execute(
            select(func.count(IrisEmbedding.id)).where(IrisEmbedding.user_id == user_id)
        )
        return result.scalar_one()

    async def delete_by_user(self, user_id: uuid.UUID) -> int:
        from sqlalchemy import delete
        result = await self.db.execute(
            delete(IrisEmbedding).where(IrisEmbedding.user_id == user_id)
        )
        return result.rowcount


class FingerprintRepository:
    """Repository for fingerprint template storage and retrieval."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        user_id: uuid.UUID,
        template_data: bytes,
        finger_position: int = 2,
        finger_position_label: str | None = None,
        minutiae_count: int | None = None,
        quality_score: float | None = None,
        ridge_density: float | None = None,
        capture_device: str | None = None,
        capture_dpi: int | None = None,
        impression_type: str = "live_scan",
        algorithm_version: str = "minutiae_v1",
        source_image_bytes: bytes | None = None,
    ):
        from app.models.fingerprint_template import FingerprintTemplate
        record = FingerprintTemplate(
            user_id=user_id,
            template_data=template_data,
            finger_position=finger_position,
            finger_position_label=finger_position_label,
            minutiae_count=minutiae_count,
            quality_score=quality_score,
            ridge_density=ridge_density,
            capture_device=capture_device,
            capture_dpi=capture_dpi,
            impression_type=impression_type,
            algorithm_version=algorithm_version,
            source_image_bytes=source_image_bytes,
        )
        self.db.add(record)
        await self.db.flush()
        await self.db.refresh(record)
        return record

    async def get_by_user(self, user_id: uuid.UUID):
        from app.models.fingerprint_template import FingerprintTemplate
        result = await self.db.execute(
            select(FingerprintTemplate).where(FingerprintTemplate.user_id == user_id)
        )
        return list(result.scalars().all())

    async def get_all(self):
        from app.models.fingerprint_template import FingerprintTemplate
        result = await self.db.execute(select(FingerprintTemplate))
        return list(result.scalars().all())

    async def count_by_user(self, user_id: uuid.UUID) -> int:
        from sqlalchemy import func
        from app.models.fingerprint_template import FingerprintTemplate
        result = await self.db.execute(
            select(func.count(FingerprintTemplate.id)).where(FingerprintTemplate.user_id == user_id)
        )
        return result.scalar_one()

    async def delete_by_user(self, user_id: uuid.UUID) -> int:
        from sqlalchemy import delete
        from app.models.fingerprint_template import FingerprintTemplate
        result = await self.db.execute(
            delete(FingerprintTemplate).where(FingerprintTemplate.user_id == user_id)
        )
        return result.rowcount


class MerchantRepository:
    """Repository for merchant CRUD."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, business_name: str, business_email: str, **kwargs):
        from app.models.merchant import Merchant
        merchant = Merchant(business_name=business_name, business_email=business_email, **kwargs)
        self.db.add(merchant)
        await self.db.flush()
        await self.db.refresh(merchant)
        return merchant

    async def get_by_id(self, merchant_id: uuid.UUID):
        from app.models.merchant import Merchant
        result = await self.db.execute(select(Merchant).where(Merchant.id == merchant_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str):
        from app.models.merchant import Merchant
        result = await self.db.execute(select(Merchant).where(Merchant.business_email == email))
        return result.scalar_one_or_none()

    async def get_all(self, page: int = 1, page_size: int = 50):
        from sqlalchemy import func
        from app.models.merchant import Merchant
        total_r = await self.db.execute(select(func.count(Merchant.id)))
        total = total_r.scalar_one()
        offset = (page - 1) * page_size
        result = await self.db.execute(
            select(Merchant).order_by(Merchant.created_at.desc()).offset(offset).limit(page_size)
        )
        return list(result.scalars().all()), total


class BankAccountRepository:
    """Repository for bank account linking."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(self, user_id: uuid.UUID, bank_name: str, account_mask: str, encrypted_token: str, **kwargs):
        from app.models.bank_account import BankAccount
        account = BankAccount(
            user_id=user_id,
            bank_name=bank_name,
            account_mask=account_mask,
            encrypted_token=encrypted_token,
            **kwargs,
        )
        self.db.add(account)
        await self.db.flush()
        await self.db.refresh(account)
        return account

    async def get_by_user(self, user_id: uuid.UUID):
        from app.models.bank_account import BankAccount
        result = await self.db.execute(
            select(BankAccount).where(
                BankAccount.user_id == user_id,
                BankAccount.is_active == True,  # noqa: E712
            ).order_by(BankAccount.is_default.desc())
        )
        return list(result.scalars().all())

    async def get_default(self, user_id: uuid.UUID):
        from app.models.bank_account import BankAccount
        result = await self.db.execute(
            select(BankAccount).where(
                BankAccount.user_id == user_id,
                BankAccount.is_default == True,  # noqa: E712
                BankAccount.is_active == True,  # noqa: E712
            )
        )
        return result.scalar_one_or_none()
