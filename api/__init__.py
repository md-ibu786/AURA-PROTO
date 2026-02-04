"""
============================================================================
FILE: __init__.py
LOCATION: api/__init__.py
============================================================================

PURPOSE:
    Package initialization for AURA-NOTES-MANAGER API module.
    Exports core components and tasks.

EXPORTS:
    - KnowledgeGraphProcessor: Core KG processing class
    - GeminiClient: Gemini API client
    - Entity, Relationship, Chunk: Data classes
    - EntityType: Entity type enum
    - process_document_simple: Convenience processing function
    - process_document_task, process_batch_task: Celery tasks
    - All configuration constants

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

__all__ = [
    *_KG_EXPORTS,
    *_TASK_EXPORTS,
]

# M2KG Module exports
from .modules import (
    ModuleService,
    ModuleCreate,
    ModuleUpdate,
    ModuleResponse,
    ModuleListResponse,
    ModuleStatus,
    modules_router,
)

__all__ += [
    "ModuleService",
    "ModuleCreate",
    "ModuleUpdate",
    "ModuleResponse",
    "ModuleListResponse",
    "ModuleStatus",
    "modules_router",
]
