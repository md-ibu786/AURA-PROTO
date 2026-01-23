# genai_client.py
# GenAI client helper for Gemini models via google.genai/generativeai
#
# Provides a lightweight wrapper for optional GenAI usage with graceful
# fallback when the package or API key is unavailable.
#
# @see: services/summarizer.py - Uses GenAI when available
# @note: Set GENAI_API_KEY or GOOGLE_API_KEY to enable

from __future__ import annotations

import os
import sys
from typing import Any


_TEST_MODE = os.getenv("AURA_TEST_MODE", "").lower() == "true"
_PYTEST_CONTEXT = os.getenv("PYTEST_CURRENT_TEST") is not None
_EXPLICITLY_DISABLED = (
    ("google.genai" in sys.modules and sys.modules.get("google.genai") is None)
    or (
        "google.generativeai" in sys.modules
        and sys.modules.get("google.generativeai") is None
    )
    or (
        _PYTEST_CONTEXT
        and sys.modules.get("google.genai") is None
        and sys.modules.get("google.generativeai") is None
    )
)

if _TEST_MODE and os.getenv("GENAI_FORCE_AVAILABLE", "").lower() != "true":
    genai = None  # type: ignore
    GENAI_AVAILABLE = False
elif _EXPLICITLY_DISABLED:
    genai = None  # type: ignore
    GENAI_AVAILABLE = False
else:
    try:
        import google.genai as genai  # type: ignore
        if genai is None:  # pragma: no cover - defensive for patched modules
            raise ImportError("google.genai unavailable")
        GENAI_AVAILABLE = True
    except Exception:  # pragma: no cover
        try:
            import google.generativeai as genai  # type: ignore
            if genai is None:  # pragma: no cover - defensive for patched modules
                raise ImportError("google.generativeai unavailable")
            GENAI_AVAILABLE = True
        except Exception:
            genai = None  # type: ignore
            GENAI_AVAILABLE = False


def _get_api_key() -> str | None:
    return os.getenv("GENAI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def get_genai_model(model_name: str) -> Any | None:
    if not GENAI_AVAILABLE or genai is None:
        return None

    api_key = _get_api_key()
    if not api_key and os.getenv("AURA_TEST_MODE", "").lower() != "true":
        return None
    if not api_key:
        api_key = "test-key"

    if hasattr(genai, "configure"):
        genai.configure(api_key=api_key)

    if hasattr(genai, "GenerativeModel"):
        return genai.GenerativeModel(model_name)

    return None


def generate_content_with_thinking(model: Any, prompt: str) -> Any:
    if model is None:
        raise RuntimeError("GenAI model is not available")

    return model.generate_content(prompt)
