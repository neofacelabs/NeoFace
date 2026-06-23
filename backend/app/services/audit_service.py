"""
NeoFace AaaS — Audit Service
Thin wrapper around AuditEventRepository for emitting events
from any service layer and exporting CSV.
"""

from __future__ import annotations

import csv
import io
import uuid
from datetime import datetime
from typing import Any

from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.audit_event_repository import AuditEventRepository
from app.schemas.aaas import AuditEventResponse

# ── Canonical event type constants ─────────────────────────────────────────────
class AuditEventType:
    IDENTITY_ENROLLED   = "identity.enrolled"
    IDENTITY_VERIFIED   = "identity.verified"
    IDENTITY_DELETED    = "identity.deleted"
    VERIFICATION_PASSED = "verification.passed"
    VERIFICATION_FAILED = "verification.failed"
    LIVENESS_PASSED     = "liveness.passed"
    LIVENESS_FAILED     = "liveness.failed"
    API_KEY_CREATED     = "api_key.created"
    API_KEY_ROTATED     = "api_key.rotated"
    API_KEY_REVOKED     = "api_key.revoked"
    SETTINGS_CHANGED    = "settings.changed"
    WEBHOOK_CREATED     = "webhook.created"
    SESSION_CREATED     = "session.created"
    SESSION_FAILED      = "session.failed"


class AuditService:
    def __init__(self, db: AsyncSession) -> None:
        self.repo = AuditEventRepository(db)

    async def emit(
        self,
        org_id: uuid.UUID,
        event_type: str,
        app_id: uuid.UUID | None = None,
        actor_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        ip_address: str | None = None,
    ) -> None:
        """Fire-and-forget audit event. Call without awaiting in hot paths."""
        await self.repo.emit(
            org_id=org_id,
            event_type=event_type,
            app_id=app_id,
            actor_id=actor_id,
            entity_type=entity_type,
            entity_id=entity_id,
            metadata=metadata,
            ip_address=ip_address,
        )

    async def list(
        self,
        org_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
        app_id: uuid.UUID | None = None,
        event_type: str | None = None,
        actor_id: uuid.UUID | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> tuple[list[AuditEventResponse], int]:
        events, total = await self.repo.list_by_org(
            org_id,
            page=page,
            page_size=page_size,
            app_id=app_id,
            event_type=event_type,
            actor_id=actor_id,
            from_date=from_date,
            to_date=to_date,
        )
        return [AuditEventResponse.model_validate(e) for e in events], total

    async def export_csv(
        self,
        org_id: uuid.UUID,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> StreamingResponse:
        events = await self.repo.list_all_for_export(
            org_id, from_date=from_date, to_date=to_date
        )

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "id", "event_type", "entity_type", "entity_id",
            "actor_id", "application_id", "ip_address", "created_at"
        ])
        for e in events:
            writer.writerow([
                str(e.id),
                e.event_type,
                e.entity_type or "",
                e.entity_id or "",
                str(e.actor_id) if e.actor_id else "",
                str(e.application_id) if e.application_id else "",
                e.ip_address or "",
                e.created_at.isoformat(),
            ])

        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=audit_export_{org_id}.csv"
            },
        )
