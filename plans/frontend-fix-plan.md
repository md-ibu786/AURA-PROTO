# Frontend Architecture Fix Plan — AURA-NOTES-MANAGER

**Generated:** 2026-05-24  
**Source:** `reviews/frontend-architecture-review.md`  
**Scope:** All 21 findings (2 Critical, 6 High, 8 Medium, 5 Low)

---

## Overview

| Item | Detail |
|------|--------|
| **Total findings** | 21 (2C, 6H, 8M, 5L) |
| **Files to modify** | 12 existing files |
| **Files to create** | 3 new files (ErrorBoundary, admin-dashboard.css, login-page.css) |
| **Estimated effort** | 6 fix groups, ~25–30 discrete edits |
| **Risk level** | Medium — largest change is AdminDashboard decomposition |

### Affected Files Summary

| File | Findings | Severity |
|------|----------|----------|
| `App.tsx` | C1, H5 | Critical, High |
| `main.tsx` | C1 | Critical |
| `stores/index.ts` | H4 | High |
| `stores/useAuthStore.ts` | H6 | High |
| `stores/useExplorerStore.ts` | M7 | Medium |
| `pages/AdminDashboard.tsx` | H1, H2, H3, M1, M4, M6 | High ×3, Medium ×3 |
| `pages/ExplorerPage.tsx` | C2, M5, L5 | Critical, Medium, Low |
| `pages/LoginPage.tsx` | H3, H5, M8 | High ×2, Medium |
| `pages/UsagePage.tsx` | M2 | Medium |
| `components/layout/Header.tsx` | C2, M3 | Critical, Medium |
| `components/layout/Sidebar.tsx` | C2, L4 | Critical, Low |
| `components/LoadingSpinner.tsx` | L2 | Low |
| `components/explorer/SelectionActionBar.tsx` | (confirm replacement) | High |

---

## Prerequisites

1. **Verify zustand 5.x**: `package.json` shows `"zustand": "^5.0.2"`. Confirm `useShallow` is available at `zustand/react/shallow` (it is in 5.x).
2. **Root venv activated**: All Python tasks use `../../.venv`.
3. **No other branches**: Ensure clean working tree before starting.
4. **Run baseline tests**: `cd frontend && npm run build && npm test` to confirm green baseline.
5. **Verify sonner is configured**: Confirmed — `App.tsx` line 46: `<Toaster position="bottom-right" richColors closeButton />`.

---

## Fix Groups

### Group 1: App Shell Safety Net (C1, L2)

**Rationale:** The app has zero error boundaries. Any render crash produces a white screen with no recovery. This is the highest-impact, lowest-effort fix. LoadingSpinner also needs basic accessibility.

#### 1a. Create `ErrorBoundary` component

- **File to create:** `frontend/src/components/ErrorBoundary.tsx`
- **Current code:** Does not exist.
- **New code:** Copy the pattern from `AURA-CHAT/client/src/components/ErrorBoundary.tsx` (class component with `getDerivedStateFromError`, `componentDidCatch`, retry button). Adapt to match AURA-NOTES-MANAGER styling.
- **Key design decisions:**
  - Use Tailwind utility classes (consistent with SettingsPage, AdminHeader)
  - Include `RefreshCw` retry button
  - Log to `console.error` in `componentDidCatch`
  - Accept optional `fallback` prop for per-route customization

```tsx
// frontend/src/components/ErrorBoundary.tsx
import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
    state: State = { hasError: false, error: null };

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('ErrorBoundary caught:', error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) return this.props.fallback;

            return (
                <div className="min-h-screen flex items-center justify-center bg-primary-theme p-4">
                    <div className="text-center space-y-4 max-w-md">
                        <AlertCircle className="w-12 h-12 text-destructive mx-auto" />
                        <h2 className="text-xl font-bold text-primary">Something went wrong</h2>
                        <p className="text-secondary text-sm">{this.state.error?.message}</p>
                        <button
                            onClick={() => this.setState({ hasError: false, error: null })}
                            className="btn btn-primary inline-flex items-center gap-2"
                        >
                            <RefreshCw className="w-4 h-4" />
                            Try again
                        </button>
                    </div>
                </div>
            );
        }
        return this.props.children;
    }
}
```

- **Validation:** Import and render `<ErrorBoundary><div>test</div></ErrorBoundary>` in a test — verify child renders. Throw in child — verify fallback shows.

#### 1b. Wrap app routes in ErrorBoundary

- **File:** `frontend/src/App.tsx`
- **Current code (lines 46–67):**
  ```tsx
  <BrowserRouter>
      <Toaster ... />
      <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/admin" element={...} />
          ...
      </Routes>
  </BrowserRouter>
  ```
