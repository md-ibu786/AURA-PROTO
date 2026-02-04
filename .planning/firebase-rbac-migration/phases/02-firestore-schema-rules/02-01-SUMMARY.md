# Phase 02 Plan 01: Firestore User Schema Summary

**Firestore user schema documentation with shared TS/Pydantic models and updated user endpoints validated against RBAC constraints**

## Accomplishments
- Documented Firestore `users` schema with constraints, examples, versioning, indexes, and security considerations.
- Added shared TypeScript and Python models plus validation utilities aligned to the Firestore schema.
- Updated user management endpoints to accept new inputs, validate role rules, and write normalized Firestore documents.

## Files Created/Modified
- `documentations/firebase-schema.md` - Firestore users schema documentation.
- `.gitignore` - Allow tracking documentation files.
- `frontend/src/types/user.ts` - Firestore user types and input shapes.
- `frontend/src/types/index.ts` - Barrel export updates for user types.
- `frontend/src/stores/useAuthStore.ts` - AuthUser typing aligned with Firestore user types.
- `api/models.py` - Pydantic models for Firestore user schema.
- `api/validators.py` - Role/status validation and normalization helpers.
- `api/users.py` - Endpoints updated to use new models and validators.
- `api/auth.py` - Exposes FirestoreUser import for verification.
- `api/__init__.py` - Optional imports to avoid PyMuPDF DLL failures on package import.
- `.planning/firebase-rbac-migration/ROADMAP.md` - Plan progress updated.

## Decisions Made
- Kept existing `UserResponse` payloads for `/api/users` endpoints to preserve AdminDashboard fields; FirestoreUser is used for validation/storage.
- Added Pydantic alias support for both camelCase and snake_case inputs to avoid breaking existing clients.

## Deviations from Plan
- Added `.gitignore` exceptions so `documentations/firebase-schema.md` is tracked.
- Included `password` in `CreateUserInput` to keep admin create-user flow and mock login compatibility.
- Guarded `api/__init__.py` imports to prevent PyMuPDF DLL errors from blocking `from api.auth import FirestoreUser` verification.
- Reinstalled `PyMuPDF`/`PyMuPDFb` in the project venv to resolve DLL load failures and unblock `pytest`.

## Issues Encountered
- `pytest` initially failed during collection due to PyMuPDF DLL load failure (`fitz` / `pymupdf`), affecting `tests/test_audio_validation.py`, `tests/test_department_duplicates.py`, and `tests/test_graph_preview.py`. Reinstalling `PyMuPDF`/`PyMuPDFb` resolved the issue; `pytest` now passes.
- Python 3.10 EOL warning from `google.api_core` surfaced during verification commands (non-blocking).

## Next Phase Readiness
- Phase 02-01 complete and ready for `02-02-PLAN.md`.
- Full test suite passes after PyMuPDF reinstall; ready to proceed.

---
*Phase: 02-firestore-schema-rules*
*Completed: 2026-02-04*
