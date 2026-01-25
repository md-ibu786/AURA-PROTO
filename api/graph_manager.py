# graph_manager.py
# Centralized graph manager for Neo4j graph traversal and manipulation operations

# Provides graph traversal methods for multi-hop entity expansion, subgraph extraction,
# and neighbor retrieval. Separates graph-specific operations from RAG search logic
# to enable reuse across different components (RAGEngine, Query API, etc.).

# @see: api/rag_engine.py - Uses GraphManager for graph expansion in search
# @see: api/neo4j_config.py - Neo4j driver configuration
# @note: 2-hop traversal default; increase cautiously to avoid performance issues

from __future__ import annotations

import time
import logging
from typing import List, Dict, Any, Optional, Literal

from pydantic import BaseModel, Field


# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

# Default graph traversal settings
DEFAULT_HOP_DEPTH = 2
MAX_HOP_DEPTH = 4
MAX_NEIGHBORS = 50
MAX_EXPANDED_ENTITIES = 20

# Relationship type weights for ranking (higher = more important)
RELATIONSHIP_WEIGHTS: Dict[str, float] = {
    "DEFINES": 1.0,  # Strongest semantic connection
    "DEPENDS_ON": 0.9,
    "USES": 0.8,
    "SUPPORTS": 0.8,
    "EXTENDS": 0.7,
    "IMPLEMENTS": 0.7,
    "CONTRADICTS": 0.6,
    "REFERENCES": 0.5,
    "RELATED_TO": 0.4,
}

# All supported relationship types
ALL_RELATIONSHIP_TYPES = list(RELATIONSHIP_WEIGHTS.keys())


# ============================================================================
# DATA MODELS
# ============================================================================


class Entity(BaseModel):
    """Entity node from the knowledge graph."""

    id: str
    name: str
    entity_type: str  # Topic, Concept, Methodology, Finding
    definition: Optional[str] = None
    module_id: Optional[str] = None
    confidence: Optional[float] = None
    mention_count: Optional[int] = None


class EntityPath(BaseModel):
    """
    Represents a path between two entities in the graph.

    Used to track multi-hop relationships and calculate path weights.
    """

    source_entity: str = Field(description="Name of the source entity")
    target_entity: str = Field(description="Name of the target entity")
    relationship_type: str = Field(
        description="Type of relationship (DEFINES, USES, etc.)"
    )
    confidence: float = Field(default=1.0, description="Relationship confidence score")
    hops: int = Field(default=1, description="Number of hops from original seed entity")


class GraphContext(BaseModel):
    """
    Container for expanded graph context from entity traversal.

    Holds seed entities, expanded neighbors, and the paths connecting them.
    """

    seed_entities: List[str] = Field(
        default_factory=list,
        description="Original entity IDs used as seeds for expansion",
    )
    expanded_entities: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Entities discovered through graph traversal",
    )
    paths: List[EntityPath] = Field(
        default_factory=list,
        description="Relationship paths connecting entities",
    )
    total_entities: int = Field(
        default=0,
        description="Total count of unique entities in context",
    )
    max_depth_reached: int = Field(
        default=0,
        description="Maximum hop depth reached during traversal",
    )
    traversal_time_ms: float = Field(
        default=0.0,
        description="Time taken for graph traversal in milliseconds",
    )


class Subgraph(BaseModel):
    """
    Subgraph extracted from the knowledge graph.

    Contains nodes and edges for visualization or analysis.
    """

    nodes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of node objects with id, name, type, etc.",
    )
    edges: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="List of edge objects with source, target, type, etc.",
    )
    node_count: int = Field(default=0, description="Number of nodes in subgraph")
    edge_count: int = Field(default=0, description="Number of edges in subgraph")


# ============================================================================
# GRAPH MANAGER CLASS
# ============================================================================


