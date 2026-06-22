"""
NeoFace User Schemas
Pydantic v2 models for request validation and response serialization.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserBase(BaseModel):
    """Shared fields across user schemas."""

    name: str = Field(..., min_length=2, max_length=255, examples=["Alice Johnson"])
    email: EmailStr = Field(..., examples=["alice@example.com"])
    phone: str | None = Field(
        default=None,
        pattern=r"^\+?[1-9]\d{1,14}$",
        examples=["+14155552671"],
    )


class UserCreate(UserBase):
    """Request body for creating a new user account."""

    password: str = Field(
        ...,
        min_length=8,
        max_length=128,
        examples=["StrongPass123!"],
    )

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserUpdate(BaseModel):
    """Request body for partial user profile updates."""

    name: str | None = Field(default=None, min_length=2, max_length=255)
    phone: str | None = Field(
        default=None,
        pattern=r"^\+?[1-9]\d{1,14}$",
    )
    is_active: bool | None = None


class UserResponse(UserBase):
    """Response body for user data (safe — no password)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: str
    is_active: bool
    is_enrolled: bool
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    """Paginated list of users."""

    total: int
    page: int
    page_size: int
    users: list[UserResponse]
