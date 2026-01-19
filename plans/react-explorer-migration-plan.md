# React Explorer Migration Implementation Plan

## 1. Introduction & Goals

This document expands the high-level migration roadmap in `MIGRATION_PLAN.md` into a detailed, step-by-step implementation plan for migrating AURA-PROTO from Streamlit to a modern React-based "Explorer" interface.

The plan is intended for engineers and technical leads who will:
- Implement new FastAPI capabilities to support an explorer-style hierarchy.
- Stand up a Vite + React + TypeScript + Tailwind frontend.
- Build a Windows Explorer / Google Drive–style interface for navigating and managing the notes hierarchy.
- Migrate usage from existing Streamlit views to the new React explorer safely and incrementally.

Non-goals for this document:
- Full implementation specifications for authentication and authorization (deferred).
- Deep redesign of the FastAPI domain models or database schema.
- Low-level component-by-component design; the focus is tasks and architecture.


## 2. Overview of Target Architecture

### 2.1 High-Level System

- **Backend**
  - FastAPI application in `api/` remains the primary backend.
  - New explorer-oriented REST endpoints expose the hierarchy as navigable tree nodes.
  - Existing CRUD endpoints for departments, semesters, subjects, modules, and notes are reused and extended where appropriate.
  - Static PDFs in `pdfs/` are served via FastAPI-mounted static directory (e.g., `/static/pdfs`).

- **Frontend**
  - New SPA under `/frontend` built with:
    - Vite
    - React + TypeScript
    - Tailwind CSS (utility-first styling)
    - `zustand` for UI and explorer state
    - `@tanstack/react-query` for data fetching and caching
    - `@dnd-kit/core` for drag-and-drop
    - `shadcn/ui` (Radix-based) for dialogs, context menus, and other primitives
  - UI paradigm:
    - Left sidebar: recursive hierarchy tree.
    - Top: breadcrumb bar showing the current path.
    - Main panel: toggleable grid/list view for children of the selected node.
    - Context menus, drag-and-drop, and multi-selection mirroring file explorer behavior.

- **Deployment model**
  - Development: React dev server (Vite) on `localhost:5173`, FastAPI on its existing port.
  - Production: React built assets served by FastAPI (or reverse proxy) with index.html fallback for client-side routing.


## 3. Phase 1: Backend Preparation (FastAPI)

Goal: Enable the existing FastAPI backend to serve the React explorer and support explorer-style operations while remaining compatible with current Streamlit UIs during migration.

### 3.1 CORS Configuration

**Task 1.1 – Audit current CORS settings (Must-have)**
- **Goal:** Understand and document current CORS configuration for FastAPI.
- **Actions:**
  1. Inspect `api/main.py` for `CORSMiddleware` configuration.
  2. Identify current allowed origins, methods, headers, and credentials options.
  3. Note any environment-specific overrides (e.g., local vs production).
- **Dependencies:** None.
- **Risks / Notes:** Make sure existing clients (Streamlit) remain functional while broadening CORS.

