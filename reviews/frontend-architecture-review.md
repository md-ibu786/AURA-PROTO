# Frontend Architecture Review — AURA-NOTES-MANAGER

**Reviewed:** 2026-05-24
**Scope:** State management, routing, architecture, component composition, performance, accessibility
**Files reviewed:** 15 primary files + 3 integration tests

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 2 |
| High | 6 |
| Medium | 8 |
| Low | 5 |

Overall the application is functional and the Zustand stores are well-structured with clear separation of concerns (server state via React Query, UI state via Zustand). The main issues are: missing error boundaries (app crash risk), Zustand selectors causing unnecessary re-renders across the board, `alert()`/`confirm()` native dialogs instead of project-owned components, and AdminDashboard being a ~2150-line mega-component.

---

## Critical

### C1. No Error Boundary Anywhere in the Application

**Files:** `App.tsx`, `main.tsx`
**Lines:** `App.tsx:39–68`, `main.tsx:40–45`

No `ErrorBoundary` component wraps any route or the application root. If any component throws during render (e.g., a corrupted tree node, an unexpected `null` from the API, a rendering bug in reagraph), the **entire application crashes to a white screen** with no recovery path.

The project even has an `ErrorBoundary.tsx` component listed in AGENTS.md (`components/ErrorBoundary.tsx`) but it is **never imported or used**.

**Evidence:** Grep for `ErrorBoundary` across all `.tsx` files returned zero results.

**Fix:** Wrap each route element (or at minimum the `<Routes>` block) in an error boundary:
```tsx
// App.tsx
<ErrorBoundary fallback={<div>Something went wrong. <a href="/">Go home</a></div>}>
    <Routes>...</Routes>
</ErrorBoundary>
```
Add per-route error boundaries for `/admin` and `/*` to isolate failures.

---

### C2. Zustand `useExplorerStore()` Called Without Selectors — Mass Re-renders

**Files:** `Header.tsx:46`, `Sidebar.tsx:44`, `ExplorerPage.tsx:37–47`

Every component that calls `useExplorerStore()` (no selector) subscribes to **the entire store**. Any change to any field — `searchQuery`, `contextMenuPosition`, `selectionMode`, `warningDialog`, etc. — triggers a re-render of every subscribing component.

**Evidence:**
- `Header.tsx:46` destructures 10 fields from `useExplorerStore()`
- `Sidebar.tsx:44` destructures 4 fields from `useExplorerStore()`
- `ExplorerPage.tsx:37` destructures 8 fields from `useExplorerStore()`

This means typing in the search box, right-clicking for a context menu, or toggling selection mode re-renders the Sidebar, Header, and ExplorerPage simultaneously.

**Fix:** Use Zustand selectors:
```tsx
// Before (Header.tsx)
const { currentPath, navigateUp, ... } = useExplorerStore();

// After
const currentPath = useExplorerStore(s => s.currentPath);
const navigateUp = useExplorerStore(s => s.navigateUp);
// ... or use a single shallow-equality selector:
const { currentPath, navigateUp, ... } = useExplorerStore(
    useShallow(s => ({
        currentPath: s.currentPath,
        navigateUp: s.navigateUp,
        // ...
    }))
);
```
Zustand provides `useShallow` from `zustand/react/shallow` for multi-field selectors.

---

## High

### H1. `alert()` and `confirm()` Used Instead of Project-Owned UI Components

**File:** `AdminDashboard.tsx` (15+ occurrences)
**Lines:** 313, 345, 352, 379, 405, 412, 423, 449, 456, 470, 521, 528, 538, 599

Native `alert()` blocks the main thread and has **zero accessibility** (not announced by screen readers as a dialog, no keyboard navigation, looks different per browser/OS). The project already has `ConfirmDialog` (used at line 2140 in the same file) and `sonner` toasts (configured in `App.tsx`).

For example, line 412 uses `confirm('Delete this department...')` while line 2140 uses `<ConfirmDialog>` for user deletion — **inconsistent within the same file**.

