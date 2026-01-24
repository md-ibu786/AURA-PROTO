# schema.py
# FastAPI router for schema management endpoints

# Provides REST API endpoints for validating Neo4j schema against the canonical
# AURA platform definition, viewing schema status, and running migrations to
# align the database with the expected schema.

# @see: api/schemas/neo4j_schema.py - Canonical schema definition
# @see: api/schema_validator.py - SchemaValidator class
# @see: api/migrations/003_schema_alignment.py - Migration script
# @note: Migration endpoint defaults to dry_run=True for safety

from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.neo4j_config import neo4j_driver
from api.schema_validator import (
    SchemaValidator,
    SchemaValidationResult,
    SchemaStatus,
    MigrationResult,
    get_schema_validator,
)
from api.schemas.neo4j_schema import (
    SchemaDefinition,
    get_schema_definition,
    NodeType,
    RelationshipType,
    VECTOR_INDICES,
    FULLTEXT_INDICES,
    CONSTRAINTS,
    ENTITY_ENTITY_RELATIONSHIPS,
)

logger = logging.getLogger(__name__)


# ============================================================================
# ROUTER SETUP
# ============================================================================

router = APIRouter(prefix="/v1/schema", tags=["Schema"])


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class SchemaDefinitionResponse(BaseModel):
    """Response model for schema definition endpoint."""
    version: str
    updated_at: datetime
    node_types: list[str]
    relationship_types: list[str]
    entity_entity_relationships: list[str]
    vector_indices_count: int
    fulltext_indices_count: int
    constraints_count: int
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class SchemaElementsResponse(BaseModel):
    """Detailed schema elements for inspection."""
    node_types: dict[str, list[str]]  # node_type -> properties
    relationship_types: list[str]
    vector_indices: list[dict]
    fulltext_indices: list[dict]
    constraints: list[dict]


# ============================================================================
# DEPENDENCY INJECTION
# ============================================================================

def get_validator() -> SchemaValidator:
    """Get SchemaValidator instance with Neo4j driver."""
    if neo4j_driver is None:
        raise HTTPException(
            status_code=503,
            detail="Neo4j connection not available"
        )
    return SchemaValidator(neo4j_driver)


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get(
    "/definition",
    response_model=SchemaDefinitionResponse,
    summary="Get schema definition",
    description="Returns the canonical schema definition for the AURA platform."
)
async def get_schema_definition_endpoint() -> SchemaDefinitionResponse:
    """
    Get the canonical schema definition.
    
    Returns the expected schema that both AURA-NOTES-MANAGER and AURA-CHAT
    should adhere to. This is the single source of truth for the Neo4j
    graph structure.
    
    Returns:
        SchemaDefinitionResponse with node types, relationships, and counts
    """
    schema = get_schema_definition()
    
    return SchemaDefinitionResponse(
        version=schema.version,
        updated_at=schema.updated_at,
        node_types=schema.node_types,
        relationship_types=schema.relationship_types,
        entity_entity_relationships=schema.entity_entity_relationships,
        vector_indices_count=len(schema.vector_indices),
        fulltext_indices_count=len(schema.fulltext_indices),
        constraints_count=len(schema.constraints),
    )


@router.get(
    "/definition/detailed",
    response_model=SchemaElementsResponse,
    summary="Get detailed schema elements",
    description="Returns detailed information about all schema elements."
)
async def get_schema_elements() -> SchemaElementsResponse:
    """
    Get detailed schema elements.
    
    Returns full details about each node type with its properties,
    all relationship types, and complete index/constraint definitions.
    
    Returns:
        SchemaElementsResponse with detailed schema elements
    """
    from api.schemas.neo4j_schema import NODE_PROPERTIES
    
    # Build node type -> properties map
    node_props = {}
    for node_type in NodeType:
        props = NODE_PROPERTIES.get(node_type, [])
        node_props[node_type.value] = props
    
    return SchemaElementsResponse(
        node_types=node_props,
        relationship_types=[rt.value for rt in RelationshipType],
        vector_indices=[vi.model_dump() for vi in VECTOR_INDICES],
        fulltext_indices=[fi.model_dump() for fi in FULLTEXT_INDICES],
        constraints=[c.model_dump() for c in CONSTRAINTS],
    )


@router.get(
    "/validate",
    response_model=SchemaValidationResult,
    summary="Validate database schema",
    description="Validates the current Neo4j database against the expected schema."
)
async def validate_schema(
    validator: SchemaValidator = Depends(get_validator)
) -> SchemaValidationResult:
    """
    Validate current database against schema definition.
    
    Checks that all expected indices, constraints, and node types exist
    in the Neo4j database. Reports missing elements and any extra
    (unexpected) elements found.
    
    Returns:
        SchemaValidationResult with validation outcome and details
        
    Raises:
        HTTPException 503: If Neo4j connection is not available
    """
    try:
        result = validator.validate_schema()
        
        if not result.is_valid:
            logger.warning(
                f"Schema validation failed: "
                f"{len(result.missing_vector_indices)} missing vector indices, "
                f"{len(result.missing_fulltext_indices)} missing fulltext indices, "
                f"{len(result.missing_constraints)} missing constraints"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Schema validation error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Schema validation failed: {str(e)}"
        )


