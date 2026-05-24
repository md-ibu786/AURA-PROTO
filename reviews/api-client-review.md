# API Client Layer & Data Fetching Pipeline Review

**Reviewed:** 2026-05-24  
**Scope:** `frontend/src/api/` (client.ts, explorerApi.ts, audioApi.ts, userApi.ts, errors.ts, index.ts)  
**Supporting files reviewed:** useAuthStore.ts, useExplorerStore.ts, useKGProcessing.ts, useUsageApi.ts, useSettingsApi.ts, ExplorerPage.tsx, AdminDashboard.tsx, UploadDialog.tsx, vite.config.ts, kg.types.ts, FileSystemNode.ts, types/\*, firebaseClient.ts, client.test.ts

---

## Summary

The API client layer is well-structured with a centralized fetch wrapper, typed generics, consistent auth injection, and 401 retry logic. The error class hierarchy (`DuplicateError`, `AuthError`, `NetworkError`) enables typed error handling. The architecture is sound. However, there are several concrete issues ranging from dead code to missing timeout handling and inconsistent API client adoption.

---

## Findings

### F-01 — `NetworkError` is defined but never thrown (Dead Code)

**Severity:** High  
**File:** `frontend/src/api/errors.ts` (lines 70–74) and `frontend/src/api/client.ts` (line 28)  
**Description:** The file header at `client.ts:28` states *"Network failures throw NetworkError"*, but the actual implementation never throws `NetworkError`. When the native `fetch()` itself fails (e.g., DNS failure, network down, CORS block), it throws a native `TypeError`, which propagates uncaught and untyped. The `NetworkError` class in `errors.ts` is dead code — never instantiated anywhere in the codebase.

**Impact:** Consumers cannot reliably `catch (e) { if (e instanceof NetworkError) ... }` to distinguish network failures from application errors. The grep for `NetworkError` across the entire `frontend/src/` directory returns only the definition and documentation — zero usage.

**Fix:** Wrap the native `fetch()` calls in `executeWithRetry` (and `checkHealth`) with a try-catch that converts `TypeError` to `NetworkError`:

```typescript
// In executeWithRetry, around the initial fetch:
let response: Response;
try {
    response = await fetch(url, options);
} catch (e) {
    if (e instanceof TypeError) {
        throw new NetworkError(`Network request failed: ${e.message}`);
    }
    throw e;
}
```

Then re-export `NetworkError` from `client.ts` and `index.ts`.

---

### F-02 — `fetchApi<void>` on DELETE operations will throw on empty-body responses

**Severity:** High  
**File:** `frontend/src/api/client.ts` (line 200), `frontend/src/api/userApi.ts` (line 116), `frontend/src/api/explorerApi.ts` (lines 152–168, 179)  
**Description:** `fetchApi<T>` unconditionally calls `response.json()` on line 200. DELETE endpoints commonly return `204 No Content` or an empty body. Calling `.json()` on an empty body throws `SyntaxError: Unexpected end of JSON input`. This affects:
- `deleteUser()` in `userApi.ts` — returns `fetchApi<void>`
- `deleteDepartment()`, `deleteSemester()`, `deleteSubject()`, `deleteModule()`, `deleteNote()`, `deleteNoteCascade()` in `explorerApi.ts`

**Note:** This currently works only because the backend appears to return a JSON body even for DELETE responses. If the backend ever changes to return 204, all delete operations will break silently.

**Fix:** Add an early return for `void`-typed responses or for 204 status:

```typescript
// In fetchApi, after the response.ok check:
if (response.status === 204 || response.headers.get('content-length') === '0') {
    return undefined as T;
}
return response.json();
```

Or, create a separate `fetchVoid` wrapper for DELETE operations that skips JSON parsing.

---

### F-03 — No request timeout handling anywhere in the API layer

**Severity:** High  
**File:** `frontend/src/api/client.ts` (entire file), `frontend/src/api/audioApi.ts` (entire file)  
**Description:** None of the fetch wrappers (`fetchApi`, `fetchBlob`, `fetchFormData`, `executeWithRetry`, `checkHealth`) accept or set an `AbortSignal`. If the backend hangs (e.g., during a long KG batch processing call, a PDF generation, or an audio transcription), the request will hang indefinitely with no UI feedback or user recourse.

