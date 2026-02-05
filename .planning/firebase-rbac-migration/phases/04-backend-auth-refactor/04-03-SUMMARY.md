# Phase 04 Plan 03: Remove Mock Login Summary

**Removed mock login endpoint, enforced real Firebase token verification (test-only mocks), and documented Firebase auth flow with frontend sync**

## Accomplishments
- Removed the mock `/api/auth/login` endpoint and decoupled the auth router from the API
- Restricted mock token verification to `TESTING=true` only and stopped persisting passwords in Firestore
- Added Firebase auth documentation and updated the frontend auth store to use Firebase sign-in with `/api/auth/sync`

## Files Created/Modified
- `api/auth.py` - Removed mock login endpoint and gated mock tokens to tests only
- `api/main.py` - Removed auth router include after login endpoint removal
- `api/users.py` - Removed plaintext password persistence from Firestore user creation
- `frontend/src/stores/useAuthStore.ts` - Switched to Firebase sign-in, token handling, and sync flow
- `.env.example` - Production Firebase defaults with TESTING flag documentation
- `.gitignore` - Allow new auth documentation to be tracked
- `documentations/api-authentication.md` - New Firebase authentication flow documentation
- `.planning/firebase-rbac-migration/ROADMAP.md` - Marked Phase 4 complete
- `api/test_auth_integration.py` - Removed obsolete mock login integration tests

## Decisions Made
- Mock token verification is now only allowed when `TESTING=true` and `USE_REAL_FIREBASE=false`
- Frontend auth now relies on Firebase sign-in and `/api/auth/sync` instead of mock tokens

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Mock login endpoint was defined in `api/auth.py`, not `api/users.py`**
- **Found during:** Task 1 (Remove mock login endpoint)
- **Issue:** Plan referenced `api/users.py`, but the endpoint lived in `api/auth.py` with router wiring in `api/main.py`
- **Fix:** Removed the login endpoint in `api/auth.py` and dropped the router include in `api/main.py`
- **Files modified:** `api/auth.py`, `api/main.py`
- **Verification:** `python -c "from api.users import router; print('OK')"`
- **Commit:** Pending

**2. [Rule 2 - Missing Critical] Stopped persisting plaintext passwords in Firestore**
- **Found during:** Task 1 (Remove mock login endpoint)
- **Issue:** User creation still stored plaintext passwords for mock auth, which is a security risk in production
- **Fix:** Removed password field persistence from Firestore user creation
- **Files modified:** `api/users.py`
- **Verification:** `python -m py_compile api/auth.py api/auth_sync.py api/users.py`
- **Commit:** Pending

**3. [Rule 2 - Missing Critical] Updated frontend login flow to Firebase Auth**
- **Found during:** Task 4 (Create API authentication documentation)
- **Issue:** Frontend still relied on `/api/auth/login`, which no longer exists
- **Fix:** Switched to `signInWithEmailAndPassword`, removed mock token storage, and synced via `/api/auth/sync`
- **Files modified:** `frontend/src/stores/useAuthStore.ts`
- **Verification:** Manual review; relies on existing Firebase SDK config
- **Commit:** Pending

**4. [Rule 3 - Blocking] Removed obsolete mock login integration tests**
- **Found during:** Task 5 (Final validation)
- **Issue:** `api/test_auth_integration.py` only tested the removed `/api/auth/login` endpoint
- **Fix:** Removed the obsolete test file
- **Files modified:** `api/test_auth_integration.py`
- **Verification:** `pytest tests/test_auth_sync.py -v`
- **Commit:** Pending

**5. [Rule 3 - Blocking] Unignored new auth documentation for version control**
- **Found during:** Task 4 (Create API authentication documentation)
- **Issue:** `.gitignore` excluded `documentations/` so the new doc would not be tracked
- **Fix:** Added explicit unignore for `documentations/api-authentication.md`
- **Files modified:** `.gitignore`
- **Verification:** File appears as untracked and is ready to commit
- **Commit:** Pending

---

**Total deviations:** 5 auto-fixed (2 missing critical, 3 blocking), 0 deferred
**Impact on plan:** All changes were required to remove mock auth safely and keep login functional. No scope creep beyond auth correctness.

## Issues Encountered
None.

## Next Phase Readiness
Phase 4 complete. Ready for Phase 06 (App Check & Security Hardening).

---
*Phase: 04-backend-auth-refactor*
*Completed: 2026-02-05*
