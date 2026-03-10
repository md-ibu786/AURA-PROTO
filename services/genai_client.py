# genai_client.py
# Model-router-backed GenAI client shim for legacy NOTES call sites.

# Preserves the old helper names used by summarizer.py while removing all
# direct Google GenAI SDK imports from the app. Returned models are shared
# router compatibility wrappers that match the previous generate_content API.

# @see: services/vertex_ai_client.py
# @note: `genai` remains exported as None for older monkeypatch-based tests.

"""Model-router-backed GenAI client shim for legacy NOTES call sites."""

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
