"""
============================================================================
FILE: test_rbac.py
LOCATION: api/tests/test_rbac.py
============================================================================

PURPOSE:
    Unit tests for RBAC helpers and authentication dependencies.

ROLE IN PROJECT:
    Validates mock token verification, user resolution, role enforcement,
    and permission helpers without real Firebase services.

KEY COMPONENTS:
    - verify_firebase_token: Mock and real-branch error mapping
    - get_current_user: Firestore lookup and role override behavior
    - Role dependencies and permission helpers

DEPENDENCIES:
    - External: pytest, fastapi, firebase_admin
    - Internal: api.auth, api.models

USAGE:
    pytest api/tests/test_rbac.py -v
============================================================================
"""

import typing

import fastapi
from fastapi.security import HTTPAuthorizationCredentials
import pytest

import api.auth as auth_module
import api.models as models


class FakeDocSnapshot:
    """Fake Firestore document snapshot."""

    def __init__(self, data: dict, exists: bool) -> None:
        """Initialize the snapshot.

        Args:
            data: Document data.
            exists: Whether the document exists.
        """
        self._data = data
        self.exists = exists

    def to_dict(self) -> dict:
        """Return the stored document data.

        Returns:
            dict: Stored document data.
        """
        return self._data


class FakeDocRef:
    """Fake Firestore document reference."""

    def __init__(self, data: dict, exists: bool) -> None:
        """Initialize the document reference.

        Args:
            data: Document data.
            exists: Whether the document exists.
        """
        self._data = data
        self._exists = exists

    def get(self) -> FakeDocSnapshot:
        """Return a fake document snapshot.

        Returns:
            FakeDocSnapshot: The document snapshot.
        """
        return FakeDocSnapshot(self._data, self._exists)


class FakeCollection:
    """Fake Firestore collection reference."""

    def __init__(self, docs_by_id: dict) -> None:
        """Initialize the collection.

        Args:
            docs_by_id: Mapping of uid to document data.
        """
        self._docs_by_id = docs_by_id

    def document(self, uid: str) -> FakeDocRef:
        """Return a fake document reference.

        Args:
            uid: Document id.

        Returns:
            FakeDocRef: The document reference.
        """
        exists = uid in self._docs_by_id
        data = self._docs_by_id.get(uid, {})
        return FakeDocRef(data, exists)


class FakeDb:
    """Fake Firestore database."""

    def __init__(self, docs_by_id: dict) -> None:
        """Initialize the database.

        Args:
            docs_by_id: Mapping of uid to document data.
        """
        self._docs_by_id = docs_by_id

    def collection(self, name: str) -> FakeCollection:
        """Return a fake collection.

        Args:
            name: Collection name.

        Returns:
            FakeCollection: The collection reference.
        """
        return FakeCollection(self._docs_by_id)


class FakeAuthClient:
    """Fake Firebase auth client."""

    def __init__(
        self,
        result: typing.Optional[dict],
        exc: typing.Optional[Exception] = None,
    ) -> None:
        """Initialize the client.

        Args:
            result: Decoded token claims to return.
            exc: Exception to raise if provided, or None for
                success.
        """
        self._result = result
        self._exc = exc

    def verify_id_token(self, token: str, clock_skew_seconds: int) -> dict:
        """Return decoded claims or raise an exception.

        Args:
            token: Firebase ID token.
            clock_skew_seconds: Clock skew allowance.

        Returns:
            dict: Decoded claims.
        """
        if self._exc:
            raise self._exc
        return typing.cast(dict, self._result)


def _make_credentials(token: str) -> HTTPAuthorizationCredentials:
    """Create HTTP authorization credentials.

    Args:
        token: Bearer token string.

    Returns:
        HTTPAuthorizationCredentials: Credentials object.
    """
    return HTTPAuthorizationCredentials(scheme='Bearer', credentials=token)


def _make_user(
    uid: str,
    role: models.UserRole,
    status: models.UserStatus = 'active',
    department_id: typing.Optional[str] = None,
    subject_ids: typing.Optional[list[str]] = None,
) -> models.FirestoreUser:
    """Build a FirestoreUser for tests.

    Args:
        uid: Firebase uid.
        role: User role.
        status: Account status.
        department_id: Department id.
        subject_ids: Subject ids.

    Returns:
        FirestoreUser: User model.
    """
    return models.FirestoreUser(
        uid=uid,
        email=f'{uid}@example.com',
        displayName='Test User',
        role=role,
        status=status,
        departmentId=department_id,
        subjectIds=subject_ids or [],
    )


