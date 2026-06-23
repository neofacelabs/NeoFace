"""
NeoFace AaaS — Celery Webhook Delivery Task
Delivers webhook payloads to customer endpoints with exponential backoff.

Retry policy:
  - Max 3 attempts
  - Backoff: 30s → 120s → 480s
  - On final failure: mark delivery as failed
"""

from __future__ import annotations

import json
from celery import Celery
from app.core.config import settings

# ── Celery app ────────────────────────────────────────────────────────────────
celery_app = Celery(
    "neoface_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=480,
)
def deliver_webhook(self, delivery_id: str) -> dict:
    """
    Deliver a single webhook payload to the registered endpoint.

    Uses synchronous httpx (Celery tasks are sync by default).
    Updates the WebhookDelivery record with the result.
    """
    import httpx
    from sqlalchemy.orm import Session
    from sqlalchemy import create_engine, select

    # Use synchronous DB for Celery task
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "+psycopg2")
    engine = create_engine(sync_url, pool_pre_ping=True)

    with Session(engine) as db:
        from app.models.webhook import WebhookDelivery, WebhookEndpoint
        import uuid

        delivery_uuid = uuid.UUID(delivery_id)
        delivery = db.get(WebhookDelivery, delivery_uuid)
        if not delivery:
            return {"error": "delivery not found"}

        endpoint = db.get(WebhookEndpoint, delivery.endpoint_id)
        if not endpoint or endpoint.status != "active":
            delivery.status = "failed"
            db.commit()
            return {"error": "endpoint inactive"}

        # Build payload with signature
        from app.services.webhook_service import sign_payload
        signature = sign_payload(endpoint.signing_secret, delivery.payload)

        try:
            delivery.attempts += 1
            resp = httpx.post(
                endpoint.url,
                json=delivery.payload,
                headers={
                    "Content-Type": "application/json",
                    "X-NeoFace-Signature": signature,
                    "X-NeoFace-Event": delivery.event_type,
                    "User-Agent": "NeoFace-Webhooks/1.0",
                },
                timeout=10.0,
            )
            delivery.http_status = resp.status_code
            if resp.status_code < 400:
                delivery.status = "success"
            else:
                delivery.status = "failed"
                raise Exception(f"HTTP {resp.status_code}")

        except Exception as exc:
            delivery.status = "retrying" if self.request.retries < self.max_retries else "failed"
            db.commit()
            raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))

        db.commit()
        return {"status": delivery.status, "http_status": delivery.http_status}
