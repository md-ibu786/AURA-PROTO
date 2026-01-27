# genai_client.py
# Backward-compatible Gemini client shim using Vertex AI
#
# Provides a lightweight wrapper that preserves the legacy API for modules
# still calling `get_genai_model` and `generate_content_with_thinking` while
# delegating to Vertex AI via services/vertex_ai_client.
#
# @see: services/vertex_ai_client.py - Primary Vertex AI integration
# @note: Uses ADC authentication; no API key configuration required

from __future__ import annotations

import os
from typing import Any

from services.vertex_ai_client import GenerationConfig, generate_content, get_model


_TEST_MODE = os.getenv("AURA_TEST_MODE", "").lower() == "true"
GENAI_AVAILABLE = True


def get_genai_model(model_name: str) -> Any | None:
    if not GENAI_AVAILABLE:
        return None

    try:
        return get_model(model_name)
    except Exception:
        return None


def generate_content_with_thinking(model: Any, prompt: str) -> Any:
    if model is None:
        raise RuntimeError("GenAI model is not available")

    return generate_content(
        model,
        prompt,
        generation_config=GenerationConfig(
            temperature=0.2,
            max_output_tokens=4096,
        ),
    )