- **New code:**
  ```tsx
  <BrowserRouter>
      <Toaster position="bottom-right" richColors closeButton />
      <ErrorBoundary>
          <Routes>
              <Route path="/login" element={
                  <ErrorBoundary>
                      <LoginPage />
                  </ErrorBoundary>
              } />
              <Route path="/admin" element={
                  <ProtectedRoute requiredRole="admin">
                      <ErrorBoundary>
                          <AdminDashboard />
                      </ErrorBoundary>
                  </ProtectedRoute>
              } />
              <Route path="/settings" element={
                  <ProtectedRoute requiredRole="admin">
                      <ErrorBoundary>
                          <SettingsPage />
                      </ErrorBoundary>
                  </ProtectedRoute>
              } />
              <Route path="/usage" element={
                  <ProtectedRoute requiredRole="admin">
                      <ErrorBoundary>
                          <UsagePage />
                      </ErrorBoundary>
                  </ProtectedRoute>
              } />
              <Route path="/*" element={
                  <ProtectedRoute>
                      <ErrorBoundary>
                          <ExplorerPage />
                      </ErrorBoundary>
                  </ProtectedRoute>
              } />
          </Routes>
      </ErrorBoundary>
  </BrowserRouter>
  ```
- **Add import:** `import { ErrorBoundary } from './components/ErrorBoundary'`
- **Validation:** `npm run build` — no type errors. Manually test by throwing in a component — verify fallback renders instead of white screen.

#### 1c. Add accessibility to LoadingSpinner

- **File:** `frontend/src/components/LoadingSpinner.tsx`
- **Current code (lines 29–38):**
  ```tsx
  <div className="min-h-screen flex items-center justify-center bg-primary-theme">
      <div className="flex flex-col items-center gap-4">
          <div className="animate-spin ..." />
          <p className="text-secondary font-medium">Loading...</p>
      </div>
  </div>
  ```
- **New code:**
  ```tsx
  <div role="status" aria-live="polite" className="min-h-screen flex items-center justify-center bg-primary-theme">
      <div className="flex flex-col items-center gap-4">
          <div className="animate-spin ..." />
          <p className="text-secondary font-medium">Loading...</p>
      </div>
  </div>
  ```
- **Change:** Add `role="status"` and `aria-live="polite"` to the outer `<div>`.
- **Validation:** Inspect in browser dev tools — verify `role="status"` present. Screen reader should announce "Loading..." when spinner appears.

---

### Group 2: Zustand Store Hardening (C2, H4, H6, M7)

**Rationale:** Every component subscribing to `useExplorerStore()` without a selector re-renders on *any* store change. This is the root cause of sluggish interactions (typing in search, toggling selection mode, opening context menus). The auth store has the same issue. Barrel export and timeout cleanup are bundled here since they're all store-layer concerns.

**Dependency:** None. Independent of Group 1.

#### 2a. Add `useShallow` selectors to `Header.tsx`

- **File:** `frontend/src/components/layout/Header.tsx`
- **Current code (lines 48–60):**
  ```tsx
  const {
      currentPath, navigateUp, setCurrentPath,
      viewMode, setViewMode, searchQuery, setSearchQuery,
      setActiveNode, selectionMode, setSelectionMode,
      setDeleteMode, setMobileMenuOpen,
  } = useExplorerStore();
  ```
- **New code:**
  ```tsx
  import { useShallow } from 'zustand/react/shallow';
  // ... (add to existing import block)

  const {
      currentPath, navigateUp, setCurrentPath,
      viewMode, setViewMode, searchQuery, setSearchQuery,
      setActiveNode, selectionMode, setSelectionMode,
      setDeleteMode, setMobileMenuOpen,
  } = useExplorerStore(useShallow(s => ({
      currentPath: s.currentPath,
      navigateUp: s.navigateUp,
      setCurrentPath: s.setCurrentPath,
      viewMode: s.viewMode,
      setViewMode: s.setViewMode,
      searchQuery: s.searchQuery,
      setSearchQuery: s.setSearchQuery,
      setActiveNode: s.setActiveNode,
      selectionMode: s.selectionMode,
      setSelectionMode: s.setSelectionMode,
      setDeleteMode: s.setDeleteMode,
      setMobileMenuOpen: s.setMobileMenuOpen,
  })));
  ```
- **Validation:** `npm run build`. Manual: open explorer, type in search box, verify Sidebar does not flash.

#### 2b. Add `useShallow` selectors to `Sidebar.tsx`

- **File:** `frontend/src/components/layout/Sidebar.tsx`
- **Current code (line 44):**
  ```tsx
  const { currentPath, startCreating, mobileMenuOpen, setMobileMenuOpen } = useExplorerStore();
  ```
