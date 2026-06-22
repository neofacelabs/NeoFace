"""
NeoFace Users API
Endpoints:
- GET    /api/v1/users           — List all users (admin)
- GET    /api/v1/users/{user_id} — Get user profile
- PATCH  /api/v1/users/{user_id} — Update user profile (admin)
- DELETE /api/v1/users/{user_id} — Deactivate user (admin)
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import TokenData, get_current_user_token, require_admin
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserListResponse, UserResponse, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "",
    response_model=UserListResponse,
    summary="List all users (admin only)",
)
async def list_users(
    page: int = Query(default=1, ge=1, description="Page number"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    active_only: bool = Query(default=False, description="Filter to active users only"),
    token_data: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    """Return paginated list of all users. Admin role required."""
    user_repo = UserRepository(db)
    users, total = await user_repo.get_all(
        page=page, page_size=page_size, active_only=active_only
    )
    return UserListResponse(
        total=total,
        page=page,
        page_size=page_size,
        users=[UserResponse.model_validate(u) for u in users],
    )


@router.get(
    "/{user_id}",
    response_model=UserResponse,
    summary="Get user profile",
)
async def get_user(
    user_id: uuid.UUID,
    token_data: TokenData = Depends(get_current_user_token),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """
    Get a user's profile.
    Users can only view their own profile; admins can view any profile.
    """
    # Non-admin users can only access their own profile
    if token_data.role != "admin" and str(user_id) != token_data.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this profile",
        )

    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse.model_validate(user)


@router.patch(
    "/{user_id}",
    response_model=UserResponse,
    summary="Update user profile (admin only)",
)
async def update_user(
    user_id: uuid.UUID,
    schema: UserUpdate,
    token_data: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Partially update a user's profile fields. Admin role required."""
    user_repo = UserRepository(db)
    user = await user_repo.update(user_id, schema)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return UserResponse.model_validate(user)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Deactivate a user (admin only)",
)
async def deactivate_user(
    user_id: uuid.UUID,
    token_data: TokenData = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Soft-delete a user by setting is_active=False.
    Does not delete data — use for compliance/audit trail.
    """
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    await user_repo.deactivate(user_id)
    return {"message": f"User {user_id} deactivated successfully"}
