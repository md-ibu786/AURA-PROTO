# test_graph_preview.py
# Tests for graph preview API endpoints

# Verifies the lightweight graph preview API returns correct
# data structure for module visualization without RAG dependencies.
# Tests both endpoints (graph data + stats) with mocking to avoid Neo4j.

# @see: api/routers/graph_preview.py - Endpoints under test
# @see: api/schemas/graph_preview.py - Response schemas
# @note: Uses mocking for graph_manager to avoid Neo4j dependency

import os
import sys
import pytest
from pathlib import Path
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

# Set test mode before any imports
os.environ["AURA_TEST_MODE"] = "true"

# Add project paths
sys.path.insert(0, str(Path(__file__).parent.parent / "api"))
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.main import app
from api.schemas.graph_preview import (
    GraphNode,
    GraphEdge,
    GraphPreviewResponse,
    GraphStatsResponse,
)

client = TestClient(app)


@pytest.fixture
def mock_graph_data():
    """Sample graph data for testing."""
    return {
        "nodes": [
            {
                "id": "n1",
                "label": "Machine Learning",
                "name": "Machine Learning",
                "type": "Topic",
                "properties": {
                    "definition": "Study of algorithms that improve through experience",
                    "confidence": 0.95,
                    "mention_count": 10,
                },
            },
            {
                "id": "n2",
                "label": "Neural Networks",
                "name": "Neural Networks",
                "type": "Concept",
                "properties": {
                    "definition": "Computing systems inspired by biological neural networks",
                    "confidence": 0.88,
                    "mention_count": 8,
                },
            },
        ],
        "edges": [
            {
                "id": "e1",
                "source": "n1",
                "target": "n2",
                "type": "CONTAINS",
                "properties": {"confidence": 0.92},
            },
        ],
        "node_count": 2,
        "edge_count": 1,
        "module_id": "test-module",
    }


@pytest.fixture
def mock_stats_data():
    """Sample stats data for testing."""
    return {
        "node_count": 50,
        "edge_count": 75,
        "entity_types": {"Topic": 10, "Concept": 30, "Finding": 10},
        "relationship_types": {"CONTAINS": 40, "RELATES_TO": 35},
    }


@pytest.fixture
def mock_neo4j_session():
    """Mock Neo4j session with query results."""
    mock_session = Mock()
    mock_session.__enter__ = Mock(return_value=mock_session)
    mock_session.__exit__ = Mock(return_value=None)
    return mock_session


