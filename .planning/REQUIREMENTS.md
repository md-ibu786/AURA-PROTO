# Requirements: AURA-NOTES-MANAGER

**Defined:** 2026-04-06
**Core Value:** Reliable, role-aware management of departmental learning content and processing workflows.

## v1 Requirements

Requirements for milestone v1.1 Codebase Reliability and Hygiene.

### Verification Recovery

- [ ] **TEST-01**: Maintainers can run the canonical frontend E2E auth and RBAC suites without broken fixture imports or stale auth setup wiring.
- [ ] **TEST-02**: Critical frontend E2E flows use deterministic waits and meaningful assertions instead of fixed sleeps or tautological checks.
- [ ] **TEST-03**: Backend and frontend verification commands fail fast on hanging tests and high-signal hygiene issues relevant to this milestone.
- [ ] **TEST-04**: The active verification stack reflects the current product surface and no longer depends on conflicting or stale test configuration defaults.

### Failure Hardening

- [ ] **FAIL-01**: Users receive explicit failure states for audited upload, processing, and admin actions instead of silent no-op behavior.
- [ ] **FAIL-02**: Backend paths that currently swallow failures emit actionable logs or structured failure outcomes without hiding the error.
- [ ] **FAIL-03**: High-risk frontend request flows use a canonical auth and error-handling path instead of ad hoc page-level implementations.

### Hotspot Remediation

- [ ] **PERF-01**: Audited KG lookup and queue endpoints avoid full note collection scans in request paths.
- [ ] **PERF-02**: Audited long-running job and task-status stores are bounded so they cannot grow unbounded in memory over time.
- [ ] **PERF-03**: Known async request hotspots avoid blocking the event loop with audited synchronous external I/O patterns.
- [ ] **PERF-04**: Audited frontend polling and upload flows clean up timers and in-flight requests safely on close, unmount, or navigation.

### Safe Cleanup

- [ ] **CLEAN-01**: High-confidence dead code and placeholder components identified in the audit can be removed without breaking app or test entrypoints.
- [ ] **CLEAN-02**: Secret-like residue and stale generated artifacts identified in the audit are removed or remediated safely.
- [ ] **CLEAN-03**: Unused or stale test utilities and repo artifacts are either pruned or explicitly quarantined with rationale.

### Drift Reduction

- [ ] **DRIFT-01**: Duplicate request, helper, or config paths that currently create reliability drift are consolidated only where behavior is proven equivalent.
- [ ] **DRIFT-02**: Duplicate or conflicting test stacks, docs, or milestone-planning artifacts are reduced so there is one clear source of truth for active workflows.
- [ ] **DRIFT-03**: Shared helper logic identified as low-risk duplication is centralized where doing so removes ongoing divergence risk.

## v2 Requirements

Deferred beyond milestone v1.1.

### Diagnostics and Auditability

- **OBS-01**: Team can trace audited request and background-task failures with structured correlation data.
- **OBS-02**: Cleanup changes produce a formal evidence trail of what was deleted, deferred, or retained and why.

## Out of Scope

Explicitly excluded from this milestone.

| Feature | Reason |
|---------|--------|
| New end-user features unrelated to the audited issues | This milestone is stabilization and cleanup, not product expansion |
| Broad platform migrations or architectural rewrites | Safe-first brownfield delivery takes priority over large structural change |
| Aggressive deletion with weak evidence | Hidden consumers remain a known brownfield risk |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| TEST-01 | TDB | Pending |
| TEST-02 | TDB | Pending |
| TEST-03 | TDB | Pending |
| TEST-04 | TDB | Pending |
| FAIL-01 | TDB | Pending |
| FAIL-02 | TDB | Pending |
| FAIL-03 | TDB | Pending |
| PERF-01 | TDB | Pending |
| PERF-02 | TDB | Pending |
| PERF-03 | TDB | Pending |
| PERF-04 | TDB | Pending |
| CLEAN-01 | TDB | Pending |
| CLEAN-02 | TDB | Pending |
| CLEAN-03 | TDB | Pending |
| DRIFT-01 | TDB | Pending |
| DRIFT-02 | TDB | Pending |
| DRIFT-03 | TDB | Pending |

**Coverage:**
- v1 requirements: 17 total
- Mapped to phases: 0
- Unmapped: 17 ⚠️

---
*Requirements defined: 2026-04-06*
*Last updated: 2026-04-06 after initial definition*
