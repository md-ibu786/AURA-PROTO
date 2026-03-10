# Codebase Concerns

**Analysis Date:** 2026-03-10

## Tech Debt

**Monolithic backend and frontend files:**
- Issue: Core workflows are concentrated in very large files, which couples unrelated responsibilities and makes safe changes expensive.
- Files: `api/kg_processor.py`, `api/hierarchy_crud.py`, `api/users.py`, `api/audio_processing.py`, `api/tasks/document_processing_tasks.py`, `frontend/src/pages/AdminDashboard.tsx`
- Impact: Bug fixes require broad regression testing, ownership is unclear, and selective unit testing is difficult because logic is not isolated behind small services/components.
- Fix approach: Split each file by responsibility first (routing vs service vs persistence vs validation in Python, page container vs feature panels/hooks in React), then add focused tests around the extracted units.

**Overlapping API surfaces and ownership boundaries:**
- Issue: The repo maintains multiple read/write surfaces for similar hierarchy concepts: legacy endpoints in `api/main.py` and `api/hierarchy_crud.py`, read-only AURA-CHAT navigation in `api/hierarchy/router.py`, explorer endpoints in `api/explorer.py`, and a separate M2KG module system in `api/modules/router.py` + `api/modules/service.py` backed by `m2kg_modules` instead of hierarchy `modules`.
- Files: `api/main.py`, `api/hierarchy_crud.py`, `api/hierarchy/router.py`, `api/explorer.py`, `api/modules/router.py`, `api/modules/service.py`, `frontend/src/api/explorerApi.ts`
- Impact: New work can easily land in the wrong abstraction, data models diverge, and feature parity/security fixes must be repeated across parallel endpoints.
- Fix approach: Define one canonical API per domain, document which surfaces are legacy vs active, and progressively retire or wrap duplicate endpoints.

**Import-path workarounds instead of stable package boundaries:**
- Issue: Several modules patch `sys.path`, use `importlib.util`, or maintain layered fallback imports to make direct execution work.
- Files: `api/main.py`, `api/hierarchy/router.py`, `api/audio_processing.py`, `api/tasks/document_processing_tasks.py`, `tools/migrate_db.py`
- Impact: Packaging behavior differs between runtime, tests, and scripts; import bugs become environment-specific and harder to reproduce.
- Fix approach: Standardize `api`/`services` as importable packages, run entrypoints with module execution (`python -m ...`), and remove path mutation fallbacks.

## Known Bugs

**Playwright config points at a different port than Vite dev server:**
- Symptoms: Frontend E2E runs are prone to startup failures or connection issues because Playwright expects `http://127.0.0.1:5173` while Vite is configured for port `5174`.
- Files: `frontend/playwright.config.ts`, `frontend/vite.config.ts`
- Trigger: Run `npm run test:e2e` from `frontend/` with the default config.
- Workaround: Override the port manually or align one of the configs before running E2E.

**Explorer upload state type does not match backend note IDs:**
- Symptoms: Upload dialog state models `noteId` as a number even though note IDs are Firestore strings across the backend.
- Files: `frontend/src/components/explorer/UploadDialog.tsx`, `api/audio_processing.py`, `api/notes.py`
- Trigger: Consume `processing.result.noteId` as a numeric value in future UI logic.
- Workaround: Treat note IDs as opaque strings and update the dialog typing before adding more upload result handling.

## Security Considerations

**Protected resources are exposed without authentication:**
- Risk: Several routes that mutate data, trigger expensive processing, or expose generated files do not require auth dependencies even though adjacent code assumes RBAC.
- Files: `api/audio_processing.py`, `api/modules/router.py`, `api/kg/router.py`, `api/routers/summaries.py`, `api/routers/trends.py`, `api/routers/templates.py`, `api/routers/schema.py`, `api/main.py`, `api/hierarchy/router.py`
- Current mitigation: Frontend route guards in `frontend/src/components/ProtectedRoute.tsx` and token-aware client helpers in `frontend/src/api/client.ts` reduce casual UI access only.
- Recommendations: Add backend auth dependencies to every non-public route, enforce subject/department/module authorization server-side, and explicitly list the few endpoints that are intentionally public.

**PDF and document files are directly reachable outside the authenticated download route:**
- Risk: `api/main.py` defines `/api/pdfs/{filename}` but also mounts `/pdfs` as static files, and uploaded documents are stored under that mount point.
- Files: `api/main.py`, `api/audio_processing.py`, `api/hierarchy_crud.py`
- Current mitigation: `_resolve_pdf_path()` blocks traversal only for the `/api/pdfs/{filename}` route.
- Recommendations: Remove or gate the `/pdfs` static mount, serve files only through authenticated handlers, and centralize file authorization with note ownership checks.

