---
phase: 07-failure-hardening-shared-seams
plan: 02
subsystem: api
tags: [error-handling, auth, refactoring, tdd]

# Dependency graph
requires:
  - phase: 06-verification-recovery
    provides: Verified test infrastructure and consistent verification commands
provides:
  - Centralized error classes (DuplicateError, AuthError, NetworkError)
  - Single 401 retry logic path (executeWithRetry)
  - Explicit auth failure handling in getAuthHeader
affects: [client.ts consumers, auth flows]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Error class hierarchy with cause property for chaining"
    - "Extracted shared retry logic pattern"

key-files:
  created:
    - frontend/src/api/errors.ts
  modified:
    - frontend/src/api/client.ts
    - frontend/src/api/client.test.ts

key-decisions:
  - "Moved DuplicateError from client.ts to dedicated errors.ts module for centralized error handling"
  - "AuthError includes optional cause property for error chaining while preserving original error context"
  - "getAuthHeader now throws AuthError instead of silently returning empty headers on token retrieval failure"

patterns-established:
  - "Error classes centralized in errors.ts with re-exports from client.ts for backward compatibility"
  - "executeWithRetry provides single source of truth for 401 retry logic across all fetch functions"

requirements-completed: [FAIL-01, FAIL-03, DRIFT-01, DRIFT-03]

# Metrics
duration: 35min
completed: 2026-04-06
---

# Phase 7 Plan 02: Error Handling Consolidation Summary

**Extracted shared retry logic, centralized error classes, and added explicit auth failure handling with test coverage.**

## Performance

- **Duration:** 35 min
- **Started:** 2026-04-06T21:23:00Z
- **Completed:** 2026-04-06T21:58:00Z
- **Tasks:** 3
- **Files modified:** 3

## Accomplishments

- Created dedicated `errors.ts` module with DuplicateError, AuthError, NetworkError classes
- Extracted 401 retry logic into single `executeWithRetry` helper function
- Refactored `getAuthHeader` to throw `AuthError` on token retrieval failure (explicit failure mode)
- All three fetch functions (fetchApi, fetchBlob, fetchFormData) now use shared retry logic
- Added comprehensive test coverage for auth failure scenarios

## Task Commits

Each task was committed atomically:

1. **Task 1: Create errors.ts with centralized error classes** - `6ae6e6b` (feat)
   - DuplicateError (moved from client.ts)
   - AuthError (new - with optional cause property)
   - NetworkError (new)

2. **Task 2: Extend client.test.ts with auth failure tests** - `dd34a86` (test)
   - TDD RED phase - 4 failing tests for auth failure scenarios
   - Tests for AuthError cause property
   - Tests for getAuthHeader throwing AuthError

3. **Task 3: Refactor client.ts with extracted retry logic** - `2699adf` (feat)
   - Consolidated 401 retry logic (was duplicated 3 times)
   - Updated getAuthHeader to throw AuthError on failure
   - Re-exported error classes for backward compatibility
   - All 7 tests passing

**Plan metadata:** Not yet committed (orchestrator manages final commit)

## Files Created/Modified

- `frontend/src/api/errors.ts` - New file with centralized error classes
- `frontend/src/api/client.ts` - Refactored with executeWithRetry, imports errors.ts
- `frontend/src/api/client.test.ts` - Extended with AuthError and auth failure tests

## Decisions Made

- **Dedicated errors.ts module:** Moved DuplicateError out of client.ts into dedicated errors module. This provides a single source for error classes and allows future expansion without modifying client.ts. Re-exported from client.ts for backward compatibility.

- **AuthError with cause chaining:** Added optional `cause` property to AuthError following standard Error cause patterns. This preserves original error context while providing actionable error messages.

- **Throw vs return empty:** Changed getAuthHeader behavior from silently returning `{}` on failure to throwing AuthError. This makes authentication problems visible to callers instead of hiding them. Callers expecting no auth (unauthenticated routes) should handle AuthError appropriately.

## Deviations from Plan

None - plan executed exactly as written.

## Threat Surface Scan

No additional threat surfaces introduced beyond those identified in the plan's threat model:
- T-07-03 (AuthError.cause exposure): Mitigated - cause is only logged server-side
- T-07-04 (Silent auth bypass): Mitigated - AuthError prevents silent auth failure

## Verification Results

All success criteria verified:
- [x] errors.ts exists with DuplicateError, AuthError, NetworkError
- [x] client.ts imports error classes from errors.ts
- [x] getAuthHeader throws AuthError on token retrieval failure
- [x] executeWithRetry function exists and is used by fetchApi, fetchBlob, fetchFormData
- [x] 401 retry logic appears only once (in executeWithRetry) - verified: `grep -c "response.status === 401"` returns 1
- [x] All existing client.test.ts tests pass
- [x] New auth failure tests pass
- [x] TypeScript compilation succeeds

## Known Stubs

None - all implementations are complete.

## Issues Encountered

None - implementation was straightforward following the plan.

## Next Phase Readiness

- Consolidated error handling foundation established
- Single source of truth for 401 retry logic eliminates drift risk
- Explicit AuthError enables proper auth failure handling in calling code
- Ready for Phase 7 Plan 03 to address remaining error handling patterns (backend silent failures)

## Self-Check: PASSED

- [x] `frontend/src/api/errors.ts` - EXISTS
- [x] `frontend/src/api/client.ts` - EXISTS (modified)
- [x] `frontend/src/api/client.test.ts` - EXISTS (modified)
- [x] Commit `6ae6e6b` - Found in git log
- [x] Commit `dd34a86` - Found in git log
- [x] Commit `2699adf` - Found in git log

---
*Phase: 07-failure-hardening-shared-seams*
*Completed: 2026-04-06*