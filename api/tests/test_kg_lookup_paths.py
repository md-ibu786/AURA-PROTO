"""
============================================================================
FILE: test_kg_lookup_paths.py
LOCATION: api/tests/test_kg_lookup_paths.py
============================================================================

PURPOSE:
    Regression tests proving KG request paths avoid full-note-collection scans.

ROLE IN PROJECT:
    Ensures that get_document_kg_status and get_processing_queue use bounded
    Firestore queries instead of streaming all notes and filtering in Python.

DEPENDENCIES:
    - External: pytest
    - Internal: api.kg.router, api.tasks.document_processing_tasks

USAGE:
    pytest api/tests/test_kg_lookup_paths.py -v
============================================================================
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime

# Import the functions under test
from api.kg.router import get_document_kg_status, get_processing_queue
from api.tasks.document_processing_tasks import _find_note_by_id


# =============================================================================
# TEST 1: get_document_kg_status avoids full scan
# =============================================================================


def test_get_document_kg_status_avoids_full_scan():
    """
    Test that get_document_kg_status uses bounded lookup by id field
    and never falls back to collection_group('notes').stream() without
    an equality filter.

    Expected behavior:
    - Uses FieldFilter("id", "==", document_id) query
    - Uses limit(1)
    - Does NOT use __name__ range query with Python-side filtering
    - Does NOT fall back to stream-all-notes iteration
    """
    mock_doc = MagicMock()
    mock_doc.id = "doc123"
    mock_doc.to_dict.return_value = {
        "id": "doc123",
        "module_id": "mod1",
        "file_name": "test.pdf",
        "kg_status": "pending",
    }
    mock_doc.reference.path = (
        "departments/dept1/semesters/sem1/subjects/subj1/modules/mod1/notes/doc123"
    )

    mock_stream_result = [mock_doc]

    # Track all stream() calls to detect full scans
    stream_calls = []

    class MockCollectionGroup:
        def __init__(self, collection_name):
            self.collection_name = collection_name
            self._filters = []

        def where(self, *args, **kwargs):
            # Capture filter info
            self._filters.append(("where", args, kwargs))
            return self

        def limit(self, n):
            return self

        def stream(self):
            stream_calls.append(self._filters)
            return iter(mock_stream_result)

    mock_db = MagicMock()

    def make_collection_group(name):
        return MockCollectionGroup(name)

    mock_db.collection_group = make_collection_group

    with patch("api.kg.router.db", mock_db):
        result = get_document_kg_status("doc123")

    # Verify we got a result
    assert result.document_id == "doc123"
    assert result.kg_status.value == "pending"

    # CRITICAL: Verify there was exactly ONE stream() call (the bounded one)
    # and it used an equality filter on the 'id' field
    assert len(stream_calls) == 1, (
        f"Expected exactly 1 stream() call for bounded lookup, got {len(stream_calls)}. "
        f"Multiple stream calls indicate a fallback pattern."
    )

    # Verify the query used an equality filter (FieldFilter("id", "==", ...))
    call_filters = stream_calls[0]
    has_equality_filter = any("id" in str(f) and "==" in str(f) for f in call_filters)
    assert has_equality_filter, (
        f"Query did not use equality filter on 'id' field. Filters used: {call_filters}"
    )


def test_get_document_kg_status_404_when_not_found():
    """
    Test that get_document_kg_status returns 404 when no document matches.
    Should use bounded query, not stream-all.
    """
    mock_db = MagicMock()

    class MockCollectionGroup:
        def __init__(self, collection_name):
            self.collection_name = collection_name

        def where(self, *args, **kwargs):
            return self

        def limit(self, n):
            return self

        def stream(self):
            # Return empty iterator - document not found
            return iter([])

    mock_db.collection_group = lambda name: MockCollectionGroup(name)

    with patch("api.kg.router.db", mock_db):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            get_document_kg_status("nonexistent_doc")
        assert exc_info.value.status_code == 404


# =============================================================================
# TEST 2: get_processing_queue uses Firestore kg_status filter
# =============================================================================


def test_get_processing_queue_filters_in_firestore():
    """
    Test that get_processing_queue queries only notes with kg_status == 'processing'
    at the Firestore level, not by streaming all notes and filtering in Python.

    Expected behavior:
    - Uses FieldFilter("kg_status", "==", "processing") in Firestore query
    - Does NOT stream all notes and filter in Python
    - Maps returned docs to ProcessingQueueItem
    """
    mock_doc = MagicMock()
    mock_doc.id = "doc123"
    mock_doc.to_dict.return_value = {
        "id": "doc123",
        "module_id": "mod1",
        "file_name": "test.pdf",
        "kg_status": "processing",
        "kg_progress": 50,
        "kg_step": "chunking",
        "kg_started_at": datetime.utcnow(),
    }
    mock_doc.reference.path = (
        "departments/dept1/semesters/sem1/subjects/subj1/modules/mod1/notes/doc123"
    )

    mock_stream_result = [mock_doc]

    # Track stream calls
    stream_calls = []

    class MockCollectionGroup:
        def __init__(self, collection_name):
            self.collection_name = collection_name
            self._filters = []

        def where(self, *args, **kwargs):
            self._filters.append(("where", args, kwargs))
            return self

        def limit(self, n):
            return self

        def stream(self):
            stream_calls.append(self._filters)
            return iter(mock_stream_result)

    mock_db = MagicMock()
    mock_db.collection_group = lambda name: MockCollectionGroup(name)

    with patch("api.kg.router.db", mock_db):
        result = get_processing_queue()

    # Verify we got results
    assert len(result) == 1
    assert result[0].document_id == "doc123"
    assert result[0].status.value == "processing"

    # CRITICAL: Verify stream was called with kg_status equality filter
    assert len(stream_calls) == 1, (
        f"Expected exactly 1 stream() call, got {len(stream_calls)}"
    )

    call_filters = stream_calls[0]
    has_kg_status_filter = any(
        "kg_status" in str(f) and "processing" in str(f) for f in call_filters
    )
    assert has_kg_status_filter, (
        f"Query did not filter by kg_status == 'processing' at Firestore level. "
        f"Filters used: {call_filters}"
    )


def test_get_processing_queue_returns_empty_on_error():
    """
    Test that get_processing_queue returns empty list gracefully on error
    without falling back to a full scan.
    """
    mock_db = MagicMock()

    class MockCollectionGroup:
        def where(self, *args, **kwargs):
            return self

        def stream(self):
            raise Exception("Firestore index error")

    mock_db.collection_group = lambda name: MockCollectionGroup()

    with patch("api.kg.router.db", mock_db):
        result = get_processing_queue()

    # Should return empty list, not crash
    assert result == []


# =============================================================================
# TEST 3: _find_note_by_id uses bounded lookup
# =============================================================================


def test_find_note_by_id_with_module_id():
    """
    Test that _find_note_by_id prefers scoped module lookup when module_id
    is provided.
    """
    mock_note_doc = MagicMock()
    mock_note_doc.reference.path = (
        "departments/dept1/semesters/sem1/subjects/subj1/modules/mod1/notes/doc123"
    )
    mock_note_doc.exists = True

    mock_module_doc = MagicMock()
    mock_module_doc.reference.collection.return_value.document.return_value.get.return_value = mock_note_doc

    mock_db = MagicMock()

    class MockCollectionGroup:
        def __init__(self, name):
            self.name = name
            self._filters = []

        def where(self, *args, **kwargs):
            self._filters.append(("where", args, kwargs))
            return self

        def limit(self, n):
            return self

        def stream(self):
            if self.name == "modules":
                return iter([mock_module_doc])
            return iter([])

    mock_db.collection_group = lambda name: MockCollectionGroup(name)

    with patch("api.tasks.document_processing_tasks.db", mock_db):
        result = _find_note_by_id("doc123", module_id="mod1")

    assert result is not None
    mock_module_doc.reference.collection.assert_called()


def test_find_note_by_id_without_module_id():
    """
    Test that _find_note_by_id uses stored id equality query when module_id
    is not provided.
    """
    mock_doc = MagicMock()
    mock_doc.reference.path = (
        "departments/dept1/semesters/sem1/subjects/subj1/modules/mod1/notes/doc123"
    )

    stream_calls = []

    class MockCollectionGroup:
        def __init__(self, name):
            self.name = name
            self._filters = []

        def where(self, *args, **kwargs):
            self._filters.append(("where", args, kwargs))
            return self

        def limit(self, n):
            return self

        def stream(self):
            stream_calls.append(self._filters)
            return iter([mock_doc])

    mock_db = MagicMock()
    mock_db.collection_group = lambda name: MockCollectionGroup(name)

    with patch("api.tasks.document_processing_tasks.db", mock_db):
        result = _find_note_by_id("doc123", module_id=None)

    assert result is not None

    # Verify equality filter on 'id' field
    assert len(stream_calls) == 1
    call_filters = stream_calls[0]
    has_id_filter = any("id" in str(f) and "==" in str(f) for f in call_filters)
    assert has_id_filter, f"Expected id equality filter, got: {call_filters}"


def test_find_note_by_id_returns_none_when_not_found():
    """
    Test that _find_note_by_id returns None (not an exception) when
    document is not found.
    """
    mock_db = MagicMock()

    class MockCollectionGroup:
        def where(self, *args, **kwargs):
            return self

        def limit(self, n):
            return self

        def stream(self):
            return iter([])

    mock_db.collection_group = lambda name: MockCollectionGroup(name)

    with patch("api.tasks.document_processing_tasks.db", mock_db):
        result = _find_note_by_id("nonexistent", module_id=None)

    assert result is None


# =============================================================================
# TEST 4: No stream-all fallback in error paths
# =============================================================================


def test_no_stream_all_fallback_in_get_document_kg_status():
    """
    Verify that get_document_kg_status does NOT call collection_group('notes').stream()
    without an equality filter anywhere in its code path.

    This test searches the source for problematic patterns.
    """
    import inspect
    from api.kg import router

    source = inspect.getsource(router.get_document_kg_status)

    # The function should NOT have a pattern like:
    # collection_group("notes").stream() followed by Python filtering
    # or a fallback iteration over all notes

    # Check that there's no second .stream() call without a filter
    lines = source.split("\n")
    stream_count = sum(1 for line in lines if ".stream()" in line)

    # Should have at most 1 stream() call (the bounded one)
    assert stream_count <= 1, (
        f"get_document_kg_status has {stream_count} .stream() calls. "
        "Expected at most 1 (the bounded query). "
        "Multiple stream() calls indicate a fallback pattern."
    )


def test_no_stream_all_fallback_in_get_processing_queue():
    """
    Verify that get_processing_queue does NOT iterate all notes.
    """
    import inspect
    from api.kg import router

    source = inspect.getsource(router.get_processing_queue)

    lines = source.split("\n")

    # Should NOT have a pattern of streaming all then filtering in Python
    has_full_scan = False
    for i, line in enumerate(lines):
        if ".stream()" in line:
            # Check if next few lines have Python filtering
            subsequent = "\n".join(lines[i : i + 5])
            if "for " in subsequent and "kg_status" in subsequent:
                # This is the bad pattern: stream all + Python filter
                has_full_scan = True
                break

    assert not has_full_scan, (
        "get_processing_queue appears to stream all notes and filter in Python. "
        "Should use Firestore-level filtering instead."
    )
