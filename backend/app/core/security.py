"""
NeoFace Security Module
Handles:
- JWT token creation and verification
- Password hashing and verification (bcrypt)
- OAuth2 password flow
- Token payload models
"""

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, computed_field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger

# ── OAuth2 scheme ─────────────────────────────────────────────────────────────
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Token models ──────────────────────────────────────────────────────────────
class TokenData(BaseModel):
    """Data extracted from a valid JWT token."""

    user_id: str
    email: str
    role: str
    exp: datetime

    @computed_field  # type: ignore[misc]
    @property
    def user_uuid(self) -> UUID:
        """Convenience UUID-typed user_id for repository calls."""
        return UUID(self.user_id)


class TokenPair(BaseModel):
    """Access + refresh token pair returned on login."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires


# ── Password hashing ──────────────────────────────────────────────────────────
class PasswordHasher:
    """
    Bcrypt-based password hashing.
    Uses cost factor 12 for production-grade security.
    """

    ROUNDS: int = 12

    @staticmethod
    def hash(plain_password: str) -> str:
        """Hash a plain-text password."""
        salt = bcrypt.gensalt(rounds=PasswordHasher.ROUNDS)
        hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
        return hashed.decode("utf-8")

    @staticmethod
    def verify(plain_password: str, hashed_password: str) -> bool:
        """Verify a plain-text password against its hash."""
        try:
            return bcrypt.checkpw(
                plain_password.encode("utf-8"),
                hashed_password.encode("utf-8"),
            )
        except Exception:
            return False


# ── JWT utilities ─────────────────────────────────────────────────────────────
class JWTHandler:
    """Handles JWT creation, signing, and verification."""

    @staticmethod
    def create_access_token(
        user_id: str,
        email: str,
        role: str,
        extra_claims: dict[str, Any] | None = None,
    ) -> str:
        """
        Create a signed JWT access token.
        Expires in JWT_ACCESS_TOKEN_EXPIRE_MINUTES.
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

        payload: dict[str, Any] = {
            "sub": user_id,
            "email": email,
            "role": role,
            "type": "access",
            "iat": now,
            "exp": expire,
        }

        if extra_claims:
            payload.update(extra_claims)

        return jwt.encode(
            payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )

    @staticmethod
    def create_refresh_token(user_id: str, email: str) -> str:
        """
        Create a signed JWT refresh token.
        Longer-lived; used to obtain new access tokens.
        """
        now = datetime.now(timezone.utc)
        expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

        payload: dict[str, Any] = {
            "sub": user_id,
            "email": email,
            "type": "refresh",
            "iat": now,
            "exp": expire,
        }

        return jwt.encode(
            payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )

    @staticmethod
    def decode_token(token: str) -> dict[str, Any]:
        """
        Decode and verify a JWT token.
        Raises HTTPException on invalid or expired tokens.
        """
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET,
                algorithms=[settings.JWT_ALGORITHM],
            )
            return payload
        except JWTError as exc:
            logger.warning("JWT decode failed", error=str(exc))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @staticmethod
    def create_token_pair(user_id: str, email: str, role: str) -> TokenPair:
        """Create both access and refresh tokens."""
        access_token = JWTHandler.create_access_token(user_id, email, role)
        refresh_token = JWTHandler.create_refresh_token(user_id, email)
        return TokenPair(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )


# ── Dependencies ──────────────────────────────────────────────────────────────
async def get_current_user_token(
    token: str = Depends(oauth2_scheme),
) -> TokenData:
    """
    FastAPI dependency: decode JWT and return TokenData.
    Raises 401 if token is missing, invalid, or expired.
    """
    payload = JWTHandler.decode_token(token)

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenData(
        user_id=payload["sub"],
        email=payload["email"],
        role=payload.get("role", "user"),
        exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
    )


async def require_admin(
    token_data: TokenData = Depends(get_current_user_token),
) -> TokenData:
    """
    FastAPI dependency: require admin role.
    Raises 403 if the user is not an admin.
    """
    if token_data.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return token_data


# ── Convenience singletons ────────────────────────────────────────────────────
password_hasher = PasswordHasher()
jwt_handler = JWTHandler()

oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

async def get_current_user_optional(
    token: str | None = Depends(oauth2_scheme_optional),
) -> TokenData | None:
    """
    FastAPI dependency: decode JWT optionally and return TokenData or None.
    Does not raise exception if token is missing.
    """
    if not token:
        return None
    try:
        payload = JWTHandler.decode_token(token)
        if payload.get("type") != "access":
            return None
        return TokenData(
            user_id=payload["sub"],
            email=payload["email"],
            role=payload.get("role", "user"),
            exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
        )
    except Exception:
        return None

# Alias for use in new routers
get_current_user = get_current_user_token



# ── Merchant API Key Security ──────────────────────────────────────────────────
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from app.core.database import get_db

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)

async def get_current_merchant(
    api_key: str | None = Depends(api_key_header),
    db: AsyncSession = Depends(get_db),
):
    """
    FastAPI dependency: authenticate a merchant using x-api-key header.
    Returns the Merchant model instance if valid, or None.
    """
    if not api_key:
        return None

    prefix = api_key[:12]
    from app.models.merchant import Merchant
    result = await db.execute(
        select(Merchant).where(
            Merchant.api_key_prefix == prefix,
            Merchant.is_active == True  # noqa: E712
        )
    )
    merchant = result.scalar_one_or_none()
    if not merchant or not merchant.api_key_hash:
        return None

    try:
        if bcrypt.checkpw(api_key.encode("utf-8"), merchant.api_key_hash.encode("utf-8")):
            return merchant
    except Exception:
        pass

    return None
