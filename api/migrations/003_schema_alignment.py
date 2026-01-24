#!/usr/bin/env python3
"""
============================================================================
MIGRATION: 003 - Schema Alignment
VERSION: 003
CREATED: 2026-01-24
============================================================================

PURPOSE:
    Align AURA-NOTES-MANAGER Neo4j schema with the unified AURA platform schema.
    Ensures both AURA-NOTES-MANAGER and AURA-CHAT can read/write consistently
    to the shared Neo4j database.

CHANGES:
    1. Creates any missing vector indices from the canonical schema
    2. Creates any missing fulltext indices
    3. Creates any missing constraints
    4. Does NOT remove existing data or indices (additive only)
    5. All operations are idempotent (IF NOT EXISTS)

PREREQUISITES:
    - Migration 002 (KG Enhancement Schema) must be completed
    - Neo4j 5.15+ for vector index syntax

IDEMPOTENCY:
    All operations use IF NOT EXISTS to ensure safe re-execution

REFERENCE:
    - Schema Definition: api/schemas/neo4j_schema.py
    - Validator: api/schema_validator.py
    - Plan: .planning/phases/11-kg-advanced/11-04-PLAN.md

@see: 002_kg_enhancement_schema.py - Previous migration
@see: schema_validator.py - Validation utilities
@note: This migration is additive only - no data loss
============================================================================
"""

import os
import sys
from datetime import datetime
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from migrations import Migration, run_migration
from neo4j_config import neo4j_driver
from logging_config import logger
from schemas.neo4j_schema import (
    VECTOR_INDICES,
    FULLTEXT_INDICES,
    CONSTRAINTS,
    generate_vector_index_cypher,
    generate_fulltext_index_cypher,
    generate_constraint_cypher,
)


