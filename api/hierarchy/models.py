# models.py
# =========================
#
# Pydantic models for hierarchy API responses.
# Defines response schemas for department, semester, subject, and module endpoints.
# Ensures consistent response format across all hierarchy navigation APIs.
# Used by hierarchy router and consumed by AURA-CHAT proxy endpoints.
#
# Features:
# ----------
# - Typed response models for all hierarchy levels
# - Pagination support via list response models
# - Field descriptions for API documentation
# - Example schemas for Swagger UI
#
# Classes/Functions:
# ------------------
# - DepartmentResponse: Single department response
# - SemesterResponse: Single semester response
# - SubjectResponse: Single subject response
# - ModuleHierarchyResponse: Single module response (hierarchy context)
# - DepartmentListResponse: List of departments with total count
# - SemesterListResponse: List of semesters with total count
# - SubjectListResponse: List of subjects with total count
# - ModuleListResponse: List of modules with total count
#
# @see: router.py - FastAPI router using these models
# @see: api/hierarchy.py - Data access functions returning raw dicts
# @note: Response models wrap items in list format with total count
# @note: Department ID used as top-level root collection in Firestore

from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from datetime import datetime


class DepartmentResponse(BaseModel):
    """Response model for a single department."""
    id: str = Field(..., description="Department ID")
    code: str = Field(..., description="Department code (e.g., 'CS', 'IT')")
    name: str = Field(..., description="Department display name")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "dept_cs_001",
                "code": "CS",
                "name": "Computer Science"
            }
        }
    )


class SemesterResponse(BaseModel):
    """Response model for a single semester."""
    id: str = Field(..., description="Semester ID")
    name: str = Field(..., description="Semester display name")
    year: Optional[int] = Field(None, description="Academic year")
    semester_number: int = Field(..., description="Semester number (1-8)")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "sem_2026_s1",
                "name": "Semester 1",
                "year": 2026,
                "semester_number": 1
            }
        }
    )


class SubjectResponse(BaseModel):
    """Response model for a single subject."""
    id: str = Field(..., description="Subject ID")
    code: str = Field(..., description="Subject code (e.g., 'CS201')")
    name: str = Field(..., description="Subject display name")
    module_count: int = Field(0, description="Number of modules in this subject")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "subj_cs201",
                "code": "CS201",
                "name": "Data Structures",
                "module_count": 5
            }
        }
    )


class ModuleHierarchyResponse(BaseModel):
    """Response model for a single module (in hierarchy context)."""
    id: str = Field(..., description="Module ID")
    code: str = Field(..., description="Module code")
    name: str = Field(..., description="Module display name")
    description: Optional[str] = Field(None, description="Module description")
    document_count: int = Field(0, description="Number of documents in this module")
    module_number: Optional[int] = Field(None, description="Module ordering number")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "mod_cs201_m01",
                "code": "M01",
                "name": "Introduction to Arrays",
                "description": "Basic array concepts and operations",
                "document_count": 3,
                "module_number": 1
            }
        }
    )


# List response models with pagination info

class DepartmentListResponse(BaseModel):
    """Response model for list of departments."""
    items: List[DepartmentResponse] = Field(default_factory=list, description="List of departments")
    total: int = Field(..., description="Total count of departments")
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {"id": "dept_cs_001", "code": "CS", "name": "Computer Science"}
                ],
                "total": 1
            }
        }
    )


class SemesterListResponse(BaseModel):
    """Response model for list of semesters."""
    items: List[SemesterResponse] = Field(default_factory=list, description="List of semesters")
    total: int = Field(..., description="Total count of semesters")


class SubjectListResponse(BaseModel):
    """Response model for list of subjects."""
    items: List[SubjectResponse] = Field(default_factory=list, description="List of subjects")
    total: int = Field(..., description="Total count of subjects")


class ModuleListResponse(BaseModel):
    """Response model for list of modules."""
    items: List[ModuleHierarchyResponse] = Field(default_factory=list, description="List of modules")
    total: int = Field(..., description="Total count of modules")
