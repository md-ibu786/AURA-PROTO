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

DEPENDENCIES:
    - External: pytest, sys, unittest.mock, types

USAGE:
    Automatically loaded by pytest when running tests in api/tests/.
    Tests can safely import api modules that depend on Firestore/Firebase.
============================================================================
"""

import sys
from unittest.mock import MagicMock
import types


class MockModule(types.ModuleType):
    """
    A module-like object that allows any attribute access and import.
    Automatically registers sub-modules in sys.modules when accessed.
    """

    def __init__(self, name, auto_register=True):
        super().__init__(name)
        self._attrs = {}
        self._auto_register = auto_register

    def __getattr__(self, name):
        if name not in self._attrs:
            child_name = f"{self.__name__}.{name}"
            child = MockModule(child_name, self._auto_register)
            self._attrs[name] = child
            # Always auto-register in sys.modules for sub-modules
            if self._auto_register:
                sys.modules[child_name] = child
        return self._attrs[name]

    def __call__(self, *args, **kwargs):
        return MagicMock()

    def __iter__(self):
        """Allow iteration over module attributes for Python's import system."""
        return iter([])


# Pre-populate sys.modules with mocks BEFORE any imports happen
# This ensures that when api modules import google/firebase packages,
# they get our mocks instead of trying to load the real packages

# Google Cloud mocks
google = MockModule("google", auto_register=True)
sys.modules["google"] = google

google_cloud = MockModule("google.cloud", auto_register=True)
sys.modules["google.cloud"] = google_cloud

firestore_v1 = MockModule("google.cloud.firestore_v1", auto_register=True)
firestore_v1.AsyncClient = MagicMock()
firestore_v1.FieldFilter = MagicMock()
sys.modules["google.cloud.firestore_v1"] = firestore_v1

firestore_async_client = MockModule(
    "google.cloud.firestore_v1.async_client", auto_register=True
)
firestore_async_client.AsyncClient = MagicMock()
sys.modules["google.cloud.firestore_v1.async_client"] = firestore_async_client

firestore = MockModule("google.cloud.firestore", auto_register=True)
firestore.FieldFilter = MagicMock()
sys.modules["google.cloud.firestore"] = firestore

google_auth = MockModule("google.auth", auto_register=True)
sys.modules["google.auth"] = google_auth

google_auth_exceptions = MockModule("google.auth.exceptions", auto_register=True)
google_auth_exceptions.DefaultCredentialsError = Exception
sys.modules["google.auth.exceptions"] = google_auth_exceptions

# Firebase Admin mocks
firebase_admin = MockModule("firebase_admin", auto_register=True)
sys.modules["firebase_admin"] = firebase_admin

firebase_admin_app = MockModule("firebase_admin.app", auto_register=True)
sys.modules["firebase_admin.app"] = firebase_admin_app

firebase_admin_credentials = MockModule(
    "firebase_admin.credentials", auto_register=True
)
sys.modules["firebase_admin.credentials"] = firebase_admin_credentials

firebase_admin_firestore = MockModule("firebase_admin.firestore", auto_register=True)
sys.modules["firebase_admin.firestore"] = firebase_admin_firestore

firebase_admin_auth = MockModule("firebase_admin.auth", auto_register=True)
firebase_admin_auth.auth = MagicMock()
firebase_admin.auth = firebase_admin_auth  # Wire auth into firebase_admin
sys.modules["firebase_admin.auth"] = firebase_admin_auth

# model_router mocks
model_router = MockModule("model_router", auto_register=True)
model_router.get_default_router = MagicMock(return_value=MagicMock())
model_router.resolve_use_case_config = MagicMock(return_value=MagicMock())
sys.modules["model_router"] = model_router

model_router_compat = MockModule("model_router.compat", auto_register=True)
sys.modules["model_router.compat"] = model_router_compat

# services mocks - use auto_register=True so sub-modules are auto-registered
services = MockModule("services", auto_register=True)
sys.modules["services"] = services

vertex_ai_client = MockModule("services.vertex_ai_client", auto_register=True)
sys.modules["services.vertex_ai_client"] = vertex_ai_client

chunking_utils = MockModule("services.chunking_utils", auto_register=True)
chunking_utils.count_tokens = MagicMock(return_value=100)
chunking_utils.split_into_sentences = MagicMock(return_value=["sentence1", "sentence2"])
sys.modules["services.chunking_utils"] = chunking_utils
