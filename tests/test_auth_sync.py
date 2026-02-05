"""
============================================================================
FILE: test_auth_sync.py
LOCATION: tests/test_auth_sync.py
============================================================================

PURPOSE:
    Tests for user synchronization endpoints.

ROLE IN PROJECT:
    Ensures the Firebase Auth <-> Firestore sync flow works for first
    login, and admin-managed user lifecycle endpoints behave correctly.

KEY COMPONENTS:
    - TestUserSync: /api/auth/sync endpoint behavior
    - TestAdminUserCreation: /api/admin/users creation behavior
    - TestUserUpdate: /api/admin/users/{uid} update behavior
    - TestUserDeletion: /api/admin/users/{uid} delete behavior

DEPENDENCIES:
    - External: pytest, fastapi
    - Internal: api.auth_sync, api.auth, api.main, api.models

USAGE:
    Run with: pytest tests/test_auth_sync.py -v
============================================================================
"""

from unittest.mock import MagicMock, patch
import sys

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.main import app
from api.models import FirestoreUser


client = TestClient(app)

_auth_sync_module = sys.modules.get("auth_sync")
if _auth_sync_module is None:
    _auth_sync_module = sys.modules.get("api.auth_sync")
if _auth_sync_module is None:
    import api.auth_sync as _auth_sync_module
_sync_dependency = _auth_sync_module.get_current_auth_user

_auth_module = sys.modules.get("auth")
if _auth_module is None:
    from api.auth import require_admin as _require_admin_dependency
else:
    _require_admin_dependency = _auth_module.require_admin


@pytest.fixture(autouse=True)
def reset_dependency_overrides() -> None:
    """Ensure dependency overrides are reset between tests."""
    app.dependency_overrides = {}
    yield
    app.dependency_overrides = {}


def _admin_user() -> FirestoreUser:
    return FirestoreUser(
        uid="admin-1",
        email="admin@aura.edu",
        displayName="Admin User",
        role="admin",
        status="active",
    )


class TestUserSync:
    """Tests for /api/auth/sync endpoint."""

    def test_sync_new_user(self) -> None:
        """Test syncing a new user creates Firestore document."""
        mock_db = MagicMock()
        users_collection = mock_db.collection.return_value
        user_ref = users_collection.document.return_value
        user_doc = MagicMock()
        user_doc.exists = False
        user_ref.get.return_value = user_doc
        users_collection.limit.return_value.stream.return_value = []

        mock_auth_user = MagicMock()
        mock_auth_user.email = "newuser@aura.edu"
        mock_auth_user.display_name = "New User"
        mock_auth_user.custom_claims = {}

        mock_auth_client = MagicMock()
        mock_auth_client.get_user.return_value = mock_auth_user

        app.dependency_overrides[_sync_dependency] = (
            lambda: {"uid": "user-123"}
        )

        with patch.object(
            _auth_sync_module, "get_db", return_value=mock_db
        ), patch.object(
            _auth_sync_module, "get_auth", return_value=mock_auth_client
        ):
            response = client.post(
                "/api/auth/sync",
                json={"displayName": "New User"},
            )

        assert response.status_code == 200
        body = response.json()
        assert body["isNewUser"] is True
        assert body["user"]["role"] == "admin"
        user_ref.set.assert_called_once()

    def test_sync_existing_user(self) -> None:
        """Test syncing existing user returns existing data."""
        mock_db = MagicMock()
        users_collection = mock_db.collection.return_value
        user_ref = users_collection.document.return_value
        user_doc = MagicMock()
        user_doc.exists = True
        user_doc.to_dict.return_value = {
            "email": "existing@aura.edu",
            "displayName": "Existing User",
            "role": "student",
            "status": "active",
            "departmentId": "dept-1",
            "subjectIds": [],
            "createdAt": "2026-02-05T00:00:00",
            "updatedAt": "2026-02-05T00:00:00",
            "_v": 1,
        }
        user_ref.get.return_value = user_doc

        app.dependency_overrides[_sync_dependency] = (
            lambda: {"uid": "user-456"}
        )

        with patch.object(_auth_sync_module, "get_db", return_value=mock_db):
            response = client.post("/api/auth/sync")

        assert response.status_code == 200
        body = response.json()
        assert body["isNewUser"] is False
        assert body["user"]["email"] == "existing@aura.edu"

    def test_first_user_becomes_admin(self) -> None:
        """Test that first user gets admin role."""
        mock_db = MagicMock()
        users_collection = mock_db.collection.return_value
        user_ref = users_collection.document.return_value
        user_doc = MagicMock()
        user_doc.exists = False
        user_ref.get.return_value = user_doc
        users_collection.limit.return_value.stream.return_value = []

        mock_auth_user = MagicMock()
        mock_auth_user.email = "first@aura.edu"
        mock_auth_user.display_name = "First User"
        mock_auth_user.custom_claims = {}

        mock_auth_client = MagicMock()
        mock_auth_client.get_user.return_value = mock_auth_user

        app.dependency_overrides[_sync_dependency] = (
            lambda: {"uid": "first-user"}
        )

        with patch.object(
            _auth_sync_module, "get_db", return_value=mock_db
        ), patch.object(
            _auth_sync_module, "get_auth", return_value=mock_auth_client
        ):
            response = client.post("/api/auth/sync")

        assert response.status_code == 200
        assert response.json()["user"]["role"] == "admin"


