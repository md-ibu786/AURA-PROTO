# Codebase Concerns

**Analysis Date:** 2026-02-06

---

## Critical Issues

### Service Account Keys Committed to Repository

**Risk:** HIGH - Active security breach
- Files: `serviceAccountKey-auth.json`, `serviceAccountKey-old.json`
- Impact: Private keys and credentials are exposed in version control
- Evidence: Keys are visible in repository root with actual private key material
- Mitigation: These files are in `.gitignore` but were committed before the rule was added
- **Action Required:**
  1. Immediately revoke these service accounts in Firebase Console
  2. Generate new service account keys
  3. Use `git filter-branch` or BFG Repo-Cleaner to remove from git history
  4. Rotate all Firebase credentials
  5. Audit access logs for unauthorized usage

### Debug Print Statements in Authentication Flow

**Risk:** MEDIUM - Information disclosure in production
- Files: `api/auth.py:78`, `api/auth.py:85`, `api/auth.py:92`
- Issue: Token validation errors printed to console with sensitive details
- Code:
  ```python
  except auth.InvalidIdTokenError as exc:
      print(f"DEBUG: Invalid token error: {exc}")
  ```
- Impact: Leaks authentication implementation details and token error messages
- Fix: Replace `print()` with proper logging using `logger.debug()`
- Priority: HIGH - Deploy before production

### Broad Exception Catching Without Logging

**Risk:** MEDIUM - Silent failures masking critical errors
- Occurrences: 17 instances in API layer
- Files: `api/config.py:218`, `api/cache.py:105`, `api/users.py:71`, `api/users.py:191`, `api/users.py:211`, `api/users.py:500`, `api/hierarchy_crud.py:186`, `api/main.py:468`, `api/main.py:516`
- Pattern:
  ```python
  except Exception:
      pass  # Silent failure
  ```
- Impact: Errors are swallowed without investigation, making debugging impossible
- Examples:
  - `api/users.py:71` - Firebase custom claims updates fail silently
  - `api/users.py:191` - Department lookups fail silently, cache "Unknown Department"
  - `api/hierarchy_crud.py:186` - PDF deletion failures ignored
- **Fix Required:** Add logging for all exception handlers:
  ```python
  except Exception as e:
      logger.error(f"Failed to update custom claims for {user_id}: {e}")
  ```

---

## Security Concerns

### Missing Environment Variable Validation

**Risk:** MEDIUM - Service failures from missing configuration
- Files: `api/config.py`, `services/stt.py:126`
- Issue: Critical environment variables not validated at startup
- Missing checks for:
  - `FIREBASE_CREDENTIALS` path existence
  - `GOOGLE_APPLICATION_CREDENTIALS` validity
  - `NEO4J_PASSWORD` presence
  - `REDIS_URL` format
- Impact: App starts successfully but fails on first request
- **Recommendation:** Add startup validation in `api/main.py`:
  ```python
  @app.on_event("startup")
  async def validate_environment():
      required = ["FIREBASE_CREDENTIALS", "NEO4J_PASSWORD"]
      missing = [k for k in required if not os.getenv(k)]
      if missing:
          raise RuntimeError(f"Missing env vars: {missing}")
  ```

### Deepgram API Key in Service Code

**Risk:** LOW - API key validation leaks implementation details
- File: `services/stt.py:126-128`
- Code:
  ```python
  api_key = os.getenv("DEEPGRAM_API_KEY")
  if not api_key:
      raise ValueError("DEEPGRAM_API_KEY environment variable is not set.")
  ```
- Issue: Error message reveals exact environment variable name
- Better: Generic message "Audio transcription not configured"

### Deprecated API Key Parameters Still Accepted

**Risk:** LOW - Confusing API surface
- Files: `services/embeddings.py:92`, `services/llm_entity_extractor.py:204`
- Pattern: Functions accept `api_key` parameter but ignore it with warning
- Code:
  ```python
  if api_key:
      logger.warning("EmbeddingService no longer uses API keys; ignoring api_key")
  ```
- Impact: Developers may think keys are required, adds confusion
- **Fix:** Remove deprecated parameters in next major version

### Firebase API Keys Hardcoded in Client

