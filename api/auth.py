"""
============================================================================
FILE: auth.py
LOCATION: api/auth.py
============================================================================

PURPOSE:
    Firebase Authentication utilities for verifying ID tokens and extracting
    user role information for role-based access control (RBAC).

ROLE IN PROJECT:
    Provides FastAPI dependencies for protected endpoints. All endpoints that
    require authentication or specific roles should use these dependencies.

KEY COMPONENTS:
    - verify_firebase_token(): Verify Firebase ID token from Authorization
      header
    - get_current_user(): FastAPI dependency returning current user with role
    - require_admin(): Dependency that ensures user is an admin
    - require_staff(): Dependency that ensures user is staff (or admin)
    - require_role(): Factory for role-checking dependencies

DEPENDENCIES:
    - External: firebase_admin.auth, fastapi
    - Internal: config.py (Firestore client)

USAGE:
    from auth import get_current_user, require_admin
    
    @app.get("/api/users")
    async def list_users(user = Depends(require_admin)):
        ...
============================================================================
"""

import os

from firebase_admin import auth
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:
    from config import get_auth, get_db
    from models import FirestoreUser
except ImportError:
    from api.config import get_auth, get_db
    from api.models import FirestoreUser


security = HTTPBearer()


async def verify_firebase_token(token: str) -> dict:
    """
    Verify a Firebase ID token and return decoded claims.

    Args:
        token: The Firebase ID token (JWT)

    Returns:
        dict: Decoded token claims containing uid, email, etc.

    Raises:
        HTTPException: If token is invalid or expired
    """
    use_real_firebase = os.getenv("USE_REAL_FIREBASE", "false").lower() == "true"
    is_testing = os.getenv("TESTING", "false").lower() == "true"

    if is_testing and not use_real_firebase:
        return _verify_mock_token(token)

    try:
        auth_client = get_auth()
        # Allow 10 seconds of clock skew to prevent "Token used too early" errors
        decoded_token = auth_client.verify_id_token(token, clock_skew_seconds=10)
        return decoded_token
    except auth.InvalidIdTokenError as exc:
        print(f"DEBUG: Invalid token error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except auth.ExpiredIdTokenError as exc:
        print(f"DEBUG: Expired token error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication token has expired: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except auth.RevokedIdTokenError as exc:
        print(f"DEBUG: Revoked token error: {exc}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication token has been revoked: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )


def _verify_mock_token(token: str) -> dict:
    """Mock token verification for test-only usage."""
    if token.startswith("mock-token-"):
        parts = token.split("-")
        if len(parts) >= 4:
            role = parts[2]
            uid = "-".join(parts[3:])
        elif len(parts) == 3:
            role = parts[2]
            uid = f"mock-{role}-user"
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid mock token",
            )

        return {
            "uid": uid,
            "email": f"{role}@aura.edu",
            "name": f"Mock {role.capitalize()}",
            "role": role,
        }

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid mock token",
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> FirestoreUser:
    """
    Extract and verify the current user from the Authorization header.

    This dependency:
    1. Extracts the Bearer token from the Authorization header
    2. Verifies the token with Firebase Auth
    3. Looks up the user in Firestore for current permissions
    4. Returns a FirestoreUser model

    Usage:
        @app.get("/protected")
        async def protected_route(
            user: FirestoreUser = Depends(get_current_user),
        ):
            return {"message": f"Hello {user.displayName}"}
    """
    token = credentials.credentials

    decoded_token = await verify_firebase_token(token)
    uid = decoded_token.get("uid")

    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing uid claim",
            headers={"WWW-Authenticate": "Bearer"},
        )

    database = get_db()
    user_doc = database.collection("users").document(uid).get()

    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found in database",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_data = user_doc.to_dict()

    if user_data.get("status") != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    user_data["uid"] = uid
    if "role" in decoded_token:
        user_data["role"] = decoded_token["role"]

    return FirestoreUser(**user_data)


async def require_admin(
    user: FirestoreUser = Depends(get_current_user),
) -> FirestoreUser:
    """Dependency that requires admin role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


async def require_staff(
    user: FirestoreUser = Depends(get_current_user),
) -> FirestoreUser:
    """Dependency that requires staff or admin role."""
    if user.role not in ("admin", "staff"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff access required",
        )
    return user


async def require_staff_or_admin(
    user: FirestoreUser = Depends(get_current_user),
) -> FirestoreUser:
    """Alias for require_staff for clarity."""
    return await require_staff(user)


async def require_active_user(
    user: FirestoreUser = Depends(get_current_user),
) -> FirestoreUser:
    """Dependency that requires active user (any role)."""
    return user


def require_role(*allowed_roles: str):
    async def role_checker(
        user: FirestoreUser = Depends(get_current_user),
    ) -> FirestoreUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Role access required",
            )
        return user
    return role_checker


def has_subject_access(user: FirestoreUser, subject_id: str) -> bool:
    """
    Check if user has access to a specific subject.

    Args:
        user: The FirestoreUser to check
        subject_id: The subject ID to check access for

    Returns:
        bool: True if user has access to the subject
    """
    if user.role == "admin":
        return True

    if user.role == "staff":
        return subject_id in (user.subjectIds or [])

    return False


def has_department_access(user: FirestoreUser, department_id: str) -> bool:
    """
    Check if user has access to a specific department.

    Args:
        user: The FirestoreUser to check
        department_id: The department ID to check access for

    Returns:
        bool: True if user has access to the department
    """
    if user.role == "admin":
        return True

    return user.departmentId == department_id


def can_modify_note(user: FirestoreUser, note_data: dict) -> bool:
    """
    Check if user can modify a note.

    Args:
        user: The FirestoreUser to check
        note_data: The note document data (must contain subjectId)

    Returns:
        bool: True if user can modify the note
    """
    if user.role == "admin":
        return True

    if user.role == "staff":
        subject_id = note_data.get("subjectId")
        return bool(subject_id) and has_subject_access(user, subject_id)

    return False


def can_create_note_in_subject(
    user: FirestoreUser,
    subject_id: str,
) -> bool:
    """
    Check if user can create a note in a specific subject.

    Args:
        user: The FirestoreUser to check
        subject_id: The subject ID where note would be created

    Returns:
        bool: True if user can create a note in the subject
    """
    return has_subject_access(user, subject_id)

