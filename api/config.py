# config.py
# Centralized configuration for AI services and infrastructure

# Longer description (2-4 lines):
# - Loads .env values and exposes constants for Vertex AI, Neo4j, Redis,
#   and Celery settings used across the API and services layer.
# - Ensures GOOGLE_APPLICATION_CREDENTIALS is set for Vertex AI SDK usage
#   to keep authentication consistent across environments.

# @see: AURA-NOTES-MANAGER/.env - Environment variable values
# @note: Defaults support local development without secrets

import os
from pathlib import Path

from dotenv import load_dotenv


# Load environment variables from .env
dotenv_path = Path(__file__).parent.parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

# Google Cloud / Vertex AI Configuration
VERTEX_PROJECT = os.getenv("VERTEX_PROJECT", "lucky-processor-480412-n8")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
VERTEX_CREDENTIALS = os.getenv(
    "VERTEX_CREDENTIALS",
    "AURA-NOTES-MANAGER/service_account.json",
)
GOOGLE_APPLICATION_CREDENTIALS = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    VERTEX_CREDENTIALS,
)

# Set GOOGLE_APPLICATION_CREDENTIALS for Vertex AI SDK
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

# LLM Model Configuration
LLM_ENTITY_EXTRACTION_MODEL = "gemini-2.5-flash-lite"
LLM_SUMMARIZATION_MODEL = "gemini-2.5-flash-lite"
EMBEDDING_MODEL = "text-embedding-004"

# Test Mode (set to True to skip actual API calls)
AURA_TEST_MODE = os.getenv("AURA_TEST_MODE", "false").lower() == "true"

# Neo4j Configuration
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://127.0.0.1:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "password")

# Redis Configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")

# Celery Configuration
CELERY_RESULT_EXPIRES = int(os.getenv("CELERY_RESULT_EXPIRES", "3600"))
