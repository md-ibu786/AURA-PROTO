"""
============================================================================
FILE: vertex_ai_client.py
LOCATION: services/vertex_ai_client.py
============================================================================

PURPOSE:
    Legacy Vertex AI façade backed by the shared model router.
    Preserves the historical NOTES import surface while delegating generation
    work to model_router compatibility helpers.

ROLE IN PROJECT:
    Compatibility layer for Vertex AI integration.
    - Maintains existing import surface for downstream services
    - Removes direct Google Vertex AI SDK dependencies from the app
    - Delegates to shared model_router for actual generation
    - Provides legacy error types for backward compatibility

KEY COMPONENTS:
    - GenerationConfig: Config shim for router translation
    - generate_content: Main generation function
    - VertexAIRequestError: Legacy error type for NOTES callers
    - SafetySetting: Placeholder for legacy type compatibility
    - Part: Minimal legacy part shim for older imports

DEPENDENCIES:
    - External: model_router (compat, errors, providers, router)
    - Internal: None

USAGE:
    from services.vertex_ai_client import generate_content, GenerationConfig

    config = GenerationConfig(temperature=0.7, max_output_tokens=1024)
    response = generate_content("gemini-pro", "Hello, world!", config)
============================================================================
"""

from __future__ import annotations

import os
from typing import Any, Optional

from model_router.compat import (
    VertexCompatModel,
    VertexCompatResponse,
    _extract_generation_config,
    _run_sync,
)
from model_router.errors import ModelRouterError
from model_router.providers.vertex_ai import _normalize_vertex_model_name
from model_router.router import get_default_router


class GenerationConfig:
    """Thin config shim storing kwargs for router translation."""

    def __init__(self, **kwargs: Any) -> None:
        self._kwargs = dict(kwargs)
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict copy of the stored config values."""
        return dict(self._kwargs)


class VertexAIRequestError(ModelRouterError):
    """Legacy error type preserved for existing NOTES callers."""

    def __init__(
        self,
        message: str = "",
        *,
        model: str = "",
        location: str = "",
        operation: str = "",
        original: BaseException | None = None,
        **kwargs: Any,
    ) -> None:
        details = message
        if not details and operation:
            details = (
                f"Vertex AI Gemini {operation} failed "
                f"(model={model or '<unknown>'!r}, "
                f"location={location or 'vertex_ai'!r})"
            )
            if original is not None:
                details = f"{details}: {original.__class__.__name__}: {original}"
        super().__init__(
            details or "Vertex AI request failed",
            provider="vertex_ai",
            model=model,
            original=original,
            **kwargs,
        )
        self.location = location or "vertex_ai"
        self.operation = operation


class SafetySetting:
    """Placeholder kept for legacy type compatibility."""


class Part:
    """Minimal legacy part shim retained for older imports/tests."""

    def __init__(self, text: str) -> None:
        self.text = text


GenerativeModel = VertexCompatModel


def init_vertex_ai(model_name: str | None = None) -> None:
    """No-op preserved for backwards compatibility."""
    del model_name


def normalize_model_name(model_name: str) -> str:
    """Normalize legacy `models/`-prefixed Vertex model identifiers."""
    if not isinstance(model_name, str) or not model_name.strip():
        raise ValueError("model_name must be a non-empty string")
    return _normalize_vertex_model_name(model_name)


def get_model(model_name: str) -> VertexCompatModel:
    """Return a model-router-backed legacy-compatible model wrapper."""
    if os.getenv("USE_MODEL_ROUTER", "").lower() == "true":
        try:
            import model_router.compat as compat_module

            return compat_module.VertexCompatModel(model_name)
        except ImportError:
            pass

    init_vertex_ai(model_name)
    normalized = normalize_model_name(model_name)
    return GenerativeModel(normalized)


def block_none_safety_settings() -> list[Any]:
    """Return a no-op safety settings override for legacy callers."""
    return []


def _operation_from_contents(contents: Any) -> str:
    """Classify the legacy request operation for error messages."""
    if isinstance(contents, str):
        return "text generation"
    return "multimodal generation"


def _model_name_from_model(model: Any) -> str:
    """Extract a model name from legacy wrappers for error reporting."""
    for attr in ("model_name", "_model_name"):
        value = getattr(model, attr, None)
        if isinstance(value, str) and value:
            return value
    return "<unknown>"


def generate_content(
    model: Any,
    contents: Any,
    *,
    generation_config: GenerationConfig | dict[str, Any] | None = None,
    safety_settings: Optional[list[Any]] = None,
) -> VertexCompatResponse:
    """Generate content through a compat model or direct router fallback."""
    try:
        if hasattr(model, "generate_content"):
            return model.generate_content(
                contents,
                generation_config=generation_config,
                safety_settings=safety_settings,
            )

        request_kwargs: dict[str, Any] = {
            "model": _model_name_from_model(model),
            "contents": contents,
        }
        request_kwargs.update(_extract_generation_config(generation_config))
        if safety_settings is not None:
            request_kwargs["safety_settings"] = safety_settings

        response = _run_sync(get_default_router().generate(**request_kwargs))
        return VertexCompatResponse(response.text, metadata=response.metadata)
    except Exception as error:
        model_name = _model_name_from_model(model)
        raise VertexAIRequestError(
            model=model_name,
            location="vertex_ai",
            operation=_operation_from_contents(contents),
            original=error,
        ) from error


__all__ = [
    "GenerationConfig",
    "Part",
    "GenerativeModel",
    "SafetySetting",
    "VertexAIRequestError",
    "block_none_safety_settings",
    "generate_content",
    "get_model",
    "init_vertex_ai",
    "normalize_model_name",
]
