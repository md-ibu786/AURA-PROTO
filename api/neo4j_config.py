"""
============================================================================
FILE: neo4j_config.py
LOCATION: api/neo4j_config.py
============================================================================

PURPOSE:
    Handles Neo4j driver initialization and provides graph database client
    instances for the entire backend application.

ROLE IN PROJECT:
    This is the Neo4j database configuration layer. All modules that need to
    interact with Neo4j import `neo4j_driver` from this file.
    It ensures the driver is initialized only once (singleton pattern) and
    handles credential resolution from environment variables.

KEY COMPONENTS:
    - init_neo4j(): Initializes Neo4j driver with connection pooling
    - test_connection(): Verifies connectivity to Neo4j instance
    - neo4j_driver: Global Neo4j driver instance
    - close_neo4j(): Cleanup function to close driver

DEPENDENCIES:
    - External: neo4j (official Python driver)
    - Internal: Reads .env for NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

USAGE:
    from api.neo4j_config import neo4j_driver

    # Execute Cypher query
    with neo4j_driver.session() as session:
        result = session.run("MATCH (n) RETURN count(n)")
        print(result.single()[0])

ENVIRONMENT VARIABLES:
    - NEO4J_URI: Connection URI (e.g., bolt://localhost:7687 or neo4j+s://xxx.databases.neo4j.io)
    - NEO4J_USER: Username (default: neo4j)
    - NEO4J_PASSWORD: Password for authentication
============================================================================
"""

import os
from typing import Optional, Dict, List, Any
from neo4j import GraphDatabase, Driver
from dotenv import load_dotenv


# ============================================================================
# KG ENHANCEMENT CONSTANTS
# ============================================================================

# Entity relationship types for knowledge graph edges
# Used for entity-entity relationships in KG Pipeline Enhancement (Phase 09)
# @see: .planning/KG-ENHANCEMENT-ROADMAP.md - Phase 09 requirements
ENTITY_RELATIONSHIP_TYPES: List[str] = [
    "DEFINES",  # Entity A defines Entity B
    "DEPENDS_ON",  # Entity A depends on Entity B
    "USES",  # Entity A uses Entity B
    "SUPPORTS",  # Entity A supports/validates Entity B
    "CONTRADICTS",  # Entity A contradicts Entity B
    "EXTENDS",  # Entity A extends/builds upon Entity B
    "IMPLEMENTS",  # Entity A implements Entity B
    "REFERENCES",  # Entity A references Entity B
    "RELATED_TO",  # General relationship between entities
]

# Required vector indices for KG enhancement schema
# These must exist for verify_kg_enhancement_schema() to return True
KG_ENHANCEMENT_VECTOR_INDICES: List[str] = [
    "parent_chunk_vector_index",
    "topic_vector_index",
    "concept_vector_index",
    "methodology_vector_index",
    "finding_vector_index",
]

# Required fulltext indices for hybrid search
KG_ENHANCEMENT_FULLTEXT_INDICES: List[str] = [
    "chunk_fulltext_index",
]

# Required constraints for KG enhancement
KG_ENHANCEMENT_CONSTRAINTS: List[str] = [
    "parent_chunk_id_unique",
]

# Load environment variables from .env file
load_dotenv()

# Global driver instance
_neo4j_driver: Optional[Driver] = None


def init_neo4j() -> Driver:
    """
    Initializes Neo4j driver and returns it.
    Uses singleton pattern to prevent multiple driver instances.

    Returns:
        Driver: Configured Neo4j driver instance with connection pooling

    Raises:
        ValueError: If required environment variables are missing
        Exception: If connection to Neo4j fails
    """
    global _neo4j_driver

    # Return existing driver if already initialized
    if _neo4j_driver is not None:
        return _neo4j_driver

    # Get credentials from environment
    neo4j_uri = os.getenv("NEO4J_URI")
    neo4j_user = os.getenv("NEO4J_USER", "neo4j")
    neo4j_password = os.getenv("NEO4J_PASSWORD")

    # Validate required credentials
    if not neo4j_uri:
        raise ValueError(
            "NEO4J_URI environment variable is required. "
            "Example: NEO4J_URI=bolt://localhost:7687"
        )

    if not neo4j_password:
        raise ValueError(
            "NEO4J_PASSWORD environment variable is required. Set it in your .env file."
        )

    try:
        # Initialize driver with connection pooling and timeouts
        # Based on AURA-CHAT/backend/graph_manager.py patterns
        _neo4j_driver = GraphDatabase.driver(
            neo4j_uri,
            auth=(neo4j_user, neo4j_password),
            # Connection pool settings to prevent stale connections
            keep_alive=True,  # Send TCP keep-alive packets
            connection_timeout=30,  # 30s connection timeout
            max_connection_lifetime=300,  # 5 min max connection age
            max_connection_pool_size=50,  # Pool size
        )

        # Verify connectivity
        _neo4j_driver.verify_connectivity()
        print(f"✓ Successfully connected to Neo4j at {neo4j_uri}")

        return _neo4j_driver

    except Exception as e:
        print(f"✗ Failed to connect to Neo4j: {e}")
        raise


