# vertex_ai_client.py
# =========================
#
# Thin wrapper around Google Vertex AI's Generative Models API for Gemini text generation.
#
# Features:
# ---------
# - Handles Google Application Default Credentials (ADC) authentication
# - Provides convenient functions for model loading and text generation
# - Implements custom exception with context (model, location, operation)
# - Disables safety filtering for academic content via block_none_safety_settings()
# - Supports both preview and stable vertexai SDK imports
#
# Classes/Functions:
# ------------------
# - VertexAIRequestError: Custom exception with model, location, operation, and original error
# - init_vertex_ai(): Initializes SDK with ADC credentials
# - get_model(model_name): Returns a GenerativeModel instance
# - generate_content(model, contents, generation_config): Generates text from model
# - block_none_safety_settings(): Returns list disabling all safety filtering
# - normalize_model_name(model_name): Strips "models/" prefix from model names
#
# @see coc.py - Uses for transcript cleaning/auditing
# @see summarizer.py - Uses for note generation
# @note Requires VERTEX_PROJECT and VERTEX_LOCATION env vars; uses GCP ADC authentication
# @note Gemini 3 models automatically use "global" location regardless of VERTEX_LOCATION setting

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

_LOCATION = os.environ.get("VERTEX_LOCATION", "us-central1")
_INITIALIZED = False
_CURRENT_LOCATION: str | None = None


def _is_gemini3_model(model_name: str | None) -> bool:
    """Check if the model is a Gemini 3 model that requires global location.

    Gemini 3 preview models are only available through the global endpoint.

    Args:
        model_name: The model name to check.

    Returns:
        True if the model is a Gemini 3 model.
    """
    if not model_name:
        return False
    normalized = model_name.lower()
    return "gemini-3" in normalized or "gemini3" in normalized


def _normalize_location(location: str, model_name: str | None = None) -> str:
    """Normalize location for Vertex AI SDK compatibility.

    For Gemini 3 preview models, always use "global" location as they are
    only available through the global endpoint. For other models, uses the
    configured VERTEX_LOCATION or defaults to us-central1.

    Args:
        location: The requested location.
        model_name: Optional model name to check for Gemini 3 models.

    Returns:
        The location to use for Vertex AI initialization.
    """
    # Gemini 3 models require global location
    if _is_gemini3_model(model_name):
        return "global"

    # For other locations, keep as-is (us-central1 or user-specified)
    return location


class _TestGenerativeModel:
    def __init__(self, model_name: str) -> None:
        self._model_name = model_name

    def generate_content(self, *args, **kwargs):
        class _TestResponse:
            def __init__(self, text: str) -> None:
                self.text = text

        return _TestResponse("Test-mode notes output.")


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
    _, project_id = google.auth.default(
        scopes=["https://www.googleapis.com/auth/cloud-platform"]
    )  # type: ignore
    if project_id:
        return project_id

    # Final fallback: read from credentials file
    creds_path = os.environ.get("VERTEX_CREDENTIALS") or os.environ.get(
        "GOOGLE_APPLICATION_CREDENTIALS"
    )
    if creds_path:
        return _read_project_id_from_credentials_file(creds_path)

    return None


def init_vertex_ai(model_name: str | None = None) -> None:
    """Initialize Vertex AI with appropriate location for the model.

    Args:
        model_name: Optional model name to determine location. Gemini 3 models
            will use "global" location, others will use VERTEX_LOCATION.
    """
    global _INITIALIZED, _CURRENT_LOCATION

    # Determine the required location for this model
    required_location = _normalize_location(_LOCATION, model_name)

    # If already initialized with the same location, skip re-initialization
    if _INITIALIZED and _CURRENT_LOCATION == required_location:
        return

    if os.getenv("AURA_TEST_MODE", "").lower() == "true":
        _INITIALIZED = True
        _CURRENT_LOCATION = required_location
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

    vertexai.init(project=project_id, location=required_location)
    _INITIALIZED = True
    _CURRENT_LOCATION = required_location


def normalize_model_name(model_name: str) -> str:
    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("model_name must be a non-empty string")

    normalized = model_name.strip()
    if normalized.startswith("models/"):
        normalized = normalized[len("models/") :]

    return normalized


def get_model(model_name: str) -> GenerativeModel:
    if os.getenv("AURA_TEST_MODE", "").lower() == "true":
        return _TestGenerativeModel(model_name)

    init_vertex_ai(model_name)

    normalized = normalize_model_name(model_name)
    try:
        return GenerativeModel(normalized)
    except Exception as e:
        raise VertexAIRequestError(
            model=model_name,
            location=_normalize_location(_LOCATION, model_name),
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
