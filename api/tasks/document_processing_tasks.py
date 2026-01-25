"""
============================================================================
FILE: document_processing_tasks.py
LOCATION: api/tasks/document_processing_tasks.py
============================================================================

PURPOSE:
    Celery tasks for async, non-blocking document processing with progress
    tracking. Enables background KG processing without blocking API requests.

ROLE IN PROJECT:
    Part of Phase 2 (Knowledge Graph Processor) - provides async task queue
    integration for the KnowledgeGraphProcessor. Tasks are dispatched from
    API endpoints and processed by Celery workers.

KEY COMPONENTS:
    - Celery app instance configuration
    - process_document_task: Single document processing with retry
    - process_batch_task: Batch document processing
    - Progress tracking via task state
    - Time limits and retry policies

DEPENDENCIES:
    - External: celery, redis
    - Internal: kg_processor (KnowledgeGraphProcessor)

USAGE:
    # Start worker
    celery -A api.tasks worker -l info

    # Dispatch task
    from api.tasks import process_document_task
    result = process_document_task.delay(doc_id, module_id, user_id)

    # Check progress
    state, meta = result.state, result.info
============================================================================
"""

import os
import sys
import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum

# Celery imports
from celery import Celery, Task
from celery.exceptions import SoftTimeLimitExceeded, MaxRetriesExceededError

# Add parent directories to path for imports
_current_dir = os.path.dirname(__file__)
_api_dir = os.path.dirname(_current_dir)
_root_dir = os.path.dirname(_api_dir)
sys.path.insert(0, _api_dir)
sys.path.insert(0, _root_dir)

# Import processor
from kg_processor import KnowledgeGraphProcessor, process_document_simple
from logging_config import logger

# Import Firestore for status updates
try:
    from config import db
except ImportError:
    from api.config import db

from google.cloud.firestore import FieldFilter


# ============================================================================
# FIRESTORE STATUS UPDATE HELPER
# ============================================================================

def _find_note_by_id(document_id: str):
    """Find a note document by ID using collection_group query.

    Notes are stored in nested subcollections: modules/{module_id}/notes/{note_id}
    Use collection_group to find them regardless of their parent module.

    Args:
        document_id: The note document ID to find

    Returns:
        The note document reference if found, None otherwise
    """
    try:
        # Use collection_group to find note in any modules subcollection
        notes = list(
            db.collection_group("notes")
            .filter(FieldFilter("__name__", ">=", document_id))
            .filter(FieldFilter("__name__", "<=", document_id + "\uf8ff"))
            .limit(1)
            .stream()
        )
        if notes:
            return notes[0].reference
        return None
    except Exception as e:
        logger.error(f"Error finding note {document_id}: {e}")
        return None


def update_document_status(
    document_id: str,
    status: str,
    error: Optional[str] = None,
    progress: Optional[int] = None,
    step: Optional[str] = None,
    chunk_count: Optional[int] = None,
    entity_count: Optional[int] = None
):
    """
    Update document KG status in Firestore.

    Args:
        document_id: Firestore document ID
        status: KG status (pending, processing, ready, failed)
        error: Error message if status is failed
        progress: Progress percentage (0-100)
        step: Current processing step (parsing, chunking, etc.)
        chunk_count: Number of chunks created (for ready status)
        entity_count: Number of entities extracted (for ready status)
    """
    # Find the note in nested subcollections
    doc_ref = _find_note_by_id(document_id)

    if doc_ref is None:
        logger.error(f"No document found to update: {document_id}")
        return

    update_data = {
        "kg_status": status,
        "updated_at": datetime.utcnow()
    }

    if error:
        update_data["kg_error"] = error
    if progress is not None:
        update_data["kg_progress"] = progress
    if step:
        update_data["kg_step"] = step
    if status == "processing":
        update_data["kg_started_at"] = datetime.utcnow()
    if status == "ready":
        update_data["kg_processed_at"] = datetime.utcnow()
        if chunk_count is not None:
            update_data["kg_chunk_count"] = chunk_count
        if entity_count is not None:
            update_data["kg_entity_count"] = entity_count

    try:
        doc_ref.update(update_data)
        logger.debug(f"Updated KG status for document {document_id}: {status}")
    except Exception as e:
        logger.error(f"Failed to update KG status for document {document_id}: {e}")

# ============================================================================
# CELERY APP CONFIGURATION
# ============================================================================

# Redis broker configuration
# Strip whitespace to avoid connection issues with trailing spaces
REDIS_HOST = os.environ.get('REDIS_HOST', '127.0.0.1').strip()
REDIS_PORT = int(os.environ.get('REDIS_PORT', 6379))
REDIS_DB = int(os.environ.get('REDIS_DB', 0))

# Log Redis config for debugging
logger.info(f"Celery Redis config: host='{REDIS_HOST}', port={REDIS_PORT}, db={REDIS_DB}")

