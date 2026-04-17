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

try:
    from config import db
except (ImportError, ModuleNotFoundError):
    try:
        from .config import db
    except (ImportError, ModuleNotFoundError):
        from api.config import db


def _merge_doc(doc: Any) -> Dict[str, Any]:
    """Merge doc.id and doc.to_dict() into a single dict safely."""
    data = doc.to_dict() or {}
    result = dict(data)
    result["id"] = doc.id
    return result


def get_all_departments() -> List[Dict[str, Any]]:
    docs = db.collection("departments").order_by("name").stream()
    result = []
    for doc in docs:
        entry = _merge_doc(doc)
        entry["label"] = doc.get("name")
        entry["type"] = "department"
        result.append(entry)
    return result


def get_semesters_by_department(department_id: str) -> List[Dict[str, Any]]:
    ref = db.collection("departments").document(department_id)
    doc = ref.get()
    if not doc.exists:
        return []

    docs = ref.collection("semesters").order_by("semester_number").stream()
    result = []
    for d in docs:
        entry = _merge_doc(d)
        entry["label"] = f"{d.get('semester_number')} - {d.get('name')}"
        entry["type"] = "semester"
        result.append(entry)
    return result


def get_subjects_by_semester(
    semester_id: str, department_id: Optional[str] = None
) -> List[Dict[str, Any]]:
    if department_id:
        semester_ref = (
            db.collection("departments")
            .document(department_id)
            .collection("semesters")
            .document(semester_id)
        )
        subjects = semester_ref.collection("subjects").order_by("name").stream()
        result = []
        for d in subjects:
            entry = _merge_doc(d)
            entry["label"] = f"{d.get('code')} - {d.get('name')}"
            entry["type"] = "subject"
            result.append(entry)
        return result

    docs = list(
        db.collection_group("semesters").where("id", "==", semester_id).stream()
    )
    if not docs:
        return []

    semester_ref = docs[0].reference
    subjects = semester_ref.collection("subjects").order_by("name").stream()
    result = []
    for d in subjects:
        entry = _merge_doc(d)
        entry["label"] = f"{d.get('code')} - {d.get('name')}"
        entry["type"] = "subject"
        result.append(entry)
    return result


def get_modules_by_subject(
    subject_id: str,
    department_id: Optional[str] = None,
    semester_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    if department_id and semester_id:
        subject_ref = (
            db.collection("departments")
            .document(department_id)
            .collection("semesters")
            .document(semester_id)
            .collection("subjects")
            .document(subject_id)
        )
        modules = subject_ref.collection("modules").order_by("module_number").stream()
        result = []
        for d in modules:
            entry = _merge_doc(d)
            entry["label"] = f"Module {d.get('module_number')} - {d.get('name')}"
            entry["type"] = "module"
            result.append(entry)
        return result

    docs = list(db.collection_group("subjects").where("id", "==", subject_id).stream())
    if not docs:
        return []

    subject_ref = docs[0].reference
    modules = subject_ref.collection("modules").order_by("module_number").stream()
    result = []
    for d in modules:
        entry = _merge_doc(d)
        entry["label"] = f"Module {d.get('module_number')} - {d.get('name')}"
        entry["type"] = "module"
        result.append(entry)
    return result


def validate_hierarchy(
    module_id: str, subject_id: str, semester_id: str, department_id: str
) -> bool:
    """
    Verify that the module resides under subject -> semester -> department.
    In Firestore, this is checking the path:
    departments/{dept}/semesters/{sem}/subjects/{subj}/modules/{mod}
    """
    path = (
        f"departments/{department_id}/semesters/{semester_id}"
        f"/subjects/{subject_id}/modules/{module_id}"
    )
    doc = db.document(path).get()
    return doc.exists
