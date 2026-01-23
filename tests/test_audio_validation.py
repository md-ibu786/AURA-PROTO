# test_audio_validation.py
# API tests for audio validation and transcription error handling
#
# Covers validation and error reporting for audio transcription routes.
#
# @see: api/audio_processing.py - Transcription endpoint behavior
# @note: Uses TestClient without external services

import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app

client = TestClient(app)

def test_transcribe_with_unsupported_format():
    """Should return 400 for unsupported audio formats."""
    file_content = b"this is a text file, not audio"
    files = {"file": ("test.txt", file_content, "text/plain")}
    
    response = client.post("/api/audio/transcribe", files=files)
    
    # Existing behavior might be different, but we want 400
    assert response.status_code == 400
    assert "Unsupported file format" in response.json()["detail"]

def test_transcribe_with_very_small_file():
    """Should return 400 for files that are too small to be valid audio."""
    file_content = b"1234567890"
    files = {"file": ("test.mp3", file_content, "audio/mpeg")}
    
    response = client.post("/api/audio/transcribe", files=files)
    
    assert response.status_code == 400
    assert "File too small" in response.json()["detail"]

@patch("api.audio_processing.process_audio_file")
def test_transcribe_deepgram_timeout(mock_process):
    """Should handle Deepgram timeouts gracefully."""
    mock_process.side_effect = Exception("Deepgram transcription failed: Operation timed out")
    
    # Use larger buffer to bypass MIN_AUDIO_SIZE (1024)
    file_content = b"fake audio content" * 100
    files = {"file": ("test.mp3", file_content, "audio/mpeg")}
    
    response = client.post("/api/audio/transcribe", files=files)
    
    assert response.status_code == 200
    assert response.json()["success"] is False
    error_text = response.json()["error"].lower()
    assert "timed out" in error_text or "transcription failed" in error_text
