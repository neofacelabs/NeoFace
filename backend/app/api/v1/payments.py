"""
NeoFace Payments API
Biometric payment authorization endpoints.

POST /api/v1/payments/authorize   — Authorize a payment with biometric proof
GET  /api/v1/payments/history     — Paginated transaction history (user)
GET  /api/v1/payments/{id}        — Single transaction detail
GET  /api/v1/payments/admin/all   — All transactions (admin)
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import TokenData, get_current_user, require_admin, get_current_merchant, get_current_user_optional
from app.models.merchant import Merchant
from app.repositories.transaction_repository import TransactionRepository
from app.schemas.payment import (
    PaymentAuthorizeResponse,
    PaymentBreakdown,
    BiometricBreakdownFace,
    BiometricBreakdownIris,
    BiometricBreakdownFingerprint,
    TransactionListResponse,
    TransactionResponse,
)
from app.services.payment_service import PaymentAuthorizationService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.post(
    "/authorize",
    response_model=PaymentAuthorizeResponse,
    summary="Authorize a biometric payment",
    status_code=status.HTTP_200_OK,
)
async def authorize_payment(
    request: Request,
    # Financial fields
    amount: float = Form(..., gt=0, description="Payment amount"),
    currency: str = Form(default="USD"),
    merchant_id: uuid.UUID | None = Form(default=None),
    merchant_reference: str | None = Form(default=None),
    description: str | None = Form(default=None),
    # Biometric files (at least one required)
    face_image: UploadFile | None = File(default=None, description="Face photo for biometric auth"),
    iris_image: UploadFile | None = File(default=None, description="Iris close-up for iris auth"),
    fingerprint_image: UploadFile | None = File(default=None, description="Fingerprint scan image"),
    current_user: TokenData | None = Depends(get_current_user_optional),
    merchant: Merchant | None = Depends(get_current_merchant),
    db: AsyncSession = Depends(get_db),
) -> PaymentAuthorizeResponse:
    """
    Authorize a payment using one or more biometric modalities.

    The endpoint accepts multipart/form-data with:
    - Financial parameters (amount, currency, merchant_id)
    - One or more biometric image files (face_image, iris_image, fingerprint_image)

    Returns a fusion-scored authorization decision with per-modality breakdown.
    """
    if not current_user and not merchant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Provide a valid user token or merchant API key."
        )

    if not any([face_image, iris_image, fingerprint_image]):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least one biometric image (face_image, iris_image, or fingerprint_image) is required.",
        )

    # Restrict/enforce merchant tenant id
    if merchant:
        merchant_id = merchant.id

    # Read image bytes
    face_bytes = await face_image.read() if face_image else None
    iris_bytes = await iris_image.read() if iris_image else None
    fingerprint_bytes = await fingerprint_image.read() if fingerprint_image else None

    # Client context
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    device_id = request.headers.get("x-device-id")

    svc = PaymentAuthorizationService(db=db)
    result = await svc.authorize(
        amount=amount,
        currency=currency,
        merchant_id=merchant_id,
        merchant_reference=merchant_reference,
        description=description,
        face_image_bytes=face_bytes,
        iris_image_bytes=iris_bytes,
        fingerprint_image_bytes=fingerprint_bytes,
        ip_address=ip_address,
        device_id=device_id,
        user_agent=user_agent,
    )

    # Build breakdown
    breakdown_data = result.get("breakdown", {})
    face_bd = None
    iris_bd = None
    fp_bd = None
    if breakdown_data.get("face"):
        face_bd = BiometricBreakdownFace(**breakdown_data["face"])
    if breakdown_data.get("iris"):
        iris_bd = BiometricBreakdownIris(**breakdown_data["iris"])
    if breakdown_data.get("fingerprint"):
        fp_bd = BiometricBreakdownFingerprint(**breakdown_data["fingerprint"])

    return PaymentAuthorizeResponse(
        authorized=result["authorized"],
        transaction_id=result.get("transaction_id"),
        amount=result["amount"],
        currency=result["currency"],
        status=result["status"],
        fusion_score=result["fusion_score"],
        threshold_used=result["threshold_used"],
        modalities_used=result["modalities_used"],
        resolved_user_id=result.get("resolved_user_id"),
        failure_reason=result.get("failure_reason"),
        is_liveness_passed=result["is_liveness_passed"],
        authorized_at=result.get("authorized_at"),
        breakdown=PaymentBreakdown(face=face_bd, iris=iris_bd, fingerprint=fp_bd),
    )


@router.get(
    "/history",
    response_model=TransactionListResponse,
    summary="Get payment history for current user or merchant",
)
async def get_payment_history(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    status_filter: str | None = Query(default=None, alias="status"),
    current_user: TokenData | None = Depends(get_current_user_optional),
    merchant: Merchant | None = Depends(get_current_merchant),
    db: AsyncSession = Depends(get_db),
) -> TransactionListResponse:
    """Returns paginated payment history for the authenticated user or merchant."""
    if not current_user and not merchant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Provide a valid user token or merchant API key."
        )

    txn_repo = TransactionRepository(db)
    if merchant:
        transactions, total = await txn_repo.get_recent(
            page=page,
            page_size=page_size,
            merchant_id=merchant.id,
            status=status_filter,
        )
    else:
        # current_user is guaranteed to be not None here
        transactions, total = await txn_repo.get_by_user(
            user_id=current_user.user_uuid,
            page=page,
            page_size=page_size,
            status=status_filter,
        )
    return TransactionListResponse(
        total=total,
        page=page,
        page_size=page_size,
        transactions=[TransactionResponse.model_validate(t) for t in transactions],
    )


@router.get(
    "/admin/all",
    response_model=TransactionListResponse,
    summary="All transactions (admin only)",
    dependencies=[Depends(require_admin)],
)
async def get_all_transactions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    status_filter: str | None = Query(default=None, alias="status"),
    db: AsyncSession = Depends(get_db),
) -> TransactionListResponse:
    """Admin-only: paginated list of all transactions across all users."""
    txn_repo = TransactionRepository(db)
    transactions, total = await txn_repo.get_recent(
        page=page,
        page_size=page_size,
        status=status_filter,
    )
    return TransactionListResponse(
        total=total,
        page=page,
        page_size=page_size,
        transactions=[TransactionResponse.model_validate(t) for t in transactions],
    )


@router.get(
    "/{transaction_id}",
    response_model=TransactionResponse,
    summary="Get a single transaction by ID",
)
async def get_transaction(
    transaction_id: uuid.UUID,
    current_user: TokenData | None = Depends(get_current_user_optional),
    merchant: Merchant | None = Depends(get_current_merchant),
    db: AsyncSession = Depends(get_db),
) -> TransactionResponse:
    """Retrieve a single transaction. Users can only access their own transactions. Merchants can only access theirs."""
    if not current_user and not merchant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required: Provide a valid user token or merchant API key."
        )

    txn_repo = TransactionRepository(db)
    txn = await txn_repo.get_by_id(transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    # Authorization: allow admin, owner user, or matching merchant
    is_admin = current_user and current_user.role in ("admin", "superadmin")
    is_owner = current_user and txn.user_id == current_user.user_uuid
    is_merchant = merchant and txn.merchant_id == merchant.id

    if not (is_admin or is_owner or is_merchant):
        raise HTTPException(status_code=403, detail="Access denied")

    return TransactionResponse.model_validate(txn)
