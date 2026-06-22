"""Initial schema — all NeoFace tables

Revision ID: 001_initial_schema
Revises:
Create Date: 2024-01-01 00:00:00.000000

Creates the complete NeoFace database schema in one migration:
  - users
  - face_embeddings
  - auth_logs
  - enrollment_logs
  - verification_logs
  - audit_logs

All tables use UUID primary keys generated server-side by gen_random_uuid().
Timestamps are stored as TIMESTAMPTZ (timezone-aware) using NOW().

Prerequisites (already enabled in Supabase by default):
  - uuid-ossp   → gen_random_uuid()
  - pgcrypto    → cryptographic helpers

Run with:
    alembic upgrade 001_initial_schema
Roll back with:
    alembic downgrade base
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID

# ── Alembic revision identifiers ──────────────────────────────────────────────
revision: str = "001_initial_schema"
down_revision: str | None = None   # This is the base migration
branch_labels: str | None = None
depends_on: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# UPGRADE
# ─────────────────────────────────────────────────────────────────────────────

def upgrade() -> None:
    """Create all NeoFace tables with indexes and constraints."""

    # ── PostgreSQL extensions ──────────────────────────────────────────────────
    # Supabase enables these by default; the IF NOT EXISTS guard makes the
    # migration safe to re-run (e.g. in a fresh local Postgres instance).
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    # ─────────────────────────────────────────────────────────────────────────
    # 1. users
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        # Primary key — server-side UUID avoids client-supplied values
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="User unique identifier",
        ),
        # Identity
        sa.Column("name", sa.String(255), nullable=False, comment="Full display name"),
        sa.Column(
            "email",
            sa.String(320),
            nullable=False,
            unique=True,
            comment="Unique email address",
        ),
        sa.Column(
            "phone",
            sa.String(20),
            nullable=True,
            comment="Optional E.164 phone number",
        ),
        # Auth
        sa.Column(
            "hashed_password",
            sa.String(255),
            nullable=True,
            comment="bcrypt hashed password (null for biometric-only users)",
        ),
        sa.Column(
            "role",
            sa.String(20),
            nullable=False,
            server_default="user",
            comment="user | admin",
        ),
        # Status flags
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
            comment="Soft-delete / account suspension flag",
        ),
        sa.Column(
            "is_enrolled",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
            comment="True once face enrollment is complete",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            comment="Account creation timestamp",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            comment="Last profile update timestamp",
        ),
    )

    # Indexes on users
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_is_active", "users", ["is_active"])

    # ─────────────────────────────────────────────────────────────────────────
    # 2. face_embeddings
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "face_embeddings",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Embedding record unique identifier",
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            comment="Owner user reference",
        ),
        # The 512-dim ArcFace vector stored as a PostgreSQL float array.
        # For large-scale approximate nearest-neighbour search, consider
        # migrating this column to pgvector's VECTOR(512) type.
        sa.Column(
            "embedding_vector",
            ARRAY(sa.Float),
            nullable=False,
            comment="512-dimensional ArcFace face embedding (L2-normalised)",
        ),
        sa.Column(
            "embedding_version",
            sa.String(50),
            nullable=False,
            server_default="arcface_r100_v1",
            comment="Model version tag — used for re-enrollment on model upgrade",
        ),
        sa.Column(
            "embedding_dimension",
            sa.Integer,
            nullable=False,
            server_default="512",
            comment="Vector dimension (should always be 512 for ArcFace R100)",
        ),
        sa.Column(
            "quality_score",
            sa.Float,
            nullable=True,
            comment="Face image quality score at enrollment (0–100)",
        ),
        sa.Column(
            "source_image_path",
            sa.String(500),
            nullable=True,
            comment="Storage path of the source enrollment image",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            comment="Embedding creation timestamp",
        ),
    )

    op.create_index("ix_face_embeddings_user_id", "face_embeddings", ["user_id"])
    op.create_index(
        "ix_face_embeddings_version", "face_embeddings", ["embedding_version"]
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 3. auth_logs
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "auth_logs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Log entry unique identifier",
        ),
        # Nullable: failed attempts may not identify a user
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="Matched user (null if no match found)",
        ),
        sa.Column(
            "confidence_score",
            sa.Float,
            nullable=True,
            comment="Face similarity score vs. stored embedding (0.0–1.0)",
        ),
        sa.Column(
            "liveness_score",
            sa.Float,
            nullable=True,
            comment="Liveness detection score (0–100)",
        ),
        sa.Column(
            "authentication_result",
            sa.Boolean,
            nullable=False,
            comment="True if authentication succeeded",
        ),
        sa.Column(
            "failure_reason",
            sa.String(255),
            nullable=True,
            comment="Human-readable failure reason when authentication_result=false",
        ),
        sa.Column(
            "ip_address",
            sa.String(45),
            nullable=True,
            comment="IPv4 or IPv6 address of the requester",
        ),
        sa.Column(
            "user_agent",
            sa.String(512),
            nullable=True,
            comment="HTTP User-Agent header",
        ),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            comment="Event timestamp (server UTC)",
        ),
    )

    op.create_index("ix_auth_logs_user_id", "auth_logs", ["user_id"])
    op.create_index("ix_auth_logs_timestamp", "auth_logs", ["timestamp"])
    op.create_index(
        "ix_auth_logs_result", "auth_logs", ["authentication_result"]
    )

    # ─────────────────────────────────────────────────────────────────────────
    # 4. enrollment_logs
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "enrollment_logs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Enrollment log entry unique identifier",
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            comment="User being enrolled",
        ),
        sa.Column(
            "images_submitted",
            sa.Integer,
            nullable=False,
            server_default="0",
            comment="Number of images received in this enrollment request",
        ),
        sa.Column(
            "images_accepted",
            sa.Integer,
            nullable=False,
            server_default="0",
            comment="Images that passed face detection and quality checks",
        ),
        sa.Column(
            "avg_quality_score",
            sa.Float,
            nullable=True,
            comment="Mean quality score for accepted images (0–100)",
        ),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            server_default="failed",
            comment="Enrollment outcome: success | partial | failed",
        ),
        sa.Column(
            "error_message",
            sa.String(500),
            nullable=True,
            comment="Failure details when status != 'success'",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            comment="Enrollment attempt timestamp (server UTC)",
        ),
    )

    op.create_index("ix_enrollment_logs_user_id", "enrollment_logs", ["user_id"])
    op.create_index("ix_enrollment_logs_created_at", "enrollment_logs", ["created_at"])
    op.create_index("ix_enrollment_logs_status", "enrollment_logs", ["status"])

    # ─────────────────────────────────────────────────────────────────────────
    # 5. verification_logs
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "verification_logs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Verification log entry unique identifier",
        ),
        # Nullable: liveness check may run before identity is established
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="Associated user if identity was established; null for anonymous checks",
        ),
        sa.Column(
            "liveness_score",
            sa.Float,
            nullable=True,
            comment="Liveness detection score (0–100)",
        ),
        sa.Column(
            "anti_spoof_score",
            sa.Float,
            nullable=True,
            comment="Anti-spoofing confidence score (0–100)",
        ),
        sa.Column(
            "confidence_score",
            sa.Float,
            nullable=True,
            comment="Face-match confidence against stored embedding (0.0–1.0)",
        ),
        sa.Column(
            "result",
            sa.String(20),
            nullable=False,
            server_default="failed",
            comment="Verification result: passed | failed | uncertain",
        ),
        sa.Column(
            "method",
            sa.String(100),
            nullable=True,
            comment="Pipeline / model variant used, e.g. 'mediapipe_v1'",
        ),
        sa.Column(
            "ip_address",
            sa.String(45),
            nullable=True,
            comment="Requester IPv4 or IPv6 address",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            comment="Verification event timestamp (server UTC)",
        ),
    )

    op.create_index("ix_verification_logs_user_id", "verification_logs", ["user_id"])
    op.create_index("ix_verification_logs_created_at", "verification_logs", ["created_at"])
    op.create_index("ix_verification_logs_result", "verification_logs", ["result"])

    # ─────────────────────────────────────────────────────────────────────────
    # 6. audit_logs
    # ─────────────────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
            comment="Audit log entry unique identifier",
        ),
        # Nullable: system/automated actions have no human actor
        sa.Column(
            "actor_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            comment="User who performed the action; null for system actions",
        ),
        sa.Column(
            "action",
            sa.String(100),
            nullable=False,
            comment="Machine-readable action verb, e.g. 'user.create'",
        ),
        sa.Column(
            "resource_type",
            sa.String(100),
            nullable=True,
            comment="Entity/table name affected, e.g. 'users'",
        ),
        sa.Column(
            "resource_id",
            sa.String(255),
            nullable=True,
            comment="Identifier of the affected record (UUID as string)",
        ),
        # JSONB allows flexible, indexed storage of action-specific context
        sa.Column(
            "metadata",
            JSONB,
            nullable=True,
            comment="Action-specific context as JSONB (e.g. old/new field values)",
        ),
        sa.Column(
            "ip_address",
            sa.String(45),
            nullable=True,
            comment="Source IPv4 or IPv6 address of the request",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("NOW()"),
            comment="Audit event timestamp (server UTC)",
        ),
    )

    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_resource_type", "audit_logs", ["resource_type"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])
    # GIN index on metadata JSONB for fast key/value lookups
    op.create_index(
        "ix_audit_logs_metadata_gin",
        "audit_logs",
        ["metadata"],
        postgresql_using="gin",
    )


# ─────────────────────────────────────────────────────────────────────────────
# DOWNGRADE — drops tables in reverse dependency order
# ─────────────────────────────────────────────────────────────────────────────

def downgrade() -> None:
    """Drop all NeoFace tables in reverse foreign-key dependency order."""

    # Drop tables that reference users first
    op.drop_index("ix_audit_logs_metadata_gin", table_name="audit_logs")
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_resource_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_verification_logs_result", table_name="verification_logs")
    op.drop_index("ix_verification_logs_created_at", table_name="verification_logs")
    op.drop_index("ix_verification_logs_user_id", table_name="verification_logs")
    op.drop_table("verification_logs")

    op.drop_index("ix_enrollment_logs_status", table_name="enrollment_logs")
    op.drop_index("ix_enrollment_logs_created_at", table_name="enrollment_logs")
    op.drop_index("ix_enrollment_logs_user_id", table_name="enrollment_logs")
    op.drop_table("enrollment_logs")

    op.drop_index("ix_auth_logs_result", table_name="auth_logs")
    op.drop_index("ix_auth_logs_timestamp", table_name="auth_logs")
    op.drop_index("ix_auth_logs_user_id", table_name="auth_logs")
    op.drop_table("auth_logs")

    op.drop_index("ix_face_embeddings_version", table_name="face_embeddings")
    op.drop_index("ix_face_embeddings_user_id", table_name="face_embeddings")
    op.drop_table("face_embeddings")

    op.drop_index("ix_users_is_active", table_name="users")
    op.drop_index("ix_users_role", table_name="users")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