def test_connection() -> bool:
    """
    Test Neo4j connection health.

    Returns:
        bool: True if connection is healthy, False otherwise
    """
    try:
        driver = init_neo4j()
        driver.verify_connectivity()

        # Run a simple query to verify database access
        with driver.session() as session:
            result = session.run("RETURN 1 as test")
            test_value = result.single()["test"]

            if test_value == 1:
                print("✓ Neo4j connection test passed")
                return True

        return False

    except Exception as e:
        print(f"✗ Neo4j connection test failed: {e}")
        return False


def close_neo4j():
    """
    Close the Neo4j driver and clean up connections.
    Should be called during application shutdown.
    """
    global _neo4j_driver

    if _neo4j_driver is not None:
        _neo4j_driver.close()
        print("✓ Neo4j driver closed")
        _neo4j_driver = None


def get_schema_status(driver: Driver = None) -> Dict[str, Any]:
    """
    Get the current status of all KG enhancement schema elements.

    Returns a dictionary with the status of all required indices and constraints
    for the KG Pipeline Enhancement feature.

    Args:
        driver: Optional Neo4j driver. If None, uses the global neo4j_driver.

    Returns:
        Dict with structure:
        {
            "vector_indices": {"index_name": {"exists": bool, "state": str}, ...},
            "fulltext_indices": {"index_name": {"exists": bool, "state": str}, ...},
            "constraints": {"constraint_name": {"exists": bool}, ...},
            "all_present": bool,
            "all_online": bool
        }

    @see: KG_ENHANCEMENT_VECTOR_INDICES, KG_ENHANCEMENT_FULLTEXT_INDICES
    @note: state will be "ONLINE", "POPULATING", or "FAILED" for indices
    """
    target_driver = driver or _neo4j_driver

    if target_driver is None:
        return {
            "vector_indices": {},
            "fulltext_indices": {},
            "constraints": {},
            "all_present": False,
            "all_online": False,
            "error": "Neo4j driver not initialized",
        }

    result = {
        "vector_indices": {},
        "fulltext_indices": {},
        "constraints": {},
        "all_present": True,
        "all_online": True,
    }

    try:
        with target_driver.session() as session:
            # Get all indices
            index_result = session.run("SHOW INDEXES")
            indices = {record["name"]: record for record in index_result}

            # Check vector indices
            for index_name in KG_ENHANCEMENT_VECTOR_INDICES:
                if index_name in indices:
                    state = indices[index_name].get("state", "UNKNOWN")
                    result["vector_indices"][index_name] = {
                        "exists": True,
                        "state": state,
                    }
                    if state != "ONLINE":
                        result["all_online"] = False
                else:
                    result["vector_indices"][index_name] = {
                        "exists": False,
                        "state": None,
                    }
                    result["all_present"] = False
                    result["all_online"] = False

            # Check fulltext indices
            for index_name in KG_ENHANCEMENT_FULLTEXT_INDICES:
                if index_name in indices:
                    state = indices[index_name].get("state", "UNKNOWN")
                    result["fulltext_indices"][index_name] = {
                        "exists": True,
                        "state": state,
                    }
                    if state != "ONLINE":
                        result["all_online"] = False
                else:
                    result["fulltext_indices"][index_name] = {
                        "exists": False,
                        "state": None,
                    }
                    result["all_present"] = False
                    result["all_online"] = False

            # Get all constraints
            constraint_result = session.run("SHOW CONSTRAINTS")
            constraints = {record["name"]: record for record in constraint_result}

            # Check required constraints
            for constraint_name in KG_ENHANCEMENT_CONSTRAINTS:
                if constraint_name in constraints:
                    result["constraints"][constraint_name] = {"exists": True}
                else:
                    result["constraints"][constraint_name] = {"exists": False}
                    result["all_present"] = False

        return result

    except Exception as e:
        return {
            "vector_indices": {},
            "fulltext_indices": {},
            "constraints": {},
            "all_present": False,
            "all_online": False,
            "error": str(e),
        }


def verify_kg_enhancement_schema(driver: Driver = None) -> bool:
    """
    Verify that all KG enhancement schema elements are present and online.

    Checks for:
    - 5 vector indices (parent_chunk, topic, concept, methodology, finding)
    - 1 fulltext index (chunk_fulltext_index)
    - ParentChunk constraint (parent_chunk_id_unique)

    Args:
        driver: Optional Neo4j driver. If None, uses the global neo4j_driver.

    Returns:
        bool: True if all schema elements exist and indices are ONLINE

    Example:
        >>> from neo4j_config import verify_kg_enhancement_schema
        >>> if verify_kg_enhancement_schema():
        ...     print("KG enhancement schema is ready")
        ... else:
        ...     print("Run migration 002_kg_enhancement_schema.py first")

    @see: get_schema_status() for detailed status information
    @note: Returns False if any index is still POPULATING
    """
    status = get_schema_status(driver)

    if "error" in status:
        print(f"✗ Schema verification failed: {status['error']}")
        return False

    if status["all_present"] and status["all_online"]:
        print(
            "✓ KG enhancement schema verified - all indices and constraints present and ONLINE"
        )
        return True

    # Provide detailed feedback on what's missing or not ready
    if not status["all_present"]:
        missing = []
        for name, info in status["vector_indices"].items():
            if not info["exists"]:
                missing.append(f"vector index: {name}")
        for name, info in status["fulltext_indices"].items():
            if not info["exists"]:
                missing.append(f"fulltext index: {name}")
        for name, info in status["constraints"].items():
            if not info["exists"]:
                missing.append(f"constraint: {name}")
        print(f"✗ Missing schema elements: {', '.join(missing)}")

    if not status["all_online"]:
        not_online = []
        for name, info in {
            **status["vector_indices"],
            **status["fulltext_indices"],
        }.items():
            if info["exists"] and info["state"] != "ONLINE":
                not_online.append(f"{name} ({info['state']})")
        if not_online:
            print(f"⏳ Indices not yet online: {', '.join(not_online)}")

    return False


def test_entity_vector_search(
    entity_type: str,
    query_embedding: List[float],
    top_k: int = 5,
    driver: Driver = None,
) -> List[Dict[str, Any]]:
    """
    Test entity vector search using Neo4j vector indices.

    Performs a vector similarity search on entity nodes to verify that
    vector indices are working correctly for entity retrieval.

    Args:
        entity_type: Entity type to search (Topic, Concept, Methodology, Finding)
        query_embedding: 768-dimensional query embedding vector
        top_k: Number of results to return (default: 5)
        driver: Optional Neo4j driver. If None, uses the global neo4j_driver.

    Returns:
        List of dicts with entity name, definition, and similarity score:
        [
            {"name": "Entity Name", "definition": "...", "score": 0.95},
            ...
        ]

    Example:
        >>> from neo4j_config import test_entity_vector_search
        >>> from services.embeddings import EmbeddingService
        >>> embedding_service = EmbeddingService()
        >>> query_vec = embedding_service.embed_text("machine learning algorithms")
        >>> results = test_entity_vector_search("Concept", query_vec)
        >>> for r in results:
        ...     print(f"{r['name']}: {r['score']:.3f}")

    @see: KG_ENHANCEMENT_VECTOR_INDICES for available indices
    @note: Requires vector indices to be ONLINE
    """
    target_driver = driver or _neo4j_driver

    if target_driver is None:
        print("✗ Neo4j driver not initialized")
        return []

    # Map entity types to index names
    index_map = {
        "Topic": "topic_vector_index",
        "Concept": "concept_vector_index",
        "Methodology": "methodology_vector_index",
        "Finding": "finding_vector_index",
    }

    if entity_type not in index_map:
        print(f"✗ Unknown entity type: {entity_type}")
        print(f"  Valid types: {', '.join(index_map.keys())}")
        return []

    index_name = index_map[entity_type]

    # Validate embedding dimensions
    if not query_embedding or len(query_embedding) != 768:
        print(f"✗ Invalid embedding: expected 768 dimensions, got {len(query_embedding) if query_embedding else 0}")
        return []

    try:
        with target_driver.session() as session:
            # Use vector similarity search
            query = """
            CALL db.index.vector.queryNodes($index_name, $top_k, $query_embedding)
            YIELD node, score
            RETURN node.name AS name, node.definition AS definition, score
            ORDER BY score DESC
            """

            result = session.run(
                query,
                {
                    "index_name": index_name,
                    "top_k": top_k,
                    "query_embedding": query_embedding,
                },
            )

            results = []
            for record in result:
                results.append({
                    "name": record["name"],
                    "definition": record["definition"],
                    "score": record["score"],
                })

            if results:
                print(f"✓ Vector search returned {len(results)} results for {entity_type}")
            else:
                print(f"⚠ No results found for {entity_type} (index may be empty)")

            return results

    except Exception as e:
        error_str = str(e)
        if "no such index" in error_str.lower():
            print(f"✗ Vector index '{index_name}' not found")
            print("  Run migration 002_kg_enhancement_schema.py to create indices")
        else:
            print(f"✗ Vector search failed: {e}")
        return []


# Initialize driver on module import
if os.getenv("AURA_TEST_MODE", "").lower() == "true":
    neo4j_driver = None
else:
    try:
        neo4j_driver = init_neo4j()
    except Exception as e:
        print(f"Warning: Neo4j driver initialization failed: {e}")
        print("Please ensure Neo4j is running and credentials are set in .env")
        neo4j_driver = None