class SchemaAlignment(Migration):
    """
    Migration to align AURA-NOTES-MANAGER schema with unified AURA platform schema.
    
    This migration ensures compatibility between AURA-NOTES-MANAGER and AURA-CHAT
    by creating any missing schema elements from the canonical definition.
    """

    version = "003"
    description = "Align schema with unified AURA platform schema for AURA-CHAT compatibility"

    def upgrade(self, driver) -> bool:
        """
        Apply schema alignment changes.

        Creates any missing:
        - Vector indices (document, parent_chunk, chunk, entity types)
        - Fulltext indices (chunk text search)
        - Constraints (unique IDs for all node types)

        Args:
            driver: Neo4j driver instance

        Returns:
            bool: True if successful
        """
        try:
            logger.info("=" * 60)
            logger.info("MIGRATION 003: Schema Alignment")
            logger.info("=" * 60)
            
            # ========================================
            # STEP 1: CHECK CURRENT SCHEMA STATE
            # ========================================
            logger.info("Step 1: Checking current schema state...")
            
            current_indices = set()
            current_constraints = set()
            
            with driver.session() as session:
                # Get existing indices
                result = session.run("SHOW INDEXES")
                for record in result:
                    current_indices.add(record["name"])
                
                # Get existing constraints
                result = session.run("SHOW CONSTRAINTS")
                for record in result:
                    current_constraints.add(record["name"])
            
            logger.info(f"  Found {len(current_indices)} existing indices")
            logger.info(f"  Found {len(current_constraints)} existing constraints")
            
            # ========================================
            # STEP 2: CREATE MISSING VECTOR INDICES
            # ========================================
            logger.info("Step 2: Creating missing vector indices...")
            
            vector_created = 0
            vector_skipped = 0
            
            for vi in VECTOR_INDICES:
                if vi.name in current_indices:
                    logger.debug(f"  Vector index '{vi.name}' already exists, skipping")
                    vector_skipped += 1
                else:
                    cypher = generate_vector_index_cypher(vi)
                    self.execute_cypher_query(driver, cypher)
                    logger.info(f"  ✓ Created vector index: {vi.name}")
                    vector_created += 1
            
            logger.info(f"  Vector indices - Created: {vector_created}, Skipped: {vector_skipped}")
            
            # ========================================
            # STEP 3: CREATE MISSING FULLTEXT INDICES
            # ========================================
            logger.info("Step 3: Creating missing fulltext indices...")
            
            fulltext_created = 0
            fulltext_skipped = 0
            
            for fi in FULLTEXT_INDICES:
                if fi.name in current_indices:
                    logger.debug(f"  Fulltext index '{fi.name}' already exists, skipping")
                    fulltext_skipped += 1
                else:
                    cypher = generate_fulltext_index_cypher(fi)
                    self.execute_cypher_query(driver, cypher)
                    logger.info(f"  ✓ Created fulltext index: {fi.name}")
                    fulltext_created += 1
            
            logger.info(f"  Fulltext indices - Created: {fulltext_created}, Skipped: {fulltext_skipped}")
            
            # ========================================
            # STEP 4: CREATE MISSING CONSTRAINTS
            # ========================================
            logger.info("Step 4: Creating missing constraints...")
            
            constraints_created = 0
            constraints_skipped = 0
            
            for c in CONSTRAINTS:
                if c.name in current_constraints:
                    logger.debug(f"  Constraint '{c.name}' already exists, skipping")
                    constraints_skipped += 1
                else:
                    cypher = generate_constraint_cypher(c)
                    self.execute_cypher_query(driver, cypher)
                    logger.info(f"  ✓ Created constraint: {c.name}")
                    constraints_created += 1
            
            logger.info(f"  Constraints - Created: {constraints_created}, Skipped: {constraints_skipped}")
            
            # ========================================
            # STEP 5: VERIFY MIGRATION
            # ========================================
            logger.info("Step 5: Verifying migration...")
            
            if not self.verify(driver):
                logger.error("Migration verification failed")
                return False
            
            # ========================================
            # SUMMARY
            # ========================================
            total_created = vector_created + fulltext_created + constraints_created
            total_skipped = vector_skipped + fulltext_skipped + constraints_skipped
            
            logger.info("=" * 60)
            logger.info("MIGRATION 003 COMPLETE")
            logger.info(f"  Total elements created: {total_created}")
            logger.info(f"  Total elements skipped (existing): {total_skipped}")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            logger.error(f"Migration 003 failed: {e}")
            raise

    def downgrade(self, driver) -> bool:
        """
        Revert schema alignment changes (if possible).
        
        WARNING: This will drop indices and constraints created by this migration.
        Data in the nodes/relationships will NOT be affected.
        
        Args:
            driver: Neo4j driver instance
            
        Returns:
            bool: True if successful
        """
        logger.warning("=" * 60)
        logger.warning("MIGRATION 003: DOWNGRADE (REVERT)")
        logger.warning("WARNING: This will drop indices and constraints!")
        logger.warning("=" * 60)
        
        try:
            # Note: We only drop what we created, not pre-existing elements
            # In practice, we can't distinguish, so we just log a warning
            logger.warning("Downgrade not fully implemented for safety reasons.")
            logger.warning("To fully revert, manually drop the following indices and constraints:")
            
            for vi in VECTOR_INDICES:
                logger.warning(f"  DROP INDEX {vi.name} IF EXISTS")
            
            for fi in FULLTEXT_INDICES:
                logger.warning(f"  DROP INDEX {fi.name} IF EXISTS")
            
            for c in CONSTRAINTS:
                logger.warning(f"  DROP CONSTRAINT {c.name} IF EXISTS")
            
            return True
            
        except Exception as e:
            logger.error(f"Downgrade failed: {e}")
            return False

    def verify(self, driver) -> bool:
        """
        Verify migration was successful.
        
        Checks that all expected indices and constraints exist.
        
        Args:
            driver: Neo4j driver instance
            
        Returns:
            bool: True if all expected elements are present
        """
        try:
            from schema_validator import SchemaValidator
            
            validator = SchemaValidator(driver)
            result = validator.validate_schema()
            
            if result.is_valid:
                logger.info("✓ Schema validation passed - all elements present")
                return True
            
            # Log what's missing
            if result.missing_vector_indices:
                logger.error(f"Missing vector indices: {result.missing_vector_indices}")
            if result.missing_fulltext_indices:
                logger.error(f"Missing fulltext indices: {result.missing_fulltext_indices}")
            if result.missing_constraints:
                logger.error(f"Missing constraints: {result.missing_constraints}")
            
            return False
            
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return False


