"""
============================================================================
FILE: validators.py
LOCATION: api/validators.py
============================================================================

PURPOSE:
    Validation utilities for user data and RBAC constraints

ROLE IN PROJECT:
    Shared validation logic used by user creation and update endpoints
    Ensures data integrity across the application

KEY COMPONENTS:
    - validate_user_role_constraints: Role-specific schema validation
    - validate_status_transition: Status change authorization checks
    - normalize_user_data: Default normalization for Firestore writes

DEPENDENCIES:
    - External: None
    - Internal: None

USAGE:
    from api.validators import validate_user_role_constraints
============================================================================
"""

import typing


def validate_user_role_constraints(
    role: typing.Literal["admin", "staff", "student"],
    department_id: typing.Optional[str],
    subject_ids: list[str],
) -> None:
    """Validate that user data matches role requirements.

    Args:
        role: User role.
        department_id: Department ID if applicable.
        subject_ids: Subject IDs if applicable.

    Raises:
        ValueError: If validation fails.
    """
    if role == "student":
        if not department_id:
            raise ValueError("departmentId is required for student role")
        if subject_ids:
            raise ValueError("subjectIds should be empty for student role")

    elif role == "staff":
        if not subject_ids:
            raise ValueError("subjectIds is required for staff role")
        # department_id is optional but recommended for staff

    elif role == "admin":
        if subject_ids:
            raise ValueError("subjectIds should be empty for admin role")

    else:
        raise ValueError(f"Invalid role: {role}")


def validate_status_transition(
    old_status: typing.Literal["active", "disabled"],
    new_status: typing.Literal["active", "disabled"],
    current_user_role: typing.Literal["admin", "staff", "student"],
) -> None:
    """Validate if a status change is allowed.

    Args:
        old_status: Current status.
        new_status: Requested status.
        current_user_role: Role of the actor performing the change.

    Raises:
        ValueError: If transition is not allowed.
    """
    if current_user_role != "admin":
        raise ValueError("Only admins can change user status")

    if old_status == new_status:
        raise ValueError("New status must be different from current status")


def normalize_user_data(data: dict) -> dict:
    """Normalize user data before saving to Firestore.

    Args:
        data: Raw user data.

    Returns:
        dict: Normalized user data.
    """
    normalized = data.copy()

    if "status" not in normalized:
        normalized["status"] = "active"

    if "subjectIds" not in normalized or normalized["subjectIds"] is None:
        normalized["subjectIds"] = []

    if "departmentId" not in normalized:
        normalized["departmentId"] = None

    if "_v" not in normalized:
        normalized["_v"] = 1

    if isinstance(normalized.get("subjectIds"), tuple):
        normalized["subjectIds"] = list(normalized["subjectIds"])

    return normalized
