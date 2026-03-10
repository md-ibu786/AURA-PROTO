"""
============================================================================
FILE: settings.py
LOCATION: api/routers/settings.py
============================================================================

PURPOSE:
    Admin settings endpoints for shared model router configuration.

ROLE IN PROJECT:
    Exposes runtime defaults, cached provider model discovery, and encrypted
    provider API key management so AURA-NOTES-MANAGER shares the same Redis-
    backed configuration surface as AURA-CHAT.

KEY COMPONENTS:
    - get_redis: Async Redis dependency for shared settings state
    - get_settings_store/get_key_manager/get_model_cache: Shared helper wiring
    - Settings endpoints: defaults CRUD, provider model discovery, key storage

DEPENDENCIES:
    - External: fastapi, pydantic, redis.asyncio
    - Internal: model_router shared package

USAGE:
    Mounted by api/main.py at /api/v1/settings/*
============================================================================
"""

from __future__ import annotations

import logging
import os
from collections.abc import Awaitable, Callable

import redis.asyncio as redis_asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from model_router import KeyManager, ModelCache, ProviderType, SettingsStore
from model_router import get_default_router
from model_router.config import OpenRouterConfig
from model_router.errors import (
    AuthenticationError,
    ModelRouterError,
    ModelUnavailableError,
    RateLimitError,
)
from model_router.providers.openrouter import OpenRouterProvider
from model_router.types import ModelInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/settings", tags=["Settings"])

ALLOWED_USE_CASES = {"chat", "embeddings", "entity_extraction"}
DEFAULT_REDIS_URL = "redis://localhost:6379"

_redis_client: redis_asyncio.Redis | None = None


class DefaultModelUpdate(BaseModel):
    """Payload for updating a use-case default model."""

    provider: str
    model: str


class ApiKeyCreate(BaseModel):
    """Payload for storing a provider API key."""

    api_key: str


def get_redis() -> redis_asyncio.Redis:
    """Return a module-scoped async Redis client."""
    global _redis_client
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", DEFAULT_REDIS_URL)
        _redis_client = redis_asyncio.from_url(
            redis_url,
            decode_responses=True,
        )
    return _redis_client


def get_settings_store(
    redis_client: redis_asyncio.Redis = Depends(get_redis),
) -> SettingsStore:
    """Build a settings store from the injected Redis dependency."""
    return SettingsStore(redis_client)


def get_key_manager(
    redis_client: redis_asyncio.Redis = Depends(get_redis),
) -> KeyManager:
    """Build a key manager from the injected Redis dependency."""
    try:
        return KeyManager(redis_client)
    except ValueError as error:
        raise HTTPException(status_code=500, detail=str(error)) from error


def get_model_cache(
    redis_client: redis_asyncio.Redis = Depends(get_redis),
) -> ModelCache:
    """Build a model cache backed by the shared router singleton."""
    return ModelCache(redis_client, get_default_router())


def _map_model_router_error(error: ModelRouterError) -> HTTPException:
    """Translate shared model router errors into HTTP exceptions."""
    if isinstance(error, AuthenticationError):
        return HTTPException(status_code=401, detail=str(error))
    if isinstance(error, RateLimitError):
        return HTTPException(status_code=429, detail=str(error))
    if isinstance(error, ModelUnavailableError):
        return HTTPException(status_code=404, detail=str(error))
    return HTTPException(status_code=500, detail=str(error))


async def _validate_openrouter_key(api_key: str) -> bool:
    """Validate an OpenRouter key using a temporary provider instance."""
    config = OpenRouterConfig.from_env().model_copy(update={"api_key": api_key})
    provider = OpenRouterProvider(config)
    return await provider.health_check()


async def _validate_provider_key(
    provider: str,
    key_manager: KeyManager,
) -> bool:
    """Validate a stored provider key when runtime support exists."""
    validator: Callable[[str], Awaitable[bool]] | None = None
    if provider == ProviderType.OPENROUTER.value:
        validator = _validate_openrouter_key

    if validator is None:
        return False

    return await key_manager.validate_key(provider, validator)