# ============================================================================
# ASYNC VERSION FOR AURA-CHAT COMPATIBILITY
# ============================================================================

async def upgrade_async(driver) -> bool:
    """
    Async version of upgrade for AURA-CHAT compatibility.
    
    AURA-CHAT uses AsyncGraphDatabase, so this function provides
    an async interface for the same migration logic.
    
    Args:
        driver: Async Neo4j driver instance
        
    Returns:
        bool: True if successful
    """
    try:
        logger.info("Running async schema alignment migration...")
        
        # Get current indices and constraints
        async with driver.session() as session:
            result = await session.run("SHOW INDEXES")
            current_indices = {record["name"] async for record in result}
            
            result = await session.run("SHOW CONSTRAINTS")
            current_constraints = {record["name"] async for record in result}
        
        # Create missing vector indices
        for vi in VECTOR_INDICES:
            if vi.name not in current_indices:
                cypher = generate_vector_index_cypher(vi)
                async with driver.session() as session:
                    await session.run(cypher)
                logger.info(f"✓ Created vector index: {vi.name}")
        
        # Create missing fulltext indices
        for fi in FULLTEXT_INDICES:
            if fi.name not in current_indices:
                cypher = generate_fulltext_index_cypher(fi)
                async with driver.session() as session:
                    await session.run(cypher)
                logger.info(f"✓ Created fulltext index: {fi.name}")
        
        # Create missing constraints
        for c in CONSTRAINTS:
            if c.name not in current_constraints:
                cypher = generate_constraint_cypher(c)
                async with driver.session() as session:
                    await session.run(cypher)
                logger.info(f"✓ Created constraint: {c.name}")
        
        return await verify_async(driver)
        
    except Exception as e:
        logger.error(f"Async migration failed: {e}")
        return False


async def verify_async(driver) -> bool:
    """
    Async verification for the migration.
    
    Args:
        driver: Async Neo4j driver instance
        
    Returns:
        bool: True if all elements are present
    """
    try:
        expected_indices = {vi.name for vi in VECTOR_INDICES}
        expected_indices.update(fi.name for fi in FULLTEXT_INDICES)
        expected_constraints = {c.name for c in CONSTRAINTS}
        
        async with driver.session() as session:
            result = await session.run("SHOW INDEXES")
            current_indices = {record["name"] async for record in result}
            
            result = await session.run("SHOW CONSTRAINTS")
            current_constraints = {record["name"] async for record in result}
        
        missing_indices = expected_indices - current_indices
        missing_constraints = expected_constraints - current_constraints
        
        if missing_indices or missing_constraints:
            if missing_indices:
                logger.error(f"Missing indices: {missing_indices}")
            if missing_constraints:
                logger.error(f"Missing constraints: {missing_constraints}")
            return False
        
        logger.info("✓ Async schema validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Async verification failed: {e}")
        return False


# ============================================================================
# CLI ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Run schema alignment migration"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify current schema state"
    )
    
    args = parser.parse_args()
    
    if neo4j_driver is None:
        print("ERROR: Neo4j driver not initialized. Check .env configuration.")
        sys.exit(1)
    
    migration = SchemaAlignment()
    
    if args.verify_only:
        print("Verifying schema...")
        if migration.verify(neo4j_driver):
            print("Schema is valid and aligned.")
            sys.exit(0)
        else:
            print("Schema has missing elements.")
            sys.exit(1)
    
    if args.dry_run:
        print("DRY RUN: Would execute the following changes...")
        from schema_validator import SchemaValidator
        validator = SchemaValidator(neo4j_driver)
        script = validator.generate_migration_script()
        print(script)
        sys.exit(0)
    
    # Run the migration
    success = run_migration(migration, neo4j_driver)
    sys.exit(0 if success else 1)
