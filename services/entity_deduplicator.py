# entity_deduplicator.py
# Semantic entity deduplication using embedding similarity

# Identifies and merges semantically similar entities (e.g., "ML" and "Machine Learning")
# using cosine similarity on embeddings. Uses Union-Find algorithm for transitive
# grouping and confidence-based merge strategy to select canonical entities.

# @see: services/embeddings.py - Embedding generation service
# @see: api/kg_processor.py - KG processing pipeline integration
# @note: Threshold of 0.85 is tuned for academic entities; adjust if needed

"""
============================================================================
FILE: entity_deduplicator.py
LOCATION: services/entity_deduplicator.py
============================================================================

PURPOSE:
    Semantic deduplication of entities using embedding-based similarity.
    Catches cases where LLMs extract the same concept with different names:
    - "Machine Learning" vs "ML" vs "machine-learning"
    - "Software-Defined Networking" vs "SDN"
    
DEPENDENCIES:
    - services.embeddings.EmbeddingService for embedding generation
    - numpy for efficient matrix operations
    
USAGE:
    from services.entity_deduplicator import EntityDeduplicator
    
    deduplicator = EntityDeduplicator(similarity_threshold=0.85)
    unique_entities, merge_map = deduplicator.deduplicate(entities, embeddings)
    
============================================================================
"""

import logging
import math
from typing import Any, Dict, List, Optional, Tuple

# ============================================================================
# CONFIGURATION
# ============================================================================

# Cosine similarity threshold for considering entities as duplicates
ENTITY_DEDUP_SIMILARITY_THRESHOLD = 0.85

# Minimum entities required for semantic deduplication (below this, skip)
MIN_ENTITIES_FOR_SEMANTIC_DEDUP = 3

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# ENTITY DEDUPLICATOR CLASS
# ============================================================================