The grep for `AbortController` and `AbortSignal` across the entire `frontend/src/` directory returned zero results.

**Particularly risky endpoints:**
- `/audio/process-pipeline` — long-running audio processing
- `/v1/kg/process-batch` — knowledge graph batch processing
- `/pdfs/zip` — zip generation for large file sets

**Fix:** Add a configurable timeout to `executeWithRetry`:

```typescript
async function executeWithRetry(
    url: string,
    options: RequestInit,
    timeoutMs: number = 30_000
): Promise<Response> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

    // If caller already provided a signal, link them
    if (options.signal) {
        options.signal.addEventListener('abort', () => controller.abort());
    }

    try {
        const response = await fetch(url, {
            ...options,
            signal: controller.signal,
        });
        return response;
    } catch (e) {
        if (e instanceof DOMException && e.name === 'AbortError') {
            throw new NetworkError(`Request timed out after ${timeoutMs}ms: ${url}`);
        }
        throw e;
    } finally {
        clearTimeout(timeoutId);
    }
}
```

For long-running operations (`startPipeline`, `processKGBatch`), pass a higher timeout or expose the signal for consumer cancellation.

---

### F-04 — AdminDashboard.tsx bypasses the API client entirely (raw `fetch()` calls)

**Severity:** High  
**File:** `frontend/src/pages/AdminDashboard.tsx` (lines 156, 164, 176, 197, 252, 295, 330, 360, 389, 415, 433, 459, 482, 500, 531, 574)  
**Description:** `AdminDashboard.tsx` contains **16+ raw `fetch()` calls** that bypass the centralized API client. This means:
- **No 401 retry logic** — stale tokens cause hard failures
- **No DuplicateError detection** — 409 conflicts are not typed
- **No consistent error parsing** — each call parses errors differently
- **Inconsistent auth header injection** — some calls include auth headers, others don't (e.g., line 164: `fetch('/departments')` has no auth header)
- **No centralized error handling** — each catch block has ad-hoc logic

**Impact:** Admin users have a degraded experience compared to staff/student users. Token refresh doesn't apply to any admin operation.

**Fix:** Refactor AdminDashboard to use `fetchApi`, `fetchFormData` from the API client, or at minimum create typed wrappers in `userApi.ts` / `explorerApi.ts` for the admin-specific endpoints. The existing `userApi.ts` already has `listUsers`, `createUser`, `updateUser`, `deleteUser` — these should be used instead of raw fetch.

---

### F-05 — UploadDialog.tsx bypasses the API client (raw `fetch()` calls)

**Severity:** Medium  
**File:** `frontend/src/components/explorer/UploadDialog.tsx` (lines 120, 233, 272)  
**Description:** UploadDialog uses raw `fetch()` for:
- Polling pipeline status (line 120): `fetch('/api/audio/pipeline-status/${processing.jobId}')`
- Uploading documents (line 233): `fetch('/api/audio/upload-document', ...)`
- Starting pipeline (line 272): `fetch('/api/audio/process-pipeline', ...)`

These bypass the API client's auth injection and error handling. The existing `audioApi.ts` already provides `startPipeline()` and `getPipelineStatus()` — they are not being used.

**Impact:** Inconsistent auth handling. If the user's token expires during a long upload, there's no retry.

**Fix:** Replace raw `fetch()` calls with `startPipeline()`, `getPipelineStatus()`, and `fetchFormData()` from `audioApi.ts` / `client.ts`.

---

### F-06 — Missing explicit return types on CRUD functions in `explorerApi.ts`

**Severity:** Medium  
**File:** `frontend/src/api/explorerApi.ts` (lines 89, 96, 103, 110, 117, 124, 131, 138, 145, 152, 156, 160, 164, 168, 179)  
**Description:** 15 functions call `fetchApi('/...')` without an explicit type parameter or return type annotation. Examples:

