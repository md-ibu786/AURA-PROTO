"""
========================================================================
FILE: test_usage_date_range.py
LOCATION: AURA-NOTES-MANAGER/api/tests/test_usage_date_range.py
========================================================================

PURPOSE:
    Validate usage router date range parsing behavior for defaults,
    date-only end dates, and explicit-time end dates.

ROLE IN PROJECT:
    Guards usage dashboard filter accuracy by asserting inclusive
    end-of-day behavior for date-only end_date inputs.
    - Key responsibility 1: Verify default UTC date window behavior
    - Key responsibility 2: Verify date-only and explicit-time handling

KEY COMPONENTS:
    - test_parse_date_range_defaults: Verifies default 30-day UTC window
    - test_parse_date_range_date_only_end_date: Verifies end-of-day shift
    - test_parse_date_range_explicit_time_end_date: Verifies no shift

DEPENDENCIES:
    - External: datetime
    - Internal: routers.usage._parse_date_range

USAGE:
    .venv/Scripts/python -m pytest AURA-NOTES-MANAGER/api/tests/
    test_usage_date_range.py -v
========================================================================
"""

from datetime import datetime, timedelta, timezone
from enum import Enum
import importlib.util
from pathlib import Path
import sys
import types

from pydantic import BaseModel


class _DocumentSummary(BaseModel):
    """Minimal summary schema stub for router package side-effect imports."""

    summary: str = ''


class _ModuleSummary(BaseModel):
    """Minimal module summary schema stub for router package side effects."""

    summary: str = ''


class _SummaryLength(str, Enum):
    """Minimal summary length enum stub for router package side effects."""

    BRIEF = 'brief'
    STANDARD = 'standard'
    DETAILED = 'detailed'


class _SummaryService:
    """Minimal service stub so api.routers package import can resolve."""

    def __init__(self, *args, **kwargs) -> None:
        del args, kwargs


_summary_service_stub = types.ModuleType('services.summary_service')
_summary_service_stub.DocumentSummary = _DocumentSummary
_summary_service_stub.ModuleSummary = _ModuleSummary
_summary_service_stub.SummaryLength = _SummaryLength
_summary_service_stub.SummaryService = _SummaryService
sys.modules.setdefault('services.summary_service', _summary_service_stub)


try:
    from routers.usage import _parse_date_range
except ImportError:
    try:
        from api.routers.usage import _parse_date_range
    except ImportError:
        routers_pkg = types.ModuleType('routers')
        routers_pkg.__path__ = []
        sys.modules.setdefault('routers', routers_pkg)

        routers_settings = types.ModuleType('routers.settings')
        routers_settings.get_redis = lambda: None
        sys.modules.setdefault('routers.settings', routers_settings)

        usage_path = Path(__file__).resolve().parents[1] / 'routers' / 'usage.py'
        spec = importlib.util.spec_from_file_location(
            'usage_router_date_range_test',
            usage_path,
        )
        if spec is None or spec.loader is None:
            raise RuntimeError('Unable to load usage router module for tests')
        usage_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(usage_module)
        _parse_date_range = usage_module._parse_date_range


def test_parse_date_range_defaults() -> None:
    """Defaults should produce a UTC-aware 30-day window ending at now."""
    before = datetime.now(timezone.utc)
    start_date, end_date = _parse_date_range(None, None)
    after = datetime.now(timezone.utc)

    assert start_date.tzinfo == timezone.utc
    assert end_date.tzinfo == timezone.utc
    assert before - timedelta(days=30) <= start_date <= after - timedelta(days=30)
    assert before <= end_date <= after


def test_parse_date_range_date_only_end_date() -> None:
    """Date-only end_date should be normalized to end-of-day UTC."""
    _, end_date = _parse_date_range(None, datetime(2026, 5, 16))

    assert end_date == datetime(
        2026,
        5,
        16,
        23,
        59,
        59,
        999999,
        tzinfo=timezone.utc,
    )


def test_parse_date_range_explicit_time_end_date() -> None:
    """Explicit end_date time should remain unchanged except UTC tz attach."""
    _, end_date = _parse_date_range(None, datetime(2026, 5, 16, 14, 30, 0))

    assert end_date == datetime(2026, 5, 16, 14, 30, 0, tzinfo=timezone.utc)


def test_parse_date_range_start_date_midnight_not_adjusted() -> None:
    """Start date at midnight should stay midnight and never shift to EOD."""
    start_date, _ = _parse_date_range(datetime(2026, 5, 1), None)

    assert start_date == datetime(2026, 5, 1, tzinfo=timezone.utc)


def test_parse_date_range_both_provided() -> None:
    """When both provided date-only, start remains midnight and end is EOD."""
    start_date, end_date = _parse_date_range(
        datetime(2026, 5, 1),
        datetime(2026, 5, 16),
    )

    assert start_date == datetime(2026, 5, 1, tzinfo=timezone.utc)
    assert end_date == datetime(
        2026,
        5,
        16,
        23,
        59,
        59,
        999999,
        tzinfo=timezone.utc,
    )