- **New code:**
  ```tsx
  import { useShallow } from 'zustand/react/shallow';

  const { currentPath, startCreating, mobileMenuOpen, setMobileMenuOpen } = useExplorerStore(
      useShallow(s => ({
          currentPath: s.currentPath,
          startCreating: s.startCreating,
          mobileMenuOpen: s.mobileMenuOpen,
          setMobileMenuOpen: s.setMobileMenuOpen,
      }))
  );
  ```
- **Validation:** `npm run build`.

#### 2c. Add `useShallow` selectors to `ExplorerPage.tsx`

- **File:** `frontend/src/pages/ExplorerPage.tsx`
- **Current code (lines 39–48):**
  ```tsx
  const {
      viewMode, currentPath, contextMenuPosition,
      closeContextMenu, creatingNodeType, deleteDialogOpen,
      nodeToDelete, closeDeleteDialog, navigateTo
  } = useExplorerStore();
  ```
- **New code:**
  ```tsx
  import { useShallow } from 'zustand/react/shallow';

  const {
      viewMode, currentPath, contextMenuPosition,
      closeContextMenu, creatingNodeType, deleteDialogOpen,
      nodeToDelete, closeDeleteDialog, navigateTo
  } = useExplorerStore(useShallow(s => ({
      viewMode: s.viewMode,
      currentPath: s.currentPath,
      contextMenuPosition: s.contextMenuPosition,
      closeContextMenu: s.closeContextMenu,
      creatingNodeType: s.creatingNodeType,
      deleteDialogOpen: s.deleteDialogOpen,
      nodeToDelete: s.nodeToDelete,
      closeDeleteDialog: s.closeDeleteDialog,
      navigateTo: s.navigateTo,
  })));
  ```
- **Also fix auth store selector (H6)** — replace:
  ```tsx
  const { user, isAdmin } = useAuthStore();
  ```
  with:
  ```tsx
  const user = useAuthStore(s => s.user);
  const isAdmin = useAuthStore(s => s.isAdmin);
  ```
- **Validation:** `npm run build`. Manual: navigate explorer, verify no unnecessary re-renders.

#### 2d. Fix auth store selectors across all consumers (H6)

Every file that destructures `useAuthStore()` without selectors subscribes to the entire auth store. Fix each one.

| File | Line | Current | Change to |
|------|------|---------|-----------|
| `components/ProtectedRoute.tsx` | 44 | `const { user, isLoading, isInitialized } = useAuthStore()` | Individual selectors: `const user = useAuthStore(s => s.user)` etc. |
| `components/layout/Sidebar.tsx` | 45 | `const { user, logout } = useAuthStore()` | Individual selectors |
| `components/layout/AdminHeader.tsx` | 44 | `const { user, logout } = useAuthStore()` | Individual selectors |
| `components/explorer/ContextMenu.tsx` | ~27 | `const { user, ... } = useAuthStore()` | Individual selectors |
| `components/explorer/SelectionActionBar.tsx` | ~31 | `const { ... } = useAuthStore()` | Individual selectors |
| `pages/LoginPage.tsx` | 29 | `const { login, isLoading, error, user } = useAuthStore()` | Individual selectors |
| `pages/AdminDashboard.tsx` | 59 | `const { user, getIdToken } = useAuthStore()` | Individual selectors |

- **Pattern for all:**
  ```tsx
  // Before
  const { user, logout } = useAuthStore();
  // After
  const user = useAuthStore(s => s.user);
  const logout = useAuthStore(s => s.logout);
  ```
- **Note:** For `api/client.ts` (line 54) — this is a non-component module using `useAuthStore.getState()`, which is fine and doesn't need selector changes.
- **Validation:** `npm run build && npm test`.

#### 2e. Add `useAuthStore` to barrel export (H4)

- **File:** `frontend/src/stores/index.ts`
- **Current code:**
  ```ts
  export { useExplorerStore } from './useExplorerStore';
  ```
- **New code:**
  ```ts
  export { useExplorerStore } from './useExplorerStore';
  export { useAuthStore, initAuthListener } from './useAuthStore';
  export type { AuthUser, UserRole } from './useAuthStore';
  ```
- **After this change**, update imports in all 12+ files that use `../stores/useAuthStore` to use `../stores` or `../../stores` (the barrel). This is optional but recommended for consistency.
  - Alternatively, keep direct imports and just fix the barrel — the barrel is useful for future consumers.
  - **Recommended approach:** Add to barrel now, migrate imports in a follow-up to keep this change set small.
- **Validation:** `npm run build`. Verify `import { useAuthStore } from '@/stores'` works.

#### 2f. Fix `warningTimeoutId` leak (M7)