class TestAdminUserCreation:
    """Tests for /api/admin/users endpoint."""

    def test_admin_can_create_user(self) -> None:
        """Test admin can create user in Firebase Auth and Firestore."""
        mock_db = MagicMock()
        users_collection = mock_db.collection.return_value
        user_ref = users_collection.document.return_value

        mock_auth_user = MagicMock()
        mock_auth_user.uid = "new-user-1"

        mock_auth_client = MagicMock()
        mock_auth_client.create_user.return_value = mock_auth_user
        mock_auth_client.set_custom_user_claims = MagicMock()

        app.dependency_overrides[_require_admin_dependency] = _admin_user

        with patch.object(
            _auth_sync_module, "get_db", return_value=mock_db
        ), patch.object(
            _auth_sync_module, "get_auth", return_value=mock_auth_client
        ):
            response = client.post(
                "/api/admin/users",
                json={
                    "email": "user@aura.edu",
                    "password": "Secure123",
                    "displayName": "New User",
                    "role": "admin",
                },
            )

        assert response.status_code == 200
        mock_auth_client.create_user.assert_called_once()
        mock_auth_client.set_custom_user_claims.assert_called_once_with(
            "new-user-1", {"role": "admin"}
        )
        user_ref.set.assert_called_once()

    def test_non_admin_cannot_create_user(self) -> None:
        """Test non-admin is forbidden from creating users."""
        def _deny_admin() -> FirestoreUser:
            raise HTTPException(status_code=403, detail="Admin access required")

        app.dependency_overrides[_require_admin_dependency] = _deny_admin

        response = client.post(
            "/api/admin/users",
            json={
                "email": "user@aura.edu",
                "password": "Secure123",
                "displayName": "New User",
                "role": "admin",
            },
        )

        assert response.status_code == 403

    def test_duplicate_email_rejected(self) -> None:
        """Test creating user with existing email returns 409."""
        class EmailAlreadyExistsError(Exception):
            pass

        mock_auth_client = MagicMock()
        mock_auth_client.EmailAlreadyExistsError = EmailAlreadyExistsError
        mock_auth_client.create_user.side_effect = (
            EmailAlreadyExistsError("dup")
        )

        app.dependency_overrides[_require_admin_dependency] = _admin_user

        with patch.object(
            _auth_sync_module, "get_db", return_value=MagicMock()
        ), patch.object(
            _auth_sync_module, "get_auth", return_value=mock_auth_client
        ):
            response = client.post(
                "/api/admin/users",
                json={
                    "email": "user@aura.edu",
                    "password": "Secure123",
                    "displayName": "New User",
                    "role": "admin",
                },
            )

        assert response.status_code == 409

    def test_staff_requires_subjects(self) -> None:
        """Test that staff role requires subjectIds."""
        app.dependency_overrides[_require_admin_dependency] = _admin_user

        response = client.post(
            "/api/admin/users",
            json={
                "email": "staff@aura.edu",
                "password": "Secure123",
                "displayName": "Staff User",
                "role": "staff",
                "subjectIds": [],
            },
        )

        assert response.status_code == 422


