#!/usr/bin/env python3
"""
============================================================================
MIGRATION: 001 - Add Module Schema
VERSION: 001
CREATED: 2026-01-19
============================================================================

PURPOSE:
    Add Module, StudySession, and Message node types to Neo4j database
    with appropriate constraints and HNSW vector indices for Phase 1 of
    AURA M2KG implementation.

CHANGES:
    1. Module Node:
       - Unique constraint on Module.id
       - Index on Module.user_id for ownership queries
       - Properties: id, code, name, description, subject_id, semester,
                     department, kg_status, kg_processed_at, created_by,
                     published_at, created_at, updated_at
    
    2. StudySession Node:
       - Unique constraint on StudySession.id
       - Index on StudySession.user_id
       - Properties: id, title, module_ids, user_id, status, message_count,
                     settings, created_at, updated_at, is_active
    
    3. Message Node:
       - Unique constraint on Message.id
       - Index on Message.session_id for fast session queries
       - Properties: id, session_id, role, content, created_at, model_used,
                     sources, thinking_content, token_count
    
    4. Chunk Vector Index (HNSW):
       - 768 dimensions (Gemini text-embedding-004)
       - Cosine similarity function
       - Optimized for semantic search

IDEMPOTENCY:
    All operations use IF NOT EXISTS to ensure safe re-execution

REFERENCE:
    - Source: .planning/ROADMAP.md Phase 1
    - Pattern: AURA-CHAT/backend/graph_manager.py
============================================================================
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from migrations import Migration, run_migration
from neo4j_config import neo4j_driver
from logging_config import logger


class AddModuleSchema(Migration):
    """Migration to add Module, StudySession, Message nodes with constraints."""
    
    version = "001"
    description = "Add Module, StudySession, Message nodes with constraints and vector indices"
    
    def upgrade(self, driver) -> bool:
        """
        Apply migration: Create node constraints and indices.
        
        Args:
            driver: Neo4j driver instance
            
        Returns:
            bool: True if successful
        """
        try:
            # ========================================
            # STEP 1: MODULE NODE CONSTRAINTS
            # ========================================
            logger.info("Creating Module node constraints...")
            
            # Unique constraint on Module.id
            module_id_constraint = """
            CREATE CONSTRAINT module_id_unique IF NOT EXISTS
            FOR (m:Module) REQUIRE m.id IS UNIQUE
            """
            self.execute_cypher_query(driver, module_id_constraint)
            logger.info("✓ Created constraint: module_id_unique")
            
            # Index on Module.user_id for fast ownership queries
            module_user_index = """
            CREATE INDEX module_user_idx IF NOT EXISTS
            FOR (m:Module) ON (m.user_id)
            """
            self.execute_cypher_query(driver, module_user_index)
            logger.info("✓ Created index: module_user_idx")
            
            # Index on Module.code for fast code lookups
            module_code_index = """
            CREATE INDEX module_code_idx IF NOT EXISTS
            FOR (m:Module) ON (m.code)
            """
            self.execute_cypher_query(driver, module_code_index)
            logger.info("✓ Created index: module_code_idx")
            
            # Index on Module.kg_status for filtering by processing status
            module_status_index = """
            CREATE INDEX module_status_idx IF NOT EXISTS
            FOR (m:Module) ON (m.kg_status)
            """
            self.execute_cypher_query(driver, module_status_index)
            logger.info("✓ Created index: module_status_idx")
            
            # ========================================
            # STEP 2: STUDYSESSION NODE CONSTRAINTS
            # ========================================
            logger.info("Creating StudySession node constraints...")
            
            # Unique constraint on StudySession.id
            session_id_constraint = """
            CREATE CONSTRAINT studysession_id_unique IF NOT EXISTS
            FOR (s:StudySession) REQUIRE s.id IS UNIQUE
            """
            self.execute_cypher_query(driver, session_id_constraint)
            logger.info("✓ Created constraint: studysession_id_unique")
            
            # Index on StudySession.user_id for user's sessions
            session_user_index = """
            CREATE INDEX studysession_user_idx IF NOT EXISTS
            FOR (s:StudySession) ON (s.user_id)
            """
            self.execute_cypher_query(driver, session_user_index)
            logger.info("✓ Created index: studysession_user_idx")
            
            # Index on StudySession.status for filtering active sessions
            session_status_index = """
            CREATE INDEX studysession_status_idx IF NOT EXISTS
            FOR (s:StudySession) ON (s.status)
            """
            self.execute_cypher_query(driver, session_status_index)
            logger.info("✓ Created index: studysession_status_idx")
            
            # ========================================
            # STEP 3: MESSAGE NODE CONSTRAINTS
            # ========================================
            logger.info("Creating Message node constraints...")
            
            # Unique constraint on Message.id
            message_id_constraint = """
            CREATE CONSTRAINT message_id_unique IF NOT EXISTS
            FOR (m:Message) REQUIRE m.id IS UNIQUE
            """
            self.execute_cypher_query(driver, message_id_constraint)
            logger.info("✓ Created constraint: message_id_unique")
            
            # Index on Message.session_id for fast session message queries
            message_session_index = """
            CREATE INDEX message_session_idx IF NOT EXISTS
            FOR (m:Message) ON (m.session_id)
            """
            self.execute_cypher_query(driver, message_session_index)
            logger.info("✓ Created index: message_session_idx")
            
            # Index on Message.created_at for chronological ordering
            message_created_index = """
            CREATE INDEX message_created_idx IF NOT EXISTS
            FOR (m:Message) ON (m.created_at)
            """
            self.execute_cypher_query(driver, message_created_index)
            logger.info("✓ Created index: message_created_idx")
            
            # ========================================
            # STEP 4: DOCUMENT NODE EXTENSION
            # ========================================
            logger.info("Creating Document node indices for module support...")
            
            # Index on Document.module_id for module-scoped queries
            # Documents will be assigned to modules via module_id property
            document_module_index = """
            CREATE INDEX document_module_idx IF NOT EXISTS
            FOR (d:Document) ON (d.module_id)
            """
            self.execute_cypher_query(driver, document_module_index)
            logger.info("✓ Created index: document_module_idx")
            
            # ========================================
            # STEP 5: CHUNK NODE EXTENSION
            # ========================================
            logger.info("Creating Chunk node indices for module support...")
            
            # Index on Chunk.module_id for module-filtered search
            chunk_module_index = """
            CREATE INDEX chunk_module_idx IF NOT EXISTS
            FOR (c:Chunk) ON (c.module_id)
            """
            self.execute_cypher_query(driver, chunk_module_index)
            logger.info("✓ Created index: chunk_module_idx")
            
            # ========================================
            # STEP 6: VECTOR INDEX FOR SEMANTIC SEARCH
            # ========================================
            logger.info("Creating HNSW vector index for Chunk embeddings...")
            
            # HNSW vector index for Chunk nodes
            # 768 dimensions for Gemini text-embedding-004
            # Cosine similarity for semantic search
            chunk_vector_index = """
            CREATE VECTOR INDEX chunk_vector_index IF NOT EXISTS
            FOR (c:Chunk) ON (c.embedding)
            OPTIONS {indexConfig: {
              `vector.dimensions`: 768,
              `vector.similarity_function`: 'cosine',
              `vector.hnsw.m`: 16,
              `vector.hnsw.ef_construction`: 200
            }}
            """
            self.execute_cypher_query(driver, chunk_vector_index)
            logger.info("✓ Created vector index: chunk_vector_index")
            
            logger.info("All constraints and indices created successfully!")
            return True
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise
    
    def downgrade(self, driver) -> bool:
        """
        Rollback migration (not implemented - forward-only).
        
        To manually rollback, run these Cypher commands:
        
        DROP CONSTRAINT module_id_unique IF EXISTS
        DROP INDEX module_user_idx IF EXISTS
        DROP CONSTRAINT studysession_id_unique IF EXISTS
        DROP INDEX studysession_user_idx IF EXISTS
        DROP CONSTRAINT message_id_unique IF EXISTS
        DROP INDEX message_session_idx IF EXISTS
        DROP INDEX chunk_vector_index IF EXISTS
        """
        raise NotImplementedError(
            "This migration is forward-only. "
            "See docstring for manual rollback commands."
        )


def main():
    """
    Execute the migration script.
    Can be run directly: python 001_add_module_schema.py
    """
    if neo4j_driver is None:
        logger.error("Neo4j driver not initialized. Check your .env configuration.")
        logger.error("Required env vars: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")
        return False
    
    migration = AddModuleSchema()
    success = run_migration(migration, neo4j_driver)
    
    if success:
        print("\n" + "=" * 70)
        print("✓ Migration 001 completed successfully!")
        print("=" * 70)
        print("\nNext steps:")
        print("1. Verify constraints: Run in Neo4j Browser: SHOW CONSTRAINTS")
        print("2. Verify indices: Run in Neo4j Browser: SHOW INDEXES")
        print("3. Verify vector index: Run in Neo4j Browser: SHOW VECTOR INDEXES")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("✗ Migration 001 FAILED")
        print("=" * 70)
        print("Check the logs above for error details.")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
