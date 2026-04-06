# Phase 7: Failure Hardening & Shared Seams - Research

**Researched:** 2026-04-06
**Domain:** Error handling, API client consolidation, silent failure elimination
**Confidence:** HIGH

## Summary

Phase 7 addresses two interconnected problems: (1) silent failures that hide errors from users and operators, and (2) duplicated request/error-handling logic that creates reliability drift. The codebase has **178+ `except Exception` handlers** in the backend with varying behaviors—some log and continue, some silently pass, some re-raise. The frontend has **duplicated fetch/auth/retry logic** across `client.ts` (3 functions) and `useAuthStore.ts` (3 additional fetch calls), creating divergence risk.

**Key findings:**
- Backend `audio_processing.py` line 460 uses bare `except Exception: pass` when DB note creation fails—a confirmed silent failure
- Frontend `getAuthHeader()` silently returns `{}` on token failure (line 69-72), meaning requests proceed unauthenticated without warning
- Auth/retry logic is copy-pasted 6 times across the codebase, each with subtle variations
- Health check (`checkHealth()`) has its own fetch wrapper instead of using `fetchApi`

**Primary recommendation:** Establish canonical error handling patterns (frontend: extend `client.ts` exports; backend: standardized exception handling module) and audit/remediate the identified silent failure paths.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| FAIL-01 | Users receive explicit failure states for audited upload, processing, and admin actions instead of silent no-op behavior | Identified 2 critical silent failures in audio_processing.py (lines 390, 460) and 1 in getAuthHeader() |
| FAIL-02 | Backend paths that currently swallow failures emit actionable logs or structured failure outcomes without hiding the error | Found 178+ exception handlers; 7 log warnings on failure; bare `except: pass` at line 460 |
| FAIL-03 | High-risk frontend request flows use a canonical auth and error-handling path instead of ad hoc page-level implementations | useAuthStore.ts has 4 direct fetch() calls bypassing client.ts; checkHealth() has custom wrapper |
| DRIFT-01 | Duplicate request, helper, or config paths that currently create reliability drift are consolidated only where behavior is proven equivalent | Auth header + 401 retry logic duplicated in fetchApi, fetchBlob, fetchFormData (identical) |
| DRIFT-03 | Shared helper logic identified as low-risk duplication is centralized where doing so removes ongoing divergence risk | getAuthHeader() is the canonical source; wrap401Retry could be extracted |
</phase_requirements>

## Standard Stack

### Core (Already in Use)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Vitest | 3.2.4 (project), 4.1.2 (latest) | Frontend unit testing | [VERIFIED: npm registry] Already configured in vite.config.ts |
| Playwright | 1.50.0 (project), 1.59.1 (latest) | Frontend E2E testing | [VERIFIED: npm registry] Already configured |
| Pytest | 8.x | Backend unit testing | [VERIFIED: conftest.py exists] Standard Python testing |

### Supporting (For This Phase)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Python `logging` | stdlib | Structured backend logging | All exception handlers should use logger |
| Custom error classes | N/A | Typed frontend errors | Extend DuplicateError pattern for other error types |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Custom error classes | neverthrow | More functional, but adds dependency + learning curve |
| Python logging | structlog | Better structured output, but more setup needed |

**No new dependencies recommended.** This phase is about consolidation, not addition.

## Architecture Patterns

### Recommended Error Handling Structure

**Frontend:**
```
frontend/src/api/
├── client.ts           # Core fetch wrappers (extend, don't duplicate)
│   ├── getAuthHeader() # Single source of auth header logic
│   ├── fetchApi<T>()   # JSON requests
│   ├── fetchBlob()     # Binary downloads  
│   ├── fetchFormData() # File uploads
│   └── (NEW) wrap401Retry() # Extracted retry logic
├── errors.ts           # (NEW) Error type exports
│   ├── DuplicateError  # Move from client.ts
│   ├── AuthError       # (NEW) For auth failures
│   └── NetworkError    # (NEW) For network failures
└── [feature]Api.ts     # Feature-specific wrappers using client.ts
```

**Backend:**
```
api/
├── errors/             # (NEW) Centralized error handling
│   ├── __init__.py     # Error classes and handlers
│   └── handlers.py     # FastAPI exception handlers
├── [module].py         # Feature modules using standardized patterns
└── main.py             # Wire up exception handlers
```

