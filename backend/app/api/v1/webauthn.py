"""
NeoFace WebAuthn API — FIDO2/WebAuthn fingerprint enrollment & payment signing.

SECURITY MODEL:
  - Private keys NEVER leave the device secure enclave.
  - Only publicKey + credentialId stored server-side.
  - No fingerprint images, templates, or raw scans accepted.

Endpoints:
  POST /api/v1/webauthn/register/begin
  POST /api/v1/webauthn/register/complete
  POST /api/v1/webauthn/authenticate/begin
  POST /api/v1/webauthn/authenticate/complete
  GET  /api/v1/webauthn/devices
  PATCH /api/v1/webauthn/devices/{id}
  DELETE /api/v1/webauthn/devices/{id}
  PATCH /api/v1/webauthn/devices/{id}/payments
  POST /api/v1/webauthn/payment/begin
  POST /api/v1/webauthn/payment/complete
"""

import json
import uuid
from typing import Any

import webauthn
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from webauthn import (
    generate_registration_options,
    options_to_json,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url
from webauthn.helpers.structs import (
    AuthenticatorAttestationResponse,
    AuthenticatorAssertionResponse,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    RegistrationCredential,
    AuthenticationCredential,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from app.core.config import settings
from app.core.database import get_db
from app.core.security import TokenData, get_current_user
from app.repositories.credential_repository import CredentialRepository

router = APIRouter(prefix="/webauthn", tags=["WebAuthn"])

# ── Relying Party config (read from env so production works correctly) ─────────
RP_ID = settings.WEBAUTHN_RP_ID
RP_NAME = "NeoFace"
EXPECTED_ORIGIN = settings.WEBAUTHN_EXPECTED_ORIGIN

# ── In-memory challenge store (use Redis in production) ───────────────────────
_challenges: dict[str, bytes] = {}
_payment_challenges: dict[str, dict] = {}


def _challenge_key(user_id: uuid.UUID, flow: str) -> str:
    return f"{flow}:{user_id}"


# ── Schemas ───────────────────────────────────────────────────────────────────

class AuthenticatorResponseDict(BaseModel):
    clientDataJSON: str
    attestationObject: str | None = None
    authenticatorData: str | None = None
    signature: str | None = None
    userHandle: str | None = None


class RegisterCompleteRequest(BaseModel):
    credential_id: str
    raw_id: str
    response: AuthenticatorResponseDict
    type: str
    device_name: str = "My Device"
    device_metadata: dict = {}


class AuthenticateCompleteRequest(BaseModel):
    credential_id: str
    raw_id: str
    response: AuthenticatorResponseDict
    type: str


class RenameDeviceRequest(BaseModel):
    device_name: str


class PaymentToggleRequest(BaseModel):
    enabled: bool


class WebAuthnPaymentBeginRequest(BaseModel):
    amount: float
    currency: str = "INR"
    merchant_name: str = "NeoFace Merchant"
    description: str = ""


class WebAuthnPaymentCompleteRequest(BaseModel):
    transaction_ref: str
    credential_id: str
    raw_id: str
    response: AuthenticatorResponseDict
    type: str


# ═══════════════════════════════════════════════════════════════════════════════
# REGISTRATION
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/register/begin")
async def register_begin(
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    repo = CredentialRepository(db)
    existing = await repo.list_by_user(current_user.user_uuid)
    exclude_credentials = [
        PublicKeyCredentialDescriptor(id=c.credential_id)
        for c in existing if c.is_active
    ]

    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=str(current_user.user_uuid).encode(),
        user_name=current_user.email,
        user_display_name=current_user.email,
        authenticator_selection=AuthenticatorSelectionCriteria(
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=exclude_credentials,
    )

    _challenges[_challenge_key(current_user.user_uuid, "reg")] = options.challenge
    return JSONResponse(content=json.loads(options_to_json(options)))


@router.post("/register/complete")
async def register_complete(
    body: RegisterCompleteRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    key = _challenge_key(current_user.user_uuid, "reg")
    expected_challenge = _challenges.get(key)
    if not expected_challenge:
        raise HTTPException(400, "No active registration challenge. Call /register/begin first.")

    try:
        credential = RegistrationCredential(
            id=body.credential_id,
            raw_id=base64url_to_bytes(body.raw_id),
            response=AuthenticatorAttestationResponse(
                client_data_json=base64url_to_bytes(body.response.clientDataJSON),
                attestation_object=base64url_to_bytes(body.response.attestationObject or ""),
            ),
            type=body.type,
        )
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=RP_ID,
            expected_origin=EXPECTED_ORIGIN,
            require_user_verification=True,
        )
    except Exception as exc:
        raise HTTPException(400, f"Attestation verification failed: {exc}")

    repo = CredentialRepository(db)
    existing = await repo.get_by_credential_id(verification.credential_id)
    if existing:
        raise HTTPException(409, "This device is already enrolled.")

    ua = request.headers.get("user-agent", "")
    cred = await repo.create(
        user_id=current_user.user_uuid,
        credential_id=verification.credential_id,
        public_key=verification.credential_public_key,
        sign_count=verification.sign_count,
        aaguid=str(verification.aaguid) if verification.aaguid else None,
        device_name=body.device_name or _guess_device_name(ua),
        device_metadata={**body.device_metadata, "user_agent": ua},
    )

    _challenges.pop(key, None)
    return {
        "enrolled": True,
        "credential_uuid": str(cred.id),
        "device_name": cred.device_name,
        "enrolled_at": cred.enrolled_at.isoformat(),
    }


# ═══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/authenticate/begin")
async def authenticate_begin(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> JSONResponse:
    repo = CredentialRepository(db)
    credentials = await repo.list_by_user(current_user.user_uuid)
    active = [c for c in credentials if c.is_active]
    if not active:
        raise HTTPException(404, "No enrolled fingerprint devices found.")

    allow_credentials = [PublicKeyCredentialDescriptor(id=c.credential_id) for c in active]
    options = generate_authentication_options(
        rp_id=RP_ID,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    _challenges[_challenge_key(current_user.user_uuid, "auth")] = options.challenge
    return JSONResponse(content=json.loads(options_to_json(options)))


@router.post("/authenticate/complete")
async def authenticate_complete(
    body: AuthenticateCompleteRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    key = _challenge_key(current_user.user_uuid, "auth")
    expected_challenge = _challenges.get(key)
    if not expected_challenge:
        raise HTTPException(400, "No active authentication challenge.")

    raw_cred_id = base64url_to_bytes(body.credential_id)
    repo = CredentialRepository(db)
    stored = await repo.get_by_credential_id(raw_cred_id)
    if not stored:
        raise HTTPException(404, "Credential not found or revoked.")
    if stored.user_id != current_user.user_uuid:
        raise HTTPException(403, "Credential belongs to a different user.")

    try:
        credential = AuthenticationCredential(
            id=body.credential_id,
            raw_id=base64url_to_bytes(body.raw_id),
            response=AuthenticatorAssertionResponse(
                client_data_json=base64url_to_bytes(body.response.clientDataJSON),
                authenticator_data=base64url_to_bytes(body.response.authenticatorData or ""),
                signature=base64url_to_bytes(body.response.signature or ""),
                user_handle=base64url_to_bytes(body.response.userHandle) if body.response.userHandle else None,
            ),
            type=body.type,
        )
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=expected_challenge,
            expected_rp_id=RP_ID,
            expected_origin=EXPECTED_ORIGIN,
            credential_public_key=stored.public_key,
            credential_current_sign_count=stored.sign_count,
            require_user_verification=True,
        )
    except Exception as exc:
        raise HTTPException(400, f"Authentication failed: {exc}")

    await repo.update_sign_count(raw_cred_id, verification.new_sign_count)
    _challenges.pop(key, None)
    return {"verified": True, "credential_uuid": str(stored.id), "device_name": stored.device_name}


# ═══════════════════════════════════════════════════════════════════════════════
# DEVICE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/devices")
async def list_devices(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = CredentialRepository(db)
    creds = await repo.list_by_user(current_user.user_uuid)
    return {
        "devices": [
            {
                "id": str(c.id),
                "device_name": c.device_name,
                "aaguid": c.aaguid,
                "is_active": c.is_active,
                "fingerprint_payments_enabled": c.fingerprint_payments_enabled,
                "enrolled_at": c.enrolled_at.isoformat(),
                "last_used_at": c.last_used_at.isoformat() if c.last_used_at else None,
            }
            for c in creds
        ],
        "total": len(creds),
        "active_count": sum(1 for c in creds if c.is_active),
    }


@router.patch("/devices/{cred_id}")
async def rename_device(
    cred_id: uuid.UUID,
    body: RenameDeviceRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = CredentialRepository(db)
    updated = await repo.update_device_name(cred_id, current_user.user_uuid, body.device_name)
    if not updated:
        raise HTTPException(404, "Device not found.")
    return {"updated": True, "device_name": body.device_name}


@router.delete("/devices/{cred_id}")
async def revoke_device(
    cred_id: uuid.UUID,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = CredentialRepository(db)
    revoked = await repo.revoke(cred_id, current_user.user_uuid)
    if not revoked:
        raise HTTPException(404, "Device not found.")
    return {"revoked": True}


@router.patch("/devices/{cred_id}/payments")
async def toggle_payment_signing(
    cred_id: uuid.UUID,
    body: PaymentToggleRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    repo = CredentialRepository(db)
    updated = await repo.set_payment_enabled(cred_id, current_user.user_uuid, body.enabled)
    if not updated:
        raise HTTPException(404, "Device not found.")
    return {"fingerprint_payments_enabled": body.enabled}


# ═══════════════════════════════════════════════════════════════════════════════
# PAYMENT AUTHORIZATION
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("/payment/begin")
async def payment_begin(
    body: WebAuthnPaymentBeginRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Risk-tiered WebAuthn payment challenge."""
    amount_inr = body.amount if body.currency == "INR" else body.amount * 84
    if amount_inr < 1000:
        risk_tier, required_factors = "low", ["fingerprint"]
    elif amount_inr <= 10000:
        risk_tier, required_factors = "medium", ["fingerprint", "face"]
    else:
        risk_tier, required_factors = "high", ["fingerprint", "face", "otp"]

    repo = CredentialRepository(db)
    credentials = await repo.list_by_user(current_user.user_uuid)
    active_payment = [c for c in credentials if c.is_active and c.fingerprint_payments_enabled]
    if not active_payment:
        raise HTTPException(404, "No fingerprint device enabled for payments.")

    allow_credentials = [PublicKeyCredentialDescriptor(id=c.credential_id) for c in active_payment]
    options = generate_authentication_options(
        rp_id=RP_ID,
        allow_credentials=allow_credentials,
        user_verification=UserVerificationRequirement.REQUIRED,
    )

    transaction_ref = str(uuid.uuid4())
    _payment_challenges[transaction_ref] = {
        "challenge": options.challenge,
        "user_id": str(current_user.user_uuid),
        "amount": body.amount,
        "currency": body.currency,
        "merchant_name": body.merchant_name,
        "risk_tier": risk_tier,
        "required_factors": required_factors,
    }

    opts_dict = json.loads(options_to_json(options))
    opts_dict.update({
        "transaction_ref": transaction_ref,
        "risk_tier": risk_tier,
        "required_factors": required_factors,
        "amount": body.amount,
        "currency": body.currency,
        "merchant_name": body.merchant_name,
    })
    return opts_dict


@router.post("/payment/complete")
async def payment_complete(
    body: WebAuthnPaymentCompleteRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    ctx = _payment_challenges.get(body.transaction_ref)
    if not ctx:
        raise HTTPException(400, "Invalid or expired payment challenge.")
    if ctx["user_id"] != str(current_user.user_uuid):
        raise HTTPException(403, "Challenge user mismatch.")

    raw_cred_id = base64url_to_bytes(body.credential_id)
    repo = CredentialRepository(db)
    stored = await repo.get_by_credential_id(raw_cred_id)
    if not stored or stored.user_id != current_user.user_uuid:
        raise HTTPException(404, "Credential not found.")
    if not stored.fingerprint_payments_enabled:
        raise HTTPException(403, "Fingerprint payments disabled for this device.")

    try:
        credential = AuthenticationCredential(
            id=body.credential_id,
            raw_id=base64url_to_bytes(body.raw_id),
            response=AuthenticatorAssertionResponse(
                client_data_json=base64url_to_bytes(body.response.clientDataJSON),
                authenticator_data=base64url_to_bytes(body.response.authenticatorData or ""),
                signature=base64url_to_bytes(body.response.signature or ""),
                user_handle=base64url_to_bytes(body.response.userHandle) if body.response.userHandle else None,
            ),
            type=body.type,
        )
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=ctx["challenge"],
            expected_rp_id=RP_ID,
            expected_origin=EXPECTED_ORIGIN,
            credential_public_key=stored.public_key,
            credential_current_sign_count=stored.sign_count,
            require_user_verification=True,
        )
    except Exception as exc:
        raise HTTPException(400, f"Payment signature verification failed: {exc}")

    await repo.update_sign_count(raw_cred_id, verification.new_sign_count)
    _payment_challenges.pop(body.transaction_ref, None)

    return {
        "authorized": True,
        "transaction_ref": body.transaction_ref,
        "amount": ctx["amount"],
        "currency": ctx["currency"],
        "merchant_name": ctx["merchant_name"],
        "risk_tier": ctx["risk_tier"],
        "required_factors": ctx["required_factors"],
        "device_name": stored.device_name,
    }


def _guess_device_name(ua: str) -> str:
    ua_lower = ua.lower()
    if "iphone" in ua_lower:
        return "iPhone (Touch ID)"
    if "mac" in ua_lower and "safari" in ua_lower:
        return "Mac (Touch ID)"
    if "windows" in ua_lower:
        return "Windows PC (Windows Hello)"
    if "android" in ua_lower:
        return "Android Device"
    return "My Device"
