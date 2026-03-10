# Codebase Structure

**Analysis Date:** 2026-03-10

## Directory Layout

```text
[project-root]/
├── api/                  # FastAPI backend, routers, Firestore/KG integrations, migrations, task workers
├── frontend/             # React + Vite frontend application
├── e2e/                  # Playwright end-to-end suite with separate package.json
├── services/             # Shared backend service implementations used by AI/KG routers
├── tools/                # Data seeding, migration, cleanup, and verification scripts
├── documentations/       # Human-written docs for schema, auth, and migration procedures
├── tests/                # Root-level Jest/Firestore test assets
├── pdfs/                 # Uploaded/generated note files served by the backend
├── .planning/            # Planning artifacts and mapper outputs
├── firestore.rules       # Firestore security rules
├── firebase.json         # Firebase emulator/deploy configuration
├── requirements.txt      # Python backend dependencies
└── package.json          # Root scripts for Firestore rules/emulator workflows
```

## Directory Purposes

**`api/`:**
- Purpose: Main backend application and adjacent backend-only subsystems.
- Contains: HTTP entrypoint, auth, hierarchy read/write logic, KG routers, Celery tasks, schemas, migrations, verification scripts.
- Key files: `api/main.py`, `api/auth.py`, `api/explorer.py`, `api/hierarchy_crud.py`, `api/users.py`, `api/kg/router.py`, `api/tasks/document_processing_tasks.py`

**`api/hierarchy/`:**
- Purpose: Typed read-only hierarchy API for external consumers.
- Contains: Router and Pydantic response models.
- Key files: `api/hierarchy/router.py`, `api/hierarchy/models.py`

**`api/modules/`:**
- Purpose: Separate M2KG module management feature, distinct from hierarchy modules.
- Contains: Router, service layer, publishing workflow, feature-specific models.
- Key files: `api/modules/router.py`, `api/modules/service.py`, `api/modules/publishing.py`, `api/modules/models.py`

**`api/routers/`:**
- Purpose: Newer package-style API routers for higher-level derived features.
- Contains: Summaries, trends, templates, schema, graph preview endpoints.
- Key files: `api/routers/summaries.py`, `api/routers/trends.py`, `api/routers/templates.py`, `api/routers/schema.py`, `api/routers/graph_preview.py`

**`api/tasks/`:**
- Purpose: Async worker entrypoints and task docs.
- Contains: Celery app/task definitions and config notes.
- Key files: `api/tasks/document_processing_tasks.py`, `api/tasks/CELERY_CONFIG.md`

