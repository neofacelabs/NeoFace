"""
NeoFace AaaS — Pydantic v2 Schemas
All request/response models for the AaaS API layer.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

T = TypeVar("T")


# ── Pagination wrapper ────────────────────────────────────────────────────────

class PagedResponse(BaseModel, Generic[T]):
    """Generic paginated response envelope."""
    total: int
    page: int
    page_size: int
    items: list[T]


# ── Organization ──────────────────────────────────────────────────────────────

class OrganizationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=2, max_length=100, pattern=r"^[a-z0-9-]+$")
    plan: str = Field(default="free")


class OrganizationUpdate(BaseModel):
    name: str | None = None
    plan: str | None = None
    status: str | None = None


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    plan: str
    status: str
    created_at: datetime
    updated_at: datetime


class OrganizationDetail(OrganizationResponse):
    """Extended org view with aggregated stats."""
    application_count: int = 0
    identity_count: int = 0
    session_count_30d: int = 0
    api_call_count_30d: int = 0


# ── Application ───────────────────────────────────────────────────────────────

class ApplicationCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    environment: str = Field(default="production")
    description: str | None = None


class ApplicationUpdate(BaseModel):
    name: str | None = None
    environment: str | None = None
    status: str | None = None
    description: str | None = None


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    environment: str
    status: str
    description: str | None
    created_at: datetime
    updated_at: datetime


# ── API Key ───────────────────────────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    application_id: uuid.UUID | None = None
    scopes: list[str] = Field(
        default_factory=lambda: ["identity:read", "identity:write", "session:read"]
    )


class ApiKeyResponse(BaseModel):
    """Returned on list/get — NEVER includes the secret."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    application_id: uuid.UUID | None
    name: str
    key_prefix: str
    scopes: list[str]
    last_used_at: datetime | None
    status: str
    created_at: datetime


class ApiKeyCreatedResponse(ApiKeyResponse):
    """Returned ONLY at creation time — includes the full plaintext key (once!)."""
    plaintext_key: str


# ── Identity ──────────────────────────────────────────────────────────────────

class IdentityCreate(BaseModel):
    external_user_id: str = Field(..., min_length=1, max_length=255)
    application_id: uuid.UUID


class IdentityResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    application_id: uuid.UUID
    external_user_id: str
    enrollment_status: str
    face_embedding_id: uuid.UUID | None
    created_at: datetime
    updated_at: datetime


# ── Authentication Session ─────────────────────────────────────────────────────

class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    application_id: uuid.UUID
    identity_id: uuid.UUID | None
    event_type: str
    status: str
    confidence_score: float | None
    risk_score: float | None
    ip_address: str | None
    device_fingerprint: str | None
    latency_ms: int | None
    created_at: datetime


# ── Analytics ─────────────────────────────────────────────────────────────────

class UsageDayStat(BaseModel):
    date: date
    request_count: int
    success_count: int
    failure_count: int
    avg_latency_ms: float


class AnalyticsOverview(BaseModel):
    org_id: uuid.UUID
    period_days: int
    total_requests: int
    success_rate: float
    avg_latency_ms: float
    daily_active_identities: int
    monthly_active_identities: int
    as_of: datetime


class ApplicationUsage(BaseModel):
    application_id: uuid.UUID
    application_name: str
    request_count: int
    success_rate: float


# ── Audit Events ──────────────────────────────────────────────────────────────

class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    application_id: uuid.UUID | None
    actor_id: uuid.UUID | None
    event_type: str
    entity_type: str | None
    entity_id: str | None
    metadata_: dict[str, Any] | None = Field(None, alias="metadata_")
    ip_address: str | None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


# ── Webhook ───────────────────────────────────────────────────────────────────

class WebhookCreate(BaseModel):
    url: str = Field(..., description="HTTPS URL to deliver events to")
    events: list[str] = Field(
        default_factory=list,
        description="List of event types to subscribe to",
    )
    application_id: uuid.UUID | None = None


class WebhookResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    application_id: uuid.UUID | None
    url: str
    events: list[str]
    status: str
    created_at: datetime


class WebhookDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    endpoint_id: uuid.UUID
    event_type: str
    status: str
    http_status: int | None
    attempts: int
    next_retry_at: datetime | None
    created_at: datetime


# ── Admin: Global Metrics ─────────────────────────────────────────────────────

class GlobalMetricsResponse(BaseModel):
    organization_count: int
    application_count: int
    identity_count: int
    session_count: int
    api_calls_today: int
    avg_latency_ms: float
    threat_events_24h: int
    as_of: datetime


# ── Admin: Fraud ──────────────────────────────────────────────────────────────

class FraudOverviewResponse(BaseModel):
    spoof_attempts: int
    deepfake_detections: int
    replay_attacks: int
    high_risk_sessions: int
    total_threat_events_24h: int
    as_of: datetime


class FraudTimelinePoint(BaseModel):
    date: date
    spoof_attempts: int
    deepfake_detections: int
    high_risk_sessions: int


class FraudEventResponse(BaseModel):
    id: uuid.UUID
    event_type: str
    risk_score: float | None
    confidence: float | None
    ip_address: str | None
    created_at: datetime


# ── Admin: Model Monitoring ───────────────────────────────────────────────────

class ModelVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    model_name: str
    version: str
    accuracy: float | None
    far: float | None
    frr: float | None
    latency_ms: int | None
    status: str
    deployed_at: datetime


# ── Admin: Infrastructure ─────────────────────────────────────────────────────

class ServiceHealth(BaseModel):
    name: str
    status: str  # ok | degraded | error
    latency_ms: float | None = None
    detail: str | None = None


class InfraMetrics(BaseModel):
    cpu_percent: float
    memory_percent: float
    memory_used_gb: float
    memory_total_gb: float
    gpu_available: bool
    gpu_utilization: float | None
    queue_depth: int
    services: list[ServiceHealth]
    as_of: datetime
