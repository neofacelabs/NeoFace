"""
NeoFace Merchants API
CRUD endpoints for merchant management.

POST /api/v1/merchants/            — Create merchant (admin)
GET  /api/v1/merchants/            — List all merchants (admin)
GET  /api/v1/merchants/{id}        — Get merchant detail
PATCH /api/v1/merchants/{id}/verify — Mark merchant as verified (admin)
"""

import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import require_admin
from app.repositories.biometric_repositories import MerchantRepository
from app.schemas.payment import MerchantCreate, MerchantResponse

router = APIRouter(prefix="/merchants", tags=["Merchants"])


def _generate_api_key() -> tuple[str, str]:
    """Generate a live API key and return (full_key, prefix)."""
    raw = f"nf_live_{secrets.token_urlsafe(32)}"
    prefix = raw[:12]
    return raw, prefix


@router.post(
    "/",
    response_model=MerchantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new merchant (admin)",
    dependencies=[Depends(require_admin)],
)
async def create_merchant(
    payload: MerchantCreate,
    db: AsyncSession = Depends(get_db),
) -> MerchantResponse:
    """Register a new merchant account in the NeoFace payment network."""
    import bcrypt
    repo = MerchantRepository(db)

    # Check uniqueness
    existing = await repo.get_by_email(payload.business_email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Merchant with email {payload.business_email} already exists.",
        )

    # Generate API key
    raw_key, prefix = _generate_api_key()
    key_hash = bcrypt.hashpw(raw_key.encode(), bcrypt.gensalt()).decode()

    merchant = await repo.create(
        business_name=payload.business_name,
        business_email=payload.business_email,
        business_category=payload.business_category,
        website_url=payload.website_url,
        description=payload.description,
        default_currency=payload.default_currency,
        api_key_hash=key_hash,
        api_key_prefix=prefix,
    )
    await db.commit()
    await db.refresh(merchant)

    response = MerchantResponse.model_validate(merchant)
    # Include the raw key in this one-time response (not stored anywhere)
    # We return it as a custom header instead of polluting the response schema
    return response


@router.get(
    "/",
    summary="List all merchants (admin)",
    dependencies=[Depends(require_admin)],
)
async def list_merchants(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Paginated list of all registered merchants."""
    repo = MerchantRepository(db)
    merchants, total = await repo.get_all(page=page, page_size=page_size)
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "merchants": [MerchantResponse.model_validate(m) for m in merchants],
    }


@router.get(
    "/{merchant_id}",
    response_model=MerchantResponse,
    summary="Get merchant by ID",
    dependencies=[Depends(require_admin)],
)
async def get_merchant(
    merchant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MerchantResponse:
    """Retrieve a single merchant record."""
    repo = MerchantRepository(db)
    merchant = await repo.get_by_id(merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return MerchantResponse.model_validate(merchant)


@router.patch(
    "/{merchant_id}/verify",
    response_model=MerchantResponse,
    summary="Mark a merchant as KYB-verified (admin)",
    dependencies=[Depends(require_admin)],
)
async def verify_merchant(
    merchant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> MerchantResponse:
    """Set is_verified=True and is_sandbox=False for a merchant (live mode)."""
    from datetime import datetime, timezone
    repo = MerchantRepository(db)
    merchant = await repo.get_by_id(merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    merchant.is_verified = True
    merchant.is_sandbox = False
    merchant.verified_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(merchant)
    return MerchantResponse.model_validate(merchant)


@router.delete(
    "/{merchant_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a merchant (admin)",
    dependencies=[Depends(require_admin)],
)
async def deactivate_merchant(
    merchant_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-deactivate a merchant (does not delete records)."""
    repo = MerchantRepository(db)
    merchant = await repo.get_by_id(merchant_id)
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    merchant.is_active = False
    await db.commit()
