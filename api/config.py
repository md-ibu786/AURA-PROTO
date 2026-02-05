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

import dotenv
import firebase_admin
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.async_client import AsyncClient


# Load environment variables from .env
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DOTENV_PATH = PROJECT_ROOT / ".env"
if DOTENV_PATH.exists():
    dotenv.load_dotenv(DOTENV_PATH, override=True)

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
USE_REAL_FIREBASE = os.getenv("USE_REAL_FIREBASE", "false").lower() == "true"
USE_MOCK_DB = not USE_REAL_FIREBASE

# Global database instance
_db_instance = None
_auth_instance = None


def _resolve_credentials_path():
    """Resolve the Firebase credentials file path.

    Args:
        None.

    Returns:
        Path: Absolute path to the service account JSON file.

    Raises:
        None.
    """
    env_path = os.getenv("FIREBASE_CREDENTIALS")
    if env_path:
        path = Path(env_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / env_path
        return path
    return PROJECT_ROOT / "serviceAccountKey.json"


def get_db():
    """Get Firestore database client (mock or real).

    Args:
        None.

    Returns:
        object: Firestore client or MockFirestoreClient instance.

    Raises:
        FileNotFoundError: If real Firebase credentials are missing.
    """
    global _db_instance
    if _db_instance is None:
        if USE_MOCK_DB:
            from mock_firestore import get_mock_db

            _db_instance = get_mock_db()
        else:
            init_firebase()
            _db_instance = firestore.client()
    return _db_instance


def init_firebase():
    """Initialize Firebase Admin SDK.

    Args:
        None.

    Returns:
        None.

    Raises:
        FileNotFoundError: If real Firebase credentials are missing.
    """
    if not firebase_admin._apps:
        if USE_REAL_FIREBASE:
            key_path = _resolve_credentials_path()
            if not key_path.exists():
                raise FileNotFoundError(
                    f"Firebase credentials not found: {key_path}",
                )
            cred = credentials.Certificate(str(key_path))
            firebase_admin.initialize_app(cred)
            print("Firebase initialized with service account")
        else:
            firebase_admin.initialize_app()


def init_async_firebase():
    """Return an async Firestore client for async endpoints.

    Args:
        None.

    Returns:
        AsyncClient: Async Firestore client instance.

    Raises:
        FileNotFoundError: If real Firebase credentials are missing.
    """
    if not firebase_admin._apps:
        init_firebase()

    key_path = _resolve_credentials_path()
    from google.oauth2 import service_account

    creds = service_account.Credentials.from_service_account_file(
        str(key_path),
    )
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


def get_auth():
    """Get Firebase auth module or mock auth.

    Args:
        None.

    Returns:
        object: MockAuth instance or firebase_admin.auth module.

    Raises:
        None.
    """
    global _auth_instance
    if _auth_instance is None:
        if USE_MOCK_DB:
            from mock_firestore import MockAuth

            _auth_instance = MockAuth()
        else:
            init_firebase()
            _auth_instance = firebase_auth
    return _auth_instance


auth = get_auth()
