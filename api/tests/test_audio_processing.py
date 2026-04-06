"""
============================================================================
FILE: test_audio_processing.py
LOCATION: api/tests/test_audio_processing.py
============================================================================

PURPOSE:
    Unit tests for audio_processing.py error handling and silent failure remediation.

ROLE IN PROJECT:
    Validates that database failures in the audio pipeline are properly logged
    and communicated to users via structured warnings instead of silent pass.

KEY COMPONENTS:
    - test_pipeline_db_failure_logged: Tests that _run_pipeline logs errors with exc_info
    - test_generate_pdf_db_failure_warning: Tests that generate_pdf endpoint returns warning
    - test_pipeline_noteid_none_on_failure: Tests that noteId is None when DB fails
    - test_db_failure_logged_with_exc_info: Tests logger.error called with exc_info=True

DEPENDENCIES:
    - External: pytest, unittest.mock
    - Internal: api.audio_processing

USAGE:
    pytest api/tests/test_audio_processing.py -v
============================================================================
"""

import pytest
from unittest.mock import patch, MagicMock
import sys
import os
import logging

# Add the api directory to path to import audio_processing directly
# without triggering api/__init__.py which imports kg_processor ->_firestore
_api_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

# Import audio_processing module directly (bypasses api/__init__.py)
import audio_processing as ap_module


class TestPipelineDBFailureHandling:
    """Tests for database failure handling in _run_pipeline."""

    def test_pipeline_db_failure_logged(self):
        """Test that _run_pipeline logs DB failures and populates warnings."""
        # Setup: Create job status entry
        job_id = "test-job-123"
        ap_module.job_status_store[job_id] = {
            "status": "pending",
            "progress": 0,
            "message": "Starting...",
        }

        # Mock services to succeed
        with (
            patch("api.audio_processing.process_audio_file") as mock_transcribe,
            patch("api.audio_processing.transform_transcript") as mock_refine,
            patch("api.audio_processing.generate_university_notes") as mock_summarize,
            patch("api.audio_processing.create_pdf") as mock_pdf,
            patch("api.audio_processing.create_note_record") as mock_create_note,
        ):
            # All services succeed except DB
            mock_transcribe.return_value = {"text": "Test transcript"}
            mock_refine.return_value = "Refined transcript"
            mock_summarize.return_value = "Generated notes"
            mock_pdf.return_value = None
            # DB save fails
            mock_create_note.side_effect = Exception("Database connection failed")

            # Run pipeline
            ap_module._run_pipeline(
                job_id=job_id,
                audio_bytes=b"fake audio",
                topic="Test Topic",
                module_id="module-123",
            )

        # Verify job status has warnings
        status = ap_module.job_status_store[job_id]
        assert "warnings" in status, "Warnings field should be present on DB failure"
        assert len(status["warnings"]) > 0, "Warnings array should not be empty"
        assert "Database connection failed" in status["warnings"][0], (
            "Warning should contain error message"
        )

    def test_pipeline_noteid_none_on_failure(self):
        """Test that noteId is None when database save fails."""
        job_id = "test-job-456"
        ap_module.job_status_store[job_id] = {
            "status": "pending",
            "progress": 0,
            "message": "Starting...",
        }

        with (
            patch("api.audio_processing.process_audio_file") as mock_transcribe,
            patch("api.audio_processing.transform_transcript") as mock_refine,
            patch("api.audio_processing.generate_university_notes") as mock_summarize,
            patch("api.audio_processing.create_pdf") as mock_pdf,
            patch("api.audio_processing.create_note_record") as mock_create_note,
        ):
            mock_transcribe.return_value = {"text": "Test transcript"}
            mock_refine.return_value = "Refined transcript"
            mock_summarize.return_value = "Generated notes"
            mock_pdf.return_value = None
            mock_create_note.side_effect = Exception("DB error")

            ap_module._run_pipeline(
                job_id=job_id,
                audio_bytes=b"fake audio",
                topic="Test Topic",
                module_id="module-456",
            )

        status = ap_module.job_status_store[job_id]
        # Verify noteId is None when DB fails
        assert "result" in status, "Result should be present"
        assert status["result"]["noteId"] is None, (
            "noteId should be None when DB save fails"
        )

    def test_db_failure_logged_with_exc_info(self):
        """Test that logger.error is called with exc_info=True on DB failure."""
        job_id = "test-job-789"
        ap_module.job_status_store[job_id] = {
            "status": "pending",
            "progress": 0,
            "message": "Starting...",
        }

        # Create a mock logger to capture calls
        mock_logger = MagicMock()

        with (
            patch("api.audio_processing.process_audio_file") as mock_transcribe,
            patch("api.audio_processing.transform_transcript") as mock_refine,
            patch("api.audio_processing.generate_university_notes") as mock_summarize,
            patch("api.audio_processing.create_pdf") as mock_pdf,
            patch("api.audio_processing.create_note_record") as mock_create_note,
            patch("api.audio_processing.logger", mock_logger),
        ):
            mock_transcribe.return_value = {"text": "Test transcript"}
            mock_refine.return_value = "Refined transcript"
            mock_summarize.return_value = "Generated notes"
            mock_pdf.return_value = None
            mock_create_note.side_effect = Exception("DB connection error")

            ap_module._run_pipeline(
                job_id=job_id,
                audio_bytes=b"fake audio",
                topic="Test Topic",
                module_id="module-789",
            )

        # Verify logger.error was called with exc_info=True
        error_calls = [call for call in mock_logger.error.call_args_list]
        assert len(error_calls) > 0, "logger.error should be called on DB failure"

        # Check that at least one error call has exc_info=True
        has_exc_info = any(
            call.kwargs.get("exc_info") == True or "exc_info" in call.kwargs
            for call in error_calls
        )
        assert has_exc_info, "logger.error should be called with exc_info=True"


