"""
============================================================================
FILE: conftest.py
LOCATION: api/tests/conftest.py
============================================================================

PURPOSE:
    Pytest configuration for API tests with import mocking for Python 3.14 compatibility.

ROLE IN PROJECT:
    Sets up test environment before imports to avoid Python 3.14 protobuf compatibility issues.
    Mocks all google.cloud and firebase admin imports that fail on Python 3.14.

KEY COMPONENTS:
    - MockAsyncClient: Mock for AsyncClient
    - MockFieldFilter: Mock for FieldFilter class
    - Comprehensive sys.modules patching for google packages

DEPENDENCIES:
    - External: pytest, sys, unittest.mock
    - Internal: None

USAGE:
    Automatically loaded by pytest when running tests in api/tests/.
    Tests can safely import api modules that depend on Firestore/Firebase.
============================================================================
"""

import sys
from unittest.mock import MagicMock

# Create comprehensive mock for google package hierarchy
# This MUST be done before any imports


class MockAsyncClient:
    """Mock for AsyncClient."""

    def __init__(self, *args, **kwargs):
        pass


class MockFieldFilter:
    """Mock for firestore FieldFilter."""

    def __init__(self, *args, **kwargs):
        pass


# Create mock modules with necessary attributes
def create_mock_module():
    """Create a mock module that allows attribute access."""
    return MagicMock()


# Mock google package hierarchy
mock_google = create_mock_module()
mock_google_cloud = create_mock_module()
mock_google_auth = create_mock_module()
mock_google_auth_exceptions = create_mock_module()

# Add exceptions module
mock_google_auth_exceptions.DefaultCredentialsError = Exception
mock_google.auth = mock_google_auth

# Mock Firestore
mock_firestore_v1 = create_mock_module()
mock_firestore_v1.AsyncClient = MockAsyncClient
mock_firestore_v1.FieldFilter = MockFieldFilter

mock_firestore = create_mock_module()
mock_firestore.FieldFilter = MockFieldFilter

mock_google_cloud.firestore = mock_firestore
mock_google.cloud = mock_google_cloud

# Mock Firebase Admin
mock_firebase_admin = create_mock_module()
mock_firebase_app = create_mock_module()
mock_firebase_credentials = create_mock_module()
mock_firebase_firestore = create_mock_module()
mock_firebase_auth = create_mock_module()

# Patch sys.modules before ANY imports happen
sys.modules.setdefault("google", mock_google)
sys.modules.setdefault("google.cloud", mock_google_cloud)
sys.modules.setdefault("google.cloud.firestore", mock_firestore)
sys.modules.setdefault("google.cloud.firestore_v1", mock_firestore_v1)
sys.modules.setdefault("google.auth", mock_google_auth)
sys.modules.setdefault("google.auth.exceptions", mock_google_auth_exceptions)
sys.modules.setdefault("firebase_admin", mock_firebase_admin)
sys.modules.setdefault("firebase_admin.app", mock_firebase_app)
sys.modules.setdefault("firebase_admin.credentials", mock_firebase_credentials)
sys.modules.setdefault("firebase_admin.firestore", mock_firebase_firestore)
sys.modules.setdefault("firebase_admin.auth", mock_firebase_auth)
