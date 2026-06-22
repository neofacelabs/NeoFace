"""
NeoFace Dashboard API
Provides analytics and monitoring endpoints for the admin dashboard.

Endpoints:
- GET /api/v1/dashboard/users              — User stats
- GET /api/v1/dashboard/verifications      — Verification stats
- GET /api/v1/dashboard/success-rate       — Auth success rate
- GET /api/v1/dashboard/logs               — Recent auth logs
- GET /api/v1/dashboard/analytics          — Time-series analytics
- GET /api/v1/dashboard/payments/overview  — Real payment metrics
- GET /api/v1/dashboard/payments/daily     — Daily payment volume chart
- GET /api/v1/dashboard/payments/recent    — Live transaction feed
- GET /api/v1/dashboard/health             — System health check
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import check_db_health, get_db
from app.core.security import TokenData, require_admin
from app.repositories.auth_log_repository import AuthLogRepository
from app.repositories.user_repository import UserRepository
from app.schemas.verification import AuthLogListResponse, AuthLogResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/users",
    summary="User statistics",
    dependencies=[Depends(require_admin)],
)
async def get_user_stats(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns:
    - total_users: All registered users
    - enrolled_users: Users with face embeddings
    - active_users: Non-deactivated users
    - enrollment_rate: % of users who are enrolled
    """
    user_repo = UserRepository(db)
    total = await user_repo.count_total()
    enrolled = await user_repo.count_enrolled()
    active = await user_repo.count_active()

    return {
        "total_users": total,
        "enrolled_users": enrolled,
        "active_users": active,
        "enrollment_rate": round((enrolled / total * 100) if total > 0 else 0.0, 2),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/verifications",
    summary="Verification statistics",
    dependencies=[Depends(require_admin)],
)
async def get_verification_stats(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns:
    - total_verifications
    - successful_verifications
    - failed_verifications
    - success_rate (%)
    """
    log_repo = AuthLogRepository(db)
    total = await log_repo.count_total()
    successful = await log_repo.count_successful()

    return {
        "total_verifications": total,
        "successful_verifications": successful,
        "failed_verifications": total - successful,
        "success_rate": round((successful / total * 100) if total > 0 else 0.0, 2),
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/success-rate",
    summary="Authentication success rate",
    dependencies=[Depends(require_admin)],
)
async def get_success_rate(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Returns the overall authentication success percentage."""
    log_repo = AuthLogRepository(db)
    rate = await log_repo.get_success_rate()
    return {
        "success_rate": rate,
        "unit": "percent",
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/logs",
    response_model=AuthLogListResponse,
    summary="Recent authentication logs",
    dependencies=[Depends(require_admin)],
)
async def get_recent_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
) -> AuthLogListResponse:
    """
    Paginated list of recent authentication events.
    Sorted newest-first.
    """
    log_repo = AuthLogRepository(db)
    logs, total = await log_repo.get_recent(page=page, page_size=page_size)

    return AuthLogListResponse(
        total=total,
        page=page,
        page_size=page_size,
        logs=[AuthLogResponse.model_validate(log) for log in logs],
    )


@router.get(
    "/analytics",
    summary="Time-series analytics (enrollments/verifications per day)",
    dependencies=[Depends(require_admin)],
)
async def get_analytics(
    days: int = Query(default=7, ge=1, le=90, description="Number of days to include"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Returns daily verification counts for the last N days.
    Used to render the dashboard analytics chart.
    """
    log_repo = AuthLogRepository(db)
    daily_stats = await log_repo.get_daily_stats(days=days)

    return {
        "period_days": days,
        "daily_stats": daily_stats,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


# ── Payment Analytics ──────────────────────────────────────────────────────────

@router.get(
    "/payments/overview",
    summary="Payment transaction overview (admin)",
    dependencies=[Depends(require_admin)],
)
async def get_payment_overview(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Real financial metrics pulled from the transactions table:
    - total_transactions
    - authorized_transactions
    - failed_transactions
    - total_volume (USD)
    - authorization_rate (%)
    - modality_breakdown (per-biometric mode counts)
    """
    from app.repositories.transaction_repository import TransactionRepository
    txn_repo = TransactionRepository(db)

    total = await txn_repo.count_total()
    authorized = await txn_repo.count_authorized()
    volume = await txn_repo.get_total_volume(status="authorized")
    auth_rate = await txn_repo.get_authorization_rate()
    modality_breakdown = await txn_repo.get_modality_breakdown()

    return {
        "total_transactions": total,
        "authorized_transactions": authorized,
        "failed_transactions": total - authorized,
        "total_volume_usd": round(volume, 2),
        "authorization_rate": auth_rate,
        "modality_breakdown": modality_breakdown,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/payments/daily",
    summary="Daily payment volume time-series (admin)",
    dependencies=[Depends(require_admin)],
)
async def get_payment_daily_stats(
    days: int = Query(default=14, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Daily payment volume and transaction counts for the last N days.
    Replaces the previously hardcoded/mocked chart data.
    """
    from app.repositories.transaction_repository import TransactionRepository
    txn_repo = TransactionRepository(db)
    daily = await txn_repo.get_daily_stats(days=days)

    return {
        "period_days": days,
        "daily_stats": daily,
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/payments/recent",
    summary="Recent payment transactions live feed (admin)",
    dependencies=[Depends(require_admin)],
)
async def get_recent_payments(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Returns the most recent payment transactions for the live transaction feed."""
    from app.repositories.transaction_repository import TransactionRepository
    from app.schemas.payment import TransactionResponse
    txn_repo = TransactionRepository(db)
    transactions, total = await txn_repo.get_recent(page=page, page_size=page_size)

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "transactions": [TransactionResponse.model_validate(t) for t in transactions],
        "as_of": datetime.now(timezone.utc).isoformat(),
    }


@router.get(
    "/health",
    summary="System health check",
    include_in_schema=True,
)
async def health_check() -> dict:
    """
    Public health check endpoint.
    Used by Docker healthcheck, load balancers, and monitoring.
    """
    db_healthy = await check_db_health()

    return {
        "status": "healthy" if db_healthy else "degraded",
        "database": "ok" if db_healthy else "error",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
