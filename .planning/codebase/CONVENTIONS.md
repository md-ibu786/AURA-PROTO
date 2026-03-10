# Coding Conventions

**Analysis Date:** 2026-03-10

## Naming Patterns

**Files:**
- Frontend feature files use `UpperCamelCase.tsx` for components and pages such as `frontend/src/pages/LoginPage.tsx`, `frontend/src/components/ui/WarningDialog.tsx`, and `frontend/src/features/kg/components/ProcessDialog.tsx`.
- Frontend hooks and Zustand stores use `useX.ts` naming such as `frontend/src/stores/useAuthStore.ts`, `frontend/src/stores/useExplorerStore.ts`, and `frontend/src/hooks/useMobileBreakpoint.ts`.
- Frontend test files are usually colocated as `*.test.ts(x)` such as `frontend/src/api/client.test.ts`, `frontend/src/pages/ExplorerPage.test.tsx`, and `frontend/src/components/explorer/__tests__/ListView.test.tsx`.
- Backend application and test modules use `snake_case.py` such as `api/auth.py`, `api/hierarchy_crud.py`, `tests/test_auth_sync.py`, and `api/tests/test_rbac.py`.

**Functions:**
- TypeScript functions use `lowerCamelCase` for helpers and exported APIs, for example `getExplorerTree()` in `frontend/src/api/explorerApi.ts`, `initAuthListener()` in `frontend/src/stores/useAuthStore.ts`, and `handleCreateSubmit()` in `frontend/src/components/explorer/GridView.tsx`.
- React components are declared with `UpperCamelCase` function names such as `ProtectedRoute` in `frontend/src/components/ProtectedRoute.tsx` and `LoginPage` in `frontend/src/pages/LoginPage.tsx`.
- Python functions use `snake_case`, including dependencies and helpers like `verify_firebase_token()` in `api/auth.py`, `readiness_check()` in `api/main.py`, and `_make_user()` in `api/tests/test_rbac.py`.

**Variables:**
- Frontend variables and props use `lowerCamelCase`, including state like `renameValue` in `frontend/src/components/explorer/GridView.tsx` and `currentPath` in `frontend/src/stores/useExplorerStore.ts`.
- Backend local variables and constants mix `snake_case` and uppercase constants, for example `decoded_token` in `api/auth.py`, `PROJECT_ID` in `frontend/src/tests/firestore.rules.test.ts`, and `DEFAULT_TIMESTAMP` in `frontend/src/tests/firestore.rules.test.ts`.
- Request and response payload keys mirror backend/API field names rather than being normalized everywhere; frontend code uses both camelCase UI keys and snake_case API keys in files like `frontend/src/api/explorerApi.ts` and `frontend/src/stores/useAuthStore.ts`.

**Types:**
- TypeScript domain types use `UpperCamelCase` interfaces and aliases such as `FileSystemNode`, `BlobResponse`, `AuthUser`, and `HierarchyType` in `frontend/src/types/FileSystemNode.ts` and `frontend/src/api/client.ts`.
- Python schema types use `PascalCase` Pydantic models and `Literal` aliases such as `FirestoreUser`, `CreateUserInput`, `UserRole`, and `UserStatus` in `api/models.py`.

## Code Style

**Formatting:**
- Frontend formatting is enforced primarily by ESLint in `frontend/eslint.config.js`; there is no Prettier or Biome config detected.
- Style is semicolon-heavy in many frontend files such as `frontend/src/stores/useAuthStore.ts` and `frontend/src/api/client.ts`, but some entry files like `frontend/src/main.tsx` and `frontend/src/App.tsx` omit semicolons, so formatting is not fully uniform.
- Python files follow standard 4-space indentation and docstring-heavy style in `api/auth.py`, `api/main.py`, and `api/tests/test_rbac.py`.

**Linting:**
- Frontend uses ESLint 9 flat config in `frontend/eslint.config.js` with `@eslint/js`, `typescript-eslint`, `eslint-plugin-react-hooks`, and `eslint-plugin-react-refresh`.
- Ignored output directories are `dist` and `coverage` in `frontend/eslint.config.js`.
- The only explicit custom rule detected is `react-refresh/only-export-components` in `frontend/eslint.config.js`; other rules come from recommended presets.

## Import Organization

**Order:**
1. External packages first, for example React, router, query, and icon imports in `frontend/src/pages/ExplorerPage.tsx`.
2. Internal app modules second, grouped by store/api/component/type usage as seen in `frontend/src/pages/ExplorerPage.tsx` and `frontend/src/components/ProtectedRoute.tsx`.
3. Type-only imports usually come last or near related imports, for example `import type { FileSystemNode }` in `frontend/src/pages/ExplorerPage.tsx` and `import type { ProcessingRequest }` in `frontend/src/features/kg/hooks/useKGProcessing.ts`.

**Path Aliases:**
- Vite defines the `@` alias in `frontend/vite.config.ts`, but current source files mostly use relative imports; no active `@/...` imports were detected in `frontend/src`.

## Error Handling

**Patterns:**
- Frontend API access is funneled through typed wrappers in `frontend/src/api/client.ts`; callers generally catch `DuplicateError` for conflict handling and fall back to `Error` for generic failures.
- UI components often branch on `instanceof api.DuplicateError` and otherwise log and surface alerts, as in `frontend/src/components/explorer/GridView.tsx` and `frontend/src/components/explorer/SidebarTree.tsx`.
- Auth code translates Firebase error codes into user-facing messages in `frontend/src/stores/useAuthStore.ts` and stores the message in Zustand state instead of throwing custom UI exceptions.
- Backend request handlers prefer `raise HTTPException(...)` for request/permission failures, visible throughout `api/auth.py`, `api/main.py`, and `api/hierarchy_crud.py`.
- Backend utility code commonly wraps external service calls in `try/except` and either logs or rethrows HTTP errors, such as token verification in `api/auth.py` and readiness checks in `api/main.py`.

## Logging

**Framework:** `console` on the frontend, Python `logging`/module `logger` on the backend

**Patterns:**
- Frontend uses `console.error`, `console.warn`, and occasional `console.log` in runtime code, for example `frontend/src/stores/useAuthStore.ts`, `frontend/src/api/client.ts`, and `frontend/src/pages/ExplorerPage.tsx`.
- Backend modules create or reuse module loggers, for example `logger = logging.getLogger(__name__)` in `api/main.py`, and log operational failures before returning or raising.
- Tests occasionally patch logger objects directly, as in `tests/test_kg_router_delete.py`, to assert warning and critical paths.

## Comments

**When to Comment:**
- Large frontend and backend source files often start with required file headers describing purpose, role, dependencies, and usage, for example `frontend/src/api/client.ts`, `frontend/src/stores/useExplorerStore.ts`, and `api/main.py`.
- Inline comments are used to explain state-machine or permission behavior rather than trivial code, such as the student/staff routing notes in `frontend/src/pages/ExplorerPage.tsx` and mock/real auth branching in `frontend/src/stores/useAuthStore.ts`.
- Some files still use lightweight banner or inline comment styles instead of the longer template, such as `frontend/e2e/explorer.spec.ts`, `frontend/e2e/health.spec.ts`, and `tests/test_kg_router_delete.py`.

**JSDoc/TSDoc:**
- Frontend source leans on block headers plus occasional function comments rather than per-function TSDoc.
- Backend test and model files frequently use Python docstrings on modules, classes, and helper methods, especially in `api/tests/test_rbac.py` and `api/models.py`.

## Function Design

**Size:**
- Small focused wrappers are common in API modules like `frontend/src/api/explorerApi.ts`.
- State-heavy files centralize many actions in one module, especially `frontend/src/stores/useExplorerStore.ts` and `frontend/src/stores/useAuthStore.ts`, so large single-file stores are an accepted pattern.
- Backend endpoint files can be very large and multi-purpose, for example `api/main.py` and `api/hierarchy_crud.py`.

**Parameters:**
- TypeScript function parameters are usually explicitly typed, including callback parameters in hooks and store actions in `frontend/src/features/kg/hooks/useKGProcessing.ts` and `frontend/src/stores/useExplorerStore.ts`.
- Python public helpers usually type annotate parameters and return values in newer files like `api/tests/test_rbac.py`; older scripts/tests such as `api/test_mock_firestore.py` are less strict.

**Return Values:**
- Frontend API functions usually return typed promises such as `Promise<FileSystemNode[]>` or `Promise<BlobResponse>` from `frontend/src/api/explorerApi.ts` and `frontend/src/api/client.ts`.
- Zustand stores expose computed permissions as functions returning booleans in `frontend/src/stores/useAuthStore.ts` instead of storing duplicated booleans.
- Backend dependencies typically return Pydantic models such as `FirestoreUser` from `api/auth.py`.

## Module Design

**Exports:**
- Most utility and store modules use named exports, for example `frontend/src/api/explorerApi.ts`, `frontend/src/stores/index.ts`, `frontend/src/components/ProtectedRoute.tsx`, and `frontend/src/features/kg/hooks/useKGProcessing.ts`.
- The page shell still uses default exports for app and page components in `frontend/src/App.tsx`, `frontend/src/pages/ExplorerPage.tsx`, `frontend/src/pages/LoginPage.tsx`, and `frontend/src/pages/AdminDashboard.tsx`; follow the local file pattern when editing those files.

**Barrel Files:**
- Barrel files are used sparingly for shared surfaces, such as `frontend/src/types/index.ts`, `frontend/src/stores/index.ts`, `frontend/src/api/index.ts`, and `frontend/src/components/layout/index.ts`.
- Internal feature modules still commonly import relative leaf modules directly rather than going through a barrel, especially under `frontend/src/features/kg/` and `frontend/src/components/explorer/`.

## State Management Patterns

- Use Zustand for client/UI state in `frontend/src/stores/useExplorerStore.ts` and authentication/session state in `frontend/src/stores/useAuthStore.ts`.
- Use TanStack Query for server state, caching, and invalidation in `frontend/src/main.tsx`, `frontend/src/pages/ExplorerPage.tsx`, `frontend/src/components/explorer/GridView.tsx`, and `frontend/src/features/kg/hooks/useKGProcessing.ts`.
- Keep auth persistence in browser storage only for mock mode; `localStorage` usage is limited to `frontend/src/stores/useAuthStore.ts` and Playwright helpers in `frontend/e2e/fixtures.ts`.
- When mutating server state from components, refetch or invalidate query keys like `['explorer', 'tree']` or `['kg', 'queue']` rather than manually mutating deep tree objects, as seen in `frontend/src/components/explorer/GridView.tsx` and `frontend/src/features/kg/hooks/useKGProcessing.ts`.

---

*Convention analysis: 2026-03-10*
