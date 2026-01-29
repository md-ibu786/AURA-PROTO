# graph_preview.py
# Lightweight graph preview API for module visualization
#
# Provides graph data for staff module preview without full RAG capabilities.
# Uses graph_manager.py directly, does NOT depend on rag_engine.py.
# Returns nodes and edges for frontend visualization components.
#
# @see: api/graph_manager.py - Graph data operations
# @see: api/schemas/graph_preview.py - Response schemas
# @note: Uses get_subgraph() and direct Neo4j queries for module-scoped data

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
import logging

from api.graph_manager import GraphManager
from api.schemas.graph_preview import (
    GraphPreviewResponse,
    GraphStatsResponse,
    GraphNode,
    GraphEdge,
)
from api.neo4j_config import neo4j_driver

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/graph-preview", tags=["Graph Preview"])

# Whitelist of allowed entity types to prevent Cypher injection
ALLOWED_ENTITY_TYPES = {"Topic", "Concept", "Methodology", "Finding"}


def get_graph_manager() -> GraphManager:
    """Dependency injection for GraphManager."""
    if neo4j_driver is None:
        raise HTTPException(status_code=503, detail="Neo4j driver not initialized")
    return GraphManager(neo4j_driver)


@router.get(
    "/modules/{module_id}",
    response_model=GraphPreviewResponse,
    summary="Get graph data for module preview",
)
async def get_module_graph(
    module_id: str,
    entity_types: Optional[List[str]] = Query(
        None, description="Filter by entity types"
    ),
    limit: int = Query(100, ge=1, le=500, description="Max nodes to return"),
    graph_manager: GraphManager = Depends(get_graph_manager),
):
    """
    Retrieve graph nodes and edges for a module.

    Used by staff to preview module knowledge graph before publishing.
    Returns nodes, edges, and counts for visualization.

    Args:
        module_id: Module identifier
        entity_types: Optional filter for specific entity types (Topic, Concept, etc.)
        limit: Maximum number of nodes to return (1-500)
        graph_manager: Injected GraphManager instance

    Returns:
        GraphPreviewResponse with nodes, edges, and counts
    """
    # Validate entity_types against whitelist BEFORE try block
    # (HTTPException should not be caught by generic exception handler)
    if entity_types:
        invalid_types = set(entity_types) - ALLOWED_ENTITY_TYPES
        if invalid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid entity types: {invalid_types}. "
                f"Allowed types: {ALLOWED_ENTITY_TYPES}",
            )

    try:
        # Query Neo4j for module entities
        cypher = """
        MATCH (e)
        WHERE (e:Topic OR e:Concept OR e:Methodology OR e:Finding)
        AND e.module_id = $module_id
        """

        # Add entity type filter if specified (safe after whitelist validation)
        if entity_types:
            type_filter = " OR ".join([f"e:{t}" for t in entity_types])
            cypher += f" AND ({type_filter})"

        # Apply LIMIT in query (not Python) for efficiency
        cypher += """
        WITH e
        LIMIT $limit
        WITH collect(e) as entities
        UNWIND entities as e1
        OPTIONAL MATCH (e1)-[r]->(e2)
        WHERE e2 IN entities
        RETURN 
            [entity IN entities | {
                id: entity.id,
                name: entity.name,
                type: labels(entity)[0],
                definition: entity.definition,
                confidence: entity.confidence,
                mention_count: entity.mention_count
            }] as entity_data,
            collect(DISTINCT {
                source: e1.id, 
                target: e2.id, 
                type: type(r),
                confidence: r.confidence
            }) as relationships
        LIMIT 1
        """

        with graph_manager.driver.session() as session:
            result = session.run(cypher, {"module_id": module_id, "limit": limit})
            record = result.single()

        if not record:
            logger.info(f"No entities found for module {module_id}")
            return GraphPreviewResponse(
                nodes=[], edges=[], node_count=0, edge_count=0, module_id=module_id
            )

        # Build nodes list (node data already formatted in query)
        nodes = []
        entity_data = record["entity_data"] or []
        node_ids = set()  # Track node IDs for edge filtering

        for entity in entity_data:
            if entity:
                node_id = entity.get("id", "")
                node_ids.add(node_id)
                nodes.append(
                    GraphNode(
                        id=node_id,
                        label=entity.get("name", ""),
                        name=entity.get("name", ""),
                        type=entity.get("type", "Entity"),
                        properties={
                            "definition": entity.get("definition"),
                            "confidence": entity.get("confidence"),
                            "mention_count": entity.get("mention_count"),
                        },
                    )
                )

        # Build edges list (filter to only nodes in returned set)
        edges = []
        edge_counter = 0
        for rel in record["relationships"] or []:
            if rel and rel.get("source") and rel.get("target") and rel.get("type"):
                # Only include edges where both endpoints are in the node set
                if rel["source"] in node_ids and rel["target"] in node_ids:
                    edges.append(
                        GraphEdge(
                            id=f"{rel['source']}_{rel['target']}_{edge_counter}",
                            source=rel["source"],
                            target=rel["target"],
                            type=rel["type"],
                            properties={"confidence": rel.get("confidence", 1.0)},
                        )
                    )
                    edge_counter += 1

        logger.info(
            f"Retrieved {len(nodes)} nodes and {len(edges)} edges for module {module_id}"
        )

        return GraphPreviewResponse(
            nodes=nodes,
            edges=edges,
            node_count=len(nodes),
            edge_count=len(edges),
            module_id=module_id,
        )

    except Exception as e:
        logger.error(f"Error retrieving module graph for {module_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve graph data: {str(e)}"
        )


