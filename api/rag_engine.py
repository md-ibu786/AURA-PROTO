# rag_engine.py
# Hybrid RAG engine combining vector search and fulltext search for AURA-NOTES-MANAGER

# Implements hybrid search with weighted combination of vector similarity (0.7) and
# fulltext matching (0.3). Searches across Chunk, ParentChunk, and Entity nodes
# with module_id filtering for scoped queries. Supports configurable weights and top_k.

# @see: api/kg_processor.py - Document processing and chunk creation
# @see: api/neo4j_config.py - Neo4j configuration with vector/fulltext indices
# @see: services/embeddings.py - Query embedding generation
# @note: Latency target < 500ms for hybrid search

from __future__ import annotations

import time
import logging
from typing import List, Dict, Any, Optional, Literal

from pydantic import BaseModel, Field

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# Retrieval weights for hybrid search
VECTOR_WEIGHT = 0.7  # Weight for vector similarity scores
FULLTEXT_WEIGHT = 0.3  # Weight for fulltext/BM25 scores

# Retrieval parameters
TOP_K_RETRIEVAL = 15  # Default number of results to return
MIN_SCORE_THRESHOLD = 0.3  # Minimum combined score threshold

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)

# ============================================================================
# DATA MODELS
# ============================================================================


class SearchResult(BaseModel):
    """Individual search result from hybrid search."""

    id: str
    node_type: Literal["Chunk", "ParentChunk", "Entity"]
    text: str
    score: float
    vector_score: Optional[float] = None
    fulltext_score: Optional[float] = None
    document_id: str
    module_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SearchResults(BaseModel):
    """Container for search results with metadata."""

    query: str
    results: List[SearchResult]
    total_count: int
    search_time_ms: float
    weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "vector": VECTOR_WEIGHT,
            "fulltext": FULLTEXT_WEIGHT,
        }
    )


# ============================================================================
# RAG ENGINE CLASS
# ============================================================================