- **File:** `frontend/src/stores/useExplorerStore.ts`
- **Problem:** `openWarningDialog` (line 269) creates a `setTimeout` and stores the ID in Zustand state. If the component tree unmounts (logout, navigation), the timeout fires into the void. `reset()` clears it but is never called on unmount.
- **Fix:** Add a cleanup call in `App.tsx` logout flow. The cleanest fix is to ensure `reset()` is called when the user logs out.
- **File:** `frontend/src/App.tsx` — No direct change needed here since logout already navigates to `/login` which unmounts explorer. Instead, add a cleanup effect in `ExplorerPage.tsx`:
- **File:** `frontend/src/pages/ExplorerPage.tsx` — Add:
  ```tsx
  // Add cleanup for warning timeout on unmount
  useEffect(() => {
      return () => {
          useExplorerStore.getState().closeWarningDialog();
      };
  }, []);
  ```
- **Alternative (better):** Move timeout management to a `useRef` inside the `WarningDialog` component instead of global state. But that's a larger refactor — the cleanup effect is pragmatic.
- **Validation:** Open explorer, trigger a warning dialog, navigate to `/admin` — verify no console errors from orphaned timeout.

---

### Group 3: Export & Routing Consistency (H5, M5, M8)

**Rationale:** Three pages use default exports violating the project style guide. Admin flash-redirect and login loop risk are small but real bugs.

**Dependency:** None. Independent of Groups 1–2.

#### 3a. Convert default exports to named exports (H5)

**Files to change:**

| File | Line | Current | New |
|------|------|---------|-----|
| `pages/ExplorerPage.tsx` | 227 | `export default function ExplorerPage()` | `export function ExplorerPage()` |
| `pages/LoginPage.tsx` | 324 | `export default LoginPage` | Remove (already has `export function LoginPage()`) |
| `pages/AdminDashboard.tsx` | ~2147 | `export default AdminDashboard` | Remove (already has `export function AdminDashboard()`) |

**Update imports in `App.tsx`:**
```tsx
// Before
import ExplorerPage from './pages/ExplorerPage'
import AdminDashboard from './pages/AdminDashboard'

// After
import { ExplorerPage } from './pages/ExplorerPage'
import { AdminDashboard } from './pages/AdminDashboard'
```

**Validation:** `npm run build` — no type errors. `grep -r "export default" frontend/src/pages/` returns nothing.

#### 3b. Prevent admin flash on ExplorerPage (M5)

- **File:** `frontend/src/pages/ExplorerPage.tsx`
- **Current code (lines 51–54):**
  ```tsx
  useEffect(() => {
      if (isAdmin()) {
          navigate('/admin', { replace: true });
      }
  }, [isAdmin, navigate]);
  ```
- **Fix:** Instead of redirecting inside ExplorerPage, block admins at the route level. In `App.tsx`, change the `/*` route:
  ```tsx
  // Before
  <Route path="/*" element={
      <ProtectedRoute>
          <ExplorerPage />
      </ProtectedRoute>
  } />

  // After
  <Route path="/*" element={
      <ProtectedRoute requiredRole={['staff', 'student']}>
          <ExplorerPage />
      </ProtectedRoute>
  } />
  ```
- **Also remove** the admin redirect `useEffect` from `ExplorerPage.tsx` (lines 51–54) and the now-unnecessary `hasRedirected` ref if it was only used for this.
- **Note:** This also handles the edge case where admins navigate to `/` directly — they'll be sent to `/login` → redirected to `/admin` by `LoginPage`'s redirect logic. Actually, `ProtectedRoute` redirects to `/` if role doesn't match, then we need a fallback. Better approach: keep the `useEffect` redirect in ExplorerPage but make it conditional on `isInitialized` to prevent the flash:
  ```tsx
  useEffect(() => {
      if (isInitialized && isAdmin()) {
          navigate('/admin', { replace: true });
      }
  }, [isInitialized, isAdmin, navigate]);
  ```
  And add `const isInitialized = useAuthStore(s => s.isInitialized)` to the selectors.
- **Validation:** Log in as admin, verify no flash of explorer content before redirect.

#### 3c. Guard LoginPage redirect against `/login` loop (M8)

- **File:** `frontend/src/pages/LoginPage.tsx`
- **Current code (lines 36–44):**
  ```tsx
  useEffect(() => {
      if (user) {
          const from = (location.state as { from?: string })?.from;
          if (from) {
              navigate(from, { replace: true });
          } else if (user.role === 'admin') {
              navigate('/admin', { replace: true });
          } else {
              navigate('/', { replace: true });
          }
      }
  }, [user, navigate, location.state]);
  ```
- **New code:**
  ```tsx
  useEffect(() => {
      if (user) {
          const from = (location.state as { from?: string })?.from;
          if (from && from !== '/login') {
              navigate(from, { replace: true });
          } else if (user.role === 'admin') {
              navigate('/admin', { replace: true });
          } else {
              navigate('/', { replace: true });
          }
      }
  }, [user, navigate, location.state]);
  ```