class TestGraphPreviewEndpoints:
    """Tests for /api/v1/graph-preview endpoints."""

    def test_get_module_graph_success(self, mock_neo4j_session):
        """GET /modules/{module_id} returns graph data with correct property mappings."""
        # Mock Neo4j query result
        mock_record = Mock()
        mock_record.__getitem__ = Mock(
            side_effect=lambda key: {
                "entity_data": [
                    {
                        "id": "n1",
                        "name": "Machine Learning",
                        "type": "Topic",
                        "definition": "Study of algorithms",
                        "confidence": 0.95,
                        "mention_count": 10,
                    },
                    {
                        "id": "n2",
                        "name": "Neural Networks",
                        "type": "Concept",
                        "definition": "Computing systems",
                        "confidence": 0.88,
                        "mention_count": 8,
                    },
                ],
                "relationships": [
                    {
                        "source": "n1",
                        "target": "n2",
                        "type": "CONTAINS",
                        "confidence": 0.92,
                    }
                ],
            }[key]
        )

        mock_result = Mock()
        mock_result.single = Mock(return_value=mock_record)
        mock_neo4j_session.run = Mock(return_value=mock_result)

        with patch("api.routers.graph_preview.neo4j_driver") as mock_driver:
            mock_driver.session = Mock(return_value=mock_neo4j_session)

            response = client.get("/api/v1/graph-preview/modules/test-module")

            assert response.status_code == 200
            data = response.json()
            assert "nodes" in data
            assert "edges" in data
            assert data["node_count"] == 2
            assert data["edge_count"] == 1
            assert data["module_id"] == "test-module"

            # Verify property mappings for nodes
            nodes = data["nodes"]
            assert len(nodes) == 2

            # Check first node properties
            node1 = next(n for n in nodes if n["id"] == "n1")
            assert node1["name"] == "Machine Learning"
            assert node1["type"] == "Topic"
            assert node1["properties"]["definition"] == "Study of algorithms"
            assert node1["properties"]["confidence"] == 0.95
            assert node1["properties"]["mention_count"] == 10

            # Check second node properties
            node2 = next(n for n in nodes if n["id"] == "n2")
            assert node2["name"] == "Neural Networks"
            assert node2["type"] == "Concept"
            assert node2["properties"]["definition"] == "Computing systems"
            assert node2["properties"]["confidence"] == 0.88
            assert node2["properties"]["mention_count"] == 8

            # Verify property mappings for edges
            edges = data["edges"]
            assert len(edges) == 1
            edge = edges[0]
            assert edge["source"] == "n1"
            assert edge["target"] == "n2"
            assert edge["type"] == "CONTAINS"
            assert edge["properties"]["confidence"] == 0.92

    def test_get_module_graph_with_filters(self, mock_neo4j_session):
        """GET /modules/{module_id} accepts query parameters."""
        # Mock Neo4j query result with single entity
        mock_record = Mock()
        mock_record.__getitem__ = Mock(
            side_effect=lambda key: {
                "entity_data": [
                    {
                        "id": "n1",
                        "name": "Machine Learning",
                        "type": "Topic",
                        "definition": "Study of algorithms",
                        "confidence": 0.95,
                        "mention_count": 10,
                    }
                ],
                "relationships": [],
            }[key]
        )

        mock_result = Mock()
        mock_result.single = Mock(return_value=mock_record)
        mock_neo4j_session.run = Mock(return_value=mock_result)

        with patch("api.routers.graph_preview.neo4j_driver") as mock_driver:
            mock_driver.session = Mock(return_value=mock_neo4j_session)

            response = client.get(
                "/api/v1/graph-preview/modules/test-module",
                params={"entity_types": ["Topic", "Concept"], "limit": 50},
            )

            assert response.status_code == 200
            data = response.json()
            assert "nodes" in data
            assert data["node_count"] >= 0

    def test_get_module_graph_stats_success(self, mock_neo4j_session):
        """GET /modules/{module_id}/stats returns statistics."""
        # Mock Neo4j query results for entity counts
        entity_record_1 = Mock()
        entity_record_1.__getitem__ = Mock(
            side_effect=lambda k: {"entity_type": "Topic", "count": 10}[k]
        )

        entity_record_2 = Mock()
        entity_record_2.__getitem__ = Mock(
            side_effect=lambda k: {"entity_type": "Concept", "count": 30}[k]
        )

        entity_record_3 = Mock()
        entity_record_3.__getitem__ = Mock(
            side_effect=lambda k: {"entity_type": "Finding", "count": 10}[k]
        )

        # Mock Neo4j query results for relationship counts
        rel_record_1 = Mock()
        rel_record_1.__getitem__ = Mock(
            side_effect=lambda k: {"rel_type": "CONTAINS", "count": 40}[k]
        )

        rel_record_2 = Mock()
        rel_record_2.__getitem__ = Mock(
            side_effect=lambda k: {"rel_type": "RELATES_TO", "count": 35}[k]
        )

        # Create separate result mocks for each query
        mock_result_entities = Mock()
        mock_result_entities.__iter__ = Mock(
            return_value=iter([entity_record_1, entity_record_2, entity_record_3])
        )

        mock_result_rels = Mock()
        mock_result_rels.__iter__ = Mock(
            return_value=iter([rel_record_1, rel_record_2])
        )

        # Session.run returns different results for each call
        mock_neo4j_session.run = Mock(
            side_effect=[mock_result_entities, mock_result_rels]
        )

        with patch("api.routers.graph_preview.neo4j_driver") as mock_driver:
            mock_driver.session = Mock(return_value=mock_neo4j_session)

            response = client.get("/api/v1/graph-preview/modules/test-module/stats")

            assert response.status_code == 200
            data = response.json()
            assert "node_count" in data
            assert "edge_count" in data
            assert "entity_types" in data
            assert "relationship_types" in data
            assert data["node_count"] == 50
            assert data["edge_count"] == 75

    def test_get_module_graph_not_found(self, mock_neo4j_session):
        """GET /modules/{module_id} returns 404 for unknown module."""
        # Mock Neo4j query result with no records
        mock_result = Mock()
        mock_result.single = Mock(return_value=None)
        mock_neo4j_session.run = Mock(return_value=mock_result)

        with patch("api.routers.graph_preview.neo4j_driver") as mock_driver:
            mock_driver.session = Mock(return_value=mock_neo4j_session)

            response = client.get("/api/v1/graph-preview/modules/nonexistent")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_get_module_graph_invalid_limit(self, mock_neo4j_session):
        """GET /modules/{module_id} validates limit parameter."""
        # Need to mock Neo4j driver to get past the 503 check first
        with patch("api.routers.graph_preview.neo4j_driver") as mock_driver:
            mock_driver.session = Mock(return_value=mock_neo4j_session)

            response = client.get(
                "/api/v1/graph-preview/modules/test-module",
                params={"limit": 1000},  # Exceeds max of 500
            )

            assert response.status_code == 422  # Validation error

    def test_get_module_graph_invalid_entity_type(self, mock_neo4j_session):
        """GET /modules/{module_id} rejects invalid entity types."""
        with patch("api.routers.graph_preview.neo4j_driver") as mock_driver:
            # Need proper context manager mock for session
            mock_neo4j_session.__enter__ = Mock(return_value=mock_neo4j_session)
            mock_neo4j_session.__exit__ = Mock(return_value=None)
            mock_driver.session = Mock(return_value=mock_neo4j_session)

            response = client.get(
                "/api/v1/graph-preview/modules/test-module",
                params={"entity_types": ["InvalidType"]},
            )

            assert response.status_code == 400
            assert "Invalid entity types" in response.json()["detail"]

    def test_get_module_graph_stats_not_found(self, mock_neo4j_session):
        """GET /modules/{module_id}/stats returns 404 for unknown module."""
        # Mock Neo4j query results with empty iterators (no entities)
        mock_result_entities = Mock()
        mock_result_entities.__iter__ = Mock(return_value=iter([]))

        mock_result_rels = Mock()
        mock_result_rels.__iter__ = Mock(return_value=iter([]))

        mock_neo4j_session.run = Mock(
            side_effect=[mock_result_entities, mock_result_rels]
        )

        with patch("api.routers.graph_preview.neo4j_driver") as mock_driver:
            mock_driver.session = Mock(return_value=mock_neo4j_session)

            response = client.get("/api/v1/graph-preview/modules/nonexistent/stats")

            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()

    def test_get_module_graph_neo4j_unavailable(self):
        """GET /modules/{module_id} returns 503 when Neo4j is unavailable."""
        with patch("api.routers.graph_preview.neo4j_driver", None):
            response = client.get("/api/v1/graph-preview/modules/test-module")

            assert response.status_code == 503
            assert "Neo4j driver not initialized" in response.json()["detail"]

    def test_get_module_graph_edge_filtering(self, mock_neo4j_session):
        """GET /modules/{module_id} filters edges to only include returned nodes."""
        # Mock scenario: 3 nodes (n1, n2, n3) but relationship to n3 exists
        # The query should only return edges where BOTH endpoints are in node set
        mock_record = Mock()
        mock_record.__getitem__ = Mock(
            side_effect=lambda key: {
                "entity_data": [
                    {
                        "id": "n1",
                        "name": "Node 1",
                        "type": "Topic",
                        "definition": "First node",
                        "confidence": 0.9,
                        "mention_count": 5,
                    },
                    {
                        "id": "n2",
                        "name": "Node 2",
                        "type": "Concept",
                        "definition": "Second node",
                        "confidence": 0.85,
                        "mention_count": 3,
                    },
                ],
                "relationships": [
                    # Valid edge: both endpoints in node set
                    {
                        "source": "n1",
                        "target": "n2",
                        "type": "CONTAINS",
                        "confidence": 0.9,
                    },
                    # Invalid edge: n3 not in node set (should be filtered out)
                    {
                        "source": "n1",
                        "target": "n3",
                        "type": "RELATES_TO",
                        "confidence": 0.8,
                    },
                    # Invalid edge: n3 not in node set (should be filtered out)
                    {
                        "source": "n3",
                        "target": "n2",
                        "type": "CONTAINS",
                        "confidence": 0.7,
                    },
                ],
            }[key]
        )

        mock_result = Mock()
        mock_result.single = Mock(return_value=mock_record)
        mock_neo4j_session.run = Mock(return_value=mock_result)

        with patch("api.routers.graph_preview.neo4j_driver") as mock_driver:
            mock_driver.session = Mock(return_value=mock_neo4j_session)

            response = client.get("/api/v1/graph-preview/modules/test-module")

            assert response.status_code == 200
            data = response.json()

            # Should have 2 nodes
            assert data["node_count"] == 2
            assert len(data["nodes"]) == 2

            # Should only have 1 edge (n1->n2), edges to n3 filtered out
            assert data["edge_count"] == 1
            assert len(data["edges"]) == 1

            edge = data["edges"][0]
            assert edge["source"] == "n1"
            assert edge["target"] == "n2"
            assert edge["type"] == "CONTAINS"


