"""
FastAPI app for hierarchy and notes explorer
Run with: uvicorn main:app --reload
"""
from fastapi import FastAPI
try:
    from hierarchy import get_all_departments, get_semesters_by_department, get_subjects_by_semester, get_modules_by_subject
    from notes_explorer import router as notes_router
    from hierarchy_crud import router as crud_router
except ImportError:
    from api.hierarchy import get_all_departments, get_semesters_by_department, get_subjects_by_semester, get_modules_by_subject
    from api.notes_explorer import router as notes_router
    from api.hierarchy_crud import router as crud_router

app = FastAPI(title="AURA-PROTO", version="1.0.0")
app.include_router(notes_router)
app.include_router(crud_router)

# Serve local pdfs folder for development (mounted at /pdfs)
from fastapi.staticfiles import StaticFiles
import os
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pdfs_dir = os.path.join(base_dir, 'pdfs')
os.makedirs(pdfs_dir, exist_ok=True)
app.mount('/pdfs', StaticFiles(directory=pdfs_dir), name='pdfs')

@app.get("/departments")
def list_departments():
    return {"departments": get_all_departments()}

@app.get("/departments/{department_id}/semesters")
def list_semesters(department_id: int):
    return {"semesters": get_semesters_by_department(department_id)}

@app.get("/semesters/{semester_id}/subjects")
def list_subjects(semester_id: int):
    return {"subjects": get_subjects_by_semester(semester_id)}

@app.get("/subjects/{subject_id}/modules")
def list_modules(subject_id: int):
    return {"modules": get_modules_by_subject(subject_id)}

@app.get("/")
def root():
    return {"message": "AURA-PROTO API - Hierarchy & Notes Explorer"}

from pydantic import BaseModel
from fastapi import HTTPException

class CreateNoteRequest(BaseModel):
    department_id: int
    semester_id: int
    subject_id: int
    module_id: int
    title: str
    pdf_url: str

@app.post('/notes', status_code=201)
def create_note_endpoint(payload: CreateNoteRequest):
    # Validate hierarchy: ensure module belongs to the provided chain
    try:
        from hierarchy import validate_hierarchy
    except Exception:
        from api.hierarchy import validate_hierarchy
    if not validate_hierarchy(payload.module_id, payload.subject_id, payload.semester_id, payload.department_id):
        raise HTTPException(status_code=400, detail='Invalid hierarchy for note')
    try:
        from notes import create_note_record
    except Exception:
        from api.notes import create_note_record
    note = create_note_record(payload.module_id, payload.title, payload.pdf_url)
    if not note:
        raise HTTPException(status_code=500, detail='Failed to create note')
    return note