# Celery result backend (same Redis instance)
CELERY_RESULT_BACKEND = f'redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}'

# Create Celery app
app = Celery(
    'aura_notes_tasks',
    broker=CELERY_RESULT_BACKEND,
    backend=CELERY_RESULT_BACKEND,
    include=['api.tasks.document_processing_tasks']
)

# Celery configuration
app.conf.update(
    # Task serialization (JSON for structured data)
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # Timezone
    timezone='UTC',
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,           # Acknowledge after completion (not before)
    task_reject_on_worker_lost=True,  # Re-queue if worker dies
    worker_prefetch_multiplier=1,  # One task per worker at a time

    # Result settings (keep for 1 hour)
    result_expires=3600,
    task_track_started=True,       # Track when task starts

    # Task routing (optional - can be configured in worker)
    task_routes={
        'api.tasks.*': {'queue': 'kg_processing'},
    }
)


# ============================================================================
# PROCESSING STATES
# ============================================================================

class ProcessingState(str, Enum):
    """Task processing states for progress tracking."""
    PENDING = 'PENDING'
    RECEIVED = 'RECEIVED'
    PARSING = 'PARSING'              # 0-10%
    CHUNKING = 'CHUNKING'            # 10-30%
    EMBEDDING = 'EMBEDDING'          # 30-50%
    EXTRACTING = 'EXTRACTING'        # 50-70%
    STORING = 'STORING'              # 70-90%
    COMPLETED = 'COMPLETED'          # 100%
    FAILED = 'FAILED'
    RETRYING = 'RETRYING'


# ============================================================================
# BASE TASK CLASS
# ============================================================================

class KGProcessingTask(Task):
    """
    Base task class for knowledge graph processing tasks.

    Provides:
    - Shared processor initialization
    - Progress state updates
    - Consistent error handling
    """

    _processor = None

    @property
    def processor(self) -> KnowledgeGraphProcessor:
        """Lazy initialize the knowledge graph processor."""
        if self._processor is None:
            self._processor = KnowledgeGraphProcessor()
        return self._processor

    def update_progress(self, stage: str, progress: int, meta: Dict = None):
        """
        Update task progress state.

        Args:
            stage: Current processing stage name
            progress: Progress percentage (0-100)
            meta: Additional metadata to include
        """
        state_meta = {
            'stage': stage,
            'progress': progress,
            'started_at': getattr(self, '_start_time', None),
        }
        if meta:
            state_meta.update(meta)

        self.update_state(state=ProcessingState.PARSING.value if progress < 10 else
                         ProcessingState.CHUNKING.value if progress < 30 else
                         ProcessingState.EMBEDDING.value if progress < 50 else
                         ProcessingState.EXTRACTING.value if progress < 70 else
                         ProcessingState.STORING.value if progress < 90 else
                         ProcessingState.COMPLETED.value,
                         meta=state_meta)


# ============================================================================
# SINGLE DOCUMENT PROCESSING TASK
# ============================================================================

