"""
============================================================================
FILE: mock_firestore.py
LOCATION: api/mock_firestore.py
============================================================================

PURPOSE:
    Mock implementations for Firebase Firestore and Authentication services.
    Provides in-memory implementations of Firestore-like collections, documents,
    queries, and transactions for testing without connecting to real Firebase.

ROLE IN PROJECT:
    - Enables offline/unit testing of code that depends on Firestore
    - Provides mock data persistence using a JSON file (mock_db.json)
    - Supports both sync and async iteration patterns
    - Mimics Firebase Auth for user management testing

KEY COMPONENTS:
    - MockFirestoreClient: Main client class for mock Firestore operations
    - MockCollectionReference: Implements collection.query methods
    - MockDocumentReference: Implements document CRUD operations
    - MockDocumentSnapshot: Represents document state with to_dict()
    - MockQuery: Supports where(), order_by(), limit() operations
    - MockTransaction: Implements transactional operations
    - MockAuth: Mock Firebase Authentication service
    - MockUserRecord: User data container for auth mocking

DEPENDENCIES:
    - External: None (pure Python implementation)
    - Internal: None (self-contained module)

USAGE:
    from mock_firestore import MockFirestoreClient

    client = MockFirestoreClient()
    collection = client.collection('users')
    doc = collection.document('user-1')
    doc.set({'name': 'John', 'age': 30})

============================================================================
"""
import json
import os
import time
from typing import Any, Dict, List, Optional, Generator, AsyncGenerator


class MockAsyncIterator:
    """Wrapper to support both sync and async iteration over a list of items."""

    def __init__(self, items):
        self.items = items
        self.index = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.index >= len(self.items):
            raise StopIteration
        item = self.items[self.index]
        self.index += 1
        return item

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return self.__next__()
        except StopIteration:
            raise StopAsyncIteration


class MockDocumentReference:
    def __init__(self, collection_parent, document_id, data=None):
        self.parent = collection_parent
        self.id = document_id
        # Don't store data in self._data if it's a reference to the DB dict.
        # Instead, fetch it dynamically or store a local copy?
        # To support mutable operations that reflect in DB, we need to access parent._docs directly.
        pass

    @property
    def _data(self):
        # Dynamic access to backend storage
        return self.parent._docs.get(self.id)

    @property
    def path(self):
        return f"{self.parent.path}/{self.id}"

    def get(self, transaction=None):
        data = self._data
        return MockDocumentSnapshot(self, data, exists=bool(data is not None))

    def set(self, data: Dict[str, Any], merge=False):
        if merge:
            if self.id not in self.parent._docs:
                self.parent._docs[self.id] = {}
            self.parent._docs[self.id].update(data)
        else:
            self.parent._docs[self.id] = data
        self.parent._save()

    def update(self, data: Dict[str, Any]):
        if self.id not in self.parent._docs:
            raise Exception(f"Document {self.path} does not exist")
        self.parent._docs[self.id].update(data)
        self.parent._save()

    def delete(self):
        if self.id in self.parent._docs:
            del self.parent._docs[self.id]
        self.parent._save()

    def collection(self, collection_name):
        full_path = f"{self.path}/{collection_name}"
        return self.parent.client.collection(full_path)

    def collections(self):
        """Return all subcollections of this document."""
        prefix = f"{self.path}/"
        subcollections = []
        for path in self.parent.client._db_data.keys():
            if path.startswith(prefix) and path != prefix:
                # Extract the collection name (first part after the prefix)
                remaining = path[len(prefix) :]
                if "/" not in remaining:  # It's a direct subcollection
                    subcollections.append(self.parent.client.collection(path))
        return subcollections

    @property
    def reference(self):
        return self


class MockDocumentSnapshot:
    def __init__(self, ref, data, exists=True):
        self._ref = ref
        self.id = ref.id
        self._data = data if data is not None else {}
        self.exists = exists

    def to_dict(self):
        return self._data

    def get(self, field_path):
        if not self.exists or not self._data:
            return None

        parts = field_path.split(".")
        curr = self._data
        for part in parts:
            if isinstance(curr, dict) and part in curr:
                curr = curr[part]
            else:
                return None
        return curr

    @property
    def reference(self):
        return self._ref


class MockCollectionReference:
    def __init__(self, client, path):
        self.client = client
        self.path = path
        self.id = path.split("/")[-1]

        if path not in self.client._db_data:
            self.client._db_data[path] = {}
        self._docs = self.client._db_data[path]

    def document(self, document_id=None):
        if not document_id:
            import uuid

            document_id = str(uuid.uuid4())[:20]

        # KEY FIX: Do NOT create empty entry in _docs here
        return MockDocumentReference(self, document_id)

    def add(self, data: Dict[str, Any]):
        doc_ref = self.document()
        doc_ref.set(data)
        return None, doc_ref

    def where(self, field, op, value):
        return MockQuery(self, filters=[(field, op, value)])

    def limit(self, count):
        return MockQuery(self, limit=count)

    def order_by(self, field, direction="ASCENDING"):
        return MockQuery(self, order_by=(field, direction))

    def stream(self):
        items = []
        for doc_id, data in self._docs.items():
            # Only include if data is not None
            # Also, strictly speaking, empty dict IS a document in Firestore,
            # but for our "Ghost" bug, we probably want to treat it as valid.
            # The bug was creating keys with empty dicts for IDs that shouldn't exist.
            # If we fix document(), those keys won't be created anymore.
            # But we should also filter out existing ghosts if possible?
            # Let's just trust valid entries.
            if data is not None:
                ref = self.document(doc_id)
                items.append(MockDocumentSnapshot(ref, data, exists=True))
        return MockAsyncIterator(items)

    def _save(self):
        self.client._save_db()


class MockQuery:
    def __init__(self, collection, filters=None, limit=None, order_by=None):
        self.collection = collection
        self.filters = filters or []
        self.limit_val = limit
        self.order_by_val = order_by  # Tuple (field, direction)

    def where(self, field, op, value):
        self.filters.append((field, op, value))
        return self

    def limit(self, count):
        self.limit_val = count
        return self

    def order_by(self, field, direction="ASCENDING"):
        self.order_by_val = (field, direction)
        return self

    def stream(self):
        results = []
        for doc_id, data in self.collection._docs.items():
            match = True
            for field, op, value in self.filters:
                # Handle dot notation?
                val = data.get(field)
                if op == "==":
                    if val != value:
                        match = False
                elif op == ">":
                    if not (val is not None and val > value):
                        match = False
                elif op == ">=":
                    if not (val is not None and val >= value):
                        match = False
                elif op == "<":
                    if not (val is not None and val < value):
                        match = False
                elif op == "<=":
                    if not (val is not None and val <= value):
                        match = False
                elif op == "array_contains":
                    if not (isinstance(val, list) and value in val):
                        match = False
                elif op == "in":
                    if not (value and val in value):
                        match = False

            if match:
                ref = self.collection.document(doc_id)
                results.append(MockDocumentSnapshot(ref, data, exists=True))

        # Apply Sorting
        if self.order_by_val:
            field, direction = self.order_by_val
            reverse = direction == "DESCENDING"

            def sort_key(doc):
                val = doc._data.get(field)
                # Handle None values safely
                if val is None:
                    return "" if not reverse else "zzzz"
                return str(val)  # Simple string sort for mock

            results.sort(key=sort_key, reverse=reverse)

        if self.limit_val:
            results = results[: self.limit_val]

        return MockAsyncIterator(results)


class MockFirestoreClient:
    def __init__(self, db_file="mock_db.json"):
        self.db_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), db_file)
        self._db_data = {}
        self.reload()

    def reload(self):
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, "r") as f:
                    self._db_data = json.load(f)
            except:
                self._db_data = {}
        else:
            self._db_data = {}

    def _save_db(self):
        with open(self.db_file, "w") as f:
            json.dump(self._db_data, f, indent=2, default=str)

    def collection(self, name):
        return MockCollectionReference(self, name)

    def collection_group(self, collection_id):
        # Scan ALL paths for keys ending in collection_id
        # This is expensive but correct for a mock
        all_matches = []
        for path, docs in self._db_data.items():
            if path.split("/")[-1] == collection_id:
                coll_parent = self.collection(path)
                for doc_id, data in docs.items():
                    ref = coll_parent.document(doc_id)
                    all_matches.append(MockDocumentSnapshot(ref, data, exists=True))

        # Return a MockQuery-like object that has these results pre-loaded?
        # Or a special Chainable object
        return MockPreloadedQuery(all_matches)

    def transaction(self):
        return MockTransaction(self)