- **Change:** Add `&& from !== '/login'` guard.
- **Validation:** Navigate to `/login` with stale `from: '/login'` state — verify no infinite loop (React should bail after a few cycles anyway with `replace: true`, but the guard makes intent explicit).

---

### Group 4: Replace Native `alert()`/`confirm()` with UI Components (H1, L5)

**Rationale:** Native `alert()`/`confirm()` block the main thread, have zero accessibility, and look inconsistent across platforms. The project already has `ConfirmDialog` and `toast` from sonner.

**Dependency:** None. Independent of other groups. Can be done in parallel with Group 5, but do this first since it's smaller.

#### 4a. Replace `alert()` error messages with `toast.error()` in AdminDashboard

- **File:** `frontend/src/pages/AdminDashboard.tsx`
- **Add import:** `import { toast } from 'sonner';`
- **12 occurrences** — each `alert(err instanceof Error ? err.message : '...')` becomes `toast.error(err instanceof Error ? err.message : '...')`.

| Line | Context | Current | New |
|------|---------|---------|-----|
| 313 | `confirmDeleteUser` catch | `alert(...)` | `toast.error(...)` |
| 345 | `handleToggleStatus` catch | `alert(...)` | `toast.error(...)` |
| 352 | `handleUpdateSubjects` validation | `alert('Please select at least one subject')` | `toast.error('Please select at least one subject')` |
| 379 | `handleUpdateSubjects` catch | `alert(...)` | `toast.error(...)` |
| 405 | `handleCreateDepartment` catch | `alert(...)` | `toast.error(...)` |
| 423 | `handleDeleteDepartment` catch | `alert(...)` | `toast.error(...)` |
| 449 | `handleCreateSemester` catch | `alert(...)` | `toast.error(...)` |
| 470 | `handleDeleteSemester` catch | `alert(...)` | `toast.error(...)` |
| 521 | `handleCreateSubject` catch | `alert(...)` | `toast.error(...)` |
| 538 | `handleDeleteSubject` catch | `alert(...)` | `toast.error(...)` |
| 599 | `handleRename` catch | `alert(...)` | `toast.error(...)` |

#### 4b. Replace `confirm()` calls with `ConfirmDialog` state in AdminDashboard

- **3 occurrences** at lines 412, 456, 528.
- **Pattern:** Each `if (!confirm('Delete this X?')) return;` becomes a two-step flow with state.

**Implementation approach:** Add a generic confirm dialog state:
```tsx
const [confirmAction, setConfirmAction] = useState<{
    title: string;
    message: string;
    onConfirm: () => void;
} | null>(null);
```

**Replace each `confirm()` call:**
```tsx
// Before (line 412)
const handleDeleteDepartment = async (deptId: string) => {
    if (!confirm('Delete this department and all its contents?')) return;
    // ... delete logic
};

// After
const handleDeleteDepartment = async (deptId: string) => {
    setConfirmAction({
        title: 'Delete Department',
        message: 'Delete this department and all its contents?',
        onConfirm: async () => {
            setConfirmAction(null);
            // ... existing delete logic
        },
    });
};
```

