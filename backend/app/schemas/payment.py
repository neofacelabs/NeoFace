"""
NeoFace Payment Schemas
Pydantic v2 models for payment authorization request/response.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Request ────────────────────────────────────────────────────────────────────

class PaymentAuthorizeRequest(BaseModel):
    """Request body fields for payment authorization (non-file fields)."""
    amount: float = Field(..., gt=0, description="Payment amount (positive)")
    currency: str = Field(default="USD", min_length=3, max_length=3)
    merchant_id: uuid.UUID | None = Field(default=None)
    merchant_reference: str | None = Field(default=None, max_length=255)
    description: str | None = Field(default=None, max_length=500)


# ── Response ───────────────────────────────────────────────────────────────────

class BiometricBreakdownFace(BaseModel):
    score: float = Field(..., description="Face match score (0–100)")
    liveness_passed: bool


class BiometricBreakdownIris(BaseModel):
    match_score: float = Field(..., description="Iris match score (0–100)")
    hamming_distance: float | None


class BiometricBreakdownFingerprint(BaseModel):
    match_score: float = Field(..., description="Fingerprint match score (0–100)")
    minutiae_pairs: int


class PaymentBreakdown(BaseModel):
    face: BiometricBreakdownFace | None = None
    iris: BiometricBreakdownIris | None = None
    fingerprint: BiometricBreakdownFingerprint | None = None


class PaymentAuthorizeResponse(BaseModel):
    """Response returned after a biometric payment authorization attempt."""

    authorized: bool
    transaction_id: uuid.UUID | None
    amount: float
    currency: str
    status: str = Field(..., description="pending | authorized | failed")
    fusion_score: float = Field(..., ge=0.0, le=1.0)
    threshold_used: float
    modalities_used: list[str]
    resolved_user_id: uuid.UUID | None = None
    failure_reason: str | None = None
    is_liveness_passed: bool
    authorized_at: datetime | None = None
    breakdown: PaymentBreakdown | None = None


# ── Transaction history ────────────────────────────────────────────────────────

class TransactionResponse(BaseModel):
    """Single transaction record for history / dashboard."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    merchant_id: uuid.UUID | None
    amount: float
    currency: str
    status: str
    biometric_modality: str
    fusion_score: float | None
    failure_reason: str | None
    description: str | None
    merchant_reference: str | None
    ip_address: str | None
    created_at: datetime
    authorized_at: datetime | None
    settled_at: datetime | None


class TransactionListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    transactions: list[TransactionResponse]


# ── Merchant schemas ───────────────────────────────────────────────────────────

class MerchantCreate(BaseModel):
    business_name: str = Field(..., min_length=2, max_length=255)
    business_email: str = Field(..., max_length=320)
    business_category: str | None = None
    website_url: str | None = None
    description: str | None = None
    default_currency: str = Field(default="USD", min_length=3, max_length=3)


class MerchantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    business_name: str
    business_email: str
    business_category: str | None
    website_url: str | None
    is_verified: bool
    is_active: bool
    is_sandbox: bool
    default_currency: str
    api_key_prefix: str | None
    created_at: datetime


# ── Bank account schemas ───────────────────────────────────────────────────────

class BankAccountLinkRequest(BaseModel):
    bank_name: str = Field(..., min_length=2, max_length=255)
    account_type: str = Field(default="checking", pattern="^(checking|savings|business)$")
    account_mask: str = Field(..., min_length=4, max_length=4, pattern="^[0-9]{4}$")
    routing_mask: str | None = Field(default=None, min_length=4, max_length=4)
    account_holder_name: str | None = None
    token_provider: str = Field(default="internal", description="internal | plaid | stripe")
    encrypted_token: str = Field(..., description="Provider bank token or AES-encrypted reference")
    external_account_id: str | None = None
    currency: str = Field(default="USD", min_length=3, max_length=3)
    is_default: bool = False


class BankAccountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    bank_name: str
    account_type: str
    account_mask: str
    account_holder_name: str | None
    token_provider: str
    currency: str
    is_verified: bool
    is_default: bool
    is_active: bool
    linked_at: datetime
