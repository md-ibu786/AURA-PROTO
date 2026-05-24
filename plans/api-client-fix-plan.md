# API Client Fix Plan

**Created:** 2026-05-24
**Source:** `reviews/api-client-review.md`
**Status:** Ready

---

## Overview

**Scope:** Fix 16 findings in the frontend API client layer (`frontend/src/api/`) and two consumer files that bypass the client (`AdminDashboard.tsx`, `UploadDialog.tsx`).

**Affected files:**
- `frontend/src/api/client.ts` — core fetch wrappers, error handling, timeout, auth retry
- `frontend/src/api/errors.ts` — `NetworkError` (dead code → live code)
- `frontend/src/api/explorerApi.ts` — missing return types on 15 CRUD functions
- `frontend/src/api/audioApi.ts` — redundant `.toString()`
- `frontend/src/api/index.ts` — barrel export missing `NetworkError`
- `frontend/src/pages/AdminDashboard.tsx` — 16+ raw `fetch()` calls → use `userApi`/`explorerApi`
- `frontend/src/components/explorer/UploadDialog.tsx` — 3 raw `fetch()` calls → use `audioApi`

**Estimated effort:** ~8–10 hours total, split across 4 fix groups.

---

## Prerequisites

1. Backend running on port 8001 for manual smoke testing.
2. Frontend dev server running (`npm run dev` in `frontend/`).
3. `npm run build` passes before starting (baseline).
4. `npm run lint` passes before starting (baseline).
5. Familiarity with `userApi.ts` and `audioApi.ts` — they already provide typed wrappers that AdminDashboard and UploadDialog should be using.

---

## Fix Groups

### Group 1 — Core Client Hardening (`client.ts`, `errors.ts`, `index.ts`)

**Rationale:** These are foundational changes that all other groups depend on. Fix the empty-body crash, add timeout support, activate `NetworkError`, unify error parsing, and add `PermissionError`.

#### 1a. F-02 — Handle 204/empty-body in `fetchApi` (and `fetchFormData`)

**File:** `frontend/src/api/client.ts:200`

**Before:**
```typescript
return response.json();
```

**After:**
```typescript
if (response.status === 204 || response.headers.get('content-length') === '0') {
    return undefined as T;
}
return response.json();
```

Apply the same fix at line 257 (`fetchFormData`).

**Validation:** Call `deleteUser()` against a backend that returns 204 — should not throw.

---

#### 1b. F-01 — Convert native `TypeError` to `NetworkError` in `executeWithRetry`

**File:** `frontend/src/api/client.ts:96`

**Before:**
```typescript
let response = await fetch(url, options);
```

**After:**
```typescript
let response: Response;
try {
    response = await fetch(url, options);
} catch (e) {
    if (e instanceof TypeError) {
        throw new NetworkError(`Network request failed: ${(e as Error).message}`);
    }
    throw e;
}
```

**File:** `frontend/src/api/client.ts:55` (import)

**Before:**
```typescript
import { DuplicateError, AuthError } from './errors';
```

**After:**
```typescript
import { DuplicateError, AuthError, NetworkError } from './errors';
```

**File:** `frontend/src/api/client.ts:404` (re-export)

**Before:**
```typescript
export { DuplicateError, AuthError } from './errors';
```

**After:**
```typescript
export { DuplicateError, AuthError, NetworkError } from './errors';
```

**Validation:** Disconnect network, call `fetchApi('/test')` — should throw `NetworkError`, not raw `TypeError`.

---

#### 1c. F-03 — Add configurable timeout via `AbortController`

**File:** `frontend/src/api/client.ts:92–125`

**Before:**
```typescript
async function executeWithRetry(
    url: string,
    options: RequestInit
): Promise<Response> {
    let response: Response;
    // ... fetch and retry
```

**After:**
```typescript
async function executeWithRetry(
    url: string,
    options: RequestInit,
    timeoutMs: number = 30_000
): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    // Link caller's signal if provided
    if (options.signal) {
        options.signal.addEventListener('abort', () => controller.abort(), { once: true });
    }

    let response: Response;
    try {
        response = await fetch(url, { ...options, signal: controller.signal });
    } catch (e) {
        if (e instanceof DOMException && e.name === 'AbortError') {
            throw new NetworkError(`Request timed out after ${timeoutMs}ms: ${url}`);
        }
        if (e instanceof TypeError) {
            throw new NetworkError(`Network request failed: ${(e as Error).message}`);
        }
        throw e;
    } finally {
        clearTimeout(timeoutId);
    }
    // ... existing 401 retry logic (reuse same controller or create new one for retry)
```

