"""
============================================================================
FILE: __init__.py
LOCATION: api/hierarchy/__init__.py
============================================================================

PURPOSE:
    Package initializer for the hierarchy HTTP endpoints module.

ROLE IN PROJECT:
    Exports the hierarchy router and all Pydantic response models for
    inclusion in main.py. Provides REST APIs for navigating the academic
    hierarchy (departments, semesters, subjects, modules).

KEY COMPONENTS:
    - hierarchy_router: FastAPI router with /hierarchy prefix endpoints
    - DepartmentResponse, SemesterResponse, SubjectResponse, ModuleHierarchyResponse
    - DepartmentListResponse, SemesterListResponse, SubjectListResponse, ModuleListResponse

DEPENDENCIES:
    - External: None
    - Internal: api/hierarchy/router.py, api/hierarchy/models.py

USAGE:
    from api.hierarchy import hierarchy_router
    app.include_router(hierarchy_router, prefix="/api/v1")
============================================================================
"""
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
