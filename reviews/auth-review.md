# Authentication Pipeline Review — AURA-NOTES-MANAGER

**Reviewer:** Review Subagent
**Date:** 2026-05-24
**Scope:** Login, logout, token handling, session persistence, RBAC, frontend auth state
**Files Reviewed:**
- `api/auth.py`
- `api/auth_sync.py`
- `api/users.py`
- `frontend/src/pages/LoginPage.tsx`
- `frontend/src/stores/useAuthStore.ts`
- `frontend/src/api/firebaseClient.ts`
- `frontend/src/components/ProtectedRoute.tsx`
- `frontend/src/App.tsx`
- `frontend/src/api/client.ts`
- `api/config.py`, `api/models.py`, `api/validators.py`, `api/limiter.py`
- `api/main.py`, `frontend/src/main.tsx`, `frontend/vite.config.ts`
- `api/tests/test_rbac.py` (test coverage check)

---

## Summary

The authentication pipeline is **well-structured** overall with a clear separation between Firebase Auth (identity), Firestore (profile/RBAC), and Zustand (frontend state). The RBAC system is comprehensive, the `onIdTokenChanged` listener handles session restoration correctly, and the test suite covers the core auth dependency chain. However, there are several security and reliability issues that should be addressed, ranging from a critical mock-token forge risk to silent error swallowing that can leave the system in an inconsistent state.

| Severity | Count |
|----------|-------|
| Critical | 1 |
| High | 5 |
| Medium | 8 |
| Low | 6 |

---

## Critical

### 1. Mock Token Scheme Is Trivially Forgeable

**File:** `api/auth.py`, lines 79–96
**Severity:** Critical (if misconfigured in production)

The `_verify_mock_token` function parses role and uid directly from the token string pattern `mock-token-{role}-{uid}`. Anyone who knows this pattern can forge an admin token by sending `Authorization: Bearer mock-token-admin-attacker-uid`.

**Guard:** The mock path is gated by `TESTING=true` AND `USE_REAL_FIREBASE=false` (lines 54–55). This is safe *as long as* these env vars are correctly set in production.

**Risk:** If a deployment misconfiguration sets `TESTING=true` or forgets to set `USE_REAL_FIREBASE=true`, the entire auth system is bypassed.

**Fix Suggestions:**
- Add a startup assertion in `config.py` that fails hard if `USE_REAL_FIREBASE=false` in production environments.
- Log a CRITICAL-level warning at startup when mock auth is active.
- Consider removing the mock auth path from the production build entirely using an environment-gated import.

---

## High

### 2. Sensitive Error Details Leaked to Client

**File:** `api/auth.py`, lines 66–72
**Severity:** High

```python
detail = f"Invalid authentication token: {str(exc)}"
```

The raw exception message from `firebase_admin.auth.verify_id_token()` is passed directly to the HTTP response. Firebase SDK exceptions can contain internal details such as project IDs, token internals, or library version info.

**Fix:** Return generic messages to the client and log the full exception server-side:
```python
logger.warning("Invalid token: %s", exc)
raise HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired authentication token",
    headers={"WWW-Authenticate": "Bearer"},
)
```

### 3. Silent Error Swallowing in `_merge_custom_claims`

**File:** `api/users.py`, lines 51–58
**Severity:** High

```python
def _merge_custom_claims(user_id: str, updates: dict[str, str]) -> None:
    ...
    try:
        ...
    except Exception:
        pass
```

When updating a user's role, the code first updates Firestore, then calls `_merge_custom_claims` to update Firebase Auth custom claims. If the custom claims update fails silently, the user's ID token will contain their *old* role. Since `get_current_user` in `auth.py` line 119 uses the token role to override the Firestore role, the user effectively retains their old permissions until their token expires.

**Fix:** At minimum, log the error. Ideally, make this function return a success/failure boolean and have the caller decide whether to roll back the Firestore update or return a warning to the admin:
```python
except Exception as exc:
    logger.error("Failed to update custom claims for %s: %s", user_id, exc)
    # Optionally raise or return False
```

### 4. Silent Error Swallowing in User Update Endpoints

**File:** `api/users.py`, lines 531, 537, 555, 558, 565
**Severity:** High

Multiple `except Exception: pass` blocks when syncing display name, email, and disabled status to Firebase Auth. This creates a state where Firestore says one thing but Firebase Auth says another:
- Email mismatch → user can't log in with new email
- Display name mismatch → cosmetic inconsistency
- Disabled status mismatch → user can still authenticate even though Firestore says "disabled" (this is a **security issue**)