@app.task(
    bind=True,
    base=KGProcessingTask,
    name='api.tasks.process_document',
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=600,          # Max 10 minutes between retries
    retry_jitter=True,              # Add randomness to prevent thundering herd
    max_retries=5,
    acks_late=True,
    reject_on_worker_lost=True,
    time_limit=1800,                # 30 minutes hard limit
    soft_time_limit=1500,           # 25 minutes soft limit
    track_started=True
)
def process_document_task(
    self,
    document_id: str,
    module_id: str,
    user_id: str,
    file_path: str = None
) -> Dict[str, Any]:
    """
    Process a single document into a knowledge graph asynchronously.

    This task is IDEMPOTENT: running it multiple times with the same
    inputs produces the same result (MERGE semantics in Neo4j).

    Args:
        document_id: Unique identifier for the document
        module_id: Module ID for tagging all created nodes
        user_id: User who owns this document
        file_path: Optional path to document file (PDF/TXT)

    Returns:
        Dict containing:
        - success: Boolean indicating success/failure
        - document_id: The processed document ID
        - module_id: The module ID used
        - chunk_count: Number of chunks created
        - entity_count: Number of entities extracted
        - processing_time_seconds: Total processing time
        - error: Error message if failed

    Progress States:
        0-10%: PARSING - Extracting text from document
        10-30%: CHUNKING - Creating semantic chunks
        30-50%: EMBEDDING - Generating Gemini embeddings
        50-70%: EXTRACTING - Extracting entities with LLM
        70-90%: STORING - Saving to Neo4j
        100%: COMPLETED
    """
    task_logger = logging.getLogger(f'kg_task.{self.request.id}')

    # Record start time
    self._start_time = datetime.utcnow().isoformat()
    start_time = datetime.utcnow()

    task_logger.info(f"Starting document processing: doc={document_id}, module={module_id}")

    # Initial state update
    self.update_progress('received', 0, {
        'document_id': document_id,
        'module_id': module_id
    })

    try:
        # Validate inputs
        if not document_id:
            raise ValueError("document_id is required")
        if not module_id:
            raise ValueError("module_id is required")
        if not user_id:
            raise ValueError("user_id is required")

        # Idempotency check: skip if already processed
        # Find note in nested subcollections (modules/{id}/notes/{id})
        doc_ref = _find_note_by_id(document_id)
        if doc_ref is not None:
            doc = doc_ref.get()
            if doc.exists and doc.to_dict().get("kg_status") == "ready":
                task_logger.info(f"Document {document_id} already processed, skipping")
                return {
                    "document_id": document_id,
                    "status": "skipped",
                    "reason": "already_processed"
                }

        # Update Firestore status to PROCESSING
        update_document_status(document_id, "processing", progress=5, step="starting")

        # Update state: PARSING (0-10%)
        self.update_progress('parsing', 5, {'status': 'Extracting text from document'})
        task_logger.debug(f"Stage PARSING: Extracting text from document")

        # Process document (this handles parsing, chunking, embedding, extraction)
        # Run the async function synchronously in Celery task
        result = asyncio.run(process_document_simple(
            document_id=document_id,
            module_id=module_id,
            user_id=user_id,
            file_path=file_path
        ))

        # Update state: STORING (70-90%)
        self.update_progress('storing', 75, {'status': 'Storing in Neo4j'})
        task_logger.debug(f"Stage STORING: Saving to Neo4j")

        # Calculate processing time
        processing_time = (datetime.utcnow() - start_time).total_seconds()

        # Final result
        final_result = {
            'success': True,
            'document_id': document_id,
            'module_id': module_id,
            'user_id': user_id,
            'chunk_count': result.get('chunk_count', 0),
            'entity_count': result.get('entity_count', 0),
            'relationship_count': result.get('relationship_count', 0),
            'processing_time_seconds': processing_time,
            'task_id': self.request.id,
            'completed_at': datetime.utcnow().isoformat()
        }

        # Update state: COMPLETED (100%)
        self.update_progress('completed', 100, final_result)

        # Update Firestore status to READY
        update_document_status(
            document_id, "ready",
            progress=100, step="complete",
            chunk_count=final_result['chunk_count'],
            entity_count=final_result['entity_count']
        )

        task_logger.info(
            f"Document processing completed: doc={document_id}, "
            f"chunks={final_result['chunk_count']}, "
            f"entities={final_result['entity_count']}, "
            f"time={processing_time:.2f}s"
        )

        return final_result

    except SoftTimeLimitExceeded:
        """Handle soft time limit (25 minutes)."""
        error_msg = f"Task timed out after 25 minutes"
        task_logger.error(error_msg)

        self.update_state(
            state=ProcessingState.FAILED.value,
            meta={
                'stage': 'timeout',
                'progress': 0,
                'error': error_msg,
                'document_id': document_id
            }
        )
        update_document_status(document_id, "failed", error=error_msg)

        # Don't retry on timeout - it's likely a very large document
        raise

    except MaxRetriesExceededError:
        """Handle max retries exceeded."""
        error_msg = f"Max retries ({self.max_retries}) exceeded for document {document_id}"
        task_logger.error(error_msg)

        self.update_state(
            state=ProcessingState.FAILED.value,
            meta={
                'stage': 'max_retries',
                'progress': 0,
                'error': error_msg,
                'document_id': document_id
            }
        )
        update_document_status(document_id, "failed", error=error_msg)

        raise

    except ConnectionError as e:
        """Handle connection errors (auto-retry)."""
        task_logger.warning(f"Connection error, will retry: {e}")
        raise

    except TimeoutError as e:
        """Handle timeout errors (auto-retry)."""
        task_logger.warning(f"Timeout error, will retry: {e}")
        raise

    except ValueError as e:
        """Handle validation errors (don't retry)."""
        task_logger.error(f"Validation error: {e}")

        self.update_state(
            state=ProcessingState.FAILED.value,
            meta={
                'stage': 'validation',
                'progress': 0,
                'error': str(e),
                'document_id': document_id
            }
        )
        update_document_status(document_id, "failed", error=str(e))

        # Don't retry validation errors
        raise

    except Exception as e:
        """Handle unexpected errors."""
        task_logger.exception(f"Unexpected error processing document: {e}")

        self.update_state(
            state=ProcessingState.FAILED.value,
            meta={
                'stage': 'unexpected',
                'progress': 0,
                'error': str(e),
                'error_type': type(e).__name__,
                'document_id': document_id
            }
        )
        update_document_status(document_id, "failed", error=str(e))

        # Re-raise to trigger retry if applicable
        raise


