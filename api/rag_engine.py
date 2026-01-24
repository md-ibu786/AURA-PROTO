# rag_engine.py
# Hybrid RAG engine combining vector search, fulltext search, and graph traversal

# Implements hybrid search with weighted combination of vector similarity (0.7) and
# fulltext matching (0.3). Enhanced with graph traversal for multi-hop entity expansion
# supporting 2-hop reasoning queries. Searches across Chunk, ParentChunk, and Entity nodes
# with module_id filtering for scoped queries. Supports configurable weights and top_k.

# @see: api/kg_processor.py - Document processing and chunk creation
# @see: api/neo4j_config.py - Neo4j configuration with vector/fulltext indices
# @see: api/graph_manager.py - Graph traversal operations
# @see: services/embeddings.py - Query embedding generation
# @note: Latency target < 500ms for hybrid search, < 700ms with graph expansion

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

# Graph traversal parameters
GRAPH_HOP_DEPTH = 2  # Default number of hops for graph expansion
MAX_GRAPH_HOP_DEPTH = 4  # Maximum allowed hop depth
PARENT_CHUNK_BOOST = 1.2  # Score boost for parent chunk context
MAX_EXPANDED_ENTITIES = 20  # Maximum entities from graph expansion

# Query expansion parameters
MAX_EXPANSION_TERMS = 10  # Maximum terms to add during expansion
MIN_EXPANSION_TERM_WEIGHT = 0.3  # Minimum weight for expansion terms
ENTITY_SIMILARITY_THRESHOLD = 0.7  # Min similarity for entity matching

# Relationship type weights for ranking (higher = stronger semantic connection)
RELATIONSHIP_WEIGHTS = {
    "DEFINES": 1.0,
    "DEPENDS_ON": 0.9,
    "USES": 0.8,
    "SUPPORTS": 0.8,
    "EXTENDS": 0.7,
    "IMPLEMENTS": 0.7,
    "CONTRADICTS": 0.6,
    "REFERENCES": 0.5,
    "RELATED_TO": 0.4,
}

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


class EntityPath(BaseModel):
    """Represents a path between two entities in the graph."""

    source_entity: str
    target_entity: str
    relationship_type: str
    confidence: float = 1.0
    hops: int = 1


class GraphContext(BaseModel):
    """Container for expanded graph context from entity traversal."""

    seed_entities: List[str] = Field(default_factory=list)
    expanded_entities: List[Dict[str, Any]] = Field(default_factory=list)
    paths: List[EntityPath] = Field(default_factory=list)
    total_entities: int = 0
    max_depth_reached: int = 0
    traversal_time_ms: float = 0.0


class EnrichedSearchResult(BaseModel):
    """Search result enriched with graph context."""

    id: str
    node_type: Literal["Chunk", "ParentChunk", "Entity"]
    text: str
    score: float
    vector_score: Optional[float] = None
    fulltext_score: Optional[float] = None
    document_id: str
    module_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    related_entities: List[Dict[str, Any]] = Field(default_factory=list)
    graph_paths: List[EntityPath] = Field(default_factory=list)


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


class EnrichedSearchResults(BaseModel):
    """Container for search results enriched with graph context."""

    query: str
    results: List[EnrichedSearchResult]
    total_count: int
    search_time_ms: float
    weights: Dict[str, float] = Field(
        default_factory=lambda: {
            "vector": VECTOR_WEIGHT,
            "fulltext": FULLTEXT_WEIGHT,
        }
    )
    graph_context: Optional[GraphContext] = None


class ExpansionTerm(BaseModel):
    """Individual term added during query expansion."""

    term: str
    source_entity: str
    relationship: str
    weight: float = Field(ge=0.0, le=1.0)


class ExpandedQuery(BaseModel):
    """Result of query expansion operation."""

    original_query: str
    expanded_query: str
    expansion_terms: List[ExpansionTerm] = Field(default_factory=list)
    entities_found: List[str] = Field(default_factory=list)
    entity_ids: List[str] = Field(default_factory=list)
    expansion_time_ms: float = 0.0


class Entity(BaseModel):
    """Entity found in the knowledge graph."""

    id: str
    name: str
    entity_type: str
    definition: Optional[str] = None
    module_id: Optional[str] = None
    score: Optional[float] = None  # Similarity score if from vector search


class DocumentContext(BaseModel):
    """
    Context from a single document for multi-document reasoning.

    Contains chunks and entities extracted from a single document,
    along with relevance scoring for ranking during synthesis.
    """

    document_id: str
    document_title: str
    module_id: str
    chunks: List[Dict[str, Any]] = Field(default_factory=list)
    entities: List[str] = Field(default_factory=list)
    relevance_score: float = 0.0


class MultiDocOptions(BaseModel):
    """
    Options for multi-document queries.

    Controls the scope and behavior of cross-document reasoning,
    including citation formatting and contradiction detection.
    """

    max_documents: int = Field(default=10, ge=1, le=50)
    max_chunks_per_document: int = Field(default=5, ge=1, le=20)
    include_entity_context: bool = True
    detect_contradictions: bool = True
    citation_style: Literal["inline", "footnote", "reference"] = "inline"


class MultiDocResponse(BaseModel):
    """
    Response from multi-document query.

    Contains the synthesized answer along with citations, key points,
    and any detected contradictions across documents.
    """

    query: str
    answer: str
    confidence: float
    sources_used: int
    key_points: List[str] = Field(default_factory=list)
    citations: List[Dict[str, Any]] = Field(default_factory=list)
    contradictions: List[Dict[str, Any]] = Field(default_factory=list)
    documents_searched: int
    documents_used: int
    processing_time_ms: float
    module_ids: List[str] = Field(default_factory=list)


