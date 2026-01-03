
import os
import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore_v1.async_client import AsyncClient

def init_firebase():
    """Initializes Firebase Admin SDK and returns Firestore client."""
    # Check if already initialized to prevent errors during reloads
    if not firebase_admin._apps:
        # Path to service account key - looking in root directory
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
    
    # AsyncClient uses Application Default Credentials from the environment
    # Since firebase_admin.initialize_app sets these, it should work.
    key_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "serviceAccountKey.json")
    from google.oauth2 import service_account
    creds = service_account.Credentials.from_service_account_file(key_path)
    return AsyncClient(credentials=creds)

# Global Firestore client instances
db = init_firebase()
async_db = init_async_firebase()
