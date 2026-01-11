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

DEPENDENCIES:
    - External: google-cloud-firestore
    - Internal: config.py (db client)

USAGE:
    from notes import create_note_record
    
    note = create_note_record(
        module_id="abc123",
        title="Lecture Notes Week 1",
        pdf_url="/pdfs/lecture_notes_week_1_1704067200.pdf"
    )
    # Returns: {'id': '...', 'title': '...', 'pdf_url': '...', ...}
============================================================================
"""
from google.cloud import firestore
import datetime
import re
try:
    from config import db
except (ImportError, ModuleNotFoundError):
    try:
        from .config import db
    except (ImportError, ModuleNotFoundError):
        from api.config import db


def get_next_available_number(numbers: list[int]) -> int:
    """Find the next available sequential number (max + 1)."""
    if not numbers:
        return 1
    return max(numbers) + 1


def get_unique_name(names: list[str], base_name: str) -> str:
    """Generate unique name with (N) suffix for duplicates."""
    if base_name not in names:
        return base_name
    
    suffix_numbers = [1]
    pattern = re.compile(rf'^{re.escape(base_name)} \((\d+)\)$')
    for n in names:
        match = pattern.match(n)
        if match:
            suffix_numbers.append(int(match.group(1)))
    
    next_suffix = get_next_available_number(suffix_numbers)
    if next_suffix == 1:
        next_suffix = 2
    return f"{base_name} ({next_suffix})"


def create_note_record(module_id: str, title: str, pdf_url: str):
    """Create a note record in Firestore under the specified module."""
    # Find module doc ref
    docs = list(db.collection_group('modules').where('id', '==', module_id).stream())
    if not docs:
        return None
    
    module_ref = docs[0].reference
    
    # Get existing note titles to check for duplicates
    existing_notes = list(module_ref.collection('notes').stream())
    existing_titles = [note.to_dict().get('title', '') for note in existing_notes]
    
    # Generate unique title if duplicate exists
    unique_title = get_unique_name(existing_titles, title)
    
    new_note_ref = module_ref.collection('notes').document()
    
    data = {
        'id': new_note_ref.id,
        'title': unique_title,
        'pdf_url': pdf_url,
        'created_at': datetime.datetime.now().isoformat(),
        'module_id': module_id  # Keep reference for easier finding if needed
    }
    
    new_note_ref.set(data)
    return data

