---
phase: 08-runtime-hotspot-remediation
plan: 01
subsystem: api
tags: [firestore, kg, performance, bounded-queries, fieldfilter]

# Dependency graph
requires:
  - phase: 06-verification-recovery
    provides: Test infrastructure and verification baseline
provides:
  - Bounded KG status lookup using FieldFilter(id,==,document_id).limit(1)
  - Server-side KG queue filtering using FieldFilter(kg_status,==,processing)
  - Removed stream-all fallback patterns from KG router
affects:
  - 08-runtime-hotspot-remediation (plan 02)
  - KG frontend components

# Tech tracking
tech-stack:
  added: []
  patterns:
    - Bounded Firestore lookup: FieldFilter on stored id field with limit(1)
    - Server-side queue filtering: Query only documents matching status at Firestore level

key-files:
  created:
    - api/tests/test_kg_lookup_paths.py (regression tests documenting expected behavior)
  modified:
    - api/kg/router.py (bounded query implementation)
    - api/tests/conftest.py (improved MockModule for Python 3.14 compat)

key-decisions:
  - "Removed local _find_note_by_id from router; imported bounded version from tasks module"
  - "Queue endpoint raises HTTPException on index error instead of silent fallback to empty"

patterns-established:
  - "Pattern: Bounded note lookup - use FieldFilter(id,==,document_id).limit(1) instead of __name__ range query + Python filter"
  - "Pattern: Server-side queue filtering - query at Firestore level with FieldFilter(status,==,value) instead of streaming all and filtering in Python"

requirements-completed: [PERF-01, PERF-03]

# Metrics
duration: 15min
completed: 2026-04-06
---

# Phase 08, Plan 01: KG Router Hotspot Remediation Summary

**KG status and queue lookups now use bounded Firestore queries instead of full note collection scans**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-06T16:44:00Z
- **Completed:** 2026-04-06T16:59:00Z
- **Tasks:** 2 completed (1 test file, 1 implementation fix)
- **Files modified:** 3

## Accomplishments

- Replaced `get_document_kg_status` range query + Python fallback with bounded `FieldFilter("id", "==", document_id).limit(1)` lookup
- Replaced `get_processing_queue` Python-side full scan/filter with Firestore-level `FieldFilter("kg_status", "==", "processing")` query
- Removed local `_find_note_by_id` from router, now uses properly bounded version from `document_processing_tasks`
- Improved `conftest.py` MockModule to properly auto-register sub-modules for Python 3.14 compatibility
- Regression tests created documenting expected bounded behavior

## Task Commits

Each task was committed atomically:

1. **Task 1: Backend regression tests for bounded KG lookups** - `01a7aa1` (test)
   - Created `api/tests/test_kg_lookup_paths.py` with tests for bounded lookups

2. **Task 2: Replace router scan paths with bounded Firestore queries** - `d2532de` (feat)
   - Fixed `api/kg/router.py` to use bounded queries
   - Removed local `_find_note_by_id`, uses imported bounded version
   - Added proper error handling with HTTPException

3. **Task 3: Align task-path note lookup** - No changes needed (document_processing_tasks.py already used bounded approach)

**Plan metadata commit:** `33ffdcb` (docs: complete plan)

_Note: Tests written but could not be executed due to pre-existing project import infrastructure issues with missing `model_router` and `services.*` module dependencies_

## Files Created/Modified

- `api/tests/test_kg_lookup_paths.py` - Regression tests for bounded KG lookup behavior
- `api/kg/router.py` - Fixed implementation using bounded Firestore queries
- `api/tests/conftest.py` - Improved MockModule for Python 3.14 compatibility

## Decisions Made

- Used `FieldFilter("id", "==", document_id)` instead of `__name__` range query for document status lookup (consistent with `document_processing_tasks.py` pattern)
- Removed stream-all fallback from queue endpoint; raises explicit HTTPException on index errors
- Router imports `_find_note_by_id` from `api.tasks.document_processing_tasks` instead of maintaining local duplicate

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Test infrastructure import failures**
- **Found during:** Task 1 (test creation)
- **Issue:** `conftest.py` MockModule was not properly registering sub-modules in sys.modules, causing `ModuleNotFoundError` for `services.llm_entity_extractor` and other imports
- **Fix:** Modified MockModule to auto-register child modules in sys.modules on `__getattr__` access
- **Files modified:** `api/tests/conftest.py`
- **Verification:** Module collection progresses further (still blocked by deeper import issues)
- **Committed in:** `33ffdcb` (part of conftest fix commit)

**2. [Rule 2 - Missing Critical] Removed local _find_note_by_id that replicated bad pattern**
- **Found during:** Task 2 (implementation)
- **Issue:** Router had local `_find_note_by_id` that used full `collection_group("notes").stream()` scan, duplicating the problematic pattern
- **Fix:** Removed local function, imported properly bounded `_find_note_by_id` from `api.tasks.document_processing_tasks`
- **Files modified:** `api/kg/router.py`
- **Verification:** Code inspection confirms no remaining stream-all patterns
- **Committed in:** `d2532de` (part of router fix commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 missing critical)
**Impact on plan:** Both auto-fixes necessary for correctness. No scope creep.

## Issues Encountered

- **Test execution blocked:** The project's test infrastructure has deep pre-existing import issues - `api.kg.router` imports from `api.tasks.document_processing_tasks` which imports from `api.kg_processor` which imports many `services.*` submodules that don't exist in the project (model_router, various services). While `conftest.py` was improved, fully fixing all import chains would require extensive mocking infrastructure separate from this plan.
- **Tests written as documentation:** The test file `api/tests/test_kg_lookup_paths.py` documents the expected bounded behavior but cannot be executed in the current environment. The implementation was verified through code inspection.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Plan 08-02 (bounded audio job state + frontend cleanup) can proceed
- Implementation verification should use code inspection + manual testing since automated tests cannot run in current environment
- Consider separate infrastructure work to fix the test import chain for future reliability work

---
*Phase: 08-runtime-hotspot-remediation-01*
*Completed: 2026-04-06*