```typescript
export async function createDepartment(name: string, code: string) {
    return fetchApi('/departments', { ... });
    // Implicit return type: Promise<unknown>
}
```

Without a type parameter `<T>`, TypeScript infers `T` as `unknown`, making the return value untyped. This affects: `createDepartment`, `createSemester`, `createSubject`, `createModule`, `updateDepartment`, `updateSemester`, `updateSubject`, `updateModule`, `updateNote`, `deleteDepartment`, `deleteSemester`, `deleteSubject`, `deleteModule`, `deleteNote`, `deleteNoteCascade`.

**Fix:** Add explicit type parameters or return type annotations:

```typescript
export async function createDepartment(name: string, code: string): Promise<FileSystemNode> {
    return fetchApi<FileSystemNode>('/departments', { ... });
}
```

---

### F-07 — `checkHealth()` uses unsafe type assertions instead of validation

**Severity:** Medium  
**File:** `frontend/src/api/client.ts` (lines 349, 361, 375, 388)  
**Description:** Health check responses are cast with `as` type assertions:

```typescript
const healthData = await response.json() as { status: string; version: string };
const readyData = await response.json() as { status: string; database: string };
const redisData = await response.json() as { status: string };
chatStatus = await response.json() as ChatHealthStatus;
```

If the backend returns an unexpected shape (e.g., error page from a reverse proxy, partial response), these assertions silently produce malformed objects. The `as` keyword provides zero runtime validation.

**Fix:** Add basic runtime validation or use a type guard:

```typescript
const healthData = await response.json();
if (typeof healthData?.status !== 'string') {
    status = 'degraded';
    return;
}
version = typeof healthData.version === 'string' ? healthData.version : 'unknown';
```

---

### F-08 — `checkHealth()` bypasses `executeWithRetry` — no 401 handling

**Severity:** Medium  
**File:** `frontend/src/api/client.ts` (lines 324–392)  
**Description:** `checkHealth()` uses a custom `fetchHealth` helper that calls raw `fetch()` with auth headers but without `executeWithRetry`. If the token is stale when health check fires (it runs on a 30-second interval per `SettingsPage.tsx`), the health check will report services as "degraded" instead of retrying with a fresh token.

**Fix:** Route health checks through `executeWithRetry`, or at minimum trigger a token refresh on 401:

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

Note: Health endpoints (`/health`, `/ready`, `/health/redis`) are not under `/api` prefix, so `API_BASE` prefix must be omitted. The fix should pass the full URL to `executeWithRetry`.

---

### F-09 — `tokenRefreshPromise` can cause a refresh storm on persistently invalid tokens

**Severity:** Medium  
**File:** `frontend/src/api/client.ts` (lines 50, 96–121)  
**Description:** When multiple concurrent requests receive 401, they correctly share a single `tokenRefreshPromise`. However, after the promise resolves and `.finally()` sets `tokenRefreshPromise = null`, each retry request attempts its own fetch. If ALL retries also get 401 (because the new token is still invalid), EACH will independently trigger a NEW token refresh, creating a cascade.

Sequence:
1. Request A, B, C all get 401
2. They share one `tokenRefreshPromise`
3. Promise resolves with new token
4. `tokenRefreshPromise = null` runs
5. A, B, C each retry with new token
6. All three get 401 again
7. Each independently creates a new `tokenRefreshPromise` (3 refresh attempts)

**Fix:** Add a guard to prevent repeated refresh attempts within a short time window:

```typescript
let lastRefreshAttempt = 0;
const REFRESH_COOLDOWN_MS = 5000;

if (response.status === 401 && import.meta.env.VITE_USE_MOCK_AUTH !== 'true') {
    const now = Date.now();
    if (now - lastRefreshAttempt < REFRESH_COOLDOWN_MS) {
        throw new AuthError('Token refresh already attempted recently');
    }
    lastRefreshAttempt = now;
    // ... existing refresh logic
}
```

---

### F-10 — Inconsistent error response parsing across fetch wrappers

**Severity:** Medium  
**File:** `frontend/src/api/client.ts` (lines 185, 224, 250)  
**Description:** Three different error parsing approaches are used:

| Function | Error parsing | Behavior |
|----------|--------------|----------|
| `fetchApi` (line 185) | `response.json().catch(...)` | Assumes JSON error body, falls back to `{ detail: 'Network error' }` |
| `fetchBlob` (line 224) | `parseErrorMessage(response)` | Tries `response.text()` → JSON parse → raw text fallback |
| `fetchFormData` (line 250) | `response.json().catch(...)` | Same as `fetchApi` |

The `parseErrorMessage` function (lines 131–145) is more robust — it handles non-JSON error bodies — but is only used by `fetchBlob`. If the backend returns an HTML error page (e.g., from a reverse proxy), `fetchApi` and `fetchFormData` will silently return `{ detail: 'Network error' }` while `fetchBlob` would surface the actual content.

**Fix:** Unify all error parsing through `parseErrorMessage`:

```typescript
if (!response.ok) {
    const message = await parseErrorMessage(response);
    
    if (response.status === 409) {
        // Try to extract DuplicateError details
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

---

### F-11 — No request cancellation support (no AbortSignal propagation)

**Severity:** Medium  
**File:** `frontend/src/api/client.ts` (entire file)  
**Description:** None of the fetch wrapper signatures accept an `AbortSignal` parameter. This means:
- React Query's built-in query cancellation (which passes `signal`) is not supported
- When a user navigates away, in-flight requests continue to completion
- There's no way for a consumer to cancel a long-running request

While React Query can ignore stale results, the network request itself continues consuming bandwidth and server resources.

**Fix:** Thread `AbortSignal` through the wrapper:

```typescript
async function fetchApi<T>(
    endpoint: string,
    options?: RequestInit
): Promise<T> {
    // options.signal is already in RequestInit, just pass it through
    // The fix is to not lose it during the spread
    const response = await executeWithRetry(url, {
        ...options,
        headers: { ... },
        signal: options?.signal, // Ensure signal is passed through
    });
}
```

And document that callers can pass `{ signal: controller.signal }`.

---

### F-12 — Missing 403 Forbidden handling

**Severity:** Medium  
**File:** `frontend/src/api/client.ts` (lines 168–201)  
**Description:** The error handling in `fetchApi` covers:
- 401 → retry with new token
- 409 → DuplicateError
- Everything else → generic Error

There is no handling for 403 Forbidden, which indicates an authenticated user lacks permission. This is important in AURA-NOTES-MANAGER because of its role-based access (admin/staff/student). A staff member attempting an admin action should get a clear "insufficient permissions" error, not a generic error.

**Fix:** Add a `PermissionError` class or handle 403 explicitly:

```typescript
if (response.status === 403) {
    throw new PermissionError(
        error.detail || 'You do not have permission to perform this action'
    );
}
```

---

### F-13 — `fetchApi` sets `Content-Type: application/json` on GET requests

**Severity:** Low  
**File:** `frontend/src/api/client.ts` (line 179)  
**Description:** Every `fetchApi` call includes `'Content-Type': 'application/json'` in headers, even for GET requests where there is no body. While this doesn't cause functional issues (servers typically ignore Content-Type on GET), it's semantically incorrect and could confuse some backend middleware or logging.

**Fix:** Only set Content-Type when there's a body:

```typescript
const hasBody = options?.body !== undefined;
headers: {
    ...(hasBody ? { 'Content-Type': 'application/json' } : {}),
    ...authHeaders,
    ...options?.headers,
},
```

---

### F-14 — `startPipeline` has redundant `.toString()` call

**Severity:** Low  
**File:** `frontend/src/api/audioApi.ts` (line 49)  
**Description:**
```typescript
if (moduleId !== undefined) {
    formData.append('moduleId', moduleId.toString());
}
```
`moduleId` is already typed as `string | undefined`. The `.toString()` call is a no-op.

**Fix:** Remove `.toString()`:
```typescript
formData.append('moduleId', moduleId);
```

---

### F-15 — `NetworkError` not re-exported from barrel `index.ts`

**Severity:** Low  
**File:** `frontend/src/api/index.ts` (line 30), `frontend/src/api/client.ts` (line 403)  
**Description:** `DuplicateError` and `AuthError` are re-exported from `client.ts` (line 403) and thus available via `import { DuplicateError } from '@/api'`. However, `NetworkError` is only exported from `errors.ts` and never re-exported from `client.ts` or `index.ts`. Consumers must import directly from `@/api/errors` to use it.

**Fix:** Add `NetworkError` to the re-exports in `client.ts`:
```typescript
export { DuplicateError, AuthError, NetworkError } from './errors';
```

---

### F-16 — No response validation for API payloads

**Severity:** Low  
**File:** `frontend/src/api/client.ts` (line 200), all API modules  
**Description:** `fetchApi<T>` calls `response.json()` and returns it as `T` without runtime validation. If the backend returns a different shape due to a bug, version mismatch, or partial deployment, the frontend will silently use malformed data, potentially causing undefined behavior downstream.

This is a design tradeoff — adding Zod or similar validation to every API call adds overhead. For a production app, at minimum, critical paths (auth, tree fetching) should have runtime validation.

**Fix (optional):** Add a utility for optional response validation:

```typescript
async function fetchApi<T>(
    endpoint: string,
    options?: RequestInit,
    validate?: (data: unknown) => data is T
): Promise<T> {
    // ...
    const data = await response.json();
    if (validate && !validate(data)) {
        throw new Error(`Invalid response from ${endpoint}`);
    }
    return data as T;
}
```

---

## Architecture Observations

### Positive Patterns

1. **Centralized auth injection** — `getAuthHeader()` ensures all API calls include tokens. The shared `tokenRefreshPromise` prevents concurrent refresh races.
2. **Typed generics** — `fetchApi<T>` provides compile-time type safety for responses.
3. **Typed error hierarchy** — `DuplicateError` and `AuthError` enable specific catch handling.
4. **React Query integration** — Consumer hooks (`useKGProcessing`, `useSettingsApi`, `useUsageApi`) properly use TanStack Query with stale times, query key factories, and cache invalidation.
5. **File headers** — All files have comprehensive documentation headers per project conventions.
6. **Test coverage** — `client.test.ts` covers key scenarios: 409 handling, auth token injection, 401 retry failure.

### Concerns

1. **API client adoption is inconsistent** — AdminDashboard (16+ raw fetch calls) and UploadDialog (3 raw fetch calls) bypass the client, creating two tiers of API reliability.
2. **`backend/` vs `server/` split is absent in ANM** — Unlike AURA-CHAT, AURA-NOTES-MANAGER has a single backend, so this is not an issue here.
3. **Health check is a separate path** — `checkHealth()` doesn't use the standard wrappers, leading to divergent behavior.

---

## Priority-Ordered Remediation

| Priority | ID | Issue | Effort |
|----------|----|-------|--------|
| 1 | F-04 | AdminDashboard raw fetch bypass | 2-3 hours |
| 2 | F-02 | `fetchApi<void>` breaks on 204/empty body | 30 min |
| 3 | F-03 | No request timeout handling | 1 hour |
| 4 | F-01 | `NetworkError` dead code | 30 min |
| 5 | F-05 | UploadDialog raw fetch bypass | 1 hour |
| 6 | F-09 | Token refresh storm on persistent 401 | 30 min |
| 7 | F-10 | Inconsistent error parsing | 30 min |
| 8 | F-08 | Health check no 401 retry | 30 min |
| 9 | F-12 | Missing 403 handling | 30 min |
| 10 | F-06 | Missing return types on CRUD functions | 1 hour |
| 11 | F-07 | Unsafe type assertions in health check | 30 min |
| 12 | F-11 | No AbortSignal propagation | 1 hour |
| 13 | F-13 | Content-Type on GET requests | 15 min |
| 14 | F-14 | Redundant `.toString()` | 5 min |
| 15 | F-15 | NetworkError not in barrel export | 5 min |
| 16 | F-16 | No response validation (design choice) | 2+ hours (optional) |
