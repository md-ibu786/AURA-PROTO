"""
============================================================================
FILE: notes.py
LOCATION: api/notes.py
============================================================================

PURPOSE:
    Provides helper functions for creating note records in Firestore.
    Handles duplicate title detection and generates unique names with
    numbered suffixes when conflicts occur.

ROLE IN PROJECT:
    This module is used by:
    - main.py (create_note_endpoint) for direct note creation
    - audio_processing.py for saving notes after PDF generation
    - upload-document endpoint for document uploads

    Notes are the leaf nodes in the hierarchy (stored under modules).

KEY COMPONENTS:
    - get_next_available_number(numbers): Find next sequential number
    - get_unique_name(names, base_name): Generate unique name with (N) suffix
    - create_note_record(module_id, title, pdf_url): Create note in Firestore

DATA STRUCTURE:
    Each note document contains:
    - id: Auto-generated Firestore document ID
    - title: Display title (unique within module, auto-suffixed if duplicate)
    - pdf_url: Path to PDF/document file (e.g., /pdfs/filename.pdf)
    - created_at: ISO timestamp
    - module_id: Reference to parent module
    - subjectId: Parent subject ID (derived from module path)
    - departmentId: Parent department ID (derived from module path)

DEPENDENCIES:
    - External: google-cloud-firestore
    - Internal: config.py (db client)

USAGE:
    from notes import create_note_record

    note = create_note_record(
        module_id="abc123",
        title="Lecture Notes Week 1",
        pdf_url="/pdfs/lecture_notes_week_1_1704067200.pdf",
        subject_id="subj_456",
        department_id="dept_123",
    )
    # Returns: {'id': '...', 'title': '...', 'pdf_url': '...', ...}
============================================================================
"""

from google.cloud import firestore
from google.cloud.firestore import FieldFilter
import datetime
from typing import Optional, Sequence

try:
    from config import db
except (ImportError, ModuleNotFoundError):
    try:
        from .config import db
    except (ImportError, ModuleNotFoundError):
        from api.config import db

try:
    from utils import get_next_available_number, get_unique_name
except (ImportError, ModuleNotFoundError):
    from api.utils import get_next_available_number, get_unique_name


def _get_path_id(
    path_segments: Sequence[str],
    collection_name: str,
) -> Optional[str]:
    """Get the document ID that follows a collection name in a path."""
    try:
        index = path_segments.index(collection_name)
    except ValueError:
        return None
    if index + 1 >= len(path_segments):
        return None
    return path_segments[index + 1]


def _extract_hierarchy_ids(
    module_ref: firestore.BaseDocumentReference,
) -> tuple[Optional[str], Optional[str]]:
    """Extract subject and department IDs from a module reference path."""
    path_segments = module_ref.path.split("/")
    subject_id = _get_path_id(path_segments, "subjects")
    department_id = _get_path_id(path_segments, "departments")
    return subject_id, department_id


def create_note_record(
    module_id: str,
    title: str,
    pdf_url: str,
    subject_id: Optional[str] = None,
    department_id: Optional[str] = None,
):
    """Create a note record in Firestore under the specified module."""
    # Find module doc ref
    docs = list(db.collection_group("modules").where(filter=FieldFilter("id", "==", module_id)).stream())
    if not docs:
        return None

    module_ref = docs[0].reference

    derived_subject_id, derived_department_id = _extract_hierarchy_ids(
        docs[0].reference,
    )
    subject_id_to_store = derived_subject_id or subject_id
    department_id_to_store = derived_department_id or department_id

    # Get existing note titles to check for duplicates
    existing_notes = list(module_ref.collection("notes").stream())
    existing_titles = [note.to_dict().get("title", "") for note in existing_notes]

    # Generate unique title if duplicate exists
    unique_title = get_unique_name(existing_titles, title)

    new_note_ref = module_ref.collection("notes").document()

    data = {
        "id": new_note_ref.id,
        "title": unique_title,
        "pdf_url": pdf_url,
        "created_at": datetime.datetime.now().isoformat(),
        "module_id": module_id,  # Keep reference for easier finding if needed
    }

    if subject_id_to_store:
        data["subjectId"] = subject_id_to_store
    if department_id_to_store:
        data["departmentId"] = department_id_to_store

    new_note_ref.set(data)
    return data
