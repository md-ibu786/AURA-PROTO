"""
============================================================================
FILE: config.py
LOCATION: api/config.py
============================================================================

PURPOSE:
    Handles Firebase Admin SDK initialization and provides Firestore database
    client instances (both synchronous and asynchronous) for the entire
    backend application.

ROLE IN PROJECT:
    This is the database configuration layer. All modules that need to
    interact with Firestore import `db` or `async_db` from this file.
    It ensures Firebase is initialized only once (preventing errors during
    hot-reloads in development) and handles credential path resolution.

KEY COMPONENTS:
    - init_firebase(): Initializes Firebase Admin SDK and returns sync Firestore client
    - init_async_firebase(): Returns an async Firestore client for async endpoints
    - db: Global synchronous Firestore client instance
    - async_db: Global asynchronous Firestore client instance

DEPENDENCIES:
    - External: firebase_admin, google-cloud-firestore
    - Internal: Reads serviceAccountKey.json from project root

USAGE:
    from config import db, async_db
    
    # Sync operations
    docs = db.collection('departments').stream()
    
    # Async operations  
    async for doc in async_db.collection('departments').stream():
        ...

ENVIRONMENT VARIABLES:
    - FIREBASE_CREDENTIALS: Optional path to service account key JSON
      (falls back to serviceAccountKey.json in project root)
============================================================================
"""

import os
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.async_client import AsyncClient

def init_firebase():
    """Initializes Firebase Admin SDK and returns Firestore client."""
    # Check if already initialized to prevent errors during reloads
    if not firebase_admin._apps:
        # Check for FIREBASE_CREDENTIALS env var first, fallback to hardcoded path
        key_path = os.environ.get("FIREBASE_CREDENTIALS")
        if key_path and not os.path.isabs(key_path):
            # Resolve relative path from project root
            key_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), key_path)
        
        if not key_path:
            # Fallback to default location
            key_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "serviceAccountKey.json")
        
        if not os.path.exists(key_path):
            raise FileNotFoundError(f"Service account key not found at {key_path}")

        cred = credentials.Certificate(key_path)
        firebase_admin.initialize_app(cred)
    
    return firestore.client()

def init_async_firebase():
    """Returns an async Firestore client (shares credentials with sync client)."""
    # Ensure sync initialization happened first
    if not firebase_admin._apps:
        init_firebase()
    
    # Get credentials path from env var or fallback
    key_path = os.environ.get("FIREBASE_CREDENTIALS")
    if key_path and not os.path.isabs(key_path):
        key_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), key_path)
    if not key_path:
        key_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "serviceAccountKey.json")
    
    from google.oauth2 import service_account
    creds = service_account.Credentials.from_service_account_file(key_path)
    return AsyncClient(credentials=creds)

# Global Firestore client instances
db = init_firebase()
async_db = init_async_firebase()
