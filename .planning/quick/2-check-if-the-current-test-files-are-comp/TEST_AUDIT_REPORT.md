# Test Audit Report

**Project:** AURA-NOTES-MANAGER & AURA-CHAT
**Date:** 2026-03-08
**Audited By:** Claude Code (Quick Task 2)

---

## Executive Summary

| Project | Test Suite | Files | Passed | Failed | Skipped | Status |
|---------|-----------|-------|--------|--------|---------|--------|
| AURA-NOTES-MANAGER | Frontend Unit (Vitest) | 15 | 176 | 0 | 73 | Partial (1 file needs emulator) |
| AURA-NOTES-MANAGER | API Tests (pytest) | 1 | 0 | 0 | - | Broken (import error) |
| AURA-NOTES-MANAGER | E2E (Playwright) | 6 | - | - | - | Not executed |
| AURA-CHAT | Client Unit (Vitest) | 17 | 181 | 46 | 0 | Failing (hierarchy-related) |
| AURA-CHAT | Python Unit (pytest) | 9 | 115 | 3 | 0 | Mostly Passing |
| AURA-CHAT | E2E (Playwright) | 8 | - | - | - | Not executed |

**Overall Status:** 307 tests passing, 49 tests failing, 73 skipped

---

## Test File Inventory

### AURA-NOTES-MANAGER

#### Frontend Unit Tests (Vitest) - 15 files

| File | Tests | Framework | Status |
|------|-------|-----------|--------|
| `src/api/client.test.ts` | 2 | Vitest | Passing |
| `src/components/explorer/__tests__/ListView.test.tsx` | 16 | Vitest | Passing |
| `src/components/explorer/__tests__/SelectionOverlay.test.tsx` | 4 | Vitest | Passing |
| `src/components/ui/WarningDialog.test.tsx` | 3 | Vitest | Passing |
| `src/features/kg/components/KGStatusBadge.test.tsx` | 14 | Vitest | Passing |
| `src/features/kg/components/ProcessDialog.test.tsx` | 11 | Vitest | Passing |
| `src/features/kg/components/ProcessingQueue.test.tsx` | 14 | Vitest | Passing |
| `src/features/kg/components/__tests__/FileSelectionBar.test.tsx` | 8 | Vitest | Passing |
| `src/features/kg/hooks/useKGProcessing.test.tsx` | 18 | Vitest | Passing |
| `src/integration/GridViewWarning.test.tsx` | 2 | Vitest | Passing |
| `src/integration/StateSync.test.tsx` | 3 | Vitest | Passing |
| `src/integration/WarningDialogFlow.test.tsx` | 1 | Vitest | Passing |
| `src/pages/ExplorerPage.test.tsx` | 18 | Vitest | Passing |
| `src/stores/useExplorerStore.test.ts` | 62 | Vitest | Passing |
| `src/tests/firestore.rules.test.ts` | 73 | Jest (Vitest) | Skipped (needs emulator) |

#### API Tests (pytest) - 5 files

| File | Tests | Framework | Status |
|------|-------|-----------|--------|
| `api/test_celery_tasks.py` | - | pytest | Unknown |
| `api/test_celery_tasks_e2e.py` | - | pytest | Unknown |
| `api/test_kg_processor.py` | - | pytest | Unknown |
| `api/test_mock_firestore.py` | - | pytest | Unknown |
| `api/tests/test_rbac.py` | - | pytest | Broken (ModuleNotFoundError) |

#### E2E Tests (Playwright) - 6 files

| File | Framework | Status |
|------|-----------|--------|
| `e2e/tests/api.spec.ts` | Playwright | Not executed |
| `e2e/tests/audio.spec.ts` | Playwright | Not executed |
| `e2e/tests/explorer.spec.ts` | Playwright | Not executed |
| `frontend/e2e/auth.spec.ts` | Playwright | Not executed |
| `frontend/e2e/explorer.spec.ts` | Playwright | Not executed |
| `frontend/e2e/health.spec.ts` | Playwright | Not executed |
| `frontend/e2e/kg-processing.spec.ts` | Playwright | Not executed |
| `frontend/e2e/rbac.spec.ts` | Playwright | Not executed |