# ============================================================================
# RAG ENGINE CLASS
# ============================================================================


class RAGEngine:
    """
    Hybrid search RAG engine for AURA-NOTES-MANAGER.

    Combines vector similarity search with fulltext search for improved retrieval
    quality. Enhanced with graph traversal for multi-hop entity expansion.
    Supports module_id filtering for scoped queries.

    Features:
    - Vector search (0.7 weight) using Neo4j vector indices
    - Fulltext search (0.3 weight) using Neo4j fulltext indices
    - Graph traversal for 2-hop entity expansion
    - Module filtering for multi-tenant scenarios
    - Parent chunk context retrieval
    - Configurable weights and top_k parameters

    Example:
        from api.rag_engine import RAGEngine
        from api.neo4j_config import neo4j_driver
        from services.embeddings import EmbeddingService

        embedding_service = EmbeddingService()
        engine = RAGEngine(neo4j_driver, embedding_service)

        # Basic hybrid search
        results = await engine.search(
            query="machine learning algorithms",
            module_ids=["module_123"],
            top_k=10
        )

        # Search with graph expansion
        enriched = await engine.search_with_graph_expansion(
            query="neural networks",
            module_ids=["module_123"],
            expand_entities=True
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
                            result.metadata["parent_context"] = parent_context[
                                result.id
                            ]

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

    # ========================================================================
    # GRAPH TRAVERSAL METHODS
    # ========================================================================

    async def expand_graph_context(
        self,
        entity_ids: List[str],
        hop_depth: int = GRAPH_HOP_DEPTH,
        module_ids: Optional[List[str]] = None,
        max_entities: int = MAX_EXPANDED_ENTITIES,
    ) -> GraphContext:
        """
        Expand graph context from seed entities through multi-hop traversal.

        Traverses relationships up to hop_depth, collecting related entities
        and weighting them by relationship type and path distance.

        Args:
            entity_ids: Seed entity IDs to expand from
            hop_depth: Maximum traversal depth (default: 2, max: 4)
            module_ids: Optional module IDs to filter results
            max_entities: Maximum expanded entities to return (default: 20)

        Returns:
            GraphContext with expanded entities and relationship paths
        """
        start_time = time.time()

        if not entity_ids:
            return GraphContext(
                seed_entities=[],
                expanded_entities=[],
                paths=[],
                total_entities=0,
                max_depth_reached=0,
                traversal_time_ms=0.0,
            )

        try:
            hop_depth = min(hop_depth, MAX_GRAPH_HOP_DEPTH)

            # Build module filter
            module_filter = ""
            params: Dict[str, Any] = {
                "entity_ids": entity_ids,
                "limit": max_entities,
            }

            if module_ids:
                module_filter = "AND (related.module_id IN $module_ids OR related.module_id IS NULL)"
                params["module_ids"] = module_ids

            # Multi-hop traversal query - handles 1-hop and 2-hop
            if hop_depth == 1:
                cypher = f"""
                MATCH (start)-[r]->(related)
                WHERE (start:Topic OR start:Concept OR start:Methodology OR start:Finding)
                AND start.id IN $entity_ids
                AND (related:Topic OR related:Concept OR related:Methodology OR related:Finding)
                {module_filter}
                RETURN start.name as source, related.name as target,
                       related.id as target_id, related.definition as definition,
                       labels(related)[0] as entity_type, related.module_id as module_id,
                       type(r) as relationship_type, r.confidence as confidence,
                       1 as hops
                ORDER BY r.confidence DESC
                LIMIT $limit
                """
            else:
                # 2-hop traversal with intermediate entities
                hop1_filter = module_filter.replace("related", "hop1")
                hop2_filter = module_filter.replace("related", "hop2")
                cypher = f"""
                // 1-hop results
                MATCH (start)-[r1]->(hop1)
                WHERE (start:Topic OR start:Concept OR start:Methodology OR start:Finding)
                AND start.id IN $entity_ids
                AND (hop1:Topic OR hop1:Concept OR hop1:Methodology OR hop1:Finding)
                {hop1_filter}
                WITH start, hop1, r1, 1 as hops
                RETURN start.name as source, hop1.name as target,
                       hop1.id as target_id, hop1.definition as definition,
                       labels(hop1)[0] as entity_type, hop1.module_id as module_id,
                       type(r1) as relationship_type, r1.confidence as confidence,
                       hops

                UNION ALL

                // 2-hop results
                MATCH (start)-[r1]->(hop1)-[r2]->(hop2)
                WHERE (start:Topic OR start:Concept OR start:Methodology OR start:Finding)
                AND start.id IN $entity_ids
                AND (hop1:Topic OR hop1:Concept OR hop1:Methodology OR hop1:Finding)
                AND (hop2:Topic OR hop2:Concept OR hop2:Methodology OR hop2:Finding)
                AND NOT hop2.id IN $entity_ids
                {hop2_filter}
                WITH start, hop2, r2, 2 as hops
                RETURN start.name as source, hop2.name as target,
                       hop2.id as target_id, hop2.definition as definition,
                       labels(hop2)[0] as entity_type, hop2.module_id as module_id,
                       type(r2) as relationship_type, r2.confidence as confidence,
                       hops
                ORDER BY hops ASC, confidence DESC
                LIMIT $limit
                """

            expanded_entities: List[Dict[str, Any]] = []
            paths: List[EntityPath] = []
            seen_ids: set = set()
            max_depth = 0

            with self.driver.session() as session:
                result = session.run(cypher, params)
                for record in result:
                    target_id = record["target_id"]

                    # Track max depth
                    hops = record["hops"]
                    if hops > max_depth:
                        max_depth = hops

                    # Add path
                    rel_type = record["relationship_type"]
                    paths.append(
                        EntityPath(
                            source_entity=record["source"],
                            target_entity=record["target"],
                            relationship_type=rel_type,
                            confidence=record.get("confidence", 1.0) or 1.0,
                            hops=hops,
                        )
                    )

                    # Add entity if not seen
                    if target_id not in seen_ids:
                        seen_ids.add(target_id)
                        # Calculate weighted relevance score
                        rel_weight = RELATIONSHIP_WEIGHTS.get(rel_type, 0.4)
                        hop_decay = 1.0 / hops  # Closer entities score higher
                        confidence = record.get("confidence", 1.0) or 1.0
                        relevance = rel_weight * hop_decay * confidence

                        expanded_entities.append(
                            {
                                "id": target_id,
                                "name": record["target"],
                                "entity_type": record["entity_type"],
                                "definition": record.get("definition"),
                                "module_id": record.get("module_id"),
                                "relationship_type": rel_type,
                                "hops": hops,
                                "relevance_score": round(relevance, 4),
                            }
                        )

            # Sort by relevance score
            expanded_entities.sort(key=lambda x: x["relevance_score"], reverse=True)
            expanded_entities = expanded_entities[:max_entities]

            elapsed_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Graph expansion: {len(entity_ids)} seeds -> {len(expanded_entities)} entities "
                f"in {elapsed_ms:.1f}ms (max depth: {max_depth})"
            )

            return GraphContext(
                seed_entities=entity_ids,
                expanded_entities=expanded_entities,
                paths=paths,
                total_entities=len(expanded_entities),
                max_depth_reached=max_depth,
                traversal_time_ms=elapsed_ms,
            )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"Graph context expansion failed: {e}")
            return GraphContext(
                seed_entities=entity_ids,
                expanded_entities=[],
                paths=[],
                total_entities=0,
                max_depth_reached=0,
                traversal_time_ms=elapsed_ms,
            )

    async def _traverse_relationships(
        self,
        start_ids: List[str],
        depth: int,
        module_ids: Optional[List[str]],
    ) -> List[EntityPath]:
        """
        Traverse graph relationships from start entities to given depth.

        Args:
            start_ids: Entity IDs to start traversal from
            depth: Maximum hops to traverse
            module_ids: Optional module IDs to filter by

        Returns:
            List of EntityPath objects representing discovered paths
        """
        if not start_ids:
            return []

        depth = min(depth, MAX_GRAPH_HOP_DEPTH)

        try:
            # Build module filter
            module_filter = ""
            params: Dict[str, Any] = {"entity_ids": start_ids, "depth": depth}

            if module_ids:
                module_filter = "AND (related.module_id IN $module_ids OR related.module_id IS NULL)"
                params["module_ids"] = module_ids

            cypher = f"""
            MATCH (start)-[r]->(related)
            WHERE (start:Topic OR start:Concept OR start:Methodology OR start:Finding)
            AND start.id IN $entity_ids
            AND (related:Topic OR related:Concept OR related:Methodology OR related:Finding)
            {module_filter}
            RETURN start.name as source, related.name as target,
                   type(r) as relationship_type, r.confidence as confidence
            LIMIT 100
            """

            paths = []
            with self.driver.session() as session:
                result = session.run(cypher, params)
                for record in result:
                    paths.append(
                        EntityPath(
                            source_entity=record["source"],
                            target_entity=record["target"],
                            relationship_type=record["relationship_type"],
                            confidence=record.get("confidence", 1.0) or 1.0,
                            hops=1,
                        )
                    )

            return paths

        except Exception as e:
            logger.warning(f"Relationship traversal failed: {e}")
            return []

    def _weight_path(self, path: EntityPath) -> float:
        """
        Calculate weighted score for an entity path.

        Considers relationship type weight, confidence, and hop distance.

        Args:
            path: EntityPath to weight

        Returns:
            Weighted score between 0 and 1
        """
        rel_weight = RELATIONSHIP_WEIGHTS.get(path.relationship_type, 0.4)
        hop_decay = 1.0 / path.hops  # Closer = higher score
        confidence = path.confidence if path.confidence else 1.0

        return rel_weight * hop_decay * confidence

    async def _extract_entities_from_results(
        self,
        results: List[SearchResult],
    ) -> List[str]:
        """
        Extract entity IDs from search results by finding connected entities.

        Args:
            results: List of SearchResult objects

        Returns:
            List of entity IDs mentioned in the result chunks
        """
        if not results:
            return []

        try:
            chunk_ids = [r.id for r in results if r.node_type == "Chunk"]
            if not chunk_ids:
                return []

            cypher = """
            MATCH (c:Chunk)-[:CONTAINS_ENTITY]->(e)
            WHERE c.id IN $chunk_ids
            AND (e:Topic OR e:Concept OR e:Methodology OR e:Finding)
            RETURN DISTINCT e.id as entity_id
            LIMIT 20
            """

            entity_ids = []
            with self.driver.session() as session:
                result = session.run(cypher, {"chunk_ids": chunk_ids})
                for record in result:
                    entity_ids.append(record["entity_id"])

            logger.debug(
                f"Extracted {len(entity_ids)} entities from {len(chunk_ids)} chunks"
            )
            return entity_ids

        except Exception as e:
            logger.warning(f"Entity extraction from results failed: {e}")
            return []

    async def search_with_graph_expansion(
        self,
        query: str,
        module_ids: Optional[List[str]] = None,
        top_k: int = TOP_K_RETRIEVAL,
        vector_weight: Optional[float] = None,
        fulltext_weight: Optional[float] = None,
        min_score: float = MIN_SCORE_THRESHOLD,
        include_parent_context: bool = True,
        expand_entities: bool = True,
        hop_depth: int = GRAPH_HOP_DEPTH,
        max_expanded: int = MAX_EXPANDED_ENTITIES,
    ) -> EnrichedSearchResults:
        """
        Perform hybrid search with graph-based entity expansion.

        Combines vector and fulltext search with graph traversal to provide
        enriched results that include related entities through multi-hop
        relationships.

        Algorithm:
        1. Run hybrid search to get initial results
        2. Extract entity IDs from top results
        3. Expand entities via graph traversal
        4. Merge expanded context into results

        Args:
            query: Search query text
            module_ids: Optional list of module IDs to filter by
            top_k: Number of results to return
            vector_weight: Optional override for vector score weight
            fulltext_weight: Optional override for fulltext score weight
            min_score: Minimum combined score threshold
            include_parent_context: Whether to include parent chunk text
            expand_entities: Whether to expand via graph (default: True)
            hop_depth: Maximum traversal depth (default: 2)
            max_expanded: Maximum expanded entities per result (default: 20)

        Returns:
            EnrichedSearchResults with graph context
        """
        start_time = time.time()

        try:
            # Step 1: Run base hybrid search
            base_results = await self.search(
                query=query,
                module_ids=module_ids,
                top_k=top_k,
                vector_weight=vector_weight,
                fulltext_weight=fulltext_weight,
                min_score=min_score,
                include_parent_context=include_parent_context,
            )

            if not base_results.results or not expand_entities:
                # Return as enriched but without graph context
                enriched_results = [
                    EnrichedSearchResult(
                        id=r.id,
                        node_type=r.node_type,
                        text=r.text,
                        score=r.score,
                        vector_score=r.vector_score,
                        fulltext_score=r.fulltext_score,
                        document_id=r.document_id,
                        module_id=r.module_id,
                        metadata=r.metadata,
                        related_entities=[],
                        graph_paths=[],
                    )
                    for r in base_results.results
                ]

                elapsed_ms = (time.time() - start_time) * 1000
                return EnrichedSearchResults(
                    query=query,
                    results=enriched_results,
                    total_count=len(enriched_results),
                    search_time_ms=elapsed_ms,
                    weights=base_results.weights,
                    graph_context=None,
                )

            # Step 2: Extract entities from top results
            entity_ids = await self._extract_entities_from_results(
                base_results.results[:5]  # Only process top 5 for performance
            )

            # Step 3: Expand entities via graph traversal
            graph_context = None
            if entity_ids:
                graph_context = await self.expand_graph_context(
                    entity_ids=entity_ids,
                    hop_depth=hop_depth,
                    module_ids=module_ids,
                    max_entities=max_expanded,
                )

            # Step 4: Build enriched results with graph context
            enriched_results = []
            for r in base_results.results:
                # Find related entities for this result
                related = []
                paths = []

                if graph_context and graph_context.expanded_entities:
                    # Add top related entities
                    related = graph_context.expanded_entities[:5]
                    # Filter paths relevant to this result's entities
                    result_text_lower = r.text.lower() if r.text else ""
                    paths = [
                        p
                        for p in graph_context.paths
                        if p.source_entity.lower() in result_text_lower
                        or p.target_entity.lower() in result_text_lower
                    ][:5]

                enriched_results.append(
                    EnrichedSearchResult(
                        id=r.id,
                        node_type=r.node_type,
                        text=r.text,
                        score=r.score,
                        vector_score=r.vector_score,
                        fulltext_score=r.fulltext_score,
                        document_id=r.document_id,
                        module_id=r.module_id,
                        metadata=r.metadata,
                        related_entities=related,
                        graph_paths=paths,
                    )
                )

            elapsed_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Search with graph expansion: {len(enriched_results)} results, "
                f"{graph_context.total_entities if graph_context else 0} expanded entities, "
                f"{elapsed_ms:.1f}ms total"
            )

            return EnrichedSearchResults(
                query=query,
                results=enriched_results,
                total_count=len(enriched_results),
                search_time_ms=elapsed_ms,
                weights=base_results.weights,
                graph_context=graph_context,
            )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"Search with graph expansion failed: {e}")

            return EnrichedSearchResults(
                query=query,
                results=[],
                total_count=0,
                search_time_ms=elapsed_ms,
                weights={
                    "vector": self.vector_weight,
                    "fulltext": self.fulltext_weight,
                },
                graph_context=None,
            )

    # ========================================================================
    # QUERY EXPANSION METHODS
    # ========================================================================

    async def expand_query(
        self,
        query: str,
        module_ids: Optional[List[str]] = None,
        max_expansions: int = MAX_EXPANSION_TERMS,
        min_weight: float = MIN_EXPANSION_TERM_WEIGHT,
    ) -> ExpandedQuery:
        """
        Expand query using knowledge graph entities and relationships.

        Algorithm:
        1. Identify entities in the query (via text matching and vector similarity)
        2. Get related entities through relationships (DEFINES, USES, etc.)
        3. Select top expansion terms by weight
        4. Format expanded query for fulltext search

        Args:
            query: Original query text
            module_ids: Optional module IDs to filter entity lookup
            max_expansions: Maximum number of expansion terms (default: 10)
            min_weight: Minimum weight for expansion terms (default: 0.3)

        Returns:
            ExpandedQuery with original and expanded query text
        """
        start_time = time.time()

        if not query or not query.strip():
            return ExpandedQuery(
                original_query=query or "",
                expanded_query=query or "",
                expansion_terms=[],
                entities_found=[],
                entity_ids=[],
                expansion_time_ms=0.0,
            )

        try:
            # Step 1: Identify entities in the query
            entities = await self._identify_entities_in_query(query, module_ids)

            if not entities:
                elapsed_ms = (time.time() - start_time) * 1000
                logger.debug(f"No entities found in query, skipping expansion")
                return ExpandedQuery(
                    original_query=query,
                    expanded_query=query,
                    expansion_terms=[],
                    entities_found=[],
                    entity_ids=[],
                    expansion_time_ms=elapsed_ms,
                )

            entity_names = [e.name for e in entities]
            entity_ids = [e.id for e in entities]

            # Step 2: Get expansion terms from related entities
            expansion_terms = await self._get_expansion_terms(
                entities, module_ids, max_expansions, min_weight
            )

            # Step 3: Build expanded query
            # Add expansion terms to original query for fulltext search
            expansion_text = " ".join(t.term for t in expansion_terms)
            expanded_query = (
                f"{query} {expansion_text}".strip() if expansion_text else query
            )

            elapsed_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Query expansion: {len(entities)} entities -> "
                f"{len(expansion_terms)} terms in {elapsed_ms:.1f}ms"
            )

            return ExpandedQuery(
                original_query=query,
                expanded_query=expanded_query,
                expansion_terms=expansion_terms,
                entities_found=entity_names,
                entity_ids=entity_ids,
                expansion_time_ms=elapsed_ms,
            )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.warning(f"Query expansion failed: {e}")
            return ExpandedQuery(
                original_query=query,
                expanded_query=query,
                expansion_terms=[],
                entities_found=[],
                entity_ids=[],
                expansion_time_ms=elapsed_ms,
            )

    async def _identify_entities_in_query(
        self,
        query: str,
        module_ids: Optional[List[str]],
    ) -> List[Entity]:
        """
        Identify entities mentioned in the query.

        Uses two approaches:
        1. Text matching: Find entities whose names/definitions contain query terms
        2. Vector similarity: Find semantically similar entities

        Args:
            query: Query text
            module_ids: Optional module IDs to filter

        Returns:
            List of Entity objects found in the query
        """
        entities = []
        seen_ids: set = set()

        try:
            # Approach 1: Text-based entity lookup
            text_entities = await self._lookup_entities_by_text(query, module_ids)
            for e in text_entities:
                if e.id not in seen_ids:
                    seen_ids.add(e.id)
                    entities.append(e)

            # Approach 2: Vector similarity (if embedding service available)
            if self.embedding_service:
                vector_entities = await self._lookup_entities_by_vector(
                    query, module_ids
                )
                for e in vector_entities:
                    if e.id not in seen_ids:
                        seen_ids.add(e.id)
                        entities.append(e)

            logger.debug(f"Identified {len(entities)} entities in query")
            return entities[:10]  # Limit to top 10 entities

        except Exception as e:
            logger.warning(f"Entity identification failed: {e}")
            return []

    async def _lookup_entities_by_text(
        self,
        query: str,
        module_ids: Optional[List[str]],
    ) -> List[Entity]:
        """
        Find entities by text matching on name and definition.

        Args:
            query: Query text to match
            module_ids: Optional module IDs to filter

        Returns:
            List of matching Entity objects
        """
        try:
            # Extract key terms from query for matching
            query_terms = [
                t.strip().lower() for t in query.split() if len(t.strip()) > 2
            ]

            if not query_terms:
                return []

            # Build module filter
            module_filter = ""
            params: Dict[str, Any] = {"query_lower": query.lower()}

            if module_ids:
                module_filter = (
                    "AND (e.module_id IN $module_ids OR e.module_id IS NULL)"
                )
                params["module_ids"] = module_ids

            # Search entity names and definitions
            cypher = f"""
            MATCH (e)
            WHERE (e:Topic OR e:Concept OR e:Methodology OR e:Finding)
            AND (toLower(e.name) CONTAINS $query_lower
                 OR toLower(e.definition) CONTAINS $query_lower)
            {module_filter}
            RETURN e.id as id, e.name as name, labels(e)[0] as entity_type,
                   e.definition as definition, e.module_id as module_id
            LIMIT 5
            """

            entities = []
            with self.driver.session() as session:
                result = session.run(cypher, params)
                for record in result:
                    entities.append(
                        Entity(
                            id=record["id"],
                            name=record["name"],
                            entity_type=record["entity_type"],
                            definition=record.get("definition"),
                            module_id=record.get("module_id"),
                        )
                    )

            return entities

        except Exception as e:
            logger.warning(f"Text-based entity lookup failed: {e}")
            return []

    async def _lookup_entities_by_vector(
        self,
        query: str,
        module_ids: Optional[List[str]],
    ) -> List[Entity]:
        """
        Find entities by vector similarity.

        Args:
            query: Query text
            module_ids: Optional module IDs to filter

        Returns:
            List of semantically similar Entity objects
        """
        try:
            # Generate query embedding
            query_embedding = self.embedding_service.embed_text(query)

            if not query_embedding or len(query_embedding) != 768:
                return []

            # Build module filter
            module_filter = ""
            params: Dict[str, Any] = {
                "query_embedding": query_embedding,
                "threshold": ENTITY_SIMILARITY_THRESHOLD,
            }

            if module_ids:
                module_filter = (
                    "AND (e.module_id IN $module_ids OR e.module_id IS NULL)"
                )
                params["module_ids"] = module_ids

            # Search across entity vector indices
            # Try concept index first as most common
            entities = []

            for entity_type in ["Concept", "Topic", "Methodology", "Finding"]:
                index_name = f"{entity_type.lower()}_vector_index"
                try:
                    cypher = f"""
                    CALL db.index.vector.queryNodes($index_name, 3, $query_embedding)
                    YIELD node as e, score
                    WHERE score > $threshold
                    {module_filter}
                    RETURN e.id as id, e.name as name, '{entity_type}' as entity_type,
                           e.definition as definition, e.module_id as module_id, score
                    """
                    params["index_name"] = index_name

                    with self.driver.session() as session:
                        result = session.run(cypher, params)
                        for record in result:
                            entities.append(
                                Entity(
                                    id=record["id"],
                                    name=record["name"],
                                    entity_type=record["entity_type"],
                                    definition=record.get("definition"),
                                    module_id=record.get("module_id"),
                                    score=record.get("score"),
                                )
                            )

                except Exception:
                    # Index may not exist yet
                    continue

            # Sort by score and return top results
            entities.sort(key=lambda x: x.score or 0, reverse=True)
            return entities[:5]

        except Exception as e:
            logger.warning(f"Vector-based entity lookup failed: {e}")
            return []

    async def _get_expansion_terms(
        self,
        entities: List[Entity],
        module_ids: Optional[List[str]],
        max_terms: int,
        min_weight: float,
    ) -> List[ExpansionTerm]:
        """
        Get expansion terms from related entities.

        For each identified entity, find related entities through
        relationships and extract their names as expansion terms.

        Args:
            entities: Entities identified in the query
            module_ids: Optional module IDs to filter
            max_terms: Maximum expansion terms to return
            min_weight: Minimum weight for inclusion

        Returns:
            List of ExpansionTerm objects sorted by weight
        """
        if not entities:
            return []

        try:
            entity_ids = [e.id for e in entities]
            entity_names_lower = {e.name.lower() for e in entities}

            # Build module filter
            module_filter = ""
            params: Dict[str, Any] = {"entity_ids": entity_ids}

            if module_ids:
                module_filter = "AND (related.module_id IN $module_ids OR related.module_id IS NULL)"
                params["module_ids"] = module_ids

            # Find related entities through relationships
            cypher = f"""
            MATCH (e)-[r]->(related)
            WHERE e.id IN $entity_ids
            AND (related:Topic OR related:Concept OR related:Methodology OR related:Finding)
            AND NOT related.id IN $entity_ids
            {module_filter}
            RETURN DISTINCT related.name as term, e.name as source_entity,
                   type(r) as relationship, r.confidence as confidence
            LIMIT 30
            """

            expansion_terms = []
            with self.driver.session() as session:
                result = session.run(cypher, params)
                for record in result:
                    term = record["term"]
                    rel_type = record["relationship"]

                    # Skip if term is in original query entities
                    if term.lower() in entity_names_lower:
                        continue

                    # Calculate weight based on relationship type
                    base_weight = RELATIONSHIP_WEIGHTS.get(rel_type, 0.4)
                    confidence = record.get("confidence", 1.0) or 1.0
                    weight = base_weight * confidence

                    if weight >= min_weight:
                        expansion_terms.append(
                            ExpansionTerm(
                                term=term,
                                source_entity=record["source_entity"],
                                relationship=rel_type,
                                weight=round(weight, 4),
                            )
                        )

            # Sort by weight and limit
            expansion_terms.sort(key=lambda x: x.weight, reverse=True)
            return expansion_terms[:max_terms]

        except Exception as e:
            logger.warning(f"Expansion term retrieval failed: {e}")
            return []

    async def search_with_expansion(
        self,
        query: str,
        module_ids: Optional[List[str]] = None,
        top_k: int = TOP_K_RETRIEVAL,
        expand: bool = True,
        max_expansion_terms: int = MAX_EXPANSION_TERMS,
        min_expansion_weight: float = MIN_EXPANSION_TERM_WEIGHT,
    ) -> SearchResults:
        """
        Perform hybrid search with optional query expansion.

        Expands the query using knowledge graph entities before search
        to improve recall for queries that may not match exact terminology.

        Args:
            query: Search query text
            module_ids: Optional list of module IDs to filter by
            top_k: Number of results to return
            expand: Whether to expand query (default: True)
            max_expansion_terms: Maximum expansion terms (default: 10)
            min_expansion_weight: Minimum term weight (default: 0.3)

        Returns:
            SearchResults with expansion_info in metadata
        """
        start_time = time.time()

        expanded_query_obj = None
        search_query = query

        try:
            # Step 1: Expand query if enabled
            if expand:
                expanded_query_obj = await self.expand_query(
                    query=query,
                    module_ids=module_ids,
                    max_expansions=max_expansion_terms,
                    min_weight=min_expansion_weight,
                )

                # Use expanded query for fulltext search
                # (vector search uses original query - embeddings capture semantics)
                if expanded_query_obj.expansion_terms:
                    search_query = expanded_query_obj.expanded_query

            # Step 2: Perform hybrid search
            # For fulltext, use expanded query; for vector, use original
            results = await self._search_with_split_query(
                vector_query=query,  # Original for vector
                fulltext_query=search_query,  # Expanded for fulltext
                module_ids=module_ids,
                top_k=top_k,
            )

            # Add expansion info to results metadata
            if expanded_query_obj and expanded_query_obj.expansion_terms:
                results.weights["expansion_applied"] = True
                results.weights["expansion_terms"] = len(
                    expanded_query_obj.expansion_terms
                )

            elapsed_ms = (time.time() - start_time) * 1000
            results.search_time_ms = elapsed_ms

            logger.info(
                f"Search with expansion: {len(results.results)} results, "
                f"expanded={expand and bool(expanded_query_obj and expanded_query_obj.expansion_terms)}, "
                f"{elapsed_ms:.1f}ms"
            )

            return results

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"Search with expansion failed: {e}")
            return SearchResults(
                query=query,
                results=[],
                total_count=0,
                search_time_ms=elapsed_ms,
                weights={
                    "vector": self.vector_weight,
                    "fulltext": self.fulltext_weight,
                },
            )

    async def _search_with_split_query(
        self,
        vector_query: str,
        fulltext_query: str,
        module_ids: Optional[List[str]],
        top_k: int,
    ) -> SearchResults:
        """
        Perform hybrid search with different queries for vector and fulltext.

        This allows using the original query for vector search (semantic)
        while using the expanded query for fulltext search (lexical).

        Args:
            vector_query: Query for vector search (original)
            fulltext_query: Query for fulltext search (expanded)
            module_ids: Optional module IDs to filter
            top_k: Number of results to return

        Returns:
            Combined SearchResults
        """
        # Generate embedding for vector query
        query_embedding = self.embedding_service.embed_text(vector_query)

        if not query_embedding or len(query_embedding) != 768:
            logger.warning("Invalid query embedding, falling back to fulltext only")
            fulltext_results = await self._fulltext_search(
                fulltext_query, module_ids, top_k
            )
            return SearchResults(
                query=vector_query,
                results=fulltext_results,
                total_count=len(fulltext_results),
                search_time_ms=0,
                weights={"vector": 0, "fulltext": 1.0},
            )

        # Execute both searches
        vector_results = await self._vector_search(
            query_embedding, module_ids, top_k * 2
        )
        fulltext_results = await self._fulltext_search(
            fulltext_query, module_ids, top_k * 2
        )

        # Combine with weights
        combined = self._combine_results(
            vector_results,
            fulltext_results,
            self.vector_weight,
            self.fulltext_weight,
        )

        # Filter and limit
        filtered = [r for r in combined if r.score >= MIN_SCORE_THRESHOLD]
        filtered = filtered[:top_k]

        return SearchResults(
            query=vector_query,
            results=filtered,
            total_count=len(filtered),
            search_time_ms=0,
            weights={"vector": self.vector_weight, "fulltext": self.fulltext_weight},
        )

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

    # ========================================================================
    # MULTI-DOCUMENT REASONING METHODS
    # ========================================================================

    async def multi_document_query(
        self,
        query: str,
        module_ids: List[str],
        options: Optional[MultiDocOptions] = None,
    ) -> MultiDocResponse:
        """
        Query across multiple documents within modules.

        Gathers context from multiple documents and synthesizes
        a coherent answer with citations.

        Args:
            query: The user's question.
            module_ids: List of module IDs to search within.
            options: Query options (max_documents, citation_style, etc.).

        Returns:
            MultiDocResponse with synthesized answer and citations.
        """
        start_time = time.time()

        if options is None:
            options = MultiDocOptions()

        try:
            # Step 1: Gather cross-document context
            contexts = await self._gather_cross_document_context(
                query=query,
                module_ids=module_ids,
                max_documents=options.max_documents,
                max_chunks_per_doc=options.max_chunks_per_document,
            )

            if not contexts:
                # No relevant documents found
                elapsed_ms = (time.time() - start_time) * 1000
                return MultiDocResponse(
                    query=query,
                    answer="No relevant documents found for this query.",
                    confidence=0.0,
                    sources_used=0,
                    key_points=[],
                    citations=[],
                    contradictions=[],
                    documents_searched=0,
                    documents_used=0,
                    processing_time_ms=elapsed_ms,
                    module_ids=module_ids,
                )

            # Step 2: Synthesize answer using AnswerSynthesizer
            from services.answer_synthesizer import AnswerSynthesizer, SynthesisOptions

            synthesizer = AnswerSynthesizer()
            synthesis_options = SynthesisOptions(
                citation_style=options.citation_style,
                detect_contradictions=options.detect_contradictions,
            )

            synthesized = await synthesizer.synthesize(
                query=query,
                contexts=contexts,
                options=synthesis_options,
            )

            elapsed_ms = (time.time() - start_time) * 1000

            logger.info(
                f"Multi-doc query: {len(contexts)} documents, "
                f"confidence={synthesized.confidence:.2f}, {elapsed_ms:.1f}ms"
            )

            citations = []
            for index, citation in enumerate(synthesized.citations, start=1):
                try:
                    citation_index = int(citation.reference_id.strip("[]"))
                except (ValueError, AttributeError):
                    citation_index = index

                citations.append(
                    {
                        "index": citation_index,
                        "document_id": citation.document_id,
                        "document_title": citation.document_title,
                        "chunk_id": citation.chunk_id,
                        "text": citation.chunk_text,
                    }
                )
            contradictions = [
                {
                    "claim1": contradiction.statement_a,
                    "claim2": contradiction.statement_b,
                    "source1": contradiction.source_a,
                    "source2": contradiction.source_b,
                    "explanation": contradiction.resolution_hint or "",
                }
                for contradiction in synthesized.contradictions
            ]

            return MultiDocResponse(
                query=query,
                answer=synthesized.answer,
                confidence=synthesized.confidence,
                sources_used=synthesized.sources_used,
                key_points=synthesized.key_points,
                citations=citations,
                contradictions=contradictions,
                documents_searched=len(contexts),
                documents_used=synthesized.sources_used,
                processing_time_ms=elapsed_ms,
                module_ids=module_ids,
            )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"Multi-document query failed: {e}")
            return MultiDocResponse(
                query=query,
                answer=f"Error processing query: {str(e)}",
                confidence=0.0,
                sources_used=0,
                key_points=[],
                citations=[],
                contradictions=[],
                documents_searched=0,
                documents_used=0,
                processing_time_ms=elapsed_ms,
                module_ids=module_ids,
            )

    async def _gather_cross_document_context(
        self,
        query: str,
        module_ids: List[str],
        max_documents: int = 10,
        max_chunks_per_doc: int = 5,
    ) -> List[DocumentContext]:
        """
        Gather context from multiple documents relevant to the query.

        Algorithm:
            1. Run hybrid search across all documents in module_ids
            2. Group results by document_id
            3. For each document, get top N most relevant chunks
            4. Include entity context from graph for each document

        Args:
            query: The user's question.
            module_ids: List of module IDs to search within.
            max_documents: Maximum number of documents to include.
            max_chunks_per_doc: Maximum chunks per document.

        Returns:
            List of DocumentContext objects, one per document.
        """
        try:
            # Run broad search to find relevant chunks
            search_results = await self.search(
                query=query,
                module_ids=module_ids,
                top_k=max_documents * max_chunks_per_doc,  # Get plenty of chunks
                min_score=0.2,  # Lower threshold for broader recall
            )

            if not search_results.results:
                return []

            # Group by document
            doc_chunks: Dict[str, List[SearchResult]] = {}
            for result in search_results.results:
                doc_id = result.document_id
                if doc_id not in doc_chunks:
                    doc_chunks[doc_id] = []
                if len(doc_chunks[doc_id]) < max_chunks_per_doc:
                    doc_chunks[doc_id].append(result)

            # Limit to max_documents
            doc_ids = list(doc_chunks.keys())[:max_documents]

            # Build DocumentContext for each document
            contexts = []
            for doc_id in doc_ids:
                chunks = doc_chunks[doc_id]

                # Get document title from first chunk metadata or query
                doc_title = (
                    chunks[0].metadata.get("document_title", doc_id)
                    if chunks
                    else doc_id
                )
                module_id = (
                    chunks[0].module_id
                    if chunks
                    else (module_ids[0] if module_ids else "")
                )

                # Calculate document relevance as average chunk score
                avg_score = (
                    sum(c.score for c in chunks) / len(chunks) if chunks else 0.0
                )

                # Get entities mentioned in these chunks
                chunk_ids = [c.id for c in chunks]
                entities = await self._get_entities_for_chunks(chunk_ids)

                contexts.append(
                    DocumentContext(
                        document_id=doc_id,
                        document_title=doc_title,
                        module_id=module_id or "",
                        chunks=[
                            {
                                "id": c.id,
                                "text": c.text,
                                "score": c.score,
                            }
                            for c in chunks
                        ],
                        entities=entities,
                        relevance_score=avg_score,
                    )
                )

            # Sort by relevance
            contexts.sort(key=lambda x: x.relevance_score, reverse=True)

            logger.debug(f"Gathered context from {len(contexts)} documents")
            return contexts

        except Exception as e:
            logger.warning(f"Cross-document context gathering failed: {e}")
            return []

    async def _get_entities_for_chunks(self, chunk_ids: List[str]) -> List[str]:
        """
        Get entity names mentioned in the given chunks.

        Args:
            chunk_ids: List of chunk IDs to look up entities for.

        Returns:
            List of entity names found in the chunks.
        """
        if not chunk_ids:
            return []

        try:
            cypher = """
            MATCH (c:Chunk)-[:CONTAINS_ENTITY]->(e)
            WHERE c.id IN $chunk_ids
            AND (e:Topic OR e:Concept OR e:Methodology OR e:Finding)
            RETURN DISTINCT e.name as name
            LIMIT 20
            """

            entities = []
            with self.driver.session() as session:
                result = session.run(cypher, {"chunk_ids": chunk_ids})
                for record in result:
                    if record["name"]:
                        entities.append(record["name"])

            return entities

        except Exception as e:
            logger.warning(f"Entity extraction for chunks failed: {e}")
            return []


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
