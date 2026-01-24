#!/usr/bin/env python3
"""
============================================================================
MIGRATION: 002 - KG Enhancement Schema
VERSION: 002
CREATED: 2026-01-24
============================================================================

PURPOSE:
    Add ParentChunk nodes, entity vector indices, and fulltext index to support
    hierarchical chunking and entity embeddings for KG Pipeline Enhancement.

CHANGES:
    1. ParentChunk Node:
       - Unique constraint on ParentChunk.id
       - Properties: id, document_id, module_id, text, tokens, position,
                     embedding, created_at
       - HNSW vector index for semantic search

    2. Entity Vector Indices (NEW):
       - topic_vector_index: Topic.embedding
       - concept_vector_index: Concept.embedding
       - methodology_vector_index: Methodology.embedding
       - finding_vector_index: Finding.embedding
       All with 768 dimensions, cosine similarity, HNSW tuning

    3. Fulltext Index:
       - chunk_fulltext_index: Chunk.text for hybrid search
       - Uses English analyzer for keyword/phrase matching

RELATIONSHIPS (for reference - created by kg_processor):
    - (:Document)-[:HAS_PARENT_CHUNK]->(:ParentChunk)
    - (:ParentChunk)-[:HAS_CHILD]->(:Chunk)
    - Entity-entity: DEFINES, DEPENDS_ON, USES, SUPPORTS, CONTRADICTS,
                     EXTENDS, IMPLEMENTS, REFERENCES, RELATED_TO

IDEMPOTENCY:
    All operations use IF NOT EXISTS to ensure safe re-execution

REFERENCE:
    - Source: .planning/phases/09-kg-foundation/09-01-PLAN.md
    - Pattern: AURA-CHAT/backend/graph_manager.py (lines 167-248)
    - Configuration: 768 dimensions, cosine similarity, HNSW m=16, ef=200

@see: 001_add_module_schema.py - Previous migration pattern
@see: neo4j_config.py - verify_kg_enhancement_schema() for verification
@note: Requires Neo4j 5.15+ for vector index syntax
============================================================================
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from migrations import Migration, run_migration
from neo4j_config import neo4j_driver
from logging_config import logger


# Configuration constants (match AURA-CHAT)
EMBEDDING_DIMENSIONS = 768
HNSW_M = 16
HNSW_EF_CONSTRUCTION = 200


class KGEnhancementSchema(Migration):
    """Migration to add KG enhancement schema for hierarchical chunking and entity embeddings."""

    version = "002"
    description = "Add ParentChunk nodes, entity vector indices, and fulltext index for KG enhancement"

    def upgrade(self, driver) -> bool:
        """
        Apply migration: Create ParentChunk constraints, entity vector indices, and fulltext index.

        Args:
            driver: Neo4j driver instance

        Returns:
            bool: True if successful
        """
        try:
            # ========================================
            # STEP 1: PARENTCHUNK NODE CONSTRAINTS
            # ========================================
            logger.info("Creating ParentChunk node constraints...")

            # Unique constraint on ParentChunk.id
            parent_chunk_id_constraint = """
            CREATE CONSTRAINT parent_chunk_id_unique IF NOT EXISTS
            FOR (p:ParentChunk) REQUIRE p.id IS UNIQUE
            """
            self.execute_cypher_query(driver, parent_chunk_id_constraint)
            logger.info("✓ Created constraint: parent_chunk_id_unique")

            # Index on ParentChunk.document_id for document-scoped queries
            parent_chunk_doc_index = """
            CREATE INDEX parent_chunk_document_idx IF NOT EXISTS
            FOR (p:ParentChunk) ON (p.document_id)
            """
            self.execute_cypher_query(driver, parent_chunk_doc_index)
            logger.info("✓ Created index: parent_chunk_document_idx")

            # Index on ParentChunk.module_id for module-filtered queries
            parent_chunk_module_index = """
            CREATE INDEX parent_chunk_module_idx IF NOT EXISTS
            FOR (p:ParentChunk) ON (p.module_id)
            """
            self.execute_cypher_query(driver, parent_chunk_module_index)
            logger.info("✓ Created index: parent_chunk_module_idx")

            # ========================================
            # STEP 2: PARENTCHUNK VECTOR INDEX
            # ========================================
            logger.info("Creating ParentChunk vector index...")

            parent_chunk_vector_index = f"""
            CREATE VECTOR INDEX parent_chunk_vector_index IF NOT EXISTS
            FOR (p:ParentChunk) ON (p.embedding)
            OPTIONS {{indexConfig: {{
              `vector.dimensions`: {EMBEDDING_DIMENSIONS},
              `vector.similarity_function`: 'cosine',
              `vector.hnsw.m`: {HNSW_M},
              `vector.hnsw.ef_construction`: {HNSW_EF_CONSTRUCTION}
            }}}}
            """
            self.execute_cypher_query(driver, parent_chunk_vector_index)
            logger.info("✓ Created vector index: parent_chunk_vector_index")

            # ========================================
            # STEP 3: ENTITY VECTOR INDICES
            # ========================================
            logger.info("Creating entity vector indices...")

            entity_types = ["Topic", "Concept", "Methodology", "Finding"]

            for entity_type in entity_types:
                index_name = f"{entity_type.lower()}_vector_index"
                entity_vector_index = f"""
                CREATE VECTOR INDEX {index_name} IF NOT EXISTS
                FOR (e:{entity_type}) ON (e.embedding)
                OPTIONS {{indexConfig: {{
                  `vector.dimensions`: {EMBEDDING_DIMENSIONS},
                  `vector.similarity_function`: 'cosine',
                  `vector.hnsw.m`: {HNSW_M},
                  `vector.hnsw.ef_construction`: {HNSW_EF_CONSTRUCTION}
                }}}}
                """
                self.execute_cypher_query(driver, entity_vector_index)
                logger.info(f"✓ Created vector index: {index_name}")

            # ========================================
            # STEP 4: FULLTEXT INDEX FOR HYBRID SEARCH
            # ========================================
            logger.info("Creating fulltext index for hybrid search...")

            # Fulltext index on Chunk.text for lexical search
            # Uses English analyzer for stemming and stopword removal
            chunk_fulltext_index = """
            CREATE FULLTEXT INDEX chunk_fulltext_index IF NOT EXISTS
            FOR (c:Chunk) ON EACH [c.text]
            OPTIONS {indexConfig: {`fulltext.analyzer`: 'english'}}
            """
            self.execute_cypher_query(driver, chunk_fulltext_index)
            logger.info("✓ Created fulltext index: chunk_fulltext_index")

            # ========================================
            # STEP 5: ENTITY UNIQUE CONSTRAINTS
            # ========================================
            logger.info("Creating entity unique constraints...")

            # Ensure entity types have unique id constraints
            # (Some may exist from previous migrations, IF NOT EXISTS handles this)
            for entity_type in entity_types:
                constraint_name = f"{entity_type.lower()}_id_unique"
                entity_constraint = f"""
                CREATE CONSTRAINT {constraint_name} IF NOT EXISTS
                FOR (e:{entity_type}) REQUIRE e.id IS UNIQUE
                """
                self.execute_cypher_query(driver, entity_constraint)
                logger.info(f"✓ Created/verified constraint: {constraint_name}")

            logger.info("All KG enhancement schema changes applied successfully!")
            return True

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            raise

    def downgrade(self, driver) -> bool:
        """
        Rollback migration (not implemented - forward-only).

        To manually rollback, run these Cypher commands in Neo4j Browser:

        -- Drop ParentChunk constraints and indices
        DROP CONSTRAINT parent_chunk_id_unique IF EXISTS
        DROP INDEX parent_chunk_document_idx IF EXISTS
        DROP INDEX parent_chunk_module_idx IF EXISTS
        DROP INDEX parent_chunk_vector_index IF EXISTS

        -- Drop entity vector indices
        DROP INDEX topic_vector_index IF EXISTS
        DROP INDEX concept_vector_index IF EXISTS
        DROP INDEX methodology_vector_index IF EXISTS
        DROP INDEX finding_vector_index IF EXISTS

        -- Drop fulltext index
        DROP INDEX chunk_fulltext_index IF EXISTS

        -- Drop entity constraints (if created by this migration)
        DROP CONSTRAINT topic_id_unique IF EXISTS
        DROP CONSTRAINT concept_id_unique IF EXISTS
        DROP CONSTRAINT methodology_id_unique IF EXISTS
        DROP CONSTRAINT finding_id_unique IF EXISTS
        """
        raise NotImplementedError(
            "This migration is forward-only. "
            "See docstring for manual rollback commands."
        )


def main():
    """
    Execute the migration script.
    Can be run directly: python 002_kg_enhancement_schema.py
    """
    if neo4j_driver is None:
        logger.error("Neo4j driver not initialized. Check your .env configuration.")
        logger.error("Required env vars: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")
        return False

    migration = KGEnhancementSchema()
    success = run_migration(migration, neo4j_driver)

    if success:
        print("\n" + "=" * 70)
        print("✓ Migration 002 (KG Enhancement Schema) completed successfully!")
        print("=" * 70)
        print("\nCreated:")
        print("  • ParentChunk node constraint + indices")
        print(
            "  • 5 vector indices (parent_chunk, topic, concept, methodology, finding)"
        )
        print("  • 1 fulltext index (chunk_fulltext_index)")
        print("  • 4 entity unique constraints")
        print("\nNext steps:")
        print("1. Verify constraints: Run in Neo4j Browser: SHOW CONSTRAINTS")
        print("2. Verify indices: Run in Neo4j Browser: SHOW INDEXES")
        print("3. Verify vector indices: Run in Neo4j Browser: SHOW VECTOR INDEXES")
        print("4. Run verify_kg_enhancement_schema() from neo4j_config.py")
        print("=" * 70)
    else:
        print("\n" + "=" * 70)
        print("✗ Migration 002 FAILED")
        print("=" * 70)
        print("Check the logs above for error details.")

    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
