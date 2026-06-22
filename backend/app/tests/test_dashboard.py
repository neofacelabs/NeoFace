"""
NeoFace Dashboard Tests
Tests for admin dashboard API endpoints.
"""

import pytest
from httpx import AsyncClient

from app.tests.conftest import make_admin_token, make_user_token


class TestDashboardAPI:
    """Integration tests for dashboard endpoints (admin only)."""

    @pytest.mark.asyncio
    async def test_dashboard_users_requires_admin(
        self, async_client: AsyncClient, test_user
    ):
        """Regular users cannot access dashboard endpoints."""
        token = make_user_token(str(test_user.id), test_user.email)
        response = await async_client.get(
            "/api/v1/dashboard/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_dashboard_users_success(
        self, async_client: AsyncClient, test_admin
    ):
        """Admin can access dashboard user stats."""
        token = make_admin_token(str(test_admin.id), test_admin.email)
        response = await async_client.get(
            "/api/v1/dashboard/users",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_users" in data
        assert "enrolled_users" in data
        assert "active_users" in data
        assert "enrollment_rate" in data

    @pytest.mark.asyncio
    async def test_dashboard_verifications(
        self, async_client: AsyncClient, test_admin
    ):
        """Admin can access verification stats."""
        token = make_admin_token(str(test_admin.id), test_admin.email)
        response = await async_client.get(
            "/api/v1/dashboard/verifications",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total_verifications" in data
        assert "successful_verifications" in data
        assert "success_rate" in data

    @pytest.mark.asyncio
    async def test_dashboard_success_rate(
        self, async_client: AsyncClient, test_admin
    ):
        """Success rate endpoint returns percentage."""
        token = make_admin_token(str(test_admin.id), test_admin.email)
        response = await async_client.get(
            "/api/v1/dashboard/success-rate",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "success_rate" in data
        assert 0.0 <= data["success_rate"] <= 100.0

    @pytest.mark.asyncio
    async def test_dashboard_logs(
        self, async_client: AsyncClient, test_admin
    ):
        """Admin can retrieve recent auth logs."""
        token = make_admin_token(str(test_admin.id), test_admin.email)
        response = await async_client.get(
            "/api/v1/dashboard/logs",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "logs" in data
        assert isinstance(data["logs"], list)

    @pytest.mark.asyncio
    async def test_dashboard_analytics(
        self, async_client: AsyncClient, test_admin
    ):
        """Analytics endpoint returns time-series data."""
        token = make_admin_token(str(test_admin.id), test_admin.email)
        response = await async_client.get(
            "/api/v1/dashboard/analytics?days=7",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "period_days" in data
        assert data["period_days"] == 7
        assert "daily_stats" in data

    @pytest.mark.asyncio
    async def test_health_check_public(self, async_client: AsyncClient):
        """Health endpoint is accessible without authentication."""
        response = await async_client.get("/api/v1/dashboard/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]

    @pytest.mark.asyncio
    async def test_logs_pagination(
        self, async_client: AsyncClient, test_admin
    ):
        """Logs endpoint supports pagination parameters."""
        token = make_admin_token(str(test_admin.id), test_admin.email)
        response = await async_client.get(
            "/api/v1/dashboard/logs?page=1&page_size=5",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["page"] == 1
        assert data["page_size"] == 5

    @pytest.mark.asyncio
    async def test_dashboard_no_token_returns_401(self, async_client: AsyncClient):
        """Dashboard without auth returns 401."""
        response = await async_client.get("/api/v1/dashboard/users")
        assert response.status_code == 401
