"""
============================================================================
FILE: audio_processing.py
LOCATION: api/audio_processing.py
============================================================================

PURPOSE:
    Provides REST API endpoints for the AI-powered audio-to-notes pipeline.
    Handles audio file uploads, document uploads, and orchestrates the
    multi-step processing: transcription -> refinement -> summarization -> PDF.

ROLE IN PROJECT:
    This is the AI Note Generator backend. The React UploadDialog component
    uploads audio files here, which triggers a background processing pipeline.
    Also handles direct document uploads (PDF, DOC, TXT) for non-audio notes.

    Key features:
    - Background task processing with status polling
    - File size validation and format checking
    - Graceful service degradation if dependencies are missing

KEY COMPONENTS:
    Pydantic Models:
    - TranscribeResponse, RefineRequest/Response, SummarizeRequest/Response
    - GeneratePdfRequest/Response, PipelineRequest, PipelineStatusResponse

    Individual Step Endpoints (for debugging/manual control):
    - POST /api/audio/transcribe: Transcribe audio using Deepgram
    - POST /api/audio/refine: Clean transcript with AI
    - POST /api/audio/summarize: Generate university-grade notes
    - POST /api/audio/generate-pdf: Create PDF from notes

    Pipeline Endpoints:
    - POST /api/audio/process-pipeline: Start full async pipeline
    - GET /api/audio/pipeline-status/{job_id}: Poll job status
    - POST /api/audio/upload-document: Upload PDF/DOC/TXT directly

    Background Processing:
    - _run_pipeline(): Background task that runs all steps
    - job_status_store: In-memory job tracking (use Redis in production)

DEPENDENCIES:
    - External: fastapi, pydantic, uuid
    - Internal:
        - services/stt.py (Deepgram transcription)
        - services/coc.py (transcript transformation)
        - services/summarizer.py (note generation)
        - services/pdf_generator.py (PDF creation)
        - notes.py (database record creation)

FILE SIZE LIMITS:
    - Audio: 100MB max, 1KB min
    - Documents: 50MB max
    - Allowed audio: .mp3, .wav, .m4a, .ogg, .flac
    - Allowed docs: .pdf, .doc, .docx, .txt, .md

USAGE:
    # Start processing pipeline
    POST /api/audio/process-pipeline
    FormData: file=<audio>, topic="Lecture 1", moduleId="abc123"

    # Poll for status
    GET /api/audio/pipeline-status/{jobId}
    Returns: {status: "transcribing", progress: 35, ...}
============================================================================
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from typing import Any, Dict, Optional
import os
import time
import uuid
import json
import threading
import tempfile

try:
    import redis as _redis_lib
    _redis_client = None
except ImportError:
    _redis_lib = None
    _redis_client = None

# Structured logging
try:
    from logging_config import get_logger

    logger = get_logger("audio")
except ImportError:
    import logging

    logger = logging.getLogger("audio")

# Import services (with fallbacks if dependencies are missing)
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import services
try:
    from services.stt import process_audio_file
except ImportError as exc:
    # If it's the specific deepgram error, print it loudly but try to continue for other endpoints
    _stt_import_error = exc
    logger.error(f"CRITICAL ERROR IMPORTING STT SERVICE: {_stt_import_error}")

    def process_audio_file(*args, **kwargs) -> Dict[str, Any]:
        raise ImportError(
            f"Service unavailable due to import error: {_stt_import_error}"
        ) from _stt_import_error


try:
    from services.coc import transform_transcript
except ImportError:

    def transform_transcript(*args, **kwargs) -> str:
        raise ImportError("AI dependencies not installed")


try:
    from services.summarizer import generate_university_notes
except ImportError:

    def generate_university_notes(*args, **kwargs) -> str:
        raise ImportError("AI dependencies not installed")


try:
    from services.pdf_generator import create_pdf
except ImportError:

    def create_pdf(*args, **kwargs) -> str:
        raise ImportError("fpdf dependency not installed. Run: pip install fpdf2")


# Import note creation helper
try:
    from notes import create_note_record
except (ImportError, ModuleNotFoundError):
    try:
        from .notes import create_note_record
    except (ImportError, ModuleNotFoundError):
        from api.notes import create_note_record

router = APIRouter(prefix="/api/audio", tags=["audio-processing"])

# In-memory job store fallback (use Redis in production)
job_status_store = {}
_job_store_lock = threading.Lock()


def _get_redis():
    """Get or lazily initialize the Redis client."""
    global _redis_client
    if _redis_lib is None:
        return None
    if _redis_client is None:
        try:
            redis_url = os.environ.get(
                "REDIS_URL", "redis://localhost:6379"
            )
            _redis_client = _redis_lib.from_url(
                redis_url, decode_responses=True
            )
            _redis_client.ping()
            logger.info("Redis connected for job store")
        except Exception:
            logger.warning(
                "Redis unavailable, falling back to in-memory job store"
            )
            _redis_client = None
    return _redis_client


def _set_job(job_id: str, data: dict) -> None:
    """Store job data with TTL. Uses Redis if available, else in-memory dict."""
    data["updated_at"] = time.time()
    try:
        redis_client = _get_redis()
        if redis_client:
            redis_client.set(
                f"job:{job_id}",
                json.dumps(data),
                ex=JOB_STATUS_TTL_SECONDS,
            )
            return
    except Exception:
        logger.warning(
            "Redis set failed, using in-memory store for job %s", job_id
        )
    with _job_store_lock:
        job_status_store[job_id] = data


def _get_job(job_id: str) -> Optional[dict]:
    """Retrieve job data from Redis or in-memory store."""
    try:
        redis_client = _get_redis()
        if redis_client:
            raw = redis_client.get(f"job:{job_id}")
            return json.loads(raw) if raw else None
    except Exception:
        pass
    with _job_store_lock:
        return job_status_store.get(job_id)


def _delete_job(job_id: str) -> None:
    """Delete a job from the store."""
    try:
        redis_client = _get_redis()
        if redis_client:
            redis_client.delete(f"job:{job_id}")
            return
    except Exception:
        pass
    with _job_store_lock:
        job_status_store.pop(job_id, None)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDFS_DIR = os.path.join(BASE_DIR, "pdfs")

# File size limits (in bytes)
MAX_AUDIO_SIZE = 100 * 1024 * 1024  # 100MB for audio files
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50MB for documents
MIN_AUDIO_SIZE = 1024  # 1KB minimum
ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".flac"}
ALLOWED_AUDIO_MIMES = {
    "audio/mpeg", "audio/wav", "audio/x-m4a",
    "audio/ogg", "audio/flac", "application/octet-stream",
}

# Job status retention constants (T-08-04 mitigation)
JOB_STATUS_TTL_SECONDS = 300  # 5 minutes - terminal jobs expire after this
JOB_STATUS_MAX_ENTRIES = 100  # Max terminal jobs before oldest are evicted

# Active (non-terminal) job statuses
_ACTIVE_JOB_STATUSES = {
    "pending",
    "transcribing",
    "refining",
    "summarizing",
    "generating_pdf",
}


def _is_terminal_status(status: str) -> bool:
    """Check if a job status is terminal (complete or error)."""
    return status in ("complete", "error")


def _add_timestamp(job_data: dict) -> dict:
    """Add or update the updated_at timestamp on a job data dict."""
    job_data["updated_at"] = time.time()
    return job_data


def _cleanup_job_store() -> None:
    """
    Prune expired terminal jobs and evict oldest terminal jobs if store exceeds max entries.

    Cleanup order:
    1. Remove terminal jobs older than TTL
    2. If still over max_entries, evict oldest terminal jobs first
    3. Active in-flight jobs are never evicted by TTL or max-entry pressure
    """
    now = time.time()
    terminal_jobs = []
    active_jobs = []

    # Separate active and terminal jobs
    with _job_store_lock:
        current_store = dict(job_status_store)

    for job_id, job_data in current_store.items():
        if _is_terminal_status(job_data.get("status", "")):
            terminal_jobs.append((job_id, job_data))
        else:
            active_jobs.append((job_id, job_data))

    # Prune terminal jobs older than TTL
    terminal_jobs = [
        (job_id, job_data)
        for job_id, job_data in terminal_jobs
        if (now - job_data.get("updated_at", 0)) <= JOB_STATUS_TTL_SECONDS
    ]

    # If still over max_entries, evict oldest terminal jobs
    if len(terminal_jobs) + len(active_jobs) > JOB_STATUS_MAX_ENTRIES:
        # Sort terminal jobs by updated_at (oldest first)
        terminal_jobs.sort(key=lambda x: x[1].get("updated_at", 0))
        # Keep only enough to get under the limit
        max_terminal = max(0, JOB_STATUS_MAX_ENTRIES - len(active_jobs))
        terminal_jobs = terminal_jobs[:max_terminal]

    # Rebuild the store with surviving jobs
    new_store = {}
    for job_id, job_data in active_jobs:
        new_store[job_id] = job_data
    for job_id, job_data in terminal_jobs:
        new_store[job_id] = job_data
    with _job_store_lock:
        job_status_store.clear()
        job_status_store.update(new_store)


def validate_file_size(content_length: int, max_size: int, file_type: str) -> None:
    """Validate file size and raise HTTPException 413 if exceeded."""
    if content_length > max_size:
        max_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"{file_type} file too large. Maximum size: {max_mb:.0f}MB",
        )


# ========== MODELS ==========


class TranscribeResponse(BaseModel):
    success: bool
    transcript: Optional[str] = None
    error: Optional[str] = None


class RefineRequest(BaseModel):
    topic: str
    transcript: str


class RefineResponse(BaseModel):
    success: bool
    refinedTranscript: Optional[str] = None
    error: Optional[str] = None


class SummarizeRequest(BaseModel):
    topic: str
    refinedTranscript: str


class SummarizeResponse(BaseModel):
    success: bool
    notes: Optional[str] = None
    error: Optional[str] = None


class GeneratePdfRequest(BaseModel):
    title: str
    notes: str
    moduleId: Optional[str] = None  # Updated to str


class GeneratePdfResponse(BaseModel):
    success: bool
    pdfUrl: Optional[str] = None
    noteId: Optional[str] = None  # Updated to str
    error: Optional[str] = None
    warning: Optional[str] = None  # Partial failure indicator


class PipelineRequest(BaseModel):
    topic: str
    moduleId: Optional[str] = None  # Updated to str


class PipelineStatusResponse(BaseModel):
    jobId: str
    status: str  # 'pending', 'transcribing', 'refining', 'summarizing', 'generating_pdf', 'complete', 'error'
    progress: int  # 0-100
    message: Optional[str] = None
    result: Optional[dict] = None


# ========== ENDPOINTS ==========

# Document uploads directory
DOCS_DIR = os.path.join(BASE_DIR, "pdfs")  # Store docs alongside PDFs


@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    moduleId: str = Form(...),  # Updated to str
):
    """
    Upload a document (PDF, DOC, TXT) and create a note entry.
    """
    try:
        # Validate file type
        allowed_extensions = {".pdf", ".doc", ".docx", ".txt", ".md"}
        file_ext = os.path.splitext(file.filename or "")[1].lower()

        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"File type {file_ext} not allowed. Allowed: {', '.join(allowed_extensions)}",
            )

        # Read file content
        file_content = await file.read()

        if not file_content:
            raise HTTPException(status_code=400, detail="Empty file")

        # Validate file size
        validate_file_size(len(file_content), MAX_DOCUMENT_SIZE, "Document")

        # Ensure directory exists
        os.makedirs(DOCS_DIR, exist_ok=True)

        # Generate unique filename
        safe_title = "".join(
            c if c.isalnum() or c in (" ", "-", "_") else "_" for c in title
        )
        safe_title = safe_title.replace(" ", "_")[:50]
        filename = f"{safe_title}_{uuid.uuid4().hex[:8]}{file_ext}"
        filepath = os.path.join(DOCS_DIR, filename)

        # Save file
        with open(filepath, "wb") as f:
            f.write(file_content)

        # Create URL (documents served from same /pdfs route)
        doc_url = f"/pdfs/{filename}"

        # Insert into database using helper
        note = create_note_record(moduleId, title, doc_url)
        if not note:
            raise HTTPException(status_code=404, detail="Module not found")

        return {
            "success": True,
            "noteId": note["id"],
            "documentUrl": doc_url,
            "filename": filename,
            "message": f"Document '{title}' uploaded successfully!",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail="Upload failed. Please try again."
        )


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribe an audio file using Deepgram.
    """
    try:
        # Validate extension
        file_ext = os.path.splitext(file.filename or "")[1].lower()
        if file_ext not in ALLOWED_AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format {file_ext}. Allowed: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}",
            )

        # Content-type check (secondary validation)
        if file.content_type and file.content_type not in ALLOWED_AUDIO_MIMES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content type '{file.content_type}'. Expected audio file.",
            )

        # Read file bytes
        audio_bytes = await file.read()

        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")

        # Validate file size
        if len(audio_bytes) < MIN_AUDIO_SIZE:
            raise HTTPException(
                status_code=400, detail="File too small to be a valid audio recording"
            )

        validate_file_size(len(audio_bytes), MAX_AUDIO_SIZE, "Audio")

        # Process with Deepgram
        result = process_audio_file(audio_bytes)

        return TranscribeResponse(success=True, transcript=result.get("text", ""))
    except HTTPException as e:
        raise e  # Re-raise 400/413 errors
    except ValueError as e:
        return TranscribeResponse(success=False, error=str(e))
    except Exception as e:
        logger.error(f"Transcription failed: {e}", exc_info=True)
        error_msg = str(e)
        if "timed out" in error_msg.lower():
            return TranscribeResponse(
                success=False,
                error="Transcription timed out. Please try a shorter recording or check your connection.",
            )
        return TranscribeResponse(
            success=False, error="Transcription failed. Please try again."
        )


@router.post("/refine", response_model=RefineResponse)
async def refine_transcript(request: RefineRequest):
    """
    Refine/clean a transcript using AI.
    """
    try:
        if not request.transcript:
            raise HTTPException(status_code=400, detail="Transcript is required")

        refined = transform_transcript(request.topic, request.transcript)

        return RefineResponse(success=True, refinedTranscript=refined)
    except Exception as e:
        logger.error(f"Refinement failed: {e}", exc_info=True)
        return RefineResponse(
            success=False, error="Refinement failed. Please try again."
        )


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_transcript(request: SummarizeRequest):
    """
    Generate university-grade notes from refined transcript.
    """
    try:
        if not request.refinedTranscript:
            raise HTTPException(
                status_code=400, detail="Refined transcript is required"
            )

        notes = generate_university_notes(request.topic, request.refinedTranscript)

        return SummarizeResponse(success=True, notes=notes)
    except Exception as e:
        logger.error(f"Summarization failed: {e}", exc_info=True)
        return SummarizeResponse(
            success=False, error="Summarization failed. Please try again."
        )


@router.post("/generate-pdf", response_model=GeneratePdfResponse)
async def generate_pdf(request: GeneratePdfRequest):
    """
    Generate a PDF from notes and optionally save to database.
    """
    try:
        if not request.notes:
            raise HTTPException(status_code=400, detail="Notes content is required")

        # Ensure pdfs directory exists
        os.makedirs(PDFS_DIR, exist_ok=True)

        filename = _make_pdf_filename(request.title)
        filepath = os.path.join(PDFS_DIR, filename)

        # Generate PDF
        create_pdf(request.notes, request.title, filepath)

        pdf_url = f"/pdfs/{filename}"
        note_id = None

        # Optionally save to database if moduleId is provided
        warning_message = None
        if request.moduleId:
            try:
                note = create_note_record(request.moduleId, request.title, pdf_url)
                if note:
                    note_id = note["id"]
            except Exception as db_error:
                # PDF was generated but DB save failed
                logger.error(
                    f"Failed to save note to database: {db_error}", exc_info=True
                )
                warning_message = (
                    f"PDF generated but note record creation failed: {str(db_error)}"
                )

        return GeneratePdfResponse(
            success=True, pdfUrl=pdf_url, noteId=note_id, warning=warning_message
        )
    except Exception as e:
        logger.error(f"PDF generation failed: {e}", exc_info=True)
        return GeneratePdfResponse(
            success=False, error="PDF generation failed. Please try again."
        )


