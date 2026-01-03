"""
Audio Processing API endpoints.
Exposes services folder functionality for React frontend.
"""
from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
import os
import time
import uuid

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
except ImportError as e:
    # If it's the specific deepgram error, print it loudly but try to continue for other endpoints
    logger.error(f"CRITICAL ERROR IMPORTING STT SERVICE: {e}")
    try:
        import deepgram
    except Exception as d_err:
        pass
        
    def process_audio_file(*args, **kwargs):
        raise ImportError(f"Service unavailable due to import error: {e}")

try:
    from services.coc import transform_transcript
except ImportError as e:
    def transform_transcript(*args, **kwargs):
        raise ImportError("AI dependencies not installed")

try:
    from services.summarizer import generate_university_notes
except ImportError as e:
    def generate_university_notes(*args, **kwargs):
        raise ImportError("AI dependencies not installed")

try:
    from services.pdf_generator import create_pdf
except ImportError as e:
    def create_pdf(*args, **kwargs):
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

# In-memory job status store (for demo; use Redis in production)
job_status_store = {}

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PDFS_DIR = os.path.join(BASE_DIR, 'pdfs')

# File size limits (in bytes)
MAX_AUDIO_SIZE = 100 * 1024 * 1024  # 100MB for audio files
MAX_DOCUMENT_SIZE = 50 * 1024 * 1024  # 50MB for documents


def validate_file_size(content_length: int, max_size: int, file_type: str) -> None:
    """Validate file size and raise HTTPException 413 if exceeded."""
    if content_length > max_size:
        max_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"{file_type} file too large. Maximum size: {max_mb:.0f}MB"
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
    moduleId: Optional[str] = None # Updated to str


class GeneratePdfResponse(BaseModel):
    success: bool
    pdfUrl: Optional[str] = None
    noteId: Optional[str] = None # Updated to str
    error: Optional[str] = None


class PipelineRequest(BaseModel):
    topic: str
    moduleId: Optional[str] = None # Updated to str


class PipelineStatusResponse(BaseModel):
    jobId: str
    status: str  # 'pending', 'transcribing', 'refining', 'summarizing', 'generating_pdf', 'complete', 'error'
    progress: int  # 0-100
    message: Optional[str] = None
    result: Optional[dict] = None


# ========== ENDPOINTS ==========

# Document uploads directory
DOCS_DIR = os.path.join(BASE_DIR, 'pdfs')  # Store docs alongside PDFs


@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    moduleId: str = Form(...) # Updated to str
):
    """
    Upload a document (PDF, DOC, TXT) and create a note entry.
    """
    try:
        # Validate file type
        allowed_extensions = {'.pdf', '.doc', '.docx', '.txt', '.md'}
        file_ext = os.path.splitext(file.filename or '')[1].lower()
        
        if file_ext not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"File type {file_ext} not allowed. Allowed: {', '.join(allowed_extensions)}"
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
        timestamp = int(time.time())
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in title)
        safe_title = safe_title.replace(' ', '_')[:50]
        filename = f"{safe_title}_{timestamp}{file_ext}"
        filepath = os.path.join(DOCS_DIR, filename)
        
        # Save file
        with open(filepath, 'wb') as f:
            f.write(file_content)
        
        # Create URL (documents served from same /pdfs route)
        doc_url = f"/pdfs/{filename}"
        
        # Insert into database using helper
        note = create_note_record(moduleId, title, doc_url)
        if not note:
             raise HTTPException(status_code=404, detail="Module not found")

        return {
            "success": True,
            "noteId": note['id'],
            "documentUrl": doc_url,
            "filename": filename,
            "message": f"Document '{title}' uploaded successfully!"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_audio(file: UploadFile = File(...)):
    """
    Transcribe an audio file using Deepgram.
    """
    try:
        # Read file bytes
        audio_bytes = await file.read()
        
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        # Validate file size
        validate_file_size(len(audio_bytes), MAX_AUDIO_SIZE, "Audio")
        
        # Process with Deepgram
        result = process_audio_file(audio_bytes)
        
        return TranscribeResponse(
            success=True,
            transcript=result.get('text', '')
        )
    except ValueError as e:
        return TranscribeResponse(success=False, error=str(e))
    except Exception as e:
        return TranscribeResponse(success=False, error=f"Transcription failed: {str(e)}")


@router.post("/refine", response_model=RefineResponse)
async def refine_transcript(request: RefineRequest):
    """
    Refine/clean a transcript using AI.
    """
    try:
        if not request.transcript:
            raise HTTPException(status_code=400, detail="Transcript is required")
        
        refined = transform_transcript(request.topic, request.transcript)
        
        return RefineResponse(
            success=True,
            refinedTranscript=refined
        )
    except Exception as e:
        return RefineResponse(success=False, error=f"Refinement failed: {str(e)}")


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_transcript(request: SummarizeRequest):
    """
    Generate university-grade notes from refined transcript.
    """
    try:
        if not request.refinedTranscript:
            raise HTTPException(status_code=400, detail="Refined transcript is required")
        
        notes = generate_university_notes(request.topic, request.refinedTranscript)
        
        return SummarizeResponse(
            success=True,
            notes=notes
        )
    except Exception as e:
        return SummarizeResponse(success=False, error=f"Summarization failed: {str(e)}")


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
        
        # Generate unique filename
        timestamp = int(time.time())
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in request.title)
        safe_title = safe_title.replace(' ', '_')[:50]
        filename = f"{safe_title}_{timestamp}.pdf"
        filepath = os.path.join(PDFS_DIR, filename)
        
        # Generate PDF
        create_pdf(request.notes, request.title, filepath)
        
        pdf_url = f"/pdfs/{filename}"
        note_id = None
        
        # Optionally save to database if moduleId is provided
        if request.moduleId:
            try:
                note = create_note_record(request.moduleId, request.title, pdf_url)
                if note:
                    note_id = note['id']
            except Exception as db_error:
                # PDF was generated but DB save failed - still return success
                logger.warning(f"Failed to save note to database: {db_error}")
        
        return GeneratePdfResponse(
            success=True,
            pdfUrl=pdf_url,
            noteId=note_id
        )
    except Exception as e:
        return GeneratePdfResponse(success=False, error=f"PDF generation failed: {str(e)}")