### Pattern 1: Explicit Failure Propagation (Frontend)

**What:** Auth failures surface to callers instead of silent degradation
**When to use:** Any request that requires authentication

**Current (PROBLEMATIC):**
```typescript
// Source: frontend/src/api/client.ts lines 63-73
async function getAuthHeader(): Promise<Record<string, string>> {
    try {
        const token = await useAuthStore.getState().getIdToken();
        if (token) {
            return { 'Authorization': `Bearer ${token}` };
        }
    } catch (e) {
        console.warn('Failed to get auth token', e); // Silent!
    }
    return {}; // Proceeds without auth - SILENT FAILURE
}
```

**Recommended:**
```typescript
// Explicit failure mode
async function getAuthHeader(): Promise<Record<string, string>> {
    try {
        const token = await useAuthStore.getState().getIdToken();
        if (token) {
            return { 'Authorization': `Bearer ${token}` };
        }
        // No token available - this is expected for unauthenticated routes
        return {};
    } catch (e) {
        // Token retrieval failed - this is unexpected
        console.error('Auth token retrieval failed:', e);
        throw new AuthError('Failed to retrieve authentication token', e);
    }
}
```

### Pattern 2: Structured Backend Failure (Python)

**What:** Exception handlers that log AND propagate structured errors
**When to use:** Any try/except block in request handlers

**Current (PROBLEMATIC):**
```python
# Source: api/audio_processing.py lines 455-461
if module_id:
    try:
        note = create_note_record(module_id, topic, pdf_url)
        if note:
            note_id = note['id']
    except Exception:
        pass  # SILENT FAILURE - DB save failed, user never knows
```

**Recommended:**
```python
# Explicit failure with structured outcome
if module_id:
    try:
        note = create_note_record(module_id, topic, pdf_url)
        if note:
            note_id = note['id']
    except Exception as e:
        logger.error(f"Failed to save note to database: {e}", exc_info=True)
        # Include failure info in response
        job_status_store[job_id]['warnings'] = [
            f"PDF generated successfully but note record creation failed: {str(e)}"
        ]
```

### Pattern 3: Extracted Retry Logic (Frontend)

**What:** Centralized 401 retry logic instead of copy-paste
**When to use:** All authenticated fetch functions

**Current (DUPLICATED):**
```typescript
// Identical logic appears in fetchApi (lines 132-150), 
// fetchBlob (lines 185-203), fetchFormData (lines 234-250)
if (response.status === 401 && import.meta.env.VITE_USE_MOCK_AUTH !== 'true') {
    try {
        const newToken = await useAuthStore.getState().getIdToken(true);
        if (newToken) {
            response = await fetch(url, { /* retry options */ });
        }
    } catch (e) {
        console.error('Token refresh failed', e);
    }
}
```

**Recommended:**
```typescript
// Extracted helper
async function executeWithRetry<T>(
    url: string, 
    options: RequestInit,
    responseHandler: (r: Response) => Promise<T>
): Promise<T> {
    let response = await fetch(url, options);
    
    if (response.status === 401 && import.meta.env.VITE_USE_MOCK_AUTH !== 'true') {
        const newToken = await useAuthStore.getState().getIdToken(true);
        if (newToken) {
            response = await fetch(url, {
                ...options,
                headers: {
                    ...options.headers,
                    'Authorization': `Bearer ${newToken}`,
                },
            });
        }
    }
    
    return responseHandler(response);
}
```

### Anti-Patterns to Avoid

- **Silent `except: pass`:** Never catch and ignore without at minimum logging [CITED: AGENTS.md Python error handling section]
- **Catch-all without context:** `except Exception as e:` is acceptable only with `logger.exception()` or `exc_info=True`
- **Duplicate fetch logic:** All API calls should flow through `client.ts` exports
- **Direct `fetch()` calls:** Outside of `client.ts`, use `fetchApi`/`fetchBlob`/`fetchFormData`

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Auth header injection | Manual header building in each API | `getAuthHeader()` from client.ts | Single source of truth |
| 401 retry logic | Copy-paste retry in each fetch | Extracted `executeWithRetry()` | Prevents divergence |
| Error parsing | Per-endpoint error extraction | `parseErrorMessage()` from client.ts | Already exists, just use it |
| Structured logging | `print()` or ad-hoc formats | Python `logging` module | Standard, configurable |