class GraphManager:
    """
    Centralized manager for Neo4j graph traversal and manipulation operations.

    Provides methods for:
    - Entity neighbor retrieval (1-hop)
    - Multi-hop graph traversal (up to 4 hops)
    - Subgraph extraction for visualization
    - Path finding between entities
    - Entity lookup by ID or name

    Example:
        from api.graph_manager import GraphManager
        from api.neo4j_config import neo4j_driver

        graph_mgr = GraphManager(neo4j_driver)

        # Get neighbors of an entity
        neighbors = await graph_mgr.get_entity_neighbors("entity_123")

        # Extract subgraph around entities
        subgraph = await graph_mgr.get_subgraph(["e1", "e2", "e3"], depth=2)
    """

    def __init__(self, neo4j_driver):
        """
        Initialize GraphManager with Neo4j driver.

        Args:
            neo4j_driver: Active Neo4j driver instance
        """
        self.driver = neo4j_driver
        logger.info("GraphManager initialized")

    async def get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
        """
        Retrieve a single entity by its ID.

        Searches across all entity types (Topic, Concept, Methodology, Finding).

        Args:
            entity_id: Unique entity identifier

        Returns:
            Entity object if found, None otherwise
        """
        try:
            cypher = """
            MATCH (e)
            WHERE (e:Topic OR e:Concept OR e:Methodology OR e:Finding)
            AND e.id = $entity_id
            RETURN e.id as id, e.name as name, labels(e)[0] as entity_type,
                   e.definition as definition, e.module_id as module_id,
                   e.confidence as confidence, e.mention_count as mention_count
            LIMIT 1
            """

            with self.driver.session() as session:
                result = session.run(cypher, {"entity_id": entity_id})
                record = result.single()

                if record:
                    return Entity(
                        id=record["id"],
                        name=record["name"],
                        entity_type=record["entity_type"],
                        definition=record.get("definition"),
                        module_id=record.get("module_id"),
                        confidence=record.get("confidence"),
                        mention_count=record.get("mention_count"),
                    )

            return None

        except Exception as e:
            logger.warning(f"Failed to get entity by ID {entity_id}: {e}")
            return None

    async def get_entities_by_name(
        self,
        name: str,
        module_id: Optional[str] = None,
    ) -> List[Entity]:
        """
        Find entities by name (case-insensitive partial match).

        Args:
            name: Entity name to search for
            module_id: Optional module ID to filter by

        Returns:
            List of matching Entity objects
        """
        try:
            if module_id:
                cypher = """
                MATCH (e)
                WHERE (e:Topic OR e:Concept OR e:Methodology OR e:Finding)
                AND toLower(e.name) CONTAINS toLower($name)
                AND e.module_id = $module_id
                RETURN e.id as id, e.name as name, labels(e)[0] as entity_type,
                       e.definition as definition, e.module_id as module_id,
                       e.confidence as confidence, e.mention_count as mention_count
                ORDER BY e.mention_count DESC
                LIMIT 20
                """
                params = {"name": name, "module_id": module_id}
            else:
                cypher = """
                MATCH (e)
                WHERE (e:Topic OR e:Concept OR e:Methodology OR e:Finding)
                AND toLower(e.name) CONTAINS toLower($name)
                RETURN e.id as id, e.name as name, labels(e)[0] as entity_type,
                       e.definition as definition, e.module_id as module_id,
                       e.confidence as confidence, e.mention_count as mention_count
                ORDER BY e.mention_count DESC
                LIMIT 20
                """
                params = {"name": name}

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
                            confidence=record.get("confidence"),
                            mention_count=record.get("mention_count"),
                        )
                    )

            logger.debug(f"Found {len(entities)} entities matching '{name}'")
            return entities

        except Exception as e:
            logger.warning(f"Failed to get entities by name '{name}': {e}")
            return []

    async def get_entity_neighbors(
        self,
        entity_id: str,
        relationship_types: Optional[List[str]] = None,
        direction: Literal["outgoing", "incoming", "both"] = "both",
        limit: int = MAX_NEIGHBORS,
    ) -> List[Dict[str, Any]]:
        """
        Get immediate neighbors (1-hop) of an entity.

        Args:
            entity_id: Entity ID to find neighbors for
            relationship_types: Filter by specific relationship types (default: all)
            direction: Relationship direction - outgoing, incoming, or both
            limit: Maximum number of neighbors to return

        Returns:
            List of neighbor dictionaries with entity info and relationship details
        """
        try:
            # Build relationship pattern based on direction
            rel_types = relationship_types or ALL_RELATIONSHIP_TYPES
            rel_pattern = "|".join(rel_types)

            if direction == "outgoing":
                match_pattern = f"(start)-[r:{rel_pattern}]->(neighbor)"
            elif direction == "incoming":
                match_pattern = f"(start)<-[r:{rel_pattern}]-(neighbor)"
            else:  # both
                match_pattern = f"(start)-[r:{rel_pattern}]-(neighbor)"

            cypher = f"""
            MATCH (start)
            WHERE (start:Topic OR start:Concept OR start:Methodology OR start:Finding)
            AND start.id = $entity_id
            MATCH {match_pattern}
            WHERE neighbor:Topic OR neighbor:Concept OR neighbor:Methodology OR neighbor:Finding
            RETURN neighbor.id as id, neighbor.name as name, labels(neighbor)[0] as entity_type,
                   neighbor.definition as definition, neighbor.module_id as module_id,
                   type(r) as relationship_type, r.confidence as rel_confidence,
                   startNode(r).id = start.id as is_outgoing
            ORDER BY r.confidence DESC
            LIMIT $limit
            """

            neighbors = []
            with self.driver.session() as session:
                result = session.run(cypher, {"entity_id": entity_id, "limit": limit})
                for record in result:
                    rel_type = record["relationship_type"]
                    neighbors.append(
                        {
                            "id": record["id"],
                            "name": record["name"],
                            "entity_type": record["entity_type"],
                            "definition": record.get("definition"),
                            "module_id": record.get("module_id"),
                            "relationship_type": rel_type,
                            "relationship_confidence": record.get(
                                "rel_confidence", 1.0
                            ),
                            "relationship_weight": RELATIONSHIP_WEIGHTS.get(
                                rel_type, 0.4
                            ),
                            "is_outgoing": record.get("is_outgoing", True),
                        }
                    )

            logger.debug(f"Found {len(neighbors)} neighbors for entity {entity_id}")
            return neighbors

        except Exception as e:
            logger.warning(f"Failed to get neighbors for entity {entity_id}: {e}")
            return []

    async def get_paths_between(
        self,
        source_id: str,
        target_id: str,
        max_hops: int = 3,
    ) -> List[EntityPath]:
        """
        Find all paths between two entities up to max_hops length.

        Args:
            source_id: Starting entity ID
            target_id: Target entity ID
            max_hops: Maximum path length (default: 3)

        Returns:
            List of EntityPath objects representing paths between entities
        """
        try:
            # Clamp max_hops to reasonable limits
            max_hops = min(max_hops, MAX_HOP_DEPTH)

            cypher = """
            MATCH path = shortestPath((source)-[*1..$max_hops]-(target))
            WHERE (source:Topic OR source:Concept OR source:Methodology OR source:Finding)
            AND (target:Topic OR target:Concept OR target:Methodology OR target:Finding)
            AND source.id = $source_id
            AND target.id = $target_id
            UNWIND relationships(path) as rel
            RETURN source.name as source_name, target.name as target_name,
                   type(rel) as relationship_type, rel.confidence as confidence,
                   length(path) as hops
            """

            paths = []
            with self.driver.session() as session:
                result = session.run(
                    cypher,
                    {
                        "source_id": source_id,
                        "target_id": target_id,
                        "max_hops": max_hops,
                    },
                )
                for record in result:
                    paths.append(
                        EntityPath(
                            source_entity=record["source_name"],
                            target_entity=record["target_name"],
                            relationship_type=record["relationship_type"],
                            confidence=record.get("confidence", 1.0) or 1.0,
                            hops=record["hops"],
                        )
                    )

            logger.debug(
                f"Found {len(paths)} paths between {source_id} and {target_id}"
            )
            return paths

        except Exception as e:
            logger.warning(
                f"Failed to find paths between {source_id} and {target_id}: {e}"
            )
            return []

    async def get_subgraph(
        self,
        entity_ids: List[str],
        depth: int = DEFAULT_HOP_DEPTH,
        module_ids: Optional[List[str]] = None,
    ) -> Subgraph:
        """
        Extract a subgraph centered on the given entities.

        Expands outward from seed entities to the specified depth,
        collecting all nodes and edges encountered.

        Args:
            entity_ids: Seed entity IDs to expand from
            depth: Number of hops to expand (default: 2)
            module_ids: Optional module IDs to filter by

        Returns:
            Subgraph object containing nodes and edges
        """
        if not entity_ids:
            return Subgraph(nodes=[], edges=[], node_count=0, edge_count=0)

        try:
            depth = min(depth, MAX_HOP_DEPTH)

            # Build module filter clause
            module_filter = ""
            params: Dict[str, Any] = {"entity_ids": entity_ids, "depth": depth}

            if module_ids:
                module_filter = "AND (related.module_id IN $module_ids OR related.module_id IS NULL)"
                params["module_ids"] = module_ids

            cypher = f"""
            MATCH (start)
            WHERE (start:Topic OR start:Concept OR start:Methodology OR start:Finding)
            AND start.id IN $entity_ids
            CALL {{
                WITH start
                MATCH path = (start)-[*1..$depth]-(related)
                WHERE (related:Topic OR related:Concept OR related:Methodology OR related:Finding)
                {module_filter}
                RETURN path
                LIMIT 100
            }}
            WITH path
            UNWIND nodes(path) as node
            UNWIND relationships(path) as rel
            WITH COLLECT(DISTINCT node) as all_nodes, COLLECT(DISTINCT rel) as all_rels
            RETURN 
                [n IN all_nodes | {{
                    id: n.id,
                    name: n.name,
                    type: labels(n)[0],
                    definition: n.definition,
                    module_id: n.module_id
                }}] as nodes,
                [r IN all_rels | {{
                    source: startNode(r).id,
                    target: endNode(r).id,
                    type: type(r),
                    confidence: r.confidence
                }}] as edges
            """

            with self.driver.session() as session:
                result = session.run(cypher, params)
                record = result.single()

                if record:
                    nodes = record["nodes"] or []
                    edges = record["edges"] or []
                    return Subgraph(
                        nodes=nodes,
                        edges=edges,
                        node_count=len(nodes),
                        edge_count=len(edges),
                    )

            return Subgraph(nodes=[], edges=[], node_count=0, edge_count=0)

        except Exception as e:
            logger.warning(f"Failed to extract subgraph: {e}")
            return Subgraph(nodes=[], edges=[], node_count=0, edge_count=0)

    async def delete_document(self, doc_id: str) -> bool:
        """
        Delete a document and ALL associated data from Neo4j.

        This performs comprehensive cleanup:
        1. Delete parent chunks (ParentChunk nodes) with DETACH DELETE
        2. Delete child/regular chunks (Chunk nodes) with DETACH DELETE
        3. Delete the Document node explicitly
        4. Delete ALL orphaned entities (not connected to any remaining Document or Chunk)

        Args:
            doc_id: The unique ID of the document to delete

        Returns:
            True if deletion was successful, False otherwise
        """
        try:
            # Step 1: Check document exists
            check_query = """
            MATCH (d:Document {id: $doc_id})
            RETURN d.id as id
            """
            with self.driver.session() as session:
                result = session.run(check_query, {"doc_id": doc_id})
                record = result.single()

                if not record:
                    logger.warning(f"Document {doc_id} not found in Neo4j")
                    return True  # Consider it a success if already not present

            logger.info(f"Starting deletion of document {doc_id}")

            # Step 2: Delete all parent chunks linked to this document
            delete_parent_chunks_query = """
            MATCH (d:Document {id: $doc_id})-[:HAS_PARENT_CHUNK]->(p:ParentChunk)
            DETACH DELETE p
            """
            with self.driver.session() as session:
                session.run(delete_parent_chunks_query, {"doc_id": doc_id})
            logger.debug(f"Deleted parent chunks for document {doc_id}")

            # Step 3: Delete all child/regular chunks linked to this document
            delete_chunks_query = """
            MATCH (d:Document {id: $doc_id})-[:HAS_CHUNK]->(c:Chunk)
            DETACH DELETE c
            """
            with self.driver.session() as session:
                session.run(delete_chunks_query, {"doc_id": doc_id})
            logger.debug(f"Deleted chunks for document {doc_id}")

            # Step 4: Delete the document node itself (MUST be separate query!)
            delete_doc_query = """
            MATCH (d:Document {id: $doc_id})
            DETACH DELETE d
            """
            with self.driver.session() as session:
                session.run(delete_doc_query, {"doc_id": doc_id})
            logger.debug(f"Deleted Document node {doc_id}")

            # Step 5: GLOBAL ORPHAN CLEANUP
            # Delete ALL entities that are not connected to ANY Document or Chunk
            # This catches all orphaned nodes regardless of how they were linked
            cleanup_orphans_query = """
            MATCH (e)
            WHERE (e:Topic OR e:Concept OR e:Methodology OR e:Finding)
            AND NOT (e)<-[:ADDRESSES_TOPIC|MENTIONS_CONCEPT|SUPPORTS|USES_METHODOLOGY]-(:Document)
            AND NOT (e)<-[:CONTAINS_ENTITY]-(:Chunk)
            DETACH DELETE e
            """
            with self.driver.session() as session:
                session.run(cleanup_orphans_query, {})
            logger.debug("Cleaned up all orphaned entities globally")

            logger.info(f"Successfully completed deletion of document {doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False

    async def expand_graph_context(
        self,
        entity_ids: List[str],
        hop_depth: int = DEFAULT_HOP_DEPTH,
        module_ids: Optional[List[str]] = None,
        max_entities: int = MAX_EXPANDED_ENTITIES,
    ) -> GraphContext:
        """
        Expand graph context from seed entities through multi-hop traversal.

        This is the primary method for graph-based context expansion in RAG.
        It traverses relationships up to hop_depth, collecting related entities
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
            hop_depth = min(hop_depth, MAX_HOP_DEPTH)

            # Build module filter
            module_filter = ""
            params: Dict[str, Any] = {
                "entity_ids": entity_ids,
                "limit": max_entities,
            }

            if module_ids:
                module_filter = "AND (related.module_id IN $module_ids OR related.module_id IS NULL)"
                params["module_ids"] = module_ids

            # Multi-hop traversal query
            # Handles 1-hop and 2-hop in one query for efficiency
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
                cypher = f"""
                // 1-hop results
                MATCH (start)-[r1]->(hop1)
                WHERE (start:Topic OR start:Concept OR start:Methodology OR start:Finding)
                AND start.id IN $entity_ids
                AND (hop1:Topic OR hop1:Concept OR hop1:Methodology OR hop1:Finding)
                {module_filter.replace("related", "hop1")}
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
                {module_filter.replace("related", "hop2")}
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


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def weight_path(path: EntityPath) -> float:
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


def create_graph_manager(neo4j_driver=None) -> GraphManager:
    """
    Factory function to create GraphManager with default Neo4j driver.

    Args:
        neo4j_driver: Optional Neo4j driver (uses global if not provided)

    Returns:
        Configured GraphManager instance
    """
    if neo4j_driver is None:
        from api.neo4j_config import neo4j_driver as default_driver

        neo4j_driver = default_driver

    return GraphManager(neo4j_driver)
