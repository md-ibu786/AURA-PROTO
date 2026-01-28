# embeddings.py
# Embedding service for AURA-NOTES-MANAGER with Vertex AI and test-mode fallback

# Provides 768-dimensional embeddings via Vertex AI text embeddings
# with batching, rate limiting, and retry logic. Test mode provides deterministic
# embeddings to avoid external dependencies during pytest runs.

# @see: api/kg_processor.py - Uses EmbeddingService for chunk and entity embeddings
# @see: api/rag_engine.py - Uses embed_query for search queries
# @see: AURA-CHAT/backend/utils/embeddings.py - Reference implementation
# @note: Test mode is enabled via AURA_TEST_MODE=true

from __future__ import annotations

import logging
import os
import re
import time
import random
import unicodedata
import sys
from functools import lru_cache
from typing import List, Dict, Any, Optional, TYPE_CHECKING

from google.cloud import aiplatform

_api_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "api"))
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

try:
    from config import EMBEDDING_MODEL
except ImportError:
    from api.config import EMBEDDING_MODEL
from services.vertex_ai_client import init_vertex_ai

if TYPE_CHECKING:
    from api.kg_processor import Entity

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

EMBEDDING_DIMENSIONS = 768  # Output vector dimensions
EMBEDDING_BATCH_SIZE = 100  # Number of texts per API request
RATE_LIMIT_RPM = 60  # Requests per minute limit (conservative)
MAX_RETRIES = 3  # Maximum retry attempts
RETRY_BACKOFF_INITIAL = 1.0  # Initial backoff delay in seconds
RETRY_BACKOFF_MULTIPLIER = 2.0  # Backoff multiplier
RETRY_BACKOFF_MAX = 30.0  # Maximum backoff delay

# Maximum text length for embedding (model limit)
MAX_TEXT_LENGTH = 30000  # Characters

# ============================================================================
# LOGGING
# ============================================================================

logger = logging.getLogger(__name__)


# ============================================================================
# EMBEDDING SERVICE CLASS
# ============================================================================


