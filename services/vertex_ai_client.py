"""
============================================================================
FILE: vertex_ai_client.py
LOCATION: services/vertex_ai_client.py
============================================================================

PURPOSE:
    Provides a thin wrapper around Google Vertex AI's Generative Models API.
    Handles SDK initialization, authentication, and provides convenient
    functions for text generation with proper error handling.

ROLE IN PROJECT:
    This is the foundational AI client used by both coc.py (transcript
    cleaning/auditing) and summarizer.py (note generation). It abstracts
    away Vertex AI initialization and provides consistent error handling.

KEY COMPONENTS:
    - VertexAIRequestError: Custom exception with context (model, location, operation)
    - init_vertex_ai(): Initialize SDK with ADC credentials
    - get_model(model_name): Get a GenerativeModel instance
    - generate_content(model, contents, generation_config): Generate text
    - block_none_safety_settings(): Disable safety filtering for academic content
    - normalize_model_name(): Strip "models/" prefix from model names

AUTHENTICATION:
    Uses Google Application Default Credentials (ADC). Set up via:
    - gcloud auth application-default login (development)
    - GOOGLE_APPLICATION_CREDENTIALS env var (service account)
    - VERTEX_CREDENTIALS env var (alternative path)

ENVIRONMENT VARIABLES:
    - VERTEX_PROJECT: GCP project ID (optional, auto-detected)
    - VERTEX_LOCATION: Model location (default: "global")
    - VERTEX_CREDENTIALS: Path to service account key (optional)
    - GOOGLE_APPLICATION_CREDENTIALS: Standard Google auth path

DEPENDENCIES:
    - External: google-auth, google-cloud-aiplatform, vertexai
    - Internal: None

USAGE:
    from services.vertex_ai_client import get_model, generate_content, GenerationConfig
    
    model = get_model("models/gemini-3-flash-preview")
    response = generate_content(
        model,
        "Explain quantum computing",
        generation_config=GenerationConfig(temperature=0.7, max_output_tokens=2048)
    )
    print(response.text)
============================================================================
"""
import json
import os
from typing import Optional

import google.auth
import vertexai

try:
    from vertexai.generative_models import (
        GenerationConfig,
        GenerativeModel,
        HarmBlockThreshold,
        HarmCategory,
        Part,
        SafetySetting,
    )
except Exception:  # pragma: no cover
    from vertexai.preview.generative_models import (  # type: ignore
        GenerationConfig,
        GenerativeModel,
        HarmBlockThreshold,
        HarmCategory,
        Part,
        SafetySetting,
    )

_LOCATION = os.environ.get("VERTEX_LOCATION", "global")
_INITIALIZED = False


class VertexAIRequestError(RuntimeError):
    def __init__(
        self,
        *,
        model: str | None,
        location: str,
        operation: str,
        original: BaseException,
    ) -> None:
        safe_model = model if isinstance(model, str) else "<unknown>"
        message = (
            f"Vertex AI Gemini {operation} failed "
            f"(model={safe_model!r}, location={location!r}): "
            f"{original.__class__.__name__}: {original}"
        )
        super().__init__(message)

        self.model = safe_model
        self.location = location
        self.operation = operation
        self.original = original


def _read_project_id_from_credentials_file(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        project_id = data.get("project_id")
        return project_id if isinstance(project_id, str) else None
    except Exception:
        return None


def _get_project_id() -> Optional[str]:
    # First, check for explicit VERTEX_PROJECT env var (preferred for multi-project setups)
    explicit_project = os.environ.get("VERTEX_PROJECT")
    if explicit_project:
        return explicit_project

    # Fallback to google.auth.default
    _, project_id = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])  # type: ignore
    if project_id:
        return project_id

    # Final fallback: read from credentials file
    creds_path = os.environ.get("VERTEX_CREDENTIALS") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_path:
        return _read_project_id_from_credentials_file(creds_path)

    return None


def init_vertex_ai() -> None:
    global _INITIALIZED

    if _INITIALIZED:
        return

    # Set GOOGLE_APPLICATION_CREDENTIALS from VERTEX_CREDENTIALS if not already set
    vertex_creds = os.environ.get("VERTEX_CREDENTIALS")
    if vertex_creds and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
        # Resolve relative path
        if not os.path.isabs(vertex_creds):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            vertex_creds = os.path.normpath(os.path.join(project_root, vertex_creds))
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = vertex_creds

    try:
        google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "Vertex AI requires Application Default Credentials (ADC). "
            "Authenticate with `gcloud auth application-default login` or set "
            "GOOGLE_APPLICATION_CREDENTIALS to a service account JSON file."
        ) from e

    project_id = _get_project_id()
    if not project_id:
        raise RuntimeError(
            "Could not determine GCP project_id from ADC. Ensure your ADC source "
            "includes a project (for example, a service account JSON containing "
            "project_id)."
        )

    vertexai.init(project=project_id, location=_LOCATION)
    _INITIALIZED = True


def normalize_model_name(model_name: str) -> str:
    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("model_name must be a non-empty string")

    normalized = model_name.strip()
    if normalized.startswith("models/"):
        normalized = normalized[len("models/") :]

    return normalized


def get_model(model_name: str) -> GenerativeModel:
    init_vertex_ai()

    normalized = normalize_model_name(model_name)
    try:
        return GenerativeModel(normalized)
    except Exception as e:
        raise VertexAIRequestError(
            model=model_name,
            location=_LOCATION,
            operation="model load",
            original=e,
        ) from e


def block_none_safety_settings() -> list[SafetySetting]:
    return [
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=HarmBlockThreshold.BLOCK_NONE,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=HarmBlockThreshold.BLOCK_NONE,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=HarmBlockThreshold.BLOCK_NONE,
        ),
        SafetySetting(
            category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=HarmBlockThreshold.BLOCK_NONE,
        ),
    ]


def _operation_from_contents(contents) -> str:
    if isinstance(contents, str):
        return "text generation"
    return "multimodal generation"


def _model_name_from_model(model: GenerativeModel) -> str:
    for attr in ("model_name", "_model_name"):
        name = getattr(model, attr, None)
        if isinstance(name, str) and name:
            return name
    return "<unknown>"


def generate_content(
    model: GenerativeModel,
    contents,
    *,
    generation_config: GenerationConfig,
    safety_settings: Optional[list[SafetySetting]] = None,
):
    try:
        return model.generate_content(
            contents,
            generation_config=generation_config,
            safety_settings=safety_settings,
        )
    except Exception as e:
        raise VertexAIRequestError(
            model=_model_name_from_model(model),
            location=_LOCATION,
            operation=_operation_from_contents(contents),
            original=e,
        ) from e


__all__ = [
    "GenerationConfig",
    "Part",
    "VertexAIRequestError",
    "get_model",
    "block_none_safety_settings",
    "generate_content",
    "normalize_model_name",
]
