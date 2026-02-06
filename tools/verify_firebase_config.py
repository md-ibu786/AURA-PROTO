"""
============================================================================
FILE: verify_firebase_config.py
LOCATION: tools/verify_firebase_config.py
============================================================================

PURPOSE:
    Validate Firebase configuration without starting the API server.

ROLE IN PROJECT:
    - Confirms environment variables and credentials are set
    - Verifies Firebase Admin SDK initialization and Firestore access

KEY COMPONENTS:
    - load_env: Loads .env from project root
    - verify_config: Runs Firebase connectivity checks

DEPENDENCIES:
    - External: firebase_admin, python-dotenv
    - Internal: None

USAGE:
    python tools/verify_firebase_config.py
============================================================================
"""

import json
import os
from pathlib import Path
import sys

import dotenv
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_env():
    """Load environment variables from .env in project root.

    Args:
        None.

    Returns:
        Path or None: Path to .env if loaded, otherwise None.

    Raises:
        None.
    """
    env_path = PROJECT_ROOT / ".env"
    if env_path.exists():
        dotenv.load_dotenv(env_path)
        return env_path
    return None


def is_real_firebase_enabled():
    """Check whether real Firebase mode is enabled.

    Args:
        None.

    Returns:
        bool: True if USE_REAL_FIREBASE is "true".

    Raises:
        None.
    """
    return os.getenv("USE_REAL_FIREBASE", "false").lower() == "true"


def resolve_credentials_path():
    """Resolve the service account JSON path.

    Args:
        None.

    Returns:
        Path: Absolute path to credentials file.

    Raises:
        None.
    """
    env_path = os.getenv("FIREBASE_CREDENTIALS")
    if env_path:
        path = Path(env_path)
        if not path.is_absolute():
            path = PROJECT_ROOT / env_path
        return path
    return PROJECT_ROOT / "serviceAccountKey-auth.json"


def validate_json_file(path):
    """Validate JSON file contents.

    Args:
        path (Path): Path to the JSON file.

    Returns:
        None.

    Raises:
        json.JSONDecodeError: If the file is invalid JSON.
        FileNotFoundError: If the file does not exist.
    """
    with path.open("r", encoding="utf-8") as file_handle:
        json.load(file_handle)


def init_firebase(path):
    """Initialize Firebase Admin SDK with credentials.

    Args:
        path (Path): Path to credentials file.

    Returns:
        None.

    Raises:
        ValueError: If credentials are invalid.
    """
    if firebase_admin._apps:
        return
    cred = credentials.Certificate(str(path))
    firebase_admin.initialize_app(cred)


def verify_config():
    """Verify Firebase configuration and connectivity.

    Args:
        None.

    Returns:
        int: Exit code (0 for success).

    Raises:
        FileNotFoundError: If credentials file is missing.
        json.JSONDecodeError: If credentials file is invalid JSON.
        ValueError: If credentials are invalid.
        Exception: For Firestore connection or network errors.
    """
    load_env()
    if os.getenv("USE_REAL_FIREBASE") is None:
        print("USE_REAL_FIREBASE not set; defaulting to false.")

    if not is_real_firebase_enabled():
        print("USE_REAL_FIREBASE=false. Mock mode active.")
        return 0

    if os.getenv("FIREBASE_CREDENTIALS") is None:
        print("FIREBASE_CREDENTIALS not set; using default path.")

    credentials_path = resolve_credentials_path()
    if not credentials_path.exists():
        raise FileNotFoundError(
            f"Firebase credentials not found: {credentials_path}",
        )

    validate_json_file(credentials_path)
    init_firebase(credentials_path)

    client = firestore.client()
    collections = list(client.collections())
    print(f"Connected to Firestore. Collections: {len(collections)}")
    return 0


def main():
    """Run configuration verification.

    Args:
        None.

    Returns:
        None.

    Raises:
        SystemExit: Exits with status code from verification.
    """
    try:
        exit_code = verify_config()
    except FileNotFoundError as exc:
        print(f"Error: {exc}")
        sys.exit(1)
    except json.JSONDecodeError as exc:
        print("Error: Service account file is not valid JSON.")
        print(f"Details: {exc}")
        sys.exit(1)
    except ValueError as exc:
        print("Error: Firebase credentials are invalid.")
        print(f"Details: {exc}")
        sys.exit(1)
    except Exception as exc:
        print("Error: Firebase connection failed.")
        print(f"Details: {exc}")
        sys.exit(1)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
