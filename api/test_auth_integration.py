"""
============================================================================
FILE: test_auth_integration.py
LOCATION: api/test_auth_integration.py
============================================================================

PURPOSE:
    Integration tests for authentication endpoints.

ROLE IN PROJECT:
    Validates end-to-end mock authentication flows for backend routes
    used by the frontend login and role-based protections.

KEY COMPONENTS:
    - client fixture: Configures test environment and TestClient
    - TestLoginEndpoint: Login success and failure scenarios
    - TestAuthMeEndpoint: Authenticated and unauthenticated /me checks
    - TestRoleProtection: Admin-only access enforcement

DEPENDENCIES:
    - External: pytest, fastapi
    - Internal: api.main

USAGE:
    pytest api/test_auth_integration.py -v
============================================================================
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with mock database."""
    import os

    os.environ["USE_REAL_FIREBASE"] = "false"
    os.environ["AURA_TEST_MODE"] = "true"

    from api.main import app

    return TestClient(app)


class TestLoginEndpoint:
    """Tests for /api/auth/login endpoint."""

    def test_login_success_admin(self, client):
        """Admin can login with correct credentials."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "Admin123!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert "token" in data
        assert data["user"]["role"] == "admin"
        assert data["token"].startswith("mock-token-admin-")

    def test_login_success_staff(self, client):
        """Staff can login with correct credentials."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "staff@test.com",
                "password": "Staff123!",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["user"]["role"] == "staff"
        assert data["user"]["departmentId"] is not None

    def test_login_invalid_password(self, client):
        """Invalid password returns 401."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "wrongpassword",
            },
        )
        assert response.status_code == 401

    def test_login_invalid_email(self, client):
        """Non-existent email returns 401."""
        response = client.post(
            "/api/auth/login",
            json={
                "email": "nobody@test.com",
                "password": "password",
            },
        )
        assert response.status_code == 401


class TestAuthMeEndpoint:
    """Tests for /api/auth/me endpoint."""

    def test_get_me_authenticated(self, client):
        """Authenticated user can get their profile."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "Admin123!",
            },
        )
        token = login_response.json()["token"]

        response = client.get(
            "/api/auth/me",
            headers={
                "Authorization": f"Bearer {token}",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "admin@test.com"
        assert data["role"] == "admin"

    def test_get_me_unauthenticated(self, client):
        """Unauthenticated request returns 401."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401


class TestRoleProtection:
    """Tests for role-based endpoint protection."""

    def test_admin_endpoint_with_admin(self, client):
        """Admin can access admin-only endpoints."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "admin@test.com",
                "password": "Admin123!",
            },
        )
        token = login_response.json()["token"]

        response = client.get(
            "/api/users",
            headers={
                "Authorization": f"Bearer {token}",
            },
        )
        assert response.status_code == 200

    def test_admin_endpoint_with_staff(self, client):
        """Staff cannot access admin-only endpoints."""
        login_response = client.post(
            "/api/auth/login",
            json={
                "email": "staff@test.com",
                "password": "Staff123!",
            },
        )
        token = login_response.json()["token"]

        response = client.get(
            "/api/users",
            headers={
                "Authorization": f"Bearer {token}",
            },
        )
        assert response.status_code == 403