**Key insight:** The codebase already has the right abstractions (`client.ts`, `DuplicateError`); the problem is inconsistent adoption, not missing infrastructure.

## Common Pitfalls

### Pitfall 1: Breaking Auth Flow While Fixing Silent Failures

**What goes wrong:** Making `getAuthHeader()` throw causes all unauthenticated routes to fail
**Why it happens:** Some routes legitimately work without auth; others require it
**How to avoid:** Distinguish between "no token available" (acceptable) and "token retrieval failed" (error)
**Warning signs:** Login page starts failing; public endpoints break

### Pitfall 2: Over-Logging Creates Noise

**What goes wrong:** Converting every `except: pass` to `logger.error()` floods logs
**Why it happens:** Some exceptions are expected (e.g., cache miss, optional feature unavailable)
**How to avoid:** Use appropriate log levels: `debug` for expected, `warning` for degraded, `error` for failures
**Warning signs:** Log volume spikes; alerts trigger on expected conditions

### Pitfall 3: Refactoring Breaks Existing Tests

**What goes wrong:** Extracting shared code changes import paths, breaking test mocks
**Why it happens:** Tests mock `fetch` or specific functions; reorganization changes what to mock
**How to avoid:** Run full test suite after each refactor; update mocks incrementally
**Warning signs:** `client.test.ts` fails; E2E auth tests break

### Pitfall 4: Partial Migration Creates Worse Drift

**What goes wrong:** Some code uses new patterns, some uses old; now 3 patterns exist
**Why it happens:** Phase completed partially; migration not tracked
**How to avoid:** Audit all call sites before starting; migrate atomically within each file
**Warning signs:** `grep 'fetch('` shows both old and new patterns after "completion"

## Code Examples

### Frontend: Current Silent Failure Points

**1. Auth header silent failure (client.ts:63-73):**
```typescript
// Source: frontend/src/api/client.ts
// [VERIFIED: direct code inspection]
async function getAuthHeader(): Promise<Record<string, string>> {
    try {
        const token = await useAuthStore.getState().getIdToken();
        if (token) {
            return { 'Authorization': `Bearer ${token}` };
        }
    } catch (e) {
        console.warn('Failed to get auth token', e); // <-- Only warns, continues
    }
    return {}; // <-- Request proceeds without auth
}
```

**2. useAuthStore bypasses client.ts (useAuthStore.ts:218, 331, 339, 349):**
```typescript
// Source: frontend/src/stores/useAuthStore.ts
// [VERIFIED: direct code inspection]
// Direct fetch instead of fetchApi - no shared error handling
const syncResponse = await fetch(`${API_BASE}/auth/sync`, {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`,
    },
    body: JSON.stringify({ displayName: firebaseUser.displayName ?? '' }),
});
```

### Backend: Current Silent Failure Points

**1. Bare except:pass in audio pipeline (audio_processing.py:460):**
```python
# Source: api/audio_processing.py lines 455-461
# [VERIFIED: direct code inspection]
if module_id:
    try:
        note = create_note_record(module_id, topic, pdf_url)
        if note:
            note_id = note['id']
    except Exception:
        pass  # <-- SILENT: DB save failed, no log, no user notification
```

**2. DB failure logged but success returned (audio_processing.py:390-392):**
```python
# Source: api/audio_processing.py lines 385-393
# [VERIFIED: direct code inspection]
try:
    note = create_note_record(request.moduleId, request.title, pdf_url)
    if note:
        note_id = note['id']
except Exception as db_error:
    # PDF was generated but DB save failed - still return success
    logger.warning(f"Failed to save note to database: {db_error}")
    # <-- Returns success=True anyway, user thinks everything worked
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `try/except pass` | Structured error outcomes | Google Python Style Guide | Prevents silent failures |
| Per-endpoint error handling | Centralized error classes | TypeScript 4.x custom errors | Type-safe error handling |
| `console.warn` for failures | Error boundaries + throw | React 18 best practices | Proper error propagation |

