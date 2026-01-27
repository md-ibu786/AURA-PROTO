# config.py
# Centralized configuration for AI services and Firestore access

# Longer description (2-4 lines):
# - Loads .env values and exposes constants for Vertex AI, Neo4j, Redis,
#   and Celery settings used across the API and services layer.
# - Initializes Firebase Admin SDK and provides Firestore clients so
#   task modules can import db/async_db consistently.

# @see: AURA-NOTES-MANAGER/.env - Environment variable values
# @note: Defaults support local development without secrets

import os
from pathlib import Path

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.async_client import AsyncClient


# Load environment variables from .env
dotenv_path = Path(__file__).parent.parent / ".env"
if dotenv_path.exists():
    load_dotenv(dotenv_path)

# Google Cloud / Vertex AI Configuration
VERTEX_PROJECT = os.getenv("VERTEX_PROJECT", "lucky-processor-480412-n8")
VERTEX_LOCATION = os.getenv("VERTEX_LOCATION", "us-central1")
VERTEX_CREDENTIALS = os.getenv(
    "VERTEX_CREDENTIALS",
    str(Path(__file__).parent.parent / "service_account.json"),
)
GOOGLE_APPLICATION_CREDENTIALS = os.getenv(
    "GOOGLE_APPLICATION_CREDENTIALS",
    VERTEX_CREDENTIALS,
)

# Set GOOGLE_APPLICATION_CREDENTIALS for Vertex AI SDK
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = GOOGLE_APPLICATION_CREDENTIALS

# LLM Model Configuration
LLM_ENTITY_EXTRACTION_MODEL = os.getenv(
    "LLM_ENTITY_EXTRACTION_MODEL",
    "gemini-2.5-flash-lite",
)
LLM_SUMMARIZATION_MODEL = os.getenv(
    "LLM_SUMMARIZATION_MODEL",
    "gemini-2.5-flash-lite",
)
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "text-embedding-004",
)

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


def init_firebase():
    """Initializes Firebase Admin SDK and returns Firestore client."""
    if not firebase_admin._apps:
        key_path = os.environ.get("FIREBASE_CREDENTIALS")
        if key_path and not os.path.isabs(key_path):
            key_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                key_path,
            )

        if not key_path:
            key_path = os.path.join(
                os.path.dirname(os.path.dirname(__file__)),
                "serviceAccountKey.json",
            )

        if not os.path.exists(key_path):
            raise FileNotFoundError(
                f"Service account key not found at {key_path}",
            )

        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)

    return firestore.client()


def init_async_firebase():
    """Returns an async Firestore client for async endpoints."""
    if not firebase_admin._apps:
        init_firebase()

    key_path = os.environ.get("FIREBASE_CREDENTIALS")
    if key_path and not os.path.isabs(key_path):
        key_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            key_path,
        )
    if not key_path:
        key_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "serviceAccountKey.json",
        )

    from google.oauth2 import service_account

    creds = service_account.Credentials.from_service_account_file(key_path)
    return AsyncClient(credentials=creds)


db = init_firebase()
async_db = init_async_firebase()
