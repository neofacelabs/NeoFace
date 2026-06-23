"""AaaS multi-tenant tables

Revision ID: 0003_aaas_multitenant
Revises: 0002_trust_engine
Create Date: 2026-06-23

Creates all tables for the NeoFace AaaS layer:
  - organizations
  - applications
  - org_memberships
  - aaas_api_keys
  - identities
  - authentication_sessions
  - usage_records
  - audit_events
  - webhook_endpoints
  - webhook_deliveries
  - model_versions

Also seeds:
  - Default organization (slug='neoface-default')
  - Default application for the default org
"""

import uuid
from datetime import datetime, timezone

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision = '0003_aaas_multitenant'
down_revision = '0002_trust_engine'
branch_labels = None
depends_on = None

_DEFAULT_ORG_ID = str(uuid.UUID("00000000-0000-4000-a000-000000000001"))
_DEFAULT_APP_ID = str(uuid.UUID("00000000-0000-4000-a000-000000000002"))


def upgrade() -> None:
    # ── organizations ─────────────────────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(100), nullable=False, unique=True),
        sa.Column("plan", sa.String(50), nullable=False, server_default="free"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_organizations_slug", "organizations", ["slug"], unique=True)

    # ── applications ──────────────────────────────────────────────────────────
    op.create_table(
        "applications",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("environment", sa.String(50), nullable=False, server_default="production"),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_applications_organization_id", "applications", ["organization_id"])

    # ── org_memberships ───────────────────────────────────────────────────────
    op.create_table(
        "org_memberships",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(50), nullable=False, server_default="member"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint("organization_id", "user_id", name="uq_org_user"),
    )
    op.create_index("ix_org_memberships_organization_id", "org_memberships", ["organization_id"])
    op.create_index("ix_org_memberships_user_id", "org_memberships", ["user_id"])

    # ── aaas_api_keys ─────────────────────────────────────────────────────────
    op.create_table(
        "aaas_api_keys",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", UUID(as_uuid=True),
                  sa.ForeignKey("applications.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("key_prefix", sa.String(12), nullable=False),
        sa.Column("hashed_secret", sa.String(255), nullable=False),
        sa.Column("scopes", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_aaas_api_keys_organization_id", "aaas_api_keys", ["organization_id"])
    op.create_index("ix_aaas_api_keys_key_prefix", "aaas_api_keys", ["key_prefix"])

    # ── identities ────────────────────────────────────────────────────────────
    op.create_table(
        "identities",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", UUID(as_uuid=True),
                  sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("external_user_id", sa.String(255), nullable=False),
        sa.Column("enrollment_status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("face_embedding_id", UUID(as_uuid=True),
                  sa.ForeignKey("face_embeddings.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_identities_organization_id", "identities", ["organization_id"])
    op.create_index("ix_identities_application_id", "identities", ["application_id"])
    op.create_index("ix_identities_external_user_id", "identities", ["external_user_id"])

    # ── authentication_sessions ───────────────────────────────────────────────
    op.create_table(
        "authentication_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", UUID(as_uuid=True),
                  sa.ForeignKey("applications.id", ondelete="CASCADE"), nullable=False),
        sa.Column("identity_id", UUID(as_uuid=True),
                  sa.ForeignKey("identities.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(50), nullable=False),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("risk_score", sa.Float, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("device_fingerprint", sa.String(512), nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_auth_sessions_organization_id", "authentication_sessions", ["organization_id"])
    op.create_index("ix_auth_sessions_application_id", "authentication_sessions", ["application_id"])
    op.create_index("ix_auth_sessions_identity_id", "authentication_sessions", ["identity_id"])
    op.create_index("ix_auth_sessions_event_type", "authentication_sessions", ["event_type"])
    op.create_index("ix_auth_sessions_status", "authentication_sessions", ["status"])
    op.create_index("ix_auth_sessions_created_at", "authentication_sessions", ["created_at"])

    # ── usage_records ─────────────────────────────────────────────────────────
    op.create_table(
        "usage_records",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", UUID(as_uuid=True),
                  sa.ForeignKey("applications.id", ondelete="SET NULL"), nullable=True),
        sa.Column("endpoint", sa.String(100), nullable=False),
        sa.Column("bucket_date", sa.Date, nullable=False),
        sa.Column("request_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("success_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("failure_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("avg_latency_ms", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.UniqueConstraint(
            "organization_id", "application_id", "endpoint", "bucket_date",
            name="uq_usage_org_app_endpoint_date",
        ),
    )
    op.create_index("ix_usage_records_organization_id", "usage_records", ["organization_id"])
    op.create_index("ix_usage_records_bucket_date", "usage_records", ["bucket_date"])

    # ── audit_events ──────────────────────────────────────────────────────────
    op.create_table(
        "audit_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", UUID(as_uuid=True),
                  sa.ForeignKey("applications.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_id", UUID(as_uuid=True),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(100), nullable=True),
        sa.Column("entity_id", sa.String(255), nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_audit_events_organization_id", "audit_events", ["organization_id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])

    # ── webhook_endpoints ─────────────────────────────────────────────────────
    op.create_table(
        "webhook_endpoints",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("organization_id", UUID(as_uuid=True),
                  sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("application_id", UUID(as_uuid=True),
                  sa.ForeignKey("applications.id", ondelete="SET NULL"), nullable=True),
        sa.Column("url", sa.Text, nullable=False),
        sa.Column("signing_secret", sa.String(255), nullable=False),
        sa.Column("events", JSONB, nullable=False, server_default=sa.text("'[]'::jsonb")),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_webhook_endpoints_organization_id", "webhook_endpoints", ["organization_id"])

    # ── webhook_deliveries ────────────────────────────────────────────────────
    op.create_table(
        "webhook_deliveries",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("endpoint_id", UUID(as_uuid=True),
                  sa.ForeignKey("webhook_endpoints.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(100), nullable=False),
        sa.Column("payload", JSONB, nullable=False),
        sa.Column("status", sa.String(50), nullable=False, server_default="pending"),
        sa.Column("http_status", sa.Integer, nullable=True),
        sa.Column("attempts", sa.Integer, nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_webhook_deliveries_endpoint_id", "webhook_deliveries", ["endpoint_id"])
    op.create_index("ix_webhook_deliveries_created_at", "webhook_deliveries", ["created_at"])

    # ── model_versions ────────────────────────────────────────────────────────
    op.create_table(
        "model_versions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True,
                  server_default=sa.text("gen_random_uuid()")),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("version", sa.String(50), nullable=False),
        sa.Column("accuracy", sa.Float, nullable=True),
        sa.Column("far", sa.Float, nullable=True),
        sa.Column("frr", sa.Float, nullable=True),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("status", sa.String(50), nullable=False, server_default="active"),
        sa.Column("deployed_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text("now()")),
    )
    op.create_index("ix_model_versions_model_name", "model_versions", ["model_name"])

    # ── Seed: Default Organization + Application ──────────────────────────────
    now = datetime.now(timezone.utc).isoformat()
    op.execute(
        f"""
        INSERT INTO organizations (id, name, slug, plan, status, created_at, updated_at)
        VALUES (
            '{_DEFAULT_ORG_ID}',
            'NeoFace Default',
            'neoface-default',
            'enterprise',
            'active',
            NOW(),
            NOW()
        )
        ON CONFLICT (slug) DO NOTHING;
        """
    )
    op.execute(
        f"""
        INSERT INTO applications (id, organization_id, name, environment, status, description, created_at, updated_at)
        VALUES (
            '{_DEFAULT_APP_ID}',
            '{_DEFAULT_ORG_ID}',
            'NeoFace Platform',
            'production',
            'active',
            'Default application for the NeoFace Labs platform',
            NOW(),
            NOW()
        )
        ON CONFLICT DO NOTHING;
        """
    )

    # ── Seed: Assign existing admin user(s) to default org ───────────────────
    op.execute(
        f"""
        INSERT INTO org_memberships (id, organization_id, user_id, role, created_at)
        SELECT
            gen_random_uuid(),
            '{_DEFAULT_ORG_ID}',
            u.id,
            CASE WHEN u.role = 'admin' THEN 'owner' ELSE 'member' END,
            NOW()
        FROM users u
        WHERE NOT EXISTS (
            SELECT 1 FROM org_memberships om
            WHERE om.user_id = u.id AND om.organization_id = '{_DEFAULT_ORG_ID}'
        );
        """
    )


def downgrade() -> None:
    op.drop_table("webhook_deliveries")
    op.drop_table("webhook_endpoints")
    op.drop_table("audit_events")
    op.drop_table("usage_records")
    op.drop_table("authentication_sessions")
    op.drop_table("identities")
    op.drop_table("aaas_api_keys")
    op.drop_table("org_memberships")
    op.drop_table("applications")
    op.drop_table("model_versions")
    op.drop_table("organizations")
