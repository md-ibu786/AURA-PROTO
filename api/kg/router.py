# router.py
# =========================
#
# FastAPI router for per-document KG status tracking and batch processing.
# Provides API endpoints for managing knowledge graph processing workflow.
#
# Features:
# ----------
# - Individual document KG status查询
# - Batch document processing with idempotency
# - Processing queue monitoring
# - Celery task status tracking
#
# Classes/Functions:
# ------------------
# - router: FastAPI router with /kg prefix
# - get_document_kg_status(): GET /kg/documents/{id}/status
# - process_batch(): POST /kg/process-batch
# - get_processing_queue(): GET /kg/processing-queue
# - get_task_status(): GET /kg/tasks/{id}/status
# - _find_note_by_id(): Helper to locate notes in nested collections
# - _doc_to_queue_item(): Helper to convert Firestore doc to queue item
#
# @see: api/modules/models.py - Pydantic models for requests/responses
# @see: api/tasks/document_processing_tasks.py - Celery tasks triggered by these endpoints
# @note: All documents are stored in Firestore, KG is stored in Neo4j
# @note: Collection group queries used to find notes in nested subcollections

from fastapi import APIRouter, HTTPException, status
from typing import List, Optional
from datetime import datetime
import logging

try:
    from config import db
except ImportError:
    from api.config import db

try:
    from modules.models import (
        DocumentKGStatus,
        KGStatus,
        BatchProcessingRequest,
        BatchProcessingResponse,
        ProcessingQueueItem,
        BatchDeleteRequest,
        BatchDeleteResponse,
    )
except ImportError:
    from api.modules.models import (
        DocumentKGStatus,
        KGStatus,
        BatchProcessingRequest,
        BatchProcessingResponse,
        ProcessingQueueItem,
        BatchDeleteRequest,
        BatchDeleteResponse,
    )

try:
    from tasks.document_processing_tasks import process_batch_task, get_task_progress
except ImportError:
    from api.tasks.document_processing_tasks import (
        process_batch_task,
        get_task_progress,
    )

try:
    from graph_manager import GraphManager
    from neo4j_config import neo4j_driver
except ImportError:
    from api.graph_manager import GraphManager
    from api.neo4j_config import neo4j_driver

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/kg", tags=["KG Processing"])


# ============================================================================
# GET /kg/documents/{document_id}/status
# ============================================================================


@router.get("/documents/{document_id}/status", response_model=DocumentKGStatus)
async def get_document_kg_status(document_id: str):
    """
    Get KG status for a single document (note).

    Returns:
    - pending: Document not yet processed
    - processing: Document currently being processed
    - ready: Document successfully processed
    - failed: Document processing failed
    """
    logger.debug(f"Getting KG status for document: {document_id}")

    # Use collection_group to find the note in nested subcollections
    notes = list(
        db.collection_group("notes")
        .where("__name__", ">=", document_id)
        .where("__name__", "<=", document_id + "\uf8ff")
        .limit(1)
        .stream()
    )

    # Also try direct lookup if collection_group doesn't work
    if not notes:
        # Try to find by iterating (fallback)
        notes = list(db.collection_group("notes").stream())
        notes = [n for n in notes if n.id == document_id]

    if not notes:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found",
        )

    doc = notes[0]
    doc_data = doc.to_dict()

    # Default to PENDING if kg_status not set
    raw_status = doc_data.get("kg_status", "pending")
    try:
        kg_status = KGStatus(raw_status)
    except ValueError:
        kg_status = KGStatus.PENDING

    return DocumentKGStatus(
        document_id=document_id,
        module_id=doc_data.get("module_id", ""),
        file_name=doc_data.get("file_name", doc_data.get("title", "Unknown")),
        kg_status=kg_status,
        kg_processed_at=doc_data.get("kg_processed_at"),
        kg_error=doc_data.get("kg_error"),
        chunk_count=doc_data.get("kg_chunk_count"),
        entity_count=doc_data.get("kg_entity_count"),
    )


# ============================================================================
# POST /kg/process-batch
# ============================================================================