class EmbeddingService:
    """
    Embedding service for generating 768-dimensional text embeddings.

    Uses Vertex AI text-embedding-004 model in production and provides
    deterministic test embeddings when AURA_TEST_MODE=true.

    Features:
    - Batch processing for efficient API usage
    - Rate limiting to prevent throttling
    - Retry logic with exponential backoff
    - Entity-specific embedding (name + definition)

    Example:
        service = EmbeddingService()
        vector = service.embed_text("Machine learning is...")
        # Returns: List[float] of length 768

        vectors = service.embed_batch(["Text 1", "Text 2"])
        # Returns: List[List[float]]
    """

    def __init__(
        self,
        model_name: str = EMBEDDING_MODEL,
        api_key: str | None = None,
    ):
        """
        Initialize embedding service.

        Args:
            model_name: Embedding model name (default: text-embedding-004)
            api_key: Deprecated. Vertex AI uses ADC credentials instead.
        """
        self.model_name = model_name
        self._test_mode = os.getenv("AURA_TEST_MODE", "").lower() == "true"
        self._embedding_model = None

        # Configuration
        self.batch_size = EMBEDDING_BATCH_SIZE
        self.rpm_limit = RATE_LIMIT_RPM
        self.max_retries = MAX_RETRIES
        self.backoff_initial = RETRY_BACKOFF_INITIAL
        self.backoff_multiplier = RETRY_BACKOFF_MULTIPLIER
        self.backoff_max = RETRY_BACKOFF_MAX

        # Rate limiting state
        self._requests_made = 0
        self._window_start = time.time()

        # Optional in-memory cache
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
            self._init_embedding_model()
            logger.info(f"EmbeddingService initialized with model: {self.model_name}")

    def _init_embedding_model(self) -> None:
        if self._embedding_model is not None or self._test_mode:
            return

        init_vertex_ai()

        try:
            self._embedding_model = aiplatform.TextEmbeddingModel.from_pretrained(
                self.model_name
            )
        except AttributeError:
            self._embedding_model = aiplatform.TextEmbeddingModel(self.model_name)

    def enable_cache(self, max_size: int = 1000) -> None:
        """
        Enable in-memory caching for repeated texts.

        Args:
            max_size: Maximum cache size (LRU eviction after this)
        """
        self._cache_enabled = True
        self._cache_max_size = max_size
        logger.info(f"Embedding cache enabled (max_size={max_size})")

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

        # Simple LRU: clear oldest entries if cache is full
        if len(self._cache) >= self._cache_max_size:
            # Remove first 10% of entries
            keys_to_remove = list(self._cache.keys())[: self._cache_max_size // 10]
            for key in keys_to_remove:
                del self._cache[key]

        self._cache[text] = embedding

    def _rate_limit(self) -> None:
        """Apply rate limiting to stay under RPM limit."""
        now = time.time()
        elapsed = now - self._window_start

        if elapsed >= 60:
            # Reset window
            self._requests_made = 0
            self._window_start = now
            return

        if self._requests_made >= self.rpm_limit:
            sleep_for = 60 - elapsed
            logger.info(
                f"Rate limit hit ({self.rpm_limit} RPM); sleeping {sleep_for:.1f}s"
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
        """
        Generate deterministic test embedding for a given text.

        Uses hash of text to produce consistent, reproducible embeddings.

        Args:
            text: Input text

        Returns:
            768-dimensional vector of floats
        """
        seed = sum(ord(ch) for ch in text) % 997
        return [((seed + i) % 101) / 100.0 for i in range(EMBEDDING_DIMENSIONS)]

    def _call_embedding_api(self, texts: List[str]) -> List[List[float]]:
        """
        Call Vertex AI embedding API with retry logic.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            Exception: If all retries fail
        """
        if self._embedding_model is None:
            self._init_embedding_model()
        if self._embedding_model is None:
            raise RuntimeError("Vertex AI embedding model is not initialized")

        attempt = 0
        delay = self.backoff_initial

        while True:
            try:
                # Truncate text if too long
                truncated_texts = [
                    text[:MAX_TEXT_LENGTH] if len(text) > MAX_TEXT_LENGTH else text
                    for text in texts
                ]

                try:
                    embeddings = self._embedding_model.get_embeddings(
                        truncated_texts,
                        output_dimensionality=EMBEDDING_DIMENSIONS,
                    )
                except TypeError:
                    embeddings = self._embedding_model.get_embeddings(truncated_texts)

                values_list = []
                for embedding in embeddings:
                    values = getattr(embedding, "values", None)
                    if values is None and isinstance(embedding, dict):
                        values = embedding.get("values")
                    if values is None:
                        logger.error(
                            f"Failed to extract embedding values from response: {embedding}"
                        )
                        raise RuntimeError("Embedding API returned no values")
                    values_list.append(list(values))

                if len(values_list) != len(texts):
                    raise RuntimeError(
                        f"Expected {len(texts)} embeddings, got {len(values_list)}"
                    )

                return values_list

            except Exception as e:
                error_str = str(e).lower()
                is_retryable = (
                    "429" in error_str
                    or "503" in error_str
                    or "rate" in error_str
                    or "quota" in error_str
                    or "unavailable" in error_str
                )

                if is_retryable and attempt < self.max_retries:
                    logger.warning(
                        f"Embedding request failed (attempt {attempt + 1}/{self.max_retries + 1}): {e}"
                    )
                    self._sleep_with_jitter(delay)
                    delay = min(self.backoff_max, delay * self.backoff_multiplier)
                    attempt += 1
                    continue

                logger.error(
                    f"Embedding request failed after {attempt + 1} attempts: {e}"
                )
                raise

    def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            768-dimensional embedding vector, or empty list if input is empty
        """
        if not text or text.strip() == "":
            return []

        # Check cache
        cached = self._get_cached(text)
        if cached is not None:
            return cached

        # Test mode
        if self._test_mode:
            embedding = self._generate_test_embedding(text)
            self._set_cached(text, embedding)
            return embedding

        # Call API
        self._rate_limit()
        embeddings = self._call_embedding_api([text])
        self._requests_made += 1

        embedding = embeddings[0] if embeddings else []
        self._set_cached(text, embedding)
        return embedding

    def embed_query(self, query: str) -> List[float]:
        """
        Generate embedding for a search query with query-specific optimization.

        This method is optimized for search queries:
        1. Cleans and normalizes the query text
        2. Uses LRU caching for recent queries (100 entries)
        3. Returns 768-dimensional vector

        Args:
            query: Search query text

        Returns:
            768-dimensional embedding vector, or empty list if input is empty

        Example:
            service = EmbeddingService()
            query_embedding = service.embed_query("machine learning algorithms")
            # Use embedding for vector similarity search
        """
        if not query or query.strip() == "":
            return []

        # Normalize query for better search results
        normalized_query = self._normalize_query(query)

        # Use cached query embedding if available
        cached_embedding = self._get_cached_query_embedding(normalized_query)
        if cached_embedding is not None:
            return cached_embedding

        # Generate embedding
        embedding = self.embed_text(normalized_query)

        # Cache the query embedding
        if embedding:
            self._cache_query_embedding(normalized_query, embedding)

        return embedding

    def _normalize_query(self, query: str) -> str:
        """
        Normalize query text for consistent embeddings.

        Applies:
        - Unicode normalization (NFKC)
        - Lowercase conversion
        - Whitespace normalization
        - Remove excessive punctuation

        Args:
            query: Raw query text

        Returns:
            Normalized query string
        """
        # Unicode normalize
        normalized = unicodedata.normalize("NFKC", query)

        # Lowercase
        normalized = normalized.lower()

        # Normalize whitespace
        normalized = " ".join(normalized.split())

        # Remove excessive punctuation but keep essential ones
        normalized = re.sub(r"[^\w\s\-\'\"\.\?\!]", " ", normalized)

        # Clean up whitespace again
        normalized = " ".join(normalized.split())

        return normalized.strip()

    def _get_cached_query_embedding(self, query: str) -> Optional[List[float]]:
        """Get cached query embedding using LRU cache."""
        return self._query_embedding_cache(query)

    def _cache_query_embedding(self, query: str, embedding: List[float]) -> None:
        """Cache query embedding (handled by LRU decorator)."""
        # The caching is done via the lru_cache on _query_embedding_cache_impl
        pass

    @staticmethod
    @lru_cache(maxsize=100)
    def _query_embedding_cache_impl(query: str) -> Optional[List[float]]:
        """
        LRU cache implementation for query embeddings.

        Note: This is a static placeholder. Actual caching happens at instance level
        via the _query_cache dict to work with instance-specific API keys.
        """
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

        # Evict oldest if cache is full
        if len(self._query_cache) >= self._query_cache_max:
            if self._query_cache_order:
                oldest = self._query_cache_order.pop(0)
                self._query_cache.pop(oldest, None)

        # Add to cache
        if query not in self._query_cache:
            self._query_cache_order.append(query)
        self._query_cache[query] = embedding

    def embed_batch(
        self,
        texts: List[str],
        batch_size: int = None,
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts with batching.

        Preserves input order. Empty/None texts get empty embeddings.

        Args:
            texts: List of texts to embed
            batch_size: Override default batch size

        Returns:
            List of embedding vectors (same order as input)
        """
        if not texts:
            return []

        effective_batch_size = batch_size or self.batch_size
        results: List[Optional[List[float]]] = [None] * len(texts)

        # Identify non-empty texts
        valid_indices = []
        valid_texts = []

        for i, text in enumerate(texts):
            if text and text.strip():
                # Check cache first
                cached = self._get_cached(text)
                if cached is not None:
                    results[i] = cached
                else:
                    valid_indices.append(i)
                    valid_texts.append(text)
            else:
                results[i] = []

        # Generate embeddings for uncached texts
        if valid_texts:
            if self._test_mode:
                # Test mode: generate deterministic embeddings
                for idx, text in zip(valid_indices, valid_texts):
                    embedding = self._generate_test_embedding(text)
                    results[idx] = embedding
                    self._set_cached(text, embedding)
            else:
                # Production: batch API calls
                for start in range(0, len(valid_texts), effective_batch_size):
                    self._rate_limit()

                    batch_texts = valid_texts[start : start + effective_batch_size]
                    batch_indices = valid_indices[start : start + effective_batch_size]

                    logger.debug(
                        f"Embedding batch of {len(batch_texts)} texts "
                        f"({start + 1}-{start + len(batch_texts)}/{len(valid_texts)})"
                    )

                    embeddings = self._call_embedding_api(batch_texts)
                    self._requests_made += 1

                    for idx, text, embedding in zip(
                        batch_indices, batch_texts, embeddings
                    ):
                        results[idx] = embedding
                        self._set_cached(text, embedding)

        # Verify all results are filled
        if any(r is None for r in results):
            raise RuntimeError("Missing embeddings for one or more inputs")

        return results

    def embed_entity(self, entity: Any) -> List[float]:
        """
        Generate embedding for an entity using name + definition.

        Combines entity name and definition for richer semantic representation.

        Args:
            entity: Entity object with 'name' and 'definition' attributes

        Returns:
            768-dimensional embedding vector
        """
        name = getattr(entity, "name", "") or ""
        definition = getattr(entity, "definition", "") or ""

        # Combine name and definition
        if definition:
            text = f"{name}: {definition}"
        else:
            text = name

        if not text.strip():
            return []

        return self.embed_text(text)

    def embed_entities(
        self,
        entities: List[Any],
    ) -> Dict[str, List[float]]:
        """
        Generate embeddings for multiple entities.

        Args:
            entities: List of Entity objects with 'id', 'name', 'definition'

        Returns:
            Dict mapping entity ID to embedding vector
        """
        if not entities:
            return {}

        # Build text representations
        entity_texts = []
        entity_ids = []

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

        # Batch generate embeddings
        embeddings = self.embed_batch(entity_texts)

        # Map to entity IDs
        result = {}
        for entity_id, embedding in zip(entity_ids, embeddings):
            result[entity_id] = embedding

        logger.info(f"Generated embeddings for {len(result)} entities")
        return result


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================


def get_embedding(text: str, api_key: str = None) -> List[float]:
    """
    Convenience function to get embedding for a single text.

    Args:
        text: Text to embed
        api_key: Deprecated. Vertex AI uses ADC credentials instead.

    Returns:
        768-dimensional embedding vector
    """
    service = EmbeddingService(api_key=api_key)
    return service.embed_text(text)


def get_embeddings_batch(texts: List[str], api_key: str = None) -> List[List[float]]:
    """
    Convenience function to get embeddings for multiple texts.

    Args:
        texts: List of texts to embed
        api_key: Deprecated. Vertex AI uses ADC credentials instead.

    Returns:
        List of embedding vectors
    """
    service = EmbeddingService(api_key=api_key)
    return service.embed_batch(texts)
