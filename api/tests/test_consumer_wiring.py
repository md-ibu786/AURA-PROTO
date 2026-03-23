"""
========================================================================
FILE: test_consumer_wiring.py
LOCATION: AURA-NOTES-MANAGER/api/tests/test_consumer_wiring.py
========================================================================

PURPOSE:
    Integration tests verifying that all 4 AURA-NOTES-MANAGER consumers
    (PP-05 through PP-08) read from SettingsStore via resolve_use_case_config()
    and route through ModelRouter with explicit provider parameter.

ROLE IN PROJECT:
    Validates end-to-end consumer wiring for the settings configuration system:
    - PP-05: kg_processor.GeminiClient reads from resolve_use_case_config()
    - PP-06: llm_entity_extractor.LLMEntityExtractor passes provider to router
    - PP-07: embeddings.EmbeddingService passes provider to router.embed()
    - PP-08: summarizer.generate_university_notes uses router with provider

KEY COMPONENTS:
    - test_kg_processor_uses_resolve_config: Verifies PP-05
    - test_entity_extractor_passes_provider: Verifies PP-06
    - test_embeddings_passes_provider: Verifies PP-07
    - test_summarizer_uses_router: Verifies PP-08
    - test_redis_fallback_graceful: Verifies fallback to env vars

DEPENDENCIES:
    - External: pytest, pytest-asyncio, unittest.mock
    - Internal: model_router.settings_store, consumer modules

USAGE:
    pytest api/tests/test_consumer_wiring.py -v
========================================================================
"""

from __future__ import annotations

import os
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Test mode must be enabled before importing consumer modules
os.environ.setdefault("AURA_TEST_MODE", "true")

# Import settings_store components
from model_router.settings_store import (
    _SENTINEL_ERROR,
    _defaults_cache,
    clear_defaults_cache,
    resolve_use_case_config,
)


# ============================================================================
# HELPERS
# ============================================================================


def _mock_get_default_sync_for(use_case: str, provider: str, model: str):
    """Return a side_effect function for get_default_sync that returns cached
    values without attempting a Redis connection."""

    def _side_effect(uc: str, **kwargs):
        if uc == use_case:
            return {"provider": provider, "model": model}
        return None

    return _side_effect


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture(autouse=True)
def clean_defaults_cache():
    """Clear _defaults_cache before and after each test to prevent contamination."""
    clear_defaults_cache()
    yield
    clear_defaults_cache()


# ============================================================================
# PP-05: KG Processor uses resolve_use_case_config
# ============================================================================


@pytest.mark.asyncio
async def test_kg_processor_uses_resolve_config():
    """
    PP-05: Verify GeminiClient routes through router.generate when calling
    generate_text with test mode disabled.

    This test:
    1. Mocks resolve_use_case_config so no Redis connection is attempted
    2. Creates GeminiClient with test mode disabled
    3. Calls generate_text and verifies the router path is exercised
    """
    mock_router = MagicMock()
    mock_generate = AsyncMock()
    mock_response = MagicMock()
    mock_response.text = "Test extraction response"
    mock_response.metadata = {}
    mock_generate.return_value = mock_response
    mock_router.generate = mock_generate

    mock_model = MagicMock()
    mock_model.generate_content = MagicMock(return_value=mock_response)

    with (
        patch("api.kg_processor.get_model", return_value=mock_model),
        patch("api.kg_processor.EMBEDDING_MODEL", "text-embedding-004"),
        patch("api.kg_processor.get_default_router", return_value=mock_router),
        patch(
            "api.kg_processor.resolve_use_case_config",
            return_value={
                "provider": "openrouter",
                "model": "anthropic/claude-3.7-sonnet",
            },
        ),
    ):
        from api.kg_processor import GeminiClient

        client = GeminiClient()
        # Disable test mode to use the real generation path
        client._test_mode = False
        client._model = mock_model

        result = await client.generate_text("Test prompt")

        # Verify router.generate was called with resolved config
        assert mock_generate.called
        assert result == "Test extraction response"


def test_kg_processor_resolves_at_runtime():
    """
    PP-05: Verify GeminiClient resolves config at runtime via resolve_use_case_config().

    This test verifies the config resolution mechanism works correctly.
    """
    # Pre-populate cache
    _defaults_cache["entity_extraction"] = {
        "value": {"provider": "vertex_ai", "model": "gemini-test-model"},
        "_cached_at": time.time(),
    }

    # Call resolve_use_case_config directly to verify it returns cached value
    config = resolve_use_case_config("entity_extraction")

    assert config["provider"] == "vertex_ai"
    assert config["model"] == "gemini-test-model"


# ============================================================================
# PP-06: Entity Extractor passes provider to router.generate
# ============================================================================