Update the retry fetch at line 113 to also use the controller signal.

**Validation:** Point API_BASE to a non-responding host — should throw `NetworkError` with timeout message after 30s.

---

#### 1d. F-09 — Add refresh cooldown to prevent refresh storms

**File:** `frontend/src/api/client.ts:60` (after `tokenRefreshPromise`)

**Add:**
```typescript
let lastRefreshAttempt = 0;
const REFRESH_COOLDOWN_MS = 5_000;
```

**File:** `frontend/src/api/client.ts:98` (inside 401 check)

**Before:**
```typescript
if (response.status === 401 && import.meta.env.VITE_USE_MOCK_AUTH !== 'true') {
```

**After:**
```typescript
if (response.status === 401 && import.meta.env.VITE_USE_MOCK_AUTH !== 'true') {
    const now = Date.now();
    if (now - lastRefreshAttempt < REFRESH_COOLDOWN_MS) {
        throw new AuthError('Token refresh already attempted recently');
    }
    lastRefreshAttempt = now;
```

**Validation:** Simulate persistent 401 — should see at most 1 refresh attempt per 5s window, not a cascade.

---

#### 1e. F-10 — Unify error parsing through `parseErrorMessage`

**File:** `frontend/src/api/client.ts:184–198` (`fetchApi` error block)

**Before:**
```typescript
if (!response.ok) {
    const error = await response.json().catch((e) => {
        console.warn('Failed to parse error response:', e);
        return { detail: 'Network error' };
    });

    if (response.status === 409) {
        const detail = error.detail;
        if (detail && typeof detail === 'object' && detail.code === 'DUPLICATE_NAME') {
            throw new DuplicateError(detail.message, detail.code);
        }
    }

    throw new Error(error.detail || `HTTP ${response.status}`);
}
```

**After:**
```typescript
if (!response.ok) {
    const message = await parseErrorMessage(response);

    if (response.status === 409) {
        try {
            const body = await response.clone().json();
            if (body?.detail?.code === 'DUPLICATE_NAME') {
                throw new DuplicateError(body.detail.message, body.detail.code);
            }
        } catch (e) {
            if (e instanceof DuplicateError) throw e;
        }
    }

    throw new Error(message);
}
```

Apply the same pattern to `fetchFormData` (line 249–254) and `fetchAuthApi` (line 283–288).

**Validation:** Return an HTML error page from backend — should surface the HTML content, not `{ detail: 'Network error' }`.

---

#### 1f. F-12 — Add `PermissionError` class and 403 handling

**File:** `frontend/src/api/errors.ts` (add after `AuthError`)

**Add:**
```typescript
export class PermissionError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'PermissionError';
    }
}
```

**File:** `frontend/src/api/client.ts:190` (inside `fetchApi` error handling, after 409 check)

**Add:**
```typescript
if (response.status === 403) {
    throw new PermissionError(message);
}
```

Import and re-export `PermissionError` alongside `DuplicateError`, `AuthError`, `NetworkError`.

**Validation:** Staff user attempts admin-only endpoint — should throw `PermissionError` with clear message.

---

#### 1g. F-13 — Only set `Content-Type` on requests with body

**File:** `frontend/src/api/client.ts:177–181`

**Before:**
```typescript
headers: {
    'Content-Type': 'application/json',
    ...authHeaders,
    ...options?.headers,
},
```

**After:**
```typescript
headers: {
    ...(options?.body ? { 'Content-Type': 'application/json' } : {}),
    ...authHeaders,
    ...options?.headers,
},
```

**Validation:** GET requests should not include `Content-Type` header (check Network tab).

---

#### 1h. F-11 — Thread `AbortSignal` through wrappers

Already handled by 1c (signal is in `RequestInit` and passed through to `executeWithRetry`). Document in JSDoc that callers can pass `{ signal: controller.signal }`.

---

### Group 2 — Health Check Fixes (`client.ts:325–401`)

**Rationale:** `checkHealth()` is a separate code path that bypasses `executeWithRetry` and uses unsafe type assertions. Fix after Group 1 since it may reuse `executeWithRetry`.

#### 2a. F-08 — Route health checks through `executeWithRetry`

**File:** `frontend/src/api/client.ts:333–343`

