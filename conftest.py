"""
============================================================================
FILE: conftest.py
LOCATION: conftest.py
============================================================================

PURPOSE:
    Pytest configuration for AURA-NOTES-MANAGER test environment.

ROLE IN PROJECT:
    Sets test-mode environment flags to avoid external service initialization.
    Ensures hermetic test execution by disabling external dependencies.
    - Disables Neo4j initialization
    - Disables Redis caching
    - Sets global test mode flags

KEY COMPONENTS:
    - Environment variable setup for AURA_TEST_MODE
    - REDIS_ENABLED set to false
    - TESTING flag configuration

DEPENDENCIES:
    - External: None
    - Internal: None

USAGE:
    Automatically loaded by pytest when running any tests.
    See: api/neo4j_config.py - Skips Neo4j init in test mode
============================================================================
"""

import os

os.environ.setdefault("AURA_TEST_MODE", "true")
os.environ.setdefault("REDIS_ENABLED", "false")
os.environ.setdefault("TESTING", "true")
