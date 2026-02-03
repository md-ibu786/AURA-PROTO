# mock_firestore.py
# Mock Firestore client for local authentication development without Firebase credentials

# Provides complete mock implementations of Firestore classes (Collection, Document,
# Query, Snapshot) and MockAuth for token verification. Enables local development
# and testing of auth flows without requiring real Firebase project setup.

# @see: api/config.py - Database initialization
# @see: api/auth.py - Uses MockAuth for token verification
# @note: Sync implementation only - async would add unnecessary complexity for local dev

from typing import Any, Optional, Dict, List, Iterator
import uuid
from datetime import datetime


# Global in-memory database
MOCK_DB: Dict[str, Dict[str, Any]] = {}


class MockDocumentSnapshot:
    """Wrapper for document data returned by queries and get() operations."""
    
    def __init__(self, doc_id: str, data: Optional[Dict[str, Any]]):
        self._id = doc_id
        self._data = data
    
    @property
    def exists(self) -> bool:
        """Returns True if document exists."""
        return self._data is not None
    
    @property
    def id(self) -> str:
        """Returns document ID."""
        return self._id
    
    def to_dict(self) -> Optional[Dict[str, Any]]:
        """Returns document data as dictionary."""
        return self._data
    
    def get(self, field: str) -> Any:
        """Get specific field value from document."""
        if self._data is None:
            return None
        return self._data.get(field)


class MockDocumentReference:
    """Document reference with CRUD operations."""
    
    def __init__(self, collection_name: str, doc_id: str):
        self._collection_name = collection_name
        self._doc_id = doc_id
    
    @property
    def id(self) -> str:
        """Returns document ID."""
        return self._doc_id
    
    def get(self) -> MockDocumentSnapshot:
        """Fetch document from MOCK_DB."""
        if self._collection_name not in MOCK_DB:
            return MockDocumentSnapshot(self._doc_id, None)
        
        data = MOCK_DB[self._collection_name].get(self._doc_id)
        return MockDocumentSnapshot(self._doc_id, data)
    
    def set(self, data: Dict[str, Any], merge: bool = False) -> None:
        """Store document in MOCK_DB."""
        if self._collection_name not in MOCK_DB:
            MOCK_DB[self._collection_name] = {}
        
        if merge and self._doc_id in MOCK_DB[self._collection_name]:
            # Merge with existing data
            existing = MOCK_DB[self._collection_name][self._doc_id]
            existing.update(data)
        else:
            # Replace entirely
            MOCK_DB[self._collection_name][self._doc_id] = data.copy()
    
    def update(self, data: Dict[str, Any]) -> None:
        """Update existing document (merge operation)."""
        if self._collection_name not in MOCK_DB:
            MOCK_DB[self._collection_name] = {}
        
        if self._doc_id in MOCK_DB[self._collection_name]:
            MOCK_DB[self._collection_name][self._doc_id].update(data)
        else:
            # Create new if doesn't exist
            MOCK_DB[self._collection_name][self._doc_id] = data.copy()
    
    def delete(self) -> None:
        """Remove document from MOCK_DB."""
        if self._collection_name in MOCK_DB:
            MOCK_DB[self._collection_name].pop(self._doc_id, None)


class MockQuery:
    """Query builder with where() filtering and limit() support."""
    
    def __init__(self, collection_name: str, filters: Optional[List] = None, limit_count: Optional[int] = None):
        self._collection_name = collection_name
        self._filters = filters or []
        self._limit_count = limit_count
    
    def where(self, field: str, op: str, value: Any) -> "MockQuery":
        """Add filter condition to query."""
        new_filters = self._filters.copy()
        new_filters.append((field, op, value))
        return MockQuery(self._collection_name, new_filters, self._limit_count)
    
    def limit(self, n: int) -> "MockQuery":
        """Limit number of results."""
        return MockQuery(self._collection_name, self._filters, n)
    
    def _match_filters(self, doc_data: Dict[str, Any]) -> bool:
        """Check if document matches all filter conditions."""
        for field, op, value in self._filters:
            field_value = doc_data.get(field)
            
            if op == "==":
                if field_value != value:
                    return False
            elif op == "!=":
                if field_value == value:
                    return False
            elif op == "in":
                if field_value not in value:
                    return False
            # Add more operators as needed (>, <, >=, <=, etc.)
        
        return True
    
    def stream(self) -> Iterator[MockDocumentSnapshot]:
        """Yield matching documents as snapshots."""
        if self._collection_name not in MOCK_DB:
            return
        
        count = 0
        for doc_id, doc_data in MOCK_DB[self._collection_name].items():
            if self._match_filters(doc_data):
                yield MockDocumentSnapshot(doc_id, doc_data)
                count += 1
                
                if self._limit_count and count >= self._limit_count:
                    break
    
    def get(self) -> List[MockDocumentSnapshot]:
        """Return list of matching documents."""
        return list(self.stream())