**Before:**
```typescript
const fetchHealth = async (endpoint: string): Promise<Response | null> => {
    try {
        const authHeaders = await getAuthHeader();
        return fetch(endpoint, {
            headers: authHeaders,
        });
    } catch (e) {
        console.warn('Health check auth failed:', e);
        return null;
    }
};
```

**After:**
```typescript
const fetchHealth = async (endpoint: string): Promise<Response | null> => {
    try {
        const authHeaders = await getAuthHeader();
        return executeWithRetry(endpoint, { headers: authHeaders });
    } catch (e) {
        console.warn('Health check failed:', e);
        return null;
    }
};
```

Note: Health endpoints (`/health`, `/ready`, `/health/redis`) are not under `/api` prefix, so pass the full URL directly (not through `API_BASE`).

**Validation:** Stale token during health check — should retry with refreshed token instead of reporting "degraded".

---

#### 2b. F-07 — Replace `as` casts with runtime validation

**File:** `frontend/src/api/client.ts:349, 361, 375, 388`

**Before (each instance):**
```typescript
const healthData = await response.json() as { status: string; version: string };
```

**After (pattern for each):**
```typescript
const healthData = await response.json();
if (typeof healthData?.status !== 'string') {
    status = 'degraded';
    // continue to next check
} else {
    version = typeof healthData.version === 'string' ? healthData.version : 'unknown';
}
```

Apply to all 4 `as` casts (lines 349, 361, 375, 388).

**Validation:** Return malformed JSON from health endpoint — should degrade gracefully, not throw.

---

### Group 3 — AdminDashboard & UploadDialog Migration

**Rationale:** These files bypass the API client entirely. Migrate to typed wrappers. This is the highest-effort group but eliminates 19+ raw `fetch()` calls.

#### 3a. F-04 — AdminDashboard → use `userApi` and `explorerApi`

**File:** `frontend/src/pages/AdminDashboard.tsx`

Replace raw fetch calls with existing typed wrappers:

| Line(s) | Raw fetch | Replace with |
|---------|-----------|-------------|
| 156 | `fetch(\`${API_BASE}/users?${params}\`)` | `listUsers(roleFilter, departmentFilter)` from `userApi.ts` |
| 164 | `fetch('/departments')` | `fetchApi('/departments')` or new `getDepartments()` in `explorerApi.ts` |
| 176 | `fetch(\`${API_BASE}/departments/${dept.id}/subjects\`)` | `fetchApi(\`/departments/${dept.id}/subjects\`)` or new wrapper |
| 197 | `fetch(\`/departments/${deptId}/semesters\`)` | `fetchApi(\`/departments/${deptId}/semesters\`)` or new wrapper |
| 252 | `fetch(\`${API_BASE}/users\`, { method: 'POST' })` | `createUser(userData)` from `userApi.ts` |
| 295 | `fetch(\`${API_BASE}/users/${userToDelete}\`, { method: 'DELETE' })` | `deleteUser(userToDelete)` from `userApi.ts` |

For remaining admin endpoints without existing wrappers (subjects CRUD, departments CRUD, etc.), either:
- Add typed functions to `explorerApi.ts` / a new `adminApi.ts`, OR
- Use `fetchApi<T>()` directly with proper type parameters.

**Key benefit:** All admin operations get 401 retry, consistent error parsing, and typed responses.

**Validation:**
1. Admin login → user list loads (no 401 on stale token).
2. Create user → duplicate email shows DuplicateError toast (not generic error).
3. Delete user → no crash on empty response (F-02 fix).

---

#### 3b. F-05 — UploadDialog → use `audioApi` wrappers

**File:** `frontend/src/components/explorer/UploadDialog.tsx`

| Line(s) | Raw fetch | Replace with |
|---------|-----------|-------------|
| 120 | `fetch(\`/api/audio/pipeline-status/${processing.jobId}\`)` | `getPipelineStatus(processing.jobId)` from `audioApi.ts` |
| 233 | `fetch('/api/audio/upload-document', ...)` | `fetchFormData('/audio/upload-document', formData)` from `client.ts` |
| 272 | `fetch('/api/audio/process-pipeline', ...)` | `startPipeline(selectedFile, topic, moduleId)` from `audioApi.ts` |

Note: `startPipeline` in `audioApi.ts` already handles FormData construction (file, topic, moduleId). The UploadDialog duplicates this logic.

**Validation:**
1. Upload audio file → pipeline starts, polling works.
2. Upload document → completes without auth error.
3. Token expires mid-upload → retry handles it.

---

### Group 4 — Type Safety & Cleanup (`explorerApi.ts`, `audioApi.ts`)

**Rationale:** Low-effort fixes that improve type safety and remove dead code.

#### 4a. F-06 — Add explicit return types to 15 CRUD functions

**File:** `frontend/src/api/explorerApi.ts:88–179`

Add `<T>` type parameters and/or return type annotations to all untyped functions:

```typescript
// Before:
export async function createDepartment(name: string, code: string) {
    return fetchApi('/departments', { ... });
}

// After:
export async function createDepartment(name: string, code: string): Promise<FileSystemNode> {
    return fetchApi<FileSystemNode>('/departments', { ... });
}
```

Functions to fix: `createDepartment`, `createSemester`, `createSubject`, `createModule`, `updateDepartment`, `updateSemester`, `updateSubject`, `updateModule`, `updateNote`, `deleteDepartment`, `deleteSemester`, `deleteSubject`, `deleteModule`, `deleteNote`, `deleteNoteCascade` (already typed at line 171 — verify).

Use `FileSystemNode` for create/update returns, `void` for delete returns.

**Validation:** `npm run build` — no `unknown` return types, no type errors.

---

#### 4b. F-14 — Remove redundant `.toString()` in `audioApi.ts`

**File:** `frontend/src/api/audioApi.ts:95`

**Before:**
```typescript
formData.append('moduleId', moduleId.toString());
```

**After:**
```typescript
formData.append('moduleId', moduleId);
```

**Validation:** `npm run build` passes.

---

#### 4c. F-15 — `NetworkError` already re-exported (handled in 1b)

The re-export at `client.ts:404` is addressed in Fix 1b. No separate action needed. The barrel `index.ts` uses `export * from './client'` (line 28), so `NetworkError` will automatically be available via `import { NetworkError } from '@/api'`.

---

## Verification Checklist

After all fix groups are applied:

- [ ] `npm run build` passes (TypeScript strict mode)
- [ ] `npm run lint` passes
- [ ] `npm test` passes (unit tests)
- [ ] Manual smoke test: Create department → rename → delete (no crash on 204)
- [ ] Manual smoke test: Admin login → user CRUD (uses typed API, not raw fetch)
- [ ] Manual smoke test: Upload audio → pipeline starts → polling works → complete
- [ ] Manual smoke test: Disconnect network → API call throws `NetworkError`
- [ ] Manual smoke test: Staff user hits admin endpoint → `PermissionError` with clear message
- [ ] Manual smoke test: Stale token → 401 retry works for both normal and admin flows
- [ ] Grep `frontend/src/` for raw `fetch(` — remaining instances should only be in `client.ts` internals and `firebaseClient.ts`
- [ ] Grep for `as {` in `client.ts` — no unsafe type assertions remain

---

## Risk Notes

1. **AdminDashboard refactor (Group 3a) is highest risk** — it touches 16+ call sites in a 2147-line file. Test every admin operation after migration. Consider doing it in sub-PRs (user CRUD first, then department/subject operations).

2. **Timeout change (1c) affects all API calls** — the 30s default may be too short for KG batch processing and audio pipeline. Consider passing `timeoutMs: 120_000` for `processKGBatch` and `startPipeline` specifically.

3. **Refresh cooldown (1d)** — if a user legitimately gets a new token that's immediately invalid (e.g., account disabled), the 5s cooldown means they'll see `AuthError` instead of an infinite loop. This is the desired behavior but may confuse users — ensure the UI surfaces `AuthError` with a "please log in again" message.

4. **Health check migration (2a)** — health endpoints are not under `/api` prefix. The `executeWithRetry` function prepends `API_BASE`. Either pass the full URL or add a `skipBase` parameter. The current plan passes full URLs directly.

5. **UploadDialog migration (3b)** — `startPipeline` in `audioApi.ts` constructs FormData internally. The UploadDialog also appends `moduleId.toString()` (line 270). After switching to `startPipeline`, verify that the `moduleId` handling matches — `audioApi.ts:95` has the same `.toString()` (fixed in 4b).

6. **`PermissionError` (1f)** — adding a new error class means consumers need to handle it. Check if any UI components have catch blocks that should display permission errors specifically. AdminDashboard currently shows generic error toasts.
