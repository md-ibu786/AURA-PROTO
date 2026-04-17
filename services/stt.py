"""
============================================================================
FILE: stt.py
LOCATION: services/stt.py
============================================================================

PURPOSE:
    Provide Deepgram speech-to-text transcription for audio inputs.

ROLE IN PROJECT:
    Used by api/audio_processing.py to transcribe uploaded audio recordings
    before refinement, summarization, and PDF generation.

KEY COMPONENTS:
    - _read_audio_bytes: Normalize input into raw audio bytes
    - _transcribe_with_deepgram: SDK v5 Deepgram call
    - process_audio_file: Main entry point returning transcript + raw response

DEPENDENCIES:
    - External: deepgram-sdk>=5.0.0
    - Internal: None

USAGE:
    process_audio_file(audio_bytes)
============================================================================
"""

import io
import os
from typing import Any, BinaryIO, Dict, Optional, Union

from deepgram import DeepgramClient


def _read_audio_bytes(audio_input: Union[BinaryIO, bytes, io.BytesIO]) -> bytes:
    """
    Reads audio data from various input types (bytes, file-like objects,
    Streamlit UploadedFile) and returns raw bytes.
    """
    if isinstance(audio_input, (bytes, bytearray)):
        return bytes(audio_input)

    # Streamlit UploadedFile supports getvalue(); prefer it to avoid
    # consuming the stream for callers.
    if hasattr(audio_input, "getvalue"):
        data = audio_input.getvalue()  # type: ignore[union-attr]
        return bytes(data) if isinstance(data, (bytes, bytearray)) else bytes()

    # File-like object (standard Python file object)
    if hasattr(audio_input, "seek"):
        try:
            audio_input.seek(0)
        except Exception:
            pass

    return audio_input.read()


def _transcribe_with_deepgram(
    deepgram: DeepgramClient,
    audio_bytes: bytes,
    options: Dict[str, Any],
    timeout: Optional[float] = None,
) -> Any:
    """
    Call Deepgram transcription with SDK version compatibility.

    Supports:
    - SDK v5+: deepgram.listen.v1.media.transcribe_file(...)

    Note: Deepgram SDK v5 uses:
    - request= for audio bytes (not source=)
    - Options passed as kwargs (not options dict)
    - request_options for timeout
    """
    listen = getattr(deepgram, "listen", None)
    if listen is None:
        raise RuntimeError("Deepgram client does not expose listen API.")

    # Build request_options for timeout (SDK v5 style)
    request_options = None
    if timeout is not None:
        request_options = {"timeout_in_seconds": int(timeout)}

    # SDK v5+ path: deepgram.listen.v1.media.transcribe_file(...)
    if hasattr(listen, "v1") and hasattr(listen.v1, "media"):
        if request_options:
            return listen.v1.media.transcribe_file(
                request=audio_bytes,
                request_options=request_options,
                **options,
            )
        return listen.v1.media.transcribe_file(
            request=audio_bytes,
            **options,
        )

    raise RuntimeError("Unsupported Deepgram SDK API surface.")


def process_audio_file(
    audio_input: Union[BinaryIO, bytes, io.BytesIO],
    timeout_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Process an audio file using Deepgram Nova-3 and return the transcript.

    Args:
        audio_input: A file-like object (from Streamlit's file uploader)
            or raw bytes containing audio data.
        timeout_seconds: Optional timeout in seconds. Defaults to 10800 (3 hours)
            for long audio files like 2-hour recordings.

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
            "Audio input was empty. If using Streamlit, ensure the uploaded "
            "file is only processed once (or use UploadedFile.getvalue())."
        )

    # Default timeout: 10 minutes for audio transcription
    if timeout_seconds is None:
        timeout_seconds = 600.0

    # Initialize Deepgram client
    try:
        deepgram = DeepgramClient(api_key=api_key)

        # Options are passed as kwargs (v5+) or as a dict (v3.x).
        options = {
            "model": "nova-3",
            "smart_format": True,
            "diarize": True,
            "utterances": True,
        }

        response = _transcribe_with_deepgram(
            deepgram,
            audio_bytes,
            options,
            timeout=timeout_seconds,
        )

        # Extract transcript
        # Deepgram Nova-3 with smart_format typically returns formatted
        # paragraphs.
        transcript_text = ""
        if response and response.results and response.results.channels:
            channel = response.results.channels[0]
            if channel.alternatives:
                # Use 'paragraphs' if available for better formatting, and
                # fall back to 'transcript' when paragraphs are missing.
                alt = channel.alternatives[0]
                if hasattr(alt, "paragraphs") and alt.paragraphs:
                    transcript_text = alt.paragraphs.transcript
                else:
                    transcript_text = alt.transcript

        return {
            "text": transcript_text,
            # Ensure we return a serializable dict, not the Deepgram object
            "full_response": (
                response.to_dict() if hasattr(response, "to_dict") else response
            ),
        }

    except Exception as e:
        raise Exception(f"Deepgram transcription failed: {str(e)}") from e
