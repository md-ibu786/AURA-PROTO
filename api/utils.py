"""
============================================================================
FILE: utils.py
LOCATION: api/utils.py
============================================================================

PURPOSE:
    Shared utility functions for hierarchy and notes modules.

ROLE IN PROJECT:
    Provides common helper functions used across multiple API modules
    to avoid code duplication.

KEY COMPONENTS:
    - get_next_available_number: Find next sequential number
    - get_unique_name: Generate unique name with (N) suffix

DEPENDENCIES:
    - External: re (standard library)

USAGE:
    from api.utils import get_next_available_number, get_unique_name
============================================================================
"""

import re


def get_next_available_number(numbers: list[int]) -> int:
    """Find the next available sequential number (max + 1)."""
    if not numbers:
        return 1
    return max(numbers) + 1


def get_unique_name(names: list[str], base_name: str) -> str:
    """Generate unique name with (N) suffix for duplicates."""
    if base_name not in names:
        return base_name

    suffix_numbers = [1]
    pattern = re.compile(rf"^{re.escape(base_name)} \((\d+)\)$")
    for n in names:
        match = pattern.match(n)
        if match:
            suffix_numbers.append(int(match.group(1)))

    next_suffix = get_next_available_number(suffix_numbers)
    if next_suffix == 1:
        next_suffix = 2
    return f"{base_name} ({next_suffix})"
