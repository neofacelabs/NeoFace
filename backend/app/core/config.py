"""
NeoFace Core Configuration
Loads and validates all environment variables using Pydantic Settings v2.
Designed for flexible multi-environment deployment (dev, staging, production).
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central configuration class for NeoFace backend.
    All settings are loaded from environment variables with sensible defaults.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Application ──────────────────────────────────────────────────────────
    APP_NAME: str = "NeoFace"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"

    # ─── Server ───────────────────────────────────────────────────────────────
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # ─── Security / JWT ───────────────────────────────────────────────────────
    JWT_SECRET: str = Field(
        default="change-this-secret-in-production-min-32-chars",
        min_length=32,
    )
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ─── Firebase (Google Auth) ───────────────────────────────────────────────
    # Paste the FULL contents of your Firebase service account JSON as a string.
    # Leave empty to disable Google Auth verification (backend falls through gracefully).
    FIREBASE_CREDENTIALS_JSON: str = ""

    # ─── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str = (
        "postgresql+asyncpg://neoface:neoface_pass@localhost:5432/neoface_db"
    )
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20

    # ─── Redis ────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 300  # seconds

    # ─── Celery ───────────────────────────────────────────────────────────────
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ─── Face Recognition ─────────────────────────────────────────────────────
    SIMILARITY_THRESHOLD: float = 0.65
    LIVENESS_THRESHOLD: float = 60.0
    MAX_ENROLLMENT_IMAGES: int = 5
    MIN_ENROLLMENT_IMAGES: int = 1
    FACE_DETECTION_MODEL: str = "buffalo_l"
    EMBEDDING_DIMENSION: int = 512

    # ─── Image Quality ────────────────────────────────────────────────────────
    MIN_IMAGE_WIDTH: int = 112
    MIN_IMAGE_HEIGHT: int = 112
    MAX_IMAGE_SIZE_MB: float = 10.0
    BLUR_THRESHOLD: float = 10.0  # Laplacian variance threshold — lowered for live webcam tolerance
    DETECTION_THRESHOLD: float = 0.40  # InsightFace detection confidence threshold



    # ─── Supabase ─────────────────────────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_PROJECT_REF: str = "wrpxcyievqnniviarcln"
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""

    # Supabase Storage bucket names
    SUPABASE_BUCKET_FACE_IMAGES: str = "face-images"
    SUPABASE_BUCKET_VERIFICATION_IMAGES: str = "verification-images"
    SUPABASE_BUCKET_LOGS: str = "logs"

    # ─── Storage ──────────────────────────────────────────────────────────────
    STORAGE_BACKEND: Literal["local", "s3", "supabase"] = "local"
    LOCAL_STORAGE_PATH: str = "./storage/faces"
    AWS_S3_BUCKET: str = "neoface-faces"
    AWS_S3_REGION: str = "us-east-1"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""

    # ─── Rate Limiting ────────────────────────────────────────────────────────
    RATE_LIMIT_VERIFICATION: str = "10/minute"
    RATE_LIMIT_ENROLLMENT: str = "5/minute"

    # ─── Admin Bootstrap ──────────────────────────────────────────────────────
    ADMIN_EMAIL: str = "admin@neoface.io"
    ADMIN_PASSWORD: str = "AdminPass123!"
    ADMIN_NAME: str = "NeoFace Admin"

    # ─── Logging ──────────────────────────────────────────────────────────────
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    LOG_FILE: str = "./logs/neoface.log"

    # ─── Anti-Spoofing / Liveness Pipeline ───────────────────────────────────
    # Path to MiniFASNet ONNX model file.
    # Download instructions: see models/README.md
    ANTI_SPOOF_MODEL_PATH: str = "./models/anti_spoof.onnx"
    # Probability threshold above which a face is considered real (0–1)
    ANTI_SPOOF_THRESHOLD: float = 0.70
    # Set to False to disable anti-spoof check (e.g. in unit tests)
    ANTI_SPOOF_ENABLED: bool = True
    # Use the full multi-stage pipeline (True) or legacy single-stage (False)
    USE_LIVENESS_PIPELINE: bool = True
    STRICT_MODEL_VERIFICATION: bool = False  # Set True in production via env var

    # ─── Trust Engine v2 — Model Paths ────────────────────────────────────────
    # Passive Liveness: MiniFASNetV1 + V2 ensemble
    MINIFASNET_V1_PATH: str = "./models/MiniFASNetV1.onnx"
    MINIFASNET_V2_PATH: str = "./models/MiniFASNetV2.onnx"

    # Emotion Recognition: MobileNetV3
    EMOTION_MODEL_PATH: str = "./models/emotion_mobilenetv3.onnx"

    # Depth Estimation: MiDaS Small + DPT Hybrid
    MIDAS_SMALL_PATH: str = "./models/midas_small.onnx"
    DPT_HYBRID_PATH:  str = "./models/dpt_hybrid.onnx"

    # Deepfake Detection: EfficientNet-B4 + XceptionNet
    EFFICIENTNET_DEEPFAKE_PATH: str = "./models/efficientnet_b4_deepfake.onnx"
    XCEPTIONNET_DEEPFAKE_PATH:  str = "./models/xceptionnet_deepfake.onnx"

    # ─── Trust Engine v2 — Thresholds ─────────────────────────────────────────
    PASSIVE_LIVENESS_THRESHOLD: float = 0.65
    DEEPFAKE_THRESHOLD: float = 0.50
    RISK_APPROVE_THRESHOLD: float = 90.0
    RISK_STEP_UP_THRESHOLD: float = 70.0
    CONTINUOUS_AUTH_REAUTH_THRESHOLD: float = 70.0
    CONTINUOUS_AUTH_CHECK_INTERVAL: int = 30  # seconds

    # ─── CORS ─────────────────────────────────────────────────────────────────
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        # Production & Vercel deployments
        "https://neofacelabs.vercel.app",
        "https://neoface.vercel.app",
        "https://neoface-git-main-divyebhatnagar.vercel.app",
    ]
    # Additional origins can be added at runtime via this env var:
    # ALLOWED_ORIGINS='["https://custom-domain.com"]'

    @field_validator("SIMILARITY_THRESHOLD")
    @classmethod
    def validate_threshold(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("SIMILARITY_THRESHOLD must be between 0.0 and 1.0")
        return v

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def database_url_sync(self) -> str:
        """Synchronous database URL for Alembic migrations."""
        return self.DATABASE_URL.replace("+asyncpg", "+psycopg2")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Returns cached settings instance.
    Use dependency injection: Depends(get_settings)
    """
    return Settings()


# Module-level singleton for convenience imports
settings = get_settings()