**Risk:** MEDIUM - API keys exposed in client-side code
- File: `frontend/src/api/firebaseClient.ts:35-41`
- Pattern:
  ```typescript
  const firebaseConfig = {
      apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
      authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
      // ...
  };
  ```
- Note: Firebase API keys are safe to expose (per Firebase docs), but App Check should be enforced
- Status: App Check configured (line 56) but warns on failure instead of blocking
- **Recommendation:** Enforce App Check in production mode

---

## Technical Debt

### Manual Cascade Delete with TODO Comment

**Risk:** MEDIUM - Data orphaning and storage leaks
- File: `api/hierarchy_crud.py:360`
- Code:
  ```python
  # Manual cascade TODO: Files cleanup (omitted for brevity, requires iterating notes)
  # We will just do DB cleanup here. File cleanup requires note path lookup.
  ```
- Impact: PDF files in `pdfs/` directory are not deleted when departments are removed
- Evidence: `pdfs/` directory is gitignored, suggesting it's used for storage
- Consequence: Storage fills up with orphaned PDFs
- **Fix Path:**
  1. Implement recursive PDF cleanup in `delete_document_recursive()`
  2. Track PDF paths in note documents
  3. Add background cleanup job for orphaned files

### Redis/Celery Integration Not Fully Implemented

**Risk:** MEDIUM - Async processing not production-ready
- Files: `api/cache.py`, `api/tasks/document_processing_tasks.py`
- Status: Code exists but not enforced
- Issues:
  - Redis client gracefully degrades to no-op when unavailable (line 40-65)
  - Celery tasks defined but worker deployment not documented
  - No health checks for task queue in production
  - `REDIS_ENABLED=false` in test environment suggests optional dependency
- Impact: Document processing may time out on synchronous execution
- **Production Risk:** Large PDF processing will block API requests
- **Recommendation:**
  1. Document Celery worker deployment requirements
  2. Add health check endpoint for worker status
  3. Implement circuit breaker for Redis failures

### Inconsistent Empty Return Patterns

**Risk:** LOW - Type inconsistencies cause runtime errors
- Pattern: Functions return `[]`, `{}`, or `null` for empty results
- Occurrences: 45+ instances across codebase
- Files: `services/embeddings.py`, `api/neo4j_config.py`, `api/graph_manager.py`
- Example:
  - `api/explorer.py` returns `[]` for no results
  - `api/cache.py` returns `{}` for cache miss
  - Some functions return `None`
- Impact: Client code must handle multiple empty states
- **Fix:** Standardize on single empty return convention per type

### Test Mode Bypasses Throughout Codebase

**Risk:** MEDIUM - Production behavior untested
- Pattern: `AURA_TEST_MODE` environment variable disables external services
- Files: `api/config.py:75`, `conftest.py:11`, `api/neo4j_config.py`
- Issue: Test mode provides deterministic mocks instead of real service calls
- Examples:
  - Embeddings return deterministic vectors instead of Vertex AI calls
  - Neo4j initialization skipped in test mode
  - Redis disabled in tests
- Risk: Production code paths never tested with real external services
- **Recommendation:** Add integration test suite that tests with real services

### Mock Token Verification in Production Code

**Risk:** HIGH - Authentication bypass path exists
- File: `api/auth.py:106-132`
- Code:
  ```python
  is_testing = os.getenv("TESTING", "false").lower() == "true"
  if is_testing and not use_real_firebase:
      return _verify_mock_token(token)
  ```
- Issue: Mock authentication can be enabled in any environment
- Risk: If `TESTING=true` accidentally set in production, all auth bypassed
- Tokens like `mock-token-admin-user` would grant admin access
- **Critical Fix Required:**
  1. Remove mock auth from production builds
  2. Add assertion: `assert ENVIRONMENT != 'production' or not is_testing`
  3. Use separate test-only entry point

---

## Missing/Incomplete Features

### No Rate Limiting on File Upload Endpoints

**Risk:** MEDIUM - Resource exhaustion from large uploads
- Files: `api/audio_processing.py`, `api/modules/router.py`
- Issue: File upload endpoints lack size/rate limits
- Current rate limits: Auth (5/min), General API (100/min) via `slowapi`
- Missing: Per-endpoint file size limits, upload rate limits
- Impact: Users can upload massive PDFs causing memory exhaustion
- **Recommendation:**
  - Add `max_upload_size` middleware
  - Implement per-user upload quotas
  - Stream large files instead of loading into memory

