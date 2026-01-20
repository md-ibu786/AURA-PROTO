# models.py
# Pydantic models for M2KG Module CRUD operations

# Defines request/response schemas for Module API endpoints.
# ModuleStatus enum controls module lifecycle (draft → published → archived).
# Module ID format: {code}_{year}_S{semester} (e.g., CS201_2026_S1)

# @see: service.py - Uses these models for Firestore operations
# @see: router.py - Uses these models for FastAPI validation
# @note: This is for M2KG Modules (course units), NOT hierarchy modules

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ModuleStatus(str, Enum):
    """Module lifecycle status for KG publishing workflow."""
    DRAFT = "draft"           # Initial state, not visible to students
    PUBLISHED = "published"   # Published to students, KG processed
    ARCHIVED = "archived"     # Soft-deleted, hidden from all views


class ModuleCreate(BaseModel):
    """Request model for creating a module."""
    name: str = Field(..., min_length=1, max_length=200, description="Module display name")
    code: str = Field(..., min_length=1, max_length=50, description="Module code (e.g., CS201)")
    description: Optional[str] = Field(None, description="Module description")
    year: int = Field(..., ge=2000, le=2100, description="Academic year")
    semester: int = Field(..., ge=1, le=4, description="Semester number (1-4)")


class ModuleUpdate(BaseModel):
    """Request model for updating a module."""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    status: Optional[ModuleStatus] = None


class ModuleResponse(BaseModel):
    """Response model for module data."""
    id: str
    name: str
    code: str
    description: Optional[str]
    year: int
    semester: int
    status: ModuleStatus
    document_count: int
    created_by: str
    created_at: datetime
    updated_at: datetime

    class Config:
        # Allow datetime serialization from Firestore Timestamp
        from_attributes = True


class ModuleListResponse(BaseModel):
    """Response for listing modules with pagination."""
    modules: List[ModuleResponse]
    total: int
    page: int
    page_size: int


# ============================================================================
# PER-DOCUMENT KG STATUS MODELS
# ============================================================================

class KGStatus(str, Enum):
    """Per-document KG processing status for incremental processing."""
    PENDING = "pending"       # Not yet processed
    PROCESSING = "processing" # Currently being processed
    READY = "ready"           # Successfully processed
    FAILED = "failed"         # Processing failed


class DocumentKGStatus(BaseModel):
    """Per-document KG status response."""
    document_id: str
    module_id: str
    file_name: str
    kg_status: KGStatus
    kg_processed_at: Optional[datetime] = None
    kg_error: Optional[str] = None
    chunk_count: Optional[int] = None
    entity_count: Optional[int] = None


class BatchProcessingRequest(BaseModel):
    """Request for batch document processing."""
    file_ids: List[str] = Field(..., description="List of document IDs to process")
    module_id: str = Field(..., description="Module ID for tagging all created nodes")
    options: Optional[Dict[str, Any]] = Field(None, description="Optional processing options")


class BatchProcessingResponse(BaseModel):
    """Response for batch processing request."""
    task_id: str
    status_url: str
    documents_queued: int
    documents_skipped: int  # Already processed (idempotency)
    message: str


class ProcessingQueueItem(BaseModel):
    """Document currently in processing queue."""
    document_id: str
    module_id: str
    file_name: str
    status: KGStatus
    progress: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    step: str = Field(..., description="Current processing step (parsing, chunking, etc.)")
    started_at: datetime
