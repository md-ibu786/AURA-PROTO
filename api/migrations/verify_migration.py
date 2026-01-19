#!/usr/bin/env python3
"""
============================================================================
MIGRATION VERIFICATION SCRIPT
============================================================================

PURPOSE:
    Verify that migration 001_add_module_schema.py completed successfully.
    Tests all constraints, indices, and node creation capabilities.

USAGE:
    python api/migrations/verify_migration.py

REQUIREMENTS:
    - Neo4j must be running
    - Migration 001 must have been executed
    - .env must be configured with Neo4j credentials
============================================================================
"""

import os
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from neo4j_config import neo4j_driver
from logging_config import logger


class MigrationVerifier:
    """Verify Neo4j schema migration."""
    
    def __init__(self, driver):
        self.driver = driver
        self.checks_passed = 0
        self.checks_failed = 0
    
    def run_query(self, query, params=None):
        """Execute a Cypher query and return results."""
        try:
            with self.driver.session() as session:
                result = session.run(query, params or {})
                return [record.data() for record in result]
        except Exception as e:
            logger.error(f"Query failed: {e}")
            return None
    
    def check_constraints(self):
        """Verify all required constraints exist."""
        print("\n" + "=" * 70)
        print("CHECKING CONSTRAINTS")
        print("=" * 70)
        
        expected_constraints = [
            "module_id_unique",
            "studysession_id_unique",
            "message_id_unique"
        ]
        
        query = "SHOW CONSTRAINTS"
        results = self.run_query(query)
        
        if results is None:
            print("✗ Failed to retrieve constraints")
            self.checks_failed += 1
            return False
        
        constraint_names = [r.get('name') for r in results]
        
        for expected in expected_constraints:
            if expected in constraint_names:
                print(f"✓ Constraint '{expected}' exists")
                self.checks_passed += 1
            else:
                print(f"✗ Constraint '{expected}' NOT FOUND")
                self.checks_failed += 1
        
        return self.checks_failed == 0
    
    def check_indices(self):
        """Verify all required indices exist."""
        print("\n" + "=" * 70)
        print("CHECKING INDICES")
        print("=" * 70)
        
        expected_indices = [
            "module_user_idx",
            "module_code_idx",
            "module_status_idx",
            "studysession_user_idx",
            "studysession_status_idx",
            "message_session_idx",
            "message_created_idx",
            "document_module_idx",
            "chunk_module_idx"
        ]
        
        query = "SHOW INDEXES"
        results = self.run_query(query)
        
        if results is None:
            print("✗ Failed to retrieve indices")
            self.checks_failed += 1
            return False
        
        index_names = [r.get('name') for r in results]
        
        for expected in expected_indices:
            if expected in index_names:
                print(f"✓ Index '{expected}' exists")
                self.checks_passed += 1
            else:
                print(f"✗ Index '{expected}' NOT FOUND")
                self.checks_failed += 1
        
        return True
    
    def check_vector_index(self):
        """Verify vector index exists with correct configuration."""
        print("\n" + "=" * 70)
        print("CHECKING VECTOR INDEX")
        print("=" * 70)
        
        try:
            query = "SHOW VECTOR INDEXES"
            results = self.run_query(query)
            
            if results is None:
                print("✗ Failed to retrieve vector indices (may require Neo4j 5.11+)")
                self.checks_failed += 1
                return False
            
            vector_index_found = False
            for idx in results:
                if idx.get('name') == 'chunk_vector_index':
                    vector_index_found = True
                    print(f"✓ Vector index 'chunk_vector_index' exists")
                    print(f"  - State: {idx.get('state', 'unknown')}")
                    print(f"  - Type: {idx.get('type', 'unknown')}")
                    self.checks_passed += 1
                    break
            
            if not vector_index_found:
                print("✗ Vector index 'chunk_vector_index' NOT FOUND")
                self.checks_failed += 1
            
            return vector_index_found
            
        except Exception as e:
            print(f"✗ Vector index check failed: {e}")
            print("  Note: Vector indices require Neo4j 5.11+")
            self.checks_failed += 1
            return False
    
    def test_module_creation(self):
        """Test creating a Module node."""
        print("\n" + "=" * 70)
        print("TESTING MODULE NODE CREATION")
        print("=" * 70)
        
        try:
            # Create test module
            create_query = """
            CREATE (m:Module {
                id: 'verify_test_mod_001',
                code: 'VERIFY101',
                name: 'Verification Test Module',
                user_id: 'verify_test_user',
                kg_status: 'draft',
                created_at: datetime(),
                updated_at: datetime()
            })
            RETURN m.id as id
            """
            result = self.run_query(create_query)
            
            if result and result[0].get('id') == 'verify_test_mod_001':
                print("✓ Module node created successfully")
                self.checks_passed += 1
                
                # Cleanup
                cleanup_query = "MATCH (m:Module {id: 'verify_test_mod_001'}) DELETE m"
                self.run_query(cleanup_query)
                print("✓ Test module cleaned up")
                return True
            else:
                print("✗ Module node creation failed")
                self.checks_failed += 1
                return False
                
        except Exception as e:
            print(f"✗ Module creation test failed: {e}")
            self.checks_failed += 1
            return False
    
    def test_studysession_creation(self):
        """Test creating a StudySession node."""
        print("\n" + "=" * 70)
        print("TESTING STUDYSESSION NODE CREATION")
        print("=" * 70)
        
        try:
            create_query = """
            CREATE (s:StudySession {
                id: 'verify_test_session_001',
                title: 'Test Session',
                module_ids: ['mod_001', 'mod_002'],
                user_id: 'verify_test_user',
                status: 'active',
                message_count: 0,
                created_at: datetime(),
                updated_at: datetime(),
                is_active: true
            })
            RETURN s.id as id
            """
            result = self.run_query(create_query)
            
            if result and result[0].get('id') == 'verify_test_session_001':
                print("✓ StudySession node created successfully")
                self.checks_passed += 1
                
                # Cleanup
                cleanup_query = "MATCH (s:StudySession {id: 'verify_test_session_001'}) DELETE s"
                self.run_query(cleanup_query)
                print("✓ Test session cleaned up")
                return True
            else:
                print("✗ StudySession node creation failed")
                self.checks_failed += 1
                return False
                
        except Exception as e:
            print(f"✗ StudySession creation test failed: {e}")
            self.checks_failed += 1
            return False
    
    def test_message_creation(self):
        """Test creating a Message node."""
        print("\n" + "=" * 70)
        print("TESTING MESSAGE NODE CREATION")
        print("=" * 70)
        
        try:
            create_query = """
            CREATE (m:Message {
                id: 'verify_test_msg_001',
                session_id: 'session_001',
                role: 'user',
                content: 'Test message content',
                created_at: datetime()
            })
            RETURN m.id as id
            """
            result = self.run_query(create_query)
            
            if result and result[0].get('id') == 'verify_test_msg_001':
                print("✓ Message node created successfully")
                self.checks_passed += 1
                
                # Cleanup
                cleanup_query = "MATCH (m:Message {id: 'verify_test_msg_001'}) DELETE m"
                self.run_query(cleanup_query)
                print("✓ Test message cleaned up")
                return True
            else:
                print("✗ Message node creation failed")
                self.checks_failed += 1
                return False
                
        except Exception as e:
            print(f"✗ Message creation test failed: {e}")
            self.checks_failed += 1
            return False
    
    def test_document_with_module_id(self):
        """Test creating a Document with module_id."""
        print("\n" + "=" * 70)
        print("TESTING DOCUMENT WITH MODULE_ID")
        print("=" * 70)
        
        try:
            create_query = """
            CREATE (d:Document {
                id: 'verify_test_doc_001',
                title: 'Test Document',
                module_id: 'mod_test_001',
                upload_date: datetime()
            })
            RETURN d.id as id, d.module_id as module_id
            """
            result = self.run_query(create_query)
            
            if result and result[0].get('module_id') == 'mod_test_001':
                print("✓ Document with module_id created successfully")
                self.checks_passed += 1
                
                # Cleanup
                cleanup_query = "MATCH (d:Document {id: 'verify_test_doc_001'}) DELETE d"
                self.run_query(cleanup_query)
                print("✓ Test document cleaned up")
                return True
            else:
                print("✗ Document with module_id creation failed")
                self.checks_failed += 1
                return False
                
        except Exception as e:
            print(f"✗ Document creation test failed: {e}")
            self.checks_failed += 1
            return False
    
    def test_chunk_with_module_id(self):
        """Test creating a Chunk with module_id."""
        print("\n" + "=" * 70)
        print("TESTING CHUNK WITH MODULE_ID")
        print("=" * 70)
        
        try:
            create_query = """
            CREATE (c:Chunk {
                id: 'verify_test_chunk_001',
                text: 'Test chunk content',
                module_id: 'mod_test_001',
                token_count: 10,
                index: 0
            })
            RETURN c.id as id, c.module_id as module_id
            """
            result = self.run_query(create_query)
            
            if result and result[0].get('module_id') == 'mod_test_001':
                print("✓ Chunk with module_id created successfully")
                self.checks_passed += 1
                
                # Cleanup
                cleanup_query = "MATCH (c:Chunk {id: 'verify_test_chunk_001'}) DELETE c"
                self.run_query(cleanup_query)
                print("✓ Test chunk cleaned up")
                return True
            else:
                print("✗ Chunk with module_id creation failed")
                self.checks_failed += 1
                return False
                
        except Exception as e:
            print(f"✗ Chunk creation test failed: {e}")
            self.checks_failed += 1
            return False
    
    def run_all_checks(self):
        """Run all verification checks."""
        print("\n" + "=" * 70)
        print("MIGRATION VERIFICATION SCRIPT")
        print("Neo4j Migration 001: Module Schema")
        print("=" * 70)
        
        # Run all checks
        self.check_constraints()
        self.check_indices()
        self.check_vector_index()
        self.test_module_creation()
        self.test_studysession_creation()
        self.test_message_creation()
        self.test_document_with_module_id()
        self.test_chunk_with_module_id()
        
        # Final report
        print("\n" + "=" * 70)
        print("VERIFICATION SUMMARY")
        print("=" * 70)
        print(f"✓ Checks Passed: {self.checks_passed}")
        print(f"✗ Checks Failed: {self.checks_failed}")
        print("=" * 70)
        
        if self.checks_failed == 0:
            print("\n🎉 ALL CHECKS PASSED! Migration verified successfully.")
            print("=" * 70)
            return True
        else:
            print(f"\n⚠️  {self.checks_failed} CHECK(S) FAILED!")
            print("Please review the output above for details.")
            print("=" * 70)
            return False


def main():
    """Run migration verification."""
    if neo4j_driver is None:
        print("✗ Neo4j driver not initialized. Check your .env configuration.")
        print("Required env vars: NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD")
        return False
    
    verifier = MigrationVerifier(neo4j_driver)
    success = verifier.run_all_checks()
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
