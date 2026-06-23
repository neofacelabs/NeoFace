"""
NeoFace AaaS — Sessions Router
GET /api/v1/sessions
GET /api/v1/sessions/{id}
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.api_key_auth import OrgContext, get_org_context
from app.schemas.aaas import PagedResponse, SessionResponse
from app.services.session_service import SessionService

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.get(
    "",
    response_model=PagedResponse[SessionResponse],
    summary="List authentication sessions",
)
async def list_sessions(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    application_id: uuid.UUID | None = Query(default=None),
    event_type: str | None = Query(default=None, description="enrollment|verification|liveness|authentication"),
    status: str | None = Query(default=None, description="success|failure|pending|challenge"),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> PagedResponse[SessionResponse]:
    svc = SessionService(db)
    sessions, total = await svc.list(
        ctx.org_id,
        page=page,
        page_size=page_size,
        app_id=application_id,
        event_type=event_type,
        status=status,
        from_date=from_date,
        to_date=to_date,
    )
    return PagedResponse(total=total, page=page, page_size=page_size, items=sessions)


@router.get(
    "/{session_id}",
    response_model=SessionResponse,
    summary="Get a single authentication session",
)
async def get_session(
    session_id: uuid.UUID,
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> SessionResponse:
    svc = SessionService(db)
    return await svc.get(session_id, ctx.org_id)