**Fix:** At minimum, log each failure. For the disabled status case specifically, this should be treated as a hard failure since it has security implications:
```python
if update_data.status == "disabled":
    try:
        firebase_auth.update_user(user_id, disabled=True)
    except Exception as exc:
        logger.error("CRITICAL: Failed to disable user %s in Firebase Auth: %s", user_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to disable user in authentication system"
        )
```

### 5. Race Condition: Concurrent `refreshUser` Calls During Login

**File:** `frontend/src/stores/useAuthStore.ts`, lines 221–268 and 444–453
**Severity:** High

When a user logs in:
1. `login()` calls `signInWithEmailAndPassword()` → Firebase Auth state changes
2. The `onIdTokenChanged` listener (line 444) fires and calls `refreshUser()`
3. `login()` then also calls `refreshUser()` (line 262)

Two concurrent `refreshUser()` calls race against each other, both making HTTP requests to `/api/auth/me`. While the store state should converge to the same value, this causes:
- Unnecessary duplicate network requests
- Potential UI flicker as `set()` is called twice
- If one fails and the other succeeds, the final state depends on timing

**Fix:** Add a guard to prevent concurrent refreshes:
```typescript
refreshUser: async () => {
    const { firebaseUser, _refreshPromise } = get();
    if (_refreshPromise) return _refreshPromise;
    if (!firebaseUser) { ... }

    const promise = (async () => { /* existing logic */ })();
    set({ _refreshPromise: promise });
    promise.finally(() => set({ _refreshPromise: null }));
    return promise;
}
```

### 6. No Rate Limiting on `/api/auth/me` Endpoint

**File:** `api/users.py`, line 71 (endpoint definition)
**Severity:** High

The `/api/auth/me` endpoint has no rate limiting. It's called on every page load and token refresh. While it requires authentication, a compromised token or brute-force attempt could flood this endpoint, causing excessive Firestore reads. The sync endpoint (`/api/auth/sync`) correctly has `@limiter.limit("5/minute")` but `/api/auth/me` does not.

**Fix:** Add rate limiting:
```python
@router.get("/auth/me", response_model=UserResponse)
@limiter.limit("30/minute")
async def get_me(request: Request, user: FirestoreUser = Depends(get_current_user)):
```

---

## Medium

### 7. Redundant Firestore Read in `/api/auth/me`

**File:** `api/users.py`, lines 71–74
**Severity:** Medium (performance)

```python
async def get_me(user: FirestoreUser = Depends(get_current_user)):
    user_doc = db.collection("users").document(user.uid).get()
```

The `get_current_user` dependency (in `auth.py`) already fetches and parses the user document from Firestore. The `get_me` endpoint fetches it *again* to read `createdAt`/`updatedAt` fields. This doubles Firestore read costs for every authenticated page load.

**Fix:** Either:
- Add `createdAt` and `updatedAt` to the `FirestoreUser` model so they're available from the dependency, OR
- Accept that the `/api/auth/me` response doesn't include these fields (they're rarely needed on the client)

### 8. Token Refresh Doesn't Trigger `isLoading` State

**File:** `frontend/src/stores/useAuthStore.ts`, lines 232–268
**Severity:** Medium

`refreshUser` only sets `isLoading: false` when it finishes (or fails). It never sets `isLoading: true` at the start. If a token refresh is triggered by `onIdTokenChanged` (e.g., after an hour when the token auto-refreshes), the loading state remains `false` throughout, and if the refresh fails, the user is silently logged out without any loading indicator or error message.

**Fix:** Set `isLoading: true` at the start of `refreshUser`:
```typescript
refreshUser: async () => {
    const { firebaseUser } = get();
    if (!firebaseUser) {
        set({ user: null, isLoading: false });
        return;
    }
    set({ isLoading: true }); // Add this
    try {
        ...
```

### 9. Silent Logout on Temporary Network Errors

**File:** `frontend/src/stores/useAuthStore.ts`, lines 265–268
**Severity:** Medium

```typescript
} catch (error) {
    console.error('Failed to refresh user:', error);
    set({ user: null, isLoading: false });
}
```

Any network error during `refreshUser` (timeout, DNS failure, server restart) causes the user to be silently logged out. There's no retry mechanism and no error message shown to the user.