def _find_note_by_id(note_id: str):
    """Find a note document by ID using collection_group query."""
    # Try to find the note in nested subcollections
    notes = list(db.collection_group("notes").stream())
    for note in notes:
        if note.id == note_id:
            return note
    return None


@router.post("/process-batch", response_model=BatchProcessingResponse)
async def process_batch(request: BatchProcessingRequest):
    """
    Process multiple documents in batch for KG creation.

    - All documents must belong to the same module
    - Already processed documents are skipped (idempotent)
    - Returns task info for progress tracking
    """
    logger.info(
        f"Batch processing request: {len(request.file_ids)} documents for module {request.module_id}"
    )

    # Validate all documents exist and belong to module
    skipped_ids = []
    queued_ids = []
    note_paths = {}  # Store note paths for processing

    for doc_id in request.file_ids:
        # Find note using collection_group
        note = _find_note_by_id(doc_id)

        if not note:
            logger.warning(f"Note {doc_id} not found, skipping")
            continue  # Skip non-existent docs

        doc_data = note.to_dict()
        note_path = note.reference.path

        # Extract module_id from the note path (e.g., departments/.../modules/{module_id}/notes/{note_id})
        path_parts = note_path.split("/")
        note_module_id = None
        for i, part in enumerate(path_parts):
            if part == "modules" and i + 1 < len(path_parts):
                note_module_id = path_parts[i + 1]
                break

        # Verify document belongs to the specified module
        if note_module_id != request.module_id:
            logger.warning(
                f"Note {doc_id} belongs to module {note_module_id}, not {request.module_id}, skipping"
            )
            continue

        # Check if already processed (idempotency)
        if doc_data.get("kg_status") == "ready":
            skipped_ids.append(doc_id)
            logger.debug(f"Note {doc_id} already processed, skipping")
        else:
            queued_ids.append(doc_id)
            note_paths[doc_id] = note_path

    # If all documents already processed, return early
    if not queued_ids:
        return BatchProcessingResponse(
            task_id="",
            status_url="",
            documents_queued=0,
            documents_skipped=len(skipped_ids),
            message="All documents already processed",
        )

    # Trigger Celery batch task
    # Note: user_id should come from auth context, using "staff_user" as placeholder
    task = process_batch_task.delay(queued_ids, request.module_id, "staff_user")

    logger.info(
        f"Batch task {task.id} dispatched: {len(queued_ids)} documents queued, {len(skipped_ids)} skipped"
    )

    return BatchProcessingResponse(
        task_id=task.id,
        status_url=f"/api/v1/kg/tasks/{task.id}/status",
        documents_queued=len(queued_ids),
        documents_skipped=len(skipped_ids),
        message=f"Queued {len(queued_ids)} documents, skipped {len(skipped_ids)} already processed",
    )


# ============================================================================
# GET /kg/processing-queue
# ============================================================================


@router.get("/processing-queue", response_model=List[ProcessingQueueItem])
async def get_processing_queue():
    """
    Get all notes currently being processed for KG.

    Returns notes with kg_status == 'processing'.
    Used by frontend for ProcessingQueue component.
    """
    logger.debug("Fetching processing queue")

    queue = []

    # Scan all notes and filter in Python (avoids Firestore index requirement)
    try:
        all_notes = db.collection_group("notes").stream()
        for doc in all_notes:
            doc_data = doc.to_dict()
            if doc_data.get("kg_status") == "processing":
                queue.append(_doc_to_queue_item(doc, doc_data))
    except Exception as e:
        logger.error(f"Failed to fetch processing queue: {e}")
        # Return empty queue rather than crashing
        return []

    logger.debug(f"Processing queue contains {len(queue)} documents")
    return queue


def _doc_to_queue_item(doc, doc_data: dict):
    """Helper to convert Firestore doc to ProcessingQueueItem."""
    # Extract module_id from path
    path_parts = doc.reference.path.split("/")
    module_id = ""
    for i, part in enumerate(path_parts):
        if part == "modules" and i + 1 < len(path_parts):
            module_id = path_parts[i + 1]
            break

    # Handle missing started_at
    started_at = doc_data.get("kg_started_at")
    if started_at is None:
        started_at = datetime.utcnow()

    return ProcessingQueueItem(
        document_id=doc.id,
        module_id=module_id,
        file_name=doc_data.get("file_name", doc_data.get("title", "Unknown")),
        status=KGStatus.PROCESSING,
        progress=doc_data.get("kg_progress", 0),
        step=doc_data.get("kg_step", "processing"),
        started_at=started_at,
    )