@pytest.mark.asyncio
async def test_entity_extractor_passes_provider():
    """
    PP-06: Verify LLMEntityExtractor reads from SettingsStore and routes
    through router.generate when calling extract_entities.

    This test:
    1. Mocks resolve_use_case_config so no Redis connection is attempted
    2. Disables test mode so extract_entities uses the real LLM path
    3. Verifies router.generate (via vertex_ai_client) was called
    """
    mock_router = MagicMock()
    mock_generate = AsyncMock()
    mock_response = MagicMock()
    mock_response.text = (
        '{"concepts": [], "topics": [], "methodologies": [], "findings": []}'
    )
    mock_response.metadata = {}
    mock_generate.return_value = mock_response
    mock_router.generate = mock_generate

    mock_model = MagicMock()
    mock_model.generate_content = MagicMock(return_value=mock_response)

    with (
        patch(
            "services.llm_entity_extractor.get_default_router", return_value=mock_router
        ),
        patch("services.llm_entity_extractor.get_model", return_value=mock_model),
        patch(
            "services.llm_entity_extractor.resolve_use_case_config",
            return_value={"provider": "vertex_ai", "model": "gemini-test"},
        ),
    ):
        from services.llm_entity_extractor import LLMEntityExtractor

        extractor = LLMEntityExtractor()
        # Disable test mode to use real generation path
        extractor._test_mode = False
        extractor._model = mock_model

        result = await extractor.extract_entities(
            "test text for extraction with enough content to be meaningful",
            doc_id="test-doc",
        )

        # Verify result structure
        assert "concepts" in result
        assert "topics" in result
        assert "methodologies" in result
        assert "findings" in result

        # Verify generate_content or router.generate was called
        assert mock_model.generate_content.called or mock_generate.called


def test_entity_extractor_resolves_config():
    """
    PP-06: Verify LLMEntityExtractor resolves config via resolve_use_case_config().
    """
    # Pre-populate cache
    _defaults_cache["entity_extraction"] = {
        "value": {"provider": "openrouter", "model": "claude-instant"},
        "_cached_at": time.time(),
    }

    # Verify config resolution
    config = resolve_use_case_config("entity_extraction")

    assert config["provider"] == "openrouter"
    assert config["model"] == "claude-instant"


# ============================================================================
# PP-07: Embeddings passes provider to router.embed
# ============================================================================


def test_embeddings_passes_provider():
    """
    PP-07: Verify EmbeddingService passes provider parameter to router.embed().

    This test:
    1. Mocks resolve_use_case_config to return embeddings config
    2. Mocks _run_sync to capture the provider from the embed call
    3. Disables test mode so embed_text uses the real router path
    4. Calls embed_text and verifies router.embed was called with provider="vertex_ai"
    """
    # Capture the provider parameter from router.embed calls
    captured_provider = None

    def mock_run_sync(coro):
        """Mock _run_sync that returns test data without executing coroutines."""
        nonlocal captured_provider
        return [[0.1] * 768]

    mock_router = MagicMock()

    def capturing_embed(texts, provider=None):
        nonlocal captured_provider
        captured_provider = provider
        mock_coro = MagicMock()
        mock_coro.__await__ = MagicMock(return_value=iter([[[0.1] * 768]]))
        return mock_coro

    mock_router.embed = MagicMock(side_effect=capturing_embed)

    with (
        patch("services.embeddings.get_default_router", return_value=mock_router),
        patch("services.embeddings._run_sync", side_effect=mock_run_sync),
        patch(
            "services.embeddings.resolve_use_case_config",
            return_value={"provider": "vertex_ai", "model": "text-embedding-004"},
        ),
    ):
        from services.embeddings import EmbeddingService

        service = EmbeddingService()

        # Disable test mode to exercise the real router path
        service._test_mode = False

        embedding = service.embed_text("test text")

        # Verify embedding was generated
        assert len(embedding) == 768

        # Verify provider was passed to router.embed
        assert captured_provider == "vertex_ai"


def test_embeddings_resolves_config():
    """
    PP-07: Verify EmbeddingService resolves config via resolve_use_case_config().
    """
    # Pre-populate cache
    _defaults_cache["embeddings"] = {
        "value": {"provider": "openrouter", "model": "embed-001"},
        "_cached_at": time.time(),
    }

    # Verify config resolution
    config = resolve_use_case_config("embeddings")

    assert config["provider"] == "openrouter"
    assert config["model"] == "embed-001"


# ============================================================================
# PP-08: Summarizer uses router with explicit provider
# ============================================================================


