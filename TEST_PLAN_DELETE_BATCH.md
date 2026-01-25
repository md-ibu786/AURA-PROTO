# Test Plan: `/kg/delete-batch` Endpoint with Retry Logic

## Overview
Comprehensive test suite for the Knowledge Graph batch deletion endpoint with Firestore retry logic and orphan entity cleanup.

**Test File**: `tests/test_kg_router_delete.py`
**Lines**: 1,175
**Test Methods**: 30
**Coverage Areas**: 6 test classes

---

## Objective & Behaviors to Test

### Primary Objective
Verify that the `/kg/delete-batch` FastAPI endpoint:
1. Validates request models correctly
2. Deletes documents from Neo4j with proper status checks
3. Handles Firestore updates with exponential backoff retry logic
4. Aggregates orphan cleanup across batch deletions
5. Gracefully handles partial failures and edge cases

### Behavioral Categories

#### 1. Request/Response Model Validation
**Behaviors to Test**:
- BatchDeleteRequest accepts valid file_ids and module_id
- BatchDeleteRequest requires both fields (non-optional)
- Empty file_ids list is accepted (edge case)
- BatchDeleteResponse correctly structures deleted_count, failed[], message

**Test Methods**: 6
- `test_valid_batch_request_creates_model` - Positive test
- `test_batch_request_requires_file_ids` - Negative test (missing field)
- `test_batch_request_requires_module_id` - Negative test (missing field)
- `test_batch_request_accepts_empty_file_ids` - Edge case
- `test_batch_delete_response_creation` - Positive response structure
- `test_batch_delete_response_default_failed_list` - Default handling

---

#### 2. Successful Deletion Flow
**Behaviors to Test**:
- Single document deletion succeeds and returns deleted_count=1
- Multiple documents deletion counts correctly
- Orphan cleanup called with aggregated entity IDs
- Log messages indicate successful completion

**Test Methods**: 2
- `test_delete_single_document_success` - Positive test (single doc)
- `test_delete_multiple_documents_success` - Positive test (multiple docs)

---

#### 3. Partial Failures & Edge Cases
**Behaviors to Test**:
- Some docs fail, others succeed → return count + failed[]
- Non-existent documents skipped and marked failed
- Documents with kg_status != "ready" skipped
- Module_id mismatch detected and document skipped
- Non-ready documents not deleted

**Test Methods**: 4
- `test_partial_failure_some_docs_fail` - Positive test (partial success)
- `test_document_not_found_skipped` - Negative test (not found)
- `test_not_kg_ready_skipped` - Negative test (status check)
- `test_module_id_mismatch_skipped` - Negative test (validation)

---

#### 4. Firestore Retry Logic (Exponential Backoff)
**Behaviors to Test**:
- Success on first attempt → 1 DB call, no retries
- Success on second attempt → 2 DB calls, 1 sleep (0.5s)
- Failure after max retries (3 attempts) → 3 calls, 2 sleeps
- Exponential backoff: 0.5s → 1s → 2s
- Warning logged on each retry
- Critical log on final failure

**Test Methods**: 5
- `test_firestore_update_success_first_attempt` - Positive (1st try)
- `test_firestore_update_success_second_attempt` - Positive (2nd try)
- `test_firestore_update_failure_max_retries` - Negative (all fail)
- `test_firestore_exponential_backoff_timing` - Positive (backoff sequence)
- `test_firestore_update_logs_warning_on_retry` - Positive (logging)

---

#### 5. Batch Orphan Cleanup Flow
**Behaviors to Test**:
- Cleanup called ONCE after all deletions complete
- Entity IDs from all successful deletions aggregated
- Entity IDs deduplicated (set used before cleanup)
- Cleanup skipped if no deletions succeeded
- Cleanup runs even on partial success

**Test Methods**: 4
- `test_orphan_cleanup_runs_once_after_all_deletions` - Positive (single call)
- `test_orphan_cleanup_deduplicates_entity_ids` - Positive (dedup)
- `test_orphan_cleanup_not_called_if_no_deletions` - Positive (skip)
- `test_orphan_cleanup_runs_on_partial_success` - Positive (partial)

---

#### 6. Error Handling
**Behaviors to Test**:
- Firestore note lookup failure doesn't crash endpoint
- Neo4j deletion failure recorded in failed[]
- Firestore update failure after Neo4j success counts as deleted
- GraphManager initialization failure handled gracefully

**Test Methods**: 4
- `test_firestore_note_lookup_failure_skips_doc` - Negative (FS error)
- `test_neo4j_deletion_failure_recorded_in_failed` - Negative (Neo4j error)
- `test_firestore_update_failure_counted_as_deleted` - Negative (FS after Neo4j)
- `test_graph_manager_initialization_failure_handled` - Negative (init error)

---

#### 7. Empty & Edge Case Requests
**Behaviors to Test**:
- Empty file_ids list processed gracefully
- Empty module_id accepted (may not match any docs)
- Very long module_id handled without crashing

**Test Methods**: 3
- `test_empty_file_ids_request` - Edge case (empty list)
- `test_empty_module_id_validation` - Edge case (empty string)
- `test_very_long_module_id` - Edge case (oversized)

---

#### 8. Integration Scenarios
**Behaviors to Test**:
- Full workflow with mixed success/failure outcomes
- 4-scenario combination:
  - doc_001: Ready + module match + Neo4j success = deleted
  - doc_002: Ready + module match + Neo4j fails = failed
  - doc_003: Not ready = skipped (failed)
  - doc_missing: Not found = skipped (failed)

**Test Methods**: 1
- `test_full_workflow_mixed_success_and_failure` - Integration test

---

## Test Structure & Fixtures

### Core Fixtures (8 total)

| Fixture | Purpose | Returns |
|---------|---------|---------|
| `mock_firestore_db` | Mocked Firestore with collection_group | MagicMock |
| `mock_graph_manager` | Mocked GraphManager with async methods | MagicMock |
| `sample_batch_request` | Valid batch request with 3 file_ids | BatchDeleteRequest |
| `sample_notes_data` | 4 sample notes with various statuses | dict |
| `test_client` | FastAPI TestClient for HTTP requests | TestClient |
| `valid_batch_request_data` | Valid JSON request | dict |
| `invalid_empty_file_ids` | JSON with empty file_ids | dict |
| `invalid_missing_module_id` | JSON missing module_id | dict |

### Mock Objects
- **Firestore**: collection_group().stream() returns mock documents
- **Neo4j**: GraphManager.delete_document returns (bool, List[str])
- **Firestore Retry**: asyncio.sleep mocked to avoid delays

---

## Expected Results Summary

| Test Category | Count | Success | Notes |
|---------------|-------|---------|-------|
| Request Validation | 6 | All pass | Edge cases included |
| Successful Deletion | 2 | All pass | Single & multiple docs |
| Partial Failures | 4 | All pass | Various failure modes |
| Firestore Retry | 5 | All pass | Exponential backoff verified |
| Orphan Cleanup | 4 | All pass | Deduplication tested |
| Error Handling | 4 | All pass | Graceful degradation |
| Edge Cases | 3 | All pass | Empty/long payloads |
| Integration | 1 | All pass | Mixed scenario |
| **TOTAL** | **30** | **All pass** | Comprehensive coverage |

---

## Test Execution

### Run All Tests
```bash
cd AURA-NOTES-MANAGER
pytest tests/test_kg_router_delete.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_kg_router_delete.py::TestBatchDeleteRequestValidation -v
pytest tests/test_kg_router_delete.py::TestSuccessfulDeletion -v
pytest tests/test_kg_router_delete.py::TestFirestoreRetryLogic -v
```

### Run Specific Test
```bash
pytest tests/test_kg_router_delete.py::TestFirestoreRetryLogic::test_firestore_exponential_backoff_timing -v
```

### With Coverage
```bash
pytest tests/test_kg_router_delete.py --cov=api.kg.router --cov-report=term-missing
```

---

## Key Testing Patterns Used

### 1. Arrange-Act-Assert (AAA)
Every test follows:
```python
# Arrange: Setup mocks and fixtures
# Act: Execute the endpoint/method
# Assert: Verify expected outcomes
```

### 2. Async/Await Compatibility
- AsyncMock for async methods
- @pytest.mark.asyncio decorator for async tests
- Mocked asyncio.sleep to avoid delays

### 3. Deterministic Tests
- No real network calls
- No file I/O
- No time dependencies
- All externals mocked

### 4. Dual Test Coverage
Each major behavior has:
- **Positive test**: Verifies correct functionality
- **Negative test**: Verifies failure/error handling

---

## Dependencies