**Fix:**
- Replace `confirm()` calls with `<ConfirmDialog>` component (already imported).
- Replace `alert()` calls with `toast.error()` from sonner (already configured in `App.tsx`).
- Add state for each confirmation dialog (department delete, semester delete, subject delete).

---

### H2. AdminDashboard Is a ~2150-Line Mega-Component

**File:** `AdminDashboard.tsx` — 2148 lines, 20+ `useState` hooks, inline `<style>` tag (~500 lines of CSS)

This single file contains:
- User CRUD logic + form state
- Department CRUD + form state
- Semester CRUD + form state
- Subject CRUD + form state
- Staff subject assignment modal logic
- Inline rename logic
- Filter logic
- All UI for two tabs
- ~500 lines of inline CSS

**Impact:** Extremely difficult to test, maintain, or refactor. Any change risks unintended side effects.

**Fix:** Decompose into:
```
pages/admin/
├── AdminDashboard.tsx         # Layout + tabs only
├── hooks/
│   ├── useAdminUsers.ts       # User CRUD hook
│   ├── useAdminHierarchy.ts   # Dept/sem/subj CRUD hook
│   └── useAdminSubjects.ts    # Staff subject assignment
├── components/
│   ├── UserManagementTab.tsx
│   ├── HierarchyTab.tsx
│   ├── CreateUserForm.tsx
│   ├── UserTable.tsx
│   ├── EditSubjectsModal.tsx
│   └── HierarchyColumn.tsx
```

---

### H3. Inline `<style>` Tags in Components — FOUC and SSR Risks

**Files:** `AdminDashboard.tsx:1788–2130`, `LoginPage.tsx:180–323`

Both components inject raw CSS via `<style>{`...`}</style>` inside JSX. This:
- Causes flash of unstyled content (FOUC) on initial render
- Breaks SSR/hydration if ever needed
- Duplicates CSS that could be in the Tailwind-based stylesheet
- Is inconsistent — `SettingsPage` and `UsagePage` use Tailwind utility classes

**Fix:** Move styles to dedicated CSS files (`admin-dashboard.css`, `login-page.css`) imported at the top, or convert to Tailwind utility classes (preferred since Tailwind is already configured).

---

### H4. `stores/index.ts` Barrel Export Omits `useAuthStore`

**File:** `stores/index.ts`

The barrel only exports `useExplorerStore`:
```ts
export { useExplorerStore } from './useExplorerStore';
```

But `useAuthStore` is imported from a direct path (`../stores/useAuthStore`) in **12+ files**. This creates an inconsistency where some stores go through the barrel and others don't.

**Fix:** Add `useAuthStore` to the barrel:
```ts
export { useExplorerStore } from './useExplorerStore';
export { useAuthStore, initAuthListener } from './useAuthStore';
```

---

### H5. Inconsistent Export Patterns — `default` vs Named Exports

**Files:**
- `export default`: `ExplorerPage.tsx:63`, `LoginPage.tsx:324`, `AdminDashboard.tsx:2147`
- Named export: `SettingsPage.tsx`, `UsagePage.tsx`, `Header.tsx`, `Sidebar.tsx`, `LoadingSpinner.tsx`

The project style guide explicitly states: **"DO NOT use default exports"**. Three page components violate this.

**Evidence in `App.tsx` import style is inconsistent:**
```tsx
import ExplorerPage from './pages/ExplorerPage'           // default
import { LoginPage } from './pages/LoginPage'              // named
import AdminDashboard from './pages/AdminDashboard'        // default
import { SettingsPage } from './pages/SettingsPage'        // named
import { UsagePage } from './pages/UsagePage'              // named
```

**Fix:** Convert the three default exports to named exports and update imports in `App.tsx`.

---

### H6. `useAuthStore` Computed Functions Are Not Stable References

**File:** `useAuthStore.ts:95–125`

Computed properties like `isAdmin`, `isStaff`, `canManageModules` are stored as **plain functions** in the store. Each call to `useAuthStore()` that destructures these gets function references. However, the real problem is that components calling `const { isAdmin } = useAuthStore()` subscribe to the **entire auth store** (same issue as C2 but for auth).

Components like `ExplorerPage.tsx:43` call `const { user, isAdmin } = useAuthStore()` and then call `isAdmin()` in effects and JSX — this causes re-renders when **any** auth field changes (e.g., `isLoading`, `error`, `isInitialized`).

**Fix:** Either:
1. Use selectors: `const isAdmin = useAuthStore(s => s.user?.role === 'admin')`
2. Or derive outside the store: `const isAdmin = user?.role === 'admin'`

---

## Medium

### M1. Missing Loading/Disabled States for Hierarchy CRUD in AdminDashboard

**File:** `AdminDashboard.tsx`

- `handleDeleteDepartment` (line 410): No loading state — button remains clickable during the async delete.
- `handleDeleteSemester` (line 455): Same issue.
- `handleDeleteSubject` (line 527): Same issue.
- `handleToggleStatus` (line 320): No loading/disabled state on the toggle button — user can double-click.
- `handleRename` (line 560): No loading state on the rename save button.

**Fix:** Add `isDeleting` / `isUpdating` state flags and disable buttons during operations, or use a single `pendingAction` state pattern.

---

### M2. `getDefaultDateRange()` Creates New Objects on Every Render

**File:** `UsagePage.tsx:41–48`

```tsx
function getDefaultDateRange(): { start: string; end: string } {
    const end = new Date();
    const start = new Date();
    start.setDate(start.getDate() - 30);
    return { start: start.toISOString().split('T')[0], end: end.toISOString().split('T')[0] };
}
```

This function is called at component top-level (`const defaults = getDefaultDateRange()`) on every render, creating new Date objects and strings each time. While not a major perf issue since `useState` ignores subsequent values, it's wasteful and misleading.

**Fix:** Use lazy initialization:
```tsx
const [startDate, setStartDate] = useState(() => {
    const d = new Date(); d.setDate(d.getDate() - 30);
    return d.toISOString().split('T')[0];
});
const [endDate, setEndDate] = useState(() => new Date().toISOString().split('T')[0]);
```

---

### M3. No Debounce on Search Input

**File:** `Header.tsx:150–155` (desktop), `Header.tsx:127–132` (mobile)

Search input updates `searchQuery` in Zustand on every keystroke. If `GridView`/`ListView` filter items based on this query, every keystroke triggers a re-render of the entire content area.

**Fix:** Use a debounced local state for the input, then sync to the store:
```tsx
const [localSearch, setLocalSearch] = useState(searchQuery);
useDebouncedEffect(() => setSearchQuery(localSearch), [localSearch], 200);
```

---

### M4. Potential Stale Closure in AdminDashboard Checkbox Handler

**File:** `AdminDashboard.tsx:366–380`

```tsx
onChange={e => {
    const currentDeptSubjects = selectedSubjectsByDept.get(currentDeptForSubjects) || [];
    // ...
    setCreateForm({ ...createForm, subject_ids: allSelected });
}}
```

The `createForm` reference is captured from the closure. If multiple checkboxes are clicked rapidly, the spread of `createForm` may use a stale value, losing previously entered fields (email, password, etc.).

**Fix:** Use functional state update:
```tsx
setCreateForm(prev => ({ ...prev, subject_ids: allSelected }));
```

---

### M5. ExplorerPage Redirect Logic Redundant with ProtectedRoute

**Files:** `ExplorerPage.tsx:51–54`, `App.tsx:62–66`

```tsx
// ExplorerPage.tsx:51-54
useEffect(() => {
    if (isAdmin()) {
        navigate('/admin', { replace: true });
    }
}, [isAdmin, navigate]);
```

The root `/*` route in `App.tsx` is wrapped in `<ProtectedRoute>` with **no `requiredRole`**, so admins are allowed through. Then ExplorerPage redirects them to `/admin`. This works but creates a flash: the admin briefly sees the explorer layout before the redirect fires.

**Fix:** Either:
1. Add `requiredRole={['staff', 'student']}` to the `/*` route in `App.tsx` (cleanest).
2. Or use a layout route that checks the role before rendering.

---

### M6. Missing `aria-*` Attributes and Semantic HTML in AdminDashboard

**File:** `AdminDashboard.tsx`

- Tab buttons (line 648–658) lack `role="tab"`, `aria-selected`, and the tab panel lacks `role="tabpanel"`.
- Modal overlay (line 1613) lacks `role="dialog"`, `aria-modal="true"`, `aria-labelledby`.
- Inline rename inputs lack `aria-label`.
- Stats cards are `div`s instead of semantic `<section>` or `<article>`.
- Data table (line 742) is properly `<table>` but sortable columns lack `aria-sort`.

**Fix:** Add appropriate ARIA roles and attributes. For tabs:
```tsx
<button role="tab" aria-selected={activeTab === 'users'}>User Management</button>
```

---

### M7. `warningTimeoutId` Stored in Zustand State — Potential Leak on Unmount

**File:** `useExplorerStore.ts:269–282`

`openWarningDialog` sets a `setTimeout` and stores the ID in Zustand state. If the component tree unmounts (e.g., logout, navigation), the timeout continues running. The `reset()` action clears it, but `reset()` is never called on unmount.

**Evidence:** `reset()` is never called in any `useEffect` cleanup or route transition.

**Fix:** Either:
1. Call `reset()` in a cleanup effect at the app level.
2. Use `useRef` in the WarningDialog component for the timeout instead of global state.

---

### M8. `LoginPage` Redirect Creates Potential Infinite Loop

**File:** `LoginPage.tsx:35–44`

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

If `from` points back to `/login` (e.g., if the user bookmarked `/login` with stale state), this creates an infinite redirect loop. The `replace: true` prevents history accumulation but not the render cycle.

**Fix:** Add a guard:
```tsx
if (from && from !== '/login') { navigate(from, { replace: true }); }
```

---

## Low

### L1. `useAuthStore` `refreshUser` Uses Raw `fetch()` Instead of `fetchApi`

**File:** `useAuthStore.ts:217–290`

The `refreshUser` function uses raw `fetch()` with manual auth headers. The code comment explains this is intentional to avoid circular dependencies and handle 401 specially. This is acceptable but worth noting that:
- Error handling is inconsistent with the rest of the API layer.
- The sync-then-retry pattern (401 → sync → retry) is duplicated in `client.ts:executeWithRetry`.

**Note:** This is acknowledged in the code comments and appears to be a conscious design decision.

---

### L2. `LoadingSpinner` Missing `aria-live` Region

**File:** `LoadingSpinner.tsx:29–38`

The loading spinner has no `aria-live="polite"` or `role="status"`, so screen readers don't announce the loading state.

**Fix:**
```tsx
<div role="status" aria-live="polite" className="min-h-screen ...">
    <span className="sr-only">Loading...</span>
    ...
</div>
```

---

### L3. Integration Tests Don't Cover Auth Flows or Route Protection

**Files:** `integration/StateSync.test.tsx`, `integration/WarningDialogFlow.test.tsx`, `integration/GridViewWarning.test.tsx`

All three integration tests cover explorer store state and warning dialogs. None test:
- Auth state transitions (login, logout, token refresh)
- Route protection (unauthenticated → redirect to /login)
- Role-based access (admin-only pages)
- Mock auth flow

**Note:** These may be covered by E2E tests, but unit-level integration tests for auth would catch regressions faster.

---

### L4. `AdminDashboard` Uses Inline `style` Attributes Extensively

**File:** `Sidebar.tsx` — lines 131, 149, 154, 160, 165, 170

