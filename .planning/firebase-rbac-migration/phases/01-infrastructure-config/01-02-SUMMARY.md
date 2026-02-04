# Phase 01 Plan 02: Backend Configuration Summary

**Firebase-aware config with mock/real switching, dotenv loading, and validation script**

## Accomplishments
- Updated `api/config.py` to load `.env`, initialize Firebase Admin SDK, and switch between mock and real Firestore.
- Added `get_auth()` and a mock DB helper to preserve backward compatibility in mock mode.
- Created `tools/verify_firebase_config.py` and validated mock-mode configuration.

## Files Created/Modified
- `api/config.py` - Conditional Firebase initialization, auth accessor, and env loading.
- `api/mock_firestore.py` - Added `get_mock_db()` helper for mock mode.
- `tools/verify_firebase_config.py` - Standalone Firebase configuration verifier.
- `.env` - Added Firebase configuration using `serviceAccountKey-auth.json`.
- `.planning/firebase-rbac-migration/ROADMAP.md` - Marked Plan 01-02 complete and Phase 1 complete.

## Decisions Made
- Continued using `serviceAccountKey-auth.json` (user preference) for credentials.
- Left `USE_REAL_FIREBASE=false` by default to preserve mock mode.

## Deviations from Plan

### User-Requested Adjustments
- Updated `.env` to use `serviceAccountKey-auth.json` instead of `serviceAccountKey.json`.

## Issues Encountered
- `pip install -r requirements.txt` emitted a dependency warning: `google-genai`
  requires `google-auth>=2.47.0`, but `google-auth==2.35.0` is pinned.
- Firebase verification commands emitted a warning that Python 3.10 will
  lose support for `google.api_core` after 2026-10-04 (non-blocking).

## Next Phase Readiness
- Phase 1 complete; ready for `02-01-PLAN.md` (Firestore user schema).
- Consider reconciling `google-auth` pin with `google-genai` requirements
  when updating dependencies.

---
*Phase: 01-infrastructure-config*
*Completed: 2026-02-04*
