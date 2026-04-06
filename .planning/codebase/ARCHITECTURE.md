# Architecture

**Analysis Date:** 2026-03-10

## Pattern Overview

**Overall:** Full-stack layered application with a React SPA, a FastAPI monolith, Firestore-backed hierarchy storage, and opt-in knowledge-graph/AI subsystems.

**Key Characteristics:**
- The frontend keeps client UI state in Zustand and server state in React Query, with typed API wrappers in `frontend/src/api/client.ts`, `frontend/src/stores/useExplorerStore.ts`, and `frontend/src/features/kg/hooks/useKGProcessing.ts`.
- The backend is a single FastAPI app in `api/main.py` that composes multiple routers, but the codebase mixes older flat modules like `api/explorer.py` and `api/hierarchy_crud.py` with newer package-style routers such as `api/modules/router.py` and `api/routers/summaries.py`.
- Firestore is the system of record for hierarchy, notes, and users via `api/config.py`; Neo4j, Redis, Celery, and AI services are attached as feature-specific subsystems rather than as a separate backend service layer.

## Layers

**Frontend App Shell:**
- Purpose: Boot the SPA, register providers, and define protected routes.
- Location: `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/components/ProtectedRoute.tsx`
- Contains: `QueryClientProvider`, router setup, auth listener startup, route guards.
- Depends on: React Router, TanStack Query, auth store.
- Used by: All frontend pages and components.

**Frontend Page Orchestration:**
- Purpose: Turn route-level state into concrete page layouts and workflows.
- Location: `frontend/src/pages/ExplorerPage.tsx`, `frontend/src/pages/LoginPage.tsx`, `frontend/src/pages/AdminDashboard.tsx`
- Contains: Explorer layout orchestration, login flow, admin CRUD dashboard.
- Depends on: Zustand stores, typed API modules, page-level component composition.
- Used by: Route entries in `frontend/src/App.tsx`.

**Frontend State Layer:**
- Purpose: Hold durable client-side state that is not owned by the server.
- Location: `frontend/src/stores/useAuthStore.ts`, `frontend/src/stores/useExplorerStore.ts`
- Contains: Auth session state, role helpers, breadcrumb/navigation state, selection state, dialog state, KG polling flags.
- Depends on: Firebase Auth in `frontend/src/api/firebaseClient.ts`, browser storage, frontend API functions.
- Used by: Pages, explorer components, route guards, KG hooks.

**Frontend API / Integration Layer:**
- Purpose: Normalize backend calls and keep response typing at the edge.
- Location: `frontend/src/api/client.ts`, `frontend/src/api/explorerApi.ts`, `frontend/src/api/audioApi.ts`, `frontend/src/api/userApi.ts`
- Contains: Auth-aware fetch wrappers, duplicate-name error mapping, CRUD calls, file upload helpers, KG endpoints.
- Depends on: Native `fetch`, auth store token retrieval, backend route contracts.
- Used by: Pages, components, React Query hooks, auth hydration.

**Frontend Feature / Presentation Layer:**
- Purpose: Render explorer, dialogs, layout chrome, and KG controls.
- Location: `frontend/src/components/explorer/`, `frontend/src/components/layout/`, `frontend/src/components/ui/`, `frontend/src/features/kg/`
- Contains: Tree/list/grid views, upload dialog, selection controls, KG badges, processing queue.
- Depends on: Zustand state, typed nodes from `frontend/src/types/FileSystemNode.ts`, API hooks.
- Used by: `frontend/src/pages/ExplorerPage.tsx` and `frontend/src/pages/AdminDashboard.tsx`.

**FastAPI Composition Layer:**
- Purpose: Configure middleware and mount all HTTP surfaces.
- Location: `api/main.py`
- Contains: CORS, security headers, rate limiting, router mounting, health/readiness endpoints, PDF download endpoints, a few legacy direct endpoints.
- Depends on: Router modules, config, static file serving.
- Used by: Uvicorn entrypoint and E2E tests in `frontend/playwright.config.ts`.

**Backend Read/Write Hierarchy Layer:**
- Purpose: Expose Firestore-backed hierarchy browsing and mutations.
- Location: `api/hierarchy.py`, `api/explorer.py`, `api/hierarchy_crud.py`, `api/notes.py`
- Contains: Read helpers, async tree assembly, CRUD endpoints, note creation helpers, move/cascade delete logic.
- Depends on: Firestore clients from `api/config.py` and permission helpers from `api/auth.py`.
- Used by: Explorer frontend, admin dashboard, upload/audio flows.

**Backend Auth / User Management Layer:**
- Purpose: Verify Firebase tokens, enforce RBAC, sync user records, and manage users.
- Location: `api/auth.py`, `api/auth_sync.py`, `api/users.py`, `api/models.py`, `api/validators.py`
- Contains: Bearer token verification, FastAPI dependencies, `/api/auth/sync`, `/api/auth/me`, `/api/users` CRUD.
- Depends on: Firebase Admin auth, Firestore user documents, role validation.
- Used by: Protected backend routes and frontend auth flows.