```tsx
style={{ padding: '8px 12px', display: 'flex', flexDirection: 'column', gap: '4px' }}
```

The Sidebar mixes Tailwind utility classes (`flex items-center gap-sm`) with inline `style` props. This creates maintenance confusion about which styling approach to follow.

**Fix:** Convert inline styles to Tailwind classes for consistency.

---

### L5. `ExplorerPage` `handleDeleteConfirm` Uses `alert()` for Error

**File:** `ExplorerPage.tsx:148`

```tsx
} catch (error) {
    alert(`Failed to delete: ${(error as Error).message}`);
}
```

Same issue as H1 but in a different file. Should use `toast.error()` from sonner.

---

## Architecture Observations (No Action Required)

### Positive Patterns

1. **Clean store separation**: Zustand for UI state, React Query for server state. The `useExplorerStore` is purely client-side UI state; `getExplorerTree` uses React Query. This is textbook Zustand + React Query architecture.

2. **Auth store with sync-then-retry**: The `refreshUser` 401 handling with sync-then-retry is a thoughtful pattern for Firebase token expiration.

3. **`ProtectedRoute` component**: Well-designed route guard supporting single role, array of roles, and department scoping.

4. **`useMobileBreakpoint` hook**: Clean implementation using `matchMedia` API with proper event listener cleanup.

5. **Integration tests**: Having integration tests for the store + WarningDialog flow is good practice and catches cross-cutting issues.

6. **Tree filtering in ExplorerPage**: The `getFilteredTree()` and `getCurrentChildren()` logic correctly handles role-based filtering (admin sees all, staff sees their subjects, student sees their department).

### Areas for Future Improvement

1. **No shared admin layout**: Each admin page (`AdminDashboard`, `SettingsPage`, `UsagePage`) independently renders `<AdminHeader>`. A shared layout route would reduce duplication:
   ```tsx
   <Route path="/admin" element={<AdminLayout />}>
       <Route index element={<AdminDashboard />} />
       <Route path="settings" element={<SettingsPage />} />
       <Route path="usage" element={<UsagePage />} />
   </Route>
   ```

2. **No typed API response models**: API responses are typed inline (`response.json() as { status: string; ... }`). Shared response types would improve type safety.

3. **CSS strategy needs alignment**: The codebase uses four styling approaches: Tailwind utilities, CSS modules/files, inline `style` props, and inline `<style>` tags. Picking one (Tailwind) and migrating consistently would reduce confusion.

---

## Files Reviewed

| File | Lines | Issues Found |
|------|-------|-------------|
| `stores/useAuthStore.ts` | 312 | H6, L1 |
| `stores/useExplorerStore.ts` | 340 | M7 |
| `stores/index.ts` | 14 | H4 |
| `App.tsx` | 68 | C1 |
| `main.tsx` | 45 | C1 |
| `pages/AdminDashboard.tsx` | 2148 | H1, H2, H3, M1, M4, M6 |
| `pages/SettingsPage.tsx` | 220 | (clean) |
| `pages/UsagePage.tsx` | 117 | M2 |
| `components/layout/Header.tsx` | 188 | C2, M3 |
| `components/layout/Sidebar.tsx` | 175 | C2, L4 |
| `components/layout/AdminHeader.tsx` | 95 | (clean) |
| `components/LoadingSpinner.tsx` | 38 | L2 |
| `components/ProtectedRoute.tsx` | 62 | (clean) |
| `hooks/useMobileBreakpoint.ts` | 45 | (clean) |
| `pages/ExplorerPage.tsx` | 227 | C2, M5, L5 |
| `pages/LoginPage.tsx` | 324 | H3, H5, M8 |
| `integration/GridViewWarning.test.tsx` | 117 | L3 |
| `integration/StateSync.test.tsx` | 80 | L3 |
| `integration/WarningDialogFlow.test.tsx` | 102 | L3 |
