"""
NeoFace Payment Authorization Service
Orchestrates the biometric payment pipeline:
  1. Accept face / iris / fingerprint biometric payloads
  2. Run each biometric verification
  3. Fuse scores via BiometricFusionEngine
  4. Record the transaction in the database
  5. Return the authorization decision
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.repositories.biometric_repositories import (
    BankAccountRepository,
    FingerprintRepository,
    IrisRepository,
    MerchantRepository,
)
from app.repositories.embedding_repository import EmbeddingRepository
from app.repositories.transaction_repository import TransactionRepository
from app.repositories.user_repository import UserRepository
from app.services.face_detector import FaceDetectorService
from app.services.face_embedding import FaceEmbeddingService
from app.services.fingerprint_service import FingerprintService, FingerprintTemplate
from app.services.fusion_engine import BiometricFusionEngine, BiometricSignals, FusionDecision
from app.services.iris_service import IrisService
from app.utils.dependencies import get_face_detector


class PaymentAuthorizationService:
    """
    Orchestrates end-to-end biometric payment authorization.

    Supported modalities:
    - face: ArcFace embedding match + liveness/anti-spoof
    - iris: Gabor IrisCode + Hamming Distance match
    - fingerprint: ISO minutiae template + MCC match
    - multi_modal: any combination of the above
    """

    def __init__(
        self,
        db: AsyncSession,
        face_detector: FaceDetectorService | None = None,
    ) -> None:
        self.db = db
        self.face_detector = face_detector or get_face_detector()

        # Repositories
        self.txn_repo = TransactionRepository(db)
        self.user_repo = UserRepository(db)
        self.embedding_repo = EmbeddingRepository(db)
        self.iris_repo = IrisRepository(db)
        self.fingerprint_repo = FingerprintRepository(db)
        self.merchant_repo = MerchantRepository(db)
        self.bank_account_repo = BankAccountRepository(db)

        # Biometric services
        self.iris_service = IrisService.get_instance()
        self.fingerprint_service = FingerprintService.get_instance()
        self.fusion_engine = BiometricFusionEngine.get_instance()

    async def authorize(
        self,
        amount: float,
        currency: str = "USD",
        merchant_id: uuid.UUID | None = None,
        merchant_reference: str | None = None,
        description: str | None = None,
        # Biometric payloads (at least one required)
        face_image_bytes: bytes | None = None,
        iris_image_bytes: bytes | None = None,
        fingerprint_image_bytes: bytes | None = None,
        # Context
        ip_address: str | None = None,
        device_id: str | None = None,
        user_agent: str | None = None,
        threshold_override: float | None = None,
    ) -> dict:
        """
        Main payment authorization entrypoint.
        Returns a structured authorization result dict.
        """
        if not any([face_image_bytes, iris_image_bytes, fingerprint_image_bytes]):
            return {
                "authorized": False,
                "failure_reason": "no_biometric_payload",
                "transaction_id": None,
                "fusion_score": 0.0,
                "modalities_used": [],
            }

        # Determine requested modality
        modalities_presented = []
        if face_image_bytes:
            modalities_presented.append("face")
        if iris_image_bytes:
            modalities_presented.append("iris")
        if fingerprint_image_bytes:
            modalities_presented.append("fingerprint")

        biometric_modality = (
            "multi_modal" if len(modalities_presented) > 1
            else modalities_presented[0]
        )

        # ── Create pending transaction ──────────────────────────────────────
        txn = await self.txn_repo.create(
            amount=amount,
            currency=currency,
            merchant_id=merchant_id,
            biometric_modality=biometric_modality,
            status="pending",
            merchant_reference=merchant_reference,
            description=description,
            ip_address=ip_address,
            device_id=device_id,
            user_agent=user_agent,
        )
        await self.db.commit()

        signals = BiometricSignals(requested_modality=biometric_modality)

        # ── Face verification ───────────────────────────────────────────────
        face_embedding_hash: str | None = None
        if face_image_bytes:
            try:
                face_result = await self._run_face_verification(
                    face_image_bytes,
                    threshold_override=threshold_override,
                )
                signals.face_similarity_score = face_result.get("confidence_score", 0.0) / 100.0
                signals.face_liveness_score = face_result.get("liveness_score", 0.0)
                signals.face_liveness_passed = face_result.get("liveness_passed", False)
                signals.face_anti_spoof_passed = face_result.get("anti_spoof_passed", False)
                signals.face_blink_detected = face_result.get("blink_detected", False)
                signals.face_head_turn_detected = face_result.get("head_turn_detected", False)
                signals.face_user_id = face_result.get("user_id")
                face_embedding_hash = face_result.get("embedding_hash")
            except Exception as exc:
                logger.warning("PaymentService: face verification error", error=str(exc))

        # ── Iris verification ───────────────────────────────────────────────
        iris_code_hash: str | None = None
        if iris_image_bytes:
            try:
                iris_result = await self._run_iris_verification(iris_image_bytes)
                signals.iris_match_score = iris_result.get("match_score", 0.0)
                signals.iris_hamming_distance = iris_result.get("hamming_distance", 1.0)
                signals.iris_matched_user_id = iris_result.get("user_id")
                iris_code_hash = iris_result.get("code_hash")
            except Exception as exc:
                logger.warning("PaymentService: iris verification error", error=str(exc))

        # ── Fingerprint verification ────────────────────────────────────────
        fingerprint_hash: str | None = None
        if fingerprint_image_bytes:
            try:
                fp_result = await self._run_fingerprint_verification(fingerprint_image_bytes)
                signals.fingerprint_match_score = fp_result.get("match_score", 0.0)
                signals.fingerprint_minutiae_pairs = fp_result.get("minutiae_pairs", 0)
                signals.fingerprint_matched_user_id = fp_result.get("user_id")
                fingerprint_hash = fp_result.get("template_hash")
            except Exception as exc:
                logger.warning("PaymentService: fingerprint verification error", error=str(exc))

        # ── Fusion decision ─────────────────────────────────────────────────
        if threshold_override:
            self.fusion_engine.fusion_threshold = threshold_override

        decision: FusionDecision = self.fusion_engine.evaluate(signals)

        # ── Resolve user and bank account ───────────────────────────────────
        resolved_user_id = None
        bank_account_id = None
        default_account = None
        if decision.resolved_user_id:
            try:
                resolved_user_id = uuid.UUID(decision.resolved_user_id)
                default_account = await self.bank_account_repo.get_default(resolved_user_id)
                if default_account:
                    bank_account_id = default_account.id
            except Exception:
                pass

        # ── Run payment settlement if authorized ─────────────────────────────
        final_status = "failed"
        failure_reason = decision.failure_reason
        authorized_at = None

        if decision.authorized:
            if not default_account:
                failure_reason = "no_linked_bank_account"
            else:
                from app.services.stripe_gateway import StripeGateway
                gateway = StripeGateway.get_instance()
                settlement = gateway.process_bank_transfer(
                    amount=amount,
                    currency=currency,
                    bank_token=default_account.encrypted_token,
                    account_holder=default_account.account_holder_name,
                )
                if settlement["success"]:
                    final_status = "authorized"
                    authorized_at = datetime.now(timezone.utc)
                else:
                    failure_reason = settlement["error"] or "settlement_failed"

        await self.txn_repo.update_status(
            transaction_id=txn.id,
            status=final_status,
            failure_reason=failure_reason,
            fusion_score=decision.fusion_score,
            is_liveness_passed=decision.is_liveness_passed,
            authorized_at=authorized_at,
        )

        # Update user_id and bank account on transaction
        txn.user_id = resolved_user_id
        txn.bank_account_id = bank_account_id

        # ── Attach biometric detail ─────────────────────────────────────────
        await self.txn_repo.add_biometric_detail(
            transaction_id=txn.id,
            face_similarity_score=signals.face_similarity_score,
            face_liveness_score=signals.face_liveness_score,
            iris_hamming_distance=signals.iris_hamming_distance,
            iris_match_score=signals.iris_match_score,
            fingerprint_match_score=signals.fingerprint_match_score,
            fusion_score=decision.fusion_score,
            face_liveness_passed=signals.face_liveness_passed,
            anti_spoof_passed=signals.face_anti_spoof_passed,
            blink_detected=signals.face_blink_detected,
            head_turn_detected=signals.face_head_turn_detected,
            face_embedding_hash=face_embedding_hash,
            iris_code_hash=iris_code_hash,
            fingerprint_template_hash=fingerprint_hash,
        )
        await self.db.commit()

        logger.info(
            "PaymentService.authorize complete",
            transaction_id=str(txn.id),
            authorized=decision.authorized,
            fusion_score=decision.fusion_score,
            modalities=decision.modalities_used,
        )

        return {
            "authorized": decision.authorized,
            "transaction_id": str(txn.id),
            "fusion_score": decision.fusion_score,
            "threshold_used": decision.threshold_used,
            "modalities_used": decision.modalities_used,
            "resolved_user_id": str(resolved_user_id) if resolved_user_id else None,
            "failure_reason": decision.failure_reason,
            "is_liveness_passed": decision.is_liveness_passed,
            "amount": float(amount),
            "currency": currency,
            "status": final_status,
            "authorized_at": authorized_at.isoformat() if authorized_at else None,
            # Per-modality breakdown for API response
            "breakdown": {
                "face": {
                    "score": round((signals.face_similarity_score or 0) * 100, 2),
                    "liveness_passed": signals.face_liveness_passed,
                },
                "iris": {
                    "match_score": round((signals.iris_match_score or 0) * 100, 2),
                    "hamming_distance": signals.iris_hamming_distance,
                } if signals.iris_match_score is not None else None,
                "fingerprint": {
                    "match_score": round((signals.fingerprint_match_score or 0) * 100, 2),
                    "minutiae_pairs": signals.fingerprint_minutiae_pairs,
                } if signals.fingerprint_match_score is not None else None,
            },
        }

    # ── Internal biometric runners ──────────────────────────────────────────

    async def _run_face_verification(
        self,
        image_bytes: bytes,
        threshold_override: float | None = None,
    ) -> dict:
        """Run the existing face verification pipeline and return signal dict."""
        from app.services.verification_service import VerificationService
        from app.services.face_embedding import FaceEmbeddingService
        from app.services.liveness_service import LivenessService
        import hashlib

        embedder = FaceEmbeddingService()
        liveness = LivenessService()
        svc = VerificationService(
            db=self.db,
            detector=self.face_detector,
            embedder=embedder,
            liveness=liveness,
        )
        response = await svc.verify(
            image_bytes=image_bytes,
            ip_address=None,
            user_agent=None,
            threshold=threshold_override,
            use_pipeline=True,
        )

        embedding_hash = None
        if response.user_id:
            embeddings = await self.embedding_repo.get_by_user(response.user_id)
            if embeddings:
                embedding_hash = hashlib.sha256(
                    str(embeddings[0].embedding_vector).encode()
                ).hexdigest()

        return {
            "confidence_score": response.confidence_score,
            "liveness_score": response.liveness_score,
            "liveness_passed": response.liveness_detail.is_live,
            "anti_spoof_passed": response.liveness_detail.anti_spoof_score >= 50,
            "blink_detected": response.liveness_detail.blink_detected,
            "head_turn_detected": response.liveness_detail.head_turn_detected,
            "user_id": str(response.user_id) if response.user_id else None,
            "embedding_hash": embedding_hash,
        }

    async def _run_iris_verification(self, image_bytes: bytes) -> dict:
        """Run iris pipeline and return signal dict."""
        iris_code = self.iris_service.process_image(image_bytes)
        if iris_code is None:
            return {"match_score": 0.0, "hamming_distance": 1.0, "user_id": None, "code_hash": None}

        enrolled = await self.iris_repo.get_all()
        result = self.iris_service.match(iris_code, enrolled)

        return {
            "match_score": result.match_score,
            "hamming_distance": result.hamming_distance,
            "user_id": result.matched_user_id,
            "code_hash": iris_code.sha256,
        }

    async def _run_fingerprint_verification(self, image_bytes: bytes) -> dict:
        """Run fingerprint pipeline and return signal dict."""
        template = self.fingerprint_service.extract_minutiae(image_bytes)
        if template is None:
            return {"match_score": 0.0, "minutiae_pairs": 0, "user_id": None, "template_hash": None}

        enrolled = await self.fingerprint_repo.get_all()
        result = self.fingerprint_service.match(template, enrolled)

        return {
            "match_score": result.match_score,
            "minutiae_pairs": result.minutiae_pairs,
            "user_id": result.matched_user_id,
            "template_hash": template.sha256,
        }
