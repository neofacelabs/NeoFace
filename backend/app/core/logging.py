"""
NeoFace Structured Logging
Uses Loguru for structured, leveled, and file-rotated logging.
All enrollment, verification, liveness, and exception events are captured.
"""

import sys
from pathlib import Path

from loguru import logger

from app.core.config import settings


def setup_logging() -> None:
    """
    Configure Loguru with:
    - Console handler (colorized in development)
    - Rotating file handler
    - Structured JSON output in production
    """
    # Remove default handler
    logger.remove()

    log_format_dev = (
        "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )

    log_format_prod = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )

    log_format = log_format_dev if not settings.is_production else log_format_prod

    # ── Console output ────────────────────────────────────────────────────────
    logger.add(
        sys.stdout,
        format=log_format,
        level=settings.LOG_LEVEL,
        colorize=not settings.is_production,
        backtrace=settings.DEBUG,
        diagnose=settings.DEBUG,
    )

    # ── File output ───────────────────────────────────────────────────────────
    log_path = Path(settings.LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        str(log_path),
        format=log_format_prod,
        level=settings.LOG_LEVEL,
        rotation="100 MB",
        retention="30 days",
        compression="gz",
        backtrace=True,
        diagnose=False,  # Never diagnose in files (may expose sensitive data)
        enqueue=True,    # Thread-safe async logging
    )

    logger.info(
        "Logging initialized",
        app=settings.APP_NAME,
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        level=settings.LOG_LEVEL,
    )


class EnrollmentLogger:
    """Structured logger for enrollment events."""

    @staticmethod
    def enrollment_started(user_email: str, image_count: int) -> None:
        logger.info(
            "Enrollment started",
            event="enrollment_started",
            user_email=user_email,
            image_count=image_count,
        )

    @staticmethod
    def enrollment_completed(user_id: str, confidence: float) -> None:
        logger.info(
            "Enrollment completed",
            event="enrollment_completed",
            user_id=user_id,
            confidence=confidence,
        )

    @staticmethod
    def enrollment_failed(user_email: str, reason: str) -> None:
        logger.warning(
            "Enrollment failed",
            event="enrollment_failed",
            user_email=user_email,
            reason=reason,
        )


class VerificationLogger:
    """Structured logger for verification events."""

    @staticmethod
    def verification_started(ip_address: str) -> None:
        logger.info(
            "Verification started",
            event="verification_started",
            ip_address=ip_address,
        )

    @staticmethod
    def verification_completed(
        user_id: str,
        authenticated: bool,
        confidence: float,
        liveness_score: float,
        ip_address: str,
    ) -> None:
        level = "info" if authenticated else "warning"
        getattr(logger, level)(
            "Verification completed",
            event="verification_completed",
            user_id=user_id,
            authenticated=authenticated,
            confidence_score=confidence,
            liveness_score=liveness_score,
            ip_address=ip_address,
        )

    @staticmethod
    def liveness_failed(ip_address: str, score: float) -> None:
        logger.warning(
            "Liveness check failed",
            event="liveness_failed",
            ip_address=ip_address,
            liveness_score=score,
        )

    @staticmethod
    def verification_failed(reason: str, ip_address: str) -> None:
        logger.warning(
            "Verification failed",
            event="verification_failed",
            reason=reason,
            ip_address=ip_address,
        )
