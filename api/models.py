"""
============================================================================
FILE: models.py
LOCATION: api/models.py
============================================================================

PURPOSE:
    Pydantic models for Firestore user schema and API inputs

ROLE IN PROJECT:
    Centralizes user schema definitions for consistent validation
    Shared by auth utilities and user management endpoints

KEY COMPONENTS:
    - FirestoreUser: Canonical Firestore user document model
    - CreateUserInput: Input model for user creation
    - UpdateUserInput: Input model for user updates

DEPENDENCIES:
    - External: pydantic
    - Internal: None

USAGE:
    from api.models import FirestoreUser, CreateUserInput, UpdateUserInput
============================================================================
"""

import datetime
import typing

import pydantic


UserRole = typing.Literal["admin", "staff", "student"]
UserStatus = typing.Literal["active", "disabled"]


class FirestoreUser(pydantic.BaseModel):
    """Represents a user document in Firestore."""

    model_config = pydantic.ConfigDict(populate_by_name=True)

    uid: str = pydantic.Field(..., description="Firebase Auth UID")
    email: str = pydantic.Field(..., description="User email address")
    displayName: typing.Optional[str] = pydantic.Field(
        None,
        description="User display name",
    )
    role: UserRole = pydantic.Field(..., description="User role")
    status: UserStatus = pydantic.Field(
        "active",
        description="Account status",
    )
    departmentId: typing.Optional[str] = pydantic.Field(
        None,
        description="Department ID (required for students)",
    )
    subjectIds: list[str] = pydantic.Field(
        default_factory=list,
        description="Assigned subject IDs (required for staff)",
    )
    createdAt: str = pydantic.Field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat(),
        description="ISO 8601 creation time",
    )
    updatedAt: str = pydantic.Field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat(),
        description="ISO 8601 update time",
    )
    schemaVersion: int = pydantic.Field(
        1,
        alias="_v",
        description="Schema version",
    )


class CreateUserInput(pydantic.BaseModel):
    """Input for creating a new user."""

    model_config = pydantic.ConfigDict(populate_by_name=True)

    email: str
    password: str
    displayName: typing.Optional[str] = pydantic.Field(
        None,
        validation_alias=pydantic.AliasChoices("displayName", "display_name"),
    )
    role: UserRole
    status: UserStatus = pydantic.Field(
        "active",
        validation_alias=pydantic.AliasChoices("status"),
    )
    departmentId: typing.Optional[str] = pydantic.Field(
        None,
        validation_alias=pydantic.AliasChoices("departmentId", "department_id"),
    )
    subjectIds: list[str] = pydantic.Field(
        default_factory=list,
        validation_alias=pydantic.AliasChoices("subjectIds", "subject_ids"),
    )

    @pydantic.model_validator(mode="after")
    def validate_role_constraints(self) -> "CreateUserInput":
        """Validate role-specific requirements.

        Args:
            self: Model instance.

        Returns:
            CreateUserInput: Validated instance.

        Raises:
            ValueError: If role constraints fail.
        """
        if self.role == "student" and not self.departmentId:
            raise ValueError("departmentId is required for student role")
        if self.role == "staff" and not self.subjectIds:
            raise ValueError("subjectIds is required for staff role")
        if self.role in ("admin", "student") and self.subjectIds:
            raise ValueError(
                "subjectIds should be empty for admin or student role",
            )
        return self


class UpdateUserInput(pydantic.BaseModel):
    """Input for updating an existing user."""

    model_config = pydantic.ConfigDict(populate_by_name=True)

    email: typing.Optional[str] = None
    displayName: typing.Optional[str] = pydantic.Field(
        None,
        validation_alias=pydantic.AliasChoices("displayName", "display_name"),
    )
    role: typing.Optional[UserRole] = None
    status: typing.Optional[UserStatus] = pydantic.Field(
        None,
        validation_alias=pydantic.AliasChoices("status"),
    )
    departmentId: typing.Optional[str] = pydantic.Field(
        None,
        validation_alias=pydantic.AliasChoices("departmentId", "department_id"),
    )
    subjectIds: typing.Optional[list[str]] = pydantic.Field(
        None,
        validation_alias=pydantic.AliasChoices("subjectIds", "subject_ids"),
    )