class TestUserUpdate:
    """Tests for user update endpoint."""

    def test_admin_can_update_user(self) -> None:
        """Test admin can update user metadata."""
        mock_db = MagicMock()
        users_collection = mock_db.collection.return_value
        user_ref = users_collection.document.return_value

        existing_doc = MagicMock()
        existing_doc.exists = True

        updated_doc = MagicMock()
        updated_doc.exists = True
        updated_doc.to_dict.return_value = {
            "email": "user@aura.edu",
            "displayName": "Updated User",
            "role": "student",
            "status": "active",
            "departmentId": "dept-1",
            "subjectIds": [],
            "createdAt": "2026-02-05T00:00:00",
            "updatedAt": "2026-02-05T01:00:00",
            "_v": 1,
        }

        user_ref.get.side_effect = [existing_doc, updated_doc]

        mock_auth_client = MagicMock()

        app.dependency_overrides[_require_admin_dependency] = _admin_user

        with patch.object(
            _auth_sync_module, "get_db", return_value=mock_db
        ), patch.object(
            _auth_sync_module, "get_auth", return_value=mock_auth_client
        ):
            response = client.put(
                "/api/admin/users/user-123",
                json={"displayName": "Updated User"},
            )

        assert response.status_code == 200
        assert response.json()["displayName"] == "Updated User"
        mock_auth_client.update_user.assert_called_once_with(
            "user-123", display_name="Updated User"
        )
        user_ref.update.assert_called_once()

    def test_update_syncs_auth_and_firestore(self) -> None:
        """Test that updates apply to both systems."""
        mock_db = MagicMock()
        users_collection = mock_db.collection.return_value
        user_ref = users_collection.document.return_value

        existing_doc = MagicMock()
        existing_doc.exists = True

        updated_doc = MagicMock()
        updated_doc.exists = True
        updated_doc.to_dict.return_value = {
            "email": "user@aura.edu",
            "displayName": "Synced User",
            "role": "staff",
            "status": "active",
            "departmentId": "dept-2",
            "subjectIds": ["subj-1"],
            "createdAt": "2026-02-05T00:00:00",
            "updatedAt": "2026-02-05T02:00:00",
            "_v": 1,
        }

        user_ref.get.side_effect = [existing_doc, updated_doc]

        mock_auth_client = MagicMock()

        app.dependency_overrides[_require_admin_dependency] = _admin_user

        with patch.object(
            _auth_sync_module, "get_db", return_value=mock_db
        ), patch.object(
            _auth_sync_module, "get_auth", return_value=mock_auth_client
        ):
            response = client.put(
                "/api/admin/users/user-999",
                json={"displayName": "Synced User"},
            )

        assert response.status_code == 200
        mock_auth_client.update_user.assert_called_once()
        user_ref.update.assert_called_once()


class TestUserDeletion:
    """Tests for user delete endpoint."""

    def test_admin_can_delete_user(self) -> None:
        """Test admin can delete user."""
        mock_db = MagicMock()
        users_collection = mock_db.collection.return_value
        user_ref = users_collection.document.return_value
        user_doc = MagicMock()
        user_doc.exists = True
        user_ref.get.return_value = user_doc

        mock_auth_client = MagicMock()

        app.dependency_overrides[_require_admin_dependency] = _admin_user

        with patch.object(
            _auth_sync_module, "get_db", return_value=mock_db
        ), patch.object(
            _auth_sync_module, "get_auth", return_value=mock_auth_client
        ):
            response = client.delete("/api/admin/users/user-123")

        assert response.status_code == 200
        mock_auth_client.delete_user.assert_called_once_with("user-123")
        user_ref.delete.assert_called_once()

    def test_self_deletion_prevented(self) -> None:
        """Test admin cannot delete own account."""
        def _self_admin() -> FirestoreUser:
            return FirestoreUser(
                uid="admin-self",
                email="admin@aura.edu",
                displayName="Admin User",
                role="admin",
                status="active",
            )

        app.dependency_overrides[_require_admin_dependency] = _self_admin

        response = client.delete("/api/admin/users/admin-self")

        assert response.status_code == 400

    def test_deletion_removes_from_both_systems(self) -> None:
        """Test that deletion removes from Auth and Firestore."""
        mock_db = MagicMock()
        users_collection = mock_db.collection.return_value
        user_ref = users_collection.document.return_value
        user_doc = MagicMock()
        user_doc.exists = True
        user_ref.get.return_value = user_doc

        mock_auth_client = MagicMock()

        app.dependency_overrides[_require_admin_dependency] = _admin_user

        with patch.object(
            _auth_sync_module, "get_db", return_value=mock_db
        ), patch.object(
            _auth_sync_module, "get_auth", return_value=mock_auth_client
        ):
            response = client.delete("/api/admin/users/user-321")

        assert response.status_code == 200
        mock_auth_client.delete_user.assert_called_once_with("user-321")
        user_ref.delete.assert_called_once()
