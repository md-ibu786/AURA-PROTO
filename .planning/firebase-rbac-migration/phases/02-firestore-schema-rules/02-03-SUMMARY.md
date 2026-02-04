# Phase 02 Plan 03: Security Rules Testing Summary

**Firestore emulator-backed security rules test suite covering auth, admin, staff, student, and edge-case RBAC scenarios with CI automation**

## Accomplishments
- Built a comprehensive Firestore rules test suite covering all roles, auth states, and edge cases
- Added shared test utilities and Jest setup for consistent emulator-based rule testing
- Wired npm scripts and CI workflow to run rules tests automatically

## Files Created/Modified
- `tests/firestore/rules-test-utils.js` - Shared helpers for auth contexts, test data, and environment setup
- `tests/firestore/setup.js` - Jest setup for emulator timeouts
- `tests/firestore/auth.test.js` - Authentication and unauthenticated access tests
- `tests/firestore/admin.test.js` - Admin CRUD and global access tests
- `tests/firestore/staff.test.js` - Staff subject-scoped access tests
- `tests/firestore/student.test.js` - Student read-only and edge case tests
- `jest.config.js` - Jest configuration for Firestore rules tests
- `.github/workflows/firestore-rules.yml` - CI workflow for rules tests
- `package.json` - Added rules/emulator test scripts
- `package-lock.json` - Recorded test dependency installs
- `.gitignore` - Unignored `tests/firestore` so rules tests are tracked
- `firestore.rules` - Hardened helpers for status claims and null-safe user lookups

## Decisions Made
- Serialized Jest workers (`maxWorkers: 1`) to avoid emulator data races during parallel test runs

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Hardened rules helpers to avoid null evaluation errors**
- **Found during:** Task 6 (Staff/Student role tests)
- **Issue:** `userDoc()` lookups could throw null evaluation errors when user data was missing
- **Fix:** Added null-safe checks in helper functions and relaxed active-status checks
- **Files modified:** `firestore.rules`
- **Verification:** `npm run test:rules` passes
- **Commit:** (this commit)

**2. [Rule 3 - Blocking] Serialized Jest workers to prevent emulator data races**
- **Found during:** Task 7 (Rules test runner)
- **Issue:** Parallel test files cleared shared emulator data mid-run, causing nondeterministic failures
- **Fix:** Set `maxWorkers: 1` in Jest config for rules tests
- **Files modified:** `jest.config.js`
- **Verification:** `npm run test:rules` passes
- **Commit:** (this commit)

**3. [Rule 3 - Blocking] Unignored Firestore rules tests for tracking**
- **Found during:** Task 2 (Test utilities)
- **Issue:** Root `tests/` directory was ignored, preventing rules tests from being committed
- **Fix:** Added targeted unignore for `tests/firestore/**`
- **Files modified:** `.gitignore`
- **Verification:** `tests/firestore/*` tracked by git status
- **Commit:** (this commit)

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking), 0 deferred
**Impact on plan:** All deviations were required for reliable test execution and delivery of tracked test artifacts. No scope creep.

## Issues Encountered
- Parallel Jest workers conflicted on shared emulator state; resolved by serializing test workers

## Next Phase Readiness
- Phase 2 complete; ready to begin Phase 3 data migration (`03-01-PLAN.md`)

---
*Phase: 02-firestore-schema-rules*
*Completed: 2026-02-04*
