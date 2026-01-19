"""
============================================================================
FILE: main.py
LOCATION: api/main.py
============================================================================

PURPOSE:
    Main entry point for the AURA-PROTO FastAPI backend application.
    Initializes the web server, configures middleware, and mounts all
    API routers for hierarchy management, file exploration, and audio
    processing pipelines.

ROLE IN PROJECT:
    This is the central orchestrator of the backend. It:
    - Loads environment variables (including Firebase/Google credentials)
    - Configures CORS for React frontend communication
    - Sets up rate limiting to prevent abuse
    - Mounts static file serving for generated PDFs
    - Includes all API routers (CRUD, Explorer, Audio)
    - Provides health check endpoints for deployment monitoring

KEY COMPONENTS:
    - app: The FastAPI application instance
    - list_departments/semesters/subjects/modules: Legacy hierarchy endpoints
    - root(): API welcome endpoint
    - health_check(): Liveness probe for container orchestration
    - readiness_check(): Readiness probe checking Firestore connectivity
    - create_note_endpoint(): Direct note creation with hierarchy validation
    - CreateNoteRequest: Pydantic model for note creation payload

DEPENDENCIES:
    - External: fastapi, slowapi (rate limiting), python-dotenv
    - Internal: hierarchy.py, hierarchy_crud.py, explorer.py, audio_processing.py, config.py

USAGE:
    Run with: uvicorn main:app --reload --port 8000
    Or from project root: cd api && python -m uvicorn main:app --reload
    Access API docs at: http://localhost:8000/docs
============================================================================
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

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from hierarchy import get_all_departments, get_semesters_by_department, get_subjects_by_semester, get_modules_by_subject
    from hierarchy_crud import router as crud_router
    from explorer import router as explorer_router
    from audio_processing import router as audio_router
except (ImportError, ModuleNotFoundError):
    # Fallback to absolute imports if running from project root
    from api.hierarchy import get_all_departments, get_semesters_by_department, get_subjects_by_semester, get_modules_by_subject
    from api.hierarchy_crud import router as crud_router
    from api.explorer import router as explorer_router
    from api.audio_processing import router as audio_router

# Import M2KG modules router
try:
    from modules import modules_router
except (ImportError, ModuleNotFoundError):
    from api.modules import modules_router

app = FastAPI(title="AURA-PROTO", version="1.0.0")

# Rate limiting configuration

# Rate limiting configuration
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS configuration for React frontend
origins = [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(crud_router)
app.include_router(explorer_router)
app.include_router(audio_router)
app.include_router(modules_router, prefix="/api/v1")  # M2KG Module endpoints

from fastapi.staticfiles import StaticFiles
base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pdfs_dir = os.path.join(base_dir, 'pdfs')
os.makedirs(pdfs_dir, exist_ok=True)
app.mount('/pdfs', StaticFiles(directory=pdfs_dir), name='pdfs')

@app.get("/departments")
def list_departments():
    return {"departments": get_all_departments()}

@app.get("/departments/{department_id}/semesters")
def list_semesters(department_id: str):
    return {"semesters": get_semesters_by_department(department_id)}

@app.get("/semesters/{semester_id}/subjects")
def list_subjects(semester_id: str):
    return {"subjects": get_subjects_by_semester(semester_id)}

@app.get("/subjects/{subject_id}/modules")
def list_modules(subject_id: str):
    return {"modules": get_modules_by_subject(subject_id)}

@app.get("/")
def root():
    return {"message": "AURA-PROTO API - Hierarchy & Notes Explorer"}

@app.get("/health")
def health_check():
    """Liveness probe - confirms app is running."""
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/ready")
async def readiness_check():
    """Readiness probe - confirms Firestore is accessible."""
    try:
        from config import db
        db.collection('departments').limit(1).get()
        return {"status": "ready", "database": "connected"}
    except Exception:
        return Response(
            content='{"status": "not_ready", "database": "disconnected"}',
            status_code=503,
            media_type="application/json"
        )

@app.get("/health/redis")
def redis_health_check():
    """Check Redis connection status."""
    try:
        from cache import redis_client
    except ImportError:
        try:
            from api.cache import redis_client
        except ImportError:
            return {"status": "unavailable", "redis": "package_not_found"}
    
    connected = redis_client.ping()
    return {
        "status": "healthy" if connected else "unhealthy",
        "redis": "connected" if connected else "disconnected"
    }

from pydantic import BaseModel
from fastapi import HTTPException

class CreateNoteRequest(BaseModel):
    department_id: str
    semester_id: str
    subject_id: str
    module_id: str
    title: str
    pdf_url: str

@app.post('/notes', status_code=201)
def create_note_endpoint(payload: CreateNoteRequest):
    # Validate hierarchy using path check
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
