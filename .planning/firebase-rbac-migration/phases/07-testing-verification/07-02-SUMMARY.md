# Phase 07 Plan 02: Security Rules Unit Tests Summary

**Firestore Security Rules test suite (73 tests) running on the emulator with staff-only module/note writes**

## Accomplishments
- Added a comprehensive Firestore rules test suite covering users, hierarchy, modules, notes, and edge cases
- Wired emulator-driven test scripts and Jest configuration for TypeScript rules tests
- Aligned module/note write permissions with staff-only policy and validated via passing tests
- Verified the rules suite passes end-to-end with the Firestore emulator

## Files Created/Modified
- `frontend/src/tests/firestore.rules.test.ts` - Firestore Security Rules test suite (73 tests)
- `frontend/package.json` - Added rules test scripts and testing dependencies
- `frontend/package-lock.json` - Dependency lockfile updates
- `frontend/jest.config.cjs` - Jest configuration for TypeScript rules tests
- `frontend/tsconfig.jest.json` - Jest-specific TypeScript config
- `firestore.rules` - Enforced staff-only module/note write permissions
- `.planning/firebase-rbac-migration/ROADMAP.md` - Phase 7 progress update
- `.planning/ISSUES.md` - Logged documentation enhancement

## Test Coverage
| Collection | Tests | Scenarios |
|------------|-------|-----------|
| users | 9 | Read own, read others, create/update/delete, list |
| departments | 6 | Read (auth/unauth), write (admin only) |
| semesters | 6 | Read (auth/unauth), write (admin only) |
| subjects | 8 | Read, create (admin), update (admin/staff assigned) |
| modules | 11 | Read, create/update (staff assigned), delete (admin) |
| notes | 13 | Read (role-based), create/update (staff assigned), delete (admin) |
| edge cases | 20 | Disabled users, invalid data, queries, missing permissions |
| **Total** | **73 tests** | **All passing** |

## Decisions Made
- Confirmed admins do not create/update modules or notes; staff-only writes remain enforced

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 4 - Architectural] Enforced staff-only module/note writes in security rules (user-approved)**
- **Found during:** Task 5 (Modules and notes rules testing)
- **Issue:** Existing rules allowed admin create/update for modules and notes, conflicting with plan and UI permissions
- **Fix:** Updated `firestore.rules` to restrict module/note create/update to staff with subject access
- **Files modified:** firestore.rules
- **Verification:** `npm run test:rules` (73 tests passed in emulator)
- **Commit:** Pending

**2. [Rule 3 - Blocking] Added Jest + ts-jest config for TypeScript rules tests**
- **Found during:** Task 2 (Test harness setup)
- **Issue:** Jest could not execute `.ts` rules tests without TypeScript transform configuration
- **Fix:** Added `jest.config.cjs` and `tsconfig.jest.json`; installed `ts-jest`
- **Files modified:** frontend/jest.config.cjs, frontend/tsconfig.jest.json, frontend/package.json, frontend/package-lock.json
- **Verification:** `npm run test:rules` (73 tests passed in emulator)
- **Commit:** Pending

### Deferred Enhancements

Logged to `.planning/ISSUES.md` for future consideration:
- ISS-001: Clarify admin module/note permissions in roadmap docs (discovered in Task 6)

---

**Total deviations:** 2 auto-fixed (1 architectural with approval, 1 blocking), 1 deferred
**Impact on plan:** Changes were required to align rules and enable TypeScript test execution; no scope creep.

## Issues Encountered
- None. Emulator `PERMISSION_DENIED` warnings were expected for `assertFails` cases and did not affect test results.

## Next Phase Readiness
Ready for 07-03-PLAN.md: End-to-end integration tests.

---
*Phase: 07-testing-verification*
*Completed: 2026-02-05*
