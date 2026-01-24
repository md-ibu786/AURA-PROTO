# graph_visualizer.py
# Graph visualization service for generating visualization-ready graph data

# Provides methods to generate graph visualizations at different granularity levels
# (module, document, cross-module), apply layout algorithms, and export graphs
# in multiple formats. Consistent with AURA-CHAT graph visualization patterns.

# @see: api/graph_manager.py - Graph traversal operations
# @see: api/routers/query.py - API endpoints using this service
# @see: api/schemas/neo4j_schema.py - Canonical schema definition
# @note: Force-directed layout is the default; others available for specific use cases

from __future__ import annotations

import io
import json
import math
import logging
from datetime import datetime
from enum import Enum
from typing import List, Dict, Any, Optional, Tuple, Set
from xml.etree import ElementTree as ET

from pydantic import BaseModel, Field


# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# CONSTANTS
# ============================================================================

# Entity type colors (consistent across AURA platform)
ENTITY_COLORS: Dict[str, str] = {
    "Topic": "#4CAF50",
    "Concept": "#2196F3",
    "Methodology": "#FF9800",
    "Finding": "#9C27B0",
    "Definition": "#00BCD4",
    "Document": "#795548",
    "Chunk": "#607D8B",
    "ParentChunk": "#8D6E63",
    "Module": "#3F51B5",
    "StudySession": "#E91E63",
    "Message": "#9E9E9E",
}

# Default node sizes by type
DEFAULT_NODE_SIZES: Dict[str, float] = {
    "Module": 2.0,
    "Document": 1.5,
    "ParentChunk": 1.2,
    "Topic": 1.3,
    "Concept": 1.2,
    "Methodology": 1.2,
    "Finding": 1.2,
    "Definition": 1.0,
    "Chunk": 0.8,
}

# Relationship colors
RELATIONSHIP_COLORS: Dict[str, str] = {
    "DEFINES": "#4CAF50",
    "DEPENDS_ON": "#FF5722",
    "USES": "#2196F3",
    "SUPPORTS": "#8BC34A",
    "CONTRADICTS": "#F44336",
    "EXTENDS": "#9C27B0",
    "IMPLEMENTS": "#00BCD4",
    "REFERENCES": "#607D8B",
    "RELATED_TO": "#9E9E9E",
    "HAS_CHUNK": "#BDBDBD",
    "HAS_PARENT_CHUNK": "#BDBDBD",
    "HAS_CHILD": "#BDBDBD",
    "CONTAINS_ENTITY": "#78909C",
    "ADDRESSES_TOPIC": "#4CAF50",
    "BELONGS_TO_MODULE": "#3F51B5",
}


# ============================================================================
# ENUMS
# ============================================================================


class LayoutType(str, Enum):
    """Available graph layout algorithms."""
    FORCE_DIRECTED = "force_directed"
    HIERARCHICAL = "hierarchical"
    RADIAL = "radial"
    CIRCULAR = "circular"


class ExportFormat(str, Enum):
    """Available graph export formats."""
    JSON = "json"
    GRAPHML = "graphml"
    GEXF = "gexf"
    CSV = "csv"


# ============================================================================
# DATA MODELS
# ============================================================================


class GraphOptions(BaseModel):
    """Options for graph generation and filtering."""
    include_entity_types: Optional[List[str]] = Field(
        None,
        description="Entity types to include (None = all)"
    )
    exclude_entity_types: Optional[List[str]] = Field(
        None,
        description="Entity types to exclude"
    )
    include_relationship_types: Optional[List[str]] = Field(
        None,
        description="Relationship types to include (None = all)"
    )
    exclude_relationship_types: Optional[List[str]] = Field(
        None,
        description="Relationship types to exclude"
    )
    max_nodes: int = Field(
        500,
        ge=1,
        le=2000,
        description="Maximum number of nodes to include"
    )
    include_chunks: bool = Field(
        False,
        description="Include chunk nodes in visualization"
    )
    include_documents: bool = Field(
        True,
        description="Include document nodes in visualization"
    )
    layout: LayoutType = Field(
        LayoutType.FORCE_DIRECTED,
        description="Layout algorithm to apply"
    )
    group_by: Optional[str] = Field(
        None,
        description="Grouping attribute: 'type', 'module', 'document'"
    )


class VisualizationNode(BaseModel):
    """Node for graph visualization."""
    id: str
    label: str
    type: str
    group: Optional[str] = None
    size: float = 1.0
    color: Optional[str] = None
    x: Optional[float] = None
    y: Optional[float] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class VisualizationEdge(BaseModel):
    """Edge for graph visualization."""
    id: str
    source: str
    target: str
    type: str
    weight: float = 1.0
    color: Optional[str] = None
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphMetadata(BaseModel):
    """Metadata about the generated graph."""
    module_ids: List[str] = Field(default_factory=list)
    document_ids: List[str] = Field(default_factory=list)
    node_count: int = 0
    edge_count: int = 0
    entity_type_counts: Dict[str, int] = Field(default_factory=dict)
    relationship_type_counts: Dict[str, int] = Field(default_factory=dict)
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    options_used: Optional[GraphOptions] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class VisualizationGraph(BaseModel):
    """Complete visualization-ready graph."""
    nodes: List[VisualizationNode] = Field(default_factory=list)
    edges: List[VisualizationEdge] = Field(default_factory=list)
    metadata: GraphMetadata = Field(default_factory=GraphMetadata)
    layout_applied: bool = False

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# LAYOUT ALGORITHMS
# ============================================================================


