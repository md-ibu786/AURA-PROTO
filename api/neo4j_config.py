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
from typing import Optional
from neo4j import GraphDatabase, Driver
from dotenv import load_dotenv

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
            "NEO4J_PASSWORD environment variable is required. "
            "Set it in your .env file."
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
            max_connection_pool_size=50  # Pool size
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


# Initialize driver on module import
try:
    neo4j_driver = init_neo4j()
except Exception as e:
    print(f"Warning: Neo4j driver initialization failed: {e}")
    print("Please ensure Neo4j is running and credentials are set in .env")
    neo4j_driver = None