@router.get(
    "/status",
    response_model=SchemaStatus,
    summary="Get schema status",
    description="Returns a high-level summary of the current schema status."
)
async def get_schema_status(
    validator: SchemaValidator = Depends(get_validator)
) -> SchemaStatus:
    """
    Get current schema status and statistics.
    
    Provides a quick overview of whether the schema is valid, how many
    elements are missing, and whether indices are ready for queries.
    
    Returns:
        SchemaStatus with summary information
        
    Raises:
        HTTPException 503: If Neo4j connection is not available
    """
    try:
        return validator.get_schema_status()
        
    except Exception as e:
        logger.error(f"Schema status error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get schema status: {str(e)}"
        )


@router.get(
    "/missing",
    summary="Get missing schema elements",
    description="Returns lists of missing indices and constraints."
)
async def get_missing_elements(
    validator: SchemaValidator = Depends(get_validator)
) -> dict:
    """
    Get missing schema elements.
    
    Returns specific lists of which indices and constraints are missing
    from the database and need to be created.
    
    Returns:
        Dict with missing_indices and missing_constraints lists
    """
    try:
        missing_indices = validator.get_missing_indices()
        missing_constraints = validator.get_missing_constraints()
        
        return {
            "missing_indices": missing_indices,
            "missing_constraints": missing_constraints,
            "total_missing": len(missing_indices) + len(missing_constraints),
        }
        
    except Exception as e:
        logger.error(f"Error getting missing elements: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get missing elements: {str(e)}"
        )


@router.get(
    "/migration-script",
    summary="Generate migration script",
    description="Generates a Cypher migration script to align the database with the expected schema."
)
async def get_migration_script(
    validator: SchemaValidator = Depends(get_validator)
) -> dict:
    """
    Generate migration script for schema alignment.
    
    Returns Cypher statements that would create any missing indices
    and constraints. All statements use IF NOT EXISTS for idempotency.
    
    Returns:
        Dict with script content
    """
    try:
        script = validator.generate_migration_script()
        
        return {
            "script": script,
            "generated_at": datetime.utcnow().isoformat(),
        }
        
    except Exception as e:
        logger.error(f"Error generating migration script: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate migration script: {str(e)}"
        )


@router.post(
    "/migrate",
    response_model=MigrationResult,
    summary="Run schema migration",
    description="Runs migration to create missing schema elements. Defaults to dry_run=True for safety."
)
async def run_migration(
    dry_run: bool = Query(
        True,
        description="If True, only shows what would be done without making changes"
    ),
    validator: SchemaValidator = Depends(get_validator)
) -> MigrationResult:
    """
    Run schema migration.
    
    Creates any missing indices and constraints to align the database
    with the canonical schema definition.
    
    IMPORTANT: dry_run defaults to True for safety. Set to False to
    actually execute the migration.
    
    Args:
        dry_run: If True (default), only show what would be done
        
    Returns:
        MigrationResult with execution details
        
    Raises:
        HTTPException 503: If Neo4j connection is not available
        HTTPException 500: If migration fails
    """
    try:
        if dry_run:
            logger.info("Running migration in dry-run mode")
        else:
            logger.info("Running migration (LIVE)")
        
        result = validator.run_migration(dry_run=dry_run)
        
        if not result.success and not dry_run:
            logger.error(f"Migration failed: {result.errors}")
        elif not dry_run:
            logger.info(
                f"Migration complete: {result.statements_executed} statements executed"
            )
        
        return result
        
    except Exception as e:
        logger.error(f"Migration error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Migration failed: {str(e)}"
        )


@router.get(
    "/health",
    summary="Schema health check",
    description="Quick health check for schema validation."
)
async def schema_health_check() -> dict:
    """
    Quick schema health check.
    
    Returns basic information about schema validity without
    full validation details.
    
    Returns:
        Dict with health status
    """
    try:
        if neo4j_driver is None:
            return {
                "healthy": False,
                "neo4j_connected": False,
                "message": "Neo4j driver not initialized"
            }
        
        validator = SchemaValidator(neo4j_driver)
        status = validator.get_schema_status()
        
        return {
            "healthy": status.is_valid,
            "neo4j_connected": True,
            "schema_version": status.schema_version,
            "indices_ready": status.indices_ready,
            "constraints_ready": status.constraints_ready,
            "missing_count": status.missing_count,
        }
        
    except Exception as e:
        return {
            "healthy": False,
            "neo4j_connected": False,
            "message": str(e)
        }
