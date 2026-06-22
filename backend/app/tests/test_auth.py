"""
NeoFace Authentication Tests
Tests for JWT auth, login, register, and protected endpoints.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient

from app.core.security import JWTHandler, PasswordHasher, TokenData
from app.tests.conftest import make_admin_token, make_user_token


class TestPasswordHasher:
    """Unit tests for bcrypt password hashing."""

    def test_hash_produces_different_results(self):
        """Same password produces different hashes (salt)."""
        hash1 = PasswordHasher.hash("password123")
        hash2 = PasswordHasher.hash("password123")
        assert hash1 != hash2

    def test_verify_correct_password(self):
        """Correct password verifies successfully."""
        plain = "MySecurePass123!"
        hashed = PasswordHasher.hash(plain)
        assert PasswordHasher.verify(plain, hashed) is True

    def test_verify_wrong_password(self):
        """Wrong password fails verification."""
        hashed = PasswordHasher.hash("correct-password")
        assert PasswordHasher.verify("wrong-password", hashed) is False

    def test_verify_empty_password_fails(self):
        """Empty password fails against any hash."""
        hashed = PasswordHasher.hash("some-password")
        assert PasswordHasher.verify("", hashed) is False

    def test_hash_minimum_length_works(self):
        """8-character password can be hashed."""
        hashed = PasswordHasher.hash("Pass123!")
        assert PasswordHasher.verify("Pass123!", hashed) is True


class TestJWTHandler:
    """Unit tests for JWT token creation and decoding."""

    def test_create_access_token(self):
        """Access token contains expected claims."""
        token = JWTHandler.create_access_token(
            user_id="test-id",
            email="test@test.com",
            role="user",
        )
        payload = JWTHandler.decode_token(token)

        assert payload["sub"] == "test-id"
        assert payload["email"] == "test@test.com"
        assert payload["role"] == "user"
        assert payload["type"] == "access"

    def test_create_refresh_token(self):
        """Refresh token has type=refresh and longer expiry."""
        token = JWTHandler.create_refresh_token(
            user_id="test-id",
            email="test@test.com",
        )
        payload = JWTHandler.decode_token(token)

        assert payload["type"] == "refresh"
        assert payload["sub"] == "test-id"

    def test_create_token_pair(self):
        """Token pair contains both access and refresh tokens."""
        pair = JWTHandler.create_token_pair(
            user_id="test-id",
            email="test@test.com",
            role="admin",
        )
        assert pair.access_token
        assert pair.refresh_token
        assert pair.token_type == "bearer"
        assert pair.expires_in > 0

    def test_decode_invalid_token_raises(self):
        """Decoding garbage raises HTTPException."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            JWTHandler.decode_token("this.is.not.a.jwt")

        assert exc_info.value.status_code == 401

    def test_decode_expired_token_raises(self):
        """Expired token raises HTTPException."""
        from fastapi import HTTPException
        from jose import jwt
        from app.core.config import settings

        expired_payload = {
            "sub": "test",
            "email": "test@test.com",
            "role": "user",
            "type": "access",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        expired_token = jwt.encode(
            expired_payload,
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM,
        )

        with pytest.raises(HTTPException) as exc_info:
            JWTHandler.decode_token(expired_token)

        assert exc_info.value.status_code == 401

    def test_admin_role_in_token(self):
        """Admin role is correctly encoded in token."""
        token = JWTHandler.create_access_token(
            user_id="admin-id",
            email="admin@test.com",
            role="admin",
        )
        payload = JWTHandler.decode_token(token)
        assert payload["role"] == "admin"


class TestAuthAPI:
    """Integration tests for auth API endpoints."""

    @pytest.mark.asyncio
    async def test_login_success(self, async_client: AsyncClient, test_user):
        """Test successful login returns JWT pair."""
        response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "TestPass123!",
                "grant_type": "password",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, async_client: AsyncClient, test_user):
        """Test login with wrong password returns 401."""
        response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": test_user.email,
                "password": "WrongPassword!",
                "grant_type": "password",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, async_client: AsyncClient):
        """Test login with unknown email returns 401."""
        response = await async_client.post(
            "/api/v1/auth/login",
            data={
                "username": "nobody@nowhere.com",
                "password": "SomePass123!",
                "grant_type": "password",
            },
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_register_success(self, async_client: AsyncClient):
        """Test new user registration."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "name": "New User",
                "email": f"newuser_{uuid.uuid4().hex[:8]}@test.com",
                "password": "NewPass123!",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert "email" in data
        assert "hashed_password" not in data  # Never expose password hash

    @pytest.mark.asyncio
    async def test_register_duplicate_email(self, async_client: AsyncClient, test_user):
        """Test that duplicate email registration returns 409."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "name": "Duplicate",
                "email": test_user.email,
                "password": "Pass123!X",
            },
        )
        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_me_endpoint_requires_auth(self, async_client: AsyncClient):
        """Test /me endpoint without token returns 401."""
        response = await async_client.get("/api/v1/auth/me")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_me_endpoint_returns_profile(
        self, async_client: AsyncClient, test_user
    ):
        """Test /me endpoint returns current user profile."""
        token = make_user_token(str(test_user.id), test_user.email)
        response = await async_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == test_user.email
        assert data["role"] == test_user.role

    @pytest.mark.asyncio
    async def test_weak_password_rejected(self, async_client: AsyncClient):
        """Test that weak passwords are rejected at validation."""
        response = await async_client.post(
            "/api/v1/auth/register",
            json={
                "name": "Weak Password User",
                "email": "weak@test.com",
                "password": "password",  # No uppercase, no digit
            },
        )
        assert response.status_code == 422