**Deprecated/outdated:**
- `catch(e) {}` empty blocks: Forbidden by AGENTS.md [CITED: AGENTS.md error handling section]
- `except:` bare clauses: Forbidden by Google Python Style Guide [CITED: AGENTS.md Python section]

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | useAuthStore fetch calls can safely migrate to fetchApi without breaking auth flow | Architecture Patterns | Medium - auth is critical path |
| A2 | checkHealth() custom fetch is intentional (avoids /api prefix) | Code Examples | Low - health checks are non-critical |
| A3 | The 178 exception handlers can be categorized into expected/warning/error without detailed audit | Summary | Medium - some may need individual review |

## Open Questions

1. **Should `getAuthHeader()` throw or return empty on failure?**
   - What we know: Currently returns `{}`, allowing unauthenticated requests
   - What's unclear: Are there routes that legitimately work with or without auth?
   - Recommendation: Add explicit mode parameter `getAuthHeader(required: boolean)`

2. **How should job_status_store communicate partial failures?**
   - What we know: Currently returns `status: 'complete'` even when DB save fails
   - What's unclear: Does UI currently display warnings from job status?
   - Recommendation: Add `warnings: string[]` field to job status schema

3. **Should useAuthStore migrate to client.ts or keep separate auth flow?**
   - What we know: Auth flows have specific error handling needs (Firebase error codes)
   - What's unclear: Whether client.ts should know about Firebase-specific errors
   - Recommendation: Keep auth-specific flows in useAuthStore but extract shared retry logic

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework (Frontend) | Vitest 3.2.4 with jsdom |
| Framework (Backend) | Pytest (version in requirements.txt) |
| Frontend Config | vite.config.ts `test` block |
| Backend Config | conftest.py (test mode flags) |
| Quick run (Frontend) | `npm test -- src/api/client.test.ts` |
| Quick run (Backend) | `pytest api/test_audio_processing.py -x` |
| Full suite (Frontend) | `npm test` in frontend/ |
| Full suite (Backend) | `pytest` in project root |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| FAIL-01 | Auth failures surface explicitly | unit | `npm test -- src/api/client.test.ts` | ✅ (exists, needs extension) |
| FAIL-02 | Backend exceptions logged | unit | `pytest api/tests/test_audio_processing.py -x` | ❌ Wave 0 |
| FAIL-03 | useAuthStore uses client.ts | unit | `npm test -- src/stores/useAuthStore.test.ts` | ❌ Wave 0 |
| DRIFT-01 | No duplicate fetch logic | lint | Manual audit / grep verification | N/A |
| DRIFT-03 | Shared helpers centralized | lint | Manual audit | N/A |

### Sampling Rate
- **Per task commit:** `npm test -- src/api/client.test.ts` + `pytest -x` (fast subset)
- **Per wave merge:** Full `npm test` + `pytest`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `frontend/src/api/client.test.ts` — extend with auth failure tests (FAIL-01)
- [ ] `api/tests/test_audio_processing.py` — test exception logging (FAIL-02)
- [ ] `frontend/src/stores/useAuthStore.test.ts` — create if not exists (FAIL-03)

## Sources

### Primary (HIGH confidence)
- [VERIFIED: Direct codebase inspection] frontend/src/api/client.ts — all fetch wrapper patterns
- [VERIFIED: Direct codebase inspection] api/audio_processing.py — silent failure patterns
- [VERIFIED: Direct codebase inspection] frontend/src/stores/useAuthStore.ts — duplicate fetch logic
- [VERIFIED: npm registry] vitest@4.1.2, @playwright/test@1.59.1 — current versions

### Secondary (MEDIUM confidence)  
- [CITED: AGENTS.md] Error handling requirements and forbidden patterns
- [VERIFIED: grep output] 178 exception handlers in api/ directory

### Tertiary (LOW confidence)
- [ASSUMED] All 178 exception handlers can be categorized without individual audit

## Metadata

**Confidence breakdown:**
- Silent failure identification: HIGH — verified by direct code inspection
- Architecture patterns: HIGH — based on existing codebase patterns
- Test infrastructure: HIGH — verified config files exist
- Migration risk assessment: MEDIUM — some assumptions about auth flow behavior

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (30 days — stable patterns, no external dependencies)