def _serialize_models(models: list[ModelInfo]) -> list[dict[str, object]]:
    """Return JSON-safe model payloads for API responses."""
    return [model.model_dump(mode="json") for model in models]


@router.get("/defaults")
async def get_defaults(
    store: SettingsStore = Depends(get_settings_store),
) -> dict[str, dict[str, str]]:
    """Return all configured use-case defaults."""
    return await store.get_defaults()


@router.put("/defaults/{use_case}")
async def set_default(
    use_case: str,
    payload: DefaultModelUpdate,
    store: SettingsStore = Depends(get_settings_store),
) -> dict[str, str]:
    """Update the default provider/model for a specific use case."""
    if use_case not in ALLOWED_USE_CASES:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown use case: {use_case}",
        )

    await store.set_default(use_case, payload.provider, payload.model)
    return {
        "use_case": use_case,
        "provider": payload.provider,
        "model": payload.model,
    }


@router.get("/providers/{provider}/models")
async def list_models(
    provider: str,
    refresh: bool = Query(default=False),
    cache: ModelCache = Depends(get_model_cache),
) -> list[dict[str, object]]:
    """Return cached or refreshed models for a provider."""
    try:
        models = await cache.get_models(provider, force_refresh=refresh)
    except ModelRouterError as error:
        raise _map_model_router_error(error) from error
    return _serialize_models(models)


@router.get("/models")
async def list_all_models(
    cache: ModelCache = Depends(get_model_cache),
) -> list[dict[str, object]]:
    """Return all models exposed by the current router."""
    models: list[ModelInfo] = []
    for provider in ProviderType:
        try:
            models.extend(await cache.get_models(provider.value))
        except ModelUnavailableError:
            continue
        except ModelRouterError as error:
            raise _map_model_router_error(error) from error
    return _serialize_models(models)


@router.post("/providers/{provider}/api-key")
async def store_api_key(
    provider: str,
    payload: ApiKeyCreate,
    key_manager: KeyManager = Depends(get_key_manager),
) -> dict[str, object]:
    """Store an encrypted provider API key and return its masked value."""
    try:
        masked_key = await key_manager.store_key(provider, payload.api_key)
        is_valid = await _validate_provider_key(provider, key_manager)
    except ModelRouterError as error:
        raise _map_model_router_error(error) from error

    return {
        "provider": provider,
        "masked_key": masked_key,
        "valid": is_valid,
    }


@router.get("/providers/{provider}/api-key")
async def get_api_key(
    provider: str,
    key_manager: KeyManager = Depends(get_key_manager),
) -> dict[str, str]:
    """Return the masked key for a configured provider."""
    masked_key = await key_manager.get_masked_key(provider)
    if masked_key is None:
        raise HTTPException(
            status_code=404,
            detail=f"No API key configured for {provider}",
        )
    return {"provider": provider, "masked_key": masked_key}


@router.delete("/providers/{provider}/api-key")
async def delete_api_key(
    provider: str,
    key_manager: KeyManager = Depends(get_key_manager),
) -> dict[str, object]:
    """Delete a configured provider API key."""
    deleted = await key_manager.delete_key(provider)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"No API key configured for {provider}",
        )
    return {"provider": provider, "deleted": True}


@router.post("/providers/{provider}/validate")
async def validate_api_key(
    provider: str,
    key_manager: KeyManager = Depends(get_key_manager),
) -> dict[str, object]:
    """Re-validate a stored provider key and return its masked display value."""
    masked_key = await key_manager.get_masked_key(provider)
    if masked_key is None:
        raise HTTPException(
            status_code=404,
            detail=f"No API key configured for {provider}",
        )

    try:
        is_valid = await _validate_provider_key(provider, key_manager)
    except ModelRouterError as error:
        raise _map_model_router_error(error) from error

    return {
        "provider": provider,
        "masked_key": masked_key,
        "valid": is_valid,
    }
