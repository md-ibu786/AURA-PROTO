# summaries.py
# FastAPI router for auto-summarization endpoints

# Provides REST API endpoints for generating and retrieving document and module
# summaries. Supports configurable summary lengths, caching with Redis, and
# background processing for large modules.

# @see: services/summary_service.py - SummaryService for summarization logic
# @see: api/cache.py - Redis caching for summaries
# @see: api/routers/query.py - Pattern reference for router structure
# @note: Large modules (>10 docs) may use background processing

from __future__ import annotations

import logging
from typing import Dict, Union

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from services.summary_service import (
    DocumentSummary,
    ModuleSummary,
    SummaryLength,
    SummaryService,
)


# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# ROUTER CONFIGURATION
# ============================================================================

router = APIRouter(prefix="/v1/summaries", tags=["Summaries"])


# ============================================================================
# SCHEMAS
# ============================================================================


class TaskStatus(BaseModel):
    """Status response for background processing tasks."""

    task_id: str = Field(description="Unique task identifier")
    status: str = Field(description="Task status: pending, processing, completed")
    message: str = Field(description="Status message")


class CacheInvalidationResponse(BaseModel):
    """Response for cache invalidation operations."""

    status: str = Field(default="success", description="Operation status")
    message: str = Field(description="Result message")
    keys_deleted: int = Field(default=0, description="Number of cache keys deleted")


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================


async def get_summary_service() -> SummaryService:
    """
    Dependency to get SummaryService instance.

    Creates a new SummaryService with the global Neo4j driver.

    Returns:
        SummaryService: Configured summary service instance.
    """
    try:
        from api.neo4j_config import neo4j_driver
    except ImportError:
        neo4j_driver = None

    return SummaryService(neo4j_driver=neo4j_driver)


# ============================================================================
# DOCUMENT SUMMARY ENDPOINTS
# ============================================================================


@router.post("/document/{document_id}", response_model=DocumentSummary)
async def summarize_document(
    document_id: str,
    length: SummaryLength = Query(
        default=SummaryLength.STANDARD,
        description="Summary length: brief (~100 words), standard (~250), detailed (~500)",
    ),
    force_regenerate: bool = Query(
        default=False,
        description="Force regeneration even if cached",
    ),
    summary_service: SummaryService = Depends(get_summary_service),
) -> DocumentSummary:
    """
    Generate or retrieve a cached summary for a document.

    Generates an LLM-based summary of the document content, including
    key entities from the knowledge graph. Results are cached for 24 hours.

    Args:
        document_id: Unique document identifier.
        length: Summary length (brief, standard, detailed).
        force_regenerate: Force regeneration bypassing cache.
        summary_service: Injected SummaryService instance.

    Returns:
        DocumentSummary with summary text and metadata.

    Raises:
        HTTPException: 404 if document not found, 500 for processing errors.
    """
    logger.info(
        f"POST /document/{document_id}: length={length.value}, force={force_regenerate}"
    )

    try:
        summary = await summary_service.summarize_document(
            document_id=document_id,
            length=length,
            force_regenerate=force_regenerate,
        )

        if not summary.summary or summary.summary.startswith("No content"):
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found or has no content",
            )

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document summarization failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate summary: {str(e)}",
        )


@router.get("/document/{document_id}", response_model=DocumentSummary)
async def get_document_summary(
    document_id: str,
    length: SummaryLength = Query(
        default=SummaryLength.STANDARD,
        description="Summary length to retrieve",
    ),
    summary_service: SummaryService = Depends(get_summary_service),
) -> DocumentSummary:
    """
    Retrieve a cached summary for a document.

    Returns a previously generated summary if available in cache.
    Returns 404 if no cached summary exists.

    Args:
        document_id: Unique document identifier.
        length: Summary length to retrieve.
        summary_service: Injected SummaryService instance.

    Returns:
        DocumentSummary if cached, 404 otherwise.

    Raises:
        HTTPException: 404 if no cached summary exists.
    """
    logger.info(f"GET /document/{document_id}: length={length.value}")

    try:
        summary = await summary_service.get_cached_document_summary(
            document_id=document_id,
            length=length,
        )

        if summary is None:
            raise HTTPException(
                status_code=404,
                detail=f"No cached summary found for document {document_id}",
            )

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve document summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve summary: {str(e)}",
        )


@router.delete("/document/{document_id}", response_model=CacheInvalidationResponse)
async def invalidate_document_summary(
    document_id: str,
    summary_service: SummaryService = Depends(get_summary_service),
) -> CacheInvalidationResponse:
    """
    Invalidate cached summaries for a document.

    Removes all cached summaries for the specified document (all lengths).
    Use this when document content has been updated.

    Args:
        document_id: Unique document identifier.
        summary_service: Injected SummaryService instance.

    Returns:
        CacheInvalidationResponse with deletion count.
    """
    logger.info(f"DELETE /document/{document_id}: invalidating cache")

    try:
        deleted = summary_service.invalidate_document_cache(document_id)

        return CacheInvalidationResponse(
            status="success",
            message=f"Cache invalidated for document {document_id}",
            keys_deleted=deleted,
        )

    except Exception as e:
        logger.error(f"Cache invalidation failed: {e}", exc_info=True)
        return CacheInvalidationResponse(
            status="error",
            message=f"Cache invalidation failed: {str(e)}",
            keys_deleted=0,
        )


# ============================================================================
# MODULE SUMMARY ENDPOINTS
# ============================================================================

# Track background tasks (in production, use Celery or similar)
_background_tasks: Dict[str, str] = {}


