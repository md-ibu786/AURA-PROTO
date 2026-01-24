# cache.py
# Redis cache client for AURA-NOTES-MANAGER API

# Provides a singleton Redis client wrapper with connection pooling,
# automatic reconnection, and graceful fallback when Redis is unavailable.
# Used for caching summaries, embeddings, and other frequently accessed data.

# @see: services/summary_service.py - Uses cache for summary storage
# @see: api/main.py - Health check endpoint for Redis
# @note: Set REDIS_HOST, REDIS_PORT, REDIS_DB env vars to configure

from __future__ import annotations

import json
import logging
import os
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# CONFIGURATION
# ============================================================================

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None)

# Default TTL for cached items (24 hours)
DEFAULT_TTL_SECONDS = 24 * 60 * 60


# ============================================================================
# REDIS CLIENT WRAPPER
# ============================================================================


class RedisClient:
    """
    Redis client wrapper with graceful degradation.

    Provides a simple interface for caching operations with automatic
    fallback to no-op when Redis is unavailable. Supports JSON serialization
    for complex objects.

    Example:
        from api.cache import redis_client

        # Store a value
        redis_client.set("my_key", {"foo": "bar"}, ttl=3600)

        # Retrieve a value
        data = redis_client.get("my_key")

        # Delete a value
        redis_client.delete("my_key")
    """

    def __init__(self):
        """Initialize Redis client with lazy connection."""
        self._client = None
        self._available = None

    def _get_client(self):
        """Get or create Redis client connection."""
        if self._client is not None:
            return self._client

        try:
            import redis

            self._client = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                db=REDIS_DB,
                password=REDIS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            # Test connection
            self._client.ping()
            self._available = True
            logger.info(f"Redis connected: {REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}")
        except ImportError:
            logger.warning("redis package not installed, caching disabled")
            self._client = None
            self._available = False
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}, caching disabled")
            self._client = None
            self._available = False

        return self._client

    def ping(self) -> bool:
        """Check if Redis is available and responding."""
        client = self._get_client()
        if client is None:
            return False
        try:
            return client.ping()
        except Exception:
            self._available = False
            return False

    def is_available(self) -> bool:
        """Check if Redis is available without making a connection."""
        if self._available is None:
            self.ping()
        return self._available or False

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value (JSON-decoded) or None if not found/unavailable
        """
        client = self._get_client()
        if client is None:
            return None

        try:
            value = client.get(key)
            if value is None:
                return None
            return json.loads(value)
        except Exception as e:
            logger.debug(f"Cache get failed for {key}: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: int = DEFAULT_TTL_SECONDS,
    ) -> bool:
        """
        Set a value in cache.

        Args:
            key: Cache key
            value: Value to cache (will be JSON-encoded)
            ttl: Time-to-live in seconds (default: 24 hours)

        Returns:
            True if successful, False otherwise
        """
        client = self._get_client()
        if client is None:
            return False

        try:
            serialized = json.dumps(value, default=str)
            client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.debug(f"Cache set failed for {key}: {e}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete a value from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted, False otherwise
        """
        client = self._get_client()
        if client is None:
            return False

        try:
            client.delete(key)
            return True
        except Exception as e:
            logger.debug(f"Cache delete failed for {key}: {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Redis pattern (e.g., "summary:doc:*")

        Returns:
            Number of keys deleted
        """
        client = self._get_client()
        if client is None:
            return 0

        try:
            keys = client.keys(pattern)
            if keys:
                return client.delete(*keys)
            return 0
        except Exception as e:
            logger.debug(f"Cache delete pattern failed for {pattern}: {e}")
            return 0

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists, False otherwise
        """
        client = self._get_client()
        if client is None:
            return False

        try:
            return bool(client.exists(key))
        except Exception:
            return False


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

redis_client = RedisClient()
