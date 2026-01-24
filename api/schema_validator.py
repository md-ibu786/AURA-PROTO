"""
schema_validator.py
Schema validation utilities for AURA platform Neo4j database

Validates that the Neo4j database matches the expected schema definition,
detects schema drift, identifies missing indices/constraints, and generates
migration scripts to align the database with the canonical schema.

Key classes:
- SchemaValidator: Main validation class with database comparison
- SchemaValidationResult: Validation outcome with detailed findings
- SchemaComparisonResult: Cross-app schema comparison (NOTES-MANAGER vs CHAT)

@see: api/schemas/neo4j_schema.py - Canonical schema definition
@see: api/migrations/003_schema_alignment.py - Migration script
@note: Uses SHOW INDEXES and SHOW CONSTRAINTS which require Neo4j 4.2+
"""

import os
import sys
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from pydantic import BaseModel, Field
from neo4j import Driver

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from schemas.neo4j_schema import (
    NodeType,
    RelationshipType,
    VECTOR_INDICES,
    FULLTEXT_INDICES,
    CONSTRAINTS,
    ENTITY_ENTITY_RELATIONSHIPS,
    get_schema_definition,
    get_node_types,
    get_relationship_types,
    generate_vector_index_cypher,
    generate_fulltext_index_cypher,
    generate_constraint_cypher,
    VectorIndexDefinition,
    FulltextIndexDefinition,
    ConstraintDefinition,
)


# ============================================================================
# RESULT MODELS
# ============================================================================

class IndexStatus(BaseModel):
    """Status of a single index."""
    name: str
    exists: bool
    state: Optional[str] = None  # ONLINE, POPULATING, FAILED
    index_type: str = "unknown"  # VECTOR, FULLTEXT, BTREE, etc.
    node_type: Optional[str] = None
    properties: List[str] = Field(default_factory=list)


class ConstraintStatus(BaseModel):
    """Status of a single constraint."""
    name: str
    exists: bool
    constraint_type: Optional[str] = None  # UNIQUENESS, NODE_KEY, etc.
    node_type: Optional[str] = None
    properties: List[str] = Field(default_factory=list)


class PropertyMismatch(BaseModel):
    """Detected property mismatch."""
    node_type: str
    expected_properties: List[str]
    actual_properties: List[str]
    missing: List[str]
    extra: List[str]


class SchemaValidationResult(BaseModel):
    """Complete schema validation result."""
    is_valid: bool
    validated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Index status
    vector_indices: Dict[str, IndexStatus] = Field(default_factory=dict)
    fulltext_indices: Dict[str, IndexStatus] = Field(default_factory=dict)
    
    # Constraint status
    constraints: Dict[str, ConstraintStatus] = Field(default_factory=dict)
    
    # Missing elements
    missing_vector_indices: List[str] = Field(default_factory=list)
    missing_fulltext_indices: List[str] = Field(default_factory=list)
    missing_constraints: List[str] = Field(default_factory=list)
    
    # Extra elements (in DB but not in schema)
    extra_node_types: List[str] = Field(default_factory=list)
    extra_relationship_types: List[str] = Field(default_factory=list)
    
    # Property mismatches
    property_mismatches: List[PropertyMismatch] = Field(default_factory=list)
    
    # Warnings and errors
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    
    # Summary counts
    total_indices_expected: int = 0
    total_indices_present: int = 0
    total_constraints_expected: int = 0
    total_constraints_present: int = 0

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SchemaComparisonResult(BaseModel):
    """Result of comparing schemas between applications."""
    compared_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Elements unique to each app
    notes_manager_only: Dict[str, List[str]] = Field(default_factory=dict)
    chat_only: Dict[str, List[str]] = Field(default_factory=dict)
    
    # Shared elements
    shared: Dict[str, List[str]] = Field(default_factory=dict)
    
    # Conflicts (same name, different definition)
    conflicts: List[Dict[str, Any]] = Field(default_factory=list)
    
    # Compatibility assessment
    is_compatible: bool = True
    compatibility_notes: List[str] = Field(default_factory=list)


class SchemaStatus(BaseModel):
    """High-level schema status for API response."""
    is_valid: bool
    schema_version: str
    indices_ready: bool
    constraints_ready: bool
    missing_count: int
    warnings_count: int
    errors_count: int
    last_validated: datetime = Field(default_factory=datetime.utcnow)