### AURA-CHAT

#### Client Unit Tests (Vitest) - 17 files

| File | Tests | Status |
|------|-------|--------|
| `src/components/CitationPanel.test.tsx` | 9 | 1 failed |
| `src/components/ErrorBoundary.test.tsx` | 6 | Passing (stderr noise) |
| `src/components/MessageBubble.test.tsx` | 8 | Passing |
| `src/features/chat/ChatPage.test.tsx` | 12 | 12 failed |
| `src/features/chat/components/CreateSessionModal.test.tsx` | 10 | 10 failed |
| `src/features/chat/components/InputArea.test.tsx` | 7 | 7 failed |
| `src/features/chat/hooks/useChat.stream.test.ts` | 4 | Passing |
| `src/features/chat/hooks/useChat.test.tsx` | 38 | Passing |
| `src/features/graph/GraphPage.test.tsx` | 9 | 9 failed |
| `src/features/modules/hooks/useDocuments.test.ts` | 2 | Passing |
| `src/features/modules/hooks/useDocuments.test.tsx` | 5 | 5 failed |
| `src/features/modules/hooks/useModule.test.ts` | 7 | Passing |
| `src/features/modules/hooks/useModule.test.tsx` | 6 | 2 failed |
| `src/features/settings/SettingsPage.test.tsx` | 6 | Passing |
| `src/features/study-sessions/hooks/useStudySession.test.tsx` | 14 | Passing |
| `src/hooks/useGraphQuery.test.tsx` | 10 | Passing |
| `src/hooks/useTypewriter.test.ts` | 5 | Passing |
| `src/integration.test.tsx` | 8 | Passing |
| `src/simple.test.ts` | 1 | Passing |

#### Python Unit Tests (pytest) - 9 files, 118 tests

| File | Tests | Status |
|------|-------|--------|
| `tests/unit/test_dependencies_degraded_mode.py` | 4 | Passing |
| `tests/unit/test_embeddings_location_resolution.py` | 4 | Passing |
| `tests/unit/test_firestore_client_credentials.py` | 2 | 2 failed |
| `tests/unit/test_messages.py` | 14 | Passing |
| `tests/unit/test_module_filtering.py` | 16 | Passing |
| `tests/unit/test_rag_engine.py` | 52 | Passing |
| `tests/unit/test_session_crud.py` | 24 | Passing |
| `tests/unit/test_vertex_ai_location_routing.py` | 4 | 1 failed |

#### E2E Tests (Playwright) - 8 files

| File | Framework | Status |
|------|-----------|--------|
| `client/e2e/chat.spec.ts` | Playwright | Not executed |
| `client/e2e/documents.spec.ts` | Playwright | Not executed |
| `client/e2e/graph.spec.ts` | Playwright | Not executed |
| `client/e2e/health.spec.ts` | Playwright | Not executed |
| `client/e2e/mobile.spec.ts` | Playwright | Not executed |
| `client/e2e/notes.spec.ts` | Playwright | Not executed |
| `client/e2e/performance.spec.ts` | Playwright | Not executed |

---

## Failure Categorization

### Category 1: Infrastructure Issues (Environment Setup)

#### 1.1 Firebase Emulator Required
- **Test File:** `AURA-NOTES-MANAGER/frontend/src/tests/firestore.rules.test.ts`
- **Error:** `The host and port of the firestore emulator must be specified`
- **Fix Type:** Environment Setup
- **Action Required:** Run tests with `firebase emulators:exec` or configure emulator host/port

#### 1.2 Missing Test Credentials File
- **Test File:** `AURA-CHAT/tests/unit/test_firestore_client_credentials.py`
- **Tests Affected:** 2 tests
- **Error:** `FileNotFoundError: [Errno 2] No such file or directory: 'fake-firebase-creds.json'`
- **Fix Type:** Test Data Setup
- **Action Required:** Create `tests/unit/fake-firebase-creds.json` mock file

#### 1.3 TLS Certificate Bundle Issue
- **Test File:** `AURA-CHAT/tests/unit/test_firestore_client_credentials.py`
- **Error:** `Could not find a suitable TLS CA certificate bundle, invalid path`
- **Fix Type:** Environment/Dependency
- **Action Required:** Fix certifi package installation or path

#### 1.4 Module Import Error (AURA-NOTES-MANAGER API)
- **Test File:** `AURA-NOTES-MANAGER/api/tests/test_rbac.py`
- **Error:** `ModuleNotFoundError: No module named 'api'`
- **Fix Type:** Python Path Configuration
- **Action Required:** Fix PYTHONPATH or use relative imports

### Category 2: Code Changes (Implementation Drift)

#### 2.1 Hierarchy-Related Test Failures (AURA-CHAT Client)
- **Test Files:**
  - `ChatPage.test.tsx` (12 failed)
  - `CreateSessionModal.test.tsx` (10 failed)
  - `InputArea.test.tsx` (7 failed)
  - `GraphPage.test.tsx` (9 failed)
  - `useDocuments.test.tsx` (5 failed)
  - `useModule.test.tsx` (2 failed)
  - `CitationPanel.test.tsx` (1 failed)
- **Common Error:** `Unable to find role="button" with name /select department/i`
- **Root Cause:** Recent architectural changes to 4-level hierarchy (Dept → Semester → Subject → Module) not reflected in tests
- **Fix Type:** Test Update Required
- **Action Required:** Update test mocks and assertions to match new hierarchy UI

#### 2.2 Vertex AI Location Routing
- **Test File:** `AURA-CHAT/tests/unit/test_vertex_ai_location_routing.py`
- **Test:** `test_non_gemini3_model_uses_vertex_region`
- **Fix Type:** Implementation or Test Update
- **Action Required:** Verify location routing logic matches test expectations

### Category 3: Test Issues (Flaky/Incorrect Tests)

#### 3.1 Error Boundary Test Noise
- **Test File:** `AURA-CHAT/client/src/components/ErrorBoundary.test.tsx`
- **Issue:** Tests pass but produce stderr noise from React error logging
- **Status:** Not a failure, but creates noise in output
- **Fix Type:** Optional cleanup

---

## Coverage Gap Analysis

### Skipped Tests
- **AURA-NOTES-MANAGER:** 73 tests skipped in `firestore.rules.test.ts` (requires emulator)

### Missing Test Coverage Areas

1. **E2E Tests:** Not executed during audit - coverage unknown
2. **Integration Tests:** Limited coverage for full stack scenarios
3. **Backend API Tests (AURA-NOTES-MANAGER):** Import errors prevent execution
4. **Performance Tests:** Exist but not executed
5. **Security Tests:** Exist but not executed

### Recent Architectural Changes Not Fully Tested

1. **Thinking Mode Implementation** (January 2026)
   - Dual SDK approach (Vertex AI + Google Generative AI)
   - Tests exist but may not cover all edge cases

2. **Session-Based Chat Architecture** (January 2026)
   - Persistent study sessions with Neo4j
   - Tests passing but E2E coverage unknown

3. **Module Hierarchy Navigation** (January 2026)
   - 4-level hierarchy causing test failures
   - Tests need updates to match new UI

4. **Feature-Based Frontend Organization** (January 2026)
   - Both apps restructured
   - Some test imports may be outdated

---

## Recommendations

### Priority 1: Critical (Blocking)

1. **Fix AURA-CHAT Client Hierarchy Tests**
   - Update 46 failing tests to match new hierarchy UI
   - Update test mocks for department/semester/subject/module selection
   - Estimated effort: 4-6 hours

