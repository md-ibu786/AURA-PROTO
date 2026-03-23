"""
========================================================================
FILE: test_settings_router.py
LOCATION: api/tests/test_settings_router.py
========================================================================

PURPOSE:
    Integration tests for the admin settings router, covering default
    model configuration for gatekeeper and relationship_extraction use
    cases (API-01, API-02).

ROLE IN PROJECT:
    Validates settings endpoints end-to-end using offline doubles so no
    external Redis credentials are required.
    - Tests gatekeeper and relationship_extraction use case defaults
    - Tests invalid use case rejection

KEY COMPONENTS:
    - FakeAsyncRedis: In-memory async Redis double
    - test_app fixture: App with settings dependencies overridden

DEPENDENCIES:
    - External: pytest, pytest-asyncio, httpx
    - Internal: api.main, api.routers.settings

USAGE:
    pytest api/tests/test_settings_router.py -v
========================================================================
"""

from __future__ import annotations

from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

from model_router import SettingsStore
from api.main import app
from api.routers.settings import get_redis, get_settings_store


class FakeAsyncRedis:
    """Small async Redis double for settings endpoint tests."""

    def __init__(self) -> None:
        self._hashes: dict[str, dict[str, str]] = {}
        self._values: dict[str, str] = {}

    async def hset(self, name: str, key: str, value: str) -> None:
        self._hashes.setdefault(name, {})[key] = value

    async def hget(self, name: str, key: str) -> str | None:
        return self._hashes.get(name, {}).get(key)

    async def hgetall(self, name: str) -> dict[str, str]:
        return dict(self._hashes.get(name, {}))


@pytest.fixture
def fake_redis() -> FakeAsyncRedis:
    """Return an isolated async Redis double."""
    return FakeAsyncRedis()


@pytest.fixture
def test_app(fake_redis: FakeAsyncRedis):
    """Override router dependencies with offline doubles."""
    store = SettingsStore(fake_redis)
    app.dependency_overrides[get_redis] = lambda: fake_redis
    app.dependency_overrides[get_settings_store] = lambda: store
    yield app
    app.dependency_overrides.clear()


async def _request(
    test_app: Any,
    method: str,
    url: str,
    **kwargs: Any,
):
    """Execute an HTTP request against the FastAPI ASGI app."""
    transport = ASGITransport(app=test_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, url, **kwargs)


@pytest.mark.asyncio
async def test_set_default_gatekeeper(test_app: Any) -> None:
    """PUT gatekeeper default returns 200 and persists (API-01)."""
    update_response = await _request(
        test_app,
        "PUT",
        "/api/v1/settings/defaults/gatekeeper",
        json={"provider": "vertex_ai", "model": "gemini-2.5-flash-lite"},
    )
    get_response = await _request(test_app, "GET", "/api/v1/settings/defaults")

    assert update_response.status_code == 200
    assert update_response.json() == {
        "use_case": "gatekeeper",
        "provider": "vertex_ai",
        "model": "gemini-2.5-flash-lite",
    }
    assert get_response.status_code == 200
    assert "gatekeeper" in get_response.json()
    assert get_response.json()["gatekeeper"] == {
        "provider": "vertex_ai",
        "model": "gemini-2.5-flash-lite",
    }


@pytest.mark.asyncio
async def test_set_default_relationship_extraction(
    test_app: Any,
) -> None:
    """PUT relationship_extraction default returns 200 and persists (API-02)."""
    update_response = await _request(
        test_app,
        "PUT",
        "/api/v1/settings/defaults/relationship_extraction",
        json={"provider": "openrouter", "model": "anthropic/claude-3.7-sonnet"},
    )
    get_response = await _request(test_app, "GET", "/api/v1/settings/defaults")

    assert update_response.status_code == 200
    assert update_response.json() == {
        "use_case": "relationship_extraction",
        "provider": "openrouter",
        "model": "anthropic/claude-3.7-sonnet",
    }
    assert get_response.status_code == 200
    assert "relationship_extraction" in get_response.json()
    assert get_response.json()["relationship_extraction"] == {
        "provider": "openrouter",
        "model": "anthropic/claude-3.7-sonnet",
    }


@pytest.mark.asyncio
async def test_set_default_invalid_use_case(test_app: Any) -> None:
    """PUT with unknown use case returns 400."""
    response = await _request(
        test_app,
        "PUT",
        "/api/v1/settings/defaults/invalid",
        json={"provider": "vertex_ai", "model": "gemini-2.5-flash"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Unknown use case: invalid"