class MockCollection:
    """Collection reference with document access and query building."""
    
    def __init__(self, collection_name: str):
        self._collection_name = collection_name
    
    def document(self, doc_id: Optional[str] = None) -> MockDocumentReference:
        """Get document reference by ID, or create new with auto-generated ID."""
        if doc_id is None:
            doc_id = str(uuid.uuid4())
        return MockDocumentReference(self._collection_name, doc_id)
    
    def where(self, field: str, op: str, value: Any) -> MockQuery:
        """Create query with filter."""
        query = MockQuery(self._collection_name)
        return query.where(field, op, value)
    
    def stream(self) -> Iterator[MockDocumentSnapshot]:
        """Yield all documents in collection."""
        if self._collection_name not in MOCK_DB:
            return
        
        for doc_id, doc_data in MOCK_DB[self._collection_name].items():
            yield MockDocumentSnapshot(doc_id, doc_data)
    
    def add(self, data: Dict[str, Any]) -> MockDocumentReference:
        """Create document with auto-generated ID."""
        doc_id = str(uuid.uuid4())
        doc_ref = self.document(doc_id)
        doc_ref.set(data)
        return doc_ref


class MockFirestoreClient:
    """Main Firestore client mock."""
    
    def __init__(self):
        """Initialize client and seed initial data."""
        _seed_initial_data()
    
    def collection(self, name: str) -> MockCollection:
        """Get collection reference by name."""
        return self._get_or_create_collection(name)
    
    def _get_or_create_collection(self, name: str) -> MockCollection:
        """Internal helper to ensure collection exists."""
        if name not in MOCK_DB:
            MOCK_DB[name] = {}
        return MockCollection(name)


class MockAuth:
    """Mock Firebase Auth for token verification."""
    
    @staticmethod
    def verify_id_token(token: str, clock_skew_seconds: int = 10) -> Dict[str, Any]:
        """
        Parse mock token format: mock-token-{role}-{uid}
        
        Example: "mock-token-admin-001" -> {uid: "001", role: "admin", ...}
        """
        if not token.startswith("mock-token-"):
            raise ValueError("Invalid mock token format. Expected: mock-token-{role}-{uid}")
        
        parts = token.split("-")
        if len(parts) < 4:
            raise ValueError("Invalid mock token format. Expected: mock-token-{role}-{uid}")
        
        role = parts[2]  # "admin", "staff", or "student"
        uid = "-".join(parts[3:])  # Join remaining parts as UID
        
        return {
            "uid": uid,
            "email": f"{role}@test.com",
            "name": f"Mock {role.capitalize()}",
            "role": role,
        }


def _seed_initial_data():
    """Pre-populate mock database with test users."""
    if "users" not in MOCK_DB:
        MOCK_DB["users"] = {}
    
    # Only seed if empty
    if MOCK_DB["users"]:
        return
    
    seed_users = [
        {
            "id": "mock-admin-001",
            "email": "admin@test.com",
            "displayName": "Test Admin",
            "role": "admin",
            "departmentId": None,
            "subjectIds": None,
            "status": "active",
            "password": "Admin123!",
            "createdAt": "2026-01-01T00:00:00.000Z",
            "updatedAt": "2026-01-01T00:00:00.000Z"
        },
        {
            "id": "mock-staff-001",
            "email": "staff@test.com",
            "displayName": "Test Staff",
            "role": "staff",
            "departmentId": "dept-cs-001",
            "subjectIds": ["subject-001"],
            "status": "active",
            "password": "Staff123!",
            "createdAt": "2026-01-01T00:00:00.000Z",
            "updatedAt": "2026-01-01T00:00:00.000Z"
        },
        {
            "id": "mock-student-001",
            "email": "student@test.com",
            "displayName": "Test Student",
            "role": "student",
            "departmentId": "dept-cs-001",
            "subjectIds": None,
            "status": "active",
            "password": "Student123!",
            "createdAt": "2026-01-01T00:00:00.000Z",
            "updatedAt": "2026-01-01T00:00:00.000Z"
        }
    ]
    
    for user in seed_users:
        MOCK_DB["users"][user["id"]] = user
