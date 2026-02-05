"""
============================================================================
FILE: hierarchy.py
LOCATION: api/hierarchy.py
============================================================================

PURPOSE:
    Provides read-only data access helpers for the educational hierarchy.
    Retrieves departments, semesters, subjects, and modules from Firestore
    using efficient single-query patterns.

ROLE IN PROJECT:
    This is the read layer for hierarchy navigation. Used by:
    - main.py for legacy drill-down endpoints (/departments, /semesters/...)
    - Other modules needing to validate or retrieve hierarchy data
    
    Note: CRUD operations are in hierarchy_crud.py; this file is READ-ONLY.

KEY COMPONENTS:
    - get_all_departments(): Get all top-level departments
    - get_semesters_by_department(dept_id): Get semesters under a department
    - get_subjects_by_semester(sem_id): Get subjects under a semester
    - get_modules_by_subject(subj_id): Get modules under a subject
    - validate_hierarchy(): Verify a complete hierarchy path exists

DATA STRUCTURE (Firestore Nested Collections):
    departments/{dept_id}
        └── semesters/{sem_id}
            └── subjects/{subj_id}
                └── modules/{mod_id}
                    └── notes/{note_id}

DEPENDENCIES:
    - External: google-cloud-firestore
    - Internal: config.py (db client)

USAGE:
    from hierarchy import get_all_departments, validate_hierarchy
    
    depts = get_all_departments()  # Returns list of {id, label, type, ...}
    is_valid = validate_hierarchy(mod_id, subj_id, sem_id, dept_id)
============================================================================
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

def get_subjects_by_semester(semester_id: str, department_id: Optional[str] = None) -> List[Dict[str, Any]]:
    # Firestore: subcollection 'subjects'
    # If department_id is provided, use direct path for efficiency and to avoid index requirements
    if department_id:
        semester_ref = db.collection('departments').document(department_id).collection('semesters').document(semester_id)
        subjects = semester_ref.collection('subjects').order_by('name').stream()
        return [{'id': doc.id, 'label': f"{doc.get('code')} - {doc.get('name')}", 'type': 'subject', **doc.to_dict()} for doc in subjects]

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

def get_modules_by_subject(subject_id: str, department_id: Optional[str] = None, semester_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if department_id and semester_id:
        subject_ref = db.collection('departments').document(department_id)\
            .collection('semesters').document(semester_id)\
            .collection('subjects').document(subject_id)
        modules = subject_ref.collection('modules').order_by('module_number').stream()
        return [{'id': doc.id, 'label': f"Module {doc.get('module_number')} - {doc.get('name')}", 'type': 'module', **doc.to_dict()} for doc in modules]

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
