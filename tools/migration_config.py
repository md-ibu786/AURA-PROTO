"""
============================================================================
FILE: migration_config.py
LOCATION: tools/migration_config.py
============================================================================

PURPOSE:
    Configuration and mappings for Firestore data migration from mock_db.json

ROLE IN PROJECT:
    Defines migration settings, dependency order, field transformations,
    and defaults used by tools/seed_firestore.py

KEY COMPONENTS:
    - MIGRATION_SETTINGS: Batch size, retries, schema version
    - COLLECTION_ORDER: Dependency-aware migration order
    - FIELD_MAPPINGS: Drop/rename/add field rules per collection
    - REQUIRED_FIELDS: Required fields for validation
    - DEFAULT_VALUES: Default values for optional fields

DEPENDENCIES:
    - External: None
    - Internal: None

USAGE:
    from tools.migration_config import MIGRATION_SETTINGS
============================================================================
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


TransformFunc = Callable[[Dict[str, Any], "TransformContext"], Any]


@dataclass(frozen=True)
class TransformContext:
    """Context for field transformation functions."""
    collection_type: str
    collection_path: str
    doc_id: str
    path_segments: List[str]


def utc_now_iso() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.utcnow().isoformat()


def get_path_id(
    path_segments: List[str],
    collection_name: str,
) -> Optional[str]:
    """Return the document ID that follows collection_name in path."""
    try:
        index = path_segments.index(collection_name)
    except ValueError:
        return None
    if index + 1 >= len(path_segments):
        return None
    return path_segments[index + 1]


MIGRATION_SETTINGS = {
    "batch_size": 500,
    "max_retries": 3,
    "rate_limit": 500,
    "schema_version": 1,
}

# Collection migration order (dependencies first)
COLLECTION_ORDER = [
    "users",
    "departments",
    "semesters",
    "subjects",
    "modules",
    "notes",
]

# Collections that should store an explicit id field
COLLECTIONS_WITH_ID_FIELD = [
    "departments",
    "semesters",
    "subjects",
    "modules",
    "notes",
]

# Field mappings for transformations
FIELD_MAPPINGS = {
    "users": {
        "drop": ["password"],
        "rename": {},
        "add": {
            "uid": lambda _doc, ctx: ctx.doc_id,
        },
    },
    "departments": {
        "drop": [],
        "rename": {},
        "add": {},
    },
    "semesters": {
        "drop": [],
        "rename": {},
        "add": {},
    },
    "subjects": {
        "drop": [],
        "rename": {},
        "add": {},
    },
    "modules": {
        "drop": [],
        "rename": {},
        "add": {},
    },
    "notes": {
        "drop": [],
        "rename": {},
        "add": {},
    },
}

# Required fields validation
REQUIRED_FIELDS = {
    "users": ["uid", "email", "role", "status"],
    "departments": ["name", "code"],
    "semesters": ["name", "semester_number", "department_id"],
    "subjects": ["name", "code", "semester_id"],
    "modules": ["name", "module_number", "subject_id"],
    "notes": ["title", "pdf_url", "module_id"],
}

# Default values for optional fields
DEFAULT_VALUES = {
    "users": {
        "status": "active",
        "subjectIds": [],
        "departmentId": None,
        "createdAt": utc_now_iso,
        "updatedAt": utc_now_iso,
    },
}


def get_collection_type(collection_path: str) -> Optional[str]:
    """Determine collection type based on a Firestore collection path."""
    if collection_path == "users":
        return "users"
    if collection_path == "departments":
        return "departments"

    segments = collection_path.split("/")
    if len(segments) == 3 and segments[2] == "semesters":
        return "semesters"
    if len(segments) == 5 and segments[4] == "subjects":
        return "subjects"
    if len(segments) == 7 and segments[6] == "modules":
        return "modules"
    if len(segments) == 9 and segments[8] == "notes":
        return "notes"

    return None


def get_collection_priority(collection_type: str) -> int:
    """Return the sorting priority for a collection type."""
    try:
        return COLLECTION_ORDER.index(collection_type)
    except ValueError:
        return len(COLLECTION_ORDER)


def get_required_fields(collection_type: str) -> List[str]:
    """Return required fields for a collection type."""
    return REQUIRED_FIELDS.get(collection_type, [])


def get_default_values(collection_type: str) -> Dict[str, Any]:
    """Return default values for a collection type."""
    defaults = DEFAULT_VALUES.get(collection_type, {})
    evaluated: Dict[str, Any] = {}
    for key, value in defaults.items():
        evaluated[key] = value() if callable(value) else value
    return evaluated