**Session and bootstrap security remain v1-level:**
- Risk: Auth still depends on frontend-managed token/session state and first-user bootstrap logic that automatically grants admin when the `users` collection is empty.
- Files: `frontend/src/stores/useAuthStore.ts`, `api/auth_sync.py`, `.planning/STATE.md`
- Current mitigation: Firebase ID tokens are used for real auth flows and `require_admin`/`require_staff` exist for routes that opt into them.
- Recommendations: Move session handling toward httpOnly cookies or SDK-managed persistence only, remove mock-token persistence from app code outside test mode, and replace first-user auto-admin with an explicit bootstrap flow.

**Unsafe production defaults and optional protections:**
- Risk: Backend config falls back to insecure/default credentials and frontend App Check silently disables itself when the site key is absent or placeholder.
- Files: `api/config.py`, `frontend/src/api/firebaseClient.ts`
- Current mitigation: Runtime environment variables can override defaults.
- Recommendations: Fail fast in production when required secrets are missing, remove default `NEO4J_PASSWORD="password"`, and make App Check status visible in deployment checks.

## Performance Bottlenecks

**Full Firestore scans are used in hot paths:**
- Problem: Multiple endpoints load entire collections or collection groups into memory for lookup, filtering, or pagination.
- Files: `api/kg/router.py`, `api/tasks/document_processing_tasks.py`, `api/notes.py`, `api/users.py`, `api/modules/service.py`, `api/hierarchy_crud.py`
- Cause: Repeated `list(...stream())` patterns, collection-group scans for note lookup, and in-memory pagination/counting.
- Improvement path: Store lookup-friendly fields, use indexed equality queries with `limit(1)`, move counts to precomputed fields where needed, and paginate at the database level instead of materializing whole result sets.

**Explorer tree build is N+1 heavy and always fetches deep hierarchy:**
- Problem: The frontend requests depth `5` immediately and the backend recursively fetches children and note counts for the whole tree.
- Files: `frontend/src/pages/ExplorerPage.tsx`, `frontend/src/api/explorerApi.ts`, `api/explorer.py`
- Cause: `getExplorerTree(5)` plus per-node async child/count queries in `_build_*` helpers.
- Improvement path: Default to shallow/lazy loading, cache subtree responses, and avoid per-module note counting on initial page load.

**Admin dashboard performs sequential fan-out requests per department:**
- Problem: User management bootstrapping fetches departments and then loops through departments one-by-one to fetch subjects.
- Files: `frontend/src/pages/AdminDashboard.tsx`, `api/users.py`
- Cause: `fetchData()` issues serial `fetch` calls instead of using a batched backend endpoint or parallel requests.
- Improvement path: Add one backend endpoint that returns departments plus assignment-ready subjects, or parallelize client requests with bounded concurrency.

## Fragile Areas

**Cascade delete and file cleanup hide failures:**
- Files: `api/hierarchy_crud.py`
- Why fragile: Recursive deletes swallow file deletion errors, department delete still carries a TODO for file cleanup, and path-based PDF removal depends on stored URL shape.
- Safe modification: Change deletion behavior only with integration tests that verify Firestore cleanup, KG cleanup, and file removal together.
- Test coverage: Gaps around recursive delete/file cleanup paths; existing delete-focused tests are concentrated on KG batch deletion in `tests/test_kg_router_delete.py` and `tests/test_graph_manager_delete.py` rather than hierarchy CRUD file deletion.

**KG processing path spans router, task queue, and processor with placeholder identity:**
- Files: `api/kg/router.py`, `api/tasks/document_processing_tasks.py`, `api/kg_processor.py`
- Why fragile: Routers scan notes globally, enqueue work with placeholder user IDs (`"staff_user"` / `"staff_user_001"`), and depend on cross-system status synchronization between Firestore, Celery, Redis, and Neo4j.
- Safe modification: Keep request validation, task dispatch, status updates, and graph writes separate; add contract tests around one end-to-end batch flow before changing note lookup or task payloads.
- Test coverage: Gaps around authenticated batch processing and router-level access control; current tests focus on delete retry logic in `tests/test_kg_router_delete.py` rather than the full process-batch path.

