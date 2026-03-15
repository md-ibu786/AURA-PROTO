"""
============================================================================
FILE: embeddings.py
LOCATION: services/embeddings.py
============================================================================

PURPOSE:
    Embedding service façade backed by the shared model router with batching,
    retry logic, rate limiting, and convenience helpers for generating text embeddings.

ROLE IN PROJECT:
    Central service for generating embeddings used by knowledge graph processing
    and entity deduplication. Delegates actual requests to model_router while
    preserving existing API contracts for backward compatibility.
    - Key responsibility 1: Batch embedding generation with retry logic
    - Key responsibility 2: Rate limiting and error handling for embedding requests

KEY COMPONENTS:
    - EmbeddingService: Main class for embedding generation with caching
    - batch_embed: Batch processing with configurable batch size
    - embed: Single text embedding with retry logic
    - cosine_similarity: Utility for computing similarity between embeddings

DEPENDENCIES:
    - External: model_router (internal router for Vertex AI)
    - Internal: None (standalone service)

USAGE:
    from services.embeddings import EmbeddingService
    service = EmbeddingService()
    embedding = service.embed("text to embed")
============================================================================
"""

from __future__ import annotations

import logging
import os
import random
import re
import sys
import time
import unicodedata
from functools import lru_cache
from typing import Any, Dict, List, Optional

from model_router import get_default_router
from model_router.compat import _run_sync
from model_router.errors import ModelRouterError, RateLimitError

_api_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "api"))
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

try:
    from config import EMBEDDING_MODEL
except ImportError:
    from api.config import EMBEDDING_MODEL

