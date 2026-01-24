# feedback_manager.py
# Service for storing and retrieving user feedback in Neo4j

# Manages persistence of user feedback on search results and answers to enable
# continuous improvement of the RAG system. Stores feedback as Feedback nodes
# in Neo4j with relationships to the rated content. Supports analytics queries
# for identifying low-quality content and tracking system performance.

# @see: api/schemas/feedback.py - Feedback schema definitions
# @see: api/routers/query.py - Feedback API endpoints
# @note: Feedback nodes are linked to results via FEEDBACK_FOR relationships

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from neo4j import Driver

from api.schemas.feedback import (
    AnswerFeedback,
    FeedbackStats,
    FeedbackType,
    ImplicitFeedback,
    LowQualityResult,
    ResultFeedback,
    compute_query_hash,
)


# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# FEEDBACK MANAGER
# ============================================================================


class FeedbackManager:
    """
    Service for storing and retrieving user feedback in Neo4j.

    Provides methods for:
    - Submitting result relevance feedback
    - Submitting answer quality feedback
    - Recording implicit feedback (clicks, dwell time)
    - Retrieving feedback statistics
    - Identifying low-quality results

    Feedback is stored as Feedback nodes in Neo4j with relationships to
    the chunks/entities being rated. This enables graph-based analytics
    and integration with the knowledge graph.

    Example:
        >>> manager = FeedbackManager(neo4j_driver)
        >>> feedback_id = await manager.submit_result_feedback(
        ...     ResultFeedback(
        ...         query="machine learning",
        ...         result_id="chunk_123",
        ...         result_rank=0,
        ...         relevance_score=0.9,
        ...     )
        ... )
        >>> stats = await manager.get_feedback_stats(module_id="CS101")
    """

    def __init__(self, driver: Driver):
        """
        Initialize FeedbackManager with Neo4j driver.

        Args:
            driver: Neo4j driver instance for database operations.
        """
        self._driver = driver

    # ========================================================================
    # FEEDBACK SUBMISSION
    # ========================================================================

    async def submit_result_feedback(self, feedback: ResultFeedback) -> str:
        """
        Store result relevance feedback in Neo4j.

        Creates a Feedback node and optionally links it to the result node
        if the result exists in the graph.

        Args:
            feedback: Result feedback with relevance score and metadata.

        Returns:
            Unique feedback ID for the stored entry.

        Raises:
            Exception: If Neo4j operation fails.
        """
        feedback_id = f"fb_{uuid.uuid4().hex[:12]}"
        query_hash = feedback.query_hash

        logger.info(
            f"Storing result feedback: result_id={feedback.result_id}, "
            f"relevance={feedback.relevance_score:.2f}"
        )

        try:
            with self._driver.session() as session:
                # Create Feedback node
                result = session.run(
                    """
                    CREATE (f:Feedback {
                        id: $feedback_id,
                        query_hash: $query_hash,
                        query: $query,
                        result_id: $result_id,
                        result_rank: $result_rank,
                        relevance_score: $relevance_score,
                        feedback_type: $feedback_type,
                        user_id: $user_id,
                        session_id: $session_id,
                        module_ids: $module_ids,
                        comment: $comment,
                        timestamp: datetime($timestamp),
                        is_positive: $is_positive
                    })
                    RETURN f.id as id
                    """,
                    {
                        "feedback_id": feedback_id,
                        "query_hash": query_hash,
                        "query": feedback.query[:500],  # Truncate for storage
                        "result_id": feedback.result_id,
                        "result_rank": feedback.result_rank,
                        "relevance_score": feedback.relevance_score,
                        "feedback_type": feedback.feedback_type.value,
                        "user_id": feedback.user_id,
                        "session_id": feedback.session_id,
                        "module_ids": feedback.module_ids,
                        "comment": feedback.comment,
                        "timestamp": feedback.timestamp.isoformat(),
                        "is_positive": feedback.relevance_score >= 0.5,
                    },
                )
                result.single()

                # Try to link to the result node if it exists
                session.run(
                    """
                    MATCH (f:Feedback {id: $feedback_id})
                    OPTIONAL MATCH (r)
                    WHERE r.id = $result_id
                    FOREACH (_ IN CASE WHEN r IS NOT NULL THEN [1] ELSE [] END |
                        MERGE (f)-[:FEEDBACK_FOR]->(r)
                    )
                    """,
                    {
                        "feedback_id": feedback_id,
                        "result_id": feedback.result_id,
                    },
                )

            logger.debug(f"Stored feedback: {feedback_id}")
            return feedback_id

        except Exception as e:
            logger.error(f"Failed to store result feedback: {e}")
            raise

    async def submit_answer_feedback(self, feedback: AnswerFeedback) -> str:
        """
        Store answer quality feedback in Neo4j.

        Creates a Feedback node for answer-level feedback (helpful/not helpful).

        Args:
            feedback: Answer feedback with helpfulness rating and metadata.

        Returns:
            Unique feedback ID for the stored entry.

        Raises:
            Exception: If Neo4j operation fails.
        """
        feedback_id = f"fb_{uuid.uuid4().hex[:12]}"
        query_hash = feedback.query_hash

        logger.info(
            f"Storing answer feedback: answer_hash={feedback.answer_hash[:8]}..., "
            f"helpful={feedback.helpful}"
        )

        try:
            with self._driver.session() as session:
                # Create Feedback node
                result = session.run(
                    """
                    CREATE (f:Feedback {
                        id: $feedback_id,
                        query_hash: $query_hash,
                        query: $query,
                        answer_hash: $answer_hash,
                        helpful: $helpful,
                        accuracy_score: $accuracy_score,
                        feedback_type: $feedback_type,
                        user_id: $user_id,
                        session_id: $session_id,
                        module_ids: $module_ids,
                        comment: $comment,
                        timestamp: datetime($timestamp),
                        is_positive: $is_positive
                    })
                    RETURN f.id as id
                    """,
                    {
                        "feedback_id": feedback_id,
                        "query_hash": query_hash,
                        "query": feedback.query[:500],
                        "answer_hash": feedback.answer_hash,
                        "helpful": feedback.helpful,
                        "accuracy_score": feedback.accuracy_score,
                        "feedback_type": feedback.feedback_type.value,
                        "user_id": feedback.user_id,
                        "session_id": feedback.session_id,
                        "module_ids": feedback.module_ids,
                        "comment": feedback.comment,
                        "timestamp": feedback.timestamp.isoformat(),
                        "is_positive": feedback.helpful,
                    },
                )
                result.single()

            logger.debug(f"Stored answer feedback: {feedback_id}")
            return feedback_id

        except Exception as e:
            logger.error(f"Failed to store answer feedback: {e}")
            raise

    async def submit_implicit_feedback(self, feedback: ImplicitFeedback) -> str:
        """
        Store implicit feedback signals (clicks, dwell time).

        Creates a Feedback node for implicit behavioral signals.

        Args:
            feedback: Implicit feedback with click/dwell time data.

        Returns:
            Unique feedback ID for the stored entry.

        Raises:
            Exception: If Neo4j operation fails.
        """
        feedback_id = f"fb_{uuid.uuid4().hex[:12]}"
        query_hash = feedback.query_hash

        # Infer positivity from implicit signals
        is_positive = True  # Clicks are positive
        if feedback.feedback_type == FeedbackType.DWELL_TIME:
            # Dwell time > 5 seconds is considered positive
            is_positive = (feedback.dwell_time_ms or 0) > 5000

        logger.debug(
            f"Storing implicit feedback: type={feedback.feedback_type.value}, "
            f"result_id={feedback.result_id}"
        )

        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    CREATE (f:Feedback {
                        id: $feedback_id,
                        query_hash: $query_hash,
                        query: $query,
                        result_id: $result_id,
                        result_rank: $result_rank,
                        feedback_type: $feedback_type,
                        dwell_time_ms: $dwell_time_ms,
                        user_id: $user_id,
                        session_id: $session_id,
                        timestamp: datetime($timestamp),
                        is_positive: $is_positive
                    })
                    RETURN f.id as id
                    """,
                    {
                        "feedback_id": feedback_id,
                        "query_hash": query_hash,
                        "query": feedback.query[:500],
                        "result_id": feedback.result_id,
                        "result_rank": feedback.result_rank,
                        "feedback_type": feedback.feedback_type.value,
                        "dwell_time_ms": feedback.dwell_time_ms,
                        "user_id": feedback.user_id,
                        "session_id": feedback.session_id,
                        "timestamp": feedback.timestamp.isoformat(),
                        "is_positive": is_positive,
                    },
                )
                result.single()

                # Try to link to the result node
                session.run(
                    """
                    MATCH (f:Feedback {id: $feedback_id})
                    OPTIONAL MATCH (r)
                    WHERE r.id = $result_id
                    FOREACH (_ IN CASE WHEN r IS NOT NULL THEN [1] ELSE [] END |
                        MERGE (f)-[:FEEDBACK_FOR]->(r)
                    )
                    """,
                    {
                        "feedback_id": feedback_id,
                        "result_id": feedback.result_id,
                    },
                )

            return feedback_id

        except Exception as e:
            logger.error(f"Failed to store implicit feedback: {e}")
            raise

    # ========================================================================
    # FEEDBACK RETRIEVAL
    # ========================================================================

    async def get_feedback_for_query(self, query_hash: str) -> List[Dict[str, Any]]:
        """
        Get all feedback for a specific query (by hash).

        Args:
            query_hash: SHA-256 hash of the normalized query.

        Returns:
            List of feedback records matching the query hash.
        """
        logger.debug(f"Retrieving feedback for query_hash: {query_hash[:16]}...")

        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (f:Feedback {query_hash: $query_hash})
                    RETURN f {
                        .id, .query, .result_id, .answer_hash,
                        .relevance_score, .helpful, .feedback_type,
                        .is_positive, .comment,
                        timestamp: toString(f.timestamp)
                    } as feedback
                    ORDER BY f.timestamp DESC
                    LIMIT 100
                    """,
                    {"query_hash": query_hash},
                )

                return [record["feedback"] for record in result]

        except Exception as e:
            logger.error(f"Failed to retrieve feedback: {e}")
            return []

    async def get_feedback_stats(
        self,
        module_id: Optional[str] = None,
        time_range: Optional[Tuple[datetime, datetime]] = None,
    ) -> FeedbackStats:
        """
        Get aggregated feedback statistics.

        Args:
            module_id: Optional module ID to filter stats.
            time_range: Optional (start, end) datetime tuple.

        Returns:
            FeedbackStats with aggregated metrics.
        """
        logger.info(f"Calculating feedback stats: module_id={module_id}")

        try:
            with self._driver.session() as session:
                # Build WHERE clause
                conditions = ["TRUE"]
                params: Dict[str, Any] = {}

                if module_id:
                    conditions.append("$module_id IN f.module_ids")
                    params["module_id"] = module_id

                if time_range:
                    conditions.append("f.timestamp >= datetime($start)")
                    conditions.append("f.timestamp <= datetime($end)")
                    params["start"] = time_range[0].isoformat()
                    params["end"] = time_range[1].isoformat()

                where_clause = " AND ".join(conditions)

                # Get total counts and averages
                stats_result = session.run(
                    f"""
                    MATCH (f:Feedback)
                    WHERE {where_clause}
                    RETURN
                        count(f) as total,
                        avg(CASE WHEN f.is_positive THEN 1.0 ELSE 0.0 END) as positive_ratio,
                        avg(COALESCE(f.relevance_score, 
                            CASE WHEN f.helpful THEN 1.0 
                                 WHEN f.helpful = false THEN 0.0 
                                 ELSE 0.5 END)) as avg_relevance
                    """,
                    params,
                )
                stats = stats_result.single()

                total = stats["total"] or 0
                positive_ratio = stats["positive_ratio"] or 0.0
                avg_relevance = stats["avg_relevance"] or 0.0

                # Get counts by feedback type
                type_result = session.run(
                    f"""
                    MATCH (f:Feedback)
                    WHERE {where_clause}
                    RETURN f.feedback_type as type, count(f) as count
                    """,
                    params,
                )
                feedback_by_type = {
                    record["type"]: record["count"] for record in type_result
                }

                # Get counts by module
                module_result = session.run(
                    f"""
                    MATCH (f:Feedback)
                    WHERE {where_clause}
                    UNWIND f.module_ids as module
                    RETURN module, count(f) as count
                    ORDER BY count DESC
                    LIMIT 20
                    """,
                    params,
                )
                feedback_by_module = {
                    record["module"]: record["count"] for record in module_result
                }

            return FeedbackStats(
                total_feedback_count=total,
                positive_feedback_ratio=positive_ratio,
                average_relevance_score=avg_relevance,
                feedback_by_type=feedback_by_type,
                feedback_by_module=feedback_by_module,
                time_range_start=time_range[0] if time_range else None,
                time_range_end=time_range[1] if time_range else None,
            )

        except Exception as e:
            logger.error(f"Failed to calculate feedback stats: {e}")
            return FeedbackStats(
                total_feedback_count=0,
                positive_feedback_ratio=0.0,
                average_relevance_score=0.0,
                feedback_by_type={},
                feedback_by_module={},
            )

    async def get_low_quality_results(
        self,
        threshold: float = 0.3,
        limit: int = 50,
    ) -> List[LowQualityResult]:
        """
        Get results that consistently receive low relevance scores.

        Identifies chunks/entities that may need content quality review
        based on user feedback patterns.

        Args:
            threshold: Maximum average relevance score (0.0-1.0).
            limit: Maximum number of results to return.

        Returns:
            List of LowQualityResult with problem content.
        """
        logger.info(f"Finding low-quality results: threshold={threshold}")

        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (f:Feedback)
                    WHERE f.result_id IS NOT NULL
                      AND f.relevance_score IS NOT NULL
                    WITH f.result_id as result_id,
                         avg(f.relevance_score) as avg_relevance,
                         count(f) as feedback_count,
                         collect(DISTINCT f.query)[..5] as sample_queries
                    WHERE avg_relevance <= $threshold
                      AND feedback_count >= 2
                    OPTIONAL MATCH (r) WHERE r.id = result_id
                    RETURN result_id,
                           COALESCE(labels(r)[0], 'Unknown') as result_type,
                           avg_relevance,
                           feedback_count,
                           sample_queries
                    ORDER BY avg_relevance ASC, feedback_count DESC
                    LIMIT $limit
                    """,
                    {"threshold": threshold, "limit": limit},
                )

                low_quality = []
                for record in result:
                    low_quality.append(
                        LowQualityResult(
                            result_id=record["result_id"],
                            result_type=record["result_type"],
                            average_relevance=record["avg_relevance"],
                            feedback_count=record["feedback_count"],
                            sample_queries=record["sample_queries"] or [],
                        )
                    )

                logger.info(f"Found {len(low_quality)} low-quality results")
                return low_quality

        except Exception as e:
            logger.error(f"Failed to find low-quality results: {e}")
            return []

    # ========================================================================
    # UTILITY METHODS
    # ========================================================================

    async def delete_old_feedback(self, days: int = 90) -> int:
        """
        Delete feedback older than specified days.

        Args:
            days: Number of days to keep feedback (default 90).

        Returns:
            Number of deleted feedback entries.
        """
        logger.info(f"Deleting feedback older than {days} days")

        try:
            with self._driver.session() as session:
                result = session.run(
                    """
                    MATCH (f:Feedback)
                    WHERE f.timestamp < datetime() - duration({days: $days})
                    WITH f LIMIT 1000
                    DETACH DELETE f
                    RETURN count(*) as deleted
                    """,
                    {"days": days},
                )
                deleted = result.single()["deleted"]

            logger.info(f"Deleted {deleted} old feedback entries")
            return deleted

        except Exception as e:
            logger.error(f"Failed to delete old feedback: {e}")
            return 0
