# Project Retrospective

*A living document updated after each milestone. Lessons feed forward into future planning.*

## Milestone: v1.1 — Codebase Reliability and Hygiene

**Shipped:** 2026-04-06
**Phases:** 4 | **Plans:** 13 | **Sessions:** ~13

### What Was Built
- Fixed broken E2E fixture imports and standardized timeout configuration
- Replaced fixed sleeps with deterministic wait utilities and meaningful assertions
- Migrated deprecated root `e2e/` to `frontend/e2e/`, consolidating to single E2E stack
- Backend silent failure remediation — explicit error states instead of no-ops
- Frontend error infrastructure consolidation in `client.ts` with centralized auth and error handling
- Auth store migration — fetch logic consolidated to single canonical path
- Removed KG request-path note collection scans — bounded Firestore queries now in place
- Bound audio job status retention with TTL-based eviction and max-entry limits
- Frontend polling cleanup verified — timers and in-flight requests properly cleaned on unmount/navigation
- Removed tracked credential leaks and added Gitleaks CI guardrail
- Purged generated coverage and test report artifacts
- Removed deprecated root E2E implementation (tombstone retained)

### What Worked
- Safe-first cleanup strategy — reduced risk in brownfield codebase
- Phase ordering worked well: verification first, shared seams second, runtime hotspots third, cleanup last
- TDD approach for regression tests ensured fixes were verifiable
- Centralizing error handling and auth paths before cleanup reduced risk of regressions

### What Was Inefficient
- Some fixture imports had hidden dependencies that required multiple iterations to fully fix
- Mixed legacy test stacks created confusion about which was the canonical source of truth

### Patterns Established
- Bounded Firestore queries should be the default pattern to prevent performance issues at scale
- TTL-based eviction for in-memory stores prevents unbounded growth
- Centralized error handling via dedicated error classes rather than ad-hoc error handling
- CI guardrails (gitleaks) prevent credential leaks before they enter the repository

### Key Lessons
1. Verification infrastructure must be trustworthy before attempting deeper fixes — fix tests first
2. Centralize error handling early to avoid inconsistent failure modes across pages
3. Safe cleanup with tombstones and CI guardrails enables confident removal of legacy code
4. Bounded queries and TTL evictions are essential patterns for production-grade Firestore and in-memory stores

### Cost Observations
- Model mix: primarily opus for implementation, sonnet for reviews and guidance
- Sessions: ~13 sessions for 4 phases, 13 plans
- Notable: milestone focused on reliability hygiene rather than new features — lower visible output but high long-term value

---

## Cross-Milestone Trends

### Process Evolution

| Milestone | Sessions | Phases | Key Change |
|-----------|----------|--------|------------|
| v1.0 | ~9 | 5 | MVP authentication system with mock infrastructure |
| v1.1 | ~13 | 4 | Reliability and hygiene — test fixes, error handling, performance, cleanup |

### Cumulative Quality

| Milestone | Requirements | Validated | Key Quality Focus |
|-----------|--------------|-----------|-------------------|
| v1.0 | 9 | 9/9 | Authentication, RBAC, mock infrastructure |
| v1.1 | 17 | 17/17 | Test reliability, error handling, performance, cleanup |

### Top Lessons (Verified Across Milestones)

1. Mock infrastructure enables development without external dependencies (v1.0 lesson applied in v1.1)
2. Centralized patterns (auth, error handling) reduce inconsistency bugs
3. Verification-first approach catches issues before they compound