EMBEDDING_DIMENSIONS = 768
EMBEDDING_BATCH_SIZE = 100
RATE_LIMIT_RPM = 60
MAX_RETRIES = 3
RETRY_BACKOFF_INITIAL = 1.0
RETRY_BACKOFF_MULTIPLIER = 2.0
RETRY_BACKOFF_MAX = 30.0
MAX_TEXT_LENGTH = 30000

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Embedding service for generating 768-dimensional text embeddings."""

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL,
        api_key: str | None = None,
    ) -> None:
        self.model_name = model_name
        self._test_mode = os.getenv("AURA_TEST_MODE", "").lower() == "true"

        self.batch_size = EMBEDDING_BATCH_SIZE
        self.rpm_limit = RATE_LIMIT_RPM
        self.max_retries = MAX_RETRIES
        self.backoff_initial = RETRY_BACKOFF_INITIAL
        self.backoff_multiplier = RETRY_BACKOFF_MULTIPLIER
        self.backoff_max = RETRY_BACKOFF_MAX

        self._requests_made = 0
        self._window_start = time.time()

        self._cache: Dict[str, List[float]] = {}
        self._cache_enabled = False
        self._cache_max_size = 1000

        if api_key:
            logger.warning("EmbeddingService no longer uses API keys; ignoring api_key")

        if self._test_mode:
            logger.info(
                "EmbeddingService initialized in test mode "
                f"(dimensions: {EMBEDDING_DIMENSIONS})"
            )
        else:
            logger.info(
                "EmbeddingService initialized with model: %s",
                self.model_name,
            )

    def enable_cache(self, max_size: int = 1000) -> None:
        """Enable in-memory caching for repeated texts."""
        self._cache_enabled = True
        self._cache_max_size = max_size
        logger.info("Embedding cache enabled (max_size=%s)", max_size)

    def disable_cache(self) -> None:
        """Disable caching and clear cache."""
        self._cache_enabled = False
        self._cache.clear()

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._cache.clear()

    def _get_cached(self, text: str) -> Optional[List[float]]:
        """Get embedding from cache if available."""
        if not self._cache_enabled:
            return None
        return self._cache.get(text)

    def _set_cached(self, text: str, embedding: List[float]) -> None:
        """Store embedding in cache."""
        if not self._cache_enabled:
            return

        if len(self._cache) >= self._cache_max_size:
            keys_to_remove = list(self._cache.keys())[: self._cache_max_size // 10]
            for key in keys_to_remove:
                del self._cache[key]

        self._cache[text] = embedding

    def _rate_limit(self) -> None:
        """Apply rate limiting to stay under RPM limit."""
        now = time.time()
        elapsed = now - self._window_start

        if elapsed >= 60:
            self._requests_made = 0
            self._window_start = now
            return

        if self._requests_made >= self.rpm_limit:
            sleep_for = 60 - elapsed
            logger.info(
                "Rate limit hit (%s RPM); sleeping %.1fs",
                self.rpm_limit,
                sleep_for,
            )
            time.sleep(sleep_for)
            self._requests_made = 0
            self._window_start = time.time()

    def _sleep_with_jitter(self, base_delay: float) -> None:
        """Sleep with random jitter to prevent thundering herd."""
        jitter = random.uniform(0, base_delay * 0.1)
        delay = min(self.backoff_max, base_delay + jitter)
        time.sleep(delay)

    def _generate_test_embedding(self, text: str) -> List[float]:
        """Generate a deterministic embedding vector for test mode."""
        seed = sum(ord(ch) for ch in text) % 997
        return [((seed + i) % 101) / 100.0 for i in range(EMBEDDING_DIMENSIONS)]

    def _normalize_texts(self, texts: List[str]) -> List[str]:
        """Truncate oversized texts before handing them to the router."""
        normalized: List[str] = []
        for text in texts:
            if len(text) > MAX_TEXT_LENGTH:
                normalized.append(text[:MAX_TEXT_LENGTH])
            else:
                normalized.append(text)
        return normalized

    def _embed_batch_sync(self, texts: List[str]) -> List[List[float]]:
        """Delegate a single embedding batch to model_router synchronously."""
        router = get_default_router()
        return _run_sync(router.embed(self._normalize_texts(texts)))

    def _call_embedding_api(self, texts: List[str]) -> List[List[float]]:
        """Call router embeddings with retry logic for transient failures."""
        attempt = 0
        delay = self.backoff_initial

        while True:
            try:
                embeddings = self._embed_batch_sync(texts)
                if len(embeddings) != len(texts):
                    raise RuntimeError(
                        f"Expected {len(texts)} embeddings, got {len(embeddings)}"
                    )
                return embeddings
            except Exception as error:
                retry_after = None
                is_retryable = False

                if isinstance(error, RateLimitError):
                    retry_after = error.retry_after
                    is_retryable = True
                elif isinstance(error, ModelRouterError):
                    error_str = str(error).lower()
                    is_retryable = (
                        "429" in error_str
                        or "503" in error_str
                        or "rate" in error_str
                        or "quota" in error_str
                        or "unavailable" in error_str
                    )
                else:
                    error_str = str(error).lower()
                    is_retryable = (
                        "429" in error_str
                        or "503" in error_str
                        or "rate" in error_str
                        or "quota" in error_str
                        or "unavailable" in error_str
                    )

                if is_retryable and attempt < self.max_retries:
                    logger.warning(
                        "Embedding request failed (attempt %s/%s): %s",
                        attempt + 1,
                        self.max_retries + 1,
                        error,
                    )
                    if retry_after is not None:
                        time.sleep(max(float(retry_after), 0.0))
                    else:
                        self._sleep_with_jitter(delay)
                        delay = min(
                            self.backoff_max,
                            delay * self.backoff_multiplier,
                        )
                    attempt += 1
                    continue

                logger.error(
                    "Embedding request failed after %s attempts: %s",
                    attempt + 1,
                    error,
                )
                raise

    def embed_text(self, text: str) -> List[float]:
        """Generate embedding for a single text."""
        if not text or text.strip() == "":
            return []

        cached = self._get_cached(text)
        if cached is not None:
            return cached

        if self._test_mode:
            embedding = self._generate_test_embedding(text)
            self._set_cached(text, embedding)
            return embedding

        self._rate_limit()
        embeddings = self._call_embedding_api([text])
        self._requests_made += 1

        embedding = embeddings[0] if embeddings else []
        self._set_cached(text, embedding)
        return embedding

    def embed_query(self, query: str) -> List[float]:
        """Generate embedding for a search query with query normalization."""
        if not query or query.strip() == "":
            return []

        normalized_query = self._normalize_query(query)
        cached_embedding = self._get_cached_query_embedding(normalized_query)
        if cached_embedding is not None:
            return cached_embedding

        embedding = self.embed_text(normalized_query)
        if embedding:
            self._cache_query_embedding(normalized_query, embedding)

        return embedding

    def _normalize_query(self, query: str) -> str:
        """Normalize query text for consistent embeddings."""
        normalized = unicodedata.normalize("NFKC", query)
        normalized = normalized.lower()
        normalized = " ".join(normalized.split())
        normalized = re.sub(r"[^\w\s\-\'\"\.\?\!]", " ", normalized)
        normalized = " ".join(normalized.split())
        return normalized.strip()

    def _get_cached_query_embedding(self, query: str) -> Optional[List[float]]:
        """Get cached query embedding using the instance cache."""
        return self._query_embedding_cache(query)

    def _cache_query_embedding(self, query: str, embedding: List[float]) -> None:
        """Compatibility no-op wrapper for the instance cache."""
        del query
        del embedding

    @staticmethod
    @lru_cache(maxsize=100)
    def _query_embedding_cache_impl(query: str) -> Optional[List[float]]:
        """Static placeholder retained for backward compatibility."""
        del query
        return None

    def _query_embedding_cache(self, query: str) -> Optional[List[float]]:
        """Instance-level query cache lookup."""
        if not hasattr(self, "_query_cache"):
            self._query_cache: Dict[str, List[float]] = {}
            self._query_cache_order: List[str] = []
            self._query_cache_max = 100

        return self._query_cache.get(query)

    def _cache_query_embedding(self, query: str, embedding: List[float]) -> None:
        """Instance-level query cache storage with LRU eviction."""
        if not hasattr(self, "_query_cache"):
            self._query_cache = {}
            self._query_cache_order = []
            self._query_cache_max = 100

        if len(self._query_cache) >= self._query_cache_max:
            if self._query_cache_order:
                oldest = self._query_cache_order.pop(0)
                self._query_cache.pop(oldest, None)

        if query not in self._query_cache:
            self._query_cache_order.append(query)
        self._query_cache[query] = embedding

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int | None = None,
    ) -> List[List[float]]:
        """Generate embeddings for multiple texts with batching."""
        if not texts:
            return []

        effective_batch_size = batch_size or self.batch_size
        results: List[Optional[List[float]]] = [None] * len(texts)
        valid_indices: List[int] = []
        valid_texts: List[str] = []

        for i, text in enumerate(texts):
            if text and text.strip():
                cached = self._get_cached(text)
                if cached is not None:
                    results[i] = cached
                else:
                    valid_indices.append(i)
                    valid_texts.append(text)
            else:
                results[i] = []

        if valid_texts:
            if self._test_mode:
                for idx, text in zip(valid_indices, valid_texts):
                    embedding = self._generate_test_embedding(text)
                    results[idx] = embedding
                    self._set_cached(text, embedding)
            else:
                for start in range(0, len(valid_texts), effective_batch_size):
                    self._rate_limit()
                    batch_texts = valid_texts[start : start + effective_batch_size]
                    batch_indices = valid_indices[start : start + effective_batch_size]
                    logger.debug(
                        "Embedding batch of %s texts (%s-%s/%s)",
                        len(batch_texts),
                        start + 1,
                        start + len(batch_texts),
                        len(valid_texts),
                    )
                    embeddings = self._call_embedding_api(batch_texts)
                    self._requests_made += 1

                    for idx, text, embedding in zip(
                        batch_indices,
                        batch_texts,
                        embeddings,
                    ):
                        results[idx] = embedding
                        self._set_cached(text, embedding)

        if any(result is None for result in results):
            raise RuntimeError("Missing embeddings for one or more inputs")

        return results

    def embed_entity(self, entity: Any) -> List[float]:
        """Generate embedding for an entity using name plus definition."""
        name = getattr(entity, "name", "") or ""
        definition = getattr(entity, "definition", "") or ""

        if definition:
            text = f"{name}: {definition}"
        else:
            text = name

        if not text.strip():
            return []

        return self.embed_text(text)

    def embed_entities(self, entities: List[Any]) -> Dict[str, List[float]]:
        """Generate embeddings for multiple entities."""
        if not entities:
            return {}

        entity_texts: List[str] = []
        entity_ids: List[str] = []

        for entity in entities:
            entity_id = getattr(entity, "id", None)
            if not entity_id:
                continue

            name = getattr(entity, "name", "") or ""
            definition = getattr(entity, "definition", "") or ""

            if definition:
                text = f"{name}: {definition}"
            else:
                text = name

            if text.strip():
                entity_texts.append(text)
                entity_ids.append(entity_id)

        if not entity_texts:
            return {}

        embeddings = self.embed_batch(entity_texts)
        result: Dict[str, List[float]] = {}
        for entity_id, embedding in zip(entity_ids, embeddings):
            result[entity_id] = embedding

        logger.info("Generated embeddings for %s entities", len(result))
        return result


def get_embedding(text: str, api_key: str | None = None) -> List[float]:
    """Convenience function to get an embedding for a single text."""
    service = EmbeddingService(api_key=api_key)
    return service.embed_text(text)


def get_embeddings_batch(
    texts: List[str],
    api_key: str | None = None,
) -> List[List[float]]:
    """Convenience function to get embeddings for multiple texts."""
    service = EmbeddingService(api_key=api_key)
    return service.embed_batch(texts)


__all__ = [
    "EMBEDDING_DIMENSIONS",
    "EmbeddingService",
    "get_embedding",
    "get_embeddings_batch",
]
