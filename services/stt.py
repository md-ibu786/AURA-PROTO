"""
============================================================================
FILE: stt.py (Speech-to-Text)
LOCATION: services/stt.py
============================================================================

PURPOSE:
    Provides audio transcription functionality using Deepgram's Nova-3 model.
    Converts audio files (MP3, WAV, M4A, etc.) into text transcripts with
    speaker diarization and smart formatting.

ROLE IN PROJECT:
    This is the first step in the audio-to-notes pipeline. When a user
    uploads an audio recording through the React frontend, this service
    transcribes it to text, which then flows to coc.py for cleaning.

KEY COMPONENTS:
    - _read_audio_bytes(audio_input): Convert various input types to raw bytes
    - process_audio_file(audio_input): Main transcription function

DEEPGRAM CONFIGURATION:
    - Model: Nova-3 (latest, highest quality)
    - Smart format: True (punctuation, capitalization)
    - Diarization: True (speaker identification)
    - Utterances: True (sentence-level segmentation)

RETURN FORMAT:
    {
        "text": "The full transcript text...",
        "full_response": { ... Deepgram raw response ... }
    }

DEPENDENCIES:
    - External: deepgram-sdk (Deepgram API client)
    - Internal: None

ENVIRONMENT VARIABLES:
    - DEEPGRAM_API_KEY: Required API key for Deepgram service

USAGE:
    from services.stt import process_audio_file
    
    # From file bytes
    with open("lecture.mp3", "rb") as f:
        result = process_audio_file(f.read())
    
    transcript = result["text"]
============================================================================
"""
from typing import BinaryIO, Union, Dict, Any
import io
import os

from deepgram import DeepgramClient

def _read_audio_bytes(audio_input: Union[BinaryIO, bytes, io.BytesIO]) -> bytes:
    """
    Reads audio data from various input types (bytes, file-like objects, Streamlit UploadedFile)
    and returns raw bytes.
    """
    if isinstance(audio_input, (bytes, bytearray)):
        return bytes(audio_input)

    # Streamlit UploadedFile supports getvalue(); prefer it to avoid
    # consuming the stream for callers.
    if hasattr(audio_input, "getvalue"):
        data = audio_input.getvalue()
        return bytes(data) if isinstance(data, (bytes, bytearray)) else bytes()

    # File-like object (standard Python file object)
    if hasattr(audio_input, "seek"):
        try:
            audio_input.seek(0)
        except Exception:
            pass

    return audio_input.read()


def process_audio_file(
    audio_input: Union[BinaryIO, bytes, io.BytesIO]
) -> Dict[str, Any]:

    """
    Process an audio file using Deepgram Nova-3 and return the transcript.

    Args:
        audio_input: A file-like object (from Streamlit's file uploader) 
                    or raw bytes containing audio data

    Returns:
        dict: A dictionary containing:
              - "text": The full transcript text.
              - "full_response": The raw JSON response from Deepgram.
    
    Raises:
        ValueError: If DEEPGRAM_API_KEY is missing or input is empty.
        Exception: If the Deepgram API call fails.
    """
    
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        raise ValueError("DEEPGRAM_API_KEY environment variable is not set.")

    audio_bytes = _read_audio_bytes(audio_input)
    if not audio_bytes:
        raise ValueError(
            "Audio input was empty. If using Streamlit, ensure the uploaded file "
            "is only processed once (or use UploadedFile.getvalue())."
        )

    # Initialize Deepgram client
    try:
        deepgram = DeepgramClient(api_key=api_key)

        # Deepgram SDK v5.x does not use PrerecordedOptions; pass options directly.
        options = {
            "model": "nova-3",
            "smart_format": True,
            "diarize": True,
            "utterances": True,
        }

        # SDK expects a `request=` kwarg (raw bytes, or an iterator)
        response = deepgram.listen.v1.media.transcribe_file(request=audio_bytes, **options)
        
        # Extract transcript
        # Deepgram Nova-3 with smart_format typically returns nicely formatted paragraphs.
        transcript_text = ""
        if response and response.results and response.results.channels:
            channel = response.results.channels[0]
            if channel.alternatives:
                # Use 'paragraphs' if available for better formatting, fallback to 'transcript'
                alt = channel.alternatives[0]
                if hasattr(alt, "paragraphs") and alt.paragraphs:
                    transcript_text = alt.paragraphs.transcript
                else:
                    transcript_text = alt.transcript

        return {
            "text": transcript_text,
            # Ensure we return a serializable dict, not the Deepgram object
            "full_response": response.to_dict() if hasattr(response, "to_dict") else response
        }

    except Exception as e:
        raise Exception(f"Deepgram transcription failed: {str(e)}") from e