### Firestore Security Rules Not Enforced in Backend

**Risk:** MEDIUM - Security rules bypassed by backend
- File: `firestore.rules` (comprehensive rules exist)
- Issue: Backend uses Admin SDK which bypasses security rules
- Impact: Backend code must manually replicate all RBAC logic
- Current: `api/auth.py` has `has_subject_access()`, `has_department_access()` helpers
- Gap: Not consistently enforced across all endpoints
- Example: Direct Firestore queries in `api/hierarchy.py` skip permission checks
- **Recommendation:** Add decorator to enforce permissions on all endpoints

### Incomplete Error Context in Frontend

**Risk:** LOW - Poor debugging experience for production errors
- Files: `frontend/src/api/client.ts`, `frontend/src/stores/useAuthStore.ts`
- Pattern:
  ```typescript
  console.error('Failed to refresh user:', error);
  console.warn('Failed to get auth token', e);
  ```
- Issue: Errors logged to console but not sent to error tracking service
- Missing: Sentry, LogRocket, or similar error monitoring
- Impact: Production errors invisible to developers
- **Recommendation:** Integrate error tracking SDK

### No Database Migration System

**Risk:** MEDIUM - Schema changes require manual intervention
- Files: `api/migrations/001_add_module_schema.py`, `api/migrations/002_kg_enhancement_schema.py`
- Status: Migration files exist but no automated runner
- Issue: Schema changes documented but not version-controlled in database
- Risk: Production/staging schema drift
- **Recommendation:** Implement migration tracking in Firestore metadata collection

---

## Performance Concerns

### Synchronous Neo4j Queries in Request Path

**Risk:** HIGH - Request timeouts on large graphs
- Files: `api/graph_manager.py`, `api/kg_processor.py`
- Issue: Graph queries execute synchronously during API requests
- Example: `api/graph_manager.py:281` - Entity search with no timeout
- Impact: Complex graph traversals block request thread
- Evidence: `asyncio.sleep(0.1)` in `api/kg_processor.py:2939` suggests awareness of blocking
- **Recommendation:**
  1. Add query timeouts to all Neo4j operations
  2. Move large queries to background tasks
  3. Implement pagination for graph results

### No Caching on Hierarchy Read Endpoints

**Risk:** MEDIUM - Unnecessary Firestore reads
- Files: `api/hierarchy.py` - GET endpoints
- Issue: Department/semester/subject lists fetched on every request
- Pattern: Hierarchy rarely changes but read frequently
- Impact: Firestore read quota exhaustion, slow response times
- Current: Redis available but not used for hierarchy caching
- **Recommendation:** Cache hierarchy data with 5-minute TTL

### Embedding Batch Processing Without Backpressure

**Risk:** MEDIUM - Memory exhaustion on large documents
- File: `services/embeddings.py:632-643`
- Code: `get_embeddings_batch()` processes entire batch in memory
- Config: `EMBEDDING_BATCH_SIZE = 100` (line 45)
- Issue: 100 chunks × 30KB text = 3MB per batch minimum
- Risk: Large PDFs create thousands of chunks, exhaust memory
- **Recommendation:** Implement streaming batch processing with yielding

### Frontend Console Logging in Production

**Risk:** LOW - Performance overhead from logging
- Files: `frontend/src/api/client.ts`, `frontend/src/stores/useAuthStore.ts`
- Pattern: 7 instances of `console.log/warn/error` in production code
- Impact: Browser console pollution, minor performance overhead
- **Fix:** Wrap in development-only checks:
  ```typescript
  if (import.meta.env.DEV) {
      console.error('Failed to refresh user:', error);
  }
  ```

---

## Code Quality Issues

### Inconsistent Import Patterns

**Risk:** LOW - Confusion and import errors
- Pattern: Try/except blocks for relative vs absolute imports
- Files: `api/auth.py:42-47`, `api/kg_processor.py:100-105`
- Example:
  ```python
  try:
      from config import get_auth
  except ImportError:
      from api.config import get_auth
  ```
- Issue: Suggests unclear module structure or import path configuration
- Count: 15+ occurrences across API layer
- **Recommendation:** Standardize on absolute imports with proper `sys.path` setup