def _generate_module_summary_background(
    module_id: str,
    length: SummaryLength,
    include_document_summaries: bool,
    force_regenerate: bool,
    task_id: str,
):
    """Background task for module summarization."""
    import asyncio

    async def _run():
        try:
            _background_tasks[task_id] = "processing"
            service = SummaryService()
            await service.summarize_module(
                module_id=module_id,
                length=length,
                include_document_summaries=include_document_summaries,
                force_regenerate=force_regenerate,
            )
            _background_tasks[task_id] = "completed"
        except Exception as e:
            logger.error(f"Background module summary failed: {e}")
            _background_tasks[task_id] = f"failed: {str(e)}"

    # Run in event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_run())
    finally:
        loop.close()


@router.post("/module/{module_id}", response_model=Union[ModuleSummary, TaskStatus])
async def summarize_module(
    module_id: str,
    length: SummaryLength = Query(
        default=SummaryLength.STANDARD,
        description="Summary length: brief, standard, detailed",
    ),
    include_document_summaries: bool = Query(
        default=True,
        description="Include individual document summaries in response",
    ),
    force_regenerate: bool = Query(
        default=False,
        description="Force regeneration even if cached",
    ),
    background_tasks: BackgroundTasks = None,
    summary_service: SummaryService = Depends(get_summary_service),
) -> Union[ModuleSummary, TaskStatus]:
    """
    Generate or retrieve a cached summary for a module.

    Aggregates summaries from all documents in the module and synthesizes
    a cohesive module-level overview. For large modules (>10 documents),
    may return a task_id for background processing.

    Args:
        module_id: Unique module identifier.
        length: Summary length (brief, standard, detailed).
        include_document_summaries: Include individual document summaries.
        force_regenerate: Force regeneration bypassing cache.
        background_tasks: FastAPI background tasks handler.
        summary_service: Injected SummaryService instance.

    Returns:
        ModuleSummary with aggregated summary, or TaskStatus for large modules.

    Raises:
        HTTPException: 404 if module not found, 500 for processing errors.
    """
    logger.info(
        f"POST /module/{module_id}: length={length.value}, "
        f"include_docs={include_document_summaries}, force={force_regenerate}"
    )

    try:
        # Check document count for potential background processing
        module_name, doc_ids = await summary_service._get_module_documents(module_id)

        if not doc_ids:
            raise HTTPException(
                status_code=404,
                detail=f"Module {module_id} not found or has no documents",
            )

        # For large modules, offer background processing
        if len(doc_ids) > 10 and background_tasks is not None and force_regenerate:
            import uuid

            task_id = str(uuid.uuid4())
            _background_tasks[task_id] = "pending"

            background_tasks.add_task(
                _generate_module_summary_background,
                module_id,
                length,
                include_document_summaries,
                force_regenerate,
                task_id,
            )

            return TaskStatus(
                task_id=task_id,
                status="pending",
                message=f"Module has {len(doc_ids)} documents. "
                "Processing in background. Check GET /module/{module_id} later.",
            )

        # Generate summary synchronously
        summary = await summary_service.summarize_module(
            module_id=module_id,
            length=length,
            include_document_summaries=include_document_summaries,
            force_regenerate=force_regenerate,
        )

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Module summarization failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate module summary: {str(e)}",
        )


@router.get("/module/{module_id}", response_model=ModuleSummary)
async def get_module_summary(
    module_id: str,
    length: SummaryLength = Query(
        default=SummaryLength.STANDARD,
        description="Summary length to retrieve",
    ),
    include_document_summaries: bool = Query(
        default=True,
        description="Include individual document summaries",
    ),
    summary_service: SummaryService = Depends(get_summary_service),
) -> ModuleSummary:
    """
    Retrieve a cached summary for a module.

    Returns a previously generated module summary if available in cache.
    Returns 404 if no cached summary exists.

    Args:
        module_id: Unique module identifier.
        length: Summary length to retrieve.
        include_document_summaries: Include individual document summaries.
        summary_service: Injected SummaryService instance.

    Returns:
        ModuleSummary if cached, 404 otherwise.

    Raises:
        HTTPException: 404 if no cached summary exists.
    """
    logger.info(
        f"GET /module/{module_id}: length={length.value}, "
        f"include_docs={include_document_summaries}"
    )

    try:
        summary = await summary_service.get_cached_module_summary(
            module_id=module_id,
            length=length,
            include_document_summaries=include_document_summaries,
        )

        if summary is None:
            raise HTTPException(
                status_code=404,
                detail=f"No cached summary found for module {module_id}",
            )

        return summary

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve module summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve summary: {str(e)}",
        )


@router.delete("/module/{module_id}", response_model=CacheInvalidationResponse)
async def invalidate_module_summary(
    module_id: str,
    summary_service: SummaryService = Depends(get_summary_service),
) -> CacheInvalidationResponse:
    """
    Invalidate cached summaries for a module.

    Removes all cached module summaries (all lengths).
    Does not invalidate individual document summaries.

    Args:
        module_id: Unique module identifier.
        summary_service: Injected SummaryService instance.

    Returns:
        CacheInvalidationResponse with deletion count.
    """
    logger.info(f"DELETE /module/{module_id}: invalidating cache")

    try:
        deleted = summary_service.invalidate_module_cache(module_id)

        return CacheInvalidationResponse(
            status="success",
            message=f"Cache invalidated for module {module_id}",
            keys_deleted=deleted,
        )

    except Exception as e:
        logger.error(f"Module cache invalidation failed: {e}", exc_info=True)
        return CacheInvalidationResponse(
            status="error",
            message=f"Cache invalidation failed: {str(e)}",
            keys_deleted=0,
        )
