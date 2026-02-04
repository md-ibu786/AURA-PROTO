"""
============================================================================
FILE: config.py
LOCATION: api/config.py
============================================================================

PURPOSE:
    Centralized configuration for AI services and Firestore access.

ROLE IN PROJECT:
    Loads environment variables and initializes Firestore clients for the
    API layer, supporting mock and real Firebase usage.

KEY COMPONENTS:
    - get_db: Returns mock or real Firestore client
    - init_firebase: Initializes Firebase Admin SDK
    - init_async_firebase: Initializes async Firestore client

DEPENDENCIES:
    - External: firebase_admin, google-cloud-firestore, python-dotenv
    - Internal: mock_firestore (optional)

USAGE:
    from config import db, async_db
============================================================================
"""

import os
from pathlib import Path

import firebase_admin
from dotenv import load_dotenv
from firebase_admin import credentials, firestore, auth as firebase_auth
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

# Mock Database Configuration
USE_MOCK_DB = os.environ.get("USE_REAL_FIREBASE", "false").lower() != "true"

# Global database instance
_db_instance = None


def get_db():
    """
    Get Firestore database client (mock or real).

    Returns MockFirestoreClient if USE_MOCK_DB is True, otherwise returns
    real Firestore client. Uses singleton pattern to avoid re-initialization.

    Returns:
        Firestore client or MockFirestoreClient instance
    """
    global _db_instance
    if _db_instance is None:
        if USE_MOCK_DB:
            from mock_firestore import MockFirestoreClient

            _db_instance = MockFirestoreClient()
        else:
            # Real Firebase initialization
            _db_instance = init_firebase()
    return _db_instance


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


# Initialize database clients
# Use get_db() to support mock database toggle
db = get_db()

# If using mock DB, monkeypatch firestore.transactional to avoid errors
if USE_MOCK_DB:
    try:
        from google.cloud import firestore as gcloud_firestore
        from mock_firestore import mock_transactional
        gcloud_firestore.transactional = mock_transactional
    except ImportError:
        pass

# Initialize async_db only if using real Firebase
if not USE_MOCK_DB:
    try:
        async_db = init_async_firebase()
    except Exception:
        # Fallback to sync client if async initialization fails
        async_db = db
else:
    async_db = db

if USE_MOCK_DB:
    from mock_firestore import MockAuth

    auth = MockAuth()
else:
    auth = firebase_auth
