"""
Notes storage helpers using Firestore
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

