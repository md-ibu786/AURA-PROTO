# Phase 04 Plan 02: User Sync Endpoint Summary

**Firebase Auth sync endpoint with first-login Firestore provisioning, admin
user lifecycle endpoints, and full test coverage**

## Accomplishments
- Added /api/auth/sync to create Firestore user documents on first login
- Implemented admin user create/update/delete endpoints with Auth + Firestore
  synchronization
- Added comprehensive tests covering sync, admin creation, updates, and
  deletion flows

## Files Created/Modified
- `api/auth_sync.py` - Auth/Firestore sync endpoints and admin lifecycle APIs
- `api/main.py` - Mount auth_sync router in the main FastAPI app
- `tests/test_auth_sync.py` - Unit tests for sync and admin endpoints

## Decisions Made
None - followed plan as specified.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added token-only dependency for /api/auth/sync**
- **Found during:** Task 2 (Implement POST /api/auth/sync endpoint)
- **Issue:** Using `get_current_user` would fail on first login because the
  Firestore user document does not exist yet, blocking sync entirely.
- **Fix:** Added `get_current_auth_user` to validate the ID token without
  Firestore lookup for the sync endpoint.
- **Files modified:** `api/auth_sync.py`
- **Verification:** `pytest tests/test_auth_sync.py -v`
- **Commit:** feat(04-02)

**2. [Rule 2 - Missing Critical] Blocked non-provisioned users from self-sync**
- **Found during:** Task 2 (Implement POST /api/auth/sync endpoint)
- **Issue:** Defaulting missing role claims to `student` would allow
  unauthorized self-registration, violating admin-only provisioning.
- **Fix:** Require a role custom claim for non-first users; return 403 if
  missing.
- **Files modified:** `api/auth_sync.py`
- **Verification:** `pytest tests/test_auth_sync.py -v`
- **Commit:** feat(04-02)

### Deferred Enhancements

None.

---

**Total deviations:** 2 auto-fixed (missing critical), 0 deferred
**Impact on plan:** Both changes were required for correct and secure sync
behavior. No scope creep beyond endpoint correctness.

## Issues Encountered
- Tests initially failed due to patching the wrong auth_sync module instance.
  Resolved by targeting the module actually used by the FastAPI app in tests.

## Next Phase Readiness
- Ready for 04-03 (Remove mock login).
- No blockers.

---
*Phase: 04-backend-auth-refactor*
*Completed: 2026-02-05*
