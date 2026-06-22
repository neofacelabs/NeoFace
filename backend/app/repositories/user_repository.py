"""
NeoFace User Repository
Data access layer for User model operations.
Follows Repository pattern — services call this, not SQLAlchemy directly.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate


class UserRepository:
    """
    Encapsulates all database operations for the User model.
    Injected into services via FastAPI dependency injection.
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    # ── Read ──────────────────────────────────────────────────────────────────

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        """Fetch user by primary key."""
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Fetch user by email (case-insensitive)."""
        result = await self.db.execute(
            select(User).where(func.lower(User.email) == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_all(
        self,
        page: int = 1,
        page_size: int = 20,
        active_only: bool = False,
    ) -> tuple[list[User], int]:
        """
        Paginated user list.
        Returns (users, total_count).
        """
        query = select(User)
        count_query = select(func.count(User.id))

        if active_only:
            query = query.where(User.is_active == True)  # noqa: E712
            count_query = count_query.where(User.is_active == True)  # noqa: E712

        # Total count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Paginated results
        offset = (page - 1) * page_size
        result = await self.db.execute(
            query.order_by(User.created_at.desc()).offset(offset).limit(page_size)
        )
        return list(result.scalars().all()), total

    async def exists_by_email(self, email: str) -> bool:
        """Check if an email is already registered."""
        result = await self.db.execute(
            select(func.count(User.id)).where(
                func.lower(User.email) == email.lower()
            )
        )
        return result.scalar_one() > 0

    # ── Write ─────────────────────────────────────────────────────────────────

    async def create(self, schema: UserCreate, hashed_password: str, role: str = "user") -> User:
        """Create a new user record."""
        user = User(
            name=schema.name,
            email=schema.email.lower(),
            phone=schema.phone,
            hashed_password=hashed_password,
            role=role,
        )
        self.db.add(user)
        await self.db.flush()  # Get the generated ID without committing
        await self.db.refresh(user)
        return user

    async def create_biometric_user(
        self,
        name: str,
        email: str,
        phone: str | None = None,
    ) -> User:
        """Create a biometric-only user (no password required)."""
        user = User(
            name=name,
            email=email.lower(),
            phone=phone,
            hashed_password=None,
            role="user",
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def update(self, user_id: uuid.UUID, schema: UserUpdate) -> User | None:
        """Partial update of user fields."""
        updates = schema.model_dump(exclude_none=True)
        if not updates:
            return await self.get_by_id(user_id)

        updates["updated_at"] = datetime.now(timezone.utc)

        await self.db.execute(
            update(User).where(User.id == user_id).values(**updates)
        )
        return await self.get_by_id(user_id)

    async def mark_enrolled(self, user_id: uuid.UUID) -> None:
        """Set is_enrolled=True after successful face enrollment."""
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_enrolled=True, updated_at=datetime.now(timezone.utc))
        )

    async def deactivate(self, user_id: uuid.UUID) -> None:
        """Soft-delete a user by setting is_active=False."""
        await self.db.execute(
            update(User)
            .where(User.id == user_id)
            .values(is_active=False, updated_at=datetime.now(timezone.utc))
        )

    # ── Analytics ─────────────────────────────────────────────────────────────

    async def count_total(self) -> int:
        result = await self.db.execute(select(func.count(User.id)))
        return result.scalar_one()

    async def count_enrolled(self) -> int:
        result = await self.db.execute(
            select(func.count(User.id)).where(User.is_enrolled == True)  # noqa: E712
        )
        return result.scalar_one()

    async def count_active(self) -> int:
        result = await self.db.execute(
            select(func.count(User.id)).where(User.is_active == True)  # noqa: E712
        )
        return result.scalar_one()
