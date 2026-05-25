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

DEFAULT_TRANSCRIPTION_TIMEOUT_SECONDS = float(
    os.getenv("DEEPGRAM_TIMEOUT_SECONDS", str(3 * 3600 + 300))
)


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


def _extract_duration_seconds(response: Any, response_data: Any) -> float:
    """Extract audio duration in seconds from Deepgram response metadata."""
    # SDK object path
    try:
        metadata = getattr(response, "metadata", None)
        if metadata is not None:
            duration = getattr(metadata, "duration", None)
            if duration is not None:
                return float(duration)
    except (TypeError, ValueError):
        pass

    # Serialized dict path
    if isinstance(response_data, dict):
        metadata = response_data.get("metadata")
        if isinstance(metadata, dict) and metadata.get("duration") is not None:
            try:
                return float(metadata["duration"])
            except (TypeError, ValueError):
                return 0.0

    return 0.0


def process_audio_file(
    audio_input: Union[BinaryIO, bytes, io.BytesIO],
    timeout_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Process an audio file using Deepgram Nova-3 and return the transcript.

    Args:
        audio_input: A file-like object (from Streamlit's file uploader)
            or raw bytes containing audio data.
        timeout_seconds: Optional timeout in seconds. Defaults to
            DEFAULT_TRANSCRIPTION_TIMEOUT_SECONDS (~3h 5m), aligned with
            audio-processing max duration constraints.

    Returns:
        dict: A dictionary containing:
              - "text": The full transcript text.
              - "duration": Duration in seconds (0 when unavailable).
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

    # Default timeout aligned with server-side max audio duration.
    if timeout_seconds is None:
        timeout_seconds = DEFAULT_TRANSCRIPTION_TIMEOUT_SECONDS

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

        # Ensure we return a serializable dict, not the Deepgram object.
        response_data = (
            response.to_dict() if hasattr(response, "to_dict") else response
        )

        # Extract transcript
        # Deepgram Nova-3 with smart_format typically returns formatted
        # paragraphs.
        transcript_text = ""
        if (
            response
            and hasattr(response, "results")
            and response.results
            and response.results.channels
        ):
            channel = response.results.channels[0]
            if channel.alternatives:
                # Use 'paragraphs' if available for better formatting, and
                # fall back to 'transcript' when paragraphs are missing.
                alt = channel.alternatives[0]
                if hasattr(alt, "paragraphs") and alt.paragraphs:
                    transcript_text = alt.paragraphs.transcript
                else:
                    transcript_text = alt.transcript
        elif isinstance(response_data, dict):
            channels = (
                response_data.get("results", {})
                .get("channels", [])
            )
            if channels:
                alternatives = channels[0].get("alternatives", [])
                if alternatives:
                    alt = alternatives[0]
                    paragraphs = alt.get("paragraphs")
                    if isinstance(paragraphs, dict):
                        transcript_text = paragraphs.get("transcript", "")
                    if not transcript_text:
                        transcript_text = alt.get("transcript", "")

        return {
            "text": transcript_text,
            "duration": _extract_duration_seconds(response, response_data),
            "full_response": response_data,
        }

    except Exception as e:
        raise Exception(f"Deepgram transcription failed: {str(e)}") from e
