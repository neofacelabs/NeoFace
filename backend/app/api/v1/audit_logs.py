"""
NeoFace AaaS — Audit Logs Router
GET /api/v1/audit-logs
GET /api/v1/audit-logs/export  (CSV download)
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.api_key_auth import OrgContext, get_org_context
from app.schemas.aaas import AuditEventResponse, PagedResponse
from app.services.audit_service import AuditService

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get(
    "",
    response_model=PagedResponse[AuditEventResponse],
    summary="List audit events for your organization",
)
async def list_audit_events(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    application_id: uuid.UUID | None = Query(default=None),
    event_type: str | None = Query(default=None),
    actor_id: uuid.UUID | None = Query(default=None),
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> PagedResponse[AuditEventResponse]:
    svc = AuditService(db)
    events, total = await svc.list(
        ctx.org_id,
        page=page,
        page_size=page_size,
        app_id=application_id,
        event_type=event_type,
        actor_id=actor_id,
        from_date=from_date,
        to_date=to_date,
    )
    return PagedResponse(total=total, page=page, page_size=page_size, items=events)


@router.get(
    "/export",
    summary="Export audit events as CSV",
    response_class=StreamingResponse,
)
async def export_audit_events(
    from_date: datetime | None = Query(default=None),
    to_date: datetime | None = Query(default=None),
    ctx: OrgContext = Depends(get_org_context),
    db: AsyncSession = Depends(get_db),
) -> StreamingResponse:
    svc = AuditService(db)
    return await svc.export_csv(ctx.org_id, from_date=from_date, to_date=to_date)