**Add `ConfirmDialog` for the generic confirm (it's already imported):**
```tsx
<ConfirmDialog
    isOpen={!!confirmAction}
    title={confirmAction?.title ?? ''}
    message={confirmAction?.message ?? ''}
    confirmLabel="Delete"
    variant="danger"
    destructive
    onConfirm={() => confirmAction?.onConfirm()}
    onCancel={() => setConfirmAction(null)}
/>
```

**Note:** AdminDashboard already has a `ConfirmDialog` for user deletion at the bottom of the JSX. Reuse the same pattern — or merge into one dialog with a single generic state.

#### 4c. Replace `alert()` in ExplorerPage

- **File:** `frontend/src/pages/ExplorerPage.tsx`
- **Line 148:** `alert(\`Failed to delete: ${(error as Error).message}\`)` → `toast.error(\`Failed to delete: ${(error as Error).message}\`)`
- **Add import:** `import { toast } from 'sonner';`

#### 4d. Replace `confirm()` in SelectionActionBar

- **File:** `frontend/src/components/explorer/SelectionActionBar.tsx`
- **Line 191:** `const confirmed = confirm(...)` → Use `ConfirmDialog` state pattern.
- **Add state:** `const [confirmBulkOpen, setConfirmBulkOpen] = useState(false);`
- **Show `ConfirmDialog`** before opening multiple PDFs.
- **Validation:** `npm run build && npm test`. Manual: test each delete flow, verify dialog appears instead of native prompt.

---

### Group 5: AdminDashboard Decomposition (H2, H3, M1, M4, M6)

**Rationale:** AdminDashboard is 2148 lines with 20+ `useState` hooks, ~350 lines of inline CSS, missing loading states, stale closure bugs, and no ARIA attributes. This is the largest and most complex fix group.

**Dependency:** Should follow Group 4 (alert/confirm replacement) to avoid merge conflicts.

#### 5a. Extract inline CSS to `admin-dashboard.css` (H3)

- **File to create:** `frontend/src/styles/admin-dashboard.css`
- **Source:** Cut the `<style>` block from `AdminDashboard.tsx` (lines ~1788–2130, approximately 340 lines of CSS).
- **Add import at top of AdminDashboard.tsx:** `import '../styles/admin-dashboard.css';`
- **Also extract LoginPage CSS:**
  - **File to create:** `frontend/src/styles/login-page.css`
  - **Source:** Cut the `<style>` block from `LoginPage.tsx` (lines 180–323, approximately 140 lines).
  - **Add import:** `import '../styles/login-page.css';`
- **Validation:** `npm run build`. Visual check — admin page and login page look identical.

#### 5b. Extract custom hooks from AdminDashboard (H2, part 1)

Create hooks that encapsulate CRUD logic:

**File to create:** `frontend/src/pages/admin/hooks/useAdminUsers.ts`
```ts
// Encapsulates: users state, fetchUsers, createUser, deleteUser, toggleStatus, updateSubjects
// Returns: { users, isLoading, error, createUser, deleteUser, toggleStatus, updateSubjects }
```

**File to create:** `frontend/src/pages/admin/hooks/useAdminHierarchy.ts`
```ts
// Encapsulates: departments, semesters, subjects state + CRUD
// Returns: { departments, semesters, subjects, createDepartment, deleteDepartment,
//            createSemester, deleteSemester, createSubject, deleteSubject, rename }
```

**Each hook:**
- Takes `getIdToken` as a dependency (or gets it from `useAuthStore` selector internally)
- Manages its own loading/error states (fixes M1)
- Uses `toast.error()` for error handling (already done in Group 4)
- Uses functional state updates where needed (fixes M4)

**Example skeleton for `useAdminUsers.ts`:**
```ts
import { useState, useCallback } from 'react';
import { useAuthStore } from '../../../stores/useAuthStore';
import { toast } from 'sonner';

const API_BASE = '/api';

export function useAdminUsers() {
    const [users, setUsers] = useState<UserItem[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const getIdToken = useAuthStore(s => s.getIdToken);

    const fetchUsers = useCallback(async (params?: URLSearchParams) => {
        setIsLoading(true);
        try {
            const token = await getIdToken();
            if (!token) throw new Error('Not authenticated');
            const res = await fetch(`${API_BASE}/users?${params ?? ''}`, {
                headers: { 'Authorization': `Bearer ${token}` },
            });
            if (!res.ok) throw new Error('Failed to fetch users');
            setUsers(await res.json());
        } catch (err) {
            setError(err instanceof Error ? err.message : 'An error occurred');
        } finally {
            setIsLoading(false);
        }
    }, [getIdToken]);

    // deleteUser, toggleStatus, updateSubjects — each with its own
    // loading state (e.g., isDeletingId, togglingId) for M1

    return { users, isLoading, error, fetchUsers, /* ... */ };
}
```

#### 5c. Extract sub-components from AdminDashboard (H2, part 2)

**File to create:** `frontend/src/pages/admin/components/UserManagementTab.tsx`
- Renders: create user form, user table, edit subjects modal
- Props: users, departments, departmentSubjects, CRUD handlers

**File to create:** `frontend/src/pages/admin/components/HierarchyTab.tsx`
- Renders: hierarchy grid (departments → semesters → subjects), inline forms, rename logic
- Props: departments, semesters, subjects, CRUD handlers

**File to create:** `frontend/src/pages/admin/components/UserTable.tsx`
- Renders: user table rows with action buttons
- Props: users, onEditSubjects, onDelete, onToggleStatus, renamingId

**File to create:** `frontend/src/pages/admin/components/EditSubjectsModal.tsx`
- Renders: two-panel subject assignment modal
- Props: isOpen, userId, departments, departmentSubjects, selectedSubjects, onConfirm, onCancel

**Simplified AdminDashboard.tsx target:**
```tsx
export function AdminDashboard() {
    const user = useAuthStore(s => s.user);
    const [activeTab, setActiveTab] = useState<TabType>('users');
    const usersHook = useAdminUsers();
    const hierarchyHook = useAdminHierarchy();

    return (
        <div className="admin-dashboard">
            <AdminHeader title="Admin Dashboard" />
            <Tabs activeTab={activeTab} onChange={setActiveTab} />
            <main className="admin-content">
                <StatsCards users={usersHook.users} departments={hierarchyHook.departments} />
                {activeTab === 'users' && <UserManagementTab {...usersHook} {...hierarchyHook} />}
                {activeTab === 'hierarchy' && <HierarchyTab {...hierarchyHook} />}
            </main>
        </div>
    );
}
```

**Target size:** ~100–150 lines (down from 2148).

#### 5d. Add loading/disabled states for CRUD actions (M1)

- **In `useAdminUsers` hook:** Add `deletingUserId`, `togglingUserId` state. Disable buttons while action is in progress.
- **In `useAdminHierarchy` hook:** Add `deletingDeptId`, `deletingSemId`, `deletingSubjId`, `renamingInProgress` state.
- **In component templates:** Disable buttons when loading:
  ```tsx
  <button disabled={deletingUserId === user.id} onClick={() => deleteUser(user.id)}>
      {deletingUserId === user.id ? 'Deleting...' : 'Delete'}
  </button>
  ```

#### 5e. Fix stale closure in checkbox handler (M4)

- **Current code (AdminDashboard line ~376):**
  ```tsx
  setCreateForm({ ...createForm, subject_ids: allSelected });
  ```
- **Fix:** Use functional update:
  ```tsx
  setCreateForm(prev => ({ ...prev, subject_ids: allSelected }));
  ```
- **Location:** This will be inside `UserManagementTab` or `EditSubjectsModal` after decomposition.

#### 5f. Add ARIA attributes to tabs and modals (M6)

- **Tab buttons:** Add `role="tab"`, `aria-selected`, `role="tabpanel"`.
  ```tsx
  <div className="admin-tabs" role="tablist">
      <button
          role="tab"
          aria-selected={activeTab === 'users'}
          className={`tab-btn ${activeTab === 'users' ? 'active' : ''}`}
          onClick={() => setActiveTab('users')}
      >
          User Management
      </button>
      {/* ... */}
  </div>
  ```
- **Modal overlay:** Add `role="dialog"`, `aria-modal="true"`, `aria-labelledby`.
  ```tsx
  <div className="modal-overlay" role="dialog" aria-modal="true" aria-labelledby="modal-title">
      <div className="modal-content">
          <h3 id="modal-title">Edit Subjects</h3>
          {/* ... */}
      </div>
  </div>
  ```
- **Inline rename inputs:** Add `aria-label="Rename department"`.
- **Validation:** `npm run build`. Run Lighthouse accessibility audit — verify tab and dialog roles are detected.

#### 5g. Convert Sidebar inline styles to Tailwind (L4)

- **File:** `frontend/src/components/layout/Sidebar.tsx`
- **Lines 131, 149, 154, 160, 165, 170:** Replace `style={{ ... }}` with Tailwind classes.

| Line | Current `style` | Tailwind equivalent |
|------|-----------------|---------------------|
| 131 | `style={{ padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: '4px' }}` | `className="px-3 py-2 flex flex-col gap-1"` |
| 149 | `style={{ margin: '8px 0', borderBottom: '1px solid var(--color-border)', opacity: 0.5 }}` | `className="my-2 border-b border-border opacity-50"` |
| 154 | `style={{ padding: '12px', borderTop: '1px solid var(--color-border)', marginTop: 'auto' }}` | `className="p-3 border-t border-border mt-auto"` |
| 160 | `style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}` | `className="w-full flex items-center justify-center gap-2"` |

- **Validation:** Visual comparison — sidebar looks identical.

---

### Group 6: Performance & Polish (M2, M3)

**Rationale:** Minor performance improvements. Low risk, modest benefit.

**Dependency:** None. Independent of other groups.

#### 6a. Lazy-initialize date state in UsagePage (M2)

- **File:** `frontend/src/pages/UsagePage.tsx`
- **Current code (lines 41–48):**
  ```tsx
  function getDefaultDateRange(): { start: string; end: string } {
      const end = new Date();
      const start = new Date();
      start.setDate(start.getDate() - 30);
      return {
          start: start.toISOString().split('T')[0],
          end: end.toISOString().split('T')[0],
      };
  }

  // In component:
  const defaults = getDefaultDateRange();
  const [startDate, setStartDate] = useState(defaults.start);
  const [endDate, setEndDate] = useState(defaults.end);
  ```
- **New code:**
  ```tsx
  // Remove getDefaultDateRange function entirely

  // In component:
  const [startDate, setStartDate] = useState(() => {
      const d = new Date();
      d.setDate(d.getDate() - 30);
      return d.toISOString().split('T')[0];
  });
  const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);
  ```
- **Validation:** `npm run build`. Usage page loads with correct default date range.

#### 6b. Add debounce to search input (M3)

- **File:** `frontend/src/components/layout/Header.tsx`
- **Approach:** Use a local state for the input value, debounce the store sync.
- **Current code (desktop search, line ~150):**
  ```tsx
  <input
      type="text"
      placeholder="Search..."
      value={searchQuery}
      onChange={(e) => setSearchQuery(e.target.value)}
  />
  ```
- **New code:**
  ```tsx
  // Add at top of component (inside Header):
  const [localSearch, setLocalSearch] = useState(searchQuery);

  // Sync local search to store with debounce
  useEffect(() => {
      const timer = setTimeout(() => {
          setSearchQuery(localSearch);
      }, 200);
      return () => clearTimeout(timer);
  }, [localSearch, setSearchQuery]);

  // Sync store changes back to local (e.g., when search is cleared programmatically)
  useEffect(() => {
      if (searchQuery !== localSearch) {
          setLocalSearch(searchQuery);
      }
  }, [searchQuery]); // eslint-disable-line react-hooks/exhaustive-deps

  // In JSX:
  <input
      type="text"
      placeholder="Search..."
      value={localSearch}
      onChange={(e) => setLocalSearch(e.target.value)}
  />
  ```
- **Apply to both desktop and mobile search inputs** (lines ~127–132 for mobile, ~150–155 for desktop).
- **Validation:** Type rapidly in search — verify no visible lag. GridView/ListView filtering updates after ~200ms pause.

---

## Verification Checklist

After each group, run the following:

### Build & Type Check
```bash
cd frontend
npm run build          # Must pass with zero errors
npx tsc --noEmit       # Type-only check
```

### Lint
```bash
npm run lint           # Must pass (or only pre-existing warnings)
```

### Unit Tests
```bash
npm test               # All existing tests must pass
```

### E2E Tests
```bash
npm run test:e2e       # All existing E2E tests must pass
```

### Group-Specific Verification

| Group | What to verify |
|-------|----------------|
| **1** | Error boundary shows fallback when component throws. LoadingSpinner has `role="status"`. |
| **2** | Typing in search doesn't re-render Sidebar. Opening context menu doesn't re-render Header. Barrel import works. |
| **3** | No `export default` in pages. Admin sees no explorer flash. Login redirects safely. |
| **4** | Zero `alert()` or `confirm()` calls remain in `frontend/src/pages/` and `frontend/src/components/`. All delete flows show `ConfirmDialog`. All errors show `toast.error()`. |
| **5** | AdminDashboard < 200 lines. All CRUD buttons disable during operations. Modals have ARIA roles. Visual regression: admin page looks identical. |
| **6** | UsagePage loads date defaults correctly. Search input debounces (type fast, observe 200ms delay before filter updates). |

### Final Full Verification
```bash
cd frontend
npm run build && npm run lint && npm test && npm run test:e2e
```

---

## Risk Notes

1. **AdminDashboard decomposition (Group 5)** is the highest-risk change. It touches the most code and has the highest chance of regressions.
   - **Mitigation:** Extract incrementally — hooks first, then components. Run tests after each sub-step.
   - **Rollback:** Keep the original file as `AdminDashboard.original.tsx` until all tests pass.

2. **Zustand selector migration (Group 2)** could miss a field, causing `undefined` reads.
   - **Mitigation:** `npm run build` catches most type errors. Manual smoke test after changes.

3. **ErrorBoundary placement** — wrapping individual routes means each route gets its own boundary. This is intentional (isolation) but means the error boundary state resets on navigation.
   - **Mitigation:** This is actually desirable — navigating away from a crashed page gives a fresh start.

4. **ConfirmDialog replacement (Group 4)** — replacing synchronous `confirm()` with async dialog changes the control flow. The delete action now happens in a callback, not inline.
   - **Mitigation:** Test each delete flow manually. Ensure the dialog's `onConfirm` callback captures the correct entity ID.

5. **Search debounce (Group 6)** — 200ms delay may feel slightly different to users.
   - **Mitigation:** 200ms is imperceptible. Can tune to 150ms if needed.

6. **Breaking changes to barrel export (Group 2e)** — adding `useAuthStore` to the barrel could cause duplicate module instances if some files import from barrel and others from direct path.
   - **Mitigation:** This shouldn't happen with ESM (same module resolution), but verify with build. If issues arise, defer barrel migration and just add the export.

7. **No existing unit tests for components** — `find` returned zero `.test.tsx` files in the components directory. Changes should be manually verified until test coverage is added.
   - **Mitigation:** Write smoke tests for critical paths (ErrorBoundary, admin CRUD) as part of this work.

---

## Execution Order

```
Group 1 (Safety net)     ──┐
Group 2 (Store fixes)    ──┤── Can run in parallel
Group 3 (Exports/routing)──┤
Group 6 (Performance)    ──┘
                           │
Group 4 (Dialogs)        ──┤── Depends on Group 2 (selectors)
                           │
Group 5 (Decomposition)  ──┘── Depends on Group 4 (alert/confirm already replaced)
```

**Recommended serial order:** 1 → 2 → 3 → 4 → 5 → 6