class MigrationResult(BaseModel):
    """Result of running a migration."""
    success: bool
    dry_run: bool
    statements_executed: int
    statements_failed: int
    executed_statements: List[str] = Field(default_factory=list)
    failed_statements: List[Dict[str, str]] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)


# ============================================================================
# SCHEMA VALIDATOR CLASS
# ============================================================================

class SchemaValidator:
    """
    Validates Neo4j database against the canonical AURA schema definition.
    
    Provides methods to:
    - Validate current database schema against expected schema
    - Identify missing indices, constraints, and node types
    - Generate migration scripts for schema alignment
    - Compare schemas between AURA-NOTES-MANAGER and AURA-CHAT
    
    Usage:
        validator = SchemaValidator(neo4j_driver)
        result = validator.validate_schema()
        if not result.is_valid:
            print(f"Missing indices: {result.missing_vector_indices}")
            migration_script = validator.generate_migration_script()
    """
    
    def __init__(self, driver: Driver):
        """
        Initialize SchemaValidator with a Neo4j driver.
        
        Args:
            driver: Neo4j driver instance (sync or async supported)
        """
        self.driver = driver
        self._cached_indices: Optional[Dict[str, Any]] = None
        self._cached_constraints: Optional[Dict[str, Any]] = None
        self._cached_labels: Optional[Set[str]] = None
        self._cached_rel_types: Optional[Set[str]] = None
    
    def _get_database_indices(self) -> Dict[str, Dict[str, Any]]:
        """Get all indices from the database."""
        if self._cached_indices is not None:
            return self._cached_indices
        
        with self.driver.session() as session:
            result = session.run("SHOW INDEXES")
            self._cached_indices = {
                record["name"]: dict(record)
                for record in result
            }
        return self._cached_indices
    
    def _get_database_constraints(self) -> Dict[str, Dict[str, Any]]:
        """Get all constraints from the database."""
        if self._cached_constraints is not None:
            return self._cached_constraints
        
        with self.driver.session() as session:
            result = session.run("SHOW CONSTRAINTS")
            self._cached_constraints = {
                record["name"]: dict(record)
                for record in result
            }
        return self._cached_constraints
    
    def _get_database_labels(self) -> Set[str]:
        """Get all node labels in use."""
        if self._cached_labels is not None:
            return self._cached_labels
        
        with self.driver.session() as session:
            result = session.run("CALL db.labels() YIELD label RETURN label")
            self._cached_labels = {record["label"] for record in result}
        return self._cached_labels
    
    def _get_database_relationship_types(self) -> Set[str]:
        """Get all relationship types in use."""
        if self._cached_rel_types is not None:
            return self._cached_rel_types
        
        with self.driver.session() as session:
            result = session.run(
                "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
            )
            self._cached_rel_types = {
                record["relationshipType"] for record in result
            }
        return self._cached_rel_types
    
    def _clear_cache(self):
        """Clear cached database state."""
        self._cached_indices = None
        self._cached_constraints = None
        self._cached_labels = None
        self._cached_rel_types = None
    
    def validate_schema(self) -> SchemaValidationResult:
        """
        Validate current database against expected schema definition.
        
        Checks:
        - All vector indices exist and are ONLINE
        - All fulltext indices exist and are ONLINE
        - All constraints exist
        - No unexpected node types or relationship types
        
        Returns:
            SchemaValidationResult with detailed validation outcome
        """
        self._clear_cache()
        result = SchemaValidationResult(is_valid=True)
        
        try:
            # Get current database state
            db_indices = self._get_database_indices()
            db_constraints = self._get_database_constraints()
            db_labels = self._get_database_labels()
            db_rel_types = self._get_database_relationship_types()
            
            # Expected elements from schema definition
            expected_vector_indices = {vi.name for vi in VECTOR_INDICES}
            expected_fulltext_indices = {fi.name for fi in FULLTEXT_INDICES}
            expected_constraints = {c.name for c in CONSTRAINTS}
            expected_node_types = set(get_node_types())
            expected_rel_types = set(get_relationship_types())
            
            # Set totals
            result.total_indices_expected = len(expected_vector_indices) + len(expected_fulltext_indices)
            result.total_constraints_expected = len(expected_constraints)
            
            # Check vector indices
            for vi in VECTOR_INDICES:
                if vi.name in db_indices:
                    idx_data = db_indices[vi.name]
                    status = IndexStatus(
                        name=vi.name,
                        exists=True,
                        state=idx_data.get("state", "UNKNOWN"),
                        index_type=idx_data.get("type", "VECTOR"),
                        node_type=vi.node_type,
                        properties=[vi.property],
                    )
                    result.vector_indices[vi.name] = status
                    result.total_indices_present += 1
                    
                    if status.state != "ONLINE":
                        result.warnings.append(
                            f"Vector index '{vi.name}' state is {status.state}"
                        )
                else:
                    result.vector_indices[vi.name] = IndexStatus(
                        name=vi.name,
                        exists=False,
                        node_type=vi.node_type,
                        properties=[vi.property],
                    )
                    result.missing_vector_indices.append(vi.name)
                    result.is_valid = False
            
            # Check fulltext indices
            for fi in FULLTEXT_INDICES:
                if fi.name in db_indices:
                    idx_data = db_indices[fi.name]
                    status = IndexStatus(
                        name=fi.name,
                        exists=True,
                        state=idx_data.get("state", "UNKNOWN"),
                        index_type=idx_data.get("type", "FULLTEXT"),
                        node_type=fi.node_type,
                        properties=fi.properties,
                    )
                    result.fulltext_indices[fi.name] = status
                    result.total_indices_present += 1
                    
                    if status.state != "ONLINE":
                        result.warnings.append(
                            f"Fulltext index '{fi.name}' state is {status.state}"
                        )
                else:
                    result.fulltext_indices[fi.name] = IndexStatus(
                        name=fi.name,
                        exists=False,
                        node_type=fi.node_type,
                        properties=fi.properties,
                    )
                    result.missing_fulltext_indices.append(fi.name)
                    result.is_valid = False
            
            # Check constraints
            for c in CONSTRAINTS:
                if c.name in db_constraints:
                    const_data = db_constraints[c.name]
                    status = ConstraintStatus(
                        name=c.name,
                        exists=True,
                        constraint_type=const_data.get("type", "UNIQUENESS"),
                        node_type=c.node_type,
                        properties=[c.property],
                    )
                    result.constraints[c.name] = status
                    result.total_constraints_present += 1
                else:
                    result.constraints[c.name] = ConstraintStatus(
                        name=c.name,
                        exists=False,
                        node_type=c.node_type,
                        properties=[c.property],
                    )
                    result.missing_constraints.append(c.name)
                    result.is_valid = False
            
            # Check for extra node types (in DB but not in schema)
            for label in db_labels:
                if label not in expected_node_types:
                    result.extra_node_types.append(label)
                    result.warnings.append(
                        f"Unexpected node type in database: {label}"
                    )
            
            # Check for extra relationship types
            for rel_type in db_rel_types:
                if rel_type not in expected_rel_types:
                    result.extra_relationship_types.append(rel_type)
                    # Only warn if it's not a common Neo4j internal type
                    if not rel_type.startswith("_"):
                        result.warnings.append(
                            f"Unexpected relationship type in database: {rel_type}"
                        )
            
        except Exception as e:
            result.is_valid = False
            result.errors.append(f"Validation failed: {str(e)}")
        
        return result
    
    def get_missing_indices(self) -> List[str]:
        """Get list of missing index names."""
        result = self.validate_schema()
        return result.missing_vector_indices + result.missing_fulltext_indices
    
    def get_missing_constraints(self) -> List[str]:
        """Get list of missing constraint names."""
        result = self.validate_schema()
        return result.missing_constraints
    
    def get_extra_node_types(self) -> List[str]:
        """Get list of node types in DB but not in schema."""
        result = self.validate_schema()
        return result.extra_node_types
    
    def generate_migration_script(self) -> str:
        """
        Generate a Cypher migration script to align database with schema.
        
        Returns:
            String containing Cypher statements to create missing elements.
        """
        result = self.validate_schema()
        statements = []
        
        # Generate statements for missing vector indices
        for vi in VECTOR_INDICES:
            if vi.name in result.missing_vector_indices:
                statements.append(generate_vector_index_cypher(vi).strip())
        
        # Generate statements for missing fulltext indices
        for fi in FULLTEXT_INDICES:
            if fi.name in result.missing_fulltext_indices:
                statements.append(generate_fulltext_index_cypher(fi).strip())
        
        # Generate statements for missing constraints
        for c in CONSTRAINTS:
            if c.name in result.missing_constraints:
                statements.append(generate_constraint_cypher(c).strip())
        
        if not statements:
            return "-- No migration needed, schema is aligned"
        
        header = f"""-- AURA Schema Alignment Migration
-- Generated: {datetime.utcnow().isoformat()}
-- Missing elements: {len(statements)}
-- 
-- Run each statement sequentially.
-- All statements use IF NOT EXISTS for idempotency.
"""
        return header + "\n\n" + ";\n\n".join(statements) + ";"
    
    def run_migration(self, dry_run: bool = True) -> MigrationResult:
        """
        Run migration to align database with schema.
        
        Args:
            dry_run: If True, only generate statements without executing.
                    Default is True for safety.
        
        Returns:
            MigrationResult with execution details.
        """
        result = MigrationResult(
            success=True,
            dry_run=dry_run,
            statements_executed=0,
            statements_failed=0,
        )
        
        validation = self.validate_schema()
        statements = []
        
        # Collect statements for missing elements
        for vi in VECTOR_INDICES:
            if vi.name in validation.missing_vector_indices:
                statements.append(("vector_index", vi.name, generate_vector_index_cypher(vi)))
        
        for fi in FULLTEXT_INDICES:
            if fi.name in validation.missing_fulltext_indices:
                statements.append(("fulltext_index", fi.name, generate_fulltext_index_cypher(fi)))
        
        for c in CONSTRAINTS:
            if c.name in validation.missing_constraints:
                statements.append(("constraint", c.name, generate_constraint_cypher(c)))
        
        if dry_run:
            result.executed_statements = [stmt for _, _, stmt in statements]
            return result
        
        # Execute statements
        for stmt_type, name, cypher in statements:
            try:
                with self.driver.session() as session:
                    session.run(cypher)
                result.executed_statements.append(cypher)
                result.statements_executed += 1
            except Exception as e:
                result.statements_failed += 1
                result.failed_statements.append({
                    "type": stmt_type,
                    "name": name,
                    "statement": cypher,
                    "error": str(e),
                })
                result.errors.append(f"Failed to create {stmt_type} '{name}': {e}")
                result.success = False
        
        # Clear cache after migration
        self._clear_cache()
        
        return result
    
    def get_schema_status(self) -> SchemaStatus:
        """Get high-level schema status summary."""
        validation = self.validate_schema()
        schema_def = get_schema_definition()
        
        missing_count = (
            len(validation.missing_vector_indices) +
            len(validation.missing_fulltext_indices) +
            len(validation.missing_constraints)
        )
        
        # Check if all indices are ready (present and ONLINE)
        indices_ready = (
            len(validation.missing_vector_indices) == 0 and
            len(validation.missing_fulltext_indices) == 0 and
            all(
                idx.state == "ONLINE"
                for idx in validation.vector_indices.values()
                if idx.exists
            ) and
            all(
                idx.state == "ONLINE"
                for idx in validation.fulltext_indices.values()
                if idx.exists
            )
        )
        
        return SchemaStatus(
            is_valid=validation.is_valid,
            schema_version=schema_def.version,
            indices_ready=indices_ready,
            constraints_ready=len(validation.missing_constraints) == 0,
            missing_count=missing_count,
            warnings_count=len(validation.warnings),
            errors_count=len(validation.errors),
        )


# ============================================================================
# DEPENDENCY INJECTION HELPER
# ============================================================================

def get_schema_validator() -> SchemaValidator:
    """
    Dependency injection helper for FastAPI.
    
    Usage in routers:
        @router.get("/validate")
        async def validate(validator: SchemaValidator = Depends(get_schema_validator)):
            return validator.validate_schema()
    """
    from neo4j_config import neo4j_driver
    
    if neo4j_driver is None:
        raise RuntimeError("Neo4j driver not initialized")
    
    return SchemaValidator(neo4j_driver)
