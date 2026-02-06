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
from datetime import datetime
import io
import logging
import os
import re
import zipfile

# Load .env from project root (one level up from api/)
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env_path = os.path.join(project_root, ".env")
load_dotenv(env_path, override=True)

# Fix relative GOOGLE_APPLICATION_CREDENTIALS path to absolute
gac = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
if gac and not os.path.isabs(gac):
    # Resolve relative to project root
    abs_gac = os.path.normpath(os.path.join(project_root, gac))
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = abs_gac

from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
import sys
from pathlib import Path

# Add project root to path so 'api' module can be imported
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)

try:
    from limiter import limiter
except ImportError:
    from api.limiter import limiter

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
from auth_sync import router as auth_sync_router
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

# =============================================================================
# SECURITY CONFIGURATION
# =============================================================================

# Production mode detection - enables/disables security features based on environment
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"


# CORS configuration - support both environment variable and defaults for development
# Format: comma-separated list of origins, e.g.:
#   DEVELOPMENT: http://localhost:5173
#   PRODUCTION: https://yourdomain.com,https://www.yourdomain.com
def _get_allowed_origins() -> list:
    """Get allowed CORS origins from environment or use defaults."""
    env_origins = os.getenv("ALLOWED_ORIGINS", "").strip()
    if env_origins:
        origins = [
            origin.strip() for origin in env_origins.split(",") if origin.strip()
        ]
        if IS_PRODUCTION and any(origin == "*" or "*" in origin for origin in origins):
            logger.warning(
                "ALLOWED_ORIGINS contains wildcard '*' in production; "
                "remove '*' to avoid insecure CORS configuration.",
            )
            origins = [origin for origin in origins if "*" not in origin]
        return origins
    # Default development origins
    return [
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
    ]


ALLOWED_ORIGINS = _get_allowed_origins()
logger.info("Resolved ALLOWED_ORIGINS: %s", ALLOWED_ORIGINS)

app = FastAPI(title="AURA-PROTO", version="1.0.0")

# Rate limiting configuration
# Auth endpoints: 5 requests per minute to prevent brute force attacks
# General API: 100 requests per minute
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# =============================================================================
# SECURITY HEADERS MIDDLEWARE
# =============================================================================


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add OWASP-recommended security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        """Attach security headers to every response."""
        response = await call_next(request)

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        if IS_PRODUCTION:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self'; "
                "connect-src 'self' https://*.googleapis.com https://*.firebaseio.com; "
                "frame-ancestors 'none';"
            )

        return response


# Apply SlowAPI middleware first so CORS and security headers wrap 429 responses.
app.add_middleware(SlowAPIMiddleware)


# =============================================================================
# CORS MIDDLEWARE
# =============================================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add security headers last so they run before CORS on requests.
app.add_middleware(SecurityHeadersMiddleware)

app.include_router(crud_router)
app.include_router(explorer_router)
app.include_router(audio_router)
app.include_router(auth_sync_router)
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
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pdfs_dir = os.path.join(base_dir, "pdfs")
os.makedirs(pdfs_dir, exist_ok=True)


def _resolve_pdf_path(filename: str) -> str:
    """Resolve a PDF path and block directory traversal attempts."""
    file_path = os.path.join(pdfs_dir, filename)
    real_path = os.path.realpath(file_path)
    real_pdfs_dir = os.path.realpath(pdfs_dir)

    if not real_path.startswith(real_pdfs_dir):
        raise HTTPException(
            status_code=403,
            detail="Access denied: invalid file path",
        )

    return file_path


def _safe_zip_component(value: str) -> str:
    """Sanitize a name for safe use inside a zip filename."""
    cleaned = re.sub(r'[\\/:*?"<>|]', "-", value.strip())
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.rstrip(" .")


class BulkPdfDownloadRequest(BaseModel):
    """Request payload for downloading multiple PDFs as a zip archive."""

    filenames: list[str]
    subject_name: str | None = None
    module_name: str | None = None


# Authenticated PDF download endpoint
@app.get("/api/pdfs/{filename}")
async def download_pdf(filename: str, inline: bool = Query(False)):
    """
    Serve PDF files with proper headers for download.

    This endpoint provides authenticated access to PDF files with
    Content-Disposition headers to either download or inline view.

    Args:
        filename: The name of the PDF file to download
        inline: Whether to render inline instead of downloading

    Returns:
        FileResponse: The PDF file with download headers

    Raises:
        HTTPException: 404 if file not found
    """
    file_path = _resolve_pdf_path(filename)

    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail=f"PDF file not found: {filename}",
        )

    disposition = "inline" if inline else "attachment"

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
        },
    )


@app.post("/api/pdfs/zip")
async def bulk_download_pdfs(payload: BulkPdfDownloadRequest):
    """
    Bundle multiple PDFs into a zip file and return it as a download.

    Args:
        payload: List of PDF filenames to include

    Returns:
        StreamingResponse: Zip archive containing the requested files
    """
    filenames = [name for name in payload.filenames if name]

    if not filenames:
        raise HTTPException(
            status_code=400,
            detail="No filenames provided",
        )

    seen: set[str] = set()
    unique_names: list[str] = []
    for name in filenames:
        if name in seen:
            continue
        if "/" in name or "\\" in name:
            raise HTTPException(
                status_code=400,
                detail="Invalid filename",
            )
        seen.add(name)
        unique_names.append(name)

    missing: list[str] = []
    resolved: list[tuple[str, str]] = []
    for name in unique_names:
        file_path = _resolve_pdf_path(name)
        if not os.path.exists(file_path):
            missing.append(name)
            continue
        resolved.append((name, file_path))

    if missing:
        missing_list = ", ".join(missing)
        raise HTTPException(
            status_code=404,
            detail=f"Missing files: {missing_list}",
        )

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(
        zip_buffer,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
    ) as zip_file:
        for name, file_path in resolved:
            zip_file.write(file_path, arcname=name)

    zip_buffer.seek(0)

    subject_name = (
        _safe_zip_component(payload.subject_name)
        if payload.subject_name
        else ""
    )
    module_name = (
        _safe_zip_component(payload.module_name)
        if payload.module_name
        else ""
    )

    if subject_name and module_name:
        zip_name = f"notes-{subject_name}-{module_name}.zip"
    else:
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        zip_name = f"notes_{timestamp}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{zip_name}"',
        },
    )


# Keep static file serving for backward compatibility and direct access
app.mount("/pdfs", StaticFiles(directory=pdfs_dir), name="pdfs")


@app.get("/departments")
def list_departments():
    return {"departments": get_all_departments()}


@app.get("/departments/{department_id}/semesters")
def list_semesters(department_id: str):
    return {"semesters": get_semesters_by_department(department_id)}


@app.get("/semesters/{semester_id}/subjects")
def list_subjects(semester_id: str, department_id: str | None = None):
    return {
        "subjects": get_subjects_by_semester(semester_id, department_id=department_id)
    }


@app.get("/subjects/{subject_id}/modules")
def list_modules(
    subject_id: str, department_id: str | None = None, semester_id: str | None = None
):
    return {
        "modules": get_modules_by_subject(
            subject_id, department_id=department_id, semester_id=semester_id
        )
    }


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
