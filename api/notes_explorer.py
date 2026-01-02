"""
Explorer-style endpoints that mirror the hierarchy for staff browsing
Each endpoint performs exactly one SQL query and returns minimal metadata.
"""
from fastapi import APIRouter, HTTPException
try:
    from db import execute_query, execute_one, execute_write, PLACEHOLDER
except ImportError:
    from api.db import execute_query, execute_one, execute_write, PLACEHOLDER

router = APIRouter(prefix="/notes", tags=["Notes Explorer"])

@router.get("/{department_id}")
def notes_by_department(department_id: int):
    # Return semesters for a department
    query = f"SELECT id, semester_number || ' - ' || name as label, 'semester' as type FROM semesters WHERE department_id = {PLACEHOLDER} ORDER BY semester_number"
    return execute_query(query, (department_id,)) or []

@router.get("/{department_id}/{semester_id}")
def notes_by_semester(department_id: int, semester_id: int):
    # Ensure the semester belongs to the department - single query optional; but here we return subjects
    query = f"SELECT id, code || ' - ' || name as label, 'subject' as type FROM subjects WHERE semester_id = {PLACEHOLDER} ORDER BY name"
    return execute_query(query, (semester_id,)) or []

@router.get("/{department_id}/{semester_id}/{subject_id}")
def notes_by_subject(department_id: int, semester_id: int, subject_id: int):
    query = f"SELECT id, 'Module ' || module_number || ' - ' || name as label, 'module' as type FROM modules WHERE subject_id = {PLACEHOLDER} ORDER BY module_number"
    return execute_query(query, (subject_id,)) or []

@router.get("/{department_id}/{semester_id}/{subject_id}/{module_id}")
def notes_by_module(department_id: int, semester_id: int, subject_id: int, module_id: int, limit: int = 20, offset: int = 0):
    # Return paginated notes for a module along with total count
    count_q = f"SELECT COUNT(*) as total FROM notes WHERE module_id = {PLACEHOLDER}"
    total_row = execute_one(count_q, (module_id,))
    total = total_row['total'] if total_row else 0

    query = f"SELECT id, title as label, 'note' as type, pdf_url, created_at FROM notes WHERE module_id = {PLACEHOLDER} ORDER BY created_at DESC LIMIT {PLACEHOLDER} OFFSET {PLACEHOLDER}"
    notes = execute_query(query, (module_id, limit, offset)) or []

    return {"notes": notes, "total": total}
