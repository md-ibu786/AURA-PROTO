# query.py
# FastAPI router for knowledge graph query endpoints

# Provides REST API endpoints for hybrid search with graph expansion, document/chunk
# analysis, graph schema introspection, and graph data retrieval for visualization.
# Uses dependency injection for RAGEngine and GraphManager instances.

# @see: api/schemas/search.py - SearchRequest/SearchResponse schemas
# @see: api/schemas/analysis.py - AnalysisRequest/AnalysisResponse schemas
# @see: api/schemas/graph.py - GraphSchema/GraphData schemas
# @see: api/schemas/feedback.py - Feedback schemas for relevance judgments
# @see: api/rag_engine.py - RAGEngine for hybrid search with graph expansion
# @see: api/graph_manager.py - GraphManager for graph traversal operations
# @see: api/feedback_manager.py - FeedbackManager for storing user feedback
# @note: Neo4j connection errors return 503 Service Unavailable

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j.exceptions import ServiceUnavailable

from api.feedback_manager import FeedbackManager
from api.graph_manager import GraphManager
from api.neo4j_config import neo4j_driver
from api.rag_engine import RAGEngine, MultiDocOptions, MultiDocResponse
from api.schemas.analysis import (
    AnalysisOperation,
    AnalysisRequest,
    AnalysisResponse,
    SummaryResult,
)
from api.schemas.graph import (
    GraphData,
    GraphEdge,
    GraphNode,
    GraphSchema,
    NodeTypeSchema,
    RelationshipTypeSchema,
)
from api.schemas.feedback import (
    AnswerFeedback,
    FeedbackResponse,
    FeedbackStats,
    ImplicitFeedback,
    LowQualityResult,
    ResultFeedback,
)
from api.schemas.search import (
    EnrichedSearchResponse,
    EnrichedSearchResult,
    GraphContextResponse,
    SearchRequest,
    SearchResponse,
    SearchResult,
)
from services.embeddings import EmbeddingService
from pydantic import BaseModel, Field


# ============================================================================
# MULTI-DOCUMENT QUERY SCHEMAS
# ============================================================================


