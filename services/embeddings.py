# embeddings.py
# Embedding service for AURA-NOTES-MANAGER with Gemini and test-mode fallback

# Provides 768-dimensional embeddings via Google Gemini (gemini-embedding-001)
# with batching, rate limiting, and retry logic. Test mode provides deterministic
# embeddings to avoid external dependencies during pytest runs.

# @see: api/kg_processor.py - Uses EmbeddingService for chunk and entity embeddings
# @see: AURA-CHAT/backend/utils/embeddings.py - Reference implementation
# @note: Test mode is enabled via AURA_TEST_MODE=true

from __future__ import annotations

import logging
import os
import time
import random
from typing import List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from api.kg_processor import Entity

# ============================================================================
# CONFIGURATION CONSTANTS
# ============================================================================

EMBEDDING_MODEL = "text-embedding-004"  # Gemini embedding model
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

    Uses Google Gemini's text-embedding-004 model in production and provides
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
        api_key: str = None,
    ):
        """
        Initialize embedding service.

        Args:
            model_name: Embedding model name (default: text-embedding-004)
            api_key: Google API key (defaults to GEMINI_API_KEY or GOOGLE_API_KEY env var)
        """
        self.model_name = model_name
        self.api_key = (
            api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        )
        self._test_mode = os.getenv("AURA_TEST_MODE", "").lower() == "true"

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

        if self._test_mode:
            logger.info(
                f"EmbeddingService initialized in test mode (dimensions: {EMBEDDING_DIMENSIONS})"
            )
        else:
            if not self.api_key:
                logger.warning("No API key configured for Gemini embeddings")
            logger.info(
                f"EmbeddingService initialized with model: {self.model_name}"
            )

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
        Call Gemini embedding API with retry logic.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors

        Raises:
            Exception: If all retries fail
        """
        try:
            import google.generativeai as genai
        except ImportError:
            logger.error("google-generativeai not installed")
            raise RuntimeError("google-generativeai package not installed")

        if not self.api_key:
            raise RuntimeError("No API key configured for Gemini embeddings")

        genai.configure(api_key=self.api_key)

        attempt = 0
        delay = self.backoff_initial

        while True:
            try:
                embeddings = []

                for text in texts:
                    # Truncate text if too long
                    truncated = text[:MAX_TEXT_LENGTH] if len(text) > MAX_TEXT_LENGTH else text

                    result = genai.embed_content(
                        model=self.model_name,
                        content=truncated,
                        task_type="semantic_similarity",
                    )

                    embedding = result.get("embedding", [])
                    embeddings.append(embedding)

                if len(embeddings) != len(texts):
                    raise RuntimeError(
                        f"Expected {len(texts)} embeddings, got {len(embeddings)}"
                    )

                return embeddings

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

                logger.error(f"Embedding request failed after {attempt + 1} attempts: {e}")
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

                    for idx, text, embedding in zip(batch_indices, batch_texts, embeddings):
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
        api_key: Optional API key

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
        api_key: Optional API key

    Returns:
        List of embedding vectors
    """
    service = EmbeddingService(api_key=api_key)
    return service.embed_batch(texts)
