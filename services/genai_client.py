"""
============================================================================
FILE: genai_client.py
LOCATION: services/genai_client.py
============================================================================

PURPOSE:
    Model-router-backed GenAI client shim for legacy NOTES call sites.
    Preserves the old helper names used by summarizer.py while removing all
    direct Google GenAI SDK imports from the app.

ROLE IN PROJECT:
    Compatibility layer for Google GenAI integration.
    - Maintains legacy helper names for existing code
    - Delegates to shared model_router for actual generation
    - Returns compatibility wrappers matching old generate_content API
    - Exports genai as None for monkeypatch-based tests

KEY COMPONENTS:
    - GENAI_AVAILABLE: Dynamic availability flag respecting sys.modules
    - get_genai_model: Returns model-router-backed model for legacy callers
    - generate_content_with_thinking: Thinking-friendly config generation
    - _GenaiAvailability: Internal class for availability detection

DEPENDENCIES:
    - External: model_router (compat), sys
    - Internal: services.vertex_ai_client (GenerationConfig, generate_content)

USAGE:
    from services.genai_client import get_genai_model, generate_content_with_thinking

    model = get_genai_model("gemini-pro")
    response = generate_content_with_thinking(model, "Explain quantum computing")
============================================================================
"""

from __future__ import annotations

import sys
from typing import Any

from model_router.compat import VertexCompatModel

from services.vertex_ai_client import GenerationConfig, generate_content

genai = None


class _GenaiAvailability:
    """Dynamic availability flag that respects sys.modules patching in tests."""

    def __bool__(self) -> bool:
        return not (
            ("google.genai" in sys.modules and sys.modules["google.genai"] is None)
            or (
                "google.generativeai" in sys.modules
                and sys.modules["google.generativeai"] is None
            )
        )


GENAI_AVAILABLE = _GenaiAvailability()


def get_genai_model(model_name: str) -> VertexCompatModel:
    """Return a model-router-backed model for legacy genai callers."""
    if (
        bool(GENAI_AVAILABLE)
        and genai is not None
        and hasattr(genai, "GenerativeModel")
    ):
        return genai.GenerativeModel(model_name)
    return VertexCompatModel(model_name)


def generate_content_with_thinking(model: Any, prompt: str) -> Any:
    """Generate content with a legacy thinking-friendly config surface."""
    config = GenerationConfig(
        temperature=0.2,
        max_output_tokens=4096,
    )
    if hasattr(model, "generate_content"):
        return model.generate_content(prompt, generation_config=config)
    return generate_content(model, prompt, generation_config=config)


__all__ = [
    "GENAI_AVAILABLE",
    "genai",
    "generate_content_with_thinking",
    "get_genai_model",
]
