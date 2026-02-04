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
import sys
from typing import Any

from services.vertex_ai_client import GenerationConfig, generate_content

_TEST_MODE = os.getenv("AURA_TEST_MODE", "").lower() == "true"

if _TEST_MODE:
    genai = None
    GENAI_AVAILABLE = False
elif (
    ("google.genai" in sys.modules and sys.modules["google.genai"] is None)
    or (
        "google.generativeai" in sys.modules
        and sys.modules["google.generativeai"] is None
    )
):
    genai = None
    GENAI_AVAILABLE = False
else:
    try:
        from google import genai as genai
        if genai is None:
            raise ImportError("google.genai not available")
        GENAI_AVAILABLE = True
    except Exception:
        try:
            import google.generativeai as genai
            if genai is None:
                raise ImportError("google.generativeai not available")
            GENAI_AVAILABLE = True
        except Exception:
            genai = None
            GENAI_AVAILABLE = False


def get_genai_model(model_name: str) -> Any | None:
    if not GENAI_AVAILABLE or genai is None:
        return None

    try:
        api_key = (
            os.getenv("GOOGLE_API_KEY")
            or os.getenv("GOOGLE_GENAI_API_KEY")
            or os.getenv("GOOGLE_GENERATIVEAI_API_KEY")
            or os.getenv("GENAI_API_KEY")
        )
        if hasattr(genai, "configure"):
            if api_key:
                genai.configure(api_key=api_key)
            else:
                genai.configure()
        return genai.GenerativeModel(model_name)
    except Exception:
        return None


def generate_content_with_thinking(model: Any, prompt: str) -> Any:
    if model is None:
        raise RuntimeError("GenAI model is not available")

    if hasattr(model, "generate_content"):
        return model.generate_content(prompt)

    return generate_content(
        model,
        prompt,
        generation_config=GenerationConfig(
            temperature=0.2,
            max_output_tokens=4096,
        ),
    )