**Knowledge Graph / Analytics Layer:**
- Purpose: Process note documents into Neo4j and expose KG-adjacent APIs.
- Location: `api/kg/router.py`, `api/tasks/document_processing_tasks.py`, `api/kg_processor.py`, `api/graph_manager.py`, `api/routers/graph_preview.py`, `api/routers/summaries.py`, `api/routers/trends.py`, `api/routers/templates.py`, `api/routers/schema.py`
- Contains: Batch KG processing, Celery task dispatch, graph traversal, graph preview, summaries, templates, schema inspection.
- Depends on: Firestore notes, Neo4j driver, Redis/Celery, service modules under `services/`.
- Used by: KG frontend feature module and other API consumers.

**Auxiliary Operations Layer:**
- Purpose: Seed, migrate, verify, and benchmark data outside the request path.
- Location: `tools/`, `api/migrations/`, `api/verify_*.py`
- Contains: Firestore seeding, migration transforms, verification scripts, cleanup utilities.
- Depends on: Firestore config and live project data.
- Used by: Manual maintenance workflows and milestone verification.

## Data Flow

**Explorer Navigation and CRUD:**

1. `frontend/src/App.tsx` starts `initAuthListener()` from `frontend/src/stores/useAuthStore.ts`, then routes authenticated users to `frontend/src/pages/ExplorerPage.tsx` or `frontend/src/pages/AdminDashboard.tsx`.
2. `frontend/src/pages/ExplorerPage.tsx` calls `getExplorerTree()` from `frontend/src/api/explorerApi.ts` through React Query and combines the returned Firestore tree with UI state from `frontend/src/stores/useExplorerStore.ts`.
3. User actions in `frontend/src/components/explorer/GridView.tsx`, `frontend/src/components/explorer/ListView.tsx`, `frontend/src/components/explorer/ContextMenu.tsx`, and `frontend/src/components/layout/Sidebar.tsx` invoke typed API functions such as `createSubject()`, `renameNode()`, or `deleteNote()`.
4. Backend endpoints in `api/explorer.py`, `api/hierarchy_crud.py`, and `api/notes.py` read or mutate nested Firestore collections, then the frontend invalidates or refetches `['explorer', 'tree']` to refresh the tree.

**Authentication and Role Enforcement:**

1. `frontend/src/pages/LoginPage.tsx` calls `login()` from `frontend/src/stores/useAuthStore.ts`.
2. `frontend/src/stores/useAuthStore.ts` authenticates with Firebase in `frontend/src/api/firebaseClient.ts`, then calls `/api/auth/sync` and `/api/auth/me`.
3. `api/auth_sync.py` provisions the Firestore user document when needed, and `api/users.py` returns normalized profile data.
4. Subsequent frontend requests go through `frontend/src/api/client.ts`, which adds a Bearer token from the auth store; backend route dependencies in `api/auth.py` enforce role and status checks before handlers run.

**Note Upload and Audio Pipeline:**

1. `frontend/src/components/explorer/UploadDialog.tsx` sends document uploads or audio uploads to `/api/audio/upload-document` or `/api/audio/process-pipeline`.
2. `api/audio_processing.py` stores files under `pdfs/`, optionally creates note records through `api/notes.py`, and tracks long-running audio jobs in an in-memory `job_status_store`.
3. The frontend polls `/api/audio/pipeline-status/{job_id}` until completion, then refetches the explorer tree so the new note appears in the module.

**Knowledge Graph Processing:**

1. `frontend/src/features/kg/hooks/useKGProcessing.ts` triggers `processKGBatch()` and polls `getKGProcessingQueue()` / `getKGTaskStatus()` from `frontend/src/api/explorerApi.ts`.
2. `api/kg/router.py` validates note membership, skips already-ready notes, and dispatches `process_batch_task.delay(...)` from `api/tasks/document_processing_tasks.py`.
3. Celery tasks update Firestore note status fields, call `api/kg_processor.py`, and use `api/graph_manager.py` / Neo4j to create or delete graph structures.
4. Graph consumers use APIs in `api/routers/graph_preview.py` and related router modules to read Neo4j-backed derived views.

**State Management:**
- UI-local state lives in Zustand stores at `frontend/src/stores/useExplorerStore.ts` and `frontend/src/stores/useAuthStore.ts`.
- Server state and refresh semantics live in React Query via `frontend/src/main.tsx`, `frontend/src/pages/ExplorerPage.tsx`, and `frontend/src/features/kg/hooks/useKGProcessing.ts`.

## Key Abstractions

