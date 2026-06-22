"""Trust Engine tables — liveness, emotion, headpose, deepfake, behavior, device, risk, sessions, challenges

Revision ID: 0002_trust_engine
Revises: 0001
Create Date: 2026-06-15

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

# revision identifiers
revision = '0002_trust_engine'
down_revision = '975bd29973d9'  # Runs after add_payments_and_biometrics
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── liveness_logs ──────────────────────────────────────────────────────────
    op.create_table(
        "liveness_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("liveness_score", sa.Float, nullable=True),
        sa.Column("is_live", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("confidence", sa.Float, nullable=True),
        sa.Column("anti_spoof_score", sa.Float, nullable=True),
        sa.Column("attack_type", sa.String(50), nullable=True),
        sa.Column("check_type", sa.String(20), nullable=False, server_default="passive"),
        sa.Column("challenge_type", sa.String(100), nullable=True),
        sa.Column("challenge_completed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("method", sa.String(50), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("device_id", sa.String(255), nullable=True),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("extra", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_liveness_logs_user_id", "liveness_logs", ["user_id"])
    op.create_index("ix_liveness_logs_created_at", "liveness_logs", ["created_at"])

    # ── emotion_logs ───────────────────────────────────────────────────────────
    op.create_table(
        "emotion_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("emotion", sa.String(20), nullable=False),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("all_scores", JSONB, nullable=True),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_emotion_logs_user_id", "emotion_logs", ["user_id"])
    op.create_index("ix_emotion_logs_created_at", "emotion_logs", ["created_at"])

    # ── headpose_logs ──────────────────────────────────────────────────────────
    op.create_table(
        "headpose_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("pitch", sa.Float, nullable=True),
        sa.Column("roll", sa.Float, nullable=True),
        sa.Column("yaw", sa.Float, nullable=True),
        sa.Column("is_frontal", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_headpose_logs_user_id", "headpose_logs", ["user_id"])
    op.create_index("ix_headpose_logs_created_at", "headpose_logs", ["created_at"])

    # ── deepfake_logs ──────────────────────────────────────────────────────────
    op.create_table(
        "deepfake_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("deepfake_probability", sa.Float, nullable=False),
        sa.Column("is_deepfake", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("model_used", sa.String(50), nullable=True),
        sa.Column("attack_category", sa.String(50), nullable=True),
        sa.Column("inference_ms", sa.Float, nullable=True),
        sa.Column("image_hash", sa.String(64), nullable=True),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("extra", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_deepfake_logs_user_id", "deepfake_logs", ["user_id"])
    op.create_index("ix_deepfake_logs_created_at", "deepfake_logs", ["created_at"])

    # ── behavior_profiles ──────────────────────────────────────────────────────
    op.create_table(
        "behavior_profiles",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("avg_mouse_speed", sa.Float, nullable=True),
        sa.Column("avg_mouse_curvature", sa.Float, nullable=True),
        sa.Column("avg_hesitation_rate", sa.Float, nullable=True),
        sa.Column("avg_typing_speed_wpm", sa.Float, nullable=True),
        sa.Column("avg_dwell_time_ms", sa.Float, nullable=True),
        sa.Column("avg_flight_time_ms", sa.Float, nullable=True),
        sa.Column("avg_swipe_velocity", sa.Float, nullable=True),
        sa.Column("avg_touch_pressure", sa.Float, nullable=True),
        sa.Column("avg_gesture_rhythm", sa.Float, nullable=True),
        sa.Column("total_events", sa.Integer, nullable=False, server_default="0"),
        sa.Column("profile_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("is_baseline_established", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("model_data", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_behavior_profiles_user_id", "behavior_profiles", ["user_id"])

    # ── behavior_events ────────────────────────────────────────────────────────
    op.create_table(
        "behavior_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("profile_id", UUID(as_uuid=True), sa.ForeignKey("behavior_profiles.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(30), nullable=False),
        sa.Column("metrics", JSONB, nullable=False),
        sa.Column("is_anomalous", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("anomaly_score", sa.Float, nullable=True),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_behavior_events_profile_id", "behavior_events", ["profile_id"])
    op.create_index("ix_behavior_events_user_id", "behavior_events", ["user_id"])
    op.create_index("ix_behavior_events_created_at", "behavior_events", ["created_at"])

    # ── device_trust_logs ──────────────────────────────────────────────────────
    op.create_table(
        "device_trust_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("device_id", sa.String(255), nullable=True),
        sa.Column("device_platform", sa.String(20), nullable=True),
        sa.Column("device_trust_score", sa.Integer, nullable=False),
        sa.Column("is_rooted", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_emulator", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_jailbroken", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_virtual_camera", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_headless_browser", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_automation_detected", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_usb_debugging", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("signals", JSONB, nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_device_trust_logs_user_id", "device_trust_logs", ["user_id"])
    op.create_index("ix_device_trust_logs_device_id", "device_trust_logs", ["device_id"])
    op.create_index("ix_device_trust_logs_created_at", "device_trust_logs", ["created_at"])

    # ── risk_scores ────────────────────────────────────────────────────────────
    op.create_table(
        "risk_scores",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("transaction_id", UUID(as_uuid=True), sa.ForeignKey("transactions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("face_score", sa.Float, nullable=True),
        sa.Column("liveness_score", sa.Float, nullable=True),
        sa.Column("deepfake_score", sa.Float, nullable=True),
        sa.Column("behavior_score", sa.Float, nullable=True),
        sa.Column("device_trust_score", sa.Float, nullable=True),
        sa.Column("location_trust_score", sa.Float, nullable=True),
        sa.Column("fingerprint_trust_score", sa.Float, nullable=True),
        sa.Column("final_trust_score", sa.Float, nullable=False),
        sa.Column("decision", sa.String(20), nullable=False),
        sa.Column("weights_snapshot", JSONB, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("device_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_risk_scores_user_id", "risk_scores", ["user_id"])
    op.create_index("ix_risk_scores_session_id", "risk_scores", ["session_id"])
    op.create_index("ix_risk_scores_transaction_id", "risk_scores", ["transaction_id"])
    op.create_index("ix_risk_scores_created_at", "risk_scores", ["created_at"])

    # ── continuous_sessions ────────────────────────────────────────────────────
    op.create_table(
        "continuous_sessions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_token", sa.String(255), nullable=False, unique=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("terminated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("termination_reason", sa.String(255), nullable=True),
        sa.Column("current_trust_score", sa.Float, nullable=False, server_default="100.0"),
        sa.Column("reauth_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("check_interval_seconds", sa.Integer, nullable=False, server_default="30"),
        sa.Column("device_id", sa.String(255), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_continuous_sessions_user_id", "continuous_sessions", ["user_id"])
    op.create_index("ix_continuous_sessions_session_token", "continuous_sessions", ["session_token"])

    # ── challenge_logs ─────────────────────────────────────────────────────────
    op.create_table(
        "challenge_logs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_id", sa.String(255), nullable=True),
        sa.Column("challenge_type", sa.String(200), nullable=False),
        sa.Column("challenge_steps", JSONB, nullable=True),
        sa.Column("is_completed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("is_passed", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("completion_time_ms", sa.Integer, nullable=True),
        sa.Column("failure_reason", sa.String(255), nullable=True),
        sa.Column("challenge_nonce", sa.String(64), nullable=True, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_challenge_logs_user_id", "challenge_logs", ["user_id"])
    op.create_index("ix_challenge_logs_session_id", "challenge_logs", ["session_id"])
    op.create_index("ix_challenge_logs_created_at", "challenge_logs", ["created_at"])


def downgrade() -> None:
    op.drop_table("challenge_logs")
    op.drop_table("continuous_sessions")
    op.drop_table("risk_scores")
    op.drop_table("device_trust_logs")
    op.drop_table("behavior_events")
    op.drop_table("behavior_profiles")
    op.drop_table("deepfake_logs")
    op.drop_table("headpose_logs")
    op.drop_table("emotion_logs")
    op.drop_table("liveness_logs")
