"""
============================================================================
FILE: graph_preview.py
LOCATION: api/schemas/graph_preview.py
============================================================================

PURPOSE:
    Response schemas for graph preview API endpoints. Provides Pydantic
    models for graph visualization data returned to staff for module preview.

ROLE IN PROJECT:
    Defines data structures for knowledge graph visualization that match
    frontend expectations from FRONTEND-DEPENDENCIES.md.
    - Structures graph nodes and edges for frontend rendering
    - Supports flexible metadata through properties fields
    - Enables staff to preview knowledge graph modules

KEY COMPONENTS:
    - GraphNode: Single node with id, label, name, type, and properties
    - GraphEdge: Relationship between nodes with source, target, and type
    - GraphPreviewResponse: Complete graph data for visualization

DEPENDENCIES:
    - External: pydantic (BaseModel, Field), typing
    - Internal: None

USAGE:
    from api.schemas.graph_preview import GraphNode, GraphEdge
    node = GraphNode(id="n1", label="Person", name="Alice", type="Entity")
============================================================================
"""

from __future__ import annotations

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class GraphNode(BaseModel):
    """Single node in the knowledge graph."""

    id: str
    label: str
    name: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """Single edge/relationship in the knowledge graph."""

    id: str
    source: str
    target: str
    type: str
    properties: Dict[str, Any] = Field(default_factory=dict)


class GraphPreviewResponse(BaseModel):
    """Complete graph data for visualization."""

    nodes: List[GraphNode]
    edges: List[GraphEdge]
    node_count: int
    edge_count: int
    module_id: Optional[str] = None


class GraphStatsResponse(BaseModel):
    """Statistics about a module's knowledge graph."""

    node_count: int
    edge_count: int
    entity_types: Dict[str, int]  # type -> count
    relationship_types: Dict[str, int]  # type -> count