def force_directed_layout(
    nodes: List[VisualizationNode],
    edges: List[VisualizationEdge],
    width: float = 1000,
    height: float = 800,
    iterations: int = 100
) -> List[VisualizationNode]:
    """
    Apply force-directed layout to nodes.
    
    Uses simple spring-electric model:
    - Nodes repel each other (Coulomb's law)
    - Edges attract connected nodes (spring force)
    """
    if not nodes:
        return nodes
    
    # Initialize positions in a circle
    center_x = width / 2
    center_y = height / 2
    radius = min(width, height) * 0.35
    
    positions: Dict[str, Tuple[float, float]] = {}
    for i, node in enumerate(nodes):
        angle = (2 * math.pi * i) / len(nodes)
        positions[node.id] = (
            center_x + radius * math.cos(angle),
            center_y + radius * math.sin(angle)
        )
    
    # Build adjacency for edge lookup
    edge_map: Dict[str, Set[str]] = {n.id: set() for n in nodes}
    for edge in edges:
        if edge.source in edge_map and edge.target in edge_map:
            edge_map[edge.source].add(edge.target)
            edge_map[edge.target].add(edge.source)
    
    # Force simulation parameters
    repulsion = 8000
    attraction = 0.03
    damping = 0.9
    
    for _ in range(iterations):
        forces: Dict[str, Tuple[float, float]] = {n.id: (0.0, 0.0) for n in nodes}
        
        # Repulsion between all nodes
        for i, node_a in enumerate(nodes):
            for node_b in nodes[i+1:]:
                pos_a = positions[node_a.id]
                pos_b = positions[node_b.id]
                
                dx = pos_a[0] - pos_b[0]
                dy = pos_a[1] - pos_b[1]
                dist = math.sqrt(dx * dx + dy * dy) or 0.1
                
                force = repulsion / (dist * dist)
                fx = (dx / dist) * force
                fy = (dy / dist) * force
                
                forces[node_a.id] = (forces[node_a.id][0] + fx, forces[node_a.id][1] + fy)
                forces[node_b.id] = (forces[node_b.id][0] - fx, forces[node_b.id][1] - fy)
        
        # Attraction along edges
        for edge in edges:
            if edge.source not in positions or edge.target not in positions:
                continue
                
            pos_a = positions[edge.source]
            pos_b = positions[edge.target]
            
            dx = pos_b[0] - pos_a[0]
            dy = pos_b[1] - pos_a[1]
            dist = math.sqrt(dx * dx + dy * dy) or 0.1
            
            force = dist * attraction * edge.weight
            fx = (dx / dist) * force
            fy = (dy / dist) * force
            
            forces[edge.source] = (forces[edge.source][0] + fx, forces[edge.source][1] + fy)
            forces[edge.target] = (forces[edge.target][0] - fx, forces[edge.target][1] - fy)
        
        # Apply forces with damping
        for node in nodes:
            pos = positions[node.id]
            force = forces[node.id]
            
            new_x = pos[0] + force[0] * damping
            new_y = pos[1] + force[1] * damping
            
            # Keep within bounds
            new_x = max(50, min(width - 50, new_x))
            new_y = max(50, min(height - 50, new_y))
            
            positions[node.id] = (new_x, new_y)
    
    # Apply positions to nodes
    for node in nodes:
        pos = positions[node.id]
        node.x = pos[0]
        node.y = pos[1]
    
    return nodes


def hierarchical_layout(
    nodes: List[VisualizationNode],
    edges: List[VisualizationEdge],
    width: float = 1000,
    height: float = 800
) -> List[VisualizationNode]:
    """
    Apply hierarchical layout based on node types.
    
    Layers (top to bottom):
    1. Modules
    2. Documents
    3. Topics/Concepts/Methodologies/Findings
    4. Chunks
    """
    if not nodes:
        return nodes
    
    # Define layer order
    layer_order = {
        "Module": 0,
        "Document": 1,
        "Topic": 2,
        "Concept": 2,
        "Methodology": 2,
        "Finding": 2,
        "Definition": 2,
        "ParentChunk": 3,
        "Chunk": 4,
    }
    
    # Group nodes by layer
    layers: Dict[int, List[VisualizationNode]] = {}
    for node in nodes:
        layer = layer_order.get(node.type, 2)
        if layer not in layers:
            layers[layer] = []
        layers[layer].append(node)
    
    # Calculate positions
    num_layers = max(layers.keys()) + 1 if layers else 1
    layer_height = height / (num_layers + 1)
    
    for layer_idx, layer_nodes in layers.items():
        y = layer_height * (layer_idx + 1)
        node_width = width / (len(layer_nodes) + 1)
        
        for i, node in enumerate(layer_nodes):
            node.x = node_width * (i + 1)
            node.y = y
    
    return nodes


