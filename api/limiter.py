"""
============================================================================
FILE: limiter.py
LOCATION: api/limiter.py
============================================================================

PURPOSE:
    Provide a shared SlowAPI limiter instance for the backend.

ROLE IN PROJECT:
    Centralizes rate limiting configuration so the app and routers
    use the same limiter instance and defaults.

KEY COMPONENTS:
    - limiter: SlowAPI Limiter configured with default request limits

DEPENDENCIES:
    - External: slowapi
    - Internal: none

USAGE:
    from limiter import limiter
============================================================================
"""

from slowapi import Limiter
from slowapi.util import get_remote_address


limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"],
)