# ============================================================================
# BATCH DOCUMENT PROCESSING TASK
# ============================================================================

@app.task(
    bind=True,
    base=KGProcessingTask,
    name='api.tasks.process_batch',
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    acks_late=True,
    reject_on_worker_lost=True,
    time_limit=3600,                # 1 hour hard limit
    soft_time_limit=3000,           # 50 minutes soft limit
)
def process_batch_task(
    self,
    document_ids: List[str],
    module_id: str,
    user_id: str
) -> Dict[str, Any]:
    """
    Process multiple documents in batch.

    Dispatches individual process_document_task for each document
    and returns task IDs for tracking.

    Args:
        document_ids: List of document IDs to process
        module_id: Module ID for tagging all created nodes
        user_id: User who owns these documents

    Returns:
        Dict containing:
        - success: Boolean
        - module_id: The module ID used
        - total_documents: Total documents in batch
        - task_map: Mapping of document_id to task_id
        - submitted_at: Timestamp
    """
    task_logger = logging.getLogger(f'batch_task.{self.request.id}')

    total = len(document_ids)
    task_logger.info(f"Starting batch processing: {total} documents for module {module_id}")

    # Update initial state
    self.update_state(
        state='PROCESSING',
        meta={
            'stage': 'dispatching',
            'progress': 0,
            'total': total,
            'module_id': module_id
        }
    )

    try:
        # Validate inputs
        if not document_ids:
            raise ValueError("document_ids list cannot be empty")
        if not module_id:
            raise ValueError("module_id is required")
        if not user_id:
            raise ValueError("user_id is required")

        # Dispatch tasks for each document
        task_map = {}
        submitted_at = datetime.utcnow().isoformat()

        for i, doc_id in enumerate(document_ids):
            task_logger.debug(f"Dispatching task for document {doc_id}")

            # Submit individual task
            result = process_document_task.delay(doc_id, module_id, user_id)

            task_map[doc_id] = {
                'task_id': result.id,
                'status': 'submitted',
                'submitted_at': submitted_at
            }

            # Update progress
            progress = ((i + 1) / total) * 100
            self.update_state(
                state='PROCESSING',
                meta={
                    'stage': 'dispatching',
                    'progress': progress,
                    'current': i + 1,
                    'total': total,
                    'module_id': module_id
                }
            )

        result = {
            'success': True,
            'module_id': module_id,
            'total_documents': total,
            'task_map': task_map,
            'submitted_at': submitted_at,
            'batch_task_id': self.request.id
        }

        task_logger.info(
            f"Batch processing submitted: {total} documents, "
            f"module={module_id}"
        )

        return result

    except Exception as e:
        task_logger.exception(f"Batch processing failed: {e}")

        self.update_state(
            state=ProcessingState.FAILED.value,
            meta={
                'stage': 'dispatch',
                'progress': 0,
                'error': str(e),
                'module_id': module_id
            }
        )

        raise


# ============================================================================
# HELPER FUNCTIONS FOR PROGRESS POLLING
# ============================================================================

def get_task_progress(task_id: str) -> Dict[str, Any]:
    """
    Get the progress of a processing task.

    Args:
        task_id: The Celery task ID

    Returns:
        Dict with state, progress, stage, and result/error info
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=app)

    if result.state == 'PENDING':
        return {
            'state': 'PENDING',
            'progress': 0,
            'stage': 'waiting',
            'message': 'Task is waiting to be processed'
        }

    elif result.state == 'PROCESSING':
        meta = result.info or {}
        return {
            'state': 'PROCESSING',
            'progress': meta.get('progress', 0),
            'stage': meta.get('stage', 'unknown'),
            'message': meta.get('status', 'Processing...')
        }

    elif result.state == 'SUCCESS':
        return {
            'state': 'COMPLETED',
            'progress': 100,
            'stage': 'completed',
            'result': result.result if hasattr(result, 'result') else None
        }

    elif result.state == 'FAILURE':
        return {
            'state': 'FAILED',
            'progress': 0,
            'stage': 'failed',
            'error': str(result.info) if result.info else 'Unknown error'
        }

    else:
        return {
            'state': result.state,
            'progress': 0,
            'stage': result.state.lower(),
            'message': str(result.info) if result.info else ''
        }


def cancel_task(task_id: str) -> bool:
    """
    Cancel a running task.

    Args:
        task_id: The Celery task ID

    Returns:
        True if task was revoked, False otherwise
    """
    from celery.exceptions import Ignore

    try:
        app.control.revoke(task_id, terminate=True)
        return True
    except Exception:
        return False


# ============================================================================
# TASK REGISTRY (for worker startup)
# ============================================================================

# Explicitly list tasks for better discoverability
__all__ = [
    'process_document_task',
    'process_batch_task',
    'get_task_progress',
    'cancel_task',
    'ProcessingState',
    'app'
]