def _run_pipeline(job_id: str, audio_bytes: bytes, topic: str, module_id: Optional[str]):
    """Background task to run the full processing pipeline."""
    try:
        # Step 1: Transcribe
        job_status_store[job_id] = {
            'status': 'transcribing',
            'progress': 10,
            'message': 'Transcribing audio...'
        }
        
        result = process_audio_file(audio_bytes)
        transcript = result.get('text', '')
        
        if not transcript:
            raise ValueError("Transcription returned empty result")
        
        # Step 2: Refine
        job_status_store[job_id] = {
            'status': 'refining',
            'progress': 35,
            'message': 'Refining transcript...'
        }
        
        refined = transform_transcript(topic, transcript)
        
        # Step 3: Summarize
        job_status_store[job_id] = {
            'status': 'summarizing',
            'progress': 60,
            'message': 'Generating notes...'
        }
        
        notes = generate_university_notes(topic, refined)
        
        # Step 4: Generate PDF
        job_status_store[job_id] = {
            'status': 'generating_pdf',
            'progress': 85,
            'message': 'Creating PDF...'
        }
        
        os.makedirs(PDFS_DIR, exist_ok=True)
        timestamp = int(time.time())
        safe_title = "".join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in topic)
        safe_title = safe_title.replace(' ', '_')[:50]
        filename = f"{safe_title}_{timestamp}.pdf"
        filepath = os.path.join(PDFS_DIR, filename)
        
        create_pdf(notes, topic, filepath)
        pdf_url = f"/pdfs/{filename}"
        
        note_id = None
        if module_id:
            try:
                note = create_note_record(module_id, topic, pdf_url)
                if note:
                    note_id = note['id']
            except Exception:
                pass
        
        # Complete
        job_status_store[job_id] = {
            'status': 'complete',
            'progress': 100,
            'message': 'Processing complete!',
            'result': {
                'transcript': transcript,
                'refinedTranscript': refined,
                'notes': notes,
                'pdfUrl': pdf_url,
                'noteId': note_id
            }
        }
        
    except Exception as e:
        job_status_store[job_id] = {
            'status': 'error',
            'progress': 0,
            'message': f'Error: {str(e)}',
            'result': None
        }


@router.post("/process-pipeline")
async def start_pipeline(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    topic: str = Form(...),
    moduleId: Optional[str] = Form(None) # Updated to str
):
    """
    Start the full audio processing pipeline (async with status polling).
    Returns a job ID to poll for status.
    """
    try:
        audio_bytes = await file.read()
        
        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Empty audio file")
        
        # Validate file size
        validate_file_size(len(audio_bytes), MAX_AUDIO_SIZE, "Audio")
        
        # Create job
        job_id = str(uuid.uuid4())
        job_status_store[job_id] = {
            'status': 'pending',
            'progress': 0,
            'message': 'Starting pipeline...'
        }
        
        # Start background task
        background_tasks.add_task(_run_pipeline, job_id, audio_bytes, topic, moduleId)
        
        return {"jobId": job_id, "status": "pending"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/pipeline-status/{job_id}", response_model=PipelineStatusResponse)
async def get_pipeline_status(job_id: str):
    """
    Get the status of a processing pipeline job.
    """
    if job_id not in job_status_store:
        raise HTTPException(status_code=404, detail="Job not found")
    
    status = job_status_store[job_id]
    
    return PipelineStatusResponse(
        jobId=job_id,
        status=status['status'],
        progress=status['progress'],
        message=status.get('message'),
        result=status.get('result')
    )
