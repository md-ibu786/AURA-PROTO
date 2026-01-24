# analysis.py
# Pydantic schemas for the analysis API endpoint

# Defines request/response models for AI-powered analysis operations:
# summarization, comparison, extraction, and explanation of content.
# Supports targeting chunks, documents, or entities with configurable options.

# @see: routers/analysis.py - Analysis endpoint using these schemas
# @see: services/analysis_service.py - Business logic for analysis operations
# @note: Union result type requires discriminated handling based on operation

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field


class AnalysisOperation(str, Enum):
    """Supported analysis operations."""

    SUMMARIZE = "summarize"
    COMPARE = "compare"
    EXTRACT = "extract"
    EXPLAIN = "explain"


class AnalysisRequest(BaseModel):
    """Request model for analysis operations.

    Attributes:
        operation: The type of analysis to perform.
        target_ids: List of IDs to analyze (chunk_ids, document_ids, or entity_ids).
        target_type: Type of targets being analyzed. Defaults to "chunk".
        module_ids: Optional list of module IDs to scope the analysis.
        options: Additional operation-specific options.

    Options by operation:
        - summarize: {"max_length": int, "style": "brief"|"detailed"}
        - compare: {"aspects": List[str], "format": "table"|"prose"}
        - extract: {"extraction_type": str, "schema": Dict}
        - explain: {"depth": "simple"|"detailed", "include_examples": bool}
    """

    operation: AnalysisOperation = Field(
        ..., description="The type of analysis to perform"
    )
    target_ids: List[str] = Field(
        ...,
        min_length=1,
        description="List of IDs to analyze (chunk_ids, document_ids, or entity_ids)",
    )
    target_type: Literal["chunk", "document", "entity"] = Field(
        default="chunk", description="Type of targets being analyzed"
    )
    module_ids: Optional[List[str]] = Field(
        default=None, description="Optional list of module IDs to scope the analysis"
    )
    options: Dict[str, Any] = Field(
        default_factory=dict, description="Additional operation-specific options"
    )


class SummaryResult(BaseModel):
    """Result model for summarization operations."""

    summary: str = Field(..., description="The generated summary text")
    key_points: List[str] = Field(
        default_factory=list,
        description="List of key points extracted from the content",
    )
    source_ids: List[str] = Field(
        ..., description="IDs of sources used to generate the summary"
    )


class ComparisonResult(BaseModel):
    """Result model for comparison operations."""

    similarities: List[str] = Field(
        default_factory=list, description="List of similarities between compared items"
    )
    differences: List[str] = Field(
        default_factory=list, description="List of differences between compared items"
    )
    source_a: str = Field(..., description="Identifier for the first comparison source")
    source_b: str = Field(
        ..., description="Identifier for the second comparison source"
    )


class ExtractionResult(BaseModel):
    """Result model for extraction operations."""

    extracted_items: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of extracted items with their properties",
    )
    extraction_type: str = Field(
        ...,
        description="Type of extraction performed (e.g., 'entities', 'dates', 'facts')",
    )
    source_ids: List[str] = Field(
        ..., description="IDs of sources from which items were extracted"
    )


class ExplanationResult(BaseModel):
    """Result model for explanation operations."""

    explanation: str = Field(..., description="The generated explanation text")
    related_concepts: List[str] = Field(
        default_factory=list,
        description="List of related concepts mentioned in the explanation",
    )
    graph_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Graph-based context including related entities and relationships",
    )


class AnalysisResponse(BaseModel):
    """Response model for analysis operations."""

    operation: AnalysisOperation = Field(
        ..., description="The analysis operation that was performed"
    )
    result: Union[
        SummaryResult, ComparisonResult, ExtractionResult, ExplanationResult
    ] = Field(..., description="The result of the analysis, type depends on operation")
    processing_time_ms: float = Field(
        ..., ge=0, description="Time taken to process the analysis in milliseconds"
    )
    model_used: str = Field(
        ..., description="Identifier of the AI model used for analysis"
    )