**Hierarchy Tree Node:**
- Purpose: Shared contract for the explorer hierarchy across backend and frontend.
- Examples: `api/explorer.py`, `frontend/src/types/FileSystemNode.ts`, `frontend/src/components/explorer/SidebarTree.tsx`
- Pattern: Backend Pydantic `ExplorerNode` maps directly to frontend `FileSystemNode`.

**Firestore User Model:**
- Purpose: Canonical auth/RBAC document for app users.
- Examples: `api/models.py`, `api/auth.py`, `api/users.py`, `frontend/src/types/user.ts`
- Pattern: Firestore document + Firebase token claims + frontend auth projection.

**Typed Fetch Wrapper:**
- Purpose: Centralize auth headers, duplicate-name handling, retry-after-401 logic, and response parsing.
- Examples: `frontend/src/api/client.ts`, `frontend/src/api/explorerApi.ts`, `frontend/src/api/userApi.ts`
- Pattern: Thin HTTP client plus feature-specific API modules.

**Explorer UI Store:**
- Purpose: Represent current folder, selection, dialog state, inline creation, and KG workflow toggles.
- Examples: `frontend/src/stores/useExplorerStore.ts`, `frontend/src/components/layout/Header.tsx`, `frontend/src/components/explorer/GridView.tsx`
- Pattern: Single Zustand store shared across explorer components.

**Module Split Between Hierarchy and M2KG:**
- Purpose: Distinguish hierarchy modules nested under subjects from M2KG publishing modules stored separately.
- Examples: `api/hierarchy_crud.py`, `api/modules/service.py`, `api/modules/models.py`
- Pattern: Two separate module concepts with different storage collections and APIs.

**Background KG Task Contract:**
- Purpose: Track long-running document processing outside the request thread.
- Examples: `api/kg/router.py`, `api/tasks/document_processing_tasks.py`, `frontend/src/features/kg/hooks/useKGProcessing.ts`
- Pattern: FastAPI dispatches Celery tasks, Firestore stores per-note status, React Query polls task/queue endpoints.

## Entry Points

**Frontend Browser Entry:**
- Location: `frontend/src/main.tsx`
- Triggers: Vite dev server or production frontend bundle.
- Responsibilities: Create React root, configure QueryClient, import global CSS, render `App`.

**Frontend Route Root:**
- Location: `frontend/src/App.tsx`
- Triggers: SPA render after `main.tsx`.
- Responsibilities: Start auth listener, define `/login`, `/admin`, and catch-all explorer route.

**Backend HTTP Entry:**
- Location: `api/main.py`
- Triggers: `uvicorn main:app` or Playwright web server startup in `frontend/playwright.config.ts`.
- Responsibilities: Load env, configure middleware, include routers, expose health and PDF endpoints.

**Celery Worker Entry:**
- Location: `api/tasks/document_processing_tasks.py`, `api/tasks/__init__.py`
- Triggers: Celery worker process.
- Responsibilities: Register KG processing tasks and provide task progress helpers.

**Operational Script Entry Points:**
- Location: `tools/seed_firestore.py`, `tools/migrate_db.py`, `tools/verify_migration.py`, `api/migrations/*.py`
- Triggers: Manual operator execution.
- Responsibilities: Seed data, migrate schema, verify environment/data integrity.

## Error Handling

**Strategy:** Edge-level HTTP validation plus feature-specific fallback behavior; the codebase prefers returning FastAPI `HTTPException` on request errors and lightweight frontend alerts/toasts on UI failures.

**Patterns:**
- Backend routes convert domain failures to HTTP status codes directly in `api/hierarchy_crud.py`, `api/auth.py`, `api/users.py`, and `api/kg/router.py`.
- The frontend API client in `frontend/src/api/client.ts` maps duplicate-name conflicts to `DuplicateError` and retries once on `401` by forcing token refresh.
- Long-running workflows keep explicit status state instead of holding open requests: `api/audio_processing.py` uses `job_status_store`, while `api/tasks/document_processing_tasks.py` writes progress to Celery state and Firestore.

## Cross-Cutting Concerns

**Logging:** `api/main.py`, `api/audio_processing.py`, `api/tasks/document_processing_tasks.py`, `api/kg/router.py`, and `api/graph_manager.py` use module loggers; frontend code mainly uses `console.error` / `console.warn` in `frontend/src/stores/useAuthStore.ts` and `frontend/src/api/client.ts`.
**Validation:** Pydantic request/response models live in `api/models.py`, `api/modules/models.py`, `api/hierarchy/models.py`, and router-local schemas; frontend typing mirrors backend contracts in `frontend/src/types/` and `frontend/src/features/kg/types/kg.types.ts`.
**Authentication:** Frontend Firebase Auth starts in `frontend/src/api/firebaseClient.ts` and `frontend/src/stores/useAuthStore.ts`; backend Bearer token verification and RBAC dependencies live in `api/auth.py`; route protection is mirrored in `frontend/src/components/ProtectedRoute.tsx`.

---

*Architecture analysis: 2026-03-10*
