import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.main import app

client = TestClient(app)

@patch("hierarchy_crud.db")
def test_create_duplicate_department_returns_409(mock_db):
    """
    Test that creating a department with a name that already exists
    returns a 409 Conflict status code.
    """
    mock_collection = MagicMock()
    mock_db.collection.return_value = mock_collection
    
    mock_query_where = MagicMock()
    mock_collection.where.return_value = mock_query_where
    
    mock_query_limit = MagicMock()
    mock_query_where.limit.return_value = mock_query_limit
    
    # Simulate existing document
    mock_doc = MagicMock()
    mock_doc.to_dict.return_value = {"name": "Existing Dept", "code": "ED01"}
    
    # stream() returns list with 1 item
    mock_query_limit.stream.return_value = [mock_doc]

    payload = {"name": "Existing Dept", "code": "NEWCODE"}
    response = client.post("/api/departments", json=payload)
    
    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "DUPLICATE_NAME"
    assert "already exists" in response.json()["detail"]["message"]

@patch("hierarchy_crud.db")
def test_create_unique_department_succeeds(mock_db):
    """Test that unique names are allowed."""
    mock_collection = MagicMock()
    mock_db.collection.return_value = mock_collection
    
    mock_query_where = MagicMock()
    mock_collection.where.return_value = mock_query_where
    
    mock_query_limit = MagicMock()
    mock_query_where.limit.return_value = mock_query_limit
    
    # stream() returns empty list
    mock_query_limit.stream.return_value = []
    
    # Mock document creation
    mock_new_ref = MagicMock()
    mock_new_ref.id = "new-id-123"
    mock_collection.document.return_value = mock_new_ref

    payload = {"name": "New Unique Dept", "code": "ND01"}
    response = client.post("/api/departments", json=payload)
    
    # Debug info
    if response.status_code != 200:
        print(response.json())
        
    assert response.status_code == 200
    assert response.json()["department"]["name"] == "New Unique Dept"