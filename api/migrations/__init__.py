"""
============================================================================
FILE: __init__.py
LOCATION: api/migrations/__init__.py
============================================================================

PURPOSE:
    Provides base Migration class and utilities for database schema migrations.
    All migration scripts inherit from Migration and implement upgrade/downgrade.

ROLE IN PROJECT:
    This is the migration infrastructure layer for Neo4j schema changes.
    Ensures migrations are versioned, logged, and executed safely.

KEY COMPONENTS:
    - Migration: Abstract base class for all migrations
    - execute_cypher_query: Helper to run Cypher with error handling
============================================================================
"""

import os
from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional
from neo4j import Driver, Session

# Import logging from api
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from logging_config import logger


class Migration(ABC):
    """
    Abstract base class for database migrations.
    
    All migration scripts should inherit from this class and implement:
    - version: Unique migration version identifier
    - description: Human-readable description
    - upgrade(): Method to apply the migration
    - downgrade(): Optional method to rollback (can raise NotImplementedError)
    
    Example:
        class AddModuleSchema(Migration):
            version = "001"
            description = "Add Module, StudySession, Message nodes"
            
            def upgrade(self, driver: Driver):
                self.execute_cypher_query(driver, \"CREATE CONSTRAINT...\")
    """
    
    version: str = "000"
    description: str = "Base Migration"
    timestamp: datetime = datetime.now()
    
    def __init__(self):
        self.timestamp = datetime.now()
    
    @abstractmethod
    def upgrade(self, driver: Driver) -> bool:
        """
        Apply the migration changes to the database.
        
        Args:
            driver: Neo4j driver instance
            
        Returns:
            bool: True if successful, False otherwise
        """
        pass
    
    def downgrade(self, driver: Driver) -> bool:
        """
        Rollback the migration changes (optional).
        Default implementation does nothing (forward-only migrations).
        
        Args:
            driver: Neo4j driver instance
            
        Returns:
            bool: True if successful, False otherwise
        """
        logger.warning(f"Downgrade not implemented for migration {self.version}")
        raise NotImplementedError(
            f"Migration {self.version} does not support rollback. "
            "This is a forward-only migration."
        )
    
    def execute_cypher_query(
        self, 
        driver: Driver, 
        query: str, 
        parameters: Dict[str, Any] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute a Cypher query with error handling and logging.
        
        Args:
            driver: Neo4j driver instance
            query: Cypher query string
            parameters: Optional query parameters
            
        Returns:
            List of result records as dictionaries
            
        Raises:
            Exception: If query execution fails
        """
        params = parameters or {}
        
        try:
            with driver.session() as session:
                logger.debug(f"Executing Cypher: {query[:100]}...")
                result = session.run(query, params)
                records = [record.data() for record in result]
                logger.debug(f"Query executed successfully, {len(records)} records returned")
                return records
                
        except Exception as e:
            logger.error(f"Cypher query failed: {e}")
            logger.error(f"Query: {query}")
            logger.error(f"Parameters: {params}")
            raise
    
    def log_migration_start(self):
        """Log migration start."""
        logger.info("=" * 70)
        logger.info(f"Starting Migration {self.version}: {self.description}")
        logger.info(f"Timestamp: {self.timestamp.isoformat()}")
        logger.info("=" * 70)
    
    def log_migration_success(self):
        """Log migration success."""
        logger.info("=" * 70)
        logger.info(f"Migration {self.version} completed successfully")
        logger.info("=" * 70)
    
    def log_migration_failure(self, error: Exception):
        """Log migration failure."""
        logger.error("=" * 70)
        logger.error(f"Migration {self.version} FAILED")
        logger.error(f"Error: {error}")
        logger.error("=" * 70)


def run_migration(migration: Migration, driver: Driver) -> bool:
    """
    Execute a migration with proper logging and error handling.
    
    Args:
        migration: Migration instance to execute
        driver: Neo4j driver instance
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        migration.log_migration_start()
        success = migration.upgrade(driver)
        
        if success:
            migration.log_migration_success()
        else:
            logger.error(f"Migration {migration.version} returned False")
        
        return success
        
    except Exception as e:
        migration.log_migration_failure(e)
        return False
