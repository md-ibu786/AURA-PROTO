# usage.py
# Usage query API endpoints for the AURA-NOTES-MANAGER application.

# Exposes REST endpoints for querying aggregated usage data including
# cost summaries, per-session breakdowns, and provider/model/daily
# drill-downs. Wires into the shared UsageTracker via FastAPI Depends
# injection using the same Redis client pattern as settings.py.

# @see: shared/model_router/src/model_router/usage_tracker.py
# @note: All date params default to a 30-day window when omitted.

"""Usage query API endpoints for the AURA-NOTES-MANAGER application."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
import redis.asyncio as redis_asyncio

from model_router import UsageTracker

try:
    from routers.settings import get_redis
except ImportError:
    from api.routers.settings import get_redis

router = APIRouter(prefix="/api/v1/usage", tags=["Usage"])

logger = logging.getLogger(__name__)


def get_usage_tracker(
    redis_client: redis_asyncio.Redis = Depends(get_redis),
) -> UsageTracker:
    """Build a UsageTracker from the injected Redis dependency."""
    return UsageTracker(redis_client)


def _parse_date_range(
    start_date: Optional[datetime],
    end_date: Optional[datetime],
) -> tuple[datetime, datetime]:
    """Return validated start/end datetimes with sensible defaults.

    Args:
        start_date: Optional start (default: 30 days ago).
        end_date: Optional end (default: now UTC).

    Returns:
        Tuple of (start_date, end_date) with timezone info.
    """
    now = datetime.now(timezone.utc)
    if end_date is None:
        end_date = now
    elif end_date.tzinfo is None:
        end_date = end_date.replace(tzinfo=timezone.utc)

    if start_date is None:
        start_date = now - timedelta(days=30)
    elif start_date.tzinfo is None:
        start_date = start_date.replace(tzinfo=timezone.utc)

    return start_date, end_date


@router.get("/summary")
async def get_usage_summary(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    provider: Optional[str] = None,
    tracker: UsageTracker = Depends(get_usage_tracker),
) -> dict[str, Any]:
    """Return aggregated cost data with date range filtering.

    Args:
        start_date: Start of query range (default 30 days ago).
        end_date: End of query range (default now).
        provider: Optional provider filter (e.g. 'vertex_ai').
        tracker: Injected UsageTracker instance.

    Returns:
        Aggregated summary with total_cost, total_requests,
        and breakdowns by provider, model, and day.
    """
    try:
        start, end = _parse_date_range(start_date, end_date)
        return await tracker.get_summary(start, end, provider)
    except Exception as exc:
        logger.error("Failed to get usage summary: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve usage summary",
        ) from exc


@router.get("/session/{session_id}")
async def get_session_usage(
    session_id: str,
    tracker: UsageTracker = Depends(get_usage_tracker),
) -> dict[str, Any]:
    """Return per-session token and cost totals.

    Args:
        session_id: Study session identifier.
        tracker: Injected UsageTracker instance.

    Returns:
        Session summary with total_cost, token counts, and
        request_count.
    """
    try:
        return await tracker.get_session_summary(session_id)
    except Exception as exc:
        logger.error(
            "Failed to get session usage for %s: %s",
            session_id,
            exc,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve session usage",
        ) from exc


@router.get("/by-provider")
async def get_usage_by_provider(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    tracker: UsageTracker = Depends(get_usage_tracker),
) -> list[dict[str, Any]]:
    """Return cost breakdown by provider.

    Args:
        start_date: Start of query range (default 30 days ago).
        end_date: End of query range (default now).
        tracker: Injected UsageTracker instance.

    Returns:
        List of provider cost/request breakdowns.
    """
    try:
        start, end = _parse_date_range(start_date, end_date)
        summary = await tracker.get_summary(start, end)
        return summary.get("by_provider", [])
    except Exception as exc:
        logger.error("Failed to get by-provider usage: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve provider usage",
        ) from exc


@router.get("/by-model")
async def get_usage_by_model(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    tracker: UsageTracker = Depends(get_usage_tracker),
) -> list[dict[str, Any]]:
    """Return cost breakdown by model.

    Args:
        start_date: Start of query range (default 30 days ago).
        end_date: End of query range (default now).
        tracker: Injected UsageTracker instance.

    Returns:
        List of model cost/request breakdowns.
    """
    try:
        start, end = _parse_date_range(start_date, end_date)
        summary = await tracker.get_summary(start, end)
        return summary.get("by_model", [])
    except Exception as exc:
        logger.error("Failed to get by-model usage: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve model usage",
        ) from exc


@router.get("/daily")
async def get_daily_usage(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    tracker: UsageTracker = Depends(get_usage_tracker),
) -> list[dict[str, Any]]:
    """Return daily cost and request breakdown.

    Args:
        start_date: Start of query range (default 30 days ago).
        end_date: End of query range (default now).
        tracker: Injected UsageTracker instance.

    Returns:
        List of daily cost/request breakdowns.
    """
    try:
        start, end = _parse_date_range(start_date, end_date)
        summary = await tracker.get_summary(start, end)
        return summary.get("daily", [])
    except Exception as exc:
        logger.error("Failed to get daily usage: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve daily usage",
        ) from exc