def _get_audio_duration(file_path: str) -> float:
    """Get audio duration in seconds using ffprobe. Returns 0 on failure."""
    import subprocess as _subprocess
    try:
        result = _subprocess.run(
            [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", file_path,
            ],
            capture_output=True, text=True, timeout=30,
        )
        info = json.loads(result.stdout)
        return float(info["format"]["duration"])
    except Exception:
        return 0


def _make_pdf_filename(topic: str) -> str:
    """Generate a safe, unique PDF filename from a topic string."""
    safe_title = "".join(
        c if c.isalnum() or c in (" ", "-", "_") else "_" for c in topic
    )
    safe_title = safe_title.replace(" ", "_")[:50]
    return f"{safe_title}_{uuid.uuid4().hex[:8]}.pdf"


MAX_AUDIO_DURATION_SECONDS = 3 * 3600  # 3 hours


def _run_pipeline(
    job_id: str, temp_path: str, topic: str, module_id: Optional[str]
):
    """Background task to run the full processing pipeline."""
    # Weighted progress: transcription (60%), refinement (20%),
    # summarization (10%), PDF (10%). Transcription is the longest step.
    try:
        # Pre-check audio duration via ffprobe before hitting Deepgram
        duration_seconds = _get_audio_duration(temp_path)
        if duration_seconds > MAX_AUDIO_DURATION_SECONDS:
            raise ValueError(
                f"Audio duration ({duration_seconds / 3600:.1f} hours) "
                f"exceeds maximum allowed "
                f"({MAX_AUDIO_DURATION_SECONDS / 3600:.0f} hours). "
                f"Please upload a shorter recording."
            )

        # Step 1: Transcribe — read temp file, then delete immediately
        _set_job(job_id, _add_timestamp(
            {
                "status": "transcribing",
                "progress": 10,
                "message": "Transcribing audio...",
            }
        ))

        with open(temp_path, "rb") as f:
            audio_bytes = f.read()
        os.unlink(temp_path)
        temp_path = None

        result = process_audio_file(audio_bytes)
        del audio_bytes

        transcript = result.get("text", "")

        if not transcript:
            raise ValueError("Transcription returned empty result")

        # Validate audio duration from transcript metadata (fallback)
        transcript_duration = result.get("duration", 0)
        if (
            transcript_duration > MAX_AUDIO_DURATION_SECONDS
            and duration_seconds == 0
        ):
            raise ValueError(
                f"Audio duration ({transcript_duration / 3600:.1f} hours) "
                f"exceeds maximum allowed "
                f"({MAX_AUDIO_DURATION_SECONDS / 3600:.0f} hours). "
                f"Please upload a shorter recording."
            )

        # Step 2: Refine
        _set_job(job_id, _add_timestamp(
            {
                "status": "refining",
                "progress": 35,
                "message": "Refining transcript...",
            }
        ))

        refined = transform_transcript(topic, transcript)

        # Step 3: Summarize
        _set_job(job_id, _add_timestamp(
            {
                "status": "summarizing",
                "progress": 60,
                "message": "Generating notes...",
            }
        ))

        notes = generate_university_notes(topic, refined)

        # Step 4: Generate PDF
        _set_job(job_id, _add_timestamp(
            {
                "status": "generating_pdf",
                "progress": 85,
                "message": "Creating PDF...",
            }
        ))

        os.makedirs(PDFS_DIR, exist_ok=True)
        filename = _make_pdf_filename(topic)
        filepath = os.path.join(PDFS_DIR, filename)

        create_pdf(notes, topic, filepath)
        pdf_url = f"/pdfs/{filename}"

        note_id = None
        if module_id:
            try:
                note = create_note_record(module_id, topic, pdf_url)
                if note:
                    note_id = note["id"]
            except Exception as e:
                logger.error(f"Failed to save note to database: {e}", exc_info=True)
                # Track partial failure - PDF was created but DB save failed
                job_data = _get_job(job_id) or {}
                if "warnings" not in job_data:
                    job_data["warnings"] = []
                job_data["warnings"].append(
                    f"PDF generated but note record creation failed: {str(e)}"
                )
                _set_job(job_id, _add_timestamp(job_data))

        # Complete - cleanup first to make room if needed, then record terminal state
        _cleanup_job_store()
        existing = _get_job(job_id) or {}
        complete_status = {
            "status": "complete",
            "progress": 100,
            "message": "Processing complete!",
            "result": {
                "transcript": transcript,
                "refinedTranscript": refined,
                "notes": notes,
                "pdfUrl": pdf_url,
                "noteId": note_id,
            },
        }
        if "warnings" in existing:
            complete_status["warnings"] = existing["warnings"]
        _set_job(job_id, _add_timestamp(complete_status))

    except Exception as e:
        _cleanup_job_store()
        _set_job(job_id, _add_timestamp(
            {
                "status": "error",
                "progress": 0,
                "message": f"Error: {str(e)}",
                "result": None,
            }
        ))
    finally:
        if temp_path and os.path.exists(temp_path):
            try:
                os.unlink(temp_path)
            except OSError:
                logger.warning(
                    "Failed to clean up temp file: %s", temp_path
                )