def get_mock_db():
    """Create a mock Firestore client instance.

    Args:
        None.

    Returns:
        MockFirestoreClient: New mock client instance.

    Raises:
        None.
    """
    return MockFirestoreClient()


class MockPreloadedQuery:
    def __init__(self, items):
        self.items = items

    def where(self, field, op, value):
        # Filter existing items
        filtered = []
        for doc in self.items:
            data = doc._data
            val = data.get(field)
            if op == "==":
                if val == value:
                    filtered.append(doc)
        return MockPreloadedQuery(filtered)

    def stream(self):
        return MockAsyncIterator(self.items)


class MockTransaction:
    def __init__(self, client):
        self.client = client
        self._read_only = False  # Needed by real firestore transactional decorator

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def get(self, ref):
        return ref.get()

    def set(self, ref, data):
        ref.set(data)

    def update(self, ref, data):
        ref.update(data)

    def delete(self, ref):
        ref.delete()


def mock_transactional(func):
    def wrapper(*args, **kwargs):
        # Just run it, our mock doesn't do real ACID transactions
        # We need to construct a dummy transaction object to pass if the func expects one
        return func(MockTransaction(None), *args, **kwargs)

    return wrapper


class MockUserRecord:
    def __init__(self, uid, email, display_name=None, password=None, disabled=False):
        self.uid = uid
        self.email = email
        self.display_name = display_name
        self._password = password
        self.disabled = disabled


class MockAuthError(Exception):
    pass


class MockEmailAlreadyExistsError(MockAuthError):
    pass


class MockUserNotFoundError(MockAuthError):
    pass


class MockAuth:
    # Mimic exception classes on the instance/class level so users can import them via auth.EmailAlreadyExistsError
    EmailAlreadyExistsError = MockEmailAlreadyExistsError
    UserNotFoundError = MockUserNotFoundError

    def __init__(self):
        self._users = {}  # uid -> MockUserRecord

    def create_user(
        self,
        email=None,
        password=None,
        display_name=None,
        email_verified=False,
        disabled=False,
        **kwargs,
    ):
        if not email:
            raise ValueError("Email required")
        # Check duplicates
        for u in self._users.values():
            if u.email == email:
                raise self.EmailAlreadyExistsError("Email already exists")

        import time

        uid = f"mock-user-{int(time.time() * 1000)}"
        user = MockUserRecord(uid, email, display_name, password, disabled)
        self._users[uid] = user
        return user

    def get_user(self, uid):
        if uid not in self._users:
            raise self.UserNotFoundError("User not found")
        return self._users[uid]

    def get_user_by_email(self, email):
        for u in self._users.values():
            if u.email == email:
                return u
        raise self.UserNotFoundError("User not found")

    def update_user(self, uid, **kwargs):
        if uid not in self._users:
            raise self.UserNotFoundError("User not found")
        user = self._users[uid]
        if "display_name" in kwargs:
            user.display_name = kwargs["display_name"]
        if "disabled" in kwargs:
            user.disabled = kwargs["disabled"]
        if "email" in kwargs:
            user.email = kwargs["email"]
        return user

    def delete_user(self, uid):
        if uid in self._users:
            del self._users[uid]
        # If not found, ignore (idempotent)? or verify behaviors.
        # Real Firebase raises UserNotFoundError usually.
        # But for mock, let's keep it simple.

    def verify_id_token(self, token, check_revoked=False, clock_skew_seconds=0):
        # Allow checking tokens if needed
        if token.startswith("mock-token-"):
            # Parse it
            parts = token.split("-")
            return {
                "uid": parts[3] if len(parts) > 3 else "uid",
                "email": "test@test.com",
            }
        raise Exception("Invalid mock token")
