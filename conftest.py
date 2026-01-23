# conftest.py
# Pytest configuration for AURA-NOTES-MANAGER test environment
#
# Sets test-mode environment flags to avoid external service initialization.
#
# @see: api/neo4j_config.py - Skips Neo4j init in test mode
# @note: Uses AURA_TEST_MODE=true for hermetic tests

import os

os.environ.setdefault("AURA_TEST_MODE", "true")
os.environ.setdefault("REDIS_ENABLED", "false")
