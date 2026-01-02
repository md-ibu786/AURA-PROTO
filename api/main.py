"""
FastAPI app for hierarchy and notes explorer
Run with: uvicorn main:app --reload
"""
# Load environment variables from .env file BEFORE other imports
from dotenv import load_dotenv
import os

# Load .env from project root (one level up from api/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, '.env')
load_dotenv(env_path)

# Fix relative GOOGLE_APPLICATION_CREDENTIALS path to absolute
gac = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', '')
if gac and not os.path.isabs(gac):
    # Resolve relative to project root
    abs_gac = os.path.normpath(os.path.join(project_root, gac))
    os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = abs_gac
    print(f"[DEBUG] Resolved GOOGLE_APPLICATION_CREDENTIALS to: {abs_gac}")
    print(f"[DEBUG] File exists: {os.path.exists(abs_gac)}")
else:
    print(f"[DEBUG] GOOGLE_APPLICATION_CREDENTIALS = {gac}")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
try:
    from hierarchy import get_all_departments, get_semesters_by_department, get_subjects_by_semester, get_modules_by_subject
    from notes_explorer import router as notes_router
    from hierarchy_crud import router as crud_router
    from explorer import router as explorer_router
    from audio_processing import router as audio_router
except ImportError:
    from api.hierarchy import get_all_departments, get_semesters_by_department, get_subjects_by_semester, get_modules_by_subject
    from api.notes_explorer import router as notes_router
    from api.hierarchy_crud import router as crud_router
    from api.explorer import router as explorer_router
    from api.audio_processing import router as audio_router

app = FastAPI(title="AURA-PROTO", version="1.0.0")

# CORS configuration for React frontend
origins = [
    "http://localhost:5173",  # Vite dev server
    "http://localhost:3000",  # Alternative React dev port
    "http://127.0.0.1:5173",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(notes_router)
app.include_router(crud_router)
app.include_router(explorer_router)
app.include_router(audio_router)
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