@router.post("/process-pipeline")
async def start_pipeline(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    topic: str = Form(...),
    moduleId: Optional[str] = Form(None),  # Updated to str
):
    """
    Start the full audio processing pipeline (async with status polling).
    Returns a job ID to poll for status.
    """
    try:
        # Validate extension
        file_ext = os.path.splitext(file.filename or "")[1].lower()
        if file_ext not in ALLOWED_AUDIO_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format {file_ext}. Allowed: {', '.join(ALLOWED_AUDIO_EXTENSIONS)}",
            )

        # Content-type check (secondary validation)
        if file.content_type and file.content_type not in ALLOWED_AUDIO_MIMES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid content type '{file.content_type}'. Expected audio file.",
            )

        # Write audio to temp file to avoid keeping entire file in memory
        tmp = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=os.path.splitext(file.filename or ".bin")[1],
        )
        try:
            content = await file.read()
            if not content:
                raise HTTPException(
                    status_code=400, detail="Empty audio file"
                )
            tmp.write(content)
            tmp.flush()
            tmp.close()
            temp_path = tmp.name
        except HTTPException:
            tmp.close()
            os.unlink(tmp.name)
            raise
        except Exception:
            tmp.close()
            os.unlink(tmp.name)
            raise

        # Validate file size
        content_size = os.path.getsize(temp_path)
        validate_file_size(content_size, MAX_AUDIO_SIZE, "Audio")

        # Cleanup before creating new job to maintain bounded store
        _cleanup_job_store()

        # Create job
        job_id = str(uuid.uuid4())
        _set_job(job_id, _add_timestamp(
            {
                "status": "pending",
                "progress": 0,
                "message": "Starting pipeline...",
            }
        ))

        # Start background task
        background_tasks.add_task(_run_pipeline, job_id, temp_path, topic, moduleId)

        return {"jobId": job_id, "status": "pending"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Pipeline start failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="Failed to start processing pipeline. Please try again.",
        )


@router.get("/pipeline-status/{job_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(job_id: str):
    """
    Get the status of a processing pipeline job.
    Cleanup runs before read to ensure expired/evicted jobs return 404.
    """
    # Cleanup first to evict any expired terminal jobs
    _cleanup_job_store()

    status = _get_job(job_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Job not found")

    return PipelineStatusResponse(
        jobId=job_id,
        status=status["status"],
        progress=status["progress"],
        message=status.get("message"),
        result=status.get("result"),
    )
