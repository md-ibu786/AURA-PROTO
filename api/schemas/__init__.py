"""
============================================================================
FILE: __init__.py
LOCATION: api/schemas/__init__.py
============================================================================

PURPOSE:
    Schemas package initialization for AURA-NOTES-MANAGER API.
    Re-exports search, analysis, graph, and feedback schemas for
    convenient import from the schemas package.

ROLE IN PROJECT:
    Centralizes schema imports to simplify API development.
    Provides a clean public API for importing all Pydantic models.
    - Consolidates related schemas from multiple modules
    - Reduces import complexity for route handlers
    - Maintains organized namespace for data models

KEY COMPONENTS:
    - Search schemas: SearchRequest, SearchResponse, EnrichedSearchRequest
    - Analysis schemas: AnalysisOperation, AnalysisRequest, AnalysisResponse
    - Graph schemas: GraphNode, GraphEdge, GraphMetadata
    - Feedback schemas: SearchResultFeedback, AnswerFeedback

DEPENDENCIES:
    - External: None
    - Internal: api.schemas.search, api.schemas.analysis,
                api.schemas.graph, api.schemas.graph_preview,
                api.schemas.feedback

USAGE:
    from api.schemas import SearchRequest, AnalysisResponse
    # Instead of: from api.schemas.search import SearchRequest
============================================================================
"""

from api.schemas.search import (
    SearchRequest,
    SearchResult,
    SearchResponse,
    QueryAnalysisRequest,
    FeedbackRequest,
    EnrichedSearchRequest,
    EnrichedSearchResult,
    EnrichedSearchResponse,
    GraphExpansionConfig,
)

from api.schemas.analysis import (
    AnalysisOperation,
    AnalysisRequest,
    AnalysisResponse,
    SummaryResult,
    ComparisonResult,
    ExtractionResult,
    ExplanationResult,
)

from api.schemas.graph import (
    NodeTypeSchema,
    RelationshipTypeSchema,
    GraphSchema,
    GraphNode,
    GraphEdge,
    GraphData,
)

__all__ = [
    # Search schemas
    "SearchRequest",
    "SearchResult",
    "SearchResponse",
    "QueryAnalysisRequest",
    "FeedbackRequest",
    "EnrichedSearchRequest",
    "EnrichedSearchResult",
    "EnrichedSearchResponse",
    "GraphExpansionConfig",
    # Analysis schemas
    "AnalysisOperation",
    "AnalysisRequest",
    "AnalysisResponse",
    "SummaryResult",
    "ComparisonResult",
    "ExtractionResult",
    "ExplanationResult",
    # Graph schemas
    "NodeTypeSchema",
    "RelationshipTypeSchema",
    "GraphSchema",
    "GraphNode",
    "GraphEdge",
    "GraphData",
]
