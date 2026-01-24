# feedback.py
# Pydantic schemas for user feedback on search results and answers

# Defines data models for capturing explicit and implicit user feedback
# on search result relevance and answer quality. Supports analytics and
# continuous improvement of the RAG system through relevance judgments.

# @see: api/feedback_manager.py - FeedbackManager service
# @see: api/routers/query.py - Feedback endpoints
# @note: Query hash is SHA-256 of normalized query for grouping

from __future__ import annotations

import hashlib
import re
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


# ============================================================================
# ENUMS
# ============================================================================


class FeedbackType(str, Enum):
    """Types of user feedback that can be submitted."""

    RESULT_RELEVANCE = "result_relevance"  # Explicit relevance rating
    ANSWER_QUALITY = "answer_quality"  # Helpful/not helpful
    ANSWER_ACCURACY = "answer_accuracy"  # Factual accuracy rating
    CLICK = "click"  # Implicit: user clicked on result
    DWELL_TIME = "dwell_time"  # Implicit: time spent viewing


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================


class ResultFeedback(BaseModel):
    """
    Feedback on a specific search result's relevance.

    Used when a user rates how relevant a particular chunk or entity
    was to their query. Supports both explicit ratings and implicit signals.
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The original query text",
    )
    result_id: str = Field(
        ...,
        min_length=1,
        description="ID of the chunk or entity being rated",
    )
    result_rank: int = Field(
        ...,
        ge=0,
        description="Position of result in the search results (0-indexed)",
    )
    relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Relevance rating: 0=irrelevant, 1=highly relevant",
    )
    feedback_type: FeedbackType = Field(
        default=FeedbackType.RESULT_RELEVANCE,
        description="Type of feedback being submitted",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Optional user ID for tracking (anonymized)",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for grouping related feedback",
    )
    module_ids: List[str] = Field(
        default_factory=list,
        description="Module IDs the search was scoped to",
    )
    comment: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional free-text comment",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When feedback was submitted",
    )

    @property
    def query_hash(self) -> str:
        """Compute SHA-256 hash of normalized query for grouping."""
        return compute_query_hash(self.query)


class AnswerFeedback(BaseModel):
    """
    Feedback on a synthesized answer's quality and accuracy.

    Used when a user rates the overall answer generated from search results.
    Captures both binary helpful/not-helpful and optional accuracy rating.
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The original query text",
    )
    answer_hash: str = Field(
        ...,
        min_length=1,
        description="Hash of the answer text for tracking",
    )
    helpful: bool = Field(
        ...,
        description="Whether the answer was helpful (thumbs up/down)",
    )
    accuracy_score: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Optional accuracy rating: 0=inaccurate, 1=accurate",
    )
    feedback_type: FeedbackType = Field(
        default=FeedbackType.ANSWER_QUALITY,
        description="Type of feedback being submitted",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Optional user ID for tracking (anonymized)",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for grouping related feedback",
    )
    module_ids: List[str] = Field(
        default_factory=list,
        description="Module IDs the search was scoped to",
    )
    comment: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Optional free-text comment explaining rating",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When feedback was submitted",
    )

    @property
    def query_hash(self) -> str:
        """Compute SHA-256 hash of normalized query for grouping."""
        return compute_query_hash(self.query)


class ImplicitFeedback(BaseModel):
    """
    Implicit feedback signals from user behavior.

    Captures click-through and dwell time signals that can indicate
    relevance without requiring explicit user input.
    """

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The original query text",
    )
    result_id: str = Field(
        ...,
        min_length=1,
        description="ID of the chunk or entity interacted with",
    )
    result_rank: int = Field(
        ...,
        ge=0,
        description="Position of result in the search results",
    )
    feedback_type: FeedbackType = Field(
        ...,
        description="Type of implicit signal (click, dwell_time)",
    )
    dwell_time_ms: Optional[int] = Field(
        default=None,
        ge=0,
        description="Time spent viewing in milliseconds (for dwell_time type)",
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Optional user ID for tracking",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Session ID for grouping related events",
    )
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="When the event occurred",
    )

    @field_validator("feedback_type")
    @classmethod
    def validate_implicit_type(cls, v: FeedbackType) -> FeedbackType:
        """Ensure feedback type is an implicit signal."""
        if v not in (FeedbackType.CLICK, FeedbackType.DWELL_TIME):
            raise ValueError(
                f"ImplicitFeedback requires feedback_type of 'click' or "
                f"'dwell_time', got '{v}'"
            )
        return v

    @property
    def query_hash(self) -> str:
        """Compute SHA-256 hash of normalized query for grouping."""
        return compute_query_hash(self.query)


# ============================================================================
# RESPONSE SCHEMAS
# ============================================================================


class FeedbackResponse(BaseModel):
    """Response after successfully submitting feedback."""

    feedback_id: str = Field(
        ...,
        description="Unique ID of the stored feedback",
    )
    status: str = Field(
        default="success",
        description="Status of the feedback submission",
    )
    message: str = Field(
        default="Feedback recorded successfully",
        description="Human-readable status message",
    )


class FeedbackStats(BaseModel):
    """Aggregated feedback statistics."""

    total_feedback_count: int = Field(
        ...,
        description="Total number of feedback entries",
    )
    positive_feedback_ratio: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Ratio of positive feedback (helpful=true, high relevance)",
    )
    average_relevance_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average relevance score from result feedback",
    )
    feedback_by_type: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of feedback entries by type",
    )
    feedback_by_module: Dict[str, int] = Field(
        default_factory=dict,
        description="Count of feedback entries by module",
    )
    time_range_start: Optional[datetime] = Field(
        default=None,
        description="Start of the time range for these stats",
    )
    time_range_end: Optional[datetime] = Field(
        default=None,
        description="End of the time range for these stats",
    )


class LowQualityResult(BaseModel):
    """Result that consistently receives low relevance scores."""

    result_id: str = Field(
        ...,
        description="ID of the low-quality chunk or entity",
    )
    result_type: str = Field(
        ...,
        description="Type of result (Chunk, Topic, Concept, etc.)",
    )
    average_relevance: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Average relevance score received",
    )
    feedback_count: int = Field(
        ...,
        ge=1,
        description="Number of feedback entries for this result",
    )
    sample_queries: List[str] = Field(
        default_factory=list,
        max_length=5,
        description="Sample queries where this result appeared",
    )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def compute_query_hash(query: str) -> str:
    """
    Compute SHA-256 hash of normalized query.

    Normalizes query by:
    - Converting to lowercase
    - Removing punctuation
    - Collapsing whitespace

    Args:
        query: The query text to hash.

    Returns:
        SHA-256 hex digest of the normalized query.
    """
    # Normalize: lowercase, remove punctuation, collapse whitespace
    normalized = query.lower()
    normalized = re.sub(r"[^\w\s]", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    # Compute SHA-256 hash
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def compute_answer_hash(answer: str) -> str:
    """
    Compute SHA-256 hash of an answer for tracking.

    Uses first 500 characters to avoid hashing very long answers.

    Args:
        answer: The answer text to hash.

    Returns:
        SHA-256 hex digest of the answer prefix.
    """
    # Use first 500 chars to avoid very long hashes
    prefix = answer[:500] if len(answer) > 500 else answer
    return hashlib.sha256(prefix.encode("utf-8")).hexdigest()
