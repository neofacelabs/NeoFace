"""
NeoFace AaaS — API Key Auth Middleware
Resolves org/app context from either:
  1. x-api-key header  (machine-to-machine)
  2. JWT Bearer token  (dashboard users)

Returns an OrgContext dataclass that routes can use.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import APIKeyHeader, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import JWTHandler, TokenData, get_current_user_token

# ── Scheme definitions ─────────────────────────────────────────────────────────
_api_key_scheme = APIKeyHeader(name="x-api-key", auto_error=False)
_oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


@dataclass
class OrgContext:
    """
    Resolved tenant context attached to each request.
    Populated from either API key or JWT token.
    """
    org_id: uuid.UUID
    app_id: uuid.UUID | None = None
    scopes: list[str] = field(default_factory=list)
    # JWT-authenticated dashboard users get their user_id here
    user_id: uuid.UUID | None = None
    auth_method: str = "jwt"  # "api_key" | "jwt"


async def get_org_context(
    request: Request,
    api_key: str | None = Depends(_api_key_scheme),
    token: str | None = Depends(_oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> OrgContext:
    """
    FastAPI dependency — resolves OrgContext from request credentials.

    Priority:
      1. x-api-key header → resolve org/app from key ownership
      2. Bearer JWT       → resolve org from user membership
    """

    # ── Branch 1: API Key ─────────────────────────────────────────────────────
    if api_key:
        return await _resolve_api_key(api_key, db)

    # ── Branch 2: JWT Bearer ──────────────────────────────────────────────────
    if token:
        return await _resolve_jwt(token, db)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Provide x-api-key or Bearer token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def _resolve_api_key(api_key: str, db: AsyncSession) -> OrgContext:
    """Validate API key via prefix lookup + bcrypt verify."""
    from app.repositories.api_key_repository import ApiKeyRepository

    if len(api_key) < 12:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key format")

    prefix = api_key[:12]
    repo = ApiKeyRepository(db)
    key_record = await repo.find_by_prefix(prefix)

    if not key_record:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    try:
        valid = bcrypt.checkpw(
            api_key.encode("utf-8"),
            key_record.hashed_secret.encode("utf-8"),
        )
    except Exception:
        valid = False

    if not valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

    # Update last_used_at (fire-and-forget, no await needed in background)
    await repo.touch_last_used(key_record.id)

    return OrgContext(
        org_id=key_record.organization_id,
        app_id=key_record.application_id,
        scopes=key_record.scopes or [],
        auth_method="api_key",
    )


async def _resolve_jwt(token: str, db: AsyncSession) -> OrgContext:
    """Resolve org context from a JWT-authenticated dashboard user."""
    from app.repositories.organization_repository import OrganizationRepository

    try:
        payload = JWTHandler.decode_token(token)
        if payload.get("type") != "access":
            raise ValueError("wrong token type")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = uuid.UUID(payload["sub"])
    role = payload.get("role", "user")

    org_repo = OrganizationRepository(db)

    # Admins get the default org context; they can pass ?org_id= on specific endpoints
    if role == "admin":
        default_org = await org_repo.get_default()
        if not default_org:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Default organization not seeded",
            )
        return OrgContext(
            org_id=default_org.id,
            user_id=user_id,
            scopes=["*"],
            auth_method="jwt",
        )

    # Regular users: look up their org membership
    org = await org_repo.get_user_org(user_id)
    if not org:
        # Auto-assign to default org
        default_org = await org_repo.get_default()
        if not default_org:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No organization membership found",
            )
        return OrgContext(
            org_id=default_org.id,
            user_id=user_id,
            scopes=["identity:read", "session:read"],
            auth_method="jwt",
        )

    return OrgContext(
        org_id=org.id,
        user_id=user_id,
        scopes=["identity:read", "identity:write", "session:read", "webhooks:manage"],
        auth_method="jwt",
    )


def require_scope(scope: str):
    """
    Dependency factory that checks a specific scope exists on the OrgContext.
    Usage:  Depends(require_scope("identity:write"))
    """
    async def _check(ctx: OrgContext = Depends(get_org_context)) -> OrgContext:
        if "*" not in ctx.scopes and scope not in ctx.scopes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing required scope: {scope}",
            )
        return ctx
    return _check