def _set_real_firebase_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable real-branch token verification for tests.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.setenv('TESTING', 'false')
    monkeypatch.setenv('USE_REAL_FIREBASE', 'true')


def _set_mock_firebase_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Enable mock-branch token verification for tests.

    Args:
        monkeypatch: Pytest monkeypatch fixture.
    """
    monkeypatch.setenv('TESTING', 'true')
    monkeypatch.setenv('USE_REAL_FIREBASE', 'false')


@pytest.mark.asyncio
async def test_verify_firebase_token_mock_admin(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Mock admin token returns decoded claims."""
    _set_mock_firebase_env(monkeypatch)
    claims = await auth_module.verify_firebase_token('mock-token-admin-001')
    assert claims['uid'] == '001'
    assert claims['role'] == 'admin'
    assert claims['email'] == 'admin@aura.edu'


@pytest.mark.asyncio
async def test_verify_firebase_token_mock_role_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Role-only mock token uses fallback uid format."""
    _set_mock_firebase_env(monkeypatch)
    claims = await auth_module.verify_firebase_token('mock-token-staff')
    assert claims['uid'] == 'mock-staff-user'
    assert claims['role'] == 'staff'


@pytest.mark.asyncio
async def test_verify_firebase_token_mock_invalid_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Invalid mock token raises HTTP 401."""
    _set_mock_firebase_env(monkeypatch)
    with pytest.raises(fastapi.HTTPException) as exc:
        await auth_module.verify_firebase_token('invalid-token')
    assert exc.value.status_code == fastapi.status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == 'Invalid mock token'
    assert exc.value.headers is None


@pytest.mark.asyncio
async def test_verify_firebase_token_real_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real-branch verification returns decoded claims."""
    _set_real_firebase_env(monkeypatch)
    client = FakeAuthClient({'uid': 'user-1'}, None)
    monkeypatch.setattr(auth_module, 'get_auth', lambda: client)
    claims = await auth_module.verify_firebase_token('real-token')
    assert claims['uid'] == 'user-1'


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ('exc_name', 'detail_prefix'),
    [
        ('InvalidIdTokenError', 'Invalid authentication token:'),
        ('ExpiredIdTokenError', 'Authentication token has expired:'),
        ('RevokedIdTokenError', 'Authentication token has been revoked:'),
    ],
)
async def test_verify_firebase_token_real_error_mapping(
    monkeypatch: pytest.MonkeyPatch,
    exc_name: str,
    detail_prefix: str,
) -> None:
    """Real-branch errors map to HTTP 401 responses."""
    class FakeTokenError(Exception):
        """Fake token exception for auth mapping tests."""

    _set_real_firebase_env(monkeypatch)
    monkeypatch.setattr(auth_module.auth, exc_name, FakeTokenError)
    client = FakeAuthClient(None, FakeTokenError('bad-token'))
    monkeypatch.setattr(auth_module, 'get_auth', lambda: client)

    with pytest.raises(fastapi.HTTPException) as exc:
        await auth_module.verify_firebase_token('real-token')

    assert exc.value.status_code == fastapi.status.HTTP_401_UNAUTHORIZED
    assert detail_prefix in exc.value.detail
    assert exc.value.headers == {'WWW-Authenticate': 'Bearer'}


@pytest.mark.asyncio
async def test_verify_firebase_token_real_generic_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Unexpected errors map to generic HTTP 401 responses."""
    _set_real_firebase_env(monkeypatch)
    client = FakeAuthClient(None, Exception('boom'))
    monkeypatch.setattr(auth_module, 'get_auth', lambda: client)

    with pytest.raises(fastapi.HTTPException) as exc:
        await auth_module.verify_firebase_token('real-token')

    assert exc.value.status_code == fastapi.status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail.startswith('Authentication failed:')
    assert exc.value.headers == {'WWW-Authenticate': 'Bearer'}


