"""
neo4j_schema.py
Unified Neo4j schema definition for AURA platform (NOTES-MANAGER + CHAT)

This file defines the canonical schema that both applications use.
Any schema changes should be made here and migrated to both apps.
Provides single source of truth for Neo4j node types, relationships,
properties, indices, and constraints.

@see: AURA-CHAT/backend/schemas/neo4j_schema.py (should be identical)
@see: api/neo4j_config.py - Driver initialization
@see: api/schema_validator.py - Schema validation utilities
@note: Keep this file in sync across both applications
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ============================================================================
# NODE TYPES
# ============================================================================

class NodeType(str, Enum):
    """
    Canonical node types for the AURA knowledge graph.
    
    Organized by category:
    - Document structure: DOCUMENT, PARENT_CHUNK, CHUNK
    - Entities: TOPIC, CONCEPT, METHODOLOGY, FINDING, DEFINITION, CITATION
    - Organization: MODULE
    - Sessions: STUDY_SESSION, MESSAGE (AURA-CHAT specific)
    - Feedback: FEEDBACK
    """
    # Document structure
    DOCUMENT = "Document"
    PARENT_CHUNK = "ParentChunk"
    CHUNK = "Chunk"
    
    # Entities (extracted from documents)
    TOPIC = "Topic"
    CONCEPT = "Concept"
    METHODOLOGY = "Methodology"
    FINDING = "Finding"
    DEFINITION = "Definition"
    CITATION = "Citation"
    
    # Organization
    MODULE = "Module"
    
    # Sessions (AURA-CHAT specific but shared schema)
    STUDY_SESSION = "StudySession"
    MESSAGE = "Message"
    
    # Feedback
    FEEDBACK = "Feedback"


# ============================================================================
# RELATIONSHIP TYPES
# ============================================================================

class RelationshipType(str, Enum):
    """
    Canonical relationship types for the AURA knowledge graph.
    
    Organized by category:
    - Document structure: HAS_CHUNK, HAS_PARENT_CHUNK, HAS_CHILD, BELONGS_TO_MODULE
    - Entity containment: CONTAINS_ENTITY, ADDRESSES_TOPIC
    - Entity-to-entity semantic: DEFINES, DEPENDS_ON, USES, etc.
    - Session relationships: HAS_MESSAGE, STUDIES
    - Feedback: FEEDBACK_FOR
    """
    # Document structure relationships
    HAS_CHUNK = "HAS_CHUNK"
    HAS_PARENT_CHUNK = "HAS_PARENT_CHUNK"
    HAS_CHILD = "HAS_CHILD"
    BELONGS_TO_MODULE = "BELONGS_TO_MODULE"
    
    # Entity containment relationships
    CONTAINS_ENTITY = "CONTAINS_ENTITY"
    ADDRESSES_TOPIC = "ADDRESSES_TOPIC"
    MENTIONS_CONCEPT = "MENTIONS_CONCEPT"
    USES_METHODOLOGY = "USES_METHODOLOGY"
    SUPPORTS = "SUPPORTS"
    
    # Entity-to-entity semantic relationships (9 types from Phase 09)
    DEFINES = "DEFINES"
    DEPENDS_ON = "DEPENDS_ON"
    USES = "USES"
    SUPPORTS_ENTITY = "SUPPORTS"  # Between entities (not doc->finding)
    CONTRADICTS = "CONTRADICTS"
    EXTENDS = "EXTENDS"
    IMPLEMENTS = "IMPLEMENTS"
    REFERENCES = "REFERENCES"
    RELATED_TO = "RELATED_TO"
    
    # Session relationships (AURA-CHAT)
    HAS_MESSAGE = "HAS_MESSAGE"
    STUDIES = "STUDIES"
    
    # Feedback relationships
    FEEDBACK_FOR = "FEEDBACK_FOR"


# ============================================================================
# ENTITY-ENTITY RELATIONSHIP TYPES (SUBSET FOR KG EXTRACTION)
# ============================================================================

ENTITY_ENTITY_RELATIONSHIPS: List[str] = [
    "DEFINES",
    "DEPENDS_ON",
    "USES",
    "SUPPORTS",
    "CONTRADICTS",
    "EXTENDS",
    "IMPLEMENTS",
    "REFERENCES",
    "RELATED_TO",
]


# ============================================================================
# NODE PROPERTY DEFINITIONS
# ============================================================================

NODE_PROPERTIES: Dict[NodeType, List[str]] = {
    NodeType.DOCUMENT: [
        "id",                # String! - Unique document identifier
        "title",             # String! - Document title
        "content",           # String - Full text content
        "content_type",      # String - MIME type (application/pdf, etc.)
        "original_filename", # String - Original upload filename
        "file_type",         # String - Extension (pdf, docx, txt)
        "file_path",         # String - Storage path
        "source_path",       # String - Alternative path reference
        "module_id",         # String - Associated module ID
        "year",              # Integer - Publication year
        "authors",           # String - Authors list
        "url",               # String - Source URL if applicable
        "upload_date",       # DateTime - When uploaded
        "format",            # String - Document format
        "created_at",        # DateTime - Creation timestamp
        "updated_at",        # DateTime - Last update timestamp
        "processed_at",      # DateTime - When KG processing completed
        "status",            # String - Processing status
        "word_count",        # Integer - Total word count
        "chunk_count",       # Integer - Number of chunks created
        "embedding",         # [Float] - 768-dim document embedding
    ],
    NodeType.PARENT_CHUNK: [
        "id",           # String! - Unique parent chunk identifier
        "document_id",  # String! - Parent document ID
        "module_id",    # String - Associated module ID
        "text",         # String! - Chunk text content
        "tokens",       # Integer - Token count
        "position",     # Integer - Position in document
        "embedding",    # [Float]! - 768-dim embedding
        "created_at",   # DateTime! - Creation timestamp
    ],
    NodeType.CHUNK: [
        "id",              # String! - Unique chunk identifier
        "document_id",     # String! - Parent document ID
        "module_id",       # String - Associated module ID
        "parent_chunk_id", # String - Parent chunk ID for hierarchical
        "text",            # String! - Chunk text content
        "tokens",          # Integer - Token count
        "position",        # Integer - Position in document
        "embedding",       # [Float]! - 768-dim embedding
        "created_at",      # DateTime! - Creation timestamp
    ],
    NodeType.TOPIC: [
        "id",            # String! - Unique topic identifier
        "name",          # String! - Topic name
        "definition",    # String - Topic definition
        "category",      # String - Topic category
        "module_id",     # String - Associated module ID
        "embedding",     # [Float]! - 768-dim embedding
        "confidence",    # Float - Extraction confidence
        "mention_count", # Integer - Number of mentions
        "created_at",    # DateTime! - Creation timestamp
    ],
    NodeType.CONCEPT: [
        "id",            # String! - Unique concept identifier
        "name",          # String! - Concept name
        "definition",    # String - Concept definition
        "category",      # String - Concept category
        "module_id",     # String - Associated module ID
        "embedding",     # [Float]! - 768-dim embedding
        "confidence",    # Float - Extraction confidence
        "mention_count", # Integer - Number of mentions
        "created_at",    # DateTime! - Creation timestamp
    ],
    NodeType.METHODOLOGY: [
        "id",            # String! - Unique methodology identifier
        "name",          # String! - Methodology name
        "definition",    # String - Methodology description
        "category",      # String - Methodology category
        "module_id",     # String - Associated module ID
        "embedding",     # [Float]! - 768-dim embedding
        "confidence",    # Float - Extraction confidence
        "mention_count", # Integer - Number of mentions
        "created_at",    # DateTime! - Creation timestamp
    ],
    NodeType.FINDING: [
        "id",            # String! - Unique finding identifier
        "name",          # String! - Finding name/title
        "definition",    # String - Finding description
        "category",      # String - Finding category
        "module_id",     # String - Associated module ID
        "embedding",     # [Float]! - 768-dim embedding
        "confidence",    # Float - Extraction confidence
        "mention_count", # Integer - Number of mentions
        "created_at",    # DateTime! - Creation timestamp
    ],
    NodeType.DEFINITION: [
        "id",            # String! - Unique definition identifier
        "term",          # String! - Term being defined
        "definition",    # String! - The definition text
        "module_id",     # String - Associated module ID
        "embedding",     # [Float] - 768-dim embedding
        "created_at",    # DateTime! - Creation timestamp
    ],
    NodeType.CITATION: [
        "id",            # String! - Unique citation identifier
        "text",          # String! - Citation text
        "authors",       # String - Cited authors
        "year",          # Integer - Citation year
        "source",        # String - Source publication
        "module_id",     # String - Associated module ID
        "created_at",    # DateTime! - Creation timestamp
    ],
    NodeType.MODULE: [
        "id",           # String! - Unique module identifier (e.g., "CS101")
        "code",         # String! - Module code
        "name",         # String! - Module name
        "description",  # String - Module description
        "department",   # String - Department name
        "semester",     # String - Semester (e.g., "Spring 2026")
        "kg_status",    # String - KG processing status
        "published_at", # DateTime - When published
        "created_at",   # DateTime! - Creation timestamp
        "updated_at",   # DateTime - Last update timestamp
    ],
    NodeType.STUDY_SESSION: [
        "id",            # String! - Unique session identifier
        "title",         # String - Session title
        "module_ids",    # [String] - Associated module IDs
        "user_id",       # String - User identifier
        "status",        # String - Session status
        "message_count", # Integer - Number of messages
        "created_at",    # DateTime! - Creation timestamp
        "updated_at",    # DateTime - Last update timestamp
    ],
    NodeType.MESSAGE: [
        "id",          # String! - Unique message identifier
        "session_id",  # String! - Parent session ID
        "role",        # String! - "user" or "assistant"
        "content",     # String! - Message content
        "created_at",  # DateTime! - Creation timestamp
        "model_used",  # String - AI model used for response
        "sources",     # [String] - Source document IDs
        "token_count", # Integer - Token count
    ],
    NodeType.FEEDBACK: [
        "id",           # String! - Unique feedback identifier
        "message_id",   # String! - Related message ID
        "rating",       # Float - User rating
        "helpful",      # Boolean - Was it helpful
        "comment",      # String - User comment
        "created_at",   # DateTime! - Creation timestamp
    ],
}


# ============================================================================
# VECTOR INDEX DEFINITIONS
# ============================================================================

class VectorIndexDefinition(BaseModel):
    """Definition for a Neo4j vector index."""
    name: str
    node_type: str
    property: str
    dimensions: int = 768
    similarity_function: str = "cosine"
    hnsw_m: int = 16
    hnsw_ef_construction: int = 200


VECTOR_INDICES: List[VectorIndexDefinition] = [
    VectorIndexDefinition(
        name="document_vector_index",
        node_type="Document",
        property="embedding",
    ),
    VectorIndexDefinition(
        name="parent_chunk_vector_index",
        node_type="ParentChunk",
        property="embedding",
    ),
    VectorIndexDefinition(
        name="chunk_vector_index",
        node_type="Chunk",
        property="embedding",
    ),
    VectorIndexDefinition(
        name="topic_vector_index",
        node_type="Topic",
        property="embedding",
    ),
    VectorIndexDefinition(
        name="concept_vector_index",
        node_type="Concept",
        property="embedding",
    ),
    VectorIndexDefinition(
        name="methodology_vector_index",
        node_type="Methodology",
        property="embedding",
    ),
    VectorIndexDefinition(
        name="finding_vector_index",
        node_type="Finding",
        property="embedding",
    ),
]


# ============================================================================
# FULLTEXT INDEX DEFINITIONS
# ============================================================================

class FulltextIndexDefinition(BaseModel):
    """Definition for a Neo4j fulltext index."""
    name: str
    node_type: str
    properties: List[str]
    analyzer: str = "english"


FULLTEXT_INDICES: List[FulltextIndexDefinition] = [
    FulltextIndexDefinition(
        name="chunk_fulltext_index",
        node_type="Chunk",
        properties=["text"],
    ),
]


# ============================================================================
# CONSTRAINT DEFINITIONS
# ============================================================================

class ConstraintDefinition(BaseModel):
    """Definition for a Neo4j constraint."""
    name: str
    node_type: str
    property: str
    constraint_type: str = "UNIQUE"


CONSTRAINTS: List[ConstraintDefinition] = [
    ConstraintDefinition(name="document_id_unique", node_type="Document", property="id"),
    ConstraintDefinition(name="parent_chunk_id_unique", node_type="ParentChunk", property="id"),
    ConstraintDefinition(name="chunk_id_unique", node_type="Chunk", property="id"),
    ConstraintDefinition(name="topic_id_unique", node_type="Topic", property="id"),
    ConstraintDefinition(name="concept_id_unique", node_type="Concept", property="id"),
    ConstraintDefinition(name="methodology_id_unique", node_type="Methodology", property="id"),
    ConstraintDefinition(name="finding_id_unique", node_type="Finding", property="id"),
    ConstraintDefinition(name="module_id_unique", node_type="Module", property="id"),
    ConstraintDefinition(name="study_session_id_unique", node_type="StudySession", property="id"),
    ConstraintDefinition(name="message_id_unique", node_type="Message", property="id"),
]


# ============================================================================
# SCHEMA DEFINITION MODEL
# ============================================================================

class SchemaDefinition(BaseModel):
    """Complete schema definition for AURA platform Neo4j database."""
    version: str = "1.0.0"
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    node_types: List[str] = Field(
        default_factory=lambda: [nt.value for nt in NodeType]
    )
    relationship_types: List[str] = Field(
        default_factory=lambda: [rt.value for rt in RelationshipType]
    )
    entity_entity_relationships: List[str] = Field(
        default_factory=lambda: ENTITY_ENTITY_RELATIONSHIPS
    )
    vector_indices: List[VectorIndexDefinition] = Field(
        default_factory=lambda: VECTOR_INDICES
    )
    fulltext_indices: List[FulltextIndexDefinition] = Field(
        default_factory=lambda: FULLTEXT_INDICES
    )
    constraints: List[ConstraintDefinition] = Field(
        default_factory=lambda: CONSTRAINTS
    )

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_schema_definition() -> SchemaDefinition:
    """Get the complete schema definition."""
    return SchemaDefinition()


def get_node_types() -> List[str]:
    """Get all node type names."""
    return [nt.value for nt in NodeType]


def get_relationship_types() -> List[str]:
    """Get all relationship type names."""
    return [rt.value for rt in RelationshipType]


def get_entity_types() -> List[str]:
    """Get entity node types (Topic, Concept, Methodology, Finding)."""
    return [
        NodeType.TOPIC.value,
        NodeType.CONCEPT.value,
        NodeType.METHODOLOGY.value,
        NodeType.FINDING.value,
    ]


def get_vector_index_names() -> List[str]:
    """Get all vector index names."""
    return [vi.name for vi in VECTOR_INDICES]


def get_fulltext_index_names() -> List[str]:
    """Get all fulltext index names."""
    return [fi.name for fi in FULLTEXT_INDICES]


def get_constraint_names() -> List[str]:
    """Get all constraint names."""
    return [c.name for c in CONSTRAINTS]


def get_properties_for_node(node_type: NodeType) -> List[str]:
    """Get property names for a specific node type."""
    return NODE_PROPERTIES.get(node_type, [])


def generate_vector_index_cypher(index_def: VectorIndexDefinition) -> str:
    """Generate Cypher for creating a vector index."""
    return f"""
    CREATE VECTOR INDEX {index_def.name} IF NOT EXISTS
    FOR (n:{index_def.node_type}) ON (n.{index_def.property})
    OPTIONS {{indexConfig: {{
        `vector.dimensions`: {index_def.dimensions},
        `vector.similarity_function`: '{index_def.similarity_function}',
        `vector.hnsw.m`: {index_def.hnsw_m},
        `vector.hnsw.ef_construction`: {index_def.hnsw_ef_construction}
    }} }}
    """


def generate_fulltext_index_cypher(index_def: FulltextIndexDefinition) -> str:
    """Generate Cypher for creating a fulltext index."""
    properties = ", ".join([f"n.{p}" for p in index_def.properties])
    return f"""
    CREATE FULLTEXT INDEX {index_def.name} IF NOT EXISTS
    FOR (n:{index_def.node_type}) ON EACH [{properties}]
    OPTIONS {{indexConfig: {{'fulltext.analyzer': '{index_def.analyzer}'}}}}
    """


def generate_constraint_cypher(constraint_def: ConstraintDefinition) -> str:
    """Generate Cypher for creating a constraint."""
    return f"""
    CREATE CONSTRAINT {constraint_def.name} IF NOT EXISTS
    FOR (n:{constraint_def.node_type}) REQUIRE n.{constraint_def.property} IS UNIQUE
    """


def generate_all_indices_cypher() -> List[str]:
    """Generate Cypher statements for all indices."""
    statements = []
    for vi in VECTOR_INDICES:
        statements.append(generate_vector_index_cypher(vi))
    for fi in FULLTEXT_INDICES:
        statements.append(generate_fulltext_index_cypher(fi))
    return statements


def generate_all_constraints_cypher() -> List[str]:
    """Generate Cypher statements for all constraints."""
    return [generate_constraint_cypher(c) for c in CONSTRAINTS]
