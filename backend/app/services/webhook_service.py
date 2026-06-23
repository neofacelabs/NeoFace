"""
NeoFace AaaS — Webhook Service
Handles endpoint registration, event dispatch, and delivery via Celery.
Payload signing uses HMAC-SHA256.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.webhook import WebhookDelivery, WebhookEndpoint
from app.schemas.aaas import WebhookCreate, WebhookDeliveryResponse, WebhookResponse

# Events supported by the webhook system
SUPPORTED_EVENTS = {
    "identity.enrolled",
    "identity.verified",
    "liveness.passed",
    "liveness.failed",
    "session.created",
    "session.failed",
    "api_key.created",
    "api_key.rotated",
}


def _generate_signing_secret() -> str:
    return secrets.token_hex(32)


def sign_payload(secret: str, payload: dict[str, Any]) -> str:
    """
    Generate HMAC-SHA256 signature for a webhook payload.
    Header: X-NeoFace-Signature: sha256=<hex>
    """
    body = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    sig = hmac.new(secret.encode("utf-8"), body, hashlib.sha256)
    return f"sha256={sig.hexdigest()}"


class WebhookService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create_endpoint(
        self, org_id: uuid.UUID, schema: WebhookCreate
    ) -> WebhookResponse:
        # Validate event types
        invalid = set(schema.events) - SUPPORTED_EVENTS
        if invalid:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Unsupported event types: {sorted(invalid)}. Supported: {sorted(SUPPORTED_EVENTS)}",
            )
        signing_secret = _generate_signing_secret()
        endpoint = WebhookEndpoint(
            organization_id=org_id,
            application_id=schema.application_id,
            url=str(schema.url),
            signing_secret=signing_secret,
            events=schema.events,
        )
        self.db.add(endpoint)
        await self.db.flush()
        await self.db.refresh(endpoint)
        return WebhookResponse.model_validate(endpoint)

    async def list_endpoints(
        self, org_id: uuid.UUID, page: int = 1, page_size: int = 50
    ) -> tuple[list[WebhookResponse], int]:
        q = select(WebhookEndpoint).where(
            WebhookEndpoint.organization_id == org_id,
            WebhookEndpoint.status != "disabled",
        )
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        q = q.order_by(WebhookEndpoint.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        endpoints = (await self.db.execute(q)).scalars().all()
        return [WebhookResponse.model_validate(e) for e in endpoints], total

    async def get_endpoint(
        self, endpoint_id: uuid.UUID, org_id: uuid.UUID
    ) -> WebhookEndpoint:
        result = await self.db.execute(
            select(WebhookEndpoint).where(
                WebhookEndpoint.id == endpoint_id,
                WebhookEndpoint.organization_id == org_id,
            )
        )
        endpoint = result.scalar_one_or_none()
        if not endpoint:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook endpoint not found")
        return endpoint

    async def send_test(
        self, endpoint_id: uuid.UUID, org_id: uuid.UUID
    ) -> dict:
        endpoint = await self.get_endpoint(endpoint_id, org_id)
        payload = {
            "event": "webhook.test",
            "org_id": str(org_id),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"message": "Test webhook from NeoFace Labs"},
        }
        # Create delivery record and dispatch Celery task
        delivery = WebhookDelivery(
            endpoint_id=endpoint.id,
            event_type="webhook.test",
            payload=payload,
            status="pending",
        )
        self.db.add(delivery)
        await self.db.flush()
        await self.db.refresh(delivery)

        # Dispatch Celery task
        try:
            from app.tasks.webhook_tasks import deliver_webhook
            deliver_webhook.delay(str(delivery.id))
        except Exception:
            pass  # Celery may not be running in dev; delivery logged as pending

        return {"queued": True, "delivery_id": str(delivery.id)}

    async def dispatch(
        self,
        org_id: uuid.UUID,
        event_type: str,
        payload: dict[str, Any],
    ) -> None:
        """
        Find all active endpoints subscribed to this event_type and enqueue deliveries.
        Called internally after auth events.
        """
        from sqlalchemy import text
        result = await self.db.execute(
            select(WebhookEndpoint).where(
                WebhookEndpoint.organization_id == org_id,
                WebhookEndpoint.status == "active",
                # JSONB @> operator: events list contains the event_type string
                WebhookEndpoint.events.contains([event_type]),
            )
        )
        endpoints = result.scalars().all()

        for endpoint in endpoints:
            delivery = WebhookDelivery(
                endpoint_id=endpoint.id,
                event_type=event_type,
                payload=payload,
                status="pending",
            )
            self.db.add(delivery)
            await self.db.flush()
            try:
                from app.tasks.webhook_tasks import deliver_webhook
                deliver_webhook.delay(str(delivery.id))
            except Exception:
                pass

    async def list_deliveries(
        self,
        endpoint_id: uuid.UUID,
        org_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[WebhookDeliveryResponse], int]:
        # Verify ownership
        await self.get_endpoint(endpoint_id, org_id)
        q = select(WebhookDelivery).where(WebhookDelivery.endpoint_id == endpoint_id)
        count_q = select(func.count()).select_from(q.subquery())
        total = (await self.db.execute(count_q)).scalar_one()
        q = q.order_by(WebhookDelivery.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        deliveries = (await self.db.execute(q)).scalars().all()
        return [WebhookDeliveryResponse.model_validate(d) for d in deliveries], total