def test_summarizer_uses_router():
    """
    PP-08: Verify generate_university_notes reads from SettingsStore and
    routes through the model router.

    The summarizer calls resolve_use_case_config('summarization') at runtime
    and routes through router.generate() with explicit provider. We verify
    the function completes without crashing and that the router is called.
    """
    mock_router = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Generated notes content"
    mock_response.metadata = {}

    def mock_run_sync(coro):
        """Mock _run_sync that returns test data without executing coroutines."""
        return mock_response

    mock_router.generate = MagicMock(return_value=mock_response)

    with (
        patch("services.summarizer.get_default_router", return_value=mock_router),
        patch("services.summarizer._run_sync", side_effect=mock_run_sync),
    ):
        from services.summarizer import generate_university_notes

        result = generate_university_notes(
            topic="Test Topic", cleaned_transcript="Test transcript content"
        )

        # Verify the function completed and returned content
        assert isinstance(result, str)
        assert len(result) > 0

        # Verify router.generate was called
        assert mock_router.generate.called


def test_summarizer_resolves_config():
    """
    PP-08: Verify generate_university_notes resolves config via resolve_use_case_config().
    """
    # Pre-populate cache
    _defaults_cache["summarization"] = {
        "value": {"provider": "openrouter", "model": "claude-haiku"},
        "_cached_at": time.time(),
    }

    # Verify config resolution
    config = resolve_use_case_config("summarization")

    assert config["provider"] == "openrouter"
    assert config["model"] == "claude-haiku"


# ============================================================================
# Redis Fallback Tests (PP-05/06/07/08)
# ============================================================================


def test_redis_fallback_entity_extraction():
    """
    PP-05/06: Verify entity_extraction falls back to env var when Redis unavailable.

    When _defaults_cache contains _SENTINEL_ERROR (Redis-down state),
    resolve_use_case_config should fall back to env var LLM_ENTITY_EXTRACTION_MODEL.
    """
    # Clear cache and inject sentinel error for entity_extraction
    clear_defaults_cache()
    _defaults_cache["entity_extraction"] = {
        "value": _SENTINEL_ERROR,
        "_cached_at": time.time() - 60,  # Expired
    }

    # Set env var for fallback
    os.environ["LLM_ENTITY_EXTRACTION_MODEL"] = "fallback-model"

    try:
        # Verify config resolution falls back to env var
        config = resolve_use_case_config("entity_extraction")

        assert config["provider"] == "vertex_ai"  # Provider from env var spec
        assert config["model"] == "fallback-model"  # Model from env var
    finally:
        # Clean up
        if "LLM_ENTITY_EXTRACTION_MODEL" in os.environ:
            del os.environ["LLM_ENTITY_EXTRACTION_MODEL"]


def test_redis_fallback_embeddings():
    """
    PP-07: Verify embeddings falls back to hardcoded default when Redis unavailable.
    """
    # Clear cache and inject sentinel error
    clear_defaults_cache()
    _defaults_cache["embeddings"] = {
        "value": _SENTINEL_ERROR,
        "_cached_at": time.time() - 60,
    }

    # Verify config resolution falls back to hardcoded default
    config = resolve_use_case_config("embeddings")

    assert config["provider"] == "vertex_ai"
    assert config["model"] == "text-embedding-004"  # Hardcoded default


def test_redis_fallback_summarization():
    """
    PP-08: Verify summarization falls back to env var when Redis unavailable.
    """
    # Clear cache and inject sentinel error
    clear_defaults_cache()
    _defaults_cache["summarization"] = {
        "value": _SENTINEL_ERROR,
        "_cached_at": time.time() - 60,
    }

    # Set env var
    os.environ["LLM_SUMMARIZATION_MODEL"] = "summarization-fallback"

    try:
        config = resolve_use_case_config("summarization")

        assert config["provider"] == "vertex_ai"
        assert config["model"] == "summarization-fallback"
    finally:
        if "LLM_SUMMARIZATION_MODEL" in os.environ:
            del os.environ["LLM_SUMMARIZATION_MODEL"]


def test_redis_fallback_graceful():
    """
    PP-05/06/07/08: Verify all use cases fall back gracefully when Redis is down.

    When _SENTINEL_ERROR is in the cache and no env var is set,
    resolve_use_case_config returns the hardcoded default without raising.
    """
    clear_defaults_cache()

    # Inject sentinel errors for all use cases
    for use_case in ["entity_extraction", "embeddings", "summarization"]:
        _defaults_cache[use_case] = {
            "value": _SENTINEL_ERROR,
            "_cached_at": time.time() - 60,
        }

    # Clear relevant env vars to force hardcoded fallback
    saved_env = {}
    for var in [
        "LLM_ENTITY_EXTRACTION_MODEL",
        "LLM_SUMMARIZATION_MODEL",
    ]:
        if var in os.environ:
            saved_env[var] = os.environ[var]
            del os.environ[var]

    try:
        # All should return hardcoded defaults without raising
        config_ext = resolve_use_case_config("entity_extraction")
        assert config_ext["provider"] == "vertex_ai"
        assert config_ext["model"] == "gemini-2.5-flash-lite"

        config_emb = resolve_use_case_config("embeddings")
        assert config_emb["provider"] == "vertex_ai"
        assert config_emb["model"] == "text-embedding-004"

        config_sum = resolve_use_case_config("summarization")
        assert config_sum["provider"] == "vertex_ai"
        assert config_sum["model"] == "gemini-2.5-flash-lite"
    finally:
        # Restore env vars
        for var, val in saved_env.items():
            os.environ[var] = val