# ============================================================================
# GET /kg/tasks/{task_id}/status
# ============================================================================


@router.get("/tasks/{task_id}/status")
async def get_task_status(task_id: str):
    """
    Get Celery task status and progress.

    Returns task state and meta information.
    """
    if not task_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="task_id is required"
        )

    logger.debug(f"Getting status for task: {task_id}")

    progress = get_task_progress(task_id)

    return {
        "task_id": task_id,
        "status": progress.get("state", "UNKNOWN"),
        "progress": progress.get("progress", 0),
        "stage": progress.get("stage", "unknown"),
        "result": progress.get("result"),
        "error": progress.get("error"),
    }


# ============================================================================
# POST /kg/delete-batch
# ============================================================================


@router.post("/delete-batch", response_model=BatchDeleteResponse)
async def delete_batch(request: BatchDeleteRequest):
    """
    Delete multiple documents from the Knowledge Graph.

    This completely removes documents from Neo4j:
    - Document nodes
    - All associated Chunk and ParentChunk nodes
    - Orphaned entities (Topic, Concept, Methodology, Finding)

    After deletion, Firestore kg_status is reset to 'pending'.
    """
    logger.info(
        f"Delete batch request: {len(request.file_ids)} documents for module {request.module_id}"
    )

    deleted_count = 0
    failed_ids = []

    # Initialize graph manager
    graph_manager = GraphManager(neo4j_driver)

    for doc_id in request.file_ids:
        # Find note using collection_group
        note = _find_note_by_id(doc_id)

        if not note:
            logger.warning(f"Note {doc_id} not found, skipping")
            failed_ids.append(doc_id)
            continue

        doc_data = note.to_dict()
        note_path = note.reference.path

        # Extract module_id from the note path
        path_parts = note_path.split("/")
        note_module_id = None
        for i, part in enumerate(path_parts):
            if part == "modules" and i + 1 < len(path_parts):
                note_module_id = path_parts[i + 1]
                break

        # Verify document belongs to the specified module
        if note_module_id != request.module_id:
            logger.warning(
                f"Note {doc_id} belongs to module {note_module_id}, not {request.module_id}, skipping"
            )
            failed_ids.append(doc_id)
            continue

        # Only delete documents that are actually processed
        if doc_data.get("kg_status") != "ready":
            logger.warning(f"Note {doc_id} is not KG-ready, skipping")
            failed_ids.append(doc_id)
            continue

        # Delete from Neo4j
        try:
            success = await graph_manager.delete_document(doc_id)
            if not success:
                logger.error(f"Failed to delete {doc_id} from Neo4j")
                failed_ids.append(doc_id)
                continue
        except Exception as e:
            logger.error(f"Exception deleting {doc_id} from Neo4j: {e}")
            failed_ids.append(doc_id)
            continue

        # Reset Firestore status
        try:
            note.reference.update(
                {
                    "kg_status": "pending",
                    "kg_processed_at": None,
                    "kg_chunk_count": None,
                    "kg_entity_count": None,
                    "kg_error": None,
                    "updated_at": datetime.utcnow(),
                }
            )
            logger.debug(f"Reset Firestore status for {doc_id}")
            deleted_count += 1
        except Exception as e:
            logger.error(f"Failed to reset Firestore status for {doc_id}: {e}")
            failed_ids.append(doc_id)

    logger.info(
        f"Delete batch complete: {deleted_count} deleted, {len(failed_ids)} failed"
    )

    return BatchDeleteResponse(
        deleted_count=deleted_count,
        failed=failed_ids,
        message=f"Deleted {deleted_count} documents from KG"
        + (f", {len(failed_ids)} failed" if failed_ids else ""),
    )
