"""
============================================================================
FILE: test_auth_integration.py
LOCATION: tests/test_auth_integration.py
============================================================================

PURPOSE:
    Integration tests for Firebase authentication

ROLE IN PROJECT:
    Verifies that token verification, user lookup, and RBAC helpers behave
    correctly with mock and real-mode switching.

KEY COMPONENTS:
    - TestTokenVerification: Mock token verification behavior
    - TestGetCurrentUser: Firestore lookup and status validation
    - TestRoleBasedAccess: Role-based dependencies enforcement
    - TestPermissionHelpers: Granular permission helper behavior

DEPENDENCIES:
    - External: pytest, fastapi
    - Internal: api.auth, api.models

USAGE:
    Run with: pytest tests/test_auth_integration.py -v
============================================================================
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from api.auth import (
    get_current_user,
    has_department_access,
    has_subject_access,
    require_admin,
    require_staff,
    verify_firebase_token,
)
from api.models import FirestoreUser


class TestTokenVerification:
    """Tests for token verification logic."""

    @pytest.mark.asyncio
    async def test_verify_mock_token_success(self) -> None:
        """Test that mock tokens still work when USE_REAL_FIREBASE=false."""
        with patch.dict("os.environ", {"USE_REAL_FIREBASE": "false"}):
            token = "mock-token-admin"
            result = await verify_firebase_token(token)

            assert result["uid"] == "mock-admin-user"
            assert result["email"] == "admin@aura.edu"
            assert result["role"] == "admin"

    @pytest.mark.asyncio
    async def test_verify_mock_token_invalid(self) -> None:
        """Test that invalid mock tokens are rejected."""
        with patch.dict("os.environ", {"USE_REAL_FIREBASE": "false"}):
            with pytest.raises(HTTPException) as exc_info:
                await verify_firebase_token("invalid-token")

            assert exc_info.value.status_code == 401


class TestGetCurrentUser:
    """Tests for user lookup and validation."""

    @pytest.mark.asyncio
    async def test_get_current_user_success(self) -> None:
        """Test successful user lookup."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="mock-token-admin",
        )
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "email": "test@aura.edu",
            "displayName": "Test User",
            "role": "student",
            "status": "active",
            "departmentId": "dept-1",
            "subjectIds": [],
        }
        mock_db = MagicMock()
        collection = mock_db.collection.return_value
        document = collection.document.return_value
        document.get.return_value = mock_doc

        with patch("api.auth.get_db", return_value=mock_db), patch(
            "api.auth.verify_firebase_token",
            new=AsyncMock(return_value={"uid": "user-123"}),
        ):
            user = await get_current_user(credentials)

        assert user.uid == "user-123"
        assert user.role == "student"
        assert user.departmentId == "dept-1"

    @pytest.mark.asyncio
    async def test_disabled_user_rejected(self) -> None:
        """Test that disabled users cannot access."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="mock-token-admin",
        )
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "email": "disabled@aura.edu",
            "role": "student",
            "status": "disabled",
            "departmentId": "dept-1",
            "subjectIds": [],
        }
        mock_db = MagicMock()
        collection = mock_db.collection.return_value
        document = collection.document.return_value
        document.get.return_value = mock_doc

        with patch("api.auth.get_db", return_value=mock_db), patch(
            "api.auth.verify_firebase_token",
            new=AsyncMock(return_value={"uid": "user-456"}),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_user_not_found(self) -> None:
        """Test that missing users return 401."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="mock-token-admin",
        )
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db = MagicMock()
        collection = mock_db.collection.return_value
        document = collection.document.return_value
        document.get.return_value = mock_doc

        with patch("api.auth.get_db", return_value=mock_db), patch(
            "api.auth.verify_firebase_token",
            new=AsyncMock(return_value={"uid": "missing-user"}),
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials)

        assert exc_info.value.status_code == 401


class TestRoleBasedAccess:
    """Tests for role-based dependencies."""

    @pytest.mark.asyncio
    async def test_require_admin_allows_admin(self) -> None:
        """Test that admin can access admin-only routes."""
        admin_user = FirestoreUser(
            uid="admin-1",
            email="admin@aura.edu",
            displayName="Admin User",
            role="admin",
            status="active",
        )

        result = await require_admin(admin_user)
        assert result == admin_user

    @pytest.mark.asyncio
    async def test_require_admin_rejects_non_admin(self) -> None:
        """Test that non-admin is rejected from admin routes."""
        student_user = FirestoreUser(
            uid="student-1",
            email="student@aura.edu",
            displayName="Student User",
            role="student",
            status="active",
            departmentId="dept-cs",
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_admin(student_user)

        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_staff_allows_staff(self) -> None:
        """Test that staff can access staff-only routes."""
        staff_user = FirestoreUser(
            uid="staff-1",
            email="staff@aura.edu",
            displayName="Staff User",
            role="staff",
            status="active",
            subjectIds=["sub-1"],
            departmentId="dept-cs",
        )

        result = await require_staff(staff_user)
        assert result == staff_user


class TestPermissionHelpers:
    """Tests for permission helper functions."""

    def test_has_subject_access_admin(self) -> None:
        """Test admin has access to all subjects."""
        admin = FirestoreUser(
            uid="admin-1",
            email="admin@aura.edu",
            displayName="Admin User",
            role="admin",
            status="active",
        )

        assert has_subject_access(admin, "any-subject") is True

    def test_has_subject_access_staff(self) -> None:
        """Test staff only has access to assigned subjects."""
        staff = FirestoreUser(
            uid="staff-1",
            email="staff@aura.edu",
            displayName="Staff User",
            role="staff",
            status="active",
            subjectIds=["sub-1", "sub-2"],
            departmentId="dept-cs",
        )

        assert has_subject_access(staff, "sub-1") is True
        assert has_subject_access(staff, "sub-2") is True
        assert has_subject_access(staff, "sub-3") is False

    def test_has_department_access(self) -> None:
        """Test department access check."""
        student = FirestoreUser(
            uid="student-1",
            email="student@aura.edu",
            displayName="Student User",
            role="student",
            status="active",
            departmentId="dept-cs",
        )

        assert has_department_access(student, "dept-cs") is True
        assert has_department_access(student, "dept-math") is False