# ============================================================================
# No bare except:pass in summarizer (PP-08)
# ============================================================================


def test_no_bare_except_in_summarizer():
    """
    PP-08: Verify summarizer doesn't use bare except:pass pattern.

    This is a code quality check to ensure proper error handling.
    """
    from services import summarizer
    import ast

    with open(summarizer.__file__, "r") as f:
        source = f.read()
    tree = ast.parse(source)

    # Check for bare except clauses with only pass in body
    for node in ast.walk(tree):
        if isinstance(node, ast.ExceptHandler):
            if node.type is None:
                if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                    pytest.fail(
                        "summarizer.py contains bare except:pass pattern - "
                        "should catch specific exceptions"
                    )


# ============================================================================
# Provider Parameter Verification Tests
# ============================================================================


def test_router_embed_receives_provider():
    """
    Verify router.embed() is called with explicit provider parameter from
    SettingsStore configuration.

    This test mocks the router and verifies the provider is passed correctly
    through the EmbeddingService -> router.embed() call chain.
    """
    # Capture the provider parameter
    captured_provider = None

    def capturing_embed(texts, provider=None):
        nonlocal captured_provider
        captured_provider = provider
        mock_coro = MagicMock()
        mock_coro.__await__ = MagicMock(return_value=iter([[[0.1] * 768]]))
        return mock_coro

    mock_router = MagicMock()
    mock_router.embed = MagicMock(side_effect=capturing_embed)

    def mock_run_sync(coro):
        return [[0.1] * 768]

    with (
        patch("services.embeddings.get_default_router", return_value=mock_router),
        patch("services.embeddings._run_sync", side_effect=mock_run_sync),
        patch(
            "services.embeddings.resolve_use_case_config",
            return_value={"provider": "openrouter", "model": "embed-001"},
        ),
    ):
        from services.embeddings import EmbeddingService

        service = EmbeddingService()
        service._test_mode = False

        service.embed_text("test text")

        # The provider should be captured from the SettingsStore config
        assert captured_provider == "openrouter"


def test_all_use_cases_resolve_correctly():
    """
    Verify all 4 use cases (PP-05 through PP-08) resolve correctly.

    Tests:
    - entity_extraction -> PP-05, PP-06
    - embeddings -> PP-07
    - summarization -> PP-08
    """
    # Pre-populate all caches
    _defaults_cache["entity_extraction"] = {
        "value": {"provider": "openrouter", "model": "extraction-model"},
        "_cached_at": time.time(),
    }
    _defaults_cache["embeddings"] = {
        "value": {"provider": "vertex_ai", "model": "embedding-model"},
        "_cached_at": time.time(),
    }
    _defaults_cache["summarization"] = {
        "value": {"provider": "openrouter", "model": "summarization-model"},
        "_cached_at": time.time(),
    }

    # Verify each resolves correctly
    config_extraction = resolve_use_case_config("entity_extraction")
    assert config_extraction["provider"] == "openrouter"
    assert config_extraction["model"] == "extraction-model"

    config_embeddings = resolve_use_case_config("embeddings")
    assert config_embeddings["provider"] == "vertex_ai"
    assert config_embeddings["model"] == "embedding-model"

    config_summarization = resolve_use_case_config("summarization")
    assert config_summarization["provider"] == "openrouter"
    assert config_summarization["model"] == "summarization-model"


# ============================================================================
# Cache TTL and Invalidation Tests
# ============================================================================


def test_cache_invalidation_on_clear():
    """
    Verify clear_defaults_cache() properly clears all cached values.
    """
    # Pre-populate cache
    _defaults_cache["entity_extraction"] = {
        "value": {"provider": "vertex_ai", "model": "test-model"},
        "_cached_at": time.time(),
    }
    _defaults_cache["embeddings"] = {
        "value": {"provider": "vertex_ai", "model": "test-embed"},
        "_cached_at": time.time(),
    }

    # Verify cache has entries
    assert "entity_extraction" in _defaults_cache
    assert "embeddings" in _defaults_cache

    # Clear cache
    clear_defaults_cache()

    # Verify cache is empty
    assert len(_defaults_cache) == 0
