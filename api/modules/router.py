# router.py
# FastAPI router for M2KG Module CRUD and publishing endpoints

# Provides REST API endpoints for module management by staff users.
# All endpoints are prefixed with /modules and tagged for Swagger UI grouping.
# Uses dependency injection for ModuleService and ModulePublisher.

# @see: service.py - Business logic layer
# @see: publishing.py - Publishing workflow
# @see: models.py - Request/response Pydantic schemas
# @note: Endpoints use /api/v1/modules prefix when mounted in main.py

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List, Dict, Any

try:
    from .service import ModuleService
    from .publishing import ModulePublisher
    from .models import (
        ModuleCreate, ModuleUpdate, ModuleResponse,
        ModuleListResponse, ModuleStatus
    )
except ImportError:
    from service import ModuleService
    from publishing import ModulePublisher
    from models import (
        ModuleCreate, ModuleUpdate, ModuleResponse,
        ModuleListResponse, ModuleStatus
    )

router = APIRouter(prefix="/modules", tags=["M2KG Modules"])


def get_module_service() -> ModuleService:
    """Dependency for getting ModuleService instance."""
    return ModuleService()


def get_module_publisher() -> ModulePublisher:
    """Dependency for getting ModulePublisher instance."""
    return ModulePublisher()


@router.post("", response_model=ModuleResponse, status_code=status.HTTP_201_CREATED)
def create_module(
    module_data: ModuleCreate,
    user_id: str = Query("staff_user_001", description="Staff user ID (from auth)"),
    service: ModuleService = Depends(get_module_service)
):
    """
    Create a new M2KG module.
    
    Module ID is generated as: {code}_{year}_S{semester}
    Initial status is 'draft'.
    """
    try:
        module = service.create(user_id, module_data)
        return module
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("", response_model=ModuleListResponse)
def list_modules(
    status_filter: Optional[ModuleStatus] = Query(None, alias="status", description="Filter by status"),
    year: Optional[int] = Query(None, description="Filter by year"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    service: ModuleService = Depends(get_module_service)
):
    """
    List M2KG modules with optional filters and pagination.
    
    Returns paginated list of modules sorted by creation date (newest first).
    """
    result = service.list(
        status=status_filter,
        year=year,
        page=page,
        page_size=page_size
    )
    return result


@router.get("/{module_id}", response_model=ModuleResponse)
def get_module(
    module_id: str,
    service: ModuleService = Depends(get_module_service)
):
    """
    Get a single M2KG module by ID.
    
    Module ID format: {code}_{year}_S{semester} (e.g., CS201_2026_S1)
    """
    module = service.get_by_id(module_id)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_id}' not found"
        )
    return module


@router.put("/{module_id}", response_model=ModuleResponse)
def update_module(
    module_id: str,
    update_data: ModuleUpdate,
    service: ModuleService = Depends(get_module_service)
):
    """
    Update an M2KG module.
    
    Only provided fields are updated. Status can be changed via this endpoint.
    """
    module = service.update(module_id, update_data)
    if not module:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_id}' not found"
        )
    return module


@router.delete("/{module_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_module(
    module_id: str,
    service: ModuleService = Depends(get_module_service)
):
    """
    Delete (archive) an M2KG module.
    
    This is a soft delete - status is changed to 'archived'.
    """
    success = service.delete(module_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Module '{module_id}' not found"
        )
    return None


@router.post("/{module_id}/publish", response_model=ModuleResponse)
def publish_module(
    module_id: str,
    staff_id: str = Query("staff_user_001", description="Staff user ID (from auth)"),
    publisher: ModulePublisher = Depends(get_module_publisher)
):
    """
    Publish an M2KG module to students.
    
    Workflow:
    1. Validates module exists and is in DRAFT status
    2. Updates status to PUBLISHED
    3. Adds to published_modules collection (for AURA-CHAT)
    4. Logs audit trail
    
    Returns the updated module with published_at timestamp.
    """
    try:
        return publisher.publish(module_id, staff_id)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/{module_id}/unpublish", response_model=ModuleResponse)
def unpublish_module(
    module_id: str,
    reason: Optional[str] = Query(None, description="Reason for unpublishing"),
    staff_id: str = Query("staff_user_001", description="Staff user ID (from auth)"),
    publisher: ModulePublisher = Depends(get_module_publisher)
):
    """
    Unpublish a module (hide from students).
    
    Changes status from PUBLISHED back to DRAFT.
    Removes from published_modules collection.
    """
    try:
        return publisher.unpublish(module_id, staff_id, reason)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{module_id}/audit-log")
def get_module_audit_log(
    module_id: str,
    limit: int = Query(50, ge=1, le=500, description="Max entries to return"),
    publisher: ModulePublisher = Depends(get_module_publisher)
) -> List[Dict[str, Any]]:
    """
    Get audit log for a module.
    
    Returns list of audit entries (publish, unpublish, etc.) sorted by newest first.
    """
    return publisher.get_audit_log(module_id, limit)


@router.get("/published/all")
def get_all_published_modules(
    publisher: ModulePublisher = Depends(get_module_publisher)
) -> List[Dict[str, Any]]:
    """
    Get all published modules (for AURA-CHAT).
    
    Returns list of modules with student_access=True.
    """
    return publisher.get_published_modules()