def radial_layout(
    nodes: List[VisualizationNode],
    edges: List[VisualizationEdge],
    center_node_id: Optional[str] = None,
    width: float = 1000,
    height: float = 800
) -> List[VisualizationNode]:
    """
    Apply radial layout around a center node.
    
    Center node is placed in the middle, connected nodes in concentric circles.
    """
    if not nodes:
        return nodes
    
    center_x = width / 2
    center_y = height / 2
    
    # Find center node (first node if not specified)
    center = center_node_id or (nodes[0].id if nodes else None)
    
    # Build adjacency
    neighbors: Dict[str, Set[str]] = {n.id: set() for n in nodes}
    for edge in edges:
        if edge.source in neighbors and edge.target in neighbors:
            neighbors[edge.source].add(edge.target)
            neighbors[edge.target].add(edge.source)
    
    # BFS to assign levels
    levels: Dict[str, int] = {}
    if center:
        levels[center] = 0
        queue = [center]
        while queue:
            current = queue.pop(0)
            for neighbor in neighbors.get(current, []):
                if neighbor not in levels:
                    levels[neighbor] = levels[current] + 1
                    queue.append(neighbor)
    
    # Nodes not connected to center
    max_level = max(levels.values()) if levels else 0
    for node in nodes:
        if node.id not in levels:
            levels[node.id] = max_level + 1
    
    # Group by level
    level_nodes: Dict[int, List[str]] = {}
    for node_id, level in levels.items():
        if level not in level_nodes:
            level_nodes[level] = []
        level_nodes[level].append(node_id)
    
    # Assign positions
    max_radius = min(width, height) * 0.4
    node_map = {n.id: n for n in nodes}
    
    for level, node_ids in level_nodes.items():
        if level == 0:
            # Center node
            for node_id in node_ids:
                if node_id in node_map:
                    node_map[node_id].x = center_x
                    node_map[node_id].y = center_y
        else:
            # Concentric circle
            radius = (level / (max(levels.values()) or 1)) * max_radius
            for i, node_id in enumerate(node_ids):
                angle = (2 * math.pi * i) / len(node_ids)
                if node_id in node_map:
                    node_map[node_id].x = center_x + radius * math.cos(angle)
                    node_map[node_id].y = center_y + radius * math.sin(angle)
    
    return nodes


def circular_layout(
    nodes: List[VisualizationNode],
    edges: List[VisualizationEdge],
    width: float = 1000,
    height: float = 800
) -> List[VisualizationNode]:
    """
    Apply simple circular layout.
    
    All nodes arranged in a circle, optionally grouped by type.
    """
    if not nodes:
        return nodes
    
    center_x = width / 2
    center_y = height / 2
    radius = min(width, height) * 0.4
    
    # Sort by type for grouping
    sorted_nodes = sorted(nodes, key=lambda n: n.type)
    
    for i, node in enumerate(sorted_nodes):
        angle = (2 * math.pi * i) / len(sorted_nodes)
        node.x = center_x + radius * math.cos(angle)
        node.y = center_y + radius * math.sin(angle)
    
    return nodes


# ============================================================================
# GRAPH VISUALIZER CLASS
# ============================================================================