**`frontend/src/`:**
- Purpose: All application source for the React client.
- Contains: Routes, stores, API wrappers, explorer components, KG feature module, tests, hooks, CSS, shared types.
- Key files: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/pages/ExplorerPage.tsx`, `frontend/src/stores/useAuthStore.ts`, `frontend/src/stores/useExplorerStore.ts`

**`frontend/src/api/`:**
- Purpose: Typed frontend integration boundary to backend endpoints.
- Contains: Auth-aware fetch client plus feature-specific API modules.
- Key files: `frontend/src/api/client.ts`, `frontend/src/api/explorerApi.ts`, `frontend/src/api/audioApi.ts`, `frontend/src/api/userApi.ts`, `frontend/src/api/firebaseClient.ts`

**`frontend/src/components/`:**
- Purpose: Reusable presentational and interaction components.
- Contains: `explorer/`, `layout/`, and `ui/` subtrees.
- Key files: `frontend/src/components/layout/Sidebar.tsx`, `frontend/src/components/layout/Header.tsx`, `frontend/src/components/explorer/GridView.tsx`, `frontend/src/components/explorer/UploadDialog.tsx`, `frontend/src/components/ui/ConfirmDialog.tsx`

**`frontend/src/features/kg/`:**
- Purpose: Feature-scoped Knowledge Graph UI module.
- Contains: KG components, React Query hooks, KG-specific types.
- Key files: `frontend/src/features/kg/hooks/useKGProcessing.ts`, `frontend/src/features/kg/components/ProcessDialog.tsx`, `frontend/src/features/kg/components/ProcessingQueue.tsx`

**`frontend/src/pages/`:**
- Purpose: Route-level page containers.
- Contains: Explorer, login, and admin dashboard pages.
- Key files: `frontend/src/pages/ExplorerPage.tsx`, `frontend/src/pages/LoginPage.tsx`, `frontend/src/pages/AdminDashboard.tsx`

**`frontend/src/stores/`:**
- Purpose: Zustand stores and store barrel exports.
- Contains: Auth store and explorer UI store.
- Key files: `frontend/src/stores/useAuthStore.ts`, `frontend/src/stores/useExplorerStore.ts`, `frontend/src/stores/index.ts`

**`frontend/src/types/`:**
- Purpose: Shared frontend type contracts that mirror backend models.
- Contains: Hierarchy node and user types plus barrel exports.
- Key files: `frontend/src/types/FileSystemNode.ts`, `frontend/src/types/user.ts`, `frontend/src/types/index.ts`

**`e2e/`:**
- Purpose: Separate Playwright workspace for browser and API end-to-end verification.
- Contains: Test specs, page objects, local package manifest, reports.
- Key files: `e2e/playwright.config.ts`, `e2e/tests/explorer.spec.ts`, `e2e/tests/api.spec.ts`, `e2e/tests/audio.spec.ts`, `e2e/README.md`

**`tools/`:**
- Purpose: Operator scripts for data lifecycle and environment verification.
- Contains: Seeders, migration drivers, cleanup utilities, backfills.
- Key files: `tools/seed_firestore.py`, `tools/migrate_db.py`, `tools/migration_config.py`, `tools/cleanup_pdfs.py`, `tools/verify_migration.py`

**`documentations/`:**
- Purpose: Supplemental implementation docs referenced by humans and future automation.
- Contains: Firestore schema, auth, security rules, migration notes.
- Key files: `documentations/firebase-schema.md`, `documentations/api-authentication.md`, `documentations/security-rules.md`, `documentations/migration-playbook.md`

## Key File Locations

**Entry Points:**
- `frontend/src/main.tsx`: Browser bootstrap for the React app.
- `frontend/src/App.tsx`: Route tree and auth listener startup.
- `api/main.py`: FastAPI composition root and runtime entrypoint.
- `api/tasks/document_processing_tasks.py`: Celery task registration and worker entry surface.

**Configuration:**
- `frontend/vite.config.ts`: Vite dev server, proxy rules, Vitest config, `@` alias.
- `frontend/tsconfig.app.json`: Strict TS compiler settings for app code.
- `api/config.py`: Firestore/Firebase, Neo4j, Redis, Vertex, and mock/real DB configuration.
- `firebase.json`: Firebase emulator/deploy configuration.
- `firestore.rules`: Firestore security rules.
- `requirements.txt`: Python dependency manifest.

**Core Logic:**
- `api/explorer.py`: Async tree assembly and move operations for explorer consumers.
- `api/hierarchy_crud.py`: Mutating hierarchy and note endpoints.
- `api/auth.py`: Token verification and RBAC dependencies.
- `api/users.py`: Admin user management and profile endpoints.
- `api/audio_processing.py`: File upload and audio-to-notes pipeline orchestration.
- `api/kg/router.py`: KG status, batch process, queue, and delete APIs.
- `api/graph_manager.py`: Neo4j traversal and graph mutation helpers.
- `frontend/src/pages/ExplorerPage.tsx`: Main explorer composition root.
- `frontend/src/stores/useExplorerStore.ts`: Shared explorer UI state.
- `frontend/src/api/explorerApi.ts`: Frontend contract for hierarchy and KG endpoints.

**Testing:**
- `api/tests/test_rbac.py`: Backend auth/RBAC unit tests.
- `api/test_kg_processor.py`: Backend KG processor tests.
- `frontend/src/**/*.test.tsx`: Frontend component/store/unit tests.
- `frontend/src/integration/StateSync.test.tsx`: Frontend integration-style state test.
- `frontend/src/tests/firestore.rules.test.ts`: Frontend-side Firestore rules test run via Jest.
- `e2e/tests/explorer.spec.ts`: Playwright UI workflow coverage.

## Naming Conventions

**Files:**
- Route/page components use `UpperCamelCase.tsx`: `frontend/src/pages/ExplorerPage.tsx`, `frontend/src/pages/AdminDashboard.tsx`.
- Zustand stores use `useXStore.ts`: `frontend/src/stores/useAuthStore.ts`, `frontend/src/stores/useExplorerStore.ts`.
- Backend flat feature modules use `snake_case.py`: `api/hierarchy_crud.py`, `api/audio_processing.py`, `api/auth_sync.py`.
- Package routers commonly use `router.py`, `models.py`, `service.py`, `publishing.py`: `api/modules/router.py`, `api/hierarchy/models.py`.
- Tests follow `.test.` or `.spec.` suffixes: `frontend/src/pages/ExplorerPage.test.tsx`, `api/tests/test_rbac.py`, `e2e/tests/explorer.spec.ts`.

**Directories:**
- Frontend UI directories are domain-oriented and lowercase: `frontend/src/components/explorer`, `frontend/src/features/kg`, `frontend/src/stores`.
- Backend package directories represent bounded features: `api/hierarchy`, `api/modules`, `api/kg`, `api/routers`, `api/tasks`, `api/schemas`.

## Where to Add New Code

**New Feature:**
- Frontend route/page code: `frontend/src/pages/` if the feature adds a route-level screen.
- Frontend reusable UI: `frontend/src/components/` or `frontend/src/features/<feature>/` if the feature has its own subdomain like `frontend/src/features/kg/`.
- Backend API surface: prefer `api/routers/` or a feature package like `api/<feature>/` for new router-based modules; only extend legacy flat files like `api/explorer.py` or `api/hierarchy_crud.py` when the new behavior clearly belongs to that existing surface.
- Tests: `frontend/src/**/*.test.tsx`, `api/tests/`, or `e2e/tests/` depending on scope.

**New Component/Module:**
- Explorer-specific UI: `frontend/src/components/explorer/`.
- Layout/chrome: `frontend/src/components/layout/`.
- Generic dialogs/buttons/primitives: `frontend/src/components/ui/`.
- KG-specific UI or hooks: `frontend/src/features/kg/components/` and `frontend/src/features/kg/hooks/`.
- Backend feature package: follow the `api/modules/` pattern with `router.py`, `models.py`, and `service.py` when the feature has its own lifecycle and data model.

**Utilities:**
- Frontend helpers: `frontend/src/lib/` or `frontend/src/hooks/`.
- Backend request-path helpers: colocate with the owning feature under `api/`.
- Cross-cutting operational scripts: `tools/`.

## Special Directories

**`pdfs/`:**
- Purpose: Runtime storage for uploaded/generated note files served by `/api/pdfs/{filename}` in `api/main.py`.
- Generated: Yes.
- Committed: Yes, directory exists in repo and may contain generated artifacts.

**`api/migrations/`:**
- Purpose: Firestore migration scripts and migration verification helpers.
- Generated: No.
- Committed: Yes.

**`frontend/dist/`:**
- Purpose: Vite production build output.
- Generated: Yes.
- Committed: Yes, present in the repository snapshot.

**`coverage/`, `htmlcov/`, `test-results/`, `playwright-report/`:**
- Purpose: Test and coverage artifacts from frontend, backend, and Playwright runs.
- Generated: Yes.
- Committed: Yes, present in the repository snapshot.

**`api/__pycache__/`, `api/tests/__pycache__/`, `tools/__pycache__/`:**
- Purpose: Python bytecode caches.
- Generated: Yes.
- Committed: Yes, present in the repository snapshot.

**`.planning/codebase/`:**
- Purpose: Generated architecture/stack/convention/concern reference docs consumed by GSD workflows.
- Generated: Yes.
- Committed: Yes.

---

*Structure analysis: 2026-03-10*
