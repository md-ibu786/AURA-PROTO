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
env_path = os.path.join(project_root, ".env")
load_dotenv(env_path)

# Fix relative GOOGLE_APPLICATION_CREDENTIALS path to absolute
gac = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
if gac and not os.path.isabs(gac):
    # Resolve relative to project root
    abs_gac = os.path.normpath(os.path.join(project_root, gac))
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = abs_gac

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import sys
from pathlib import Path

# Add project root to path so 'api' module can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

import importlib.util

# Import hierarchy data access functions from api/hierarchy.py file
# (not from api/hierarchy/ package which would cause circular imports)
hierarchy_file = importlib.util.spec_from_file_location(
    "hierarchy_functions", os.path.join(os.path.dirname(__file__), "hierarchy.py")
)
hierarchy_module = importlib.util.module_from_spec(hierarchy_file)
hierarchy_file.loader.exec_module(hierarchy_module)

get_all_departments = hierarchy_module.get_all_departments
get_semesters_by_department = hierarchy_module.get_semesters_by_department
get_subjects_by_semester = hierarchy_module.get_subjects_by_semester
get_modules_by_subject = hierarchy_module.get_modules_by_subject

from hierarchy_crud import router as crud_router
from explorer import router as explorer_router
from audio_processing import router as audio_router
from auth import router as auth_router
from users import router as users_router

# Import M2KG modules router
from modules import modules_router

# Import KG processing router
from kg import kg_router

# Import hierarchy navigation router (for AURA-CHAT proxy)
from hierarchy import hierarchy_router


# Import Summaries API router (Phase 11-01)
from api.routers.summaries import router as summaries_router

# Import Trends API router (Phase 11-02)
from api.routers.trends import router as trends_router

# Import Templates API router (Phase 11-03)
from api.routers.templates import router as templates_router

# Import Schema API router (Phase 11-04)
from api.routers.schema import router as schema_router

# Import Graph Preview API router (RC-02)
from api.routers.graph_preview import router as graph_preview_router

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
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(modules_router, prefix="/api/v1")  # M2KG Module endpoints
app.include_router(kg_router, prefix="/api/v1")  # KG processing endpoints
app.include_router(hierarchy_router, prefix="/api/v1")  # Hierarchy navigation endpoints

app.include_router(
    summaries_router
)  # Summaries API (Phase 11-01) - prefix already set in router
app.include_router(
    trends_router
)  # Trends API (Phase 11-02) - prefix already set in router
app.include_router(
    templates_router
)  # Templates API (Phase 11-03) - prefix already set in router
app.include_router(
    schema_router
)  # Schema API (Phase 11-04) - prefix already set in router
app.include_router(graph_preview_router)  # Graph Preview API (RC-02)


from fastapi.staticfiles import StaticFiles

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pdfs_dir = os.path.join(base_dir, "pdfs")
os.makedirs(pdfs_dir, exist_ok=True)
app.mount("/pdfs", StaticFiles(directory=pdfs_dir), name="pdfs")


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

        db.collection("departments").limit(1).get()
        return {"status": "ready", "database": "connected"}
    except Exception:
        return Response(
            content='{"status": "not_ready", "database": "disconnected"}',
            status_code=503,
            media_type="application/json",
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
        "redis": "connected" if connected else "disconnected",
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


@app.post("/notes", status_code=201)
def create_note_endpoint(payload: CreateNoteRequest):
    # Validate hierarchy using path check (use loaded hierarchy_module)
    if not hierarchy_module.validate_hierarchy(
        payload.module_id,
        payload.subject_id,
        payload.semester_id,
        payload.department_id,
    ):
        raise HTTPException(status_code=400, detail="Invalid hierarchy for note")

    try:
        from notes import create_note_record
    except Exception:
        from api.notes import create_note_record

    note = create_note_record(
        payload.module_id,
        payload.title,
        payload.pdf_url,
        subject_id=payload.subject_id,
        department_id=payload.department_id,
    )
    if not note:
        raise HTTPException(status_code=500, detail="Failed to create note")
    return note