class RAGEngine:
    """
    Hybrid search RAG engine for AURA-NOTES-MANAGER.

    Combines vector similarity search with fulltext search for improved retrieval
    quality. Supports module_id filtering for scoped queries.

    Features:
    - Vector search (0.7 weight) using Neo4j vector indices
    - Fulltext search (0.3 weight) using Neo4j fulltext indices
    - Module filtering for multi-tenant scenarios
    - Parent chunk context retrieval
    - Configurable weights and top_k parameters

    Example:
        from api.rag_engine import RAGEngine
        from api.neo4j_config import neo4j_driver
        from services.embeddings import EmbeddingService

        embedding_service = EmbeddingService()
        engine = RAGEngine(neo4j_driver, embedding_service)

        results = await engine.search(
            query="machine learning algorithms",
            module_ids=["module_123"],
            top_k=10
        )
    """

    def __init__(
        self,
        neo4j_driver,
        embedding_service,
        vector_weight: float = VECTOR_WEIGHT,
        fulltext_weight: float = FULLTEXT_WEIGHT,
    ):
        """
        Initialize RAG engine.

        Args:
            neo4j_driver: Neo4j driver instance for database queries
            embedding_service: Service for generating query embeddings
            vector_weight: Weight for vector search scores (default: 0.7)
            fulltext_weight: Weight for fulltext search scores (default: 0.3)
        """
        self.driver = neo4j_driver
        self.embedding_service = embedding_service
        self.vector_weight = vector_weight
        self.fulltext_weight = fulltext_weight

        logger.info(
            f"RAGEngine initialized with weights: vector={vector_weight}, "
            f"fulltext={fulltext_weight}"
        )

    async def search(
        self,
        query: str,
        module_ids: Optional[List[str]] = None,
        top_k: int = TOP_K_RETRIEVAL,
        vector_weight: Optional[float] = None,
        fulltext_weight: Optional[float] = None,
        min_score: float = MIN_SCORE_THRESHOLD,
        include_parent_context: bool = True,
    ) -> SearchResults:
        """
        Perform hybrid search combining vector and fulltext search.

        Args:
            query: Search query text
            module_ids: Optional list of module IDs to filter by
            top_k: Number of results to return (default: 15)
            vector_weight: Override default vector weight
            fulltext_weight: Override default fulltext weight
            min_score: Minimum combined score threshold
            include_parent_context: Whether to fetch parent chunk context

        Returns:
            SearchResults containing ranked results with scores
        """
        start_time = time.time()

        # Use instance weights if not overridden
        vec_weight = vector_weight if vector_weight is not None else self.vector_weight
        ft_weight = (
            fulltext_weight if fulltext_weight is not None else self.fulltext_weight
        )

        # Normalize weights to sum to 1.0
        total_weight = vec_weight + ft_weight
        if total_weight > 0:
            vec_weight = vec_weight / total_weight
            ft_weight = ft_weight / total_weight
        else:
            vec_weight = 0.7
            ft_weight = 0.3

        logger.info(
            f"Hybrid search: query='{query[:50]}...', module_ids={module_ids}, "
            f"top_k={top_k}, weights=(v={vec_weight:.2f}, f={ft_weight:.2f})"
        )

        try:
            # Generate query embedding
            query_embedding = self.embedding_service.embed_text(query)

            if not query_embedding or len(query_embedding) != 768:
                logger.warning(
                    f"Invalid query embedding (len={len(query_embedding) if query_embedding else 0})"
                )
                return SearchResults(
                    query=query,
                    results=[],
                    total_count=0,
                    search_time_ms=(time.time() - start_time) * 1000,
                    weights={"vector": vec_weight, "fulltext": ft_weight},
                )

            # Execute vector and fulltext search in parallel-ish manner
            vector_results = await self._vector_search(
                query_embedding, module_ids, top_k * 2
            )
            fulltext_results = await self._fulltext_search(query, module_ids, top_k * 2)

            # Combine results with weighted scoring
            combined_results = self._combine_results(
                vector_results, fulltext_results, vec_weight, ft_weight
            )

            # Filter by minimum score
            filtered_results = [r for r in combined_results if r.score >= min_score]

            # Limit to top_k
            filtered_results = filtered_results[:top_k]

            # Fetch parent context if requested
            if include_parent_context and filtered_results:
                chunk_ids = [r.id for r in filtered_results if r.node_type == "Chunk"]
                if chunk_ids:
                    parent_context = await self._get_parent_context(chunk_ids)
                    for result in filtered_results:
                        if result.id in parent_context:
                            result.metadata["parent_text"] = parent_context[result.id]

            elapsed_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Hybrid search completed: {len(filtered_results)} results in {elapsed_ms:.1f}ms"
            )

            return SearchResults(
                query=query,
                results=filtered_results,
                total_count=len(filtered_results),
                search_time_ms=elapsed_ms,
                weights={"vector": vec_weight, "fulltext": ft_weight},
            )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"Hybrid search failed: {e}")
            return SearchResults(
                query=query,
                results=[],
                total_count=0,
                search_time_ms=elapsed_ms,
                weights={"vector": vec_weight, "fulltext": ft_weight},
            )

    async def _vector_search(
        self,
        query_embedding: List[float],
        module_ids: Optional[List[str]],
        top_k: int,
    ) -> List[SearchResult]:
        """
        Perform vector similarity search using Neo4j vector index.

        Args:
            query_embedding: 768-dimensional query embedding
            module_ids: Optional module IDs for filtering
            top_k: Number of results to retrieve

        Returns:
            List of SearchResult objects with vector scores
        """
        try:
            # Build query with optional module filtering
            if module_ids:
                cypher = """
                CALL db.index.vector.queryNodes('chunk_vector_index', $top_k, $query_embedding)
                YIELD node, score
                MATCH (d:Document)-[:HAS_CHUNK]->(node)
                WHERE node.module_id IN $module_ids OR d.module_id IN $module_ids
                RETURN node.id as id, 'Chunk' as node_type, node.text as text, score,
                       d.id as document_id, COALESCE(node.module_id, d.module_id) as module_id
                ORDER BY score DESC
                LIMIT $top_k
                """
                params = {
                    "query_embedding": query_embedding,
                    "module_ids": module_ids,
                    "top_k": top_k,
                }
            else:
                cypher = """
                CALL db.index.vector.queryNodes('chunk_vector_index', $top_k, $query_embedding)
                YIELD node, score
                MATCH (d:Document)-[:HAS_CHUNK]->(node)
                RETURN node.id as id, 'Chunk' as node_type, node.text as text, score,
                       d.id as document_id, COALESCE(node.module_id, d.module_id) as module_id
                ORDER BY score DESC
                LIMIT $top_k
                """
                params = {
                    "query_embedding": query_embedding,
                    "top_k": top_k,
                }

            results = []
            with self.driver.session() as session:
                result = session.run(cypher, params)
                for record in result:
                    results.append(
                        SearchResult(
                            id=record["id"],
                            node_type=record["node_type"],
                            text=record["text"] or "",
                            score=float(record["score"]),
                            vector_score=float(record["score"]),
                            fulltext_score=None,
                            document_id=record["document_id"] or "",
                            module_id=record["module_id"],
                        )
                    )

            logger.debug(f"Vector search returned {len(results)} results")
            return results

        except Exception as e:
            logger.warning(f"Vector search failed: {e}")
            return []

    async def _fulltext_search(
        self,
        query: str,
        module_ids: Optional[List[str]],
        top_k: int,
    ) -> List[SearchResult]:
        """
        Perform fulltext search using Neo4j fulltext index.

        Args:
            query: Search query text
            module_ids: Optional module IDs for filtering
            top_k: Number of results to retrieve

        Returns:
            List of SearchResult objects with fulltext scores
        """
        try:
            # Escape special characters in query for Lucene
            escaped_query = self._escape_lucene_query(query)

            if module_ids:
                cypher = """
                CALL db.index.fulltext.queryNodes('chunk_fulltext_index', $query)
                YIELD node, score
                MATCH (d:Document)-[:HAS_CHUNK]->(node)
                WHERE node.module_id IN $module_ids OR d.module_id IN $module_ids
                RETURN node.id as id, 'Chunk' as node_type, node.text as text, score,
                       d.id as document_id, COALESCE(node.module_id, d.module_id) as module_id
                ORDER BY score DESC
                LIMIT $top_k
                """
                params = {
                    "query": escaped_query,
                    "module_ids": module_ids,
                    "top_k": top_k,
                }
            else:
                cypher = """
                CALL db.index.fulltext.queryNodes('chunk_fulltext_index', $query)
                YIELD node, score
                MATCH (d:Document)-[:HAS_CHUNK]->(node)
                RETURN node.id as id, 'Chunk' as node_type, node.text as text, score,
                       d.id as document_id, COALESCE(node.module_id, d.module_id) as module_id
                ORDER BY score DESC
                LIMIT $top_k
                """
                params = {
                    "query": escaped_query,
                    "top_k": top_k,
                }

            results = []
            with self.driver.session() as session:
                result = session.run(cypher, params)
                for record in result:
                    results.append(
                        SearchResult(
                            id=record["id"],
                            node_type=record["node_type"],
                            text=record["text"] or "",
                            score=float(record["score"]),
                            vector_score=None,
                            fulltext_score=float(record["score"]),
                            document_id=record["document_id"] or "",
                            module_id=record["module_id"],
                        )
                    )

            logger.debug(f"Fulltext search returned {len(results)} results")
            return results

        except Exception as e:
            logger.warning(f"Fulltext search failed: {e}")
            return []

    def _combine_results(
        self,
        vector_results: List[SearchResult],
        fulltext_results: List[SearchResult],
        vector_weight: float,
        fulltext_weight: float,
    ) -> List[SearchResult]:
        """
        Combine vector and fulltext results with weighted scoring.

        Algorithm:
        1. Normalize scores to 0-1 range for each result set
        2. Apply weights: combined_score = (vector_score * weight) + (fulltext_score * weight)
        3. Handle results appearing in only one search (use 0 for missing)
        4. Sort by combined score, deduplicate by id

        Args:
            vector_results: Results from vector search
            fulltext_results: Results from fulltext search
            vector_weight: Weight for vector scores
            fulltext_weight: Weight for fulltext scores

        Returns:
            Deduplicated, sorted list of combined SearchResult objects
        """
        # Build lookup dictionaries
        combined: Dict[str, SearchResult] = {}

        # Normalize vector scores (max normalization)
        max_vector = max((r.vector_score or 0 for r in vector_results), default=1.0)
        if max_vector == 0:
            max_vector = 1.0

        # Normalize fulltext scores
        max_fulltext = max(
            (r.fulltext_score or 0 for r in fulltext_results), default=1.0
        )
        if max_fulltext == 0:
            max_fulltext = 1.0

        # Add vector results
        for result in vector_results:
            norm_score = (result.vector_score or 0) / max_vector
            combined_score = norm_score * vector_weight

            combined[result.id] = SearchResult(
                id=result.id,
                node_type=result.node_type,
                text=result.text,
                score=combined_score,
                vector_score=norm_score,
                fulltext_score=0.0,
                document_id=result.document_id,
                module_id=result.module_id,
                metadata=result.metadata,
            )

        # Add or merge fulltext results
        for result in fulltext_results:
            norm_score = (result.fulltext_score or 0) / max_fulltext
            ft_contribution = norm_score * fulltext_weight

            if result.id in combined:
                # Merge: add fulltext contribution
                existing = combined[result.id]
                combined[result.id] = SearchResult(
                    id=existing.id,
                    node_type=existing.node_type,
                    text=existing.text,
                    score=existing.score + ft_contribution,
                    vector_score=existing.vector_score,
                    fulltext_score=norm_score,
                    document_id=existing.document_id,
                    module_id=existing.module_id,
                    metadata=existing.metadata,
                )
            else:
                # New result from fulltext only
                combined[result.id] = SearchResult(
                    id=result.id,
                    node_type=result.node_type,
                    text=result.text,
                    score=ft_contribution,
                    vector_score=0.0,
                    fulltext_score=norm_score,
                    document_id=result.document_id,
                    module_id=result.module_id,
                    metadata=result.metadata,
                )

        # Sort by combined score descending
        sorted_results = sorted(combined.values(), key=lambda x: x.score, reverse=True)

        logger.debug(
            f"Combined {len(vector_results)} vector + {len(fulltext_results)} fulltext "
            f"= {len(sorted_results)} unique results"
        )

        return sorted_results

    async def _get_parent_context(self, chunk_ids: List[str]) -> Dict[str, str]:
        """
        Fetch parent chunk text for given child chunk IDs.

        Args:
            chunk_ids: List of chunk IDs to look up parents for

        Returns:
            Dict mapping chunk_id to parent chunk text
        """
        if not chunk_ids:
            return {}

        try:
            cypher = """
            MATCH (p:ParentChunk)-[:HAS_CHILD]->(c:Chunk)
            WHERE c.id IN $chunk_ids
            RETURN c.id as chunk_id, p.text as parent_text
            """

            parent_context = {}
            with self.driver.session() as session:
                result = session.run(cypher, {"chunk_ids": chunk_ids})
                for record in result:
                    parent_context[record["chunk_id"]] = record["parent_text"]

            logger.debug(f"Retrieved parent context for {len(parent_context)} chunks")
            return parent_context

        except Exception as e:
            logger.warning(f"Failed to get parent context: {e}")
            return {}

    def _escape_lucene_query(self, query: str) -> str:
        """
        Escape special Lucene characters in query string.

        Args:
            query: Raw query string

        Returns:
            Escaped query string safe for Lucene fulltext index
        """
        # Lucene special characters: + - && || ! ( ) { } [ ] ^ " ~ * ? : \ /
        special_chars = [
            "+",
            "-",
            "&&",
            "||",
            "!",
            "(",
            ")",
            "{",
            "}",
            "[",
            "]",
            "^",
            '"',
            "~",
            "*",
            "?",
            ":",
            "\\",
            "/",
        ]

        escaped = query
        for char in special_chars:
            escaped = escaped.replace(char, f"\\{char}")

        return escaped


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def create_rag_engine(
    neo4j_driver=None,
    embedding_service=None,
    vector_weight: float = VECTOR_WEIGHT,
    fulltext_weight: float = FULLTEXT_WEIGHT,
) -> RAGEngine:
    """
    Factory function to create RAGEngine with default dependencies.

    Args:
        neo4j_driver: Optional Neo4j driver (uses global if not provided)
        embedding_service: Optional embedding service (creates new if not provided)
        vector_weight: Weight for vector search scores
        fulltext_weight: Weight for fulltext search scores

    Returns:
        Configured RAGEngine instance
    """
    # Import lazily to avoid circular imports
    if neo4j_driver is None:
        from api.neo4j_config import neo4j_driver as default_driver

        neo4j_driver = default_driver

    if embedding_service is None:
        from services.embeddings import EmbeddingService

        embedding_service = EmbeddingService()

    return RAGEngine(
        neo4j_driver=neo4j_driver,
        embedding_service=embedding_service,
        vector_weight=vector_weight,
        fulltext_weight=fulltext_weight,
    )
