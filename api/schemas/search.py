# search.py
# Pydantic schemas for hybrid search API requests and responses

# Defines the API contracts for the /v1/kg/query endpoint including request
# validation, response models, and weight normalization. Ensures consistent
# interface between frontend and RAG engine.

# @see: api/rag_engine.py - Uses these schemas for type safety
# @see: api/routers/query.py - API endpoint using these schemas (Phase 10-04)
# @note: vector_weight + fulltext_weight normalized to 1.0 via validator

from __future__ import annotations

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================


class SearchRequest(BaseModel):
    """
    Request schema for hybrid search API.

    Validates search parameters and normalizes weights.

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
