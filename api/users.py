"""
============================================================================
FILE: users.py
LOCATION: api/users.py
============================================================================

PURPOSE:
    Provide user management CRUD endpoints and current user profile access.

ROLE IN PROJECT:
    Enables admin management of user accounts and exposes the current
    authenticated user profile for frontend session hydration.

KEY COMPONENTS:
    - UserCreate/UserUpdate/UserResponse: Pydantic models for user data
    - get_me: Current user profile endpoint
    - list_users/create_user/get_user/update_user/delete_user: CRUD endpoints

DEPENDENCIES:
    - External: fastapi, pydantic
    - Internal: auth.py, config.py

USAGE:
    app.include_router(router)
============================================================================
"""

from datetime import datetime
from typing import List, Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr

try:
    from auth import get_current_user, require_admin, UserInfo
except (ImportError, ModuleNotFoundError):
    from api.auth import get_current_user, require_admin, UserInfo

try:
    from config import get_db
except (ImportError, ModuleNotFoundError):
    from api.config import get_db


router = APIRouter(prefix="/api", tags=["users"])


class UserCreate(BaseModel):
    """Request payload for creating a user."""

    email: EmailStr
    password: str
    display_name: str
    role: Literal["admin", "staff", "student"]
    department_id: Optional[str] = None
    subject_ids: Optional[List[str]] = None


class UserUpdate(BaseModel):
    """Request payload for updating a user."""

    display_name: Optional[str] = None
    role: Optional[Literal["admin", "staff", "student"]] = None
    department_id: Optional[str] = None
    subject_ids: Optional[List[str]] = None
    status: Optional[Literal["active", "disabled"]] = None


class UserResponse(BaseModel):
    """Response model for user data."""

    id: str
    email: str
    display_name: Optional[str] = None
    role: str
    department_id: Optional[str] = None
    subject_ids: Optional[List[str]] = None
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None


@router.get("/auth/me")
async def get_me(user: UserInfo = Depends(get_current_user)) -> dict:
    """Get current authenticated user profile.

    Args:
        user: Current authenticated user from token.

    Returns:
        dict: Current user profile fields.
    """
    db = get_db()
    user_doc = db.collection("users").document(user.uid).get()
    user_data = user_doc.to_dict() if user_doc.exists else {}

    return {
        "id": user.uid,
        "email": user.email,
        "displayName": user.display_name,
        "role": user.role,
        "departmentId": user.department_id,
        "status": user.status,
        "createdAt": user_data.get("createdAt"),
        "updatedAt": user_data.get("updatedAt"),
    }


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    role: Optional[str] = None,
    department_id: Optional[str] = None,
    admin: UserInfo = Depends(require_admin),
) -> List[UserResponse]:
    """List all users. Admin only.

    Args:
        role: Optional role filter.
        department_id: Optional department filter.
        admin: Authenticated admin user.

    Returns:
        List[UserResponse]: Users matching filters.
    """
    db = get_db()
    users_ref = db.collection("users")

    if role:
        users_ref = users_ref.where("role", "==", role)
    if department_id:
        users_ref = users_ref.where("departmentId", "==", department_id)

    users: List[UserResponse] = []
    for doc in users_ref.stream():
        data = doc.to_dict() or {}
        users.append(
            UserResponse(
                id=doc.id,
                email=data.get("email", ""),
                display_name=data.get("displayName"),
                role=data.get("role", "student"),
                department_id=data.get("departmentId"),
                subject_ids=data.get("subjectIds"),
                status=data.get("status", "active"),
                created_at=data.get("createdAt"),
                updated_at=data.get("updatedAt"),
            )
        )
    return users


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_user(
    user_data: UserCreate,
    admin: UserInfo = Depends(require_admin),
) -> UserResponse:
    """Create a new user. Admin only.

    Args:
        user_data: New user data payload.
        admin: Authenticated admin user.

    Returns:
        UserResponse: Created user data.

    Raises:
        HTTPException: 409 if email already exists.
    """
    db = get_db()
    existing = list(
        db.collection("users").where("email", "==", user_data.email).stream()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user_id = f"user-{int(datetime.now().timestamp() * 1000)}"
    now = datetime.utcnow().isoformat() + "Z"

    new_user = {
        "email": user_data.email,
        "password": user_data.password,
        "displayName": user_data.display_name,
        "role": user_data.role,
        "departmentId": user_data.department_id,
        "subjectIds": user_data.subject_ids,
        "status": "active",
        "createdAt": now,
        "updatedAt": now,
    }

    db.collection("users").document(user_id).set(new_user)

    return UserResponse(
        id=user_id,
        email=new_user["email"],
        display_name=new_user["displayName"],
        role=new_user["role"],
        department_id=new_user["departmentId"],
        subject_ids=new_user["subjectIds"],
        status=new_user["status"],
        created_at=new_user["createdAt"],
        updated_at=new_user["updatedAt"],
    )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: UserInfo = Depends(get_current_user),
) -> UserResponse:
    """Get user by ID.

    Admin can get any user; others can only get themselves.

    Args:
        user_id: User ID to fetch.
        current_user: Authenticated user.

    Returns:
        UserResponse: Requested user data.

    Raises:
        HTTPException: 403 if access denied, 404 if user not found.
    """
    if current_user.role != "admin" and current_user.uid != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied",
        )

    db = get_db()
    user_doc = db.collection("users").document(user_id).get()

    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    data = user_doc.to_dict() or {}
    return UserResponse(
        id=user_doc.id,
        email=data.get("email", ""),
        display_name=data.get("displayName"),
        role=data.get("role", "student"),
        department_id=data.get("departmentId"),
        subject_ids=data.get("subjectIds"),
        status=data.get("status", "active"),
        created_at=data.get("createdAt"),
        updated_at=data.get("updatedAt"),
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    update_data: UserUpdate,
    admin: UserInfo = Depends(require_admin),
) -> UserResponse:
    """Update a user. Admin only.

    Args:
        user_id: User ID to update.
        update_data: User update payload.
        admin: Authenticated admin user.

    Returns:
        UserResponse: Updated user data.

    Raises:
        HTTPException: 404 if user not found.
    """
    db = get_db()
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()

    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    updates = {"updatedAt": datetime.utcnow().isoformat() + "Z"}
    if update_data.display_name is not None:
        updates["displayName"] = update_data.display_name
    if update_data.role is not None:
        updates["role"] = update_data.role
    if update_data.department_id is not None:
        updates["departmentId"] = update_data.department_id
    if update_data.subject_ids is not None:
        updates["subjectIds"] = update_data.subject_ids
    if update_data.status is not None:
        updates["status"] = update_data.status

    user_ref.update(updates)

    updated_doc = user_ref.get()
    data = updated_doc.to_dict() or {}
    return UserResponse(
        id=updated_doc.id,
        email=data.get("email", ""),
        display_name=data.get("displayName"),
        role=data.get("role", "student"),
        department_id=data.get("departmentId"),
        subject_ids=data.get("subjectIds"),
        status=data.get("status", "active"),
        created_at=data.get("createdAt"),
        updated_at=data.get("updatedAt"),
    )


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: str,
    admin: UserInfo = Depends(require_admin),
) -> None:
    """Delete a user. Admin only.

    Args:
        user_id: User ID to delete.
        admin: Authenticated admin user.

    Returns:
        None: 204 response on success.

    Raises:
        HTTPException: 400 if self-deletion, 404 if user not found.
    """
    if admin.uid == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    db = get_db()
    user_ref = db.collection("users").document(user_id)
    user_doc = user_ref.get()

    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user_ref.delete()
    return None
