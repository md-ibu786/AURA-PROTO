"""
============================================================================
FILE: __init__.py
LOCATION: api/tasks/__init__.py
============================================================================

PURPOSE:
    Package initialization for the document processing tasks module.

ROLE IN PROJECT:
    Exposes Celery tasks for asynchronous knowledge graph processing to the
    rest of the API. Acts as the public interface for the tasks sub-package,
    re-exporting task functions and helpers from document_processing_tasks.

KEY COMPONENTS:
    - process_document_task: Celery task for single document KG processing
    - process_batch_task: Celery task for batch document KG processing
    - get_task_progress: Helper to poll task progress by task ID
    - cancel_task: Helper to cancel a running task
    - ProcessingState: Enum of task processing states
    - app: Celery application instance

DEPENDENCIES:
    - External: celery
    - Internal: api/tasks/document_processing_tasks.py

USAGE:
    from api.tasks import process_document_task, app
    result = process_document_task.delay(doc_id, module_id, user_id)
    # Start worker: celery -A api.tasks worker -l info -Q kg_processing
============================================================================
"""

from .document_processing_tasks import (
    process_document_task,
    process_batch_task,
    get_task_progress,
    cancel_task,
    ProcessingState,
    app,
)

__all__ = [
    "process_document_task",
    "process_batch_task",
    "get_task_progress",
    "cancel_task",
    "ProcessingState",
    "app",
]

__version__ = "1.0.0"
