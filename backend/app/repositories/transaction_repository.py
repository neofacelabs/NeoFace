"""
NeoFace Transaction Repository
Data access layer for payment transactions and analytics.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.transaction import Transaction, TransactionBiometricDetail


class TransactionRepository:
    """Repository for transaction CRUD and financial analytics."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Write ─────────────────────────────────────────────────────────────────

    async def create(
        self,
        amount: float,
        currency: str = "USD",
        user_id: uuid.UUID | None = None,
        merchant_id: uuid.UUID | None = None,
        bank_account_id: uuid.UUID | None = None,
        biometric_modality: str = "face",
        status: str = "pending",
        merchant_reference: str | None = None,
        description: str | None = None,
        ip_address: str | None = None,
        device_id: str | None = None,
        user_agent: str | None = None,
    ) -> Transaction:
        """Create a new pending transaction."""
        txn = Transaction(
            user_id=user_id,
            merchant_id=merchant_id,
            bank_account_id=bank_account_id,
            amount=amount,
            currency=currency,
            status=status,
            biometric_modality=biometric_modality,
            merchant_reference=merchant_reference,
            description=description,
            ip_address=ip_address,
            device_id=device_id,
            user_agent=user_agent,
        )
        self.db.add(txn)
        await self.db.flush()
        await self.db.refresh(txn)
        return txn

    async def add_biometric_detail(
        self,
        transaction_id: uuid.UUID,
        face_similarity_score: float | None = None,
        face_liveness_score: float | None = None,
        iris_hamming_distance: float | None = None,
        iris_match_score: float | None = None,
        fingerprint_match_score: float | None = None,
        fusion_score: float | None = None,
        face_liveness_passed: bool = False,
        anti_spoof_passed: bool = False,
        blink_detected: bool = False,
        head_turn_detected: bool = False,
        face_embedding_hash: str | None = None,
        iris_code_hash: str | None = None,
        fingerprint_template_hash: str | None = None,
    ) -> TransactionBiometricDetail:
        """Attach biometric signal breakdown to a transaction."""
        detail = TransactionBiometricDetail(
            transaction_id=transaction_id,
            face_similarity_score=face_similarity_score,
            face_liveness_score=face_liveness_score,
            iris_hamming_distance=iris_hamming_distance,
            iris_match_score=iris_match_score,
            fingerprint_match_score=fingerprint_match_score,
            fusion_score=fusion_score,
            face_liveness_passed=str(face_liveness_passed).lower(),
            anti_spoof_passed=str(anti_spoof_passed).lower(),
            blink_detected=str(blink_detected).lower(),
            head_turn_detected=str(head_turn_detected).lower(),
            face_embedding_hash=face_embedding_hash,
            iris_code_hash=iris_code_hash,
            fingerprint_template_hash=fingerprint_template_hash,
        )
        self.db.add(detail)
        await self.db.flush()
        await self.db.refresh(detail)
        return detail

    async def update_status(
        self,
        transaction_id: uuid.UUID,
        status: str,
        failure_reason: str | None = None,
        fusion_score: float | None = None,
        is_liveness_passed: bool | None = None,
        authorized_at: datetime | None = None,
        settled_at: datetime | None = None,
    ) -> Transaction | None:
        """Update transaction status after biometric decision."""
        result = await self.db.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        txn = result.scalar_one_or_none()
        if not txn:
            return None

        txn.status = status
        if failure_reason is not None:
            txn.failure_reason = failure_reason
        if fusion_score is not None:
            txn.fusion_score = fusion_score
        if is_liveness_passed is not None:
            txn.is_liveness_passed = str(is_liveness_passed).lower()
        if authorized_at is not None:
            txn.authorized_at = authorized_at
        if settled_at is not None:
            txn.settled_at = settled_at

        await self.db.flush()
        await self.db.refresh(txn)
        return txn

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_by_id(self, transaction_id: uuid.UUID) -> Transaction | None:
        result = await self.db.execute(
            select(Transaction).where(Transaction.id == transaction_id)
        )
        return result.scalar_one_or_none()

    async def get_by_user(
        self,
        user_id: uuid.UUID,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
    ) -> tuple[list[Transaction], int]:
        """Paginated transaction history for a user."""
        query = select(Transaction).where(Transaction.user_id == user_id)
        count_query = select(func.count(Transaction.id)).where(Transaction.user_id == user_id)

        if status:
            query = query.where(Transaction.status == status)
            count_query = count_query.where(Transaction.status == status)

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        result = await self.db.execute(
            query.order_by(Transaction.created_at.desc()).offset(offset).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def get_recent(
        self,
        page: int = 1,
        page_size: int = 50,
        merchant_id: uuid.UUID | None = None,
        status: str | None = None,
    ) -> tuple[list[Transaction], int]:
        """Paginated recent transactions, optionally filtered."""
        query = select(Transaction)
        count_query = select(func.count(Transaction.id))

        filters = []
        if merchant_id:
            filters.append(Transaction.merchant_id == merchant_id)
        if status:
            filters.append(Transaction.status == status)
        if filters:
            query = query.where(and_(*filters))
            count_query = count_query.where(and_(*filters))

        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        offset = (page - 1) * page_size
        result = await self.db.execute(
            query.order_by(Transaction.created_at.desc()).offset(offset).limit(page_size)
        )
        return list(result.scalars().all()), total

    # ── Analytics ─────────────────────────────────────────────────────────────

    async def count_total(self) -> int:
        result = await self.db.execute(select(func.count(Transaction.id)))
        return result.scalar_one()

    async def count_authorized(self) -> int:
        result = await self.db.execute(
            select(func.count(Transaction.id)).where(Transaction.status == "authorized")
        )
        return result.scalar_one()

    async def get_total_volume(self, status: str = "authorized") -> float:
        """Sum of all authorized transaction amounts."""
        result = await self.db.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.status == status
            )
        )
        return float(result.scalar_one())

    async def get_modality_breakdown(self) -> dict[str, int]:
        """Count of transactions per biometric modality."""
        result = await self.db.execute(
            select(Transaction.biometric_modality, func.count(Transaction.id))
            .group_by(Transaction.biometric_modality)
        )
        return {row[0]: row[1] for row in result.fetchall()}

    async def get_authorization_rate(self) -> float:
        """Returns authorization percentage (0.0–100.0)."""
        total = await self.count_total()
        if total == 0:
            return 0.0
        authorized = await self.count_authorized()
        return round((authorized / total) * 100, 2)

    async def get_daily_stats(self, days: int = 14) -> list[dict]:
        """Daily transaction volume and count for the last N days."""
        since = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.db.execute(
            select(
                func.date(Transaction.created_at).label("date"),
                func.count(Transaction.id).label("total"),
                func.sum(
                    case((Transaction.status == "authorized", 1), else_=0)
                ).label("authorized"),
                func.coalesce(
                    func.sum(
                        case((Transaction.status == "authorized", Transaction.amount), else_=0)
                    ), 0
                ).label("volume"),
            )
            .where(Transaction.created_at >= since)
            .group_by(func.date(Transaction.created_at))
            .order_by(func.date(Transaction.created_at))
        )
        rows = result.fetchall()
        return [
            {
                "date": str(row.date),
                "total": row.total,
                "authorized": int(row.authorized or 0),
                "blocked": row.total - int(row.authorized or 0),
                "volume": float(row.volume or 0),
            }
            for row in rows
        ]
