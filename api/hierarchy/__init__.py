# hierarchy/__init__.py
# Package init for hierarchy HTTP endpoints

# Exports hierarchy router for use in main.py.
# Provides REST APIs for hierarchical navigation (departments, semesters, subjects, modules).

# @see: hierarchy/router.py - FastAPI router with endpoints
# @see: hierarchy/models.py - Pydantic response schemas
# @note: Mount with prefix /api/v1 in main.py

from .router import router as hierarchy_router
from .models import (
    DepartmentResponse,
    SemesterResponse,
    SubjectResponse,
    ModuleHierarchyResponse,
    DepartmentListResponse,
    SemesterListResponse,
    SubjectListResponse,
    ModuleListResponse,
)

__all__ = [
    "hierarchy_router",
    "DepartmentResponse",
    "SemesterResponse",
    "SubjectResponse",
    "ModuleHierarchyResponse",
    "DepartmentListResponse",
    "SemesterListResponse",
    "SubjectListResponse",
    "ModuleListResponse",
]
