"""
============================================================================
FILE: test_mock_firestore.py
LOCATION: api/test_mock_firestore.py
============================================================================

PURPOSE:
    Unit tests for the mock Firestore client implementation.
    Validates CRUD operations, querying, and authentication mocking.

ROLE IN PROJECT:
    Testing infrastructure for Firestore-dependent components.
    - Ensures mock Firestore behaves like real Firestore
    - Tests document set/get/update operations
    - Validates query filtering and collection groups
    - Verifies mock authentication token handling

KEY COMPONENTS:
    - test_document_set_and_get: Basic CRUD operations
    - test_document_update: Partial document updates
    - test_query_where_equals: Filtered queries
    - test_collection_group: Subcollection queries
    - test_mock_auth_verify_token: JWT token validation mocking

DEPENDENCIES:
    - External: pytest, json
    - Internal: mock_firestore (MockFirestoreClient, MockAuth)

USAGE:
    Run from project root with pytest:
        pytest api/test_mock_firestore.py -v

    Or run all api tests:
        pytest api/ -v
============================================================================
"""

import json

import pytest

from mock_firestore import MockFirestoreClient, MockAuth


@pytest.fixture
def db(tmp_path):
    db_file = tmp_path / "mock_db.json"
    db_file.write_text(json.dumps({}))
    return MockFirestoreClient(db_file=str(db_file))


def test_document_set_and_get(db):
    doc_ref = db.collection("test_collection").document("test_doc_1")

    test_data = {"name": "Test Document", "value": 42, "active": True}

    doc_ref.set(test_data)
    doc_snapshot = doc_ref.get()

    assert doc_snapshot.exists
    assert doc_snapshot.id == "test_doc_1"
    assert doc_snapshot.to_dict() == test_data
    assert doc_snapshot.get("name") == "Test Document"
    assert doc_snapshot.get("value") == 42


def test_document_update(db):
    doc_ref = db.collection("test_collection").document("test_doc_2")

    doc_ref.set({"name": "Original", "count": 1})
    doc_ref.update({"count": 2, "updated": True})

    doc_snapshot = doc_ref.get()
    assert doc_snapshot.to_dict() == {"name": "Original", "count": 2, "updated": True}


def test_query_where_equals(db):
    users = db.collection("users")
    users.document("user-1").set({"email": "admin@test.com", "role": "admin"})
    users.document("user-2").set({"email": "staff@test.com", "role": "staff"})

    results = list(users.where("role", "==", "admin").stream())
    assert len(results) == 1
    assert results[0].get("email") == "admin@test.com"


def test_collection_group(db):
    subjects = db.collection("departments/dep1/semesters/sem1/subjects")
    subjects.document("subj-1").set({"id": "subj-1", "name": "OS"})
    subjects.document("subj-2").set({"id": "subj-2", "name": "DS"})

    group_results = list(db.collection_group("subjects").stream())
    names = sorted([doc.get("name") for doc in group_results])
    assert names == ["DS", "OS"]


def test_mock_auth_verify_token():
    mock_auth = MockAuth()

    claims = mock_auth.verify_id_token("mock-token-admin-001")
    assert claims["uid"] == "001"
    assert claims["email"] == "test@test.com"

    with pytest.raises(Exception):
        mock_auth.verify_id_token("invalid-token")
