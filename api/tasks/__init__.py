"""
============================================================================
FILE: __init__.py
LOCATION: api/tasks/__init__.py
============================================================================

PURPOSE:
    Package initialization for the document processing tasks module.
    Exports Celery tasks for async knowledge graph processing.

EXPORTS:
    - process_document_task: Single document processing Celery task
    - process_batch_task: Batch document processing Celery task
    - get_task_progress: Helper to poll task progress
    - cancel_task: Helper to cancel running tasks
    - ProcessingState: Enum of task states
    - app: Celery application instance

USAGE:
    from api.tasks import process_document_task, app

    # Dispatch task
    result = process_document_task.delay(doc_id, module_id, user_id)

    # Get progress
    from api.tasks import get_task_progress
    progress = get_task_progress(result.id)

    # Start worker
    # celery -A api.tasks worker -l info -Q kg_processing
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