class GraphVisualizer:
    """
    Service for generating visualization-ready graph data.
    
    Provides methods to:
    - Generate module-level, document-level, and cross-module graphs
    - Apply various layout algorithms
    - Export graphs in multiple formats
    
    Example:
        visualizer = GraphVisualizer(graph_manager)
        graph = await visualizer.get_module_graph("module_123", GraphOptions())
        export_data = visualizer.export_graph(graph, ExportFormat.JSON)
    """
    
    def __init__(self, graph_manager):
        """
        Initialize GraphVisualizer with a GraphManager.
        
        Args:
            graph_manager: GraphManager instance for Neo4j operations
        """
        self.graph_manager = graph_manager
        logger.info("GraphVisualizer initialized")
    
    def _get_node_color(self, node_type: str) -> str:
        """Get color for a node type."""
        return ENTITY_COLORS.get(node_type, "#999999")
    
    def _get_node_size(self, node_type: str) -> float:
        """Get default size for a node type."""
        return DEFAULT_NODE_SIZES.get(node_type, 1.0)
    
    def _get_edge_color(self, relationship_type: str) -> str:
        """Get color for a relationship type."""
        return RELATIONSHIP_COLORS.get(relationship_type, "#9E9E9E")
    
    def _filter_nodes(
        self,
        nodes: List[VisualizationNode],
        options: GraphOptions
    ) -> List[VisualizationNode]:
        """Filter nodes based on options."""
        filtered = nodes
        
        if options.include_entity_types:
            filtered = [n for n in filtered if n.type in options.include_entity_types]
        
        if options.exclude_entity_types:
            filtered = [n for n in filtered if n.type not in options.exclude_entity_types]
        
        if not options.include_chunks:
            filtered = [n for n in filtered if n.type not in ("Chunk", "ParentChunk")]
        
        if not options.include_documents:
            filtered = [n for n in filtered if n.type != "Document"]
        
        # Limit nodes
        if len(filtered) > options.max_nodes:
            filtered = filtered[:options.max_nodes]
        
        return filtered
    
    def _filter_edges(
        self,
        edges: List[VisualizationEdge],
        valid_node_ids: Set[str],
        options: GraphOptions
    ) -> List[VisualizationEdge]:
        """Filter edges based on options and valid nodes."""
        filtered = [
            e for e in edges
            if e.source in valid_node_ids and e.target in valid_node_ids
        ]
        
        if options.include_relationship_types:
            filtered = [e for e in filtered if e.type in options.include_relationship_types]
        
        if options.exclude_relationship_types:
            filtered = [e for e in filtered if e.type not in options.exclude_relationship_types]
        
        return filtered
    
    async def get_module_graph(
        self,
        module_id: str,
        options: Optional[GraphOptions] = None
    ) -> VisualizationGraph:
        """
        Get visualization graph for a module.
        
        Retrieves all entities and relationships within a module,
        applies filtering and layout.
        
        Args:
            module_id: Module identifier
            options: Graph generation options
            
        Returns:
            VisualizationGraph ready for rendering
        """
        options = options or GraphOptions()
        
        try:
            # Query for module graph data
            cypher = """
            MATCH (m:Module {id: $module_id})
            OPTIONAL MATCH (e)-[:BELONGS_TO_MODULE]->(m)
            WHERE e:Topic OR e:Concept OR e:Methodology OR e:Finding OR e:Definition
            WITH m, collect(DISTINCT e) as entities
            
            OPTIONAL MATCH (d:Document)-[:BELONGS_TO_MODULE]->(m)
            WITH m, entities, collect(DISTINCT d) as documents
            
            UNWIND entities as e1
            OPTIONAL MATCH (e1)-[r]->(e2)
            WHERE e2 IN entities
            
            RETURN 
                m as module,
                entities,
                documents,
                collect(DISTINCT {source: e1.id, target: e2.id, type: type(r)}) as relationships
            """
            
            with self.graph_manager.driver.session() as session:
                result = session.run(cypher, {"module_id": module_id})
                record = result.single()
            
            nodes: List[VisualizationNode] = []
            edges: List[VisualizationEdge] = []
            
            if record:
                # Add module node
                module = record.get("module")
                if module:
                    nodes.append(VisualizationNode(
                        id=module.get("id", module_id),
                        label=module.get("name", module_id),
                        type="Module",
                        color=self._get_node_color("Module"),
                        size=self._get_node_size("Module"),
                        group="module",
                        properties=dict(module) if module else {}
                    ))
                
                # Add entity nodes
                for entity in record.get("entities", []):
                    if entity:
                        entity_type = entity.labels[0] if hasattr(entity, 'labels') else "Entity"
                        nodes.append(VisualizationNode(
                            id=entity.get("id"),
                            label=entity.get("name", entity.get("id")),
                            type=entity_type,
                            color=self._get_node_color(entity_type),
                            size=self._get_node_size(entity_type),
                            group=entity_type.lower(),
                            properties=dict(entity)
                        ))
                
                # Add document nodes
                if options.include_documents:
                    for doc in record.get("documents", []):
                        if doc:
                            nodes.append(VisualizationNode(
                                id=doc.get("id"),
                                label=doc.get("title", doc.get("id")),
                                type="Document",
                                color=self._get_node_color("Document"),
                                size=self._get_node_size("Document"),
                                group="document",
                                properties=dict(doc)
                            ))
                
                # Add edges
                for rel in record.get("relationships", []):
                    if rel and rel.get("source") and rel.get("target"):
                        rel_type = rel.get("type", "RELATED_TO")
                        edges.append(VisualizationEdge(
                            id=f"{rel['source']}_{rel['target']}_{rel_type}",
                            source=rel["source"],
                            target=rel["target"],
                            type=rel_type,
                            color=self._get_edge_color(rel_type),
                            weight=1.0
                        ))
            
            # Apply filters
            nodes = self._filter_nodes(nodes, options)
            valid_ids = {n.id for n in nodes}
            edges = self._filter_edges(edges, valid_ids, options)
            
            # Apply layout
            graph = VisualizationGraph(
                nodes=nodes,
                edges=edges,
                metadata=GraphMetadata(
                    module_ids=[module_id],
                    node_count=len(nodes),
                    edge_count=len(edges),
                    entity_type_counts=self._count_by_type(nodes),
                    relationship_type_counts=self._count_edges_by_type(edges),
                    options_used=options
                )
            )
            
            return self.apply_layout(graph, options.layout)
            
        except Exception as e:
            logger.error(f"Error getting module graph: {e}")
            return VisualizationGraph(
                metadata=GraphMetadata(module_ids=[module_id], options_used=options)
            )
    
    async def get_document_graph(
        self,
        document_id: str,
        options: Optional[GraphOptions] = None
    ) -> VisualizationGraph:
        """
        Get visualization graph for a document.
        
        Shows document structure with chunks and extracted entities.
        
        Args:
            document_id: Document identifier
            options: Graph generation options
            
        Returns:
            VisualizationGraph for the document
        """
        options = options or GraphOptions()
        
        try:
            cypher = """
            MATCH (d:Document {id: $document_id})
            OPTIONAL MATCH (d)-[:HAS_CHUNK]->(c:Chunk)
            OPTIONAL MATCH (c)-[:CONTAINS_ENTITY]->(e)
            WHERE e:Topic OR e:Concept OR e:Methodology OR e:Finding
            
            RETURN 
                d as document,
                collect(DISTINCT c) as chunks,
                collect(DISTINCT e) as entities,
                collect(DISTINCT {chunk_id: c.id, entity_id: e.id}) as chunk_entities
            """
            
            with self.graph_manager.driver.session() as session:
                result = session.run(cypher, {"document_id": document_id})
                record = result.single()
            
            nodes: List[VisualizationNode] = []
            edges: List[VisualizationEdge] = []
            
            if record:
                # Add document node
                doc = record.get("document")
                if doc:
                    nodes.append(VisualizationNode(
                        id=doc.get("id", document_id),
                        label=doc.get("title", document_id),
                        type="Document",
                        color=self._get_node_color("Document"),
                        size=self._get_node_size("Document"),
                        properties=dict(doc)
                    ))
                
                # Add chunk nodes if requested
                if options.include_chunks:
                    for chunk in record.get("chunks", []):
                        if chunk:
                            nodes.append(VisualizationNode(
                                id=chunk.get("id"),
                                label=f"Chunk {chunk.get('position', '')}",
                                type="Chunk",
                                color=self._get_node_color("Chunk"),
                                size=self._get_node_size("Chunk"),
                                properties=dict(chunk)
                            ))
                            
                            # Add edge from document to chunk
                            edges.append(VisualizationEdge(
                                id=f"{document_id}_HAS_CHUNK_{chunk.get('id')}",
                                source=document_id,
                                target=chunk.get("id"),
                                type="HAS_CHUNK",
                                color=self._get_edge_color("HAS_CHUNK")
                            ))
                
                # Add entity nodes
                for entity in record.get("entities", []):
                    if entity:
                        entity_type = entity.labels[0] if hasattr(entity, 'labels') else "Entity"
                        nodes.append(VisualizationNode(
                            id=entity.get("id"),
                            label=entity.get("name", entity.get("id")),
                            type=entity_type,
                            color=self._get_node_color(entity_type),
                            size=self._get_node_size(entity_type),
                            properties=dict(entity)
                        ))
                
                # Add chunk-entity edges if chunks included
                if options.include_chunks:
                    for ce in record.get("chunk_entities", []):
                        if ce and ce.get("chunk_id") and ce.get("entity_id"):
                            edges.append(VisualizationEdge(
                                id=f"{ce['chunk_id']}_CONTAINS_{ce['entity_id']}",
                                source=ce["chunk_id"],
                                target=ce["entity_id"],
                                type="CONTAINS_ENTITY",
                                color=self._get_edge_color("CONTAINS_ENTITY")
                            ))
            
            # Apply filters
            nodes = self._filter_nodes(nodes, options)
            valid_ids = {n.id for n in nodes}
            edges = self._filter_edges(edges, valid_ids, options)
            
            graph = VisualizationGraph(
                nodes=nodes,
                edges=edges,
                metadata=GraphMetadata(
                    document_ids=[document_id],
                    node_count=len(nodes),
                    edge_count=len(edges),
                    entity_type_counts=self._count_by_type(nodes),
                    relationship_type_counts=self._count_edges_by_type(edges),
                    options_used=options
                )
            )
            
            return self.apply_layout(graph, options.layout)
            
        except Exception as e:
            logger.error(f"Error getting document graph: {e}")
            return VisualizationGraph(
                metadata=GraphMetadata(document_ids=[document_id], options_used=options)
            )
    
    async def get_cross_module_graph(
        self,
        module_ids: List[str],
        options: Optional[GraphOptions] = None
    ) -> VisualizationGraph:
        """
        Get visualization graph comparing multiple modules.
        
        Shows entities from each module, highlighting shared concepts.
        
        Args:
            module_ids: List of module identifiers
            options: Graph generation options
            
        Returns:
            VisualizationGraph showing cross-module relationships
        """
        options = options or GraphOptions()
        
        try:
            # Get entities for all modules
            cypher = """
            UNWIND $module_ids as module_id
            MATCH (m:Module {id: module_id})
            OPTIONAL MATCH (e)-[:BELONGS_TO_MODULE]->(m)
            WHERE e:Topic OR e:Concept OR e:Methodology OR e:Finding
            
            RETURN 
                module_id,
                m as module,
                collect(DISTINCT e) as entities
            """
            
            with self.graph_manager.driver.session() as session:
                result = session.run(cypher, {"module_ids": module_ids})
                records = list(result)
            
            nodes: List[VisualizationNode] = []
            edges: List[VisualizationEdge] = []
            seen_entity_ids: Set[str] = set()
            
            for record in records:
                module_id = record.get("module_id")
                module = record.get("module")
                
                # Add module node
                if module:
                    nodes.append(VisualizationNode(
                        id=module.get("id", module_id),
                        label=module.get("name", module_id),
                        type="Module",
                        color=self._get_node_color("Module"),
                        size=self._get_node_size("Module"),
                        group=f"module_{module_id}",
                        properties=dict(module)
                    ))
                
                # Add entity nodes with module grouping
                for entity in record.get("entities", []):
                    if entity:
                        entity_id = entity.get("id")
                        entity_type = entity.labels[0] if hasattr(entity, 'labels') else "Entity"
                        
                        if entity_id not in seen_entity_ids:
                            nodes.append(VisualizationNode(
                                id=entity_id,
                                label=entity.get("name", entity_id),
                                type=entity_type,
                                color=self._get_node_color(entity_type),
                                size=self._get_node_size(entity_type),
                                group=f"module_{module_id}",
                                properties=dict(entity)
                            ))
                            seen_entity_ids.add(entity_id)
                        
                        # Add edge from module to entity
                        edges.append(VisualizationEdge(
                            id=f"{module_id}_HAS_{entity_id}",
                            source=module_id,
                            target=entity_id,
                            type="BELONGS_TO_MODULE",
                            color=self._get_edge_color("BELONGS_TO_MODULE")
                        ))
            
            # Find cross-module relationships
            cross_cypher = """
            MATCH (e1)-[r]->(e2)
            WHERE e1:Topic OR e1:Concept OR e1:Methodology OR e1:Finding
            AND e2:Topic OR e2:Concept OR e2:Methodology OR e2:Finding
            AND e1.id IN $entity_ids AND e2.id IN $entity_ids
            RETURN DISTINCT e1.id as source, e2.id as target, type(r) as rel_type
            """
            
            with self.graph_manager.driver.session() as session:
                rel_result = session.run(cross_cypher, {"entity_ids": list(seen_entity_ids)})
                for rel in rel_result:
                    rel_type = rel.get("rel_type", "RELATED_TO")
                    edges.append(VisualizationEdge(
                        id=f"{rel['source']}_{rel['target']}_{rel_type}",
                        source=rel["source"],
                        target=rel["target"],
                        type=rel_type,
                        color=self._get_edge_color(rel_type)
                    ))
            
            # Apply filters
            nodes = self._filter_nodes(nodes, options)
            valid_ids = {n.id for n in nodes}
            edges = self._filter_edges(edges, valid_ids, options)
            
            graph = VisualizationGraph(
                nodes=nodes,
                edges=edges,
                metadata=GraphMetadata(
                    module_ids=module_ids,
                    node_count=len(nodes),
                    edge_count=len(edges),
                    entity_type_counts=self._count_by_type(nodes),
                    relationship_type_counts=self._count_edges_by_type(edges),
                    options_used=options
                )
            )
            
            return self.apply_layout(graph, options.layout)
            
        except Exception as e:
            logger.error(f"Error getting cross-module graph: {e}")
            return VisualizationGraph(
                metadata=GraphMetadata(module_ids=module_ids, options_used=options)
            )
    
    async def get_entity_neighborhood(
        self,
        entity_id: str,
        depth: int = 2
    ) -> VisualizationGraph:
        """
        Get neighborhood graph around an entity.
        
        Args:
            entity_id: Entity identifier
            depth: Number of hops to expand (1-4)
            
        Returns:
            VisualizationGraph of entity neighborhood
        """
        depth = max(1, min(4, depth))
        
        try:
            # Get entity and neighbors
            cypher = f"""
            MATCH (center {{id: $entity_id}})
            WHERE center:Topic OR center:Concept OR center:Methodology OR center:Finding
            
            CALL {{
                WITH center
                MATCH path = (center)-[*1..{depth}]-(neighbor)
                WHERE neighbor:Topic OR neighbor:Concept OR neighbor:Methodology OR neighbor:Finding
                RETURN neighbor, relationships(path) as rels
            }}
            
            RETURN 
                center,
                collect(DISTINCT neighbor) as neighbors,
                collect(DISTINCT rels) as all_rels
            """
            
            with self.graph_manager.driver.session() as session:
                result = session.run(cypher, {"entity_id": entity_id})
                record = result.single()
            
            nodes: List[VisualizationNode] = []
            edges: List[VisualizationEdge] = []
            
            if record:
                # Add center node
                center = record.get("center")
                if center:
                    center_type = center.labels[0] if hasattr(center, 'labels') else "Entity"
                    nodes.append(VisualizationNode(
                        id=center.get("id"),
                        label=center.get("name", entity_id),
                        type=center_type,
                        color=self._get_node_color(center_type),
                        size=self._get_node_size(center_type) * 1.5,  # Larger center
                        group="center",
                        properties=dict(center)
                    ))
                
                # Add neighbor nodes
                for neighbor in record.get("neighbors", []):
                    if neighbor:
                        n_type = neighbor.labels[0] if hasattr(neighbor, 'labels') else "Entity"
                        nodes.append(VisualizationNode(
                            id=neighbor.get("id"),
                            label=neighbor.get("name", neighbor.get("id")),
                            type=n_type,
                            color=self._get_node_color(n_type),
                            size=self._get_node_size(n_type),
                            properties=dict(neighbor)
                        ))
                
                # Extract edges from relationships
                seen_edges: Set[str] = set()
                for rel_list in record.get("all_rels", []):
                    if rel_list:
                        for rel in rel_list:
                            if rel:
                                edge_id = f"{rel.start_node.get('id')}_{rel.end_node.get('id')}_{type(rel).__name__}"
                                if edge_id not in seen_edges:
                                    rel_type = type(rel).__name__
                                    edges.append(VisualizationEdge(
                                        id=edge_id,
                                        source=rel.start_node.get("id"),
                                        target=rel.end_node.get("id"),
                                        type=rel_type,
                                        color=self._get_edge_color(rel_type)
                                    ))
                                    seen_edges.add(edge_id)
            
            graph = VisualizationGraph(
                nodes=nodes,
                edges=edges,
                metadata=GraphMetadata(
                    node_count=len(nodes),
                    edge_count=len(edges),
                    entity_type_counts=self._count_by_type(nodes),
                    relationship_type_counts=self._count_edges_by_type(edges)
                )
            )
            
            # Use radial layout for neighborhood
            return self.apply_layout(graph, LayoutType.RADIAL, center_node_id=entity_id)
            
        except Exception as e:
            logger.error(f"Error getting entity neighborhood: {e}")
            return VisualizationGraph()
    
    def apply_layout(
        self,
        graph: VisualizationGraph,
        layout: LayoutType,
        center_node_id: Optional[str] = None
    ) -> VisualizationGraph:
        """
        Apply layout algorithm to graph nodes.
        
        Args:
            graph: Graph to layout
            layout: Layout algorithm to use
            center_node_id: Optional center node for radial layout
            
        Returns:
            Graph with positions applied
        """
        if not graph.nodes:
            return graph
        
        if layout == LayoutType.FORCE_DIRECTED:
            graph.nodes = force_directed_layout(graph.nodes, graph.edges)
        elif layout == LayoutType.HIERARCHICAL:
            graph.nodes = hierarchical_layout(graph.nodes, graph.edges)
        elif layout == LayoutType.RADIAL:
            graph.nodes = radial_layout(graph.nodes, graph.edges, center_node_id)
        elif layout == LayoutType.CIRCULAR:
            graph.nodes = circular_layout(graph.nodes, graph.edges)
        
        graph.layout_applied = True
        return graph
    
    def export_graph(
        self,
        graph: VisualizationGraph,
        format: ExportFormat
    ) -> bytes:
        """
        Export graph in specified format.
        
        Args:
            graph: Graph to export
            format: Export format (JSON, GraphML, GEXF, CSV)
            
        Returns:
            Bytes of exported graph
        """
        if format == ExportFormat.JSON:
            return self._export_json(graph)
        elif format == ExportFormat.GRAPHML:
            return self._export_graphml(graph)
        elif format == ExportFormat.GEXF:
            return self._export_gexf(graph)
        elif format == ExportFormat.CSV:
            return self._export_csv(graph)
        else:
            return self._export_json(graph)
    
    def _export_json(self, graph: VisualizationGraph) -> bytes:
        """Export graph as JSON."""
        return json.dumps(graph.model_dump(), default=str).encode("utf-8")
    
    def _export_graphml(self, graph: VisualizationGraph) -> bytes:
        """Export graph as GraphML format."""
        root = ET.Element("graphml")
        root.set("xmlns", "http://graphml.graphdrawing.org/xmlns")
        
        # Define keys for node attributes
        for key in ["label", "type", "color", "size", "x", "y"]:
            key_elem = ET.SubElement(root, "key")
            key_elem.set("id", key)
            key_elem.set("for", "node")
            key_elem.set("attr.name", key)
            key_elem.set("attr.type", "string" if key in ["label", "type", "color"] else "double")
        
        # Define keys for edge attributes
        for key in ["type", "weight", "color"]:
            key_elem = ET.SubElement(root, "key")
            key_elem.set("id", f"e_{key}")
            key_elem.set("for", "edge")
            key_elem.set("attr.name", key)
            key_elem.set("attr.type", "string" if key in ["type", "color"] else "double")
        
        # Create graph element
        graph_elem = ET.SubElement(root, "graph")
        graph_elem.set("id", "G")
        graph_elem.set("edgedefault", "directed")
        
        # Add nodes
        for node in graph.nodes:
            node_elem = ET.SubElement(graph_elem, "node")
            node_elem.set("id", node.id)
            
            for key, value in [
                ("label", node.label),
                ("type", node.type),
                ("color", node.color or ""),
                ("size", str(node.size)),
                ("x", str(node.x or 0)),
                ("y", str(node.y or 0))
            ]:
                data_elem = ET.SubElement(node_elem, "data")
                data_elem.set("key", key)
                data_elem.text = value
        
        # Add edges
        for edge in graph.edges:
            edge_elem = ET.SubElement(graph_elem, "edge")
            edge_elem.set("id", edge.id)
            edge_elem.set("source", edge.source)
            edge_elem.set("target", edge.target)
            
            for key, value in [
                ("e_type", edge.type),
                ("e_weight", str(edge.weight)),
                ("e_color", edge.color or "")
            ]:
                data_elem = ET.SubElement(edge_elem, "data")
                data_elem.set("key", key)
                data_elem.text = value
        
        return ET.tostring(root, encoding="unicode").encode("utf-8")
    
    def _export_gexf(self, graph: VisualizationGraph) -> bytes:
        """Export graph as GEXF format (Gephi)."""
        root = ET.Element("gexf")
        root.set("xmlns", "http://www.gexf.net/1.3")
        root.set("version", "1.3")
        
        # Meta
        meta = ET.SubElement(root, "meta")
        creator = ET.SubElement(meta, "creator")
        creator.text = "AURA Platform"
        
        # Graph
        graph_elem = ET.SubElement(root, "graph")
        graph_elem.set("mode", "static")
        graph_elem.set("defaultedgetype", "directed")
        
        # Node attributes
        node_attrs = ET.SubElement(graph_elem, "attributes")
        node_attrs.set("class", "node")
        for i, (attr, atype) in enumerate([("type", "string"), ("color", "string")]):
            attr_elem = ET.SubElement(node_attrs, "attribute")
            attr_elem.set("id", str(i))
            attr_elem.set("title", attr)
            attr_elem.set("type", atype)
        
        # Nodes
        nodes_elem = ET.SubElement(graph_elem, "nodes")
        for node in graph.nodes:
            node_elem = ET.SubElement(nodes_elem, "node")
            node_elem.set("id", node.id)
            node_elem.set("label", node.label)
            
            attvalues = ET.SubElement(node_elem, "attvalues")
            for i, value in enumerate([node.type, node.color or ""]):
                attvalue = ET.SubElement(attvalues, "attvalue")
                attvalue.set("for", str(i))
                attvalue.set("value", value)
            
            if node.x is not None and node.y is not None:
                viz_pos = ET.SubElement(node_elem, "viz:position")
                viz_pos.set("x", str(node.x))
                viz_pos.set("y", str(node.y))
        
        # Edges
        edges_elem = ET.SubElement(graph_elem, "edges")
        for edge in graph.edges:
            edge_elem = ET.SubElement(edges_elem, "edge")
            edge_elem.set("id", edge.id)
            edge_elem.set("source", edge.source)
            edge_elem.set("target", edge.target)
            edge_elem.set("label", edge.type)
            edge_elem.set("weight", str(edge.weight))
        
        return ET.tostring(root, encoding="unicode").encode("utf-8")
    
    def _export_csv(self, graph: VisualizationGraph) -> bytes:
        """Export graph as CSV (nodes and edges in separate sections)."""
        output = io.StringIO()
        
        # Nodes section
        output.write("# NODES\n")
        output.write("id,label,type,color,size,x,y\n")
        for node in graph.nodes:
            output.write(f'"{node.id}","{node.label}","{node.type}","{node.color or ""}",{node.size},{node.x or 0},{node.y or 0}\n')
        
        output.write("\n# EDGES\n")
        output.write("source,target,type,weight,color\n")
        for edge in graph.edges:
            output.write(f'"{edge.source}","{edge.target}","{edge.type}",{edge.weight},"{edge.color or ""}"\n')
        
        return output.getvalue().encode("utf-8")
    
    def _count_by_type(self, nodes: List[VisualizationNode]) -> Dict[str, int]:
        """Count nodes by type."""
        counts: Dict[str, int] = {}
        for node in nodes:
            counts[node.type] = counts.get(node.type, 0) + 1
        return counts
    
    def _count_edges_by_type(self, edges: List[VisualizationEdge]) -> Dict[str, int]:
        """Count edges by relationship type."""
        counts: Dict[str, int] = {}
        for edge in edges:
            counts[edge.type] = counts.get(edge.type, 0) + 1
        return counts


# ============================================================================
# DEPENDENCY INJECTION HELPER
# ============================================================================


def get_graph_visualizer():
    """
    Dependency injection helper for FastAPI.
    
    Usage in routers:
        @router.get("/graph/module/{module_id}")
        async def get_module_graph(
            module_id: str,
            visualizer: GraphVisualizer = Depends(get_graph_visualizer)
        ):
            return await visualizer.get_module_graph(module_id)
    """
    from api.neo4j_config import neo4j_driver
    from api.graph_manager import GraphManager
    
    if neo4j_driver is None:
        raise RuntimeError("Neo4j driver not initialized")
    
    graph_manager = GraphManager(neo4j_driver)
    return GraphVisualizer(graph_manager)
