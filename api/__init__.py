"""
============================================================================
FILE: __init__.py
LOCATION: api/__init__.py
============================================================================

PURPOSE:
    Package initialization for the AURA-NOTES-MANAGER API module.

ROLE IN PROJECT:
    Acts as the top-level public interface for the api package. Re-exports
    core KG processing classes, Celery tasks, and module service components
    so consumers can import directly from `api` without knowing sub-module
    locations.

KEY COMPONENTS:
    - KnowledgeGraphProcessor: Core class for document KG processing
    - GeminiClient: Gemini API client for embeddings and entity extraction
    - process_document_task / process_batch_task: Celery async tasks
    - ModuleService / modules_router: Module management service and router

DEPENDENCIES:
    - External: celery
    - Internal: api/kg_processor.py, api/tasks/__init__.py, api/modules/

USAGE:
    from api import KnowledgeGraphProcessor
    from api.tasks import process_document_task
============================================================================
"""

# Core processor exports
_KG_EXPORTS = []
try:
    from .kg_processor import (
        KnowledgeGraphProcessor,
        GeminiClient,
        Entity,
        Relationship,
        Chunk,
        EntityType,
        ProcessingProgress,
        process_document_simple,
        # Entity extraction constants
        ENTITY_EXTRACTION_PROMPT,
        ENTITY_BATCH_SIZE,
        ENTITY_MAX_PARALLEL,
        ENTITY_DEDUP_SIMILARITY_THRESHOLD,
        ENTITY_RELATIONSHIP_TYPES,
        # Chunking constants
        CHUNK_SIZE,
        CHUNK_OVERLAP_SIZE,
        MIN_CHUNK_SIZE,
        MAX_CHUNK_SIZE,
    )

    _ = (
        KnowledgeGraphProcessor,
        GeminiClient,
        Entity,
        Relationship,
        Chunk,
        EntityType,
        ProcessingProgress,
        process_document_simple,
        ENTITY_EXTRACTION_PROMPT,
        ENTITY_BATCH_SIZE,
        ENTITY_MAX_PARALLEL,
        ENTITY_DEDUP_SIMILARITY_THRESHOLD,
        ENTITY_RELATIONSHIP_TYPES,
        CHUNK_SIZE,
        CHUNK_OVERLAP_SIZE,
        MIN_CHUNK_SIZE,
        MAX_CHUNK_SIZE,
    )

    _KG_EXPORTS = [
        "KnowledgeGraphProcessor",
        "GeminiClient",
        "Entity",
        "Relationship",
        "Chunk",
        "EntityType",
        "ProcessingProgress",
        "process_document_simple",
        "ENTITY_EXTRACTION_PROMPT",
        "ENTITY_BATCH_SIZE",
        "ENTITY_MAX_PARALLEL",
        "ENTITY_DEDUP_SIMILARITY_THRESHOLD",
        "ENTITY_RELATIONSHIP_TYPES",
        "CHUNK_SIZE",
        "CHUNK_OVERLAP_SIZE",
        "MIN_CHUNK_SIZE",
        "MAX_CHUNK_SIZE",
    ]
except ImportError:
    _KG_EXPORTS = []

# Task exports
_TASK_EXPORTS = []
try:
    from .tasks import (
        process_document_task,
        process_batch_task,
        get_task_progress,
        cancel_task,
        ProcessingState,
        app as celery_app,
    )

    _ = (
        process_document_task,
        process_batch_task,
        get_task_progress,
        cancel_task,
        ProcessingState,
        celery_app,
    )

    _TASK_EXPORTS = [
        "process_document_task",
        "process_batch_task",
        "get_task_progress",
        "cancel_task",
        "ProcessingState",
        "celery_app",
    ]
except ImportError:
    _TASK_EXPORTS = []

_MODULE_EXPORTS = []
try:
    from .modules import (
        ModuleService,
        ModuleCreate,
        ModuleUpdate,
        ModuleResponse,
        ModuleListResponse,
        ModuleStatus,
        modules_router,
    )

    _ = (
        ModuleService,
        ModuleCreate,
        ModuleUpdate,
        ModuleResponse,
        ModuleListResponse,
        ModuleStatus,
        modules_router,
    )

    _MODULE_EXPORTS = [
        "ModuleService",
        "ModuleCreate",
        "ModuleUpdate",
        "ModuleResponse",
        "ModuleListResponse",
        "ModuleStatus",
        "modules_router",
    ]
except ImportError:
    _MODULE_EXPORTS = []

__all__ = (
    tuple(_KG_EXPORTS) +
    tuple(_TASK_EXPORTS) +
    tuple(_MODULE_EXPORTS)
)
