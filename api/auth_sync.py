"""
============================================================================
FILE: auth_sync.py
LOCATION: api/auth_sync.py
============================================================================

PURPOSE:
    Handle synchronization between Firebase Auth users and Firestore users.

ROLE IN PROJECT:
    - Create Firestore user documents on first login
    - Sync user metadata between Auth and Firestore
    - Provide admin-managed user lifecycle endpoints

KEY COMPONENTS:
    - sync_user: First-login sync endpoint
    - create_firebase_user: Admin user creation
    - update_firebase_user: Admin user updates
    - delete_firebase_user: Admin user deletion

DEPENDENCIES:
    - External: fastapi, pydantic, firebase_admin
    - Internal: config.py, auth.py, validators.py

USAGE:
    Mounted in api/main.py via app.include_router(auth_sync_router)
============================================================================
"""

from datetime import datetime
from typing import Optional, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field, field_validator, model_validator

try:
    from config import get_auth, get_db
    from auth import FirestoreUser, require_admin, verify_firebase_token
    from validators import validate_user_role_constraints
except ImportError:
    from api.config import get_auth, get_db
    from api.auth import FirestoreUser, require_admin, verify_firebase_token
    from api.validators import validate_user_role_constraints


router = APIRouter()
security = HTTPBearer()


class SyncUserRequest(BaseModel):
    """Request to sync Firebase Auth user with Firestore."""

    departmentId: Optional[str] = Field(
        None,
        description="Department assignment",
    )
    subjectIds: Optional[list[str]] = Field(
        default_factory=list,
        description="Subject assignments",
    )
    displayName: Optional[str] = Field(
        None,
        description="User display name",
    )


class SyncUserResponse(BaseModel):
    """Response after user sync."""

    message: str
    user: FirestoreUser
    isNewUser: bool


class UserProfileUpdate(BaseModel):
    """Request to update user profile."""

    displayName: Optional[str] = None
    departmentId: Optional[str] = None
    subjectIds: Optional[list[str]] = None


class CreateFirebaseUserRequest(BaseModel):
    """Request to create a new user via admin."""

    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Initial password")
    displayName: str = Field(..., description="User display name")
    role: Literal["admin", "staff", "student"] = Field(
        ...,
        description="User role",
    )
    departmentId: Optional[str] = Field(
        None,
        description="Department ID",
    )
    subjectIds: list[str] = Field(
        default_factory=list,
        description="Subject IDs for staff",
    )
    sendEmailVerification: bool = Field(
        False,
        description="Send email verification",
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        """Validate password length."""
        if len(value) < 6:
            raise ValueError("Password must be at least 6 characters")
        return value

    @model_validator(mode="after")
    def validate_role_constraints(self) -> "CreateFirebaseUserRequest":
        """Validate role-specific requirements."""
        validate_user_role_constraints(
            self.role,
            self.departmentId,
            self.subjectIds,
        )
        return self


class CreateFirebaseUserResponse(BaseModel):
    """Response after creating Firebase user."""

    message: str
    uid: str
    user: FirestoreUser


async def get_current_auth_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """Return decoded Firebase token without requiring Firestore user."""
    token = credentials.credentials
    decoded_token = await verify_firebase_token(token)
    uid = decoded_token.get("uid")
    if not uid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing uid claim",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return decoded_token


@router.post("/api/auth/sync", response_model=SyncUserResponse)
async def sync_user(
    request: Optional[SyncUserRequest] = None,
    current_user: dict = Depends(get_current_auth_user),
) -> SyncUserResponse:
    """
    Sync Firebase Auth user with Firestore user document.

    Creates Firestore user document on first login, otherwise returns
    existing user data.
    """
    db = get_db()
    auth_client = get_auth()
    uid = current_user.get("uid")

    user_ref = db.collection("users").document(uid)
    user_doc = user_ref.get()

    if user_doc.exists:
        user_data = user_doc.to_dict()
        user_data["uid"] = uid
        return SyncUserResponse(
            message="User already exists",
            user=FirestoreUser(**user_data),
            isNewUser=False,
        )

    try:
        auth_user = auth_client.get_user(uid)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get user from Firebase Auth: {str(exc)}",
        ) from exc

    existing_users = list(db.collection("users").limit(1).stream())
    is_first_user = len(existing_users) == 0

    if is_first_user:
        role = "admin"
    else:
        custom_claims = getattr(auth_user, "custom_claims", None) or {}
        role = custom_claims.get("role")
        if not role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User not provisioned by admin",
            )

    display_name = ""
    if request and request.displayName is not None:
        display_name = request.displayName
    elif getattr(auth_user, "display_name", None):
        display_name = auth_user.display_name or ""

    subject_ids = []
    if request and request.subjectIds is not None:
        subject_ids = request.subjectIds

    department_id = None
    if request:
        department_id = request.departmentId

    try:
        validate_user_role_constraints(role, department_id, subject_ids)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    timestamp = datetime.utcnow().isoformat()
    user_data = {
        "uid": uid,
        "email": auth_user.email or "",
        "displayName": display_name,
        "role": role,
        "status": "active",
        "departmentId": department_id,
        "subjectIds": subject_ids,
        "createdAt": timestamp,
        "updatedAt": timestamp,
        "_v": 1,
    }

    user_ref.set(user_data)

    return SyncUserResponse(
        message="User created successfully",
        user=FirestoreUser(**user_data),
        isNewUser=True,
    )