2. **Fix Python Test Credentials**
   - Create `fake-firebase-creds.json` mock file in `AURA-CHAT/tests/unit/`
   - Fix certifi TLS bundle path issue
   - Estimated effort: 1 hour

### Priority 2: High (Important)

3. **Fix AURA-NOTES-MANAGER API Tests**
   - Fix module import error in `test_rbac.py`
   - Run and validate all API tests
   - Estimated effort: 2 hours

4. **Document Firestore Rules Test Requirements**
   - Add README for running Firestore rules tests with emulator
   - Consider CI/CD integration for emulator setup
   - Estimated effort: 1 hour

### Priority 3: Medium (Nice to Have)

5. **Clean Up Error Boundary Test Noise**
   - Suppress expected React error logging in tests
   - Estimated effort: 30 minutes

6. **Run E2E Test Suite**
   - Execute full E2E test suite for both projects
   - Document any additional failures
   - Estimated effort: 2-3 hours

7. **Add Missing Coverage**
   - Identify gaps in recent architectural changes
   - Add tests for thinking mode edge cases
   - Estimated effort: 4-6 hours

---

## Detailed Failure Log

### AURA-CHAT Client Test Failures

```
Test Files: 6 failed | 11 passed (17)
Tests: 46 failed | 181 passed (227)

Failed Files:
1. src/features/chat/ChatPage.test.tsx (12 tests)
   - Hierarchy selection not found in DOM

2. src/features/chat/components/CreateSessionModal.test.tsx (10 tests)
   - Department/semester/subject selection failing

3. src/features/chat/components/InputArea.test.tsx (7 tests)
   - Module-aware input tests failing

4. src/features/graph/GraphPage.test.tsx (9 tests)
   - Graph visualization with hierarchy failing

5. src/features/modules/hooks/useDocuments.test.tsx (5 tests)
   - Document hierarchy tests failing

6. src/features/modules/hooks/useModule.test.tsx (2 tests)
   - Module selection tests failing

7. src/components/CitationPanel.test.tsx (1 test)
   - Citation with module context failing
```

### AURA-CHAT Python Test Failures

```
test_firestore_client_credentials.py::test_firebase_credentials_resolve_repo_relative_from_server_cwd
  FileNotFoundError: fake-firebase-creds.json not found

test_firestore_client_credentials.py::test_default_credentials_resolve_repo_relative_from_server_cwd
  Assertion error: client mismatch + TLS cert bundle issue

test_vertex_ai_location_routing.py::test_non_gemini3_model_uses_vertex_region
  Location routing logic mismatch
```

---

## Appendix: Test Commands Reference

### AURA-NOTES-MANAGER

```bash
# Frontend Unit Tests
cd AURA-NOTES-MANAGER/frontend
npm test -- --run

# API Tests (after fixing imports)
cd AURA-NOTES-MANAGER/api
../.venv/Scripts/python -m pytest tests/ -v

# E2E Tests
cd AURA-NOTES-MANAGER
npm run test:e2e

# Firestore Rules Tests (requires emulator)
firebase emulators:exec --only firestore 'npm test -- src/tests/firestore.rules.test.ts'
```

### AURA-CHAT

```bash
# Client Unit Tests
cd AURA-CHAT/client
npm test -- --run

# Python Unit Tests
cd AURA-CHAT
../.venv/Scripts/python -m pytest tests/unit/ -v

# E2E Tests
cd AURA-CHAT/client
npm run test:e2e
```

---

## Conclusion

The test suites show good overall coverage with **307 passing tests**, but **49 tests are failing** primarily due to:

1. **Recent UI changes** (hierarchy navigation) not reflected in tests
2. **Missing test infrastructure** (emulator, mock credentials)
3. **Environment configuration issues** (Python paths, TLS certs)

The majority of failures (46/49) are in AURA-CHAT client tests related to the new 4-level hierarchy UI. Fixing these tests should be the top priority to ensure test suite reliability.

**Estimated Total Effort to Fix All Issues:** 12-16 hours