@router.get(
    "/modules/{module_id}/stats",
    response_model=GraphStatsResponse,
    summary="Get graph statistics for module",
)
async def get_module_graph_stats(
    module_id: str, graph_manager: GraphManager = Depends(get_graph_manager)
):
    """
    Retrieve statistics about a module's knowledge graph.

    Returns counts by entity type and relationship type for quick overview.

    Args:
        module_id: Module identifier
        graph_manager: Injected GraphManager instance

    Returns:
        GraphStatsResponse with entity and relationship counts
    """
    try:
        # Query for entity type counts
        entity_cypher = """
        MATCH (e)
        WHERE (e:Topic OR e:Concept OR e:Methodology OR e:Finding)
        AND e.module_id = $module_id
        RETURN labels(e)[0] as entity_type, count(e) as count
        """

        # Query for relationship type counts
        rel_cypher = """
        MATCH (e1)-[r]->(e2)
        WHERE (e1:Topic OR e1:Concept OR e1:Methodology OR e1:Finding)
        AND (e2:Topic OR e2:Concept OR e2:Methodology OR e2:Finding)
        AND e1.module_id = $module_id
        AND e2.module_id = $module_id
        RETURN type(r) as rel_type, count(r) as count
        """

        entity_types = {}
        relationship_types = {}
        total_nodes = 0
        total_edges = 0

        with graph_manager.driver.session() as session:
            # Get entity counts
            result = session.run(entity_cypher, {"module_id": module_id})
            for record in result:
                entity_type = record["entity_type"]
                count = record["count"]
                entity_types[entity_type] = count
                total_nodes += count

            # Get relationship counts
            result = session.run(rel_cypher, {"module_id": module_id})
            for record in result:
                rel_type = record["rel_type"]
                count = record["count"]
                relationship_types[rel_type] = count
                total_edges += count

        logger.info(
            f"Retrieved stats for module {module_id}: {total_nodes} nodes, {total_edges} edges"
        )

        return GraphStatsResponse(
            node_count=total_nodes,
            edge_count=total_edges,
            entity_types=entity_types,
            relationship_types=relationship_types,
        )

    except Exception as e:
        logger.error(f"Error retrieving stats for module {module_id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve graph stats: {str(e)}"
        )
