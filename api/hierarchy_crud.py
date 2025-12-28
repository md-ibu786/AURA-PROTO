"""
CRUD operations for hierarchy tables (departments, semesters, subjects, modules)
and notes (delete/rename only)
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

try:
    from db import execute_query, execute_one
except ImportError:
    from api.db import execute_query, execute_one

router = APIRouter(prefix="/api", tags=["hierarchy-crud"])

# ========== MODELS ==========

class DepartmentCreate(BaseModel):
    name: str
    code: str

class DepartmentUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None

class SemesterCreate(BaseModel):
    department_id: int
    semester_number: int
    name: str

class SemesterUpdate(BaseModel):
    semester_number: Optional[int] = None
    name: Optional[str] = None

class SubjectCreate(BaseModel):
    semester_id: int
    name: str
    code: str

class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None

class ModuleCreate(BaseModel):
    subject_id: int
    module_number: int
    name: str

class ModuleUpdate(BaseModel):
    module_number: Optional[int] = None
    name: Optional[str] = None

class NoteUpdate(BaseModel):
    title: str

# ========== DEPARTMENTS ==========

@router.post("/departments")
def create_department(dept: DepartmentCreate):
    """Create a new department"""
    try:
        query = "INSERT INTO departments (name, code) VALUES (?, ?)"
        execute_query(query, (dept.name, dept.code))
        
        # Get the created department
        new_dept = execute_one("SELECT * FROM departments WHERE code = ?", (dept.code,))
        return {"message": "Department created", "department": new_dept}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating department: {str(e)}")

@router.put("/departments/{dept_id}")
def update_department(dept_id: int, dept: DepartmentUpdate):
    """Update/rename a department"""
    # Check if exists
    existing = execute_one("SELECT * FROM departments WHERE id = ?", (dept_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Department not found")
    
    updates = []
    params = []
    if dept.name is not None:
        updates.append("name = ?")
        params.append(dept.name)
    if dept.code is not None:
        updates.append("code = ?")
        params.append(dept.code)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    params.append(dept_id)
    query = f"UPDATE departments SET {', '.join(updates)} WHERE id = ?"
    
    try:
        execute_query(query, tuple(params))
        updated = execute_one("SELECT * FROM departments WHERE id = ?", (dept_id,))
        return {"message": "Department updated", "department": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating department: {str(e)}")

@router.delete("/departments/{dept_id}")
def delete_department(dept_id: int):
    """Delete a department (cascades to all child records AND deletes files)"""
    import os
    
    # Check if exists
    existing = execute_one("SELECT * FROM departments WHERE id = ?", (dept_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Department not found")
    
    # Count child records
    sem_count = execute_one("SELECT COUNT(*) as cnt FROM semesters WHERE department_id = ?", (dept_id,))
    
    # Cleanup Files: Find all notes under this department
    # Note: Requires a JOIN or multiple queries. With SQLite/Simple schema, we can do a subquery
    notes_to_delete = execute_query("""
        SELECT n.pdf_url 
        FROM notes n
        JOIN modules m ON n.module_id = m.id
        JOIN subjects s ON m.subject_id = s.id
        JOIN semesters sem ON s.semester_id = sem.id
        WHERE sem.department_id = ?
    """, (dept_id,))

    files_deleted = 0
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    for note in notes_to_delete:
        pdf_url = note.get('pdf_url')
        if pdf_url:
            try:
                clean_path = pdf_url.lstrip('/')
                file_path = os.path.join(base_dir, clean_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    files_deleted += 1
            except Exception:
                pass

    try:
        execute_query("DELETE FROM departments WHERE id = ?", (dept_id,))
        return {
            "message": "Department deleted (cascade)",
            "deleted_department": existing,
            "cascaded_semesters": sem_count['cnt'] if sem_count else 0,
            "files_cleaned_up": files_deleted
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error deleting department: {str(e)}")

# ========== SEMESTERS ==========

@router.post("/semesters")
def create_semester(sem: SemesterCreate):
    """Create a new semester"""
    # Verify parent exists
    dept = execute_one("SELECT * FROM departments WHERE id = ?", (sem.department_id,))
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    try:
        query = "INSERT INTO semesters (department_id, semester_number, name) VALUES (?, ?, ?)"
        execute_query(query, (sem.department_id, sem.semester_number, sem.name))
        
        new_sem = execute_one(
            "SELECT * FROM semesters WHERE department_id = ? AND semester_number = ?",
            (sem.department_id, sem.semester_number)
        )
        return {"message": "Semester created", "semester": new_sem}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating semester: {str(e)}")

@router.put("/semesters/{sem_id}")
def update_semester(sem_id: int, sem: SemesterUpdate):
    """Update/rename a semester"""
    existing = execute_one("SELECT * FROM semesters WHERE id = ?", (sem_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Semester not found")
    
    updates = []
    params = []
    if sem.semester_number is not None:
        updates.append("semester_number = ?")
        params.append(sem.semester_number)
    if sem.name is not None:
        updates.append("name = ?")
        params.append(sem.name)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    params.append(sem_id)
    query = f"UPDATE semesters SET {', '.join(updates)} WHERE id = ?"
    
    try:
        execute_query(query, tuple(params))
        updated = execute_one("SELECT * FROM semesters WHERE id = ?", (sem_id,))
        return {"message": "Semester updated", "semester": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating semester: {str(e)}")

@router.delete("/semesters/{sem_id}")
def delete_semester(sem_id: int):
    """Delete a semester (cascades to subjects, modules, notes AND deletes files)"""
    import os
    existing = execute_one("SELECT * FROM semesters WHERE id = ?", (sem_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Semester not found")
    
    subj_count = execute_one("SELECT COUNT(*) as cnt FROM subjects WHERE semester_id = ?", (sem_id,))
    
    # Cleanup Files
    notes_to_delete = execute_query("""
        SELECT n.pdf_url 
        FROM notes n
        JOIN modules m ON n.module_id = m.id
        JOIN subjects s ON m.subject_id = s.id
        WHERE s.semester_id = ?
    """, (sem_id,))

    files_deleted = 0
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    for note in notes_to_delete:
        pdf_url = note.get('pdf_url')
        if pdf_url:
            try:
                clean_path = pdf_url.lstrip('/')
                file_path = os.path.join(base_dir, clean_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    files_deleted += 1
            except Exception:
                pass

    try:
        execute_query("DELETE FROM semesters WHERE id = ?", (sem_id,))
        return {
            "message": "Semester deleted (cascade)",
            "deleted_semester": existing,
            "cascaded_subjects": subj_count['cnt'] if subj_count else 0,
            "files_cleaned_up": files_deleted
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error deleting semester: {str(e)}")

# ========== SUBJECTS ==========

@router.post("/subjects")
def create_subject(subj: SubjectCreate):
    """Create a new subject"""
    sem = execute_one("SELECT * FROM semesters WHERE id = ?", (subj.semester_id,))
    if not sem:
        raise HTTPException(status_code=404, detail="Semester not found")
    
    try:
        query = "INSERT INTO subjects (semester_id, name, code) VALUES (?, ?, ?)"
        execute_query(query, (subj.semester_id, subj.name, subj.code))
        
        new_subj = execute_one(
            "SELECT * FROM subjects WHERE semester_id = ? AND code = ?",
            (subj.semester_id, subj.code)
        )
        return {"message": "Subject created", "subject": new_subj}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating subject: {str(e)}")

@router.put("/subjects/{subj_id}")
def update_subject(subj_id: int, subj: SubjectUpdate):
    """Update/rename a subject"""
    existing = execute_one("SELECT * FROM subjects WHERE id = ?", (subj_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    updates = []
    params = []
    if subj.name is not None:
        updates.append("name = ?")
        params.append(subj.name)
    if subj.code is not None:
        updates.append("code = ?")
        params.append(subj.code)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    params.append(subj_id)
    query = f"UPDATE subjects SET {', '.join(updates)} WHERE id = ?"
    
    try:
        execute_query(query, tuple(params))
        updated = execute_one("SELECT * FROM subjects WHERE id = ?", (subj_id,))
        return {"message": "Subject updated", "subject": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating subject: {str(e)}")

@router.delete("/subjects/{subj_id}")
def delete_subject(subj_id: int):
    """Delete a subject (cascades to modules, notes AND deletes files)"""
    import os
    existing = execute_one("SELECT * FROM subjects WHERE id = ?", (subj_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    mod_count = execute_one("SELECT COUNT(*) as cnt FROM modules WHERE subject_id = ?", (subj_id,))
    
    # Cleanup Files
    notes_to_delete = execute_query("""
        SELECT n.pdf_url 
        FROM notes n
        JOIN modules m ON n.module_id = m.id
        WHERE m.subject_id = ?
    """, (subj_id,))

    files_deleted = 0
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    for note in notes_to_delete:
        pdf_url = note.get('pdf_url')
        if pdf_url:
            try:
                clean_path = pdf_url.lstrip('/')
                file_path = os.path.join(base_dir, clean_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    files_deleted += 1
            except Exception:
                pass

    try:
        execute_query("DELETE FROM subjects WHERE id = ?", (subj_id,))
        return {
            "message": "Subject deleted (cascade)",
            "deleted_subject": existing,
            "cascaded_modules": mod_count['cnt'] if mod_count else 0,
            "files_cleaned_up": files_deleted
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error deleting subject: {str(e)}")

# ========== MODULES ==========

@router.post("/modules")
def create_module(mod: ModuleCreate):
    """Create a new module"""
    subj = execute_one("SELECT * FROM subjects WHERE id = ?", (mod.subject_id,))
    if not subj:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    try:
        query = "INSERT INTO modules (subject_id, module_number, name) VALUES (?, ?, ?)"
        execute_query(query, (mod.subject_id, mod.module_number, mod.name))
        
        new_mod = execute_one(
            "SELECT * FROM modules WHERE subject_id = ? AND module_number = ?",
            (mod.subject_id, mod.module_number)
        )
        return {"message": "Module created", "module": new_mod}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating module: {str(e)}")

@router.put("/modules/{mod_id}")
def update_module(mod_id: int, mod: ModuleUpdate):
    """Update/rename a module"""
    existing = execute_one("SELECT * FROM modules WHERE id = ?", (mod_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Module not found")
    
    updates = []
    params = []
    if mod.module_number is not None:
        updates.append("module_number = ?")
        params.append(mod.module_number)
    if mod.name is not None:
        updates.append("name = ?")
        params.append(mod.name)
    
    if not updates:
        raise HTTPException(status_code=400, detail="No updates provided")
    
    params.append(mod_id)
    query = f"UPDATE modules SET {', '.join(updates)} WHERE id = ?"
    
    try:
        execute_query(query, tuple(params))
        updated = execute_one("SELECT * FROM modules WHERE id = ?", (mod_id,))
        return {"message": "Module updated", "module": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating module: {str(e)}")

@router.delete("/modules/{mod_id}")
def delete_module(mod_id: int):
    """Delete a module (cascades to notes AND deletes files)"""
    import os
    existing = execute_one("SELECT * FROM modules WHERE id = ?", (mod_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Module not found")
    
    note_count = execute_one("SELECT COUNT(*) as cnt FROM notes WHERE module_id = ?", (mod_id,))
    
    # Cleanup Files
    notes_to_delete = execute_query("SELECT pdf_url FROM notes WHERE module_id = ?", (mod_id,))

    files_deleted = 0
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    for note in notes_to_delete:
        pdf_url = note.get('pdf_url')
        if pdf_url:
            try:
                clean_path = pdf_url.lstrip('/')
                file_path = os.path.join(base_dir, clean_path)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    files_deleted += 1
            except Exception:
                pass

    try:
        execute_query("DELETE FROM modules WHERE id = ?", (mod_id,))
        return {
            "message": "Module deleted (cascade)",
            "deleted_module": existing,
            "cascaded_notes": note_count['cnt'] if note_count else 0,
            "files_cleaned_up": files_deleted
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error deleting module: {str(e)}")

# ========== NOTES (Delete & Rename only) ==========

@router.put("/notes/{note_id}")
def update_note(note_id: int, note: NoteUpdate):
    """Rename a note (title only)"""
    existing = execute_one("SELECT * FROM notes WHERE id = ?", (note_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")
    
    try:
        execute_query("UPDATE notes SET title = ? WHERE id = ?", (note.title, note_id))
        updated = execute_one("SELECT * FROM notes WHERE id = ?", (note_id,))
        return {"message": "Note renamed", "note": updated}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating note: {str(e)}")

@router.delete("/notes/{note_id}")
def delete_note(note_id: int):
    """Delete a note AND its associated PDF file"""
    import os
    
    # Check if exists
    existing = execute_one("SELECT * FROM notes WHERE id = ?", (note_id,))
    if not existing:
        raise HTTPException(status_code=404, detail="Note not found")
    
    deleted_file = False
    error_msg = None

    # Try to delete the file
    pdf_url = existing.get('pdf_url')
    if pdf_url:
        # Construct absolute path. 
        # pdf_url is stored as "pdfs/filename.pdf" or similar relative path
        # We need to resolve it relative to the PROJECT ROOT
        try:
            # Assuming api/hierarchy_crud.py is in /api, so up one level is root
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            # If pdf_url starts with /, remove it to join correctly
            clean_path = pdf_url.lstrip('/')
            file_path = os.path.join(base_dir, clean_path)
            
            if os.path.exists(file_path):
                os.remove(file_path)
                deleted_file = True
            else:
                error_msg = f"File not found at {file_path}"
        except Exception as e:
            error_msg = f"Failed to delete file: {str(e)}"

    try:
        execute_query("DELETE FROM notes WHERE id = ?", (note_id,))
        return {
            "message": "Note deleted successfully",
            "deleted_note": existing,
            "file_deleted": deleted_file,
            "file_error": error_msg
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error deleting note: {str(e)}")