@router.post("/api/admin/users", response_model=CreateFirebaseUserResponse)
async def create_firebase_user(
    request: CreateFirebaseUserRequest,
    admin_user: FirestoreUser = Depends(require_admin),
) -> CreateFirebaseUserResponse:
    """
    Create a new user in Firebase Auth and Firestore (admin only).
    """
    db = get_db()
    auth_client = get_auth()

    invalid_email_error = getattr(auth_client, "InvalidEmailError", None)
    weak_password_error = getattr(auth_client, "WeakPasswordError", None)
    email_exists_error = getattr(auth_client, "EmailAlreadyExistsError", None)

    try:
        auth_user = auth_client.create_user(
            email=request.email,
            password=request.password,
            display_name=request.displayName,
            email_verified=False,
        )

        uid = auth_user.uid

        if hasattr(auth_client, "set_custom_user_claims"):
            auth_client.set_custom_user_claims(uid, {"role": request.role})

        timestamp = datetime.utcnow().isoformat()
        user_data = {
            "uid": uid,
            "email": request.email,
            "displayName": request.displayName,
            "role": request.role,
            "status": "active",
            "departmentId": request.departmentId,
            "subjectIds": request.subjectIds,
            "createdAt": timestamp,
            "updatedAt": timestamp,
            "_v": 1,
        }

        db.collection("users").document(uid).set(user_data)

        if request.sendEmailVerification and hasattr(
            auth_client, "generate_email_verification_link"
        ):
            verification_link = auth_client.generate_email_verification_link(
                request.email
            )
            print(f"Email verification link: {verification_link}")

        return CreateFirebaseUserResponse(
            message="User created successfully",
            uid=uid,
            user=FirestoreUser(**user_data),
        )

    except Exception as exc:
        if email_exists_error and isinstance(exc, email_exists_error):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            ) from exc
        if invalid_email_error and isinstance(exc, invalid_email_error):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email address",
            ) from exc
        if weak_password_error and isinstance(exc, weak_password_error):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is too weak",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(exc)}",
        ) from exc


@router.put("/api/admin/users/{uid}", response_model=FirestoreUser)
async def update_firebase_user(
    uid: str,
    request: UserProfileUpdate,
    admin_user: FirestoreUser = Depends(require_admin),
) -> FirestoreUser:
    """
    Update an existing user in Firebase Auth and Firestore (admin only).
    """
    db = get_db()
    auth_client = get_auth()

    user_ref = db.collection("users").document(uid)
    user_doc = user_ref.get()

    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    try:
        update_props = {}
        if request.displayName:
            update_props["display_name"] = request.displayName

        if update_props:
            auth_client.update_user(uid, **update_props)

        update_data = {"updatedAt": datetime.utcnow().isoformat()}

        if request.displayName is not None:
            update_data["displayName"] = request.displayName
        if request.departmentId is not None:
            update_data["departmentId"] = request.departmentId
        if request.subjectIds is not None:
            update_data["subjectIds"] = request.subjectIds

        user_ref.update(update_data)

        updated_doc = user_ref.get()
        user_data = updated_doc.to_dict()
        user_data["uid"] = uid

        return FirestoreUser(**user_data)

    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update user: {str(exc)}",
        ) from exc


@router.delete("/api/admin/users/{uid}")
async def delete_firebase_user(
    uid: str,
    admin_user: FirestoreUser = Depends(require_admin),
) -> dict:
    """
    Delete a user from Firebase Auth and Firestore (admin only).
    """
    db = get_db()
    auth_client = get_auth()

    if uid == admin_user.uid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    user_ref = db.collection("users").document(uid)
    user_doc = user_ref.get()

    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user_not_found_error = getattr(auth_client, "UserNotFoundError", None)

    try:
        auth_client.delete_user(uid)
        user_ref.delete()
        return {"message": "User deleted successfully"}
    except Exception as exc:
        if user_not_found_error and isinstance(exc, user_not_found_error):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found in Firebase Auth",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(exc)}",
        ) from exc