**Fix:** Distinguish between auth errors (should log out) and network errors (should retry or show error):
```typescript
} catch (error) {
    if (error instanceof TypeError && error.message.includes('fetch')) {
        // Network error - don't log out, show retry option
        console.warn('Network error during refresh, keeping session');
        set({ isLoading: false, error: 'Network error. Please check your connection.' });
    } else {
        set({ user: null, isLoading: false });
    }
}
```

### 10. LoginPage Navigation Race Condition

**File:** `frontend/src/pages/LoginPage.tsx`, lines 41–52 and 76–84
**Severity:** Medium

The `useEffect` redirects when `user` is set (triggered by `onIdTokenChanged`), and `handleSubmit` also redirects after `login()` resolves. If the auth state listener sets `user` before `handleSubmit` finishes, two `navigate()` calls execute, which can cause React Router warnings or flickering.

**Fix:** Remove the `useEffect` redirect and handle all navigation in `handleSubmit`. Or, rely solely on the `useEffect` and don't navigate in `handleSubmit`:
```typescript
const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    if (!email || !password) { ... }
    try {
        await login(email, password);
        // Navigation handled by useEffect watching `user`
    } catch (err) {
        console.error('Login failed:', err);
    }
};
```

### 11. `datetime.utcnow()` Is Deprecated

**File:** `api/auth_sync.py`, lines 230, 281, 362
**File:** `api/users.py`, lines 334, 523
**File:** `api/models.py`, lines 63, 67
**Severity:** Medium

`datetime.utcnow()` is deprecated since Python 3.12. It returns a naive datetime, which can cause subtle bugs when comparing timestamps.

**Fix:** Use `datetime.now(datetime.timezone.utc)` or `datetime.now(datetime.UTC)` (Python 3.11+).

### 12. `allow_headers=["*"]` and `allow_methods=["*"]` in CORS

**File:** `api/main.py`, lines 230–236
**Severity:** Medium

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

While `allow_credentials=True` with specific origins is fine (the app correctly restricts origins), allowing all methods and headers is overly permissive. In production, this should be locked down to only the methods and headers actually used.

**Fix:** Enumerate allowed methods and headers:
```python
allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
allow_headers=["Authorization", "Content-Type"],
```

### 13. No CSRF Protection Despite `allow_credentials=True`

**File:** `api/main.py`, line 233
**Severity:** Medium

The CORS configuration sets `allow_credentials=True`. While the app uses Bearer tokens (not cookies) for authentication, the `allow_credentials=True` flag allows cookies to be sent. If any endpoint inadvertently relies on cookies, CSRF becomes a concern. The security headers middleware adds `X-Frame-Options: DENY` which helps, but there's no explicit CSRF token mechanism.

**Current Mitigation:** Bearer tokens are not automatically sent by browsers, so standard CSRF attacks don't apply to token-based auth. This is acceptable but should be documented.

**Note:** This is a low-urgency item since Bearer tokens are inherently CSRF-safe. Flag for documentation rather than immediate code change.

### 14. No `X-Content-Type-Options` on Static PDF Responses

**File:** `api/main.py`, lines 308–320
**Severity:** Medium (tangential to auth but security-related)

The `SecurityHeadersMiddleware` applies to all responses, which is good. However, the PDF download endpoint uses `FileResponse` which may bypass middleware depending on Starlette version. Verify that security headers are applied to static file responses.

---

## Low

### 15. Accessibility: Missing `aria-live` on Error Messages

**File:** `frontend/src/pages/LoginPage.tsx`, line 118
**Severity:** Low

```tsx
{displayError && (
    <div className="error-message">
        {displayError}
    </div>
)}
```

The error message container lacks `role="alert"` or `aria-live="assertive"`, so screen readers won't announce login errors.

**Fix:**
```tsx
<div className="error-message" role="alert" aria-live="assertive">
    {displayError}
</div>
```

### 16. Accessibility: Missing `required` Attribute on Form Inputs

**File:** `frontend/src/pages/LoginPage.tsx`, lines 96, 106
**Severity:** Low

The email and password inputs lack the HTML `required` attribute. While validation is done in JavaScript, the `required` attribute provides native browser validation hints and improves the accessibility tree.

**Fix:**
```tsx
<input id="email" type="email" required ... />
<input id="password" type="password" required ... />
```

### 17. Default Export Violates Project Style Guide

**File:** `frontend/src/pages/LoginPage.tsx`, lines 42 and 152
**Severity:** Low