**Task 1.2 – Configure CORS for Vite dev server (Must-have)**
- **Goal:** Allow the React dev server on `http://localhost:5173` to call the API during development.
- **Actions:**
  1. Update `api/main.py` `CORSMiddleware` `allow_origins` to include `"http://localhost:5173"`.
  2. Prefer environment-based configuration so that additional origins can be added without code changes.
  3. Ensure `allow_methods` includes standard verbs used by the explorer (`GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `OPTIONS`).
  4. Ensure `allow_headers` covers `Content-Type`, `Authorization` (if used), and any custom headers.
- **Dependencies:** Task 1.1.
- **Risks / Notes:** Avoid `"*"` for production; instead, use a controlled set of origins.

**Task 1.3 – Plan production CORS policy (Must-have)**
- **Goal:** Define a production-ready CORS policy for the React frontend.
- **Actions:**
  1. Decide expected production frontend hostnames (e.g., `https://aura.internal`, `https://aura.example.com`).
  2. Configure `allow_origins` to these domains and document in deployment configuration (e.g., environment variables).
  3. Document CORS expectations in `README.md` or deployment docs.
- **Dependencies:** Task 1.1.
- **Risks / Notes:** Overly strict CORS will silently break the SPA; ensure errors are visible in browser logs and docs.


### 3.2 Static Files Handling for PDFs

**Task 1.4 – Serve PDFs directory via FastAPI (Must-have)**
- **Goal:** Expose generated PDFs in `pdfs/` for React to download and preview.
- **Actions:**
  1. In `api/main.py`, use `StaticFiles` to mount the `pdfs/` directory at a stable path, e.g., `/static/pdfs`.
  2. Ensure this directory is correctly referenced relative to the project root when the app is run from different working directories.
  3. Consider read-only serving; write operations remain internal to backend services.
  4. Add basic tests or manual checks to confirm PDFs can be retrieved via `GET /static/pdfs/<filename>.pdf`.
- **Dependencies:** None.
- **Risks / Notes:** Avoid accidentally exposing other filesystem paths; mount only the intended `pdfs/` directory.

**Task 1.5 – Define PDF URL construction contract (Must-have)**
- **Goal:** Provide a predictable pattern for frontend to construct PDF URLs.
- **Actions:**
  1. Document that PDF URLs follow `BASE_API_URL + '/static/pdfs/' + note.pdf_filename` (or equivalent field).
  2. Ensure note metadata returned from API includes the filename or relative path needed.
  3. If necessary, add a `pdf_path` or `pdf_filename` field in note responses.
- **Dependencies:** Task 1.4.
- **Risks / Notes:** Keep URL shape stable across environments; prefer using backend-provided fields.


### 3.3 Explorer Node Model & API

**Task 1.6 – Define explorer node data model (Must-have)**
- **Goal:** Establish a normalized shape for nodes representing hierarchy elements.
- **Proposed model:**
  ```json
  {
    "id": "<string|number>",
    "type": "department|semester|subject|module|note",
    "label": "Human-readable name",
    "parentId": "<id|null>",
    "children": [ /* optional, for tree endpoints */ ],
    "meta": {
      "noteCount": 0,
      "hasChildren": true,
      "ordering": 1,
      "pdfFilename": "<for notes>",
      "createdAt": "ISO timestamp",
      "updatedAt": "ISO timestamp"
    }
  }
  ```
- **Actions:**
  1. Design a Pydantic schema (e.g., `ExplorerNode`) encapsulating the above shape.
  2. Decide whether `children` is always included (nested tree) or only for selected endpoints.
  3. Align `id` and `parentId` with existing database primary/foreign keys.
- **Dependencies:** Familiarity with current note hierarchy models.
- **Risks / Notes:** Avoid circular structures or ambiguous parent relationships.

**Task 1.7 – Implement `GET /api/explorer/tree` (Must-have)**
- **Goal:** Provide a single endpoint for fetching the hierarchy in an explorer-friendly structure.
- **Actions:**
  1. Create a new router (e.g., `api/notes_explorer.py` or `api/explorer.py`) if not already present.
  2. Implement `GET /api/explorer/tree` that:
     - Queries hierarchical data (departments → semesters → subjects → modules → notes).
     - Maps each entity to an `ExplorerNode`.
     - Returns either:
       - A fully nested tree (`children` populated), or
       - A root-level list where each node includes `parentId` and a `hasChildren` flag (frontend builds tree).
  3. Consider optional query parameters:
     - `depth` (e.g., `1` for departments only, `2` including semesters, etc.).
     - `root_id` to fetch a subtree.
  4. Optimize for the expected hierarchy size (e.g., eager loading vs lazy loading children).
- **Dependencies:** Task 1.6.
- **Risks / Notes:** Full-tree responses can be large; consider pagination or depth limiting if necessary.

**Task 1.8 – Map CRUD operations to explorer actions (Must-have)**
- **Goal:** Ensure existing CRUD endpoints are suitable for explorer operations.
- **Actions:**
  1. Catalog existing endpoints for each entity type (department, semester, subject, module, note).
  2. For each operation (create, rename, delete, move):
     - Identify which endpoint will be called.
     - Verify required fields and request bodies.
  3. Update or add endpoints if necessary, especially for move/rename.
- **Dependencies:** Existing API documentation and code.
- **Risks / Notes:** Avoid breaking existing Streamlit clients; support old and new usage during migration.

**Task 1.9 – Implement safe "move" semantics (Must-have)**
- **Goal:** Support drag-and-drop re-parenting with validation.
- **Actions:**
  1. Decide on the move contract, e.g., `PUT /api/explorer/move` or per-entity `PUT /api/modules/{id}/move`.
  2. Request body pattern, for example:
     ```json
     { "targetParentId": "<id>", "targetParentType": "subject|module|..." }
     ```
  3. Implement validation rules:
     - Departments have no parent.
     - Semesters must have a department parent.
     - Subjects must have a semester parent.
     - Modules must have a subject parent.
     - Notes must have a module parent.
     - Disallow moving a node into its own subtree.
  4. Implement transactional updates so that moves are atomic.
- **Dependencies:** Task 1.6, Task 1.8.
- **Risks / Notes:** Incorrect moves can corrupt hierarchy; ensure clear error responses for invalid requests.

**Task 1.10 – Implement rename endpoint(s) (Must-have)**
- **Goal:** Allow renaming of any node type.
- **Actions:**
  1. Expose or confirm an endpoint such as `PATCH /api/{entity}/{id}` with a payload `{ "name": "New Name" }`.
  2. Ensure responses reflect updated labels for use in explorer.
- **Dependencies:** Task 1.8.
- **Risks / Notes:** Handle uniqueness constraints if present (e.g., no duplicate names in same parent).

**Task 1.11 – Implement delete endpoints with safety checks (Must-have)**
- **Goal:** Allow deletions while guarding against unintended cascading loss.
- **Actions:**
  1. Confirm or implement delete endpoints for each entity (`DELETE /api/{entity}/{id}`).
  2. Decide on deletion semantics:
     - Hard delete vs soft delete.
     - Cascade rules: deleting a subject may delete all modules and notes.
  3. Add optional `dry_run=true` query param to return impact summary without deleting.
- **Dependencies:** Task 1.8.
- **Risks / Notes:** Deletion behavior must be clearly communicated to frontend; consider confirmation dialogs.


### 3.4 Long-Running Operations & Optional Realtime

**Task 1.12 – Catalog long-running operations (Must-have)**
- **Goal:** Identify operations that are slow enough to warrant progress indicators.
- **Actions:**
  1. List endpoints that create or regenerate PDFs, perform transcription, or summarization.
  2. Measure/estimate typical durations.
- **Dependencies:** Knowledge of current services (`services/` and related APIs).

**Task 1.13 – Define minimal polling-based status API (Must-have)**
- **Goal:** Enable the React UI to display "Processing" states without full realtime infrastructure.
- **Actions:**
  1. Introduce a lightweight status endpoint (e.g., `GET /api/notes/{id}/status`).
  2. Expose fields indicating processing state (`queued`, `processing`, `complete`, `error`).
  3. Ensure note metadata returned in tree/list reflects a `processing` flag when appropriate.
- **Dependencies:** Task 1.12.

**Task 1.14 – Outline optional WebSockets/SSE design (Nice-to-have)**
- **Goal:** Provide a future path for true realtime updates.
- **Actions:**
  1. Sketch endpoint(s) for `ws://.../status` or `GET /api/status/stream`.
  2. Describe message format (e.g., `{ noteId, status, progress }`).
  3. Mark this as optional for v1 and not required before React launch.
- **Dependencies:** Task 1.12.


## 4. Phase 2: Frontend Architecture (React)

Goal: Stand up a well-structured, type-safe React codebase that can host the explorer interface and evolve over time.

### 4.1 Project Setup & Tooling

**Task 2.1 – Initialize Vite + React + TypeScript project (Must-have)**
- **Goal:** Create the base React project under `/frontend`.
- **Actions:**
  1. From project root, run `npm create vite@latest frontend -- --template react-ts`.
  2. Configure project metadata (name, version) as appropriate.
  3. Add basic scripts: `dev`, `build`, `preview` in `package.json`.
  4. Add `.gitignore` compatible with existing repo (node_modules, build artifacts).
- **Dependencies:** None.

**Task 2.2 – Configure Tailwind CSS (Must-have)**
- **Goal:** Set up Tailwind for styling.
- **Actions:**
  1. Install Tailwind, PostCSS, and autoprefixer.
  2. Generate `tailwind.config.cjs` and `postcss.config.cjs` in `/frontend`.
  3. Configure content paths to include all `src/**/*.{ts,tsx}` files.
  4. Add base Tailwind directives to `src/index.css` (or equivalent).
- **Dependencies:** Task 2.1.

**Task 2.3 – Install core dependencies (Must-have)**
- **Goal:** Bring in all libraries referenced in the migration plan.
- **Actions:**
  1. Install `zustand`, `@tanstack/react-query`, `@tanstack/react-query-devtools`, `@dnd-kit/core`, `@dnd-kit/sortable`, `@dnd-kit/modifiers`.
  2. Install `lucide-react`, `clsx`, `tailwind-merge`.
  3. Install `react-router-dom` (if using explicit routes beyond a single explorer page).
  4. Integrate `shadcn/ui` according to its setup instructions (if chosen) and generate base components.
- **Dependencies:** Task 2.1, 2.2.


### 4.2 Directory Structure & Routing

**Task 2.4 – Establish `/frontend/src` directory structure (Must-have)**
- **Goal:** Organize code in a way that matches planned responsibilities.
- **Proposed structure:**
  ```text
  /frontend
    └── src
        ├── api          # Axios/fetch clients and API helpers
        ├── components
        │   ├── explorer # FileRow, GridItem, SidebarTree, Breadcrumbs, ContextMenus
        │   ├── ui       # Buttons, Inputs, Dialogs, Menus (wrappers over shadcn/ui)
        │   └── layout   # Main layout (Sidebar + Header + Content)
        ├── hooks        # Custom hooks (useSelection, useContextMenu, etc.)
        ├── stores       # Zustand stores
        ├── types        # Shared TypeScript types (FileSystemNode, etc.)
        ├── pages        # Top-level pages (ExplorerPage)
        └── lib          # Utility functions (e.g., tree helpers)
  ```
- **Actions:**
  1. Create the directories above.
  2. Add placeholder `index.ts` or minimal components in each directory to validate imports.
- **Dependencies:** Task 2.1.

**Task 2.5 – Configure application shell and routing (Must-have)**
- **Goal:** Provide an entry point for the explorer.
- **Actions:**
  1. Decide between:
     - Single route SPA (only explorer), or
     - Multiple routes (e.g., `/explorer`, `/admin`). For now, focusing on explorer-only is acceptable.
  2. Implement `App.tsx` that renders `ExplorerPage` within a root layout.
  3. If using `react-router-dom`, configure a minimal router with a catch-all route for the explorer.
- **Dependencies:** Task 2.4.


### 4.3 State Management & Data Fetching

**Task 2.6 – Define core TypeScript types (Must-have)**
- **Goal:** Provide shared types mirroring backend explorer node model.
- **Actions:**
  1. Add `types/FileSystemNode.ts` defining:
     ```ts
     export type HierarchyType = 'department' | 'semester' | 'subject' | 'module' | 'note';

     export interface FileSystemNodeMeta {
       noteCount?: number;
       hasChildren?: boolean;
       ordering?: number;
       pdfFilename?: string | null;
       createdAt?: string;
       updatedAt?: string;
       processing?: boolean;
     }

     export interface FileSystemNode {
       id: string;
       type: HierarchyType;
       label: string;
       parentId: string | null;
       children?: FileSystemNode[];
       meta?: FileSystemNodeMeta;
     }
     ```
  2. Export additional interfaces as needed for API payloads (e.g., `MoveRequest`, `RenameRequest`).
- **Dependencies:** Backend model from Task 1.6.

**Task 2.7 – Set up `react-query` client and query keys (Must-have)**
- **Goal:** Centralize data fetching patterns.
- **Actions:**
  1. Create `api/client.ts` configuring base URL and axios/fetch instance.
  2. Wrap app with `QueryClientProvider` in `main.tsx`.
  3. Define query keys, e.g., `['explorer', 'tree']`, `['notes', noteId]`.
  4. Implement basic hooks, e.g., `useExplorerTree` that calls `GET /api/explorer/tree`.
- **Dependencies:** Task 2.3, 2.4.

**Task 2.8 – Design zustand store for explorer UI state (Must-have)**
- **Goal:** Keep view-related state consistent across components.
- **Actions:**
  1. Create `stores/useExplorerStore.ts` with state including:
     - `selectedIds: string[]`
     - `activeNodeId: string | null`
     - `expandedIds: Set<string>` or array
     - `viewMode: 'grid' | 'list'`
     - `clipboard: { nodeIds: string[]; mode: 'cut' | 'copy' | null }`
     - `currentPath: FileSystemNode[]` (for breadcrumbs)
  2. Add actions: `select`, `toggleSelect`, `rangeSelect`, `setViewMode`, `expand`, `collapse`, `setActiveNode`, `setClipboard`.
- **Dependencies:** Task 2.6.


### 4.4 Base UI Components

**Task 2.9 – Implement layout components (Must-have)**
- **Goal:** Provide a consistent shell around explorer content.
- **Actions:**
  1. In `components/layout/MainLayout.tsx`, render:
     - A sidebar area for tree.
     - A header area for breadcrumbs and actions.
     - A content area for grid/list view.
  2. Use Tailwind-based responsive layout (e.g., flexbox with fixed-width sidebar).
- **Dependencies:** Task 2.4.

**Task 2.10 – Create reusable UI primitives (Must-have)**
- **Goal:** Wrap `shadcn/ui` primitives or define basic ones.
- **Actions:**
  1. Implement buttons, inputs, dialogs, context menus within `components/ui/`.
  2. Ensure consistent styling and theming.
- **Dependencies:** Task 2.3.

**Task 2.11 – Wire basic ExplorerPage with fake data (Must-have)**
- **Goal:** Validate layout and interaction patterns before wiring to real API.
- **Actions:**
  1. Create `pages/ExplorerPage.tsx` using `MainLayout`.
  2. Use hard-coded mock tree data to render sidebar, breadcrumb, and main view.
  3. Implement initial selection behavior and view mode toggle using zustand.
- **Dependencies:** Task 2.8, 2.9, 2.10.


## 5. Phase 3: Explorer Interface

Goal: Implement the full explorer UX, including layout, interactions, and core operations.

### 5.1 Layout & Navigation

**Task 3.1 – Sidebar tree component (Must-have)**
- **Goal:** Render the full hierarchy as a collapsible tree.
- **Actions:**
  1. Implement `SidebarTree` in `components/explorer/SidebarTree.tsx`.
  2. Use recursive rendering or a flat list with indentation.
  3. Integrate with zustand store for expanded/collapsed state.
  4. Highlight the currently active node; clicking a node updates `activeNodeId` and `currentPath`.
- **Dependencies:** Task 2.6, 2.8, 2.7.

**Task 3.2 – Breadcrumb navigation (Must-have)**
- **Goal:** Show the path from root to the active node and allow quick navigation.
- **Actions:**
  1. Implement `Breadcrumbs` in `components/explorer/Breadcrumbs.tsx`.
  2. Use `currentPath` from store to render segments.
  3. Clicking a breadcrumb segment sets `activeNodeId` to that node and updates tree selection.
- **Dependencies:** Task 2.8, 3.1.

**Task 3.3 – Main panel grid/list views (Must-have)**
- **Goal:** Display children of the active node as either icons (grid) or rows (list).
- **Actions:**
  1. Implement `GridView` and `ListView` components.
  2. Show key attributes: label, type, note count, updated time, processing status.
  3. Connect to `viewMode` state in store and add a toggle in the header.
  4. Support responsive layout for different screen sizes.
- **Dependencies:** Task 2.8, 2.6, 2.7.


### 5.2 Selection Model & Keyboard Navigation

**Task 3.4 – Mouse-based selection (Must-have)**
- **Goal:** Provide intuitive single, multi, and range selection.
- **Actions:**
  1. In grid/list items, implement click handlers that:
     - Single click without modifier: select the clicked node only.
     - Ctrl/Cmd+click: toggle selection of one node without clearing others.
     - Shift+click: select a continuous range between last active node and clicked node.
  2. Store selection in `selectedIds` and `activeNodeId` in zustand.
  3. Use CSS classes to visually indicate selected and active items.
- **Dependencies:** Task 2.8, 3.3.

**Task 3.5 – Optional keyboard navigation (Nice-to-have)**
- **Goal:** Allow arrow-key navigation similar to desktop explorers.
- **Actions:**
  1. Add key handlers for arrow keys, Enter, and Space when main panel is focused.
  2. Move the active selection with arrows; Enter opens node (navigate into folder or open note).
- **Dependencies:** Task 3.4.
- **Notes:** Can be deferred if time-constrained.


### 5.3 Context Menus

**Task 3.6 – Define context menu options by node type (Must-have)**
- **Goal:** Clearly specify actions available for each node type.
- **Menu matrix:**

  | Node Type  | Actions                                                                 |
  |-----------|-------------------------------------------------------------------------|
  | Department| Open, Rename, Delete, New Semester                                     |
  | Semester  | Open, Rename, Delete, New Subject                                      |
  | Subject   | Open, Rename, Delete, New Module                                       |
  | Module    | Open, Rename, Delete, New Note                                         |
  | Note      | Open (preview), Download PDF, Rename, Delete, Regenerate (if supported) |

- **Actions:**
  1. Implement `ContextMenu` components using `shadcn/ui` or Radix.
  2. Wire right-click handlers in both sidebar and main panel to open menus.
  3. Dispatch actions to the appropriate API calls (rename, delete, create child, etc.).
- **Dependencies:** Task 1.8–1.11, 2.10.


### 5.4 Drag-and-Drop Reorganization

**Task 3.7 – Implement drag source and drop targets (Must-have)**
- **Goal:** Allow moving nodes via drag-and-drop while enforcing hierarchy rules.
- **Actions:**
  1. Integrate `@dnd-kit/core` into grid/list and tree.
  2. Make each node draggable.
  3. Define droppable areas for valid target nodes.
- **Dependencies:** Task 2.3, 2.8, 2.6.

**Task 3.8 – Enforce move rules and UX feedback (Must-have)**
- **Goal:** Ensure users cannot perform illegal moves and receive clear feedback.
- **Allowed moves (examples):**
  - Semester → another Department
  - Subject → another Semester
  - Module → another Subject
  - Note → another Module

  **Disallowed:**
  - Moving a parent into its child subtree.
  - Moving modules into notes, etc.

- **Actions:**
  1. Implement frontend validation based on node `type` and `parentId`.
  2. During drag, visually indicate allowed vs disallowed targets (e.g., green highlight vs red cross).
  3. On drop:
     - If allowed, call backend move endpoint (Task 1.9) and optimistically update UI.
     - If backend rejects move, revert UI and show error toast.
- **Dependencies:** Task 1.9, 3.7.


### 5.5 CRUD Operations & Search

**Task 3.9 – Creation dialogs (Must-have)**
- **Goal:** Allow users to create new departments, semesters, subjects, modules, and notes from the explorer.
- **Actions:**
  1. Implement `NewItemDialog` that adapts fields based on context (type being created).
  2. Required fields:
     - Department: name.
     - Semester: name, parent department.
     - Subject: name, parent semester.
     - Module: name, parent subject.
     - Note: name/title, parent module, plus any upload/metadata fields (if applicable).
  3. Pre-fill parent based on current selection/path.
  4. On submit, call corresponding create endpoint and refresh tree.
- **Dependencies:** Task 1.8, 3.6.

**Task 3.10 – Rename flow (Must-have)**
- **Goal:** Support renaming from both context menus and inline editing.
- **Actions:**
  1. Provide a rename dialog or inline edit field.
  2. On save, call rename endpoint and update local state.
- **Dependencies:** Task 1.10.

**Task 3.11 – Delete flow (Must-have)**
- **Goal:** Provide safe, confirmable deletion from explorer.
- **Actions:**
  1. Trigger confirmation dialog with clear description of impact (especially cascades).
  2. Optionally call delete endpoint in `dry_run` mode to show impact summary.
  3. On confirm, perform deletion, update tree, and clear selection of deleted nodes.
- **Dependencies:** Task 1.11.

**Task 3.12 – Search within current folder (Must-have)**
- **Goal:** Allow quick filtering of children of the active node.
- **Actions:**
  1. Add a search input in header.
  2. Filter displayed children client-side by label and optionally type.
  3. Highlight matches.
- **Dependencies:** Task 3.3.

**Task 3.13 – Optional global search (Nice-to-have)**
- **Goal:** Provide a cross-hierarchy search experience.
- **Actions:**
  1. Either implement client-side search over full tree data or define a new backend search endpoint.
  2. Display results in a separate panel or overlay.
- **Dependencies:** Task 1.7, 2.7.


### 5.6 PDF Preview and Status Indicators

**Task 3.14 – Open and download notes (Must-have)**
- **Goal:** Allow users to view/download PDFs from explorer.
- **Actions:**
  1. In note context menu, "Open" opens PDF in new tab using constructed URL from Task 1.5.
  2. "Download" either uses same URL or `download` attribute to force download.
- **Dependencies:** Task 1.4, 1.5.

**Task 3.15 – Show processing state and errors (Must-have)**
- **Goal:** Reflect long-running operations status in the UI.
- **Actions:**
  1. Use `meta.processing` or status endpoint to display badges (e.g., "Processing", "Error").
  2. Periodically poll status endpoint for notes that are not yet `complete`.
  3. Update list/grid items optimistically when operations are triggered (e.g., show a placeholder note while PDF is generating).
- **Dependencies:** Task 1.13, 2.7.


## 6. Phase 4: Migration & Integration

Goal: Run Streamlit and React side-by-side, validate parity, and then promote React as the primary interface.

### 6.1 Dual-Run Strategy

**Task 4.1 – Configure parallel dev environment (Must-have)**
- **Goal:** Allow developers to run both UIs against the same backend/DB.
- **Actions:**
  1. Document dev commands:
     - Start FastAPI backend.
     - Start Streamlit app on port 8501.
     - Start React dev server on port 5173.
  2. Confirm both UIs operate correctly against the same database and API.
- **Dependencies:** Phase 1–3 backend capabilities for explorer.

**Task 4.2 – Define functional parity checklist (Must-have)**
- **Goal:** Ensure React explorer can fully replace core Streamlit flows.
- **Actions:**
  1. List core operations from existing Streamlit explorer:
     - Navigating hierarchy.
     - Creating/editing/deleting nodes.
     - Generating/viewing PDFs.
  2. Create a test matrix mapping each operation to equivalent React flow.
  3. Use this matrix for manual QA during migration.
- **Dependencies:** Tasks 3.1–3.15.


### 6.2 Build, Deploy, and Routing

**Task 4.3 – Build React app (Must-have)**
- **Goal:** Produce static assets for deployment.
- **Actions:**
  1. Run `npm run build` in `/frontend`.
  2. Verify output in `/frontend/dist` looks correct (index.html, assets).
- **Dependencies:** Phase 2 completion.

**Task 4.4 – Serve React app via FastAPI (Must-have)**
- **Goal:** Expose built React app from the backend server.
- **Actions:**
  1. Configure FastAPI (or an ASGI middleware) to serve static files from the React build directory, e.g., `/static/frontend`.
  2. Route root path `/` (and possibly `/explorer`) to serve `index.html` from the build directory.
  3. Ensure existing API routes continue to function unhindered under `/api`.
- **Dependencies:** Task 4.3.

**Task 4.5 – Client-side routing fallback (Must-have)**
- **Goal:** Ensure that refreshing deep links in React app still works.
- **Actions:**
  1. Configure FastAPI (or reverse proxy) so unknown non-API paths (not starting with `/api` or `/static`) serve `index.html`.
  2. Validate that navigating directly to, e.g., `/explorer/module/123` works both from SPA navigation and browser refresh.
- **Dependencies:** Task 4.4.


### 6.3 Rollout & Feature Flags

**Task 4.6 – Implement environment-based toggle between UIs (Nice-to-have)**
- **Goal:** Allow gradual rollout of React explorer.
- **Actions:**
  1. Decide on rollout strategy, e.g.:
     - `/` → React explorer, `/streamlit` → legacy UI.
     - Or env var `USE_REACT_EXPLORER` controlling default landing page.
  2. Implement simple redirect or link from legacy UI to React explorer.
  3. Document how to switch default in ops documentation.
- **Dependencies:** Task 4.4.

**Task 4.7 – Plan deprecation of Streamlit explorer (Nice-to-have)**
- **Goal:** Define criteria and steps for fully retiring Streamlit.
- **Actions:**
  1. Set deprecation milestones based on parity checklist from Task 4.2.
  2. Once criteria are met, update documentation to point users to React explorer.
  3. Plan removal or archiving of Streamlit explorer-related files in a later cleanup phase.
- **Dependencies:** Task 4.2.


## 7. Risks, Edge Cases, and Mitigations

### 7.1 Data Consistency During Moves

- **Risk:** Invalid or partial move operations corrupt hierarchy (e.g., orphaned nodes, cycles).
- **Mitigations:**
  - Strict backend validation of allowed parent/child relationships (Task 1.9).
  - Database constraints where possible (foreign keys).
  - Use transactions to ensure move is atomic.
  - Provide clear error messages for invalid moves and do not update UI on failure.
- **Testing/Verification:**
  - Unit tests for move logic.
  - Manual tests for edge cases: moving across multiple levels, rapid consecutive moves.

### 7.2 Backward Compatibility with Existing Notes and PDFs

- **Risk:** React app can’t find older PDFs or misinterprets legacy metadata.
- **Mitigations:**
  - Keep PDF filenames and paths stable when moving to static serving (Task 1.4, 1.5).
  - Ensure explorer node model gracefully handles missing optional fields for legacy data.
  - If necessary, add a one-time migration script to normalize metadata.
- **Testing/Verification:**
  - Use a snapshot of current DB and `pdfs/` directory to test explorer.
  - Verify that a random sample of existing notes can be opened from React.

### 7.3 Performance with Large Hierarchies

- **Risk:** Full-tree responses or heavy client-side rendering cause slow initial load.
- **Mitigations:**
  - Implement depth-limited or lazy-loaded tree fetching (Task 1.7).
  - Use virtualization for large lists/grids if needed.
  - Memoize derived data (e.g., children arrays) and avoid unnecessary re-renders.
- **Testing/Verification:**
  - Load test with synthetic hierarchies of expected max size.
  - Measure initial load time and interactions in browser dev tools.

### 7.4 Long-Running PDF/Transcription Jobs

- **Risk:** Users think the app is frozen or retry operations, causing duplicates.
- **Mitigations:**
  - Clear progress and status indicators in the UI (Task 3.15).
  - Disable duplicate-triggering actions while a job is in progress.
  - Provide retry flows only when an error is explicit.
- **Testing/Verification:**
  - Simulate long-running operations in a dev environment.
  - Validate UX under slow network conditions.

### 7.5 Incomplete Parity with Streamlit

- **Risk:** Some critical flows work only in Streamlit, leading to confusion.
- **Mitigations:**
  - Maintain and use the parity checklist (Task 4.2).
  - Until parity is achieved, clearly label the React explorer as beta in UI (e.g., banner).
- **Testing/Verification:**
  - Conduct UAT sessions with current Streamlit users.
  - Track gaps as explicit tasks before deprecating Streamlit.


## 8. Suggested Milestones and Rough Ordering

This section groups tasks into milestones that can map to sprints or epics.

### Milestone 1 – Backend Foundations

- Complete Tasks 1.1–1.5 (CORS and static PDFs).
- Implement basic explorer node model and tree endpoint: Tasks 1.6–1.7.
- Map CRUD operations and implement move/rename/delete where not already present: Tasks 1.8–1.11.
- Outcome: Backend is ready to support basic explorer UI and PDF access.

### Milestone 2 – React Skeleton & Mock Explorer

- Initialize React project and Tailwind: Tasks 2.1–2.3.
- Establish directory structure and routing: Tasks 2.4–2.5.
- Define core types, stores, and react-query setup: Tasks 2.6–2.8.
- Build layout and UI primitives; display mock explorer data: Tasks 2.9–2.11.
- Outcome: Fully functional mock explorer UI with correct layout and core interactions, not yet wired to API.

### Milestone 3 – Explorer v1 Wired to Backend

- Connect explorer UI to real API endpoints for tree and CRUD: integrate Tasks 1.7–1.11 with Tasks 3.1–3.13.
- Implement sidebar tree, breadcrumbs, grid/list views, selection, context menus, and drag-and-drop.
- Implement creation, rename, delete, and folder-level search.
- Outcome: Explorer provides end-to-end functionality for hierarchy management and PDF access.

### Milestone 4 – Status Handling & UX Polish

- Implement status APIs and UI indicators: Tasks 1.12–1.13, 3.15.
- Optional: Add keyboard navigation, global search, and realtime design outline: Tasks 1.14, 3.5, 3.13.
- Refine performance for large hierarchies and optimize rendering.
- Outcome: Explorer is robust, responsive, and ready for wider user testing.

### Milestone 5 – Migration, Deployment, and Streamlit Rollback Plan

- Configure dual-run environment and parity checklist: Tasks 4.1–4.2.
- Build and serve React app via FastAPI with routing fallback: Tasks 4.3–4.5.
- Implement rollout toggles and plan Streamlit deprecation: Tasks 4.6–4.7.
- Outcome: React explorer can become the primary UI with controlled rollout and a clear path for retiring Streamlit once parity is confirmed.

---

This plan covers all phases and key ideas from `MIGRATION_PLAN.md`, expanding them into detailed, implementable tasks with dependencies, priorities, and risk considerations, suitable for turning into tickets and scheduling across multiple sprints.