@pytest.mark.asyncio
async def test_get_current_user_success_with_role_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Token role overrides Firestore role on success.

    Design note: When a user's role is changed by an admin, the
    fresh custom claims in the Firebase ID token are authoritative.
    This diverges from the original plan (07-01, Task 3 item 5)
    which assumed Firestore takes precedence, but token-based
    precedence is the correct Firebase Auth pattern: custom claims
    are set server-side and are always the latest source of truth
    for role assignments.
    """
    async def _verify_token(_: str) -> dict:
        return {'uid': 'user-1', 'role': 'admin'}

    docs = {
        'user-1': {
            'email': 'user-1@example.com',
            'displayName': 'User One',
            'role': 'student',
            'status': 'active',
        },
    }
    monkeypatch.setattr(auth_module, 'verify_firebase_token', _verify_token)
    monkeypatch.setattr(auth_module, 'get_db', lambda: FakeDb(docs))

    user = await auth_module.get_current_user(
        _make_credentials('mock-token-admin-user-1'),
    )
    assert user.uid == 'user-1'
    assert user.role == 'admin'


@pytest.mark.asyncio
async def test_get_current_user_success_without_role_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Firestore role is used when token has no role claim."""
    async def _verify_token(_: str) -> dict:
        return {'uid': 'user-2'}

    docs = {
        'user-2': {
            'email': 'user-2@example.com',
            'displayName': 'User Two',
            'role': 'staff',
            'status': 'active',
        },
    }
    monkeypatch.setattr(auth_module, 'verify_firebase_token', _verify_token)
    monkeypatch.setattr(auth_module, 'get_db', lambda: FakeDb(docs))

    user = await auth_module.get_current_user(
        _make_credentials('mock-token-staff-user-2'),
    )
    assert user.uid == 'user-2'
    assert user.role == 'staff'


@pytest.mark.asyncio
async def test_get_current_user_missing_uid_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing uid claim raises HTTP 401."""
    async def _verify_token(_: str) -> dict:
        return {'email': 'missing@example.com'}

    monkeypatch.setattr(auth_module, 'verify_firebase_token', _verify_token)

    with pytest.raises(fastapi.HTTPException) as exc:
        await auth_module.get_current_user(_make_credentials('mock-token'))

    assert exc.value.status_code == fastapi.status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == 'Token missing uid claim'
    assert exc.value.headers == {'WWW-Authenticate': 'Bearer'}


@pytest.mark.asyncio
async def test_get_current_user_user_not_found(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Missing user document raises HTTP 401."""
    async def _verify_token(_: str) -> dict:
        return {'uid': 'missing'}

    monkeypatch.setattr(auth_module, 'verify_firebase_token', _verify_token)
    monkeypatch.setattr(auth_module, 'get_db', lambda: FakeDb({}))

    with pytest.raises(fastapi.HTTPException) as exc:
        await auth_module.get_current_user(_make_credentials('mock-token'))

    assert exc.value.status_code == fastapi.status.HTTP_401_UNAUTHORIZED
    assert exc.value.detail == 'User not found in database'
    assert exc.value.headers == {'WWW-Authenticate': 'Bearer'}