### Magic Numbers Without Named Constants

**Risk:** LOW - Maintenance difficulty
- Examples:
  - `api/auth.py:75` - `clock_skew_seconds=10` (why 10?)
  - `services/embeddings.py:45` - `RATE_LIMIT_RPM = 60` (Vertex AI limit?)
  - `api/cache.py:32` - `DEFAULT_TTL_SECONDS = 24 * 60 * 60` (24 hours)
  - `api/config.py:59` - `CHUNK_SIZE=800` (tokens or chars?)
- Impact: Context for values lost, hard to tune
- **Recommendation:** Add comments explaining significance

### Duplicate Code in Test Files

**Risk:** LOW - Test maintenance burden
- Pattern: Mock setup repeated across test files
- Files: `tests/test_*.py` - 16 test files
- Example: Firestore mock initialization duplicated
- Impact: Changes to test infrastructure require updates in multiple files
- **Recommendation:** Extract to shared `tests/fixtures.py` or use pytest fixtures

### Inconsistent Function Naming

**Risk:** LOW - Cognitive overhead
- Pattern: Mix of `snake_case` and inconsistent verb usage
- Examples:
  - `get_all_departments()` vs `list_departments()`
  - `delete_document_recursive()` vs `delete_doc_by_id()`
  - `find_doc_by_id()` vs `get_document()`
- Impact: API surface harder to learn
- **Recommendation:** Establish naming conventions in `CONVENTIONS.md`

---

## Dependency Risks

### Deprecated npm Packages

**Risk:** MEDIUM - Known security vulnerabilities
- File: `package-lock.json:2622`
- Package: `glob@7.2.3`
- Warning: "Old versions of glob are not supported, and contain widely publicized security vulnerabilities"
- Status: Marked as deprecated with security advisory
- Additional: `inflight` package (line 2735) also deprecated and leaks memory
- Impact: Potential security exploits in build tooling
- **Action Required:** Update to latest Firebase tools (which pulls in newer glob)

### Python Dependencies Without Version Pins

**Risk:** MEDIUM - Non-reproducible builds
- File: `requirements.txt`
- Issues:
  - Line 11: `slowapi` - no version specified
  - All major packages use `==` pinning (good)
  - But transitive dependencies not locked
- Impact: Different environments may install incompatible versions
- **Recommendation:**
  1. Pin `slowapi` version
  2. Generate `requirements-lock.txt` with all transitive deps
  3. Use `pip-tools` for dependency management

### Firebase Admin SDK Version Mismatch

**Risk:** LOW - Potential compatibility issues
- Backend: `firebase-admin==6.5.0` (Python)
- Frontend: `firebase@12.8.0` (JavaScript)
- Gap: Major version mismatch (6 vs 12)
- Risk: Auth token format changes between versions
- Status: Currently working, but upgrade path unclear
- **Recommendation:** Check Firebase compatibility matrix

---

## Documentation Gaps

### No API Versioning Strategy

**Risk:** MEDIUM - Breaking changes impact clients
- Status: API lacks version prefix (e.g., `/v1/departments`)
- Issue: No documented process for introducing breaking changes
- Impact: Frontend and backend tightly coupled
- **Recommendation:**
  1. Add `/v1` prefix to all routes
  2. Document versioning strategy in API docs

### Environment Variable Documentation Incomplete

**Risk:** LOW - Deployment friction
- Files: `.env.example`, `.env.template`
- Missing documentation for:
  - `CELERY_RESULT_EXPIRES` - default value not in example
  - `REDIS_PASSWORD` - mentioned in code, not in templates
  - `VERTEX_LOCATION` - no guidance on choosing region
  - `CHUNK_OVERLAP` - no explanation of token overlap concept
- **Recommendation:** Create `ENVIRONMENT.md` with all variables documented

### No Production Deployment Guide

**Risk:** MEDIUM - Deployment errors
- Status: `README.md` covers local development only
- Missing:
  - Firebase configuration for production
  - Neo4j Aura setup instructions
  - Redis deployment requirements
  - Celery worker deployment
  - Environment-specific security settings
- **Recommendation:** Create `DEPLOYMENT.md` with production checklist

### Testing Coverage Unknown

