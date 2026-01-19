"""
============================================================================
FILE: test_vertex_models.py
LOCATION: tools/test_vertex_models.py
============================================================================

PURPOSE:
    Validation script to test Vertex AI Gemini model connectivity and
    functionality. Sends simple prompts to verify that models respond
    correctly and optionally tests multimodal (audio+text) capabilities.

ROLE IN PROJECT:
    Development/debugging utility for:
    - Verifying API credentials are correctly configured
    - Testing model availability before deploying
    - Comparing response quality between different model versions
    - Debugging audio transcription issues

KEY FEATURES:
    - Tests multiple models in sequence (default: Gemini 2.5, 3, 2.0 Flash)
    - Simple text prompt test (default: "Reply with exactly: OK")
    - Optional multimodal smoke test with synthetic or real audio
    - FFmpeg audio conversion for non-WAV files

COMMAND LINE OPTIONS:
    --models: Comma-separated list of model names to test
    --prompt: Custom test prompt
    --multimodal-smoke: Include synthetic audio test
    --audio: Path to real audio file for testing
    --credentials: Path to service account JSON
    --location: Vertex AI location (default: global)

DEPENDENCIES:
    - External: google-cloud-aiplatform, vertexai
    - Internal: services/vertex_ai_client.py
    - Optional: ffmpeg (for audio conversion)

USAGE:
    # Basic text test
    python tools/test_vertex_models.py
    
    # Test with real audio
    python tools/test_vertex_models.py --audio sample.mp3
    
    # Custom credentials
    python tools/test_vertex_models.py --credentials path/to/key.json
============================================================================
"""
import argparse
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Iterable

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.vertex_ai_client import (  # noqa: E402
    GenerationConfig,
    Part,
    block_none_safety_settings,
    generate_content,
    get_model,
)


DEFAULT_MODELS = (
    "models/gemini-2.5-flash",
    "models/gemini-3-flash-preview",
    "models/gemini-2.0-flash-001",
)


def iter_models(csv: str | None) -> Iterable[str]:
    if not csv:
        return DEFAULT_MODELS
    return [m.strip() for m in csv.split(",") if m.strip()]


def _synthetic_wav_header() -> bytes:
    # Minimal WAV header (no data); useful for payload sanity.
    return (
        b"RIFF"
        + (36).to_bytes(4, "little")
        + b"WAVEfmt "
        + (16).to_bytes(4, "little")
        + (1).to_bytes(2, "little")
        + (1).to_bytes(2, "little")
        + (16000).to_bytes(4, "little")
        + (32000).to_bytes(4, "little")
        + (2).to_bytes(2, "little")
        + (16).to_bytes(2, "little")
        + b"data"
        + (0).to_bytes(4, "little")
    )


def _convert_to_wav(path: str) -> bytes:
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "output.wav")
        proc = subprocess.run(
            ["ffmpeg", "-y", "-i", path, "-ac", "1", "-ar", "16000", out_path],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            stderr_tail = (proc.stderr or "")[-1000:]
            raise RuntimeError(f"ffmpeg conversion failed: {stderr_tail}")
        with open(out_path, "rb") as f:
            return f.read()


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send a simple prompt to each Vertex Gemini model for validation."
    )
    parser.add_argument(
        "--models",
        help="Comma-separated model names (default: repo models)",
    )
    parser.add_argument(
        "--prompt",
        default="Reply with exactly: OK",
        help="Test prompt sent to each model",
    )
    parser.add_argument(
        "--multimodal-smoke",
        action="store_true",
        help="Also send a synthetic audio+text request (payload sanity check).",
    )
    parser.add_argument(
        "--audio",
        help="Path to a real audio file to test audio+text requests (will be converted to WAV).",
    )
    parser.add_argument(
        "--credentials",
        help="Path to service account JSON. Sets GOOGLE_APPLICATION_CREDENTIALS for this run.",
    )
    parser.add_argument(
        "--location",
        help="Vertex location (sets VERTEX_LOCATION). Default is global.",
    )

    args = parser.parse_args()

    if args.credentials:
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = args.credentials

    if args.location:
        os.environ["VERTEX_LOCATION"] = args.location

    audio_bytes: bytes | None = None
    if args.audio:
        audio_bytes = _convert_to_wav(args.audio)

    had_error = False

    for model_name in iter_models(args.models):
        print(f"\n== {model_name} ==")
        try:
            model = get_model(model_name)

            response = generate_content(
                model,
                args.prompt,
                generation_config=GenerationConfig(temperature=0.0),
                safety_settings=block_none_safety_settings(),
            )
            text = getattr(response, "text", "") or ""
            print(f"Text Response: {text[:200]}")

            if args.multimodal_smoke or audio_bytes is not None:
                mm_audio = audio_bytes if audio_bytes is not None else _synthetic_wav_header()
                mm_response = generate_content(
                    model,
                    [Part.from_data(mm_audio, mime_type="audio/wav"), Part.from_text(args.prompt)],
                    generation_config=GenerationConfig(temperature=0.0),
                    safety_settings=block_none_safety_settings(),
                )
                mm_text = getattr(mm_response, "text", "") or ""
                print(f"Audio+Text Response: {mm_text[:200]}")
        except Exception as e:
            had_error = True
            print(f"ERROR: {e.__class__.__name__}: {e}")

    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
