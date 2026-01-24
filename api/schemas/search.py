# search.py
# Pydantic schemas for hybrid search API requests and responses

# Defines the API contracts for the /v1/kg/query endpoint including request
# validation, response models, and weight normalization. Enhanced with graph
# expansion schemas for multi-hop entity traversal support.

# @see: api/rag_engine.py - Uses these schemas for type safety
# @see: api/graph_manager.py - Graph traversal operations
# @see: api/routers/query.py - API endpoint using these schemas (Phase 10-04)
# @note: vector_weight + fulltext_weight normalized to 1.0 via validator

from __future__ import annotations

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================


class QueryExpansionConfig(BaseModel):
    """
    Configuration for query expansion.

    Controls how queries are expanded using entity relationships
    from the knowledge graph.
    """

    enabled: bool = Field(
        default=False,
        description="Whether to expand query using knowledge graph",
    )
    max_expansion_terms: int = Field(
        default=10,
        ge=0,
        le=20,
        description="Maximum number of expansion terms to add (0-20)",
    )
    min_term_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum weight threshold for expansion terms (0.0-1.0)",
    )


class SearchRequest(BaseModel):
    """
    Request schema for hybrid search API.

    Validates search parameters and normalizes weights.
    Supports optional query and graph expansion configuration.

    Example:
        {
            "query": "machine learning algorithms",
            "module_ids": ["mod_123"],
            "top_k": 15,
            "vector_weight": 0.7,
            "fulltext_weight": 0.3
        }
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Search query text (1-1000 characters)",
    )
    module_ids: Optional[List[str]] = Field(
        default=None,
        description="Optional list of module IDs to filter results",
    )
    top_k: int = Field(
        default=15,
        ge=1,
        le=100,
        description="Number of results to return (1-100)",
    )
    vector_weight: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Weight for vector similarity scores (0.0-1.0)",
    )
    fulltext_weight: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Weight for fulltext/BM25 scores (0.0-1.0)",
    )
    include_parent_context: bool = Field(
        default=True,
        description="Include parent chunk text for context",
    )
    min_score: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum combined score threshold (0.0-1.0)",
    )
    query_expansion: Optional[QueryExpansionConfig] = Field(
        default=None,
        description="Optional query expansion configuration",
    )
    graph_expansion: Optional["GraphExpansionConfig"] = Field(
        default=None,
        description="Optional graph expansion configuration",
    )

    @model_validator(mode="after")
    def normalize_weights(self) -> "SearchRequest":
        """
        Normalize weights to sum to 1.0.

        If both weights are 0, defaults to vector=0.7, fulltext=0.3.
        """
        total = self.vector_weight + self.fulltext_weight

        if total == 0:
            # Default weights if both are 0
            self.vector_weight = 0.7
            self.fulltext_weight = 0.3
        elif abs(total - 1.0) > 0.001:
            # Normalize to sum to 1.0
            self.vector_weight = self.vector_weight / total
            self.fulltext_weight = self.fulltext_weight / total

        return self

    @field_validator("module_ids")
    @classmethod
    def validate_module_ids(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate module_ids format - ensure non-empty strings."""
        if v is None:
            return None

        validated = []
        for module_id in v:
            if module_id and isinstance(module_id, str) and module_id.strip():
                validated.append(module_id.strip())

        return validated if validated else None


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================


class SearchResult(BaseModel):
    """
    Individual search result in API response.

    Contains the matched text, scores, and source information.
    """

    id: str = Field(description="Unique identifier for the result")
    node_type: str = Field(description="Type of node: Chunk, ParentChunk, or Entity")
    text: str = Field(description="Text content of the result")
    score: float = Field(description="Combined weighted score (0.0-1.0)")
    vector_score: Optional[float] = Field(
        default=None,
        description="Normalized vector similarity score",
    )
    fulltext_score: Optional[float] = Field(
        default=None,
        description="Normalized fulltext/BM25 score",
    )
    document_id: str = Field(description="Source document ID")
    document_title: Optional[str] = Field(
        default=None,
        description="Source document title",
    )
    module_id: Optional[str] = Field(
        default=None,
        description="Module ID the result belongs to",
    )
    parent_context: Optional[str] = Field(
        default=None,
        description="Parent chunk text for expanded context",
    )
    entities: List[str] = Field(
        default_factory=list,
        description="Entity names mentioned in this result",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "id": "chunk_doc123_5",
                "node_type": "Chunk",
                "text": "Machine learning algorithms use...",
                "score": 0.85,
                "vector_score": 0.9,
                "fulltext_score": 0.7,
                "document_id": "doc_123",
                "document_title": "Introduction to ML",
                "module_id": "mod_456",
                "parent_context": "Chapter 3: Supervised Learning...",
                "entities": ["Machine Learning", "Neural Networks"],
            }
        }


