"""
============================================================================
FILE: graph.py
LOCATION: api/schemas/graph.py
============================================================================

PURPOSE:
    Pydantic schemas for graph API endpoints including node types,
    relationships, and graph data structures for visualization.

ROLE IN PROJECT:
    Defines request/response schemas for the knowledge graph visualization API.
    Supports both metadata queries and graph data retrieval for frontend.
    - Provides schemas for graph metadata (types, counts, properties)
    - Structures graph data (nodes, edges) for frontend rendering
    - Supports optional pre-computed layout coordinates

KEY COMPONENTS:
    - NodeTypeSchema: Metadata about node types in the graph
    - RelationshipTypeSchema: Metadata about relationship types
    - GraphMetadata: Complete graph statistics and type information
    - GraphData: Nodes and edges for visualization rendering

DEPENDENCIES:
    - External: pydantic (BaseModel, Field), datetime, typing
    - Internal: None

USAGE:
    from api.schemas.graph import GraphData, GraphNode, GraphEdge
    data = GraphData(nodes=[...], edges=[...], total_nodes=100)
============================================================================
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class NodeTypeSchema(BaseModel):
    """Schema describing a node type in the graph."""

    name: str = Field(..., description="Name of the node type/label")
    properties: List[str] = Field(
        default_factory=list, description="List of property names on this node type"
    )
    count: int = Field(..., description="Number of nodes of this type")
    has_embedding: bool = Field(
        default=False, description="Whether nodes of this type have vector embeddings"
    )


class RelationshipTypeSchema(BaseModel):
    """Schema describing a relationship type in the graph."""

    name: str = Field(..., description="Name of the relationship type")
    source_types: List[str] = Field(
        default_factory=list, description="Node types that can be the source"
    )
    target_types: List[str] = Field(
        default_factory=list, description="Node types that can be the target"
    )
    properties: List[str] = Field(
        default_factory=list,
        description="List of property names on this relationship type",
    )
    count: int = Field(..., description="Number of relationships of this type")


class GraphSchema(BaseModel):
    """Complete schema of the graph structure and metadata."""

    node_types: List[NodeTypeSchema] = Field(
        default_factory=list, description="All node types in the graph"
    )
    relationship_types: List[RelationshipTypeSchema] = Field(
        default_factory=list, description="All relationship types in the graph"
    )
    total_nodes: int = Field(..., description="Total number of nodes in the graph")
    total_relationships: int = Field(
        ..., description="Total number of relationships in the graph"
    )
    last_updated: datetime = Field(..., description="Timestamp of last graph update")


class GraphNode(BaseModel):
    """A node in the graph for visualization."""

    id: str = Field(..., description="Unique node identifier")
    label: str = Field(..., description="Node type/label")
    name: str = Field(..., description="Display name for the node")
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Additional node properties"
    )
    x: Optional[float] = Field(
        default=None, description="X coordinate for pre-computed layouts"
    )
    y: Optional[float] = Field(
        default=None, description="Y coordinate for pre-computed layouts"
    )


class GraphEdge(BaseModel):
    """An edge/relationship in the graph for visualization."""

    id: str = Field(..., description="Unique edge identifier")
    source: str = Field(..., description="Source node ID")
    target: str = Field(..., description="Target node ID")
    type: str = Field(..., description="Relationship type name")
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Additional edge properties"
    )


class GraphData(BaseModel):
    """Graph data response containing nodes and edges for visualization."""

    nodes: List[GraphNode] = Field(
        default_factory=list, description="List of graph nodes"
    )
    edges: List[GraphEdge] = Field(
        default_factory=list, description="List of graph edges"
    )
    node_count: int = Field(..., description="Total number of nodes in response")
    edge_count: int = Field(..., description="Total number of edges in response")
    module_id: Optional[str] = Field(
        default=None, description="Module ID if graph is filtered by module"
    )
