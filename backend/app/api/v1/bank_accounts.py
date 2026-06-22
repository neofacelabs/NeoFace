"""
NeoFace Bank Accounts API
Endpoints for linking and managing bank accounts for payment settlement.

POST /api/v1/bank-accounts/link         — Link a bank account
GET  /api/v1/bank-accounts/             — List user's linked accounts
PATCH /api/v1/bank-accounts/{id}/default — Set as default account
DELETE /api/v1/bank-accounts/{id}       — Unlink (soft-delete)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import TokenData, get_current_user
from app.repositories.biometric_repositories import BankAccountRepository
from app.schemas.payment import BankAccountLinkRequest, BankAccountResponse

router = APIRouter(prefix="/bank_accounts", tags=["Bank Accounts"])


@router.post(
    "/link",
    response_model=BankAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Link a bank account for payment settlement",
)
async def link_bank_account(
    payload: BankAccountLinkRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BankAccountResponse:
    """
    Link a bank account to the authenticated user's profile.

    The encrypted_token field should contain:
    - A Plaid access_token (for Plaid integration)
    - A Stripe bank account token (for Stripe integration)
    - An AES-encrypted bank reference (for internal/manual linking)

    Raw account numbers must NEVER be sent to this endpoint.
    """
    repo = BankAccountRepository(db)

    # If user sets is_default=True, unset previous default first
    if payload.is_default:
        existing_accounts = await repo.get_by_user(current_user.user_id)
        for acc in existing_accounts:
            if acc.is_default:
                acc.is_default = False

    account = await repo.create(
        user_id=current_user.user_id,
        bank_name=payload.bank_name,
        account_type=payload.account_type,
        account_mask=payload.account_mask,
        routing_mask=payload.routing_mask,
        account_holder_name=payload.account_holder_name,
        encrypted_token=payload.encrypted_token,
        token_provider=payload.token_provider,
        external_account_id=payload.external_account_id,
        currency=payload.currency,
        is_default=payload.is_default,
    )
    await db.commit()
    await db.refresh(account)
    return BankAccountResponse.model_validate(account)


@router.get(
    "/",
    summary="List linked bank accounts",
)
async def list_bank_accounts(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Returns all active bank accounts linked to the authenticated user."""
    repo = BankAccountRepository(db)
    accounts = await repo.get_by_user(current_user.user_id)
    return {
        "total": len(accounts),
        "accounts": [BankAccountResponse.model_validate(a) for a in accounts],
    }


@router.patch(
    "/{account_id}/default",
    response_model=BankAccountResponse,
    summary="Set an account as the default payment account",
)
async def set_default_account(
    account_id: uuid.UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BankAccountResponse:
    """Designate a linked account as the default for biometric payment settlement."""
    repo = BankAccountRepository(db)
    all_accounts = await repo.get_by_user(current_user.user_id)

    target = None
    for acc in all_accounts:
        if acc.id == account_id:
            target = acc
        acc.is_default = False  # Clear all

    if not target:
        raise HTTPException(status_code=404, detail="Bank account not found or not owned by you")

    target.is_default = True
    await db.commit()
    await db.refresh(target)
    return BankAccountResponse.model_validate(target)


@router.delete(
    "/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Unlink a bank account",
)
async def unlink_bank_account(
    account_id: uuid.UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Soft-delete a linked bank account (sets is_active=False)."""
    repo = BankAccountRepository(db)
    all_accounts = await repo.get_by_user(current_user.user_id)

    target = next((a for a in all_accounts if a.id == account_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Bank account not found or not owned by you")

    target.is_active = False
    target.is_default = False
    await db.commit()
