# graph_preview.py
# Response schemas for graph preview API endpoints

# Provides Pydantic models for graph visualization data returned to staff
# for module preview. Matches frontend expectations from FRONTEND-DEPENDENCIES.md
# with GraphNode, GraphEdge, and GraphPreviewResponse types.

# @see: api/routers/graph_preview.py - API endpoints using these schemas
# @see: api/graph_manager.py - Graph data source
# @note: Properties field allows flexible entity/relationship metadata

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
