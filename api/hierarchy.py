"""
Hierarchy data access helpers (single-query per call) using Firestore.
"""
from typing import List, Dict, Any, Optional
from google.cloud import firestore
try:
    from config import db
except (ImportError, ModuleNotFoundError):
    try:
        from .config import db
    except (ImportError, ModuleNotFoundError):
        from api.config import db

def get_all_departments() -> List[Dict[str, Any]]:
    docs = db.collection('departments').order_by('name').stream()
    return [{'id': doc.id, 'label': doc.get('name'), 'type': 'department', **doc.to_dict()} for doc in docs]

def get_semesters_by_department(department_id: str) -> List[Dict[str, Any]]:
    # Firestore: subcollection 'semesters'
    ref = db.collection('departments').document(department_id)
    if not ref.get().exists:
        return []
    
    docs = ref.collection('semesters').order_by('semester_number').stream()
    return [{'id': doc.id, 'label': f"{doc.get('semester_number')} - {doc.get('name')}", 'type': 'semester', **doc.to_dict()} for doc in docs]

def get_subjects_by_semester(semester_id: str) -> List[Dict[str, Any]]:
    # Need to find the semester doc to get its subjects subcollection.
    # Since we can't easily find parent from just ID, we assume known path or use Collection Group if ID is unique.
    # But `hierarchy.py` helpers are typically "drill down".
    # Problem: `semester_id` alone isn't enough for direct path unless we map it.
    # For now, we use Collection Group Query to find the semester by ID.
    
    # Efficient way: Assume unique IDs for semesters across the board (they are auto-generated).
    docs = list(db.collection_group('semesters').where('id', '==', semester_id).stream())
    if not docs:
        return []
    
    semester_ref = docs[0].reference
    subjects = semester_ref.collection('subjects').order_by('name').stream()
    return [{'id': doc.id, 'label': f"{doc.get('code')} - {doc.get('name')}", 'type': 'subject', **doc.to_dict()} for doc in subjects]

def get_modules_by_subject(subject_id: str) -> List[Dict[str, Any]]:
    docs = list(db.collection_group('subjects').where('id', '==', subject_id).stream())
    if not docs:
        return []
    
    subject_ref = docs[0].reference
    modules = subject_ref.collection('modules').order_by('module_number').stream()
    return [{'id': doc.id, 'label': f"Module {doc.get('module_number')} - {doc.get('name')}", 'type': 'module', **doc.to_dict()} for doc in modules]


def validate_hierarchy(module_id: str, subject_id: str, semester_id: str, department_id: str) -> bool:
    """
    Verify that the module resides under subject -> semester -> department.
    In Firestore, this is checking the path:
    departments/{dept}/semesters/{sem}/subjects/{subj}/modules/{mod}
    """
    path = f"departments/{department_id}/semesters/{semester_id}/subjects/{subject_id}/modules/{module_id}"
    doc = db.document(path).get()
    return doc.exists