class MultiDocQueryRequest(BaseModel):
    """Request schema for multi-document queries."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The question to answer using multiple documents",
    )
    module_ids: List[str] = Field(
        ...,
        min_length=1,
        description="List of module IDs to search within",
    )
    max_documents: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of documents to include",
    )
    max_chunks_per_document: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum chunks per document",
    )
    include_entity_context: bool = Field(
        default=True,
        description="Include entity context from knowledge graph",
    )
    detect_contradictions: bool = Field(
        default=True,
        description="Detect and report contradictory information",
    )
    citation_style: str = Field(
        default="inline",
        description="Citation style: inline, footnote, or reference",
    )


# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# ROUTER CONFIGURATION
# ============================================================================

router = APIRouter(prefix="/v1/kg", tags=["Knowledge Graph"])

# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================


async def get_rag_engine() -> RAGEngine:
    """
    Dependency to get RAGEngine instance.

    Creates a new RAGEngine with the global Neo4j driver and EmbeddingService.

    Returns:
        RAGEngine: Configured RAG engine instance.

    Raises:
        HTTPException: 503 if Neo4j connection is unavailable.
    """
    if neo4j_driver is None:
        logger.error("Neo4j driver not initialized")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable. Please try again later.",
        )

    embedding_service = EmbeddingService()
    return RAGEngine(neo4j_driver, embedding_service)


async def get_graph_manager() -> GraphManager:
    """
    Dependency to get GraphManager instance.

    Creates a new GraphManager with the global Neo4j driver.

    Returns:
        GraphManager: Configured graph manager instance.

    Raises:
        HTTPException: 503 if Neo4j connection is unavailable.
    """
    if neo4j_driver is None:
        logger.error("Neo4j driver not initialized")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable. Please try again later.",
        )

    return GraphManager(neo4j_driver)


async def get_feedback_manager() -> FeedbackManager:
    """
    Dependency to get FeedbackManager instance.

    Creates a new FeedbackManager with the global Neo4j driver.

    Returns:
        FeedbackManager: Configured feedback manager instance.

    Raises:
        HTTPException: 503 if Neo4j connection is unavailable.
    """
    if neo4j_driver is None:
        logger.error("Neo4j driver not initialized")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable. Please try again later.",
        )

    return FeedbackManager(neo4j_driver)


# ============================================================================
# QUERY ENDPOINTS
# ============================================================================


@router.post("/query", response_model=SearchResponse)
async def hybrid_search_with_graph_expansion(
    request: SearchRequest,
    rag_engine: RAGEngine = Depends(get_rag_engine),
) -> SearchResponse:
    """
    Perform hybrid search with graph expansion.

    Combines vector similarity and fulltext search with knowledge graph traversal
    to provide enriched results. Supports module filtering and configurable weights.

    Args:
        request: Search request with query, filters, and options.
        rag_engine: Injected RAGEngine instance.

    Returns:
        SearchResponse: Search results with scores and metadata.

    Raises:
        HTTPException: 400 for invalid parameters, 503 for Neo4j errors.
    """
    logger.info(f"Hybrid search request: query='{request.query[:50]}...'")
    start_time = time.time()

    try:
        # Perform search with graph expansion
        enriched_results = await rag_engine.search_with_graph_expansion(
            query=request.query,
            module_ids=request.module_ids,
            top_k=request.top_k,
            vector_weight=request.vector_weight,
            fulltext_weight=request.fulltext_weight,
            min_score=request.min_score,
            include_parent_context=request.include_parent_context,
            expand_entities=True,
            hop_depth=2,
        )

        # Convert enriched results to response format
        results = [
            SearchResult(
                id=r.id,
                node_type=r.node_type,
                text=r.text,
                score=r.score,
                vector_score=r.vector_score,
                fulltext_score=r.fulltext_score,
                document_id=r.document_id,
                document_title=r.metadata.get("document_title"),
                module_id=r.module_id,
                parent_context=r.metadata.get("parent_context"),
                entities=[e.get("name", "") for e in r.related_entities[:5]],
            )
            for r in enriched_results.results
        ]

        elapsed_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Hybrid search completed: {len(results)} results in {elapsed_ms:.1f}ms"
        )

        return SearchResponse(
            query=request.query,
            results=results,
            total_count=len(results),
            search_time_ms=elapsed_ms,
            weights={
                "vector": request.vector_weight,
                "fulltext": request.fulltext_weight,
            },
        )

    except ServiceUnavailable as e:
        logger.error(f"Neo4j connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable. Please try again later.",
        )
    except ValueError as e:
        logger.warning(f"Invalid search parameters: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Search error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# ANALYSIS ENDPOINTS
# ============================================================================


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_content(
    request: AnalysisRequest,
    rag_engine: RAGEngine = Depends(get_rag_engine),
) -> AnalysisResponse:
    """
    Analyze documents or chunks with AI-powered operations.

    Supports summarization, comparison, extraction, and explanation operations.
    Currently returns placeholder results - full implementation in future phase.

    Args:
        request: Analysis request with operation type and target IDs.
        rag_engine: Injected RAGEngine instance.

    Returns:
        AnalysisResponse: Analysis result with processing metadata.

    Raises:
        HTTPException: 400 for invalid parameters, 404 if targets not found.
    """
    logger.info(
        f"Analysis request: operation={request.operation}, "
        f"targets={len(request.target_ids)}"
    )
    start_time = time.time()

    try:
        # Validate target_ids exist (placeholder - will be enhanced)
        if not request.target_ids:
            raise HTTPException(
                status_code=400,
                detail="At least one target ID is required",
            )

        # Stub implementation - return placeholder result
        # TODO: Implement full analysis using Gemini in future phase
        elapsed_ms = (time.time() - start_time) * 1000

        if request.operation == AnalysisOperation.SUMMARIZE:
            result = SummaryResult(
                summary="[Placeholder] Summary analysis will be implemented in a future phase.",
                key_points=[
                    "This is a placeholder response",
                    "Full summarization coming soon",
                ],
                source_ids=request.target_ids,
            )
        elif request.operation == AnalysisOperation.COMPARE:
            # For comparison, we need at least 2 targets
            if len(request.target_ids) < 2:
                raise HTTPException(
                    status_code=400,
                    detail="Comparison requires at least 2 target IDs",
                )
            from api.schemas.analysis import ComparisonResult

            result = ComparisonResult(
                similarities=["[Placeholder] Similarity analysis coming soon"],
                differences=["[Placeholder] Difference analysis coming soon"],
                source_a=request.target_ids[0],
                source_b=request.target_ids[1],
            )
        elif request.operation == AnalysisOperation.EXTRACT:
            from api.schemas.analysis import ExtractionResult

            result = ExtractionResult(
                extracted_items=[{"placeholder": "Extraction coming soon"}],
                extraction_type=request.options.get("extraction_type", "entities"),
                source_ids=request.target_ids,
            )
        elif request.operation == AnalysisOperation.EXPLAIN:
            from api.schemas.analysis import ExplanationResult

            result = ExplanationResult(
                explanation="[Placeholder] Explanation analysis will be implemented in a future phase.",
                related_concepts=["placeholder_concept"],
                graph_context={"placeholder": True},
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown operation: {request.operation}",
            )

        logger.info(f"Analysis completed in {elapsed_ms:.1f}ms")

        return AnalysisResponse(
            operation=request.operation,
            result=result,
            processing_time_ms=elapsed_ms,
            model_used="placeholder",
        )

    except HTTPException:
        raise
    except ServiceUnavailable as e:
        logger.error(f"Neo4j connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Analysis error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# GRAPH SCHEMA ENDPOINTS
# ============================================================================


@router.get("/graph/schema", response_model=GraphSchema)
async def get_graph_schema(
    graph_manager: GraphManager = Depends(get_graph_manager),
) -> GraphSchema:
    """
    Get knowledge graph schema information.

    Returns metadata about node types, relationship types, and counts in the graph.
    Useful for understanding graph structure and available query options.

    Args:
        graph_manager: Injected GraphManager instance.

    Returns:
        GraphSchema: Schema with node types, relationship types, and counts.

    Raises:
        HTTPException: 503 for Neo4j connection errors.
    """
    logger.info("Fetching graph schema")

    try:
        # Query Neo4j for node type counts
        node_types = []
        entity_labels = ["Topic", "Concept", "Methodology", "Finding"]

        with neo4j_driver.session() as session:
            # Get counts and properties for each entity type
            for label in entity_labels:
                count_result = session.run(
                    f"MATCH (n:{label}) RETURN count(n) as count"
                )
                count = count_result.single()["count"]

                # Get property keys (sample from first node)
                props_result = session.run(
                    f"MATCH (n:{label}) RETURN keys(n) as props LIMIT 1"
                )
                props_record = props_result.single()
                properties = props_record["props"] if props_record else []

                # Check if this type has embeddings
                has_embedding = "embedding" in properties

                node_types.append(
                    NodeTypeSchema(
                        name=label,
                        properties=[p for p in properties if p != "embedding"],
                        count=count,
                        has_embedding=has_embedding,
                    )
                )

            # Also include Chunk and ParentChunk
            for label in ["Chunk", "ParentChunk"]:
                count_result = session.run(
                    f"MATCH (n:{label}) RETURN count(n) as count"
                )
                count = count_result.single()["count"]

                props_result = session.run(
                    f"MATCH (n:{label}) RETURN keys(n) as props LIMIT 1"
                )
                props_record = props_result.single()
                properties = props_record["props"] if props_record else []
                has_embedding = "embedding" in properties

                node_types.append(
                    NodeTypeSchema(
                        name=label,
                        properties=[p for p in properties if p != "embedding"],
                        count=count,
                        has_embedding=has_embedding,
                    )
                )

            # Get relationship types and counts
            rel_result = session.run(
                """
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
                """
            )

            relationship_types = []
            for record in rel_result:
                rel_type = record["type"]
                rel_count = record["count"]

                # Get source and target types for this relationship
                endpoint_result = session.run(
                    f"""
                    MATCH (s)-[r:{rel_type}]->(t)
                    RETURN DISTINCT labels(s)[0] as source, labels(t)[0] as target
                    LIMIT 10
                    """
                )

                source_types = set()
                target_types = set()
                for ep in endpoint_result:
                    if ep["source"]:
                        source_types.add(ep["source"])
                    if ep["target"]:
                        target_types.add(ep["target"])

                relationship_types.append(
                    RelationshipTypeSchema(
                        name=rel_type,
                        source_types=list(source_types),
                        target_types=list(target_types),
                        properties=[],  # Could query for rel properties if needed
                        count=rel_count,
                    )
                )

            # Calculate totals
            total_nodes = sum(nt.count for nt in node_types)
            total_relationships = sum(rt.count for rt in relationship_types)

        logger.info(
            f"Graph schema: {len(node_types)} node types, "
            f"{len(relationship_types)} relationship types"
        )

        return GraphSchema(
            node_types=node_types,
            relationship_types=relationship_types,
            total_nodes=total_nodes,
            total_relationships=total_relationships,
            last_updated=datetime.utcnow(),
        )

    except ServiceUnavailable as e:
        logger.error(f"Neo4j connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Error fetching graph schema: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# GRAPH DATA ENDPOINTS
# ============================================================================


@router.get("/graph/data", response_model=GraphData)
async def get_graph_data(
    module_id: Optional[str] = Query(
        default=None,
        description="Filter by module ID",
    ),
    entity_types: Optional[List[str]] = Query(
        default=None,
        description="Filter by entity types (Topic, Concept, Methodology, Finding)",
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of nodes to return (1-1000)",
    ),
    graph_manager: GraphManager = Depends(get_graph_manager),
) -> GraphData:
    """
    Get graph data for visualization.

    Returns nodes and edges from the knowledge graph, optionally filtered by
    module and entity types. Results are limited to prevent overwhelming
    the visualization.

    Args:
        module_id: Optional module ID to filter by.
        entity_types: Optional list of entity types to include.
        limit: Maximum nodes to return (default 100, max 1000).
        graph_manager: Injected GraphManager instance.

    Returns:
        GraphData: Nodes and edges for graph visualization.

    Raises:
        HTTPException: 400 for invalid parameters, 503 for Neo4j errors.
    """
    logger.info(
        f"Fetching graph data: module_id={module_id}, "
        f"entity_types={entity_types}, limit={limit}"
    )

    try:
        # Validate entity_types if provided
        valid_types = {"Topic", "Concept", "Methodology", "Finding"}
        if entity_types:
            invalid_types = set(entity_types) - valid_types
            if invalid_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid entity types: {invalid_types}. "
                    f"Valid types are: {valid_types}",
                )

        # Build query based on filters
        type_filter = entity_types if entity_types else list(valid_types)
        type_labels = ":".join(type_filter)

        # Query for nodes
        with neo4j_driver.session() as session:
            # Build module filter
            module_clause = ""
            params = {"limit": limit}
            if module_id:
                module_clause = "AND n.module_id = $module_id"
                params["module_id"] = module_id

            # Get nodes
            node_query = f"""
            MATCH (n)
            WHERE (n:{" OR n:".join(type_filter)})
            {module_clause}
            RETURN n.id as id, labels(n)[0] as label, n.name as name,
                   n.definition as definition, n.module_id as module_id,
                   n.mention_count as mention_count
            ORDER BY n.mention_count DESC
            LIMIT $limit
            """

            node_result = session.run(node_query, params)
            nodes = []
            node_ids = set()

            for record in node_result:
                node_id = record["id"]
                if node_id:
                    node_ids.add(node_id)
                    nodes.append(
                        GraphNode(
                            id=node_id,
                            label=record["label"],
                            name=record["name"] or node_id,
                            properties={
                                "definition": record.get("definition"),
                                "module_id": record.get("module_id"),
                                "mention_count": record.get("mention_count"),
                            },
                        )
                    )

            # Get edges between the retrieved nodes
            edges = []
            if node_ids:
                edge_query = """
                MATCH (s)-[r]->(t)
                WHERE s.id IN $node_ids AND t.id IN $node_ids
                RETURN id(r) as id, s.id as source, t.id as target,
                       type(r) as type, r.confidence as confidence
                """

                edge_result = session.run(edge_query, {"node_ids": list(node_ids)})

                for record in edge_result:
                    edges.append(
                        GraphEdge(
                            id=str(record["id"]),
                            source=record["source"],
                            target=record["target"],
                            type=record["type"],
                            properties={
                                "confidence": record.get("confidence", 1.0),
                            },
                        )
                    )

        logger.info(f"Graph data: {len(nodes)} nodes, {len(edges)} edges")

        return GraphData(
            nodes=nodes,
            edges=edges,
            node_count=len(nodes),
            edge_count=len(edges),
            module_id=module_id,
        )

    except HTTPException:
        raise
    except ServiceUnavailable as e:
        logger.error(f"Neo4j connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Error fetching graph data: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# MULTI-DOCUMENT QUERY ENDPOINTS
# ============================================================================


@router.post("/query/multi-doc", response_model=MultiDocResponse)
async def multi_document_query(
    request: MultiDocQueryRequest,
    rag_engine: RAGEngine = Depends(get_rag_engine),
) -> MultiDocResponse:
    """
    Query across multiple documents within a module.

    Synthesizes information from multiple sources with proper citations.
    Detects and reports contradictory information when found.

    Args:
        request: Multi-document query request with query and module IDs.
        rag_engine: Injected RAGEngine instance.

    Returns:
        MultiDocResponse: Synthesized answer with citations and metadata.

    Raises:
        HTTPException: 400 for invalid parameters, 503 for Neo4j errors.
    """
    logger.info(
        f"Multi-doc query: query='{request.query[:50]}...', "
        f"modules={request.module_ids}"
    )

    try:
        # Build options from request
        options = MultiDocOptions(
            max_documents=request.max_documents,
            max_chunks_per_document=request.max_chunks_per_document,
            include_entity_context=request.include_entity_context,
            detect_contradictions=request.detect_contradictions,
            citation_style=request.citation_style,
        )

        # Execute multi-document query
        result = await rag_engine.multi_document_query(
            query=request.query,
            module_ids=request.module_ids,
            options=options,
        )

        logger.info(
            f"Multi-doc query completed: {result.sources_used} sources, "
            f"confidence={result.confidence:.2f}, {result.processing_time_ms:.1f}ms"
        )

        return result

    except ServiceUnavailable as e:
        logger.error(f"Neo4j connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable. Please try again later.",
        )
    except ValueError as e:
        logger.warning(f"Invalid multi-doc query parameters: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Multi-doc query error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# FEEDBACK ENDPOINTS
# ============================================================================


@router.post("/feedback/result", response_model=FeedbackResponse)
async def submit_result_feedback(
    feedback: ResultFeedback,
    feedback_manager: FeedbackManager = Depends(get_feedback_manager),
) -> FeedbackResponse:
    """
    Submit relevance feedback for a search result.

    Stores user feedback on how relevant a specific search result was to their query.
    Used for continuous improvement of search quality.

    Args:
        feedback: Result feedback with relevance score (0-1) and metadata.
        feedback_manager: Injected FeedbackManager instance.

    Returns:
        FeedbackResponse: Confirmation with feedback ID.

    Raises:
        HTTPException: 400 for invalid parameters, 503 for Neo4j errors.
    """
    logger.info(
        f"Result feedback: result_id={feedback.result_id}, "
        f"relevance={feedback.relevance_score:.2f}"
    )

    try:
        feedback_id = await feedback_manager.submit_result_feedback(feedback)

        return FeedbackResponse(
            feedback_id=feedback_id,
            status="success",
            message="Result feedback recorded successfully",
        )

    except ServiceUnavailable as e:
        logger.error(f"Neo4j connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Failed to store result feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/feedback/answer", response_model=FeedbackResponse)
async def submit_answer_feedback(
    feedback: AnswerFeedback,
    feedback_manager: FeedbackManager = Depends(get_feedback_manager),
) -> FeedbackResponse:
    """
    Submit quality feedback for a synthesized answer.

    Stores user feedback on whether an answer was helpful and accurate.
    Used for evaluating answer synthesis quality.

    Args:
        feedback: Answer feedback with helpfulness rating and optional accuracy.
        feedback_manager: Injected FeedbackManager instance.

    Returns:
        FeedbackResponse: Confirmation with feedback ID.

    Raises:
        HTTPException: 400 for invalid parameters, 503 for Neo4j errors.
    """
    logger.info(
        f"Answer feedback: answer_hash={feedback.answer_hash[:8]}..., "
        f"helpful={feedback.helpful}"
    )

    try:
        feedback_id = await feedback_manager.submit_answer_feedback(feedback)

        return FeedbackResponse(
            feedback_id=feedback_id,
            status="success",
            message="Answer feedback recorded successfully",
        )

    except ServiceUnavailable as e:
        logger.error(f"Neo4j connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Failed to store answer feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/feedback/implicit", response_model=FeedbackResponse)
async def submit_implicit_feedback(
    feedback: ImplicitFeedback,
    feedback_manager: FeedbackManager = Depends(get_feedback_manager),
) -> FeedbackResponse:
    """
    Submit implicit feedback signals (clicks, dwell time).

    Stores behavioral signals that can indicate result relevance without
    requiring explicit user input.

    Args:
        feedback: Implicit feedback with click or dwell time data.
        feedback_manager: Injected FeedbackManager instance.

    Returns:
        FeedbackResponse: Confirmation with feedback ID.

    Raises:
        HTTPException: 400 for invalid parameters, 503 for Neo4j errors.
    """
    logger.debug(
        f"Implicit feedback: type={feedback.feedback_type.value}, "
        f"result_id={feedback.result_id}"
    )

    try:
        feedback_id = await feedback_manager.submit_implicit_feedback(feedback)

        return FeedbackResponse(
            feedback_id=feedback_id,
            status="success",
            message="Implicit feedback recorded successfully",
        )

    except ServiceUnavailable as e:
        logger.error(f"Neo4j connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable. Please try again later.",
        )
    except ValueError as e:
        logger.warning(f"Invalid implicit feedback: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to store implicit feedback: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/feedback/stats", response_model=FeedbackStats)
async def get_feedback_stats(
    module_id: Optional[str] = Query(
        default=None,
        description="Filter stats by module ID",
    ),
    start_date: Optional[datetime] = Query(
        default=None,
        description="Start of time range (ISO format)",
    ),
    end_date: Optional[datetime] = Query(
        default=None,
        description="End of time range (ISO format)",
    ),
    feedback_manager: FeedbackManager = Depends(get_feedback_manager),
) -> FeedbackStats:
    """
    Get aggregated feedback statistics.

    Returns statistics on feedback including total count, positive ratio,
    average relevance scores, and breakdowns by type and module.

    Args:
        module_id: Optional module ID to filter statistics.
        start_date: Optional start of time range.
        end_date: Optional end of time range.
        feedback_manager: Injected FeedbackManager instance.

    Returns:
        FeedbackStats: Aggregated feedback metrics.

    Raises:
        HTTPException: 503 for Neo4j errors.
    """
    logger.info(f"Fetching feedback stats: module_id={module_id}")

    try:
        time_range = None
        if start_date and end_date:
            time_range = (start_date, end_date)
        elif start_date:
            time_range = (start_date, datetime.utcnow())
        elif end_date:
            # Default to 30 days before end_date
            from datetime import timedelta

            time_range = (end_date - timedelta(days=30), end_date)

        stats = await feedback_manager.get_feedback_stats(
            module_id=module_id,
            time_range=time_range,
        )

        return stats

    except ServiceUnavailable as e:
        logger.error(f"Neo4j connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Failed to fetch feedback stats: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/feedback/low-quality", response_model=List[LowQualityResult])
async def get_low_quality_results(
    threshold: float = Query(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Maximum average relevance score (0.0-1.0)",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of results to return",
    ),
    feedback_manager: FeedbackManager = Depends(get_feedback_manager),
) -> List[LowQualityResult]:
    """
    Get results that consistently receive low relevance scores.

    Identifies chunks and entities that may need content quality review
    based on user feedback patterns. Useful for finding problematic content.

    Args:
        threshold: Maximum average relevance to be considered low-quality.
        limit: Maximum results to return.
        feedback_manager: Injected FeedbackManager instance.

    Returns:
        List[LowQualityResult]: Problem content with feedback details.

    Raises:
        HTTPException: 503 for Neo4j errors.
    """
    logger.info(f"Finding low-quality results: threshold={threshold}, limit={limit}")

    try:
        results = await feedback_manager.get_low_quality_results(
            threshold=threshold,
            limit=limit,
        )

        return results

    except ServiceUnavailable as e:
        logger.error(f"Neo4j connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Failed to find low-quality results: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# GRAPH VISUALIZATION ENDPOINTS (Phase 11-05)
# ============================================================================

from fastapi import Body, Response
from api.graph_visualizer import (
    GraphVisualizer,
    GraphOptions,
    LayoutType,
    ExportFormat,
    VisualizationGraph,
    get_graph_visualizer,
)


@router.get(
    "/graph/module/{module_id}",
    response_model=VisualizationGraph,
    summary="Get module graph visualization",
    description="Get visualization-ready graph for a module with filtering and layout options.",
)
async def get_module_graph(
    module_id: str,
    include_entity_types: Optional[List[str]] = Query(
        None,
        description="Entity types to include (e.g., Topic, Concept)",
    ),
    exclude_entity_types: Optional[List[str]] = Query(
        None,
        description="Entity types to exclude",
    ),
    include_relationships: Optional[List[str]] = Query(
        None,
        description="Relationship types to include",
    ),
    exclude_relationships: Optional[List[str]] = Query(
        None,
        description="Relationship types to exclude",
    ),
    max_nodes: int = Query(
        500,
        ge=1,
        le=2000,
        description="Maximum nodes to return",
    ),
    include_chunks: bool = Query(
        False,
        description="Include chunk nodes",
    ),
    include_documents: bool = Query(
        True,
        description="Include document nodes",
    ),
    layout: LayoutType = Query(
        LayoutType.FORCE_DIRECTED,
        description="Layout algorithm to apply",
    ),
    visualizer: GraphVisualizer = Depends(get_graph_visualizer),
) -> VisualizationGraph:
    """
    Get visualization-ready graph for a module.
    
    Returns nodes and edges with positions, colors, and metadata
    suitable for direct rendering in graph visualization components.
    
    Args:
        module_id: Module identifier
        include_entity_types: Filter to only these entity types
        exclude_entity_types: Exclude these entity types
        include_relationships: Filter to only these relationship types
        exclude_relationships: Exclude these relationship types
        max_nodes: Maximum nodes in result
        include_chunks: Include chunk nodes (can be verbose)
        include_documents: Include document nodes
        layout: Layout algorithm (force_directed, hierarchical, radial, circular)
    
    Returns:
        VisualizationGraph with nodes, edges, and metadata
    """
    logger.info(f"Getting module graph: {module_id}")
    
    try:
        options = GraphOptions(
            include_entity_types=include_entity_types,
            exclude_entity_types=exclude_entity_types,
            include_relationship_types=include_relationships,
            exclude_relationship_types=exclude_relationships,
            max_nodes=max_nodes,
            include_chunks=include_chunks,
            include_documents=include_documents,
            layout=layout,
        )
        
        graph = await visualizer.get_module_graph(module_id, options)
        
        logger.info(
            f"Module graph generated: {graph.metadata.node_count} nodes, "
            f"{graph.metadata.edge_count} edges"
        )
        
        return graph
        
    except ServiceUnavailable as e:
        logger.error(f"Neo4j connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Failed to get module graph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/graph/document/{document_id}",
    response_model=VisualizationGraph,
    summary="Get document graph visualization",
    description="Get visualization-ready graph for a document showing chunks and entities.",
)
async def get_document_graph(
    document_id: str,
    include_chunks: bool = Query(
        True,
        description="Include chunk nodes in the graph",
    ),
    layout: LayoutType = Query(
        LayoutType.HIERARCHICAL,
        description="Layout algorithm (hierarchical recommended for documents)",
    ),
    max_nodes: int = Query(
        500,
        ge=1,
        le=2000,
        description="Maximum nodes to return",
    ),
    visualizer: GraphVisualizer = Depends(get_graph_visualizer),
) -> VisualizationGraph:
    """
    Get visualization-ready graph for a document.
    
    Shows document structure with chunks and extracted entities.
    Hierarchical layout is recommended for document graphs.
    
    Args:
        document_id: Document identifier
        include_chunks: Include chunk nodes (recommended True)
        layout: Layout algorithm
        max_nodes: Maximum nodes in result
    
    Returns:
        VisualizationGraph for the document
    """
    logger.info(f"Getting document graph: {document_id}")
    
    try:
        options = GraphOptions(
            include_chunks=include_chunks,
            layout=layout,
            max_nodes=max_nodes,
        )
        
        graph = await visualizer.get_document_graph(document_id, options)
        
        return graph
        
    except ServiceUnavailable as e:
        logger.error(f"Neo4j connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Failed to get document graph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/graph/cross-module",
    response_model=VisualizationGraph,
    summary="Get cross-module comparison graph",
    description="Get visualization comparing entities across multiple modules.",
)
async def get_cross_module_graph(
    module_ids: List[str] = Body(
        ...,
        min_length=2,
        description="List of module IDs to compare (minimum 2)",
    ),
    options: GraphOptions = Body(
        default_factory=GraphOptions,
        description="Graph generation options",
    ),
    visualizer: GraphVisualizer = Depends(get_graph_visualizer),
) -> VisualizationGraph:
    """
    Get visualization comparing multiple modules.
    
    Shows entities from each module with relationships between them,
    highlighting shared concepts and cross-module connections.
    
    Args:
        module_ids: List of module IDs to compare (minimum 2)
        options: Graph generation options
    
    Returns:
        VisualizationGraph showing cross-module relationships
    """
    logger.info(f"Getting cross-module graph: {module_ids}")
    
    try:
        graph = await visualizer.get_cross_module_graph(module_ids, options)
        
        logger.info(
            f"Cross-module graph generated: {len(module_ids)} modules, "
            f"{graph.metadata.node_count} nodes"
        )
        
        return graph
        
    except ServiceUnavailable as e:
        logger.error(f"Neo4j connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Failed to get cross-module graph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get(
    "/graph/entity/{entity_id}/neighborhood",
    response_model=VisualizationGraph,
    summary="Get entity neighborhood graph",
    description="Get graph showing entities connected to a specific entity.",
)
async def get_entity_neighborhood(
    entity_id: str,
    depth: int = Query(
        2,
        ge=1,
        le=4,
        description="Number of hops to expand (1-4)",
    ),
    visualizer: GraphVisualizer = Depends(get_graph_visualizer),
) -> VisualizationGraph:
    """
    Get neighborhood graph around an entity.
    
    Shows the entity and all entities connected within the specified
    number of hops. Uses radial layout with the target entity at center.
    
    Args:
        entity_id: Entity identifier
        depth: Number of relationship hops to expand
    
    Returns:
        VisualizationGraph of entity neighborhood
    """
    logger.info(f"Getting entity neighborhood: {entity_id}, depth={depth}")
    
    try:
        graph = await visualizer.get_entity_neighborhood(entity_id, depth)
        
        return graph
        
    except ServiceUnavailable as e:
        logger.error(f"Neo4j connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Database connection unavailable. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Failed to get entity neighborhood: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post(
    "/graph/export",
    summary="Export graph in various formats",
    description="Export a visualization graph in JSON, GraphML, GEXF, or CSV format.",
)
async def export_graph(
    graph: VisualizationGraph = Body(
        ...,
        description="Graph to export",
    ),
    format: ExportFormat = Query(
        ExportFormat.JSON,
        description="Export format",
    ),
    visualizer: GraphVisualizer = Depends(get_graph_visualizer),
) -> Response:
    """
    Export graph in specified format.
    
    Supported formats:
    - JSON: Full graph data with metadata
    - GraphML: Standard graph exchange format
    - GEXF: Gephi format for network analysis
    - CSV: Simple node/edge tables
    
    Args:
        graph: VisualizationGraph to export
        format: Export format
    
    Returns:
        File download response
    """
    logger.info(f"Exporting graph: {format.value}, {graph.metadata.node_count} nodes")
    
    try:
        content = visualizer.export_graph(graph, format)
        
        # Determine content type and filename
        content_types = {
            ExportFormat.JSON: "application/json",
            ExportFormat.GRAPHML: "application/xml",
            ExportFormat.GEXF: "application/xml",
            ExportFormat.CSV: "text/csv",
        }
        extensions = {
            ExportFormat.JSON: "json",
            ExportFormat.GRAPHML: "graphml",
            ExportFormat.GEXF: "gexf",
            ExportFormat.CSV: "csv",
        }
        
        return Response(
            content=content,
            media_type=content_types[format],
            headers={
                "Content-Disposition": f"attachment; filename=graph.{extensions[format]}"
            },
        )
        
    except Exception as e:
        logger.error(f"Failed to export graph: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to export graph")
