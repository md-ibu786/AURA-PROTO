"""
============================================================================
FILE: users.py
LOCATION: api/users.py
============================================================================

PURPOSE:
    User management API endpoints for the admin panel. Allows administrators
    to create, list, update, and delete users with role-based access control.

ROLE IN PROJECT:
    Provides the backend API for the Admin Dashboard user management features.
    Only administrators can manage users. Users can fetch their own profile.

KEY COMPONENTS:
    - GET /api/users: List all users (admin only)
    - POST /api/users: Create new user (admin only)
    - GET /api/users/{id}: Get user by ID
    - PUT /api/users/{id}: Update user (admin only)
    - DELETE /api/users/{id}: Delete user (admin only)
    - GET /api/auth/me: Get current authenticated user

DEPENDENCIES:
    - External: fastapi, firebase_admin
    - Internal: config.py, auth.py

USAGE:
    Include router in main.py:
    from users import router as users_router
    app.include_router(users_router)
============================================================================
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Literal
from datetime import datetime

try:
    from config import db, auth as firebase_auth
    from auth import get_current_user, require_admin, UserInfo
except ImportError:
    from api.config import db, auth as firebase_auth
    from api.auth import get_current_user, require_admin, UserInfo


router = APIRouter(prefix="/api", tags=["users"])


# ========== MODELS ==========


class UserCreate(BaseModel):
    """Request model for creating a new user."""

    email: EmailStr
    password: str
    display_name: str
    role: Literal["admin", "staff", "student"]
    department_id: Optional[str] = None  # Required for student only
    subject_ids: Optional[List[str]] = None  # Required for staff (subject-wise access)


class UserUpdate(BaseModel):
    """Request model for updating a user."""

    display_name: Optional[str] = None
    role: Optional[Literal["admin", "staff", "student"]] = None
    department_id: Optional[str] = None
    subject_ids: Optional[List[str]] = None  # For staff subject access modification
    status: Optional[Literal["active", "disabled"]] = None


class UserResponse(BaseModel):
    """Response model for user data."""

    id: str
    email: str
    display_name: Optional[str]
    role: str
    department_id: Optional[str]
    department_name: Optional[str] = None
    subject_ids: Optional[List[str]] = None
    subject_names: Optional[List[str]] = None
    status: str
    created_at: Optional[str]
    updated_at: Optional[str]


# ========== ENDPOINTS ==========


@router.get("/auth/me", response_model=UserResponse)
async def get_me(user: UserInfo = Depends(get_current_user)):
    """
    Get the current authenticated user's profile.

    Returns:
        UserResponse: Current user's details including role and department
    """
    # Fetch additional details from Firestore
    user_doc = db.collection("users").document(user.uid).get()
    user_data = user_doc.to_dict() if user_doc.exists else {}

    # Get department name if assigned
    department_name = None
    if user.department_id:
        dept_doc = db.collection("departments").document(user.department_id).get()
        if dept_doc.exists:
            department_name = dept_doc.to_dict().get("name")

    # Get subject info for staff users
    subject_ids = user_data.get("subjectIds")
    subject_names = None
    if user.role == "staff" and subject_ids:
        from hierarchy_crud import find_doc_by_id

        subject_names = []
        for subj_id in subject_ids:
            subj_ref = find_doc_by_id("subjects", subj_id)
            if subj_ref:
                subj_data = subj_ref.get().to_dict()
                subject_names.append(subj_data.get("name", "Unknown"))

    return UserResponse(
        id=user.uid,
        email=user.email,
        display_name=user.display_name,
        role=user.role,
        department_id=user.department_id,
        department_name=department_name,
        subject_ids=subject_ids if user.role == "staff" else None,
        subject_names=subject_names,
        status=user.status,
        created_at=user_data.get("createdAt"),
        updated_at=user_data.get("updatedAt"),
    )


@router.get("/users", response_model=List[UserResponse])
async def list_users(
    role: Optional[str] = None,
    department_id: Optional[str] = None,
    admin: UserInfo = Depends(require_admin),
):
    """
    List all users. Admin only.

    Args:
        role: Optional filter by role (admin, staff, student)
        department_id: Optional filter by department

    Returns:
        List of UserResponse objects
    """
    query = db.collection("users")

    if role:
        query = query.where("role", "==", role)
    if department_id:
        query = query.where("departmentId", "==", department_id)

    docs = query.stream()
    users = []

    # Cache department names and subject names for efficiency
    dept_cache = {}
    subject_cache = {}

    for doc in docs:
        data = doc.to_dict()
        dept_id = data.get("departmentId")
        dept_name = None
        user_role = data.get("role", "student")

        if dept_id:
            if dept_id not in dept_cache:
                dept_doc = db.collection("departments").document(dept_id).get()
                dept_cache[dept_id] = (
                    dept_doc.to_dict().get("name") if dept_doc.exists else None
                )
            dept_name = dept_cache[dept_id]

        # Get subject info for staff users
        subject_ids = data.get("subjectIds")
        subject_names = None
        if user_role == "staff" and subject_ids:
            from hierarchy_crud import find_doc_by_id

            subject_names = []
            for subj_id in subject_ids:
                if subj_id not in subject_cache:
                    subj_ref = find_doc_by_id("subjects", subj_id)
                    if subj_ref:
                        subj_data = subj_ref.get().to_dict()
                        subject_cache[subj_id] = subj_data.get("name", "Unknown")
                    else:
                        subject_cache[subj_id] = "Unknown"
                subject_names.append(subject_cache[subj_id])

        users.append(
            UserResponse(
                id=doc.id,
                email=data.get("email", ""),
                display_name=data.get("displayName"),
                role=user_role,
                department_id=dept_id,
                department_name=dept_name,
                subject_ids=subject_ids if user_role == "staff" else None,
                subject_names=subject_names,
                status=data.get("status", "active"),
                created_at=data.get("createdAt"),
                updated_at=data.get("updatedAt"),
            )
        )

    return users


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user_data: UserCreate, admin: UserInfo = Depends(require_admin)):
    """
    Create a new user. Admin only.

    Creates user in Firebase Auth and stores profile in Firestore.

    Args:
        user_data: User creation data including email, password, role

    Returns:
        UserResponse: Created user's details
    """
    # Validate requirements based on role
    if user_data.role == "student" and not user_data.department_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department ID is required for student role",
        )

    if user_data.role == "staff" and (
        not user_data.subject_ids or len(user_data.subject_ids) == 0
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one subject ID is required for staff role",
        )

    # Verify department exists if provided (for students)
    if user_data.department_id:
        dept_doc = db.collection("departments").document(user_data.department_id).get()
        if not dept_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Department {user_data.department_id} not found",
            )

    # Verify all subject IDs exist if provided (for staff)
    subject_names = []
    if user_data.subject_ids:
        from hierarchy_crud import find_doc_by_id

        for subject_id in user_data.subject_ids:
            subject_ref = find_doc_by_id("subjects", subject_id)
            if not subject_ref:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Subject {subject_id} not found",
                )
            subject_data = subject_ref.get().to_dict()
            subject_names.append(subject_data.get("name", "Unknown"))

    # Check if user with email already exists in Firestore
    existing_users = (
        db.collection("users").where("email", "==", user_data.email).limit(1).stream()
    )
    for _ in existing_users:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )

    try:
        # Create user in Firebase Auth
        firebase_user = firebase_auth.create_user(
            email=user_data.email,
            password=user_data.password,
            display_name=user_data.display_name,
        )

        # Store user profile in Firestore
        now = datetime.utcnow().isoformat()
        user_doc_data = {
            "email": user_data.email,
            "displayName": user_data.display_name,
            "role": user_data.role,
            "departmentId": user_data.department_id,
            "subjectIds": user_data.subject_ids if user_data.role == "staff" else None,
            "status": "active",
            "createdAt": now,
            "updatedAt": now,
            "password": user_data.password,  # Storing plain password for MOCK AUTH only!
        }

        db.collection("users").document(firebase_user.uid).set(user_doc_data)

        # Get department name for response
        dept_name = None
        if user_data.department_id:
            dept_doc = (
                db.collection("departments").document(user_data.department_id).get()
            )
            if dept_doc.exists:
                dept_name = dept_doc.to_dict().get("name")

        return UserResponse(
            id=firebase_user.uid,
            email=user_data.email,
            display_name=user_data.display_name,
            role=user_data.role,
            department_id=user_data.department_id,
            department_name=dept_name,
            subject_ids=user_data.subject_ids if user_data.role == "staff" else None,
            subject_names=subject_names if user_data.role == "staff" else None,
            status="active",
            created_at=now,
            updated_at=now,
        )

    except firebase_auth.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create user: {str(e)}",
        )


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: str, current_user: UserInfo = Depends(get_current_user)):
    """
    Get user by ID.

    Users can view their own profile. Admins can view any user.
    """
    # Check authorization
    if current_user.role != "admin" and current_user.uid != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot view other users' profiles",
        )

    user_doc = db.collection("users").document(user_id).get()

    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    data = user_doc.to_dict()
    dept_id = data.get("departmentId")
    dept_name = None
    user_role = data.get("role", "student")

    if dept_id:
        dept_doc = db.collection("departments").document(dept_id).get()
        if dept_doc.exists:
            dept_name = dept_doc.to_dict().get("name")

    # Get subject info for staff users
    subject_ids = data.get("subjectIds")
    subject_names = None
    if user_role == "staff" and subject_ids:
        from hierarchy_crud import find_doc_by_id

        subject_names = []
        for subj_id in subject_ids:
            subj_ref = find_doc_by_id("subjects", subj_id)
            if subj_ref:
                subj_data = subj_ref.get().to_dict()
                subject_names.append(subj_data.get("name", "Unknown"))

    return UserResponse(
        id=user_id,
        email=data.get("email", ""),
        display_name=data.get("displayName"),
        role=user_role,
        department_id=dept_id,
        department_name=dept_name,
        subject_ids=subject_ids if user_role == "staff" else None,
        subject_names=subject_names,
        status=data.get("status", "active"),
        created_at=data.get("createdAt"),
        updated_at=data.get("updatedAt"),
    )


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str, update_data: UserUpdate, admin: UserInfo = Depends(require_admin)
):
    """
    Update a user. Admin only.

    Can update display name, role, department, or status.
    """
    user_doc_ref = db.collection("users").document(user_id)
    user_doc = user_doc_ref.get()

    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    current_data = user_doc.to_dict()

    # Build update dict
    updates = {"updatedAt": datetime.utcnow().isoformat()}

    if update_data.display_name is not None:
        updates["displayName"] = update_data.display_name
        # Also update in Firebase Auth
        try:
            firebase_auth.update_user(user_id, display_name=update_data.display_name)
        except Exception:
            pass  # Non-critical, continue with Firestore update

    if update_data.role is not None:
        updates["role"] = update_data.role

    if update_data.department_id is not None:
        # Verify department exists
        dept_doc = (
            db.collection("departments").document(update_data.department_id).get()
        )
        if not dept_doc.exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Department {update_data.department_id} not found",
            )
        updates["departmentId"] = update_data.department_id

    # Handle subject_ids update for staff users
    if update_data.subject_ids is not None:
        if len(update_data.subject_ids) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one subject ID is required",
            )
        # Verify all subject IDs exist
        from hierarchy_crud import find_doc_by_id

        for subject_id in update_data.subject_ids:
            subject_ref = find_doc_by_id("subjects", subject_id)
            if not subject_ref:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Subject {subject_id} not found",
                )
        updates["subjectIds"] = update_data.subject_ids

    if update_data.status is not None:
        updates["status"] = update_data.status
        # If disabling, also disable in Firebase Auth
        if update_data.status == "disabled":
            try:
                firebase_auth.update_user(user_id, disabled=True)
            except Exception:
                pass
        elif update_data.status == "active":
            try:
                firebase_auth.update_user(user_id, disabled=False)
            except Exception:
                pass

    # Apply updates
    user_doc_ref.update(updates)

    # Fetch updated data for response
    updated_doc = user_doc_ref.get()
    data = updated_doc.to_dict()

    dept_id = data.get("departmentId")
    dept_name = None
    if dept_id:
        dept_doc = db.collection("departments").document(dept_id).get()
        if dept_doc.exists:
            dept_name = dept_doc.to_dict().get("name")

    # Get subject info for staff users
    subject_ids = data.get("subjectIds")
    subject_names = None
    if data.get("role") == "staff" and subject_ids:
        from hierarchy_crud import find_doc_by_id

        subject_names = []
        for subj_id in subject_ids:
            subj_ref = find_doc_by_id("subjects", subj_id)
            if subj_ref:
                subj_data = subj_ref.get().to_dict()
                subject_names.append(subj_data.get("name", "Unknown"))

    return UserResponse(
        id=user_id,
        email=data.get("email", ""),
        display_name=data.get("displayName"),
        role=data.get("role", "student"),
        department_id=dept_id,
        department_name=dept_name,
        subject_ids=subject_ids if data.get("role") == "staff" else None,
        subject_names=subject_names,
        status=data.get("status", "active"),
        created_at=data.get("createdAt"),
        updated_at=data.get("updatedAt"),
    )


# Helper function to get all subjects across all departments
def get_all_subjects():
    """Fetch all subjects across all departments with their IDs and names."""
    subjects = []
    # Use collection group query to get all subjects
    for doc in db.collection_group("subjects").stream():
        data = doc.to_dict()
        subjects.append(
            {
                "id": doc.id,
                "name": data.get("name", "Unknown"),
                "code": data.get("code", ""),
                "semester_id": data.get("semester_id", ""),
            }
        )
    return subjects


@router.get("/subjects/all")
async def list_all_subjects(admin: UserInfo = Depends(require_admin)):
    """
    Get all subjects across all departments. Admin only.

    Returns:
        List of all subjects with id, name, code, and semester_id
    """
    subjects = get_all_subjects()
    return {"subjects": subjects}


@router.get("/departments/{department_id}/subjects")
async def get_subjects_by_department(
    department_id: str, admin: UserInfo = Depends(require_admin)
):
    """
    Get all subjects for a specific department. Admin only.

    Args:
        department_id: The department ID

    Returns:
        List of subjects in the department with id, name, code, and semester_id
    """
    subjects = []
    # Query subjects from all semesters in this department
    # Structure: departments/{dept_id}/semesters/{sem_id}/subjects/{subj_id}
    semesters_ref = (
        db.collection("departments").document(department_id).collection("semesters")
    )

    for sem_doc in semesters_ref.stream():
        sem_id = sem_doc.id
        subjects_ref = (
            db.collection("departments")
            .document(department_id)
            .collection("semesters")
            .document(sem_id)
            .collection("subjects")
        )

        for subj_doc in subjects_ref.stream():
            data = subj_doc.to_dict()
            subjects.append(
                {
                    "id": subj_doc.id,
                    "name": data.get("name", "Unknown"),
                    "code": data.get("code", ""),
                    "semester_id": sem_id,
                    "department_id": department_id,
                }
            )

    return {"subjects": subjects}


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str, admin: UserInfo = Depends(require_admin)):
    """
    Delete a user. Admin only.

    Removes user from both Firebase Auth and Firestore.
    """
    # Prevent self-deletion
    if admin.uid == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    user_doc = db.collection("users").document(user_id).get()

    if not user_doc.exists:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    try:
        # Delete from Firebase Auth
        firebase_auth.delete_user(user_id)
    except firebase_auth.UserNotFoundError:
        pass  # User may not exist in Auth, continue with Firestore deletion
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user from Auth: {str(e)}",
        )

    # Delete from Firestore
    db.collection("users").document(user_id).delete()

    return None