class TestGeneratePdfDBFailureHandling:
    """Tests for database failure handling in generate_pdf endpoint."""

    @pytest.mark.asyncio
    async def test_generate_pdf_db_failure_warning(self):
        """Test that generate_pdf returns warning field when DB save fails."""
        from api.audio_processing import GeneratePdfRequest

        request = GeneratePdfRequest(
            title="Test Note", notes="Test content", moduleId="module-abc"
        )

        with (
            patch("api.audio_processing.create_pdf") as mock_pdf,
            patch("api.audio_processing.create_note_record") as mock_create_note,
        ):
            mock_pdf.return_value = None  # PDF creation succeeds
            mock_create_note.side_effect = Exception("Database timeout")

            # Import and call endpoint directly
            from api.audio_processing import generate_pdf

            response = await generate_pdf(request)

        # Verify response has warning field
        assert hasattr(response, "warning"), (
            "GeneratePdfResponse should have warning field"
        )
        assert response.warning is not None, "Warning should be populated when DB fails"
        assert "Database timeout" in response.warning, (
            "Warning should contain error message"
        )
        assert response.success is True, (
            "Success should still be True (PDF was created)"
        )
        assert response.noteId is None, "noteId should be None when DB save fails"

    @pytest.mark.asyncio
    async def test_logger_error_called_in_generate_pdf(self):
        """Test that logger.error is called with exc_info in generate_pdf."""
        from api.audio_processing import GeneratePdfRequest
        from unittest.mock import AsyncMock

        request = GeneratePdfRequest(
            title="Test Note 2", notes="Test content 2", moduleId="module-xyz"
        )

        mock_logger = MagicMock()

        with (
            patch("api.audio_processing.create_pdf") as mock_pdf,
            patch("api.audio_processing.create_note_record") as mock_create_note,
            patch("api.audio_processing.logger", mock_logger),
        ):
            mock_pdf.return_value = None
            mock_create_note.side_effect = Exception("DB error in pdf")

            from api.audio_processing import generate_pdf

            await generate_pdf(request)

        # Verify logger.error was called with exc_info
        error_calls = [call for call in mock_logger.error.call_args_list]
        assert len(error_calls) > 0, "logger.error should be called"

        has_exc_info = any(call.kwargs.get("exc_info") == True for call in error_calls)
        assert has_exc_info, "logger.error should have exc_info=True"
