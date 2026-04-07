---
phase: 07-failure-hardening-shared-seams
plan: 03
subsystem: api
tags: [error-handling, auth, refactoring, consolidation]

# Dependency graph
requires:
  - phase: 07-02
    provides: Centralized error classes (DuplicateError, AuthError), executeWithRetry helper
provides:
  - fetchAuthApi helper for auth store usage
  - Migrated login() sync call to use client.ts helper
  - Documented intentional direct fetch usage in refreshUser()
affects: [useAuthStore, auth flows]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "fetchAuthApi for explicit token parameter (avoids circular dependency)"
    - "Documented deviation pattern for specialized auth flows"

key-files:
  created: []
  modified:
    - frontend/src/api/client.ts
    - frontend/src/stores/useAuthStore.ts

key-decisions:
  - "fetchAuthApi uses explicit token parameter to avoid circular dependency during auth flows"
  - "refreshUser intentionally keeps direct fetch() calls for specialized 401 handling"
  - "login() migrated to fetchAuthApi - straightforward sync without retry logic"

patterns-established:
  - "Auth store uses fetchAuthApi when token is already available locally"
  - "Specialized auth flows (refreshUser 401 retry) remain with direct fetch for explicit control"

requirements-completed: [FAIL-03, DRIFT-01]

# Metrics
duration: 15min
completed: 2026-04-06
---

# Phase 7 Plan 03: Auth Store Fetch Migration Summary

**Migrated useAuthStore login() to use fetchAuthApi helper, documented intentional direct fetch usage in refreshUser().**

## Performance

- **Duration:** 15 min
- **Started:** 2026-04-06T21:01:37Z
- **Completed:** 2026-04-06T21:16:00Z
- **Tasks:** 3
- **Files modified:** 2

## Accomplishments

- Added `fetchAuthApi` helper to client.ts for auth store usage with explicit token parameter
- Migrated `login()` function's /auth/sync call from direct fetch() to fetchAuthApi
- Documented intentional deviation in `refreshUser()` with three reasons for keeping direct fetch
- Reduced direct fetch() usage in auth store (login sync migrated, refreshUser documented)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add fetchAuthApi helper to client.ts** - `6f03d85` (feat)
   - New exported async function for auth store
   - Accepts explicit token parameter
   - No 401 retry logic (auth store handles own retry)

2. **Task 2: Migrate useAuthStore login() to use fetchAuthApi** - `27e1980` (feat)
   - Replaced direct fetch() with fetchAuthApi<void>
   - Removed manual error handling (fetchAuthApi throws on failure)
   - Firebase error code handling preserved

3. **Task 3: Document intentional direct fetch usage in refreshUser** - `db66239` (docs)
   - Added JSDoc comment explaining deviation
   - Three reasons: specialized 401 handling, circular dep avoidance, silent fail semantics
   - References Phase 7 research

**Plan metadata:** Not yet committed (orchestrator manages final commit)

## Files Created/Modified

- `frontend/src/api/client.ts` - Added fetchAuthApi helper (lines 244-276)
- `frontend/src/stores/useAuthStore.ts` - Import fetchAuthApi, migrate login(), document refreshUser()

## Decisions Made

- **fetchAuthApi vs modifying fetchApi:** Created separate function to avoid circular dependency. fetchApi calls getAuthHeader() which calls getIdToken() on useAuthStore. During login(), the store is setting up state - passing explicit token avoids potential race conditions.

- **Not migrating refreshUser:** Documented three reasons:
  1. Specialized 401 handling with sync-then-retry pattern
  2. Avoids circular dependency during auth initialization
  3. Silent fail semantics (catch {} returns gracefully) vs throw

- **Satisfies DRIFT-01:** Consolidated where behavior is equivalent (login sync), documented where not (refreshUser 401 handling).

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

All success criteria verified:
- [x] fetchAuthApi function is exported from client.ts
- [x] login() in useAuthStore uses fetchAuthApi for /auth/sync
- [x] refreshUser() has documentation explaining intentional direct fetch usage
- [x] npm test (store tests) succeeds - 62 tests passed
- [x] npm test (client tests) succeeds - 7 tests passed
- [x] grep shows reduced direct fetch() calls (login sync migrated)

## Threat Surface Scan

No additional threat surfaces introduced beyond those identified in the plan's threat model:
- T-07-05 (fetchAuthApi token param): Mitigated - callers responsible for token validity
- T-07-06 (auth flow changes): Accept - low risk, login sync is straightforward

## Known Stubs

None - all implementations are complete.

## Issues Encountered

None - implementation was straightforward following the plan.

## Next Phase Readiness

- Auth store fetch consolidation complete
- login() now uses shared client.ts helper
- refreshUser intentionally keeps direct fetch for specialized 401 handling
- Ready for Phase 7 Plan 04 (if applicable) or next phase in roadmap

## Self-Check: PASSED

- [x] `frontend/src/api/client.ts` - EXISTS (modified, fetchAuthApi added)
- [x] `frontend/src/stores/useAuthStore.ts` - EXISTS (modified, login migrated, refreshUser documented)
- [x] Commit `6f03d85` - Found in git log
- [x] Commit `27e1980` - Found in git log
- [x] Commit `db66239` - Found in git log

---
*Phase: 07-failure-hardening-shared-seams*
*Completed: 2026-04-06*