class SearchResponse(BaseModel):
    """
    Response schema for hybrid search API.

    Contains the search results with metadata about the search.
    """

    query: str = Field(description="The original search query")
    results: List[SearchResult] = Field(
        description="List of search results ranked by score"
    )
    total_count: int = Field(description="Total number of results returned")
    search_time_ms: float = Field(description="Search execution time in milliseconds")
    weights: Dict[str, float] = Field(
        description="Weights used for hybrid search (vector, fulltext)"
    )
    expansion_info: Optional["ExpansionInfo"] = Field(
        default=None,
        description="Information about query expansion if performed",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "query": "machine learning algorithms",
                "results": [
                    {
                        "id": "chunk_doc123_5",
                        "node_type": "Chunk",
                        "text": "Machine learning algorithms...",
                        "score": 0.85,
                        "vector_score": 0.9,
                        "fulltext_score": 0.7,
                        "document_id": "doc_123",
                        "module_id": "mod_456",
                    }
                ],
                "total_count": 1,
                "search_time_ms": 45.2,
                "weights": {"vector": 0.7, "fulltext": 0.3},
                "expansion_info": {
                    "original_query": "machine learning",
                    "expanded_query": "machine learning neural networks deep learning",
                    "expansion_terms": [
                        {
                            "term": "neural networks",
                            "source_entity": "ML",
                            "relationship": "USES",
                            "weight": 0.8,
                        }
                    ],
                    "entities_identified": ["Machine Learning"],
                },
            }
        }


# ============================================================================
# ADDITIONAL SCHEMAS FOR FUTURE USE
# ============================================================================


class QueryAnalysisRequest(BaseModel):
    """Request schema for query analysis (Phase 10-04)."""

    query: str = Field(..., min_length=1, max_length=1000)
    module_ids: Optional[List[str]] = None
    action: str = Field(
        default="summarize",
        description="Analysis action: summarize, compare, extract",
    )


class FeedbackRequest(BaseModel):
    """Request schema for relevance feedback (Phase 10-06)."""

    query: str = Field(..., min_length=1, max_length=1000)
    result_id: str = Field(..., description="ID of the result being rated")
    relevance: int = Field(..., ge=1, le=5, description="Relevance rating 1-5")
    comment: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional feedback comment",
    )


# ============================================================================
# QUERY EXPANSION SCHEMAS
# ============================================================================


class ExpansionTerm(BaseModel):
    """
    Individual term added during query expansion.

    Contains the term itself and metadata about its source.
    """

    term: str = Field(description="The expansion term")
    source_entity: str = Field(description="Entity that this term came from")
    relationship: str = Field(
        description="Relationship type (e.g., DEFINES, USES, RELATED_TO)"
    )
    weight: float = Field(
        ge=0.0,
        le=1.0,
        description="Term weight based on relationship strength",
    )


class ExpansionInfo(BaseModel):
    """
    Information about query expansion performed.

    Returned in search response for transparency.
    """

    original_query: str = Field(description="Original query before expansion")
    expanded_query: str = Field(description="Query after expansion")
    expansion_terms: List[ExpansionTerm] = Field(
        default_factory=list,
        description="Terms added during expansion",
    )
    entities_identified: List[str] = Field(
        default_factory=list,
        description="Entity names identified in the original query",
    )
    expansion_time_ms: float = Field(
        default=0.0,
        description="Time taken for query expansion in milliseconds",
    )


class ExpandedQuery(BaseModel):
    """
    Result of query expansion operation.

    Contains the expanded query and metadata about the expansion process.
    """

    original_query: str = Field(description="Original query text")
    expanded_query: str = Field(description="Expanded query for fulltext search")
    expansion_terms: List[ExpansionTerm] = Field(
        default_factory=list,
        description="Terms added during expansion",
    )
    entities_found: List[str] = Field(
        default_factory=list,
        description="Entity names found in query",
    )
    entity_ids: List[str] = Field(
        default_factory=list,
        description="Entity IDs found in query",
    )
    expansion_time_ms: float = Field(
        default=0.0,
        description="Time taken for query expansion in milliseconds",
    )


# ============================================================================
# GRAPH EXPANSION SCHEMAS
# ============================================================================


class GraphExpansionConfig(BaseModel):
    """Configuration for graph-based entity expansion."""

    enabled: bool = Field(
        default=True,
        description="Whether to expand results via graph traversal",
    )
    max_hops: int = Field(
        default=2,
        ge=1,
        le=4,
        description="Maximum traversal depth (1-4 hops)",
    )
    max_expanded_entities: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum expanded entities to return (1-100)",
    )
    relationship_types: Optional[List[str]] = Field(
        default=None,
        description=(
            "Specific relationship types to traverse. "
            "Options: DEFINES, DEPENDS_ON, USES, SUPPORTS, EXTENDS, "
            "IMPLEMENTS, CONTRADICTS, REFERENCES, RELATED_TO. "
            "If None, all types are traversed."
        ),
    )

    @field_validator("relationship_types")
    @classmethod
    def validate_relationship_types(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate relationship types against allowed values."""
        if v is None:
            return None

        allowed = {
            "DEFINES",
            "DEPENDS_ON",
            "USES",
            "SUPPORTS",
            "EXTENDS",
            "IMPLEMENTS",
            "CONTRADICTS",
            "REFERENCES",
            "RELATED_TO",
        }

        validated = []
        for rel_type in v:
            if rel_type.upper() in allowed:
                validated.append(rel_type.upper())

        return validated if validated else None


class EnrichedSearchRequest(SearchRequest):
    """
    Extended search request with graph expansion configuration.

    Inherits all fields from SearchRequest and adds graph expansion options.

    Example:
        {
            "query": "machine learning algorithms",
            "module_ids": ["mod_123"],
            "top_k": 15,
            "graph_expansion": {
                "enabled": true,
                "max_hops": 2,
                "max_expanded_entities": 20
            }
        }
    """

    graph_expansion: GraphExpansionConfig = Field(
        default_factory=GraphExpansionConfig,
        description="Graph expansion configuration",
    )


class EntityContext(BaseModel):
    """
    Entity discovered through graph traversal.

    Represents a related entity found by expanding the knowledge graph
    from initial search results.
    """

    entity_id: str = Field(description="Unique entity identifier")
    entity_name: str = Field(description="Entity name")
    entity_type: str = Field(
        description="Entity type: Topic, Concept, Methodology, or Finding"
    )
    definition: Optional[str] = Field(
        default=None,
        description="Entity definition text",
    )
    relationship_to_query: str = Field(
        description="Relationship type connecting this entity to the query context",
    )
    hops_from_result: int = Field(
        ge=1,
        le=4,
        description="Number of hops from the original search result",
    )
    relevance_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Computed relevance score based on relationship and distance",
    )


class EntityPath(BaseModel):
    """
    Path representing a relationship between two entities.

    Used to trace how entities are connected through the knowledge graph.
    """

    source_entity: str = Field(description="Name of the source entity")
    target_entity: str = Field(description="Name of the target entity")
    relationship_type: str = Field(
        description="Type of relationship (DEFINES, USES, etc.)"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for this relationship",
    )
    hops: int = Field(
        default=1,
        ge=1,
        le=4,
        description="Number of hops from seed entity",
    )


class EnrichedSearchResult(SearchResult):
    """
    Search result enriched with graph context.

    Extends SearchResult with related entities discovered through
    graph traversal and the paths connecting them.
    """

    related_entities: List[EntityContext] = Field(
        default_factory=list,
        description="Entities discovered through graph expansion",
    )
    graph_paths: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Relationship paths connecting entities to this result",
    )


class GraphContextResponse(BaseModel):
    """
    Graph context summary returned with enriched search results.

    Contains metadata about the graph traversal operation.
    """

    seed_entities: List[str] = Field(
        default_factory=list,
        description="Entity IDs used as seeds for expansion",
    )
    total_expanded: int = Field(
        default=0,
        description="Total number of entities discovered",
    )
    max_depth_reached: int = Field(
        default=0,
        description="Maximum traversal depth reached",
    )
    traversal_time_ms: float = Field(
        default=0.0,
        description="Time taken for graph traversal in milliseconds",
    )


class EnrichedSearchResponse(SearchResponse):
    """
    Extended search response with graph context.

    Inherits from SearchResponse and adds graph expansion results.
    """

    results: List[EnrichedSearchResult] = Field(
        description="List of enriched search results with graph context"
    )
    graph_context: Optional[GraphContextResponse] = Field(
        default=None,
        description="Summary of graph expansion operation",
    )

    class Config:
        """Pydantic configuration."""

        json_schema_extra = {
            "example": {
                "query": "machine learning algorithms",
                "results": [
                    {
                        "id": "chunk_doc123_5",
                        "node_type": "Chunk",
                        "text": "Machine learning algorithms...",
                        "score": 0.85,
                        "vector_score": 0.9,
                        "fulltext_score": 0.7,
                        "document_id": "doc_123",
                        "module_id": "mod_456",
                        "related_entities": [
                            {
                                "entity_id": "concept_nn",
                                "entity_name": "Neural Networks",
                                "entity_type": "Concept",
                                "relationship_to_query": "USES",
                                "hops_from_result": 1,
                                "relevance_score": 0.8,
                            }
                        ],
                        "graph_paths": [
                            {
                                "source_entity": "Machine Learning",
                                "target_entity": "Neural Networks",
                                "relationship_type": "USES",
                                "confidence": 0.95,
                            }
                        ],
                    }
                ],
                "total_count": 1,
                "search_time_ms": 125.3,
                "weights": {"vector": 0.7, "fulltext": 0.3},
                "graph_context": {
                    "seed_entities": ["concept_ml"],
                    "total_expanded": 5,
                    "max_depth_reached": 2,
                    "traversal_time_ms": 45.2,
                },
            }
        }


# ============================================================================
# FORWARD REFERENCE RESOLUTION
# ============================================================================

# Rebuild models to resolve forward references
SearchRequest.model_rebuild()
SearchResponse.model_rebuild()
