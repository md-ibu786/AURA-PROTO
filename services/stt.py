"""
Speech-to-Text Backend ModuleTTThis module provides the backend processing functionality for audio files.
Currently implements a placeholder interface for audio file processing.
"""
from typing import BinaryIO, Union
import io
import mimetypes
import os
import subprocess
import tempfile

from services.vertex_ai_client import (
    GenerationConfig,
    Part,
    block_none_safety_settings,
    generate_content,
    get_model,
)


def _read_audio_bytes(audio_input: Union[BinaryIO, bytes, io.BytesIO]) -> bytes:
    if isinstance(audio_input, (bytes, bytearray)):
        return bytes(audio_input)

    # Streamlit UploadedFile supports getvalue(); prefer it to avoid
    # consuming the stream for callers.
    if hasattr(audio_input, "getvalue"):
        data = audio_input.getvalue()
        return bytes(data) if isinstance(data, (bytes, bytearray)) else bytes()

    # File-like object
    if hasattr(audio_input, "seek"):
        try:
            audio_input.seek(0)
        except Exception:
            pass

    return audio_input.read()


def _guess_mime_type(audio_input) -> str:
    mime_type = "audio/wav"
    if hasattr(audio_input, "type") and isinstance(getattr(audio_input, "type"), str):
        return audio_input.type

    if hasattr(audio_input, "name") and isinstance(getattr(audio_input, "name"), str):
        guessed, _ = mimetypes.guess_type(audio_input.name)
        if guessed:
            return guessed

    return mime_type


def _ensure_wav_mono_16k(audio_bytes: bytes, mime_type: str, filename: str | None) -> tuple[bytes, str]:
    # Vertex audio support is finicky across containers/codecs.
    # Normalize aggressively to 16kHz mono WAV.
    if mime_type in {"audio/wav", "audio/x-wav"}:
        return audio_bytes, "audio/wav"

    suffix = ".bin"
    if filename:
        _, ext = os.path.splitext(filename)
        if ext:
            suffix = ext

    with tempfile.TemporaryDirectory() as tmpdir:
        in_path = os.path.join(tmpdir, f"input{suffix}")
        out_path = os.path.join(tmpdir, "output.wav")

        with open(in_path, "wb") as f:
            f.write(audio_bytes)

        proc = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                in_path,
                "-ac",
                "1",
                "-ar",
                "16000",
                out_path,
            ],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            stderr_tail = (proc.stderr or "")[-1000:]
            raise RuntimeError(f"ffmpeg conversion failed: {stderr_tail}")

        with open(out_path, "rb") as f:
            wav_bytes = f.read()

    return wav_bytes, "audio/wav"


def process_audio_file(
    audio_input: Union[BinaryIO, bytes, io.BytesIO]
) -> str:

    """
    Process an audio file and return a confirmation message.

    Args:
        audio_input: A file-like object (from Streamlit's file uploader) 
                    or raw bytes containing audio data

    Returns:
        str: A confirmation message indicating successful processing.

    Note:
        This is currently a placeholder function. Actual speech-to-text
        logic will be implemented in future iterations.
    """
    
    audio_bytes = _read_audio_bytes(audio_input)
    if not audio_bytes:
        raise ValueError(
            "Audio input was empty. If using Streamlit, ensure the uploaded file "
            "is only processed once (or use UploadedFile.getvalue())."
        )

    filename = (
        getattr(audio_input, "name", None)
        if not isinstance(audio_input, (bytes, bytearray))
        else None
    )
    mime_type = _guess_mime_type(audio_input)
    audio_bytes, mime_type = _ensure_wav_mono_16k(audio_bytes, mime_type, filename)

    audio_part = Part.from_data(data=audio_bytes, mime_type=mime_type)

    # usage of models/gemini-2.5-flash
    model = get_model(model_name="models/gemini-2.5-flash")

    
    # define the prompt for transcription
    prompt = """
        ROLE:
        You are a precision transcription engine specialized in academic lectures. Your sole function is to convert the provided audio stream into text with 100% fidelity.

        TASK:
        Transcribe the accompanying audio file of a university lecture exactly as spoken.

        STRICT CONSTRAINTS (MUST FOLLOW):
        1. VERBATIM ONLY: Do not summarize, condense, or capture "key points." Write down every word spoken by the lecturer.
        2. NO HALLUCINATION: If a segment is inaudible or unintelligible, mark it as [INAUDIBLE]. Do not invent words to complete sentences.
        3. NO FILLER ADDITIONS: Do not add introductory phrases like "Here is the transcript" or "The lecturer says." Start directly with the first spoken word.
        4. PRESERVE CONTEXT: Maintain the exact phrasing and terminology used by the lecturer, even if it seems grammatically imperfect. Do not "autocorrect" the lecturer's speech.
        5. FORMATTING: Output the text as a continuous stream or naturally paragraphed text based on the speaker's pauses. Do not use bullet points or markdown headers unless the speaker explicitly dictates them.

        OUTPUT:
        Produce the raw transcript only.
        
        Begin!!
    """
    
    # generate content using the uploaded audio file
    # deterministic (recommended for transcription)
    api_response = generate_content(
        model,
        [audio_part, Part.from_text(prompt)],
        generation_config=GenerationConfig(temperature=0.0),
        safety_settings=block_none_safety_settings(),
    )


    response_text = getattr(api_response, "text", None)
    if not response_text:
        # Handle empty response (silence)
        candidates = getattr(api_response, "candidates", None) or []
        if candidates:
            finish_reason = getattr(candidates[0], "finish_reason", None)
            if finish_reason == 1:
                return "[SILENCE]"
            raise ValueError(
                "Gemini blocked the transcription. Finish reason: "
                f"{finish_reason if finish_reason is not None else 'Unknown'}"
            )

        return "[SILENCE]"

    # Return transcription
    return response_text

