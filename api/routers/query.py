# query.py
# FastAPI router for knowledge graph query endpoints

# Provides REST API endpoints for hybrid search with graph expansion, document/chunk
# analysis, graph schema introspection, and graph data retrieval for visualization.
# Uses dependency injection for RAGEngine and GraphManager instances.

# @see: api/schemas/search.py - SearchRequest/SearchResponse schemas
# @see: api/schemas/analysis.py - AnalysisRequest/AnalysisResponse schemas
# @see: api/schemas/graph.py - GraphSchema/GraphData schemas
# @see: api/rag_engine.py - RAGEngine for hybrid search with graph expansion
# @see: api/graph_manager.py - GraphManager for graph traversal operations
# @note: Neo4j connection errors return 503 Service Unavailable

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from neo4j.exceptions import ServiceUnavailable

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
