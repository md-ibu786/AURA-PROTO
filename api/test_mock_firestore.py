# test_mock_firestore.py
# Unit tests for mock Firestore implementation

# Comprehensive pytest suite covering CRUD operations, query filtering,
# collection streaming, seed data initialization, and mock token parsing.

# @see: api/mock_firestore.py - Implementation under test
# @note: Tests must be run from api/ directory: cd api && python -m pytest test_mock_firestore.py -v

import pytest
from mock_firestore import (
    MockFirestoreClient,
    MockAuth,
    MOCK_DB,
)


@pytest.fixture
def db():
    """Fresh MockFirestoreClient instance for each test."""
    # Clear MOCK_DB before each test except seed data
    MOCK_DB.clear()
    return MockFirestoreClient()


def test_document_set_and_get(db):
    """Test setting a document and retrieving it."""
    doc_ref = db.collection("test_collection").document("test_doc_1")
    
    test_data = {
        "name": "Test Document",
        "value": 42,
        "active": True
    }
    
    # Set document
    doc_ref.set(test_data)
    
    # Get document
    doc_snapshot = doc_ref.get()
    
    # Verify
    assert doc_snapshot.exists
    assert doc_snapshot.id == "test_doc_1"
    assert doc_snapshot.to_dict() == test_data
    assert doc_snapshot.get("name") == "Test Document"
    assert doc_snapshot.get("value") == 42


def test_document_update(db):
    """Test updating an existing document."""
    doc_ref = db.collection("test_collection").document("test_doc_2")
    
    # Initial data
    doc_ref.set({"name": "Original", "count": 1})
    
    # Update with merge
    doc_ref.update({"count": 2, "updated": True})
    
    # Verify merge
    doc_snapshot = doc_ref.get()
    assert doc_snapshot.to_dict() == {
        "name": "Original",
        "count": 2,
        "updated": True
    }


def test_document_delete(db):
    """Test deleting a document."""
    doc_ref = db.collection("test_collection").document("test_doc_3")
    
    # Create document
    doc_ref.set({"name": "To Delete"})
    assert doc_ref.get().exists
    
    # Delete document
    doc_ref.delete()
    
    # Verify deleted
    assert not doc_ref.get().exists
    assert doc_ref.get().to_dict() is None


def test_query_where_equals(db):
    """Test query filtering with == operator."""
    collection = db.collection("users")
    
    # Seed data is automatically loaded
    # Query for admin role
    results = list(collection.where("role", "==", "admin").stream())
    
    assert len(results) == 1
    assert results[0].get("role") == "admin"
    assert results[0].get("email") == "admin@test.com"


def test_query_where_in(db):
    """Test query filtering with 'in' operator."""
    collection = db.collection("users")
    
    # Query for staff or student roles
    results = list(collection.where("role", "in", ["staff", "student"]).stream())
    
    assert len(results) == 2
    roles = {doc.get("role") for doc in results}
    assert roles == {"staff", "student"}


def test_collection_stream(db):
    """Test streaming all documents in a collection."""
    collection = db.collection("users")
    
    # Stream all users (seed data)
    all_users = list(collection.stream())
    
    assert len(all_users) == 3
    emails = {doc.get("email") for doc in all_users}
    assert emails == {"admin@test.com", "staff@test.com", "student@test.com"}


def test_seed_users_exist(db):
    """Test that 3 seed users are created automatically."""
    users_collection = db.collection("users")
    all_users = list(users_collection.stream())
    
    # Verify count
    assert len(all_users) == 3
    
    # Verify roles present
    roles = {user.get("role") for user in all_users}
    assert roles == {"admin", "staff", "student"}
    
    # Verify admin user details
    admin_users = list(users_collection.where("role", "==", "admin").stream())
    assert len(admin_users) == 1
    admin = admin_users[0]
    assert admin.get("email") == "admin@test.com"
    assert admin.get("displayName") == "Test Admin"
    assert admin.get("departmentId") is None
    assert admin.get("status") == "active"


def test_mock_auth_verify_token():
    """Test MockAuth token parsing."""
    # Test valid admin token
    admin_token = "mock-token-admin-001"
    claims = MockAuth.verify_id_token(admin_token)
    
    assert claims["uid"] == "001"
    assert claims["role"] == "admin"
    assert claims["email"] == "admin@test.com"
    assert claims["name"] == "Mock Admin"
    
    # Test valid staff token
    staff_token = "mock-token-staff-abc-123"
    claims = MockAuth.verify_id_token(staff_token)
    
    assert claims["uid"] == "abc-123"
    assert claims["role"] == "staff"
    assert claims["email"] == "staff@test.com"
    
    # Test invalid token format
    with pytest.raises(ValueError, match="Invalid mock token format"):
        MockAuth.verify_id_token("invalid-token")
    
    with pytest.raises(ValueError, match="Invalid mock token format"):
        MockAuth.verify_id_token("mock-token-admin")  # Missing UID