**Mock-auth and real-auth behavior diverge materially:**
- Files: `frontend/src/stores/useAuthStore.ts`, `frontend/e2e/fixtures.ts`, `api/auth.py`
- Why fragile: Mock auth persists handcrafted tokens in localStorage, real auth uses Firebase SDK state, and E2E defaults to mock mode in `frontend/playwright.config.ts`.
- Safe modification: Treat mock auth as test-only infrastructure, keep one normalization layer for `AuthUser`, and verify any auth change in both mock and real flows.
- Test coverage: Gaps around real Firebase/browser integration; E2E coverage is heavily mock-driven and backend auth tests mostly use patched dependencies in `api/tests/test_rbac.py` and `tests/test_auth_integration.py`.

## Scaling Limits

**Audio pipeline status is single-process only:**
- Current capacity: One API process can track only its own in-memory jobs.
- Limit: `job_status_store` in `api/audio_processing.py` is lost on restart and cannot coordinate across multiple API instances.
- Scaling path: Persist pipeline state in Redis/Firestore and move job execution to a shared worker system for both status polling and recovery.

**Generated files live on local disk:**
- Current capacity: Files are written under the repo-local `pdfs` directory and served from the API host.
- Limit: Multi-instance deployments, container restarts, and large file sets create drift and missing-file risks.
- Scaling path: Move documents/PDFs to object storage, store signed/public URLs explicitly, and add lifecycle cleanup jobs.

**Module listing pagination is bounded by full collection reads:**
- Current capacity: `api/modules/service.py` reads all matching module docs before slicing pages.
- Limit: Response time and memory usage grow linearly with collection size.
- Scaling path: Use cursor-based pagination with Firestore queries and separate approximate/aggregate counting.

## Dependencies at Risk

**AI and multimodal paths are partially stubbed or degrade silently:**
- Risk: Some service imports fall back to runtime `ImportError` wrappers while multimodal services are explicitly unimplemented.
- Impact: Feature availability depends on environment quirks, and unsupported code paths may survive until runtime.
- Migration plan: Promote unsupported features behind explicit feature flags, fail fast at startup for required AI dependencies, and keep `services/multimodal/*.py` out of active routes until implemented.

## Missing Critical Features

**No durable background-job orchestration for uploads and AI processing:**
- Problem: Audio upload processing exposes async UX but still uses local process state in `api/audio_processing.py`; only KG processing uses Celery in `api/tasks/document_processing_tasks.py`.
- Blocks: Reliable recovery, horizontal scaling, and trustworthy progress/status history for note generation.

**No unified authorization model across legacy hierarchy, analytics, KG, and M2KG modules:**
- Problem: The codebase has auth helpers in `api/auth.py`, but many active routers do not consume them consistently.
- Blocks: Safe exposure of `/api/v1` functionality to real clients and clean delegation between admin, staff, and student capabilities.

## Test Coverage Gaps

**Analytics and schema routers lack direct API tests:**
- What's not tested: Route behavior, auth expectations, error mapping, and caching invalidation for summaries/trends/templates/schema endpoints.
- Files: `api/routers/summaries.py`, `api/routers/trends.py`, `api/routers/templates.py`, `api/routers/schema.py`
- Risk: Regressions in parameter validation, public exposure, and dependency failures can ship unnoticed.
- Priority: High

**Admin dashboard has no component-level test coverage:**
- What's not tested: The large user/hierarchy management page state machine, optimistic updates, and request sequencing in the React page itself.
- Files: `frontend/src/pages/AdminDashboard.tsx`
- Risk: Basic refactors can break admin workflows without fast feedback; current E2E coverage in `frontend/e2e/rbac.spec.ts` uses heavy route mocking and does not replace page-level unit coverage.
- Priority: High

**Audio workflow coverage stops at transcription validation:**
- What's not tested: `/api/audio/upload-document`, `/api/audio/process-pipeline`, `/api/audio/pipeline-status/{job_id}`, and the upload/polling UI in `frontend/src/components/explorer/UploadDialog.tsx`.
- Files: `api/audio_processing.py`, `frontend/src/components/explorer/UploadDialog.tsx`, `tests/test_audio_validation.py`
- Risk: Auth, file persistence, polling, and note-creation regressions are likely to appear only in manual testing.
- Priority: High

**CI does not exercise most of the application surface:**
- What's not tested: Backend pytest suite, frontend Vitest suite, and Playwright E2E are not present in GitHub Actions; the only detected workflow runs Firestore rules tests.
- Files: `.github/workflows/firestore-rules.yml`, `frontend/package.json`, `package.json`
- Risk: Mainline changes can merge without automated coverage for core API and UI behavior.
- Priority: High

---

*Concerns audit: 2026-03-10*