class TestGraphPreviewSchemas:
    """Tests for graph preview Pydantic schemas."""

    def test_graph_node_schema(self):
        """GraphNode validates correctly."""
        node = GraphNode(
            id="n1",
            label="Test Node",
            name="Test Node",
            type="Topic",
            properties={"key": "value", "confidence": 0.95},
        )
        assert node.id == "n1"
        assert node.type == "Topic"
        assert node.label == "Test Node"
        assert node.name == "Test Node"
        assert node.properties["key"] == "value"

    def test_graph_node_empty_properties(self):
        """GraphNode accepts empty properties dict."""
        node = GraphNode(
            id="n1", label="Test Node", name="Test Node", type="Topic", properties={}
        )
        assert node.properties == {}

    def test_graph_edge_schema(self):
        """GraphEdge validates correctly."""
        edge = GraphEdge(
            id="e1",
            source="n1",
            target="n2",
            type="RELATES_TO",
            properties={"confidence": 0.88},
        )
        assert edge.source == "n1"
        assert edge.target == "n2"
        assert edge.type == "RELATES_TO"
        assert edge.properties["confidence"] == 0.88

    def test_graph_edge_empty_properties(self):
        """GraphEdge accepts empty properties dict."""
        edge = GraphEdge(
            id="e1", source="n1", target="n2", type="CONTAINS", properties={}
        )
        assert edge.properties == {}

    def test_graph_preview_response_schema(self, mock_graph_data):
        """GraphPreviewResponse validates complete response."""
        response = GraphPreviewResponse(**mock_graph_data)
        assert len(response.nodes) == 2
        assert len(response.edges) == 1
        assert response.node_count == 2
        assert response.edge_count == 1
        assert response.module_id == "test-module"

    def test_graph_preview_response_empty_graph(self):
        """GraphPreviewResponse accepts empty graph."""
        response = GraphPreviewResponse(
            nodes=[], edges=[], node_count=0, edge_count=0, module_id="empty-module"
        )
        assert len(response.nodes) == 0
        assert len(response.edges) == 0
        assert response.node_count == 0

    def test_graph_stats_response_schema(self, mock_stats_data):
        """GraphStatsResponse validates statistics."""
        response = GraphStatsResponse(**mock_stats_data)
        assert response.node_count == 50
        assert response.edge_count == 75
        assert response.entity_types["Topic"] == 10
        assert response.entity_types["Concept"] == 30
        assert response.relationship_types["CONTAINS"] == 40

    def test_graph_stats_response_zero_counts(self):
        """GraphStatsResponse accepts zero counts."""
        response = GraphStatsResponse(
            node_count=0,
            edge_count=0,
            entity_types={},
            relationship_types={},
        )
        assert response.node_count == 0
        assert response.edge_count == 0
        assert len(response.entity_types) == 0
