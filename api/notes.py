"""
Notes storage helpers using Firestore
"""
from google.cloud import firestore
import datetime
try:
    from config import db
except (ImportError, ModuleNotFoundError):
    try:
        from .config import db
    except (ImportError, ModuleNotFoundError):
        from api.config import db

def create_note_record(module_id: str, title: str, pdf_url: str):
    """Create a note record in Firestore under the specified module."""
    # Find module doc ref
    docs = list(db.collection_group('modules').where(firestore.FieldPath.document_id(), '==', module_id).stream())
    if not docs:
        return None
    
    module_ref = docs[0].reference
    new_note_ref = module_ref.collection('notes').document()
    
    data = {
        'id': new_note_ref.id,
        'title': title,
        'pdf_url': pdf_url,
        'created_at': datetime.datetime.now().isoformat(),
        'module_id': module_id  # Keep reference for easier finding if needed
    }
    
    new_note_ref.set(data)
    return data
