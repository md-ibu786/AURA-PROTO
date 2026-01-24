# __init__.py
# Schemas package for AURA-NOTES-MANAGER API

# Re-exports search, analysis, and graph schemas for convenient import.
# @see: api/schemas/search.py - Hybrid search schemas
# @see: api/schemas/analysis.py - Analysis operation schemas
# @see: api/schemas/graph.py - Graph visualization schemas

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
