# Auth Pipeline Fix Plan

**Source:** `reviews/auth-review.md` (20 findings: 1 critical, 5 high, 8 medium, 6 low)
**Date:** 2026-05-24
**Estimated Effort:** ~4–6 hours across 4 fix groups

---

## Overview

### Scope
Security and reliability fixes across the entire authentication pipeline: token verification, error handling, RBAC enforcement, frontend auth state, and login page UX. The review found the pipeline well-structured overall, but identified a critical mock-token forge risk, multiple silent error-swallowing patterns that can desynchronize Auth/Firestore state, a frontend race condition causing duplicate requests, and accessibility/style-guide violations on the login page.

### Affected Files

| File | Changes |
|------|---------|
| `api/auth.py` | Sanitize error messages (#2) |
| `api/config.py` | Production mock-auth guard (#1) |
| `api/users.py` | Log swallowed errors (#3, #4), rate-limit `/auth/me` (#6), deduplicate Firestore read (#7), fix `datetime.utcnow()` (#11) |
| `api/auth_sync.py` | Fix `datetime.utcnow()` (#11) |
| `api/models.py` | Fix `datetime.utcnow()` default factories (#11) |
| `api/main.py` | Tighten CORS (#12), verify static-file headers (#14), fix `datetime.utcnow()` (#11) |
| `frontend/src/stores/useAuthStore.ts` | Race condition guard (#5), isLoading during refresh (#8), network-error resilience (#9) |
| `frontend/src/pages/LoginPage.tsx` | Navigation race (#10), accessibility (#15, #16), style-guide (#17, #18) |
| `api/tests/test_rbac.py` | Update tests for sanitized error messages (#2) |

### Dependency Graph

```
Group 1 (Backend Security) ──no deps──→ can start immediately
Group 2 (Backend API)       ──no deps──→ can start immediately (parallel with Group 1)
Group 3 (Frontend Auth)     ──no deps──→ can start immediately (parallel)
Group 4 (Login Page)        ──depends on Group 3 (navigation fix uses refreshUser result)
```

Groups 1–3 are fully independent and can be executed in parallel. Group 4's navigation fix (finding #10) should be done after Group 3's refreshUser changes are in place to avoid merge conflicts in the login flow.

---

## Prerequisites

1. **Environment variable `ENVIRONMENT`** must be documented and set in all deployment configs. Currently defaults to `"development"` in `config.py` line 43. Verify that production deployments set `ENVIRONMENT=production`.

2. **Python version:** The `datetime.utcnow()` replacements use `datetime.timezone.utc` which requires Python 3.2+, or `datetime.UTC` which requires Python 3.11+. The project targets Python 3.10+ (per AGENTS.md), so use `datetime.timezone.utc` for compatibility.

3. **Test the mock auth path:** Before deploying, manually verify that `TESTING=false` and `USE_REAL_FIREBASE=true` are set in production. The startup guard (Fix 1.1) will enforce this.

---

## Fix Group 1: Backend Security Hardening

**Rationale:** Addresses the critical mock-token risk, sensitive error leakage, and silent error swallowing that can leave Auth/Firestore state desynchronized. These are the highest-priority fixes.

### Fix 1.1: Production Mock-Auth Startup Guard (Finding #1 — Critical)

**File:** `api/config.py`

**Problem:** If `TESTING=true` or `USE_REAL_FIREBASE=false` in production, the mock auth path is active and anyone can forge admin tokens with `mock-token-admin-anyuid`.

**Current code (config.py, end of file, after `auth = get_auth()`):**
```python
auth = get_auth()
```

**Changed code — add after `auth = get_auth()`:**
```python
auth = get_auth()

# ── Production safety guard ──────────────────────────────────────────
if IS_PRODUCTION:
    if not USE_REAL_FIREBASE:
        raise RuntimeError(
            "CRITICAL: USE_REAL_FIREBASE must be 'true' in production. "
            "Mock authentication is not allowed in production environments."
        )
    if os.getenv("TESTING", "false").lower() == "true":
        raise RuntimeError(
            "CRITICAL: TESTING must be 'false' in production. "
            "Test mode bypasses authentication checks."
        )
    logger.info("Production auth guard: real Firebase auth confirmed")
elif not USE_REAL_FIREBASE:
    logger.warning(
        "AUTH WARNING: Mock authentication is active. "
        "Ensure USE_REAL_FIREBASE=true in production."
    )
```

**Also add at top of file** (after existing imports):
```python
import logging

logger = logging.getLogger(__name__)
```

**Validation:**
- Run `ENVIRONMENT=production USE_REAL_FIREBASE=false python -c "from api.config import app"` → should raise `RuntimeError`
- Run `ENVIRONMENT=development USE_REAL_FIREBASE=false python -c "from api.config import app"` → should log warning, not raise
- Run existing test suite: `python -m pytest api/tests/test_rbac.py -v`

---

### Fix 1.2: Sanitize Error Messages in `verify_firebase_token` (Finding #2 — High)

**File:** `api/auth.py`

**Problem:** Raw Firebase SDK exception messages (containing project IDs, token internals) are sent to the client.

**Current code (auth.py, lines 54–75):**
```python
    try:
        auth_client = get_auth()
        decoded_token = auth_client.verify_id_token(token, clock_skew_seconds=30)
        return decoded_token
    except auth.InvalidIdTokenError as exc:
        print(f"DEBUG: Invalid token error: {exc}")
        error_detail = str(exc)
        if isinstance(exc, auth.ExpiredIdTokenError):
            error_detail = f"Authentication token has expired: {error_detail}"
        elif isinstance(exc, auth.RevokedIdTokenError):
            error_detail = f"Authentication token has been revoked: {error_detail}"
        else:
            error_detail = f"Invalid authentication token: {error_detail}"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

**Changed code:**
```python
    try:
        auth_client = get_auth()
        decoded_token = auth_client.verify_id_token(
            token, clock_skew_seconds=30
        )
        return decoded_token
    except auth.InvalidIdTokenError as exc:
        logger.warning("Invalid token: %s", exc)
        if isinstance(exc, auth.ExpiredIdTokenError):
            error_detail = "Authentication token has expired"
        elif isinstance(exc, auth.RevokedIdTokenError):
            error_detail = "Authentication token has been revoked"
        else:
            error_detail = "Invalid or expired authentication token"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error_detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as exc:
        logger.error("Authentication failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

**Also add** at top of file (after existing imports):
```python
import logging

logger = logging.getLogger(__name__)
```

**Remove:** The `print(f"DEBUG: Invalid token error: {exc}")` line (use logger instead).

**Validation:**
- Run `python -m pytest api/tests/test_rbac.py -v` — update test expectations:
  - `test_verify_firebase_token_real_error_mapping`: change `detail_prefix` parametrize values:
    - `"Invalid authentication token:"` → `"Invalid or expired authentication token"`
    - `"Authentication token has expired:"` → `"Authentication token has expired"`
    - `"Authentication token has been revoked:"` → `"Authentication token has been revoked"`
  - `test_verify_firebase_token_real_generic_error`: change assertion from `startswith("Authentication failed:")` to `== "Authentication failed"`

---

### Fix 1.3: Log and Propagate `_merge_custom_claims` Errors (Finding #3 — High)

**File:** `api/users.py`

**Problem:** If custom claims update fails, the user's ID token retains the old role indefinitely (until token expiry). The `except Exception: pass` silently masks this.

**Current code (users.py, lines 51–58):**
```python
def _merge_custom_claims(user_id: str, updates: dict[str, str]) -> None:
    """Merge updates into existing Firebase custom claims."""
    if not updates:
        return
    safe_updates = {key: value for key, value in updates.items() if value}
    if not safe_updates:
        return
    try:
        user_record = firebase_auth.get_user(user_id)
        claims = user_record.custom_claims or {}
        claims.update(safe_updates)
        firebase_auth.set_custom_user_claims(user_id, claims)
    except Exception:
        pass
```

**Changed code:**
```python
import logging

logger = logging.getLogger(__name__)


def _merge_custom_claims(
    user_id: str, updates: dict[str, str]
) -> bool:
    """Merge updates into existing Firebase custom claims.

    Args:
        user_id: Firebase Auth UID.
        updates: Claims to merge (e.g., {"role": "admin"}).

    Returns:
        bool: True if claims were updated successfully.
    """
    if not updates:
        return True
    safe_updates = {
        key: value for key, value in updates.items() if value
    }
    if not safe_updates:
        return True
    try:
        user_record = firebase_auth.get_user(user_id)
        claims = user_record.custom_claims or {}
        claims.update(safe_updates)
        firebase_auth.set_custom_user_claims(user_id, claims)
        return True
    except Exception as exc:
        logger.error(
            "Failed to update custom claims for %s: %s",
            user_id,
            exc,
        )
        return False
```

**Validation:**
- Verify all callers of `_merge_custom_claims` still work (they currently ignore the return value, which is fine — the function now logs instead of silently swallowing).
- Run `python -m pytest api/tests/test_rbac.py -v`

---

### Fix 1.4: Log and Handle User Update Errors (Finding #4 — High)

**File:** `api/users.py`

**Problem:** Multiple `except Exception: pass` blocks in `update_user()` silently mask Firebase Auth sync failures. The disabled-status case is a **security issue** — Firestore says "disabled" but Auth still allows login.

**Current code (users.py, `update_user` function, scattered across lines ~531–565):**

Display name sync:
```python
        try:
            firebase_auth.update_user(
                user_id,
                display_name=update_data.displayName,
            )
        except Exception:
            pass  # Non-critical, continue with Firestore update
```

Email sync:
```python
        try:
            firebase_auth.update_user(user_id, email=update_data.email)
        except Exception:
            pass
```

Disabled status:
```python
        if update_data.status == "disabled":
            try:
                firebase_auth.update_user(user_id, disabled=True)
            except Exception:
                pass
        elif update_data.status == "active":
            try:
                firebase_auth.update_user(user_id, disabled=False)
            except Exception:
                pass
```

**Changed code — display name (log only):**
```python
        try:
            firebase_auth.update_user(
                user_id,
                display_name=update_data.displayName,
            )
        except Exception as exc:
            logger.warning(
                "Failed to sync display name for %s: %s",
                user_id,
                exc,
            )
```

**Changed code — email (log, raise for critical failure):**
```python
        try:
            firebase_auth.update_user(
                user_id, email=update_data.email
            )
        except Exception as exc:
            logger.error(
                "Failed to sync email for %s: %s",
                user_id,
                exc,
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update email in authentication system",
            ) from exc
```

**Changed code — disabled status (critical — must fail hard):**
```python
        if update_data.status == "disabled":
            try:
                firebase_auth.update_user(user_id, disabled=True)
            except Exception as exc:
                logger.error(
                    "CRITICAL: Failed to disable user %s "
                    "in Firebase Auth: %s",
                    user_id,
                    exc,
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=(
                        "Failed to disable user in "
                        "authentication system"
                    ),
                ) from exc
        elif update_data.status == "active":
            try:
                firebase_auth.update_user(
                    user_id, disabled=False
                )
            except Exception as exc:
                logger.warning(
                    "Failed to re-enable user %s: %s",
                    user_id,
                    exc,
                )
```

**Validation:**
- Write a unit test that mocks `firebase_auth.update_user` to raise, verify the HTTP 500 response for disable and email cases.
- Run existing tests: `python -m pytest api/tests/ -v`

---

### Fix 1.5: Tighten CORS Methods and Headers (Finding #12 — Medium)

**File:** `api/main.py`

**Current code (main.py, lines 230–236):**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Changed code:**
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
```

**Validation:**
- Manual test: Verify the frontend dev server (port 5174) can still make all API calls.
- Check that OPTIONS preflight requests succeed for POST/PUT/DELETE endpoints.
- If any new headers are needed (e.g., `X-Custom-Header` from a future feature), they'll need to be added to the allowlist. Document this in the CORS section.

---

## Fix Group 2: Backend API Improvements

**Rationale:** Performance (deduplicated Firestore reads), deprecation cleanup (`datetime.utcnow`), and rate limiting on a hot endpoint. These are lower-risk but improve reliability and forward-compatibility.

### Fix 2.1: Rate-Limit `/api/auth/me` (Finding #6 — High)

**File:** `api/users.py`

**Current code (users.py, line 71):**
```python
@router.get("/auth/me", response_model=UserResponse)
async def get_me(user: FirestoreUser = Depends(get_current_user)):
```

**Changed code:**
```python
@router.get("/auth/me", response_model=UserResponse)
@limiter.limit("30/minute")
async def get_me(
    request: Request,
    user: FirestoreUser = Depends(get_current_user),
):
```

**Also add** to the imports at the top of `users.py`:
```python
from fastapi import Request
```

And add the limiter import:
```python
try:
    from limiter import limiter
except ImportError:
    from api.limiter import limiter
```

**Validation:**
- Run `python -m pytest api/tests/test_rbac.py -v`
- Manual test: Verify `/api/auth/me` still works normally; rate limit only triggers at 30+ requests/minute from the same IP.

---

### Fix 2.2: Eliminate Redundant Firestore Read in `/api/auth/me` (Finding #7 — Medium)

**File:** `api/users.py`

**Problem:** `get_current_user` (in `auth.py`) already fetches the user document from Firestore. Then `get_me` fetches it *again* to get `createdAt`/`updatedAt`.

**Approach:** Add `createdAt` and `updatedAt` to the `FirestoreUser` model so they're populated by `get_current_user`. This eliminates the second read.

**File:** `api/models.py` — verify that `createdAt` and `updatedAt` already exist in `FirestoreUser` (they do, lines 63–67). They are populated by `get_current_user` when it constructs `FirestoreUser(**user_data)`.

**File:** `api/users.py` — modify `get_me` to use data from the dependency:

**Current code (users.py, `get_me`, lines ~71–110):**
```python
@router.get("/auth/me", response_model=UserResponse)
async def get_me(user: FirestoreUser = Depends(get_current_user)):
    user_doc = db.collection("users").document(user.uid).get()
    user_data = user_doc.to_dict() if user_doc.exists else {}
    if user_data is None:
        user_data = {}
    # ... fetches department name and subject names ...
    return UserResponse(
        ...
        created_at=user_data.get("createdAt"),
        updated_at=user_data.get("updatedAt"),
    )
```

**Changed code:**
```python
@router.get("/auth/me", response_model=UserResponse)
@limiter.limit("30/minute")
async def get_me(
    request: Request,
    user: FirestoreUser = Depends(get_current_user),
):
    """
    Get the current authenticated user's profile.

    Returns:
        UserResponse: Current user's details including
            role and department.
    """
    # Get department name if assigned
    department_name = None
    if user.departmentId:
        dept_doc = (
            db.collection("departments")
            .document(user.departmentId)
            .get()
        )
        if dept_doc.exists:
            dept_dict = dept_doc.to_dict()
            department_name = (
                dept_dict.get("name") if dept_dict else None
            )

    # Get subject info for staff users
    subject_ids = user.subjectIds
    subject_names = None
    if user.role == "staff" and subject_ids:
        from hierarchy_crud import find_doc_by_id

        subject_names = []
        for subj_id in subject_ids:
            subj_ref = find_doc_by_id("subjects", subj_id)
            if subj_ref:
                subj_snap = subj_ref.get()
                subj_data = subj_snap.to_dict()
                if subj_data:
                    subject_names.append(
                        subj_data.get("name", "Unknown")
                    )

    return UserResponse(
        id=user.uid,
        email=user.email,
        display_name=user.displayName,
        role=user.role,
        department_id=user.departmentId,
        department_name=department_name,
        subject_ids=(
            subject_ids if user.role == "staff" else None
        ),
        subject_names=subject_names,
        status=user.status,
        created_at=user.createdAt,
        updated_at=user.updatedAt,
    )
```

**Validation:**
- Verify `FirestoreUser` model has `createdAt` and `updatedAt` fields with defaults (it does — `models.py` lines 63–67).
- Run `python -m pytest api/tests/ -v`
- Manual test: Hit `/api/auth/me` and verify response still includes `created_at` and `updated_at`.

---

### Fix 2.3: Replace Deprecated `datetime.utcnow()` (Finding #11 — Medium)

**Files:** `api/auth_sync.py`, `api/users.py`, `api/models.py`, `api/main.py`

**Problem:** `datetime.utcnow()` is deprecated since Python 3.12 and returns a naive datetime.

**Replacement strategy:** Use `datetime.now(timezone.utc).isoformat()` everywhere. The `.isoformat()` output includes the `+00:00` suffix (timezone-aware), which is a minor behavioral change from the previous naive format. If downstream consumers parse these strings, verify they handle the timezone suffix.

**File: `api/models.py`** — default factories (lines 63–67):

**Current:**
```python
    createdAt: str = pydantic.Field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat(),
        ...
    )
    updatedAt: str = pydantic.Field(
        default_factory=lambda: datetime.datetime.utcnow().isoformat(),
        ...
    )
```

**Changed:**
```python
    createdAt: str = pydantic.Field(
        default_factory=lambda: datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        ...
    )
    updatedAt: str = pydantic.Field(
        default_factory=lambda: datetime.datetime.now(
            datetime.timezone.utc
        ).isoformat(),
        ...
    )
```

**File: `api/users.py`** — all occurrences of `datetime.utcnow().isoformat()`:

Replace all instances with `datetime.now(timezone.utc).isoformat()`. Add import:
```python
from datetime import datetime, timezone
```

Occurrences:
- Line 334: `now = datetime.utcnow().isoformat()`
- Line 523: `updates["updatedAt"] = datetime.utcnow().isoformat()`

**File: `api/auth_sync.py`** — all occurrences:

Replace all instances with `datetime.now(timezone.utc).isoformat()`. Add import:
```python
from datetime import datetime, timezone
```
(Remove `from datetime import datetime` if present, replace with the above.)

Occurrences:
- Line 230: `timestamp = datetime.utcnow().isoformat()`
- Line 281: `timestamp = datetime.utcnow().isoformat()`
- Line 362: `update_data = {"updatedAt": datetime.utcnow().isoformat()}`

**File: `api/main.py`** — line in `bulk_download_pdfs`:

**Current:**
```python
timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
```

**Changed:**
```python
timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
```

Add to main.py imports:
```python
from datetime import datetime, timezone
```
(Remove existing `from datetime import datetime` if the only usage.)

**Validation:**
- Run `python -m pytest api/tests/ -v`
- `grep -r "utcnow()" api/` → should return 0 matches after fix
- Verify ISO strings still parse correctly in frontend (the `+00:00` suffix is standard ISO 8601)

---

### Fix 2.4: Document CSRF Non-Issue (Finding #13 — Medium)

**File:** `api/main.py` (or a security docs file)

**Problem:** `allow_credentials=True` in CORS config could imply cookie-based auth, but the app uses Bearer tokens which are inherently CSRF-safe.

**Action:** Add a comment near the CORS middleware:

```python
# NOTE: allow_credentials=True is set for CORS cookie compatibility,
# but authentication uses Bearer tokens (not cookies), making this
# endpoint inherently CSRF-safe. If cookie-based auth is ever added,
# implement CSRF token validation.
app.add_middleware(
    CORSMiddleware,
    ...
)
```

**Validation:** Code review only — no functional change.

---

### Fix 2.5: Verify Security Headers on Static File Responses (Finding #14 — Medium)

**File:** `api/main.py`

**Problem:** `FileResponse` may bypass the `SecurityHeadersMiddleware` depending on Starlette version.

**Action:** Add explicit security headers to the PDF download endpoint:

**Current code (main.py, `download_pdf`):**
```python
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'{disposition}; filename="{filename}"',
        },
    )
```

**Changed code:**
```python
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/pdf",
        headers={
            "Content-Disposition": (
                f'{disposition}; filename="{filename}"'
            ),
            "X-Content-Type-Options": "nosniff",
        },
    )
```

**Validation:**
- Manual test: Download a PDF and inspect response headers for `X-Content-Type-Options: nosniff`.

---

## Fix Group 3: Frontend Auth State Management

**Rationale:** Fixes the race condition causing duplicate requests during login, adds proper loading-state signaling, and prevents silent logout on transient network errors.

### Fix 3.1: Deduplicate Concurrent `refreshUser` Calls (Finding #5 — High)

**File:** `frontend/src/stores/useAuthStore.ts`

**Problem:** On login, both `login()` and the `onIdTokenChanged` listener call `refreshUser()` concurrently, causing duplicate network requests and potential UI flicker.

**Current code (useAuthStore.ts, `refreshUser` action, ~lines 221–268):**
```typescript
refreshUser: async () => {
    const { firebaseUser } = get();
    if (!firebaseUser) {
        set({ user: null, isLoading: false });
        return;
    }

    try {
        const idToken = await firebaseUser.getIdToken();
        // ... fetch /auth/me ...
    } catch (error) {
        console.error('Failed to refresh user:', error);
        set({ user: null, isLoading: false });
    }
},
```

**Changed code:**

First, add `_refreshPromise` to the `AuthState` interface:
```typescript
interface AuthState {
    // State
    user: AuthUser | null;
    firebaseUser: FirebaseTokenProvider | null;
    isLoading: boolean;
    isInitialized: boolean;
    error: string | null;
    _refreshPromise: Promise<void> | null;  // Add this

    // ... rest unchanged
}
```

Add to initial state:
```typescript
_refreshPromise: null,
```

Then replace the `refreshUser` action:
```typescript
refreshUser: async () => {
    const { firebaseUser, _refreshPromise } = get();

    // Deduplicate concurrent calls
    if (_refreshPromise) {
        return _refreshPromise;
    }

    if (!firebaseUser) {
        set({ user: null, isLoading: false });
        return;
    }

    set({ isLoading: true });

    const promise = (async () => {
        try {
            const idToken = await firebaseUser.getIdToken();

            const response = await fetch(
                `${API_BASE}/auth/me`,
                {
                    headers: {
                        Authorization: `Bearer ${idToken}`,
                    },
                }
            );

            if (!response.ok) {
                if (response.status === 401) {
                    const syncResponse = await fetch(
                        `${API_BASE}/auth/sync`,
                        {
                            method: 'POST',
                            headers: {
                                'Content-Type':
                                    'application/json',
                                Authorization:
                                    `Bearer ${idToken}`,
                            },
                            body: JSON.stringify({}),
                        }
                    );

                    if (syncResponse.ok) {
                        const retryResponse = await fetch(
                            `${API_BASE}/auth/me`,
                            {
                                headers: {
                                    Authorization: `Bearer ${idToken}`,
                                },
                            }
                        );

                        if (retryResponse.ok) {
                            const retryUserData =
                                await retryResponse.json();
                            const retryUser: AuthUser = {
                                id: retryUserData.id,
                                email: retryUserData.email,
                                displayName:
                                    retryUserData.display_name,
                                role: retryUserData.role,
                                departmentId:
                                    retryUserData.department_id,
                                departmentName:
                                    retryUserData.department_name,
                                subjectIds:
                                    retryUserData.subject_ids ||
                                    null,
                                status: retryUserData.status,
                            };

                            set({
                                user: retryUser,
                                isLoading: false,
                            });
                            return;
                        }
                    } else {
                        console.warn(
                            'Token sync failed, ' +
                            'user will be logged out'
                        );
                    }
                }

                // Auth error (not network) — log out
                set({ user: null, isLoading: false });
                return;
            }

            const userData = await response.json();

            const newUser: AuthUser = {
                id: userData.id,
                email: userData.email,
                displayName: userData.display_name,
                role: userData.role,
                departmentId: userData.department_id,
                departmentName: userData.department_name,
                subjectIds: userData.subject_ids || null,
                status: userData.status,
            };

            set({
                user: newUser,
                isLoading: false,
            });
        } catch (error) {
            console.error('Failed to refresh user:', error);
            // Network error — keep session, don't log out
            if (
                error instanceof TypeError &&
                error.message.includes('fetch')
            ) {
                console.warn(
                    'Network error during refresh, ' +
                    'keeping session'
                );
                set({
                    isLoading: false,
                    error:
                        'Network error. ' +
                        'Please check your connection.',
                });
            } else {
                set({ user: null, isLoading: false });
            }
        }
    })();

    set({ _refreshPromise: promise });
    promise.finally(() => set({ _refreshPromise: null }));
    return promise;
},
```

**Key changes:**
1. **Deduplication guard** at the top — if a refresh is already in flight, return the existing promise.
2. **`isLoading: true`** set at the start (Fix 3.2, Finding #8).
3. **Network error resilience** in catch block (Fix 3.3, Finding #9) — distinguishes `TypeError` (fetch failure = network) from auth errors.

**Validation:**
- Manual test: Log in and observe Network tab — should see exactly one `/auth/me` call, not two.
- Verify `isLoading` is `true` during the refresh (check React DevTools or add a console.log).
- Simulate network failure (DevTools → Network → Offline) during token refresh — user should stay logged in with error message, not be logged out.

---

### Fix 3.2: (Included in Fix 3.1)

Finding #8 (isLoading not set to true at start of refresh) is addressed in Fix 3.1 by adding `set({ isLoading: true })` at the top of the promise body.

---

### Fix 3.3: (Included in Fix 3.1)

Finding #9 (silent logout on network errors) is addressed in Fix 3.1 by the conditional catch block that distinguishes `TypeError` (network) from auth errors.

---

## Fix Group 4: Login Page Improvements

**Rationale:** Fixes the navigation race condition, improves accessibility, and aligns with project style guide.

### Fix 4.1: Eliminate Navigation Race Condition (Finding #10 — Medium)

**File:** `frontend/src/pages/LoginPage.tsx`

**Problem:** Both `useEffect` (watching `user`) and `handleSubmit` navigate after login. If `onIdTokenChanged` sets `user` before `handleSubmit` finishes, two `navigate()` calls execute.

**Approach:** Remove the `navigate()` calls from `handleSubmit` and rely solely on the `useEffect` redirect.

**Current code (LoginPage.tsx, `handleSubmit`, ~lines 76–84):**
```typescript
        try {
            await login(email, password);

            // Get user role to determine redirect
            const user = useAuthStore.getState().user;
            // Force navigation to root for non-admins
            // ExplorerPage will handle the redirection to department
            if (user?.role === 'admin') {
                navigate('/admin', { replace: true });
            } else {
                navigate('/', { replace: true });
            }
        } catch (err) {
            // Error is handled by the store
            console.error('Login failed:', err);
        }
```

**Changed code:**
```typescript
        try {
            await login(email, password);
            // Navigation is handled by the useEffect watching `user`
        } catch (err) {
            // Error is handled by the store
            console.error('Login failed:', err);
        }
```

**Validation:**
- Manual test: Log in as admin → should redirect to `/admin`.
- Log in as staff/student → should redirect to `/`.
- Verify no React Router warnings in console about duplicate navigations.

---

### Fix 4.2: Add Accessibility Attributes (Findings #15, #16 — Low)

**File:** `frontend/src/pages/LoginPage.tsx`

**Current code (error message, ~line 118):**
```tsx
{displayError && (
    <div className="error-message">
        {displayError}
    </div>
)}
```

**Changed code:**
```tsx
{displayError && (
    <div
        className="error-message"
        role="alert"
        aria-live="assertive"
    >
        {displayError}
    </div>
)}
```

**Current code (email input, ~line 96):**
```tsx
<input
    id="email"
    type="email"
    value={email}
    onChange={(e) => setEmail(e.target.value)}
    placeholder="Enter your email"
    disabled={isLoading}
    autoComplete="email"
/>
```

**Changed code:**
```tsx
<input
    id="email"
    type="email"
    value={email}
    onChange={(e) => setEmail(e.target.value)}
    placeholder="Enter your email"
    disabled={isLoading}
    autoComplete="email"
    required
/>
```

**Current code (password input, ~line 106):**
```tsx
<input
    id="password"
    type="password"
    value={password}
    onChange={(e) => setPassword(e.target.value)}
    placeholder="Enter your password"
    disabled={isLoading}
    autoComplete="current-password"
/>
```

**Changed code:**
```tsx
<input
    id="password"
    type="password"
    value={password}
    onChange={(e) => setPassword(e.target.value)}
    placeholder="Enter your password"
    disabled={isLoading}
    autoComplete="current-password"
    required
/>
```

**Validation:**
- Run `cd frontend && npm run lint` — should pass.
- Run `cd frontend && npm run build` — should pass.
- Manual test: Tab through the form — screen reader should announce required fields.

---

### Fix 4.3: Remove Default Export (Finding #17 — Low)

**File:** `frontend/src/pages/LoginPage.tsx`

**Current code (end of file, ~line 152):**
```typescript
export default LoginPage;
```

**Action:** Remove this line entirely. The named export `export function LoginPage()` on line 42 is sufficient. Verify `App.tsx` already uses the named import (confirmed — line 9: `import { LoginPage } from './pages/LoginPage'`).

**Validation:**
- Run `cd frontend && npm run build` — should pass with no import errors.

---

### Fix 4.4: Extract Inline Styles to CSS File (Finding #18 — Low)

**File:** `frontend/src/pages/LoginPage.tsx` (source), `frontend/src/styles/login.css` (new)

**Action:**

1. Create `frontend/src/styles/login.css` with all the CSS currently in the `<style>` tag (~lines 121–280).

2. In `LoginPage.tsx`, remove the entire `<style>{`...`}</style>` block and add an import:
```typescript
import '../styles/login.css';
```

**Validation:**
- Run `cd frontend && npm run build` — should pass.
- Manual test: Verify the login page renders identically (no visual regressions).

---

## Verification Checklist

### Per-Group Verification

| Group | Command | Expected Result |
|-------|---------|-----------------|
| Group 1 | `python -m pytest api/tests/test_rbac.py -v` | All tests pass (some assertions updated for sanitized messages) |
| Group 1 | `python -m pytest api/tests/ -v` | Full backend test suite passes |
| Group 2 | `python -m pytest api/tests/ -v` | Full backend test suite passes |
| Group 2 | `grep -r "utcnow()" api/` | 0 matches |
| Group 3 | `cd frontend && npm run build` | Build succeeds |
| Group 3 | `cd frontend && npm run lint` | No lint errors |
| Group 4 | `cd frontend && npm run build` | Build succeeds |
| Group 4 | `cd frontend && npm run lint` | No lint errors |

### Final Integration Verification

1. **Backend smoke test:**
   ```bash
   cd AURA-NOTES-MANAGER
   python -m uvicorn api.main:app --port 8001
   # In another terminal:
   curl http://127.0.0.1:8001/health
   # Should return: {"status": "healthy", "version": "1.0.0"}
   ```

2. **Frontend smoke test:**
   ```bash
   cd AURA-NOTES-MANAGER/frontend
   npm run dev
   # Navigate to http://127.0.0.1:5174
   # Verify login page renders correctly
   # Log in and verify redirect works
   ```

3. **Production guard test:**
   ```bash
   ENVIRONMENT=production USE_REAL_FIREBASE=false python -c "from api.config import db"
   # Should raise RuntimeError
   ```

4. **Full test suite:**
   ```bash
   python -m pytest api/tests/ -v --tb=short
   cd frontend && npm run test
   ```

---

## Risk Notes

### High Risk

1. **Timestamp format change (Fix 2.3):** `datetime.now(timezone.utc).isoformat()` produces strings like `2026-05-24T12:00:00+00:00` instead of `2026-05-24T12:00:00`. Any downstream code that parses these strings with strict format expectations may break. **Mitigation:** Search for all ISO timestamp parsing in both frontend and backend before deploying.

2. **CORS tightening (Fix 1.5):** If any frontend code sends custom headers (beyond `Authorization` and `Content-Type`), the tightened CORS policy will block them. **Mitigation:** Test all API endpoints after the change. If issues arise, add the missing header to the allowlist.

3. **`refreshUser` deduplication (Fix 3.1):** The `_refreshPromise` state is added to the Zustand store. Zustand subscribers will be notified when `_refreshPromise` changes. Since it's a non-UI field, this shouldn't cause re-renders, but verify with React DevTools Profiler.

### Medium Risk

4. **Email sync failure now raises HTTP 500 (Fix 1.4):** Previously, email sync failures were silent. Now they'll return a 500 error to the admin. This is the correct behavior, but admins should be prepared for the error and understand it means Auth/Firestore are out of sync.

5. **Network error keeping session (Fix 3.1/3.3):** Keeping the user logged in during network errors means they might see stale data until the network recovers. The error message should make this clear. Consider adding a retry button in the UI.

### Low Risk

6. **`required` attribute on inputs (Fix 4.2):** Adding HTML `required` changes browser validation behavior. The existing JavaScript validation (`if (!email || !password)`) still runs first, so this is additive only.

7. **Inline styles extraction (Fix 4.4):** The CSS is currently unscoped. Moving it to a `.css` file doesn't change scoping. If class names collide with other pages, they already would have collided. No regression expected.