```tsx
export function LoginPage() { ... }
export default LoginPage;
```

The file has both a named export and a default export. The project style guide explicitly states: "DO NOT use default exports."

**Fix:** Remove `export default LoginPage;` and update the import in `App.tsx` (which already uses the named import `import { LoginPage }`).

### 18. Inline `<style>` Tag Instead of CSS/Tailwind

**File:** `frontend/src/pages/LoginPage.tsx`, lines 121–280
**Severity:** Low

150+ lines of CSS are embedded in an inline `<style>` tag within the JSX. This is inconsistent with the project's Tailwind CSS approach (visible in other components) and makes the component harder to maintain. The styles are also not scoped, so class names could collide.

**Fix:** Extract to a dedicated CSS file (e.g., `styles/login.css`) or convert to Tailwind utility classes.

### 19. `canManageModules` Returns `false` for Admins

**File:** `frontend/src/stores/useAuthStore.ts`, lines 135–142
**Severity:** Low

```typescript
canManageModules: (departmentId?: string) => {
    const { user } = get();
    if (!user) return false;
    if (user.role === 'admin') return false; // Admins can't manage modules
```

This is intentional per the comment, but it's surprising behavior. If this is a business rule, it should be documented more clearly. An admin who tries to manage modules will get silently denied with no explanation.

### 20. `initAuthListener` Fires Correctly Under StrictMode

**File:** `frontend/src/App.tsx`, lines 56–59
**Severity:** Low (informational)

```tsx
useEffect(() => {
    const unsubscribe = initAuthListener();
    return () => unsubscribe();
}, []);
```

This correctly handles React StrictMode (double-mount in dev) by returning the unsubscribe function. No issue here — just confirming this is well-implemented.

---

## What's Done Well

1. **RBAC dependency chain** (`auth.py`): The `get_current_user → require_admin → require_role` dependency chain is clean, testable, and follows FastAPI best practices. The role-override from token claims (line 119) is the correct Firebase pattern.

2. **Rate limiting on sync endpoint** (`auth_sync.py:155`): The `@limiter.limit("5/minute")` on `/api/auth/sync` prevents abuse of the first-login provisioning flow.

3. **Security headers middleware** (`main.py`): OWASP-recommended headers (X-Content-Type-Options, X-Frame-Options, HSTS in production) are properly applied.

4. **Token refresh deduplication** (`client.ts:29–30`): The shared `tokenRefreshPromise` in `executeWithRetry` correctly prevents concurrent token refresh storms.

5. **First-user admin promotion** (`auth_sync.py:177–179`): The first user in the system automatically becomes admin — a practical bootstrap mechanism.

6. **Self-deletion prevention** (`users.py:357–360`, `auth_sync.py:300–303`): Admins cannot delete their own account.

7. **App Check integration** (`firebaseClient.ts:44–52`): ReCaptcha Enterprise App Check is properly initialized with graceful fallback.

8. **Test coverage** (`test_rbac.py`): 25+ unit tests covering mock tokens, real token errors, role enforcement, and permission helpers. The test structure with fake Firestore/Auth is clean and maintainable.

9. **`onIdTokenChanged` for session persistence** (`useAuthStore.ts:444`): Using `onIdTokenChanged` (not `onAuthStateChanged`) is the correct choice for token-based auth — it fires on token refresh, not just sign-in/sign-out.

10. **Sync-then-retry pattern** (`useAuthStore.ts:241–259`): When `/api/auth/me` returns 401, the store tries `/api/auth/sync` first (to create the Firestore document for new users) then retries. This handles first-login gracefully.

---

## Recommendations (Priority Order)

1. **P0 — Add startup guard against mock auth in production** (Critical #1)
2. **P0 — Log all swallowed exceptions in `_merge_custom_claims` and user update** (High #3, #4)
3. **P1 — Sanitize error messages before sending to client** (High #2)
4. **P1 — Add rate limiting to `/api/auth/me`** (High #6)
5. **P1 — Fix concurrent refreshUser race condition** (High #5)
6. **P2 — Don't silently log out on network errors** (Medium #9)
7. **P2 — Add `aria-live` and `required` to login form** (Low #15, #16)
8. **P3 — Replace `datetime.utcnow()` with timezone-aware alternative** (Medium #11)
9. **P3 — Tighten CORS methods/headers** (Medium #12)
10. **P3 — Deduplicate Firestore read in `/api/auth/me`** (Medium #7)
