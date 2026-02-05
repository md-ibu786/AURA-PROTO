# router.py
# =========================
#
# FastAPI router for hierarchy navigation HTTP endpoints.
# Exposes read-only hierarchy navigation as REST APIs for AURA-CHAT proxy.
# Uses existing hierarchy.py functions for Firestore data fetching.
# All endpoints return typed responses using hierarchy models.
#
# Features:
# ----------
# - Read-only hierarchy navigation APIs
# - Typed responses with Pydantic models
# - Query parameter filtering
# - Drill-down navigation (dept -> semester -> subject -> module)
#
# Classes/Functions:
# ------------------
# - router: FastAPI router with /hierarchy prefix
# - get_departments(): GET /hierarchy/departments - List all departments
# - get_semesters(): GET /hierarchy/semesters - List semesters by department
# - get_subjects(): GET /hierarchy/subjects - List subjects by semester
# - get_modules(): GET /hierarchy/modules - List modules by subject
#
# @see: api/hierarchy.py - Data access functions (get_all_departments, etc.)
# @see: models.py - Pydantic response schemas
# @note: Mount with prefix /api/v1 in main.py (endpoints become /api/v1/hierarchy/...)

from typing import Optional
from fastapi import APIRouter, HTTPException, status, Query
import importlib.util
import os

# Import hierarchy data access functions from api/hierarchy.py file
# (not from api/hierarchy/ package which would cause circular imports)
hierarchy_file_path = os.path.join(os.path.dirname(__file__), "..", "hierarchy.py")
hierarchy_file = importlib.util.spec_from_file_location(
    "hierarchy_functions",
    hierarchy_file_path
)
hierarchy_module = importlib.util.module_from_spec(hierarchy_file)
hierarchy_file.loader.exec_module(hierarchy_module)

get_all_departments = hierarchy_module.get_all_departments
get_semesters_by_department = hierarchy_module.get_semesters_by_department
get_subjects_by_semester = hierarchy_module.get_subjects_by_semester
get_modules_by_subject = hierarchy_module.get_modules_by_subject

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

router = APIRouter(prefix="/hierarchy", tags=["Hierarchy Navigation"])


@router.get("/departments", response_model=DepartmentListResponse)
def get_departments() -> DepartmentListResponse:
    """
    Get all departments.
    
    Returns a list of all top-level departments for navigation.
    Used as the first step in hierarchy drill-down.
    """
    raw_departments = get_all_departments()
    
    items = [
        DepartmentResponse(
            id=dept.get("id", ""),
            code=dept.get("code", dept.get("id", "")[:4].upper()),  # Fallback to ID prefix
            name=dept.get("name", dept.get("label", "Unknown"))
        )
        for dept in raw_departments
    ]
    
    return DepartmentListResponse(items=items, total=len(items))


@router.get("/semesters", response_model=SemesterListResponse)
def get_semesters(
    department_id: str = Query(..., description="Department ID to filter semesters")
) -> SemesterListResponse:
    """
    Get semesters for a specific department.
    
    Returns a list of semesters under the specified department.
    Used as the second step in hierarchy drill-down.
    """
    raw_semesters = get_semesters_by_department(department_id)
    
    if not raw_semesters:
        # Return empty list, not 404 - department may have no semesters yet
        return SemesterListResponse(items=[], total=0)
    
    items = [
        SemesterResponse(
            id=sem.get("id", ""),
            name=sem.get("name", sem.get("label", f"Semester {sem.get('semester_number', '')}")),
            year=sem.get("year"),
            semester_number=sem.get("semester_number", 0)
        )
        for sem in raw_semesters
    ]
    
    return SemesterListResponse(items=items, total=len(items))


@router.get("/subjects", response_model=SubjectListResponse)
def get_subjects(
    department_id: str = Query(..., description="Department ID (for context)"),
    semester_id: str = Query(..., description="Semester ID to filter subjects")
) -> SubjectListResponse:
    """
    Get subjects for a specific semester.
    
    Returns a list of subjects under the specified semester.
    Department ID is passed for context/validation but filtering uses semester_id.
    Used as the third step in hierarchy drill-down.
    """
    # Note: get_subjects_by_semester now supports optional department_id for direct path access
    raw_subjects = get_subjects_by_semester(semester_id, department_id=department_id)
    
    if not raw_subjects:
        return SubjectListResponse(items=[], total=0)
    
    items = [
        SubjectResponse(
            id=subj.get("id", ""),
            code=subj.get("code", subj.get("id", "")[:6].upper()),
            name=subj.get("name", subj.get("label", "Unknown Subject")),
            module_count=subj.get("module_count", 0)
        )
        for subj in raw_subjects
    ]
    
    return SubjectListResponse(items=items, total=len(items))


@router.get("/modules", response_model=ModuleListResponse)
def get_modules(
    department_id: str = Query(..., description="Department ID (for context)"),
    semester_id: str = Query(..., description="Semester ID (for context)"),
    subject_id: str = Query(..., description="Subject ID to filter modules")
) -> ModuleListResponse:
    """
    Get modules for a specific subject.
    
    Returns a list of modules under the specified subject.
    Department ID and Semester ID are passed for context/validation.
    Used as the final step in hierarchy drill-down.
    """
    # Note: get_modules_by_subject now supports optional context for direct path access
    raw_modules = get_modules_by_subject(subject_id, department_id=department_id, semester_id=semester_id)
    
    if not raw_modules:
        return ModuleListResponse(items=[], total=0)
    
    items = [
        ModuleHierarchyResponse(
            id=mod.get("id", ""),
            code=mod.get("code", f"M{mod.get('module_number', 0):02d}"),
            name=mod.get("name", mod.get("label", "Unknown Module")),
            description=mod.get("description"),
            document_count=mod.get("document_count", 0),
            module_number=mod.get("module_number")
        )
        for mod in raw_modules
    ]
    
    return ModuleListResponse(items=items, total=len(items))