@pytest.mark.asyncio
async def test_get_current_user_disabled_user(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Disabled users are rejected with HTTP 403."""
    async def _verify_token(_: str) -> dict:
        return {'uid': 'disabled-user'}

    docs = {
        'disabled-user': {
            'email': 'disabled@example.com',
            'displayName': 'Disabled User',
            'role': 'student',
            'status': 'disabled',
        },
    }
    monkeypatch.setattr(auth_module, 'verify_firebase_token', _verify_token)
    monkeypatch.setattr(auth_module, 'get_db', lambda: FakeDb(docs))

    with pytest.raises(fastapi.HTTPException) as exc:
        await auth_module.get_current_user(_make_credentials('mock-token'))

    assert exc.value.status_code == fastapi.status.HTTP_403_FORBIDDEN
    assert exc.value.detail == 'User account is disabled'
    assert exc.value.headers is None


@pytest.mark.asyncio
async def test_get_current_user_missing_credentials() -> None:
    """Missing credentials raises an error.

    When credentials is None the function raises AttributeError
    because it tries to access .credentials on None.  In
    production, FastAPI's Depends(HTTPBearer()) prevents this by
    returning a 401 before the function is ever called.
    """
    with pytest.raises(AttributeError):
        await auth_module.get_current_user(
            None,  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_require_admin_allows_admin() -> None:
    """Admins pass require_admin."""
    user = _make_user('admin-1', 'admin')
    assert await auth_module.require_admin(user) == user


@pytest.mark.asyncio
async def test_require_admin_denies_non_admin() -> None:
    """Non-admin users are rejected by require_admin."""
    user = _make_user('staff-1', 'staff')
    with pytest.raises(fastapi.HTTPException) as exc:
        await auth_module.require_admin(user)
    assert exc.value.status_code == fastapi.status.HTTP_403_FORBIDDEN
    assert exc.value.detail == 'Admin access required'


@pytest.mark.asyncio
async def test_require_staff_or_admin_allows_staff() -> None:
    """Staff users pass require_staff_or_admin."""
    user = _make_user('staff-2', 'staff')
    assert await auth_module.require_staff_or_admin(user) == user


@pytest.mark.asyncio
async def test_require_staff_or_admin_denies_student() -> None:
    """Students are rejected by require_staff_or_admin."""
    user = _make_user('student-1', 'student')
    with pytest.raises(fastapi.HTTPException) as exc:
        await auth_module.require_staff_or_admin(user)
    assert exc.value.status_code == fastapi.status.HTTP_403_FORBIDDEN
    assert exc.value.detail == 'Staff access required'


@pytest.mark.asyncio
async def test_require_active_user_returns_user() -> None:
    """require_active_user returns the provided user."""
    user = _make_user('student-2', 'student')
    assert await auth_module.require_active_user(user) == user


@pytest.mark.asyncio
async def test_require_role_allows_listed_roles() -> None:
    """require_role allows a user with an allowed role."""
    checker = auth_module.require_role('admin', 'staff')
    user = _make_user('staff-3', 'staff')
    assert await checker(user) == user


@pytest.mark.asyncio
async def test_require_role_denies_unlisted_roles() -> None:
    """require_role denies users without allowed roles."""
    checker = auth_module.require_role('admin')
    user = _make_user('student-3', 'student')
    with pytest.raises(fastapi.HTTPException) as exc:
        await checker(user)
    assert exc.value.status_code == fastapi.status.HTTP_403_FORBIDDEN
    assert exc.value.detail == 'Role access required'


def test_has_subject_access_admin() -> None:
    """Admins can access any subject."""
    user = _make_user('admin-2', 'admin')
    assert auth_module.has_subject_access(user, 'subject-1') is True


def test_has_subject_access_staff_assignments() -> None:
    """Staff access is limited to assigned subjects."""
    user = _make_user(
        'staff-4',
        'staff',
        subject_ids=['subject-1'],
    )
    assert auth_module.has_subject_access(user, 'subject-1') is True
    assert auth_module.has_subject_access(user, 'subject-2') is False


def test_has_subject_access_student() -> None:
    """Students do not have subject access."""
    user = _make_user('student-4', 'student')
    assert auth_module.has_subject_access(user, 'subject-1') is False


def test_has_department_access_admin() -> None:
    """Admins can access any department."""
    user = _make_user('admin-3', 'admin')
    assert auth_module.has_department_access(user, 'dept-1') is True


def test_has_department_access_department_match() -> None:
    """Department access is limited to matching department ids."""
    user = _make_user(
        'staff-5',
        'staff',
        department_id='dept-1',
    )
    assert auth_module.has_department_access(user, 'dept-1') is True
    assert auth_module.has_department_access(user, 'dept-2') is False


def test_can_modify_note_staff_subject_access() -> None:
    """Staff can modify notes in assigned subjects."""
    user = _make_user(
        'staff-6',
        'staff',
        subject_ids=['subject-1'],
    )
    note_data = {'subjectId': 'subject-1'}
    assert auth_module.can_modify_note(user, note_data) is True


def test_can_modify_note_staff_missing_subject() -> None:
    """Staff cannot modify notes without subject access."""
    user = _make_user(
        'staff-7',
        'staff',
        subject_ids=['subject-1'],
    )
    assert auth_module.can_modify_note(user, {}) is False
    note_data = {'subjectId': 'subject-2'}
    assert auth_module.can_modify_note(user, note_data) is False


def test_can_modify_note_student() -> None:
    """Students cannot modify notes."""
    user = _make_user('student-5', 'student')
    note_data = {'subjectId': 'subject-1'}
    assert auth_module.can_modify_note(user, note_data) is False


def test_can_create_note_in_subject_admin() -> None:
    """Admins can create notes in any subject."""
    user = _make_user('admin-4', 'admin')
    assert auth_module.can_create_note_in_subject(user, 'subject-1') is True


def test_can_create_note_in_subject_staff() -> None:
    """Staff can create notes in assigned subjects."""
    user = _make_user(
        'staff-8',
        'staff',
        subject_ids=['subject-2'],
    )
    assert auth_module.can_create_note_in_subject(user, 'subject-2') is True
    assert auth_module.can_create_note_in_subject(user, 'subject-1') is False


def test_can_create_note_in_subject_student() -> None:
    """Students cannot create notes in subjects."""
    user = _make_user('student-6', 'student')
    assert auth_module.can_create_note_in_subject(user, 'subject-1') is False
