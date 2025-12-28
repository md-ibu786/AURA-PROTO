"""
Hierarchy data access helpers (single-query per call)
"""
try:
    from db import execute_query, execute_one
except ImportError:
    from api.db import execute_query, execute_one


def get_all_departments():
    query = "SELECT id, name as label, 'department' as type FROM departments ORDER BY name"
    return execute_query(query)


def get_semesters_by_department(department_id: int):
    query = "SELECT id, semester_number || ' - ' || name as label, 'semester' as type FROM semesters WHERE department_id = ? ORDER BY semester_number"
    return execute_query(query, (department_id,))


def get_subjects_by_semester(semester_id: int):
    query = "SELECT id, code || ' - ' || name as label, 'subject' as type FROM subjects WHERE semester_id = ? ORDER BY name"
    return execute_query(query, (semester_id,))


def get_modules_by_subject(subject_id: int):
    query = "SELECT id, 'Module ' || module_number || ' - ' || name as label, 'module' as type FROM modules WHERE subject_id = ? ORDER BY module_number"
    return execute_query(query, (subject_id,))


def validate_hierarchy(module_id: int, subject_id: int, semester_id: int, department_id: int) -> bool:
    query = """
        SELECT 1 FROM modules m
        JOIN subjects s ON m.subject_id = s.id
        JOIN semesters sem ON s.semester_id = sem.id
        JOIN departments d ON sem.department_id = d.id
        WHERE m.id = ?
          AND s.id = ?
          AND sem.id = ?
          AND d.id = ?
    """
    return execute_one(query, (module_id, subject_id, semester_id, department_id)) is not None
