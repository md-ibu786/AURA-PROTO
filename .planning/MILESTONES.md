# Milestones

## v1.1 Codebase Reliability and Hygiene (Shipped: 2026-04-07)

**Phases completed:** 0 phases, 0 plans, 0 tasks

**Key accomplishments:**

- (none recorded)

---

## v1.1 Codebase Reliability and Hygiene (Shipped: 2026-04-06)

**Phases completed:** 4 phases (6-9), 13 plans, 4 tasks

**Key accomplishments:**

### Phase 6: Verification Recovery

- Fixed broken E2E fixture imports with `useMockAuth` export alias for backward compatibility
- Fixed auth setup wiring and standardized timeout configuration across test suites
- Replaced fixed sleeps with deterministic wait utilities and meaningful assertions
- Migrated deprecated root `e2e/` to `frontend/e2e/`, consolidating to single E2E stack
- Updated documentation to reflect canonical verification workflows

### Phase 7: Failure Hardening & Shared Seams

- Backend silent failure remediation in `audio_processing.py` — explicit error states instead of no-ops
- Frontend error infrastructure consolidation in `client.ts` — centralized auth and error handling
- Auth store migration in `useAuthStore` — fetch logic consolidated to single canonical path

### Phase 8: Runtime Hotspot Remediation

- Removed KG request-path note collection scans — bounded Firestore queries now in place
- Bound audio job status retention with TTL-based eviction and max-entry limits
- Frontend polling cleanup verified — timers and in-flight requests properly cleaned on unmount/navigation

### Phase 9: Safe Cleanup & Repo Hygiene

- Removed tracked credential leaks from repository tracking
- Added Gitleaks CI guardrail to prevent future secret leaks
- Purged generated coverage and test report artifacts
- Removed deprecated root E2E implementation (tombstone retained in `frontend/e2e/`)
- Added explicit `.gitignore` patterns for cleaned artifact classes
- Refreshed operator documentation to reflect cleaned canonical workflows

**Requirements validated:** 17/17 (TEST-01 through TEST-04, FAIL-01 through FAIL-03, PERF-01 through PERF-04, CLEAN-01 through CLEAN-03, DRIFT-01 through DRIFT-03)

---

## v1.0 Authentication System (Shipped: 2026-03-08)

**Phases completed:** 5 phases, 9 plans, 8 tasks

**Key accomplishments:**

- Mock Firestore infrastructure for local development without Firebase credentials
- FastAPI authentication module with UserInfo model and role-based dependencies
- User management API with CRUD endpoints and department-level access control
- Zustand auth store with session persistence and role helpers
- Login page, ProtectedRoute component, and sidebar logout integration
- Seed script with 3 test users and 8 integration tests

---