class EntityDeduplicator:
    """
    Semantic entity deduplication using cosine similarity on embeddings.
    
    Uses Union-Find (disjoint set) algorithm to transitively group similar
    entities and selects the entity with highest confidence as canonical.
    
    Features:
    - Cosine similarity calculation
    - Union-Find for transitive grouping
    - Confidence-based merge strategy
    - Definition and context merging
    - Merge history tracking for debugging
    
    Example:
        deduplicator = EntityDeduplicator(similarity_threshold=0.85)
        
        # entities: list of dicts with 'id', 'name', 'definition', 'confidence_score'
        # embeddings: dict mapping entity name -> 768-dim embedding vector
        
        unique, mapping = deduplicator.deduplicate(entities, embeddings)
        # unique: deduplicated entity list
        # mapping: dict of old_name -> canonical_name
    """
    
    def __init__(
        self,
        similarity_threshold: float = ENTITY_DEDUP_SIMILARITY_THRESHOLD,
        use_numpy: bool = True,
    ):
        """
        Initialize deduplicator.
        
        Args:
            similarity_threshold: Cosine similarity threshold (0.0-1.0).
                                  Entities above this are considered duplicates.
                                  Default: 0.85
            use_numpy: Use numpy for vectorized operations (faster for many entities).
                       Falls back to pure Python if numpy not available.
        """
        self.similarity_threshold = similarity_threshold
        self.use_numpy = use_numpy
        self._numpy_available = False
        
        if use_numpy:
            try:
                import numpy as np
                self._numpy_available = True
                self._np = np
            except ImportError:
                logger.warning("numpy not available, using pure Python for similarity")
                self._numpy_available = False
        
        logger.info(
            f"Initialized EntityDeduplicator with threshold={similarity_threshold}, "
            f"numpy={'enabled' if self._numpy_available else 'disabled'}"
        )
    
    def deduplicate(
        self,
        entities: List[Dict[str, Any]],
        embeddings: Dict[str, List[float]],
    ) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
        """
        Deduplicate entities using semantic similarity.
        
        Algorithm:
        1. Build pairwise similarity matrix
        2. Identify pairs above threshold
        3. Use Union-Find to group all duplicates transitively
        4. For each group, select canonical entity (highest confidence)
        5. Return deduplicated list and old_name -> canonical_name mapping
        
        Args:
            entities: List of entity dicts. Each must have:
                      - 'name': Entity name (required)
                      - 'confidence_score' or 'confidence': Confidence (0-1)
                      - 'definition': Entity definition (optional)
                      - 'context': Source context (optional)
            embeddings: Dict mapping entity name to embedding vector (768-dim).
                        Names should be case-sensitive matches.
        
        Returns:
            Tuple of:
            - List of deduplicated entities (with merged contexts/definitions)
            - Dict mapping old entity names to canonical names (for relationship updates)
        """
        if not entities:
            return [], {}
        
        if len(entities) < MIN_ENTITIES_FOR_SEMANTIC_DEDUP:
            logger.debug(f"Skipping semantic dedup: only {len(entities)} entities (< {MIN_ENTITIES_FOR_SEMANTIC_DEDUP})")
            return entities, {}
        
        # Filter entities with embeddings
        entities_with_embeddings = []
        embedding_vectors = []
        entities_without_embeddings = []
        
        for entity in entities:
            name = entity.get("name", "")
            if name in embeddings and embeddings[name]:
                entities_with_embeddings.append(entity)
                embedding_vectors.append(embeddings[name])
            else:
                # Keep entities without embeddings as-is
                entities_without_embeddings.append(entity)
                logger.debug(f"Entity '{name}' has no embedding, skipping dedup")
        
        if len(entities_with_embeddings) < MIN_ENTITIES_FOR_SEMANTIC_DEDUP:
            logger.debug(f"Only {len(entities_with_embeddings)} entities have embeddings, skipping dedup")
            return entities, {}
        
        n = len(entities_with_embeddings)
        logger.info(f"Starting semantic deduplication for {n} entities")
        
        # Find duplicate pairs
        duplicate_pairs = self._find_duplicates(entities_with_embeddings, embedding_vectors)
        
        if not duplicate_pairs:
            logger.info("No duplicates found")
            return entities, {}
        
        logger.info(f"Found {len(duplicate_pairs)} duplicate pairs")
        
        # Group using Union-Find
        parent = list(range(n))
        
        def find(x: int) -> int:
            if parent[x] != x:
                parent[x] = find(parent[x])
            return parent[x]
        
        def union(x: int, y: int) -> None:
            px, py = find(x), find(y)
            if px != py:
                parent[px] = py
        
        for i, j in duplicate_pairs:
            union(i, j)
        
        # Group entities by cluster
        clusters: Dict[int, List[int]] = {}
        for i in range(n):
            root = find(i)
            if root not in clusters:
                clusters[root] = []
            clusters[root].append(i)
        
        # Merge each cluster
        deduplicated = []
        name_mapping: Dict[str, str] = {}
        
        for indices in clusters.values():
            if len(indices) == 1:
                # No duplicates, keep as-is
                deduplicated.append(entities_with_embeddings[indices[0]])
            else:
                # Merge cluster into canonical entity
                cluster_entities = [entities_with_embeddings[i] for i in indices]
                canonical = self._merge_entities_cluster(cluster_entities)
                deduplicated.append(canonical)
                
                # Build mapping from non-canonical names to canonical name
                canonical_name = canonical.get("name", "")
                for entity in cluster_entities:
                    entity_name = entity.get("name", "")
                    if entity_name != canonical_name:
                        name_mapping[entity_name] = canonical_name
                        logger.info(f"Merged: '{entity_name}' -> '{canonical_name}'")
        
        # Add back entities without embeddings
        deduplicated.extend(entities_without_embeddings)
        
        original_count = len(entities)
        final_count = len(deduplicated)
        reduction_pct = ((original_count - final_count) / original_count * 100) if original_count > 0 else 0
        
        logger.info(
            f"Semantic deduplication complete: {original_count} -> {final_count} "
            f"entities ({reduction_pct:.1f}% reduction)"
        )
        
        return deduplicated, name_mapping
    
    def _find_duplicates(
        self,
        entities: List[Dict[str, Any]],
        embedding_vectors: List[List[float]],
    ) -> List[Tuple[int, int]]:
        """
        Find all pairs of entities with similarity above threshold.
        
        Args:
            entities: List of entities (for logging)
            embedding_vectors: List of embedding vectors (same order as entities)
        
        Returns:
            List of (i, j) index pairs for similar entities
        """
        n = len(embedding_vectors)
        duplicate_pairs = []
        
        if self._numpy_available:
            # Vectorized numpy approach
            embeddings_array = self._np.array(embedding_vectors)
            
            # Normalize for cosine similarity
            norms = self._np.linalg.norm(embeddings_array, axis=1, keepdims=True)
            norms = self._np.where(norms == 0, 1, norms)  # Avoid division by zero
            normalized = embeddings_array / norms
            
            # Compute similarity matrix
            similarity_matrix = self._np.dot(normalized, normalized.T)
            
            # Find pairs above threshold (upper triangle only)
            for i in range(n):
                for j in range(i + 1, n):
                    if similarity_matrix[i, j] >= self.similarity_threshold:
                        duplicate_pairs.append((i, j))
                        logger.debug(
                            f"Similar: '{entities[i].get('name', '')}' <-> "
                            f"'{entities[j].get('name', '')}' "
                            f"(score={similarity_matrix[i, j]:.3f})"
                        )
        else:
            # Pure Python approach
            for i in range(n):
                for j in range(i + 1, n):
                    similarity = self._compute_similarity(
                        embedding_vectors[i],
                        embedding_vectors[j]
                    )
                    if similarity >= self.similarity_threshold:
                        duplicate_pairs.append((i, j))
                        logger.debug(
                            f"Similar: '{entities[i].get('name', '')}' <-> "
                            f"'{entities[j].get('name', '')}' "
                            f"(score={similarity:.3f})"
                        )
        
        return duplicate_pairs
    
    def _compute_similarity(
        self,
        emb1: List[float],
        emb2: List[float],
    ) -> float:
        """
        Compute cosine similarity between two embedding vectors.
        
        Cosine similarity = (A · B) / (||A|| * ||B||)
        
        Args:
            emb1: First embedding vector
            emb2: Second embedding vector
        
        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        if not emb1 or not emb2 or len(emb1) != len(emb2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(emb1, emb2))
        norm1 = math.sqrt(sum(a * a for a in emb1))
        norm2 = math.sqrt(sum(b * b for b in emb2))
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def _merge_entities_cluster(
        self,
        cluster_entities: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Merge a cluster of similar entities into one canonical entity.
        
        Merge strategy:
        - Canonical = entity with highest confidence_score
        - Combine definitions if significantly different
        - Aggregate mention counts
        - Merge contexts (with truncation)
        
        Args:
            cluster_entities: List of entities to merge
        
        Returns:
            Merged canonical entity
        """
        if len(cluster_entities) == 1:
            return cluster_entities[0]
        
        # Sort by confidence to get canonical (highest confidence wins)
        def get_confidence(entity: Dict[str, Any]) -> float:
            return entity.get("confidence_score", entity.get("confidence", 0.0))
        
        sorted_entities = sorted(cluster_entities, key=get_confidence, reverse=True)
        canonical = sorted_entities[0].copy()  # Copy to avoid mutation
        
        # Collect all contexts and definitions
        all_contexts = []
        all_definitions = []
        total_mention_count = 0
        merged_names = []
        
        for entity in cluster_entities:
            # Context
            context = entity.get("context", "") or ""
            if context:
                all_contexts.append(context[:100])
            
            # Definition
            definition = entity.get("definition", "") or ""
            if definition and definition not in all_definitions:
                all_definitions.append(definition)
            
            # Mention count
            total_mention_count += entity.get("mention_count", 1)
            
            # Track merged names
            name = entity.get("name", "")
            if name != canonical.get("name", ""):
                merged_names.append(name)
        
        # Merge context (join with separator, truncate to ~500 chars)
        if all_contexts:
            merged_context = " ... ".join(filter(None, all_contexts))
            if len(merged_context) > 500:
                merged_context = merged_context[:497] + "..."
            canonical["context"] = merged_context
        
        # Use first non-empty definition (highest confidence entity's definition preferred)
        if all_definitions:
            canonical["definition"] = all_definitions[0]
        
        # Update mention count
        canonical["mention_count"] = total_mention_count
        
        # Track aliases for debugging
        if merged_names:
            canonical["_merged_from"] = merged_names
        
        logger.debug(
            f"Merged {len(cluster_entities)} entities into '{canonical.get('name', '')}': "
            f"aliases={merged_names}"
        )
        
        return canonical
    
    def _merge_entities(
        self,
        entity1: Dict[str, Any],
        entity2: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Merge two entities into one (pairwise merge).
        
        Used when merging incrementally. For clusters, use _merge_entities_cluster.
        
        Args:
            entity1: First entity
            entity2: Second entity
        
        Returns:
            Merged entity (one with higher confidence as base)
        """
        return self._merge_entities_cluster([entity1, entity2])


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def deduplicate_entities(
    entities: List[Dict[str, Any]],
    embeddings: Dict[str, List[float]],
    similarity_threshold: float = ENTITY_DEDUP_SIMILARITY_THRESHOLD,
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Convenience function to deduplicate entities.
    
    Args:
        entities: List of entity dicts
        embeddings: Dict mapping entity name -> embedding vector
        similarity_threshold: Cosine similarity threshold for duplicates
    
    Returns:
        Tuple of (deduplicated entities, name mapping)
    """
    deduplicator = EntityDeduplicator(similarity_threshold=similarity_threshold)
    return deduplicator.deduplicate(entities, embeddings)
