"""
============================================================================
FILE: auth.py
LOCATION: api/auth.py
============================================================================

PURPOSE:
    Core authentication module providing FastAPI dependencies for role-based
    endpoint protection with mock token verification for local development.

ROLE IN PROJECT:
    Central authentication layer for the backend. Provides:
    - UserInfo model for authenticated user data
    - Token verification supporting mock and real Firebase tokens
    - FastAPI dependencies for role-based access control
    - Login endpoint for mock authentication

KEY COMPONENTS:
    - UserInfo: Pydantic model for user data with role and department
    - LoginRequest: Pydantic model for login credentials
    - verify_firebase_token: Token parser supporting mock-token format
    - get_current_user: FastAPI dependency extracting user from Bearer token
    - require_admin: FastAPI dependency restricting to admin role
    - require_staff: FastAPI dependency restricting to staff/admin roles
    - require_role: Factory for custom role requirements
    - require_department_access: Factory for department access validation
    - router: APIRouter with /api/auth/login endpoint

DEPENDENCIES:
    - External: fastapi, pydantic
    - Internal: config.py (get_db)

USAGE:
    from api.auth import get_current_user, require_admin

    @app.get("/admin-only")
    async def admin_endpoint(user = Depends(require_admin)):
        return {"message": f"Hello admin {user.email}"}
============================================================================
"""

from fastapi import APIRouter, Depends, HTTPException, Header, status
from pydantic import BaseModel
from typing import Optional


class UserInfo(BaseModel):
    """User information model for authenticated users."""

    uid: str
    email: str
    display_name: Optional[str] = None
    role: str  # "admin" | "staff" | "student"
    department_id: Optional[str] = None
    status: str = "active"


class LoginRequest(BaseModel):
    """Login request payload with email and password."""

    email: str
    password: str


def verify_firebase_token(token: str) -> dict:
    """
    Verify Firebase ID token and return decoded claims.

    Supports mock token format: mock-token-{role}-{uid}
    Example: "mock-token-admin-mock-admin-001"

    Args:
        token: Firebase ID token or mock token string

    Returns:
        dict: Token claims with uid, email, name, role

    Raises:
        HTTPException: 401 if token is invalid or expired
    """
    if token.startswith("mock-token-"):
        # Parse mock token format: mock-token-{role}-{uid}
        parts = token.split("-")
        if len(parts) < 4:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid mock token format",
            )

        role = parts[2]  # "admin", "staff", or "student"
        uid = "-".join(parts[3:])  # Join remaining parts as UID

        return {
            "uid": uid,
            "email": f"{role}@test.com",
            "name": f"Mock {role.capitalize()}",
            "role": role,
        }

    # Real Firebase token verification not implemented yet
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Real Firebase authentication not implemented. Use mock tokens for development.",
    )


def get_db():
    """Get database client (mock or real Firebase)."""
    try:
        from config import get_db as config_get_db

        return config_get_db()
    except ImportError:
        # Fallback to creating MockFirestoreClient directly
        from mock_firestore import MockFirestoreClient

        return MockFirestoreClient()


def get_current_user(authorization: str = Header(None)) -> UserInfo:
    """
    FastAPI dependency to extract and verify current user from Bearer token.

    Extracts token from Authorization header, verifies it, looks up user
    in Firestore, and returns UserInfo model.

    Args:
        authorization: Authorization header value (Bearer {token})

    Returns:
        UserInfo: Authenticated user information

    Raises:
        HTTPException: 401 if not authenticated, 403 if user disabled/not found
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )

    # Extract token from "Bearer {token}"
    parts = authorization.split(" ")
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Expected: Bearer {token}",
        )

    token = parts[1]

    # Verify token and get claims
    try:
        claims = verify_firebase_token(token)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token verification failed: {str(e)}",
        )

    uid = claims.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing uid claim"
        )

    # Look up user in Firestore
    db = get_db()
    user_doc = db.collection("users").document(uid).get()

    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User not found in database"
        )

    user_data = user_doc.to_dict()

    # Check if user is disabled
    if user_data.get("status") == "disabled":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account has been disabled"
        )

    # Return UserInfo
    return UserInfo(
        uid=uid,
        email=user_data.get("email", claims.get("email")),
        display_name=user_data.get("displayName"),
        role=user_data.get("role", "student"),
        department_id=user_data.get("departmentId"),
        status=user_data.get("status", "active"),
    )


def require_admin(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """
    FastAPI dependency requiring admin role.

    Args:
        user: Current authenticated user from get_current_user

    Returns:
        UserInfo: User if admin

    Raises:
        HTTPException: 403 if user is not admin
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return user


def require_staff(user: UserInfo = Depends(get_current_user)) -> UserInfo:
    """
    FastAPI dependency requiring staff or admin role.

    Args:
        user: Current authenticated user from get_current_user

    Returns:
        UserInfo: User if staff or admin

    Raises:
        HTTPException: 403 if user is not staff or admin
    """
    if user.role not in ("admin", "staff"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Staff or admin access required",
        )
    return user


def require_role(*allowed_roles: str):
    """
    Factory to create a dependency that checks for specific roles.

    Usage:
        @app.get("/endpoint")
        async def endpoint(user = Depends(require_role("admin", "staff"))):
            ...

    Args:
        allowed_roles: Variable number of role strings to allow

    Returns:
        Callable: FastAPI dependency function
    """

    def role_checker(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Required role: {' or '.join(allowed_roles)}",
            )
        return user

    return role_checker


def require_department_access(department_id: str):
    """
    Factory to create a dependency that checks user belongs to a department.
    Admins always have access to all departments.

    Usage:
        @app.get("/departments/{dept_id}/data")
        async def get_data(
            dept_id: str,
            user = Depends(require_department_access(dept_id))
        ):
            ...

    Args:
        department_id: Department ID to check access for

    Returns:
        Callable: FastAPI dependency function
    """

    def department_checker(user: UserInfo = Depends(get_current_user)) -> UserInfo:
        if user.role == "admin":
            return user
        if user.department_id != department_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No access to this department",
            )
        return user

    return department_checker


router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
async def login(creds: LoginRequest):
    """
    Mock login endpoint - validates email/password against Firestore users.

    Queries user by email, validates password, checks status, and returns
    a mock token if successful.

    Args:
        creds: LoginRequest with email and password

    Returns:
        dict: Token and user information

    Raises:
        HTTPException: 401 if credentials invalid, 403 if account disabled
    """
    db = get_db()

    # Query user by email
    users_ref = db.collection("users")
    query = users_ref.where("email", "==", creds.email)
    results = list(query.stream())

    if not results:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    user_doc = results[0]
    user_data = user_doc.to_dict()

    # Check if disabled
    if user_data.get("status") == "disabled":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account has been disabled"
        )

    # Validate password
    stored_password = user_data.get("password", "")
    if stored_password != creds.password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password"
        )

    # Generate mock token
    uid = user_doc.id
    role = user_data.get("role", "student")
    token = f"mock-token-{role}-{uid}"

    return {
        "token": token,
        "user": {
            "id": uid,
            "email": user_data.get("email"),
            "displayName": user_data.get("displayName"),
            "role": role,
            "departmentId": user_data.get("departmentId"),
            "status": user_data.get("status", "active"),
        },
    }