**Risk:** LOW - Unclear what's tested
- Files: `tests/` directory exists with 16 test files
- Issue: No coverage reports in repository
- Config: `pytest-cov==6.0.0` installed but not run in CI
- Missing: Coverage badge, coverage thresholds
- **Recommendation:** Add coverage reporting to test runs

---

## Test Coverage Gaps

### Skipped Tests in CI

**Risk:** MEDIUM - Untested code paths
- Occurrences: 3 skipped tests detected
- Files: `tests/test_api_e2e_duplicates.py:2`, `api/test_celery_tasks_e2e.py:1`
- Pattern: `@pytest.mark.skip` decorator used
- Issue: Tests disabled but still in codebase
- Impact: Features merged without test validation
- **Recommendation:** Enable or remove skipped tests

### No Frontend Unit Test Coverage

**Risk:** MEDIUM - Frontend regressions
- Frontend test framework: Vitest installed (`package.json:11`)
- Status: E2E tests exist (Playwright), unit tests minimal
- Files: Only `frontend/src/stores/useExplorerStore.test.ts` found
- Gap: No tests for components, hooks, or API clients
- Impact: UI regressions caught only in E2E tests (slow feedback)
- **Recommendation:** Add unit tests for critical paths

### Knowledge Graph Operations Untested

**Risk:** HIGH - Data corruption in graph database
- File: `api/kg_processor.py` - 2900+ lines
- Test coverage: `tests/test_kg_router_delete.py` exists but incomplete
- Missing tests for:
  - Entity extraction accuracy
  - Relationship creation
  - Embedding generation failures
  - Neo4j transaction rollbacks
- Impact: Graph data integrity issues difficult to debug
- **Recommendation:** Add comprehensive KG processor test suite

### Authentication Flow Edge Cases

**Risk:** MEDIUM - Auth bypass vulnerabilities
- Tests: `frontend/e2e/auth.spec.ts` covers happy path
- Missing:
  - Token expiration during request
  - Concurrent login/logout race conditions
  - Custom claims update propagation delays
  - Disabled user mid-session behavior
- **Recommendation:** Add auth edge case test suite

---

## Recommendations (Prioritized)

### Immediate (This Week)

1. **Revoke compromised service account keys** (Critical)
   - Files: `serviceAccountKey-auth.json`, `serviceAccountKey-old.json`
   - Action: Revoke in Firebase Console, purge from git history

2. **Replace debug print statements** (High)
   - File: `api/auth.py:78,85,92`
   - Replace with `logger.debug()`

3. **Add environment variable validation** (High)
   - File: `api/main.py`
   - Add startup checks for critical env vars

4. **Remove mock auth from production builds** (Critical)
   - File: `api/auth.py:106-132`
   - Add environment assertion

### Short Term (This Month)

5. **Implement file cleanup cascade** (Medium)
   - File: `api/hierarchy_crud.py:360`
   - Complete TODO for PDF deletion

6. **Add logging to exception handlers** (Medium)
   - Files: All 17 instances of bare `except Exception:`
   - Log before swallowing errors

7. **Update deprecated npm packages** (Medium)
   - Update Firebase tools to pull in patched `glob`

8. **Add query timeouts to Neo4j operations** (High)
   - Files: `api/graph_manager.py`, `api/kg_processor.py`
   - Prevent request timeouts

### Medium Term (This Quarter)

9. **Implement hierarchy caching** (Medium)
   - Use Redis for department/semester/subject lists
   - 5-minute TTL

10. **Add error tracking service** (Medium)
    - Integrate Sentry or similar
    - Capture production errors

11. **Create comprehensive KG test suite** (High)
    - Test entity extraction, relationships, embeddings
    - Ensure graph integrity

12. **Document production deployment** (Medium)
    - Create `DEPLOYMENT.md`
    - Include security checklist

### Long Term (Next Quarter)

13. **Implement database migration system** (Medium)
    - Track schema versions in Firestore
    - Automate migration execution

14. **Add API versioning** (Low)
    - Prefix all routes with `/v1`
    - Document breaking change policy

15. **Standardize empty return values** (Low)
    - Choose single convention per type
    - Update all functions

16. **Extract test infrastructure to fixtures** (Low)
    - Reduce test code duplication
    - Improve test maintainability

---

*Concerns audit: 2026-02-06*
