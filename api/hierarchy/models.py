"""
============================================================================
FILE: models.py
LOCATION: api/hierarchy/models.py
============================================================================

PURPOSE:
    Pydantic response models for the hierarchy navigation API.

ROLE IN PROJECT:
    Defines typed response schemas for all hierarchy levels (department,
    semester, subject, module). Ensures consistent response format across
    all hierarchy navigation endpoints and provides Swagger UI examples.

KEY COMPONENTS:
    - DepartmentResponse / DepartmentListResponse: Department schemas
    - SemesterResponse / SemesterListResponse: Semester schemas
    - SubjectResponse / SubjectListResponse: Subject schemas
    - ModuleHierarchyResponse / ModuleListResponse: Module schemas

DEPENDENCIES:
    - External: pydantic, typing
    - Internal: None

USAGE:
    from api.hierarchy.models import DepartmentListResponse
    return DepartmentListResponse(items=[...], total=len(items))
============================================================================
"""
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


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
