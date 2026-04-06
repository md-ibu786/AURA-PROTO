# Roadmap: AURA-NOTES-MANAGER

**Milestone:** v1.1 Codebase Reliability and Hygiene
**Phase numbering:** Continued from v1.0 (starts at Phase 6)
**Granularity:** Standard (inferred; no planning granularity setting was available)
**Last updated:** 2026-04-06 (Phase 9 planned)

---

## Phases

- [ ] **Phase 6: Verification Recovery** - Re-establish a trustworthy, deterministic verification baseline before deeper fixes.
- [ ] **Phase 7: Failure Hardening & Shared Seams** - Standardize error handling and low-risk shared paths before hotspot remediation.
- [ ] **Phase 8: Runtime Hotspot Remediation** - Bound audited backend and frontend runtime risks in active request and polling flows.
- [ ] **Phase 9: Safe Cleanup & Repo Hygiene** - Remove proven-safe dead code and stale artifacts after behavior and seams are stabilized.

## Phase Details

### Phase 6: Verification Recovery
**Goal**: Maintainers can trust the active verification workflow to reflect current product behavior and fail fast on audited breakage.
**Depends on**: Phase 5
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, DRIFT-02
**Success Criteria** (what must be TRUE):
  1. Maintainers can run the canonical frontend E2E auth and RBAC suites without broken fixture imports or stale auth setup wiring.
  2. Audited critical frontend E2E flows complete using deterministic waits and meaningful assertions instead of fixed sleeps or tautological checks.
  3. Frontend and backend verification commands stop quickly on hangs and surface the milestone's key hygiene failures early.
  4. There is one clear active verification stack and workflow source of truth for the current product surface.
**Plans:** 5 plans

Plans:
- [x] 06-01-PLAN.md — Fix broken fixture imports (useMockAuth export)
- [x] 06-02-PLAN.md — Fix auth setup wiring and standardize timeouts
- [x] 06-03-PLAN.md — Replace fixed waits with deterministic assertions
- [x] 06-04-PLAN.md — Consolidate E2E stacks (migrate root e2e/ to frontend/e2e/)
- [x] 06-05-PLAN.md — Update documentation for single verification stack

**UI hint**: yes

### Phase 7: Failure Hardening & Shared Seams
**Goal**: Users and maintainers get explicit, consistent failure behavior through shared request and helper paths instead of silent or drift-prone handling.
**Depends on**: Phase 6
**Requirements**: FAIL-01, FAIL-02, FAIL-03, DRIFT-01, DRIFT-03
**Success Criteria** (what must be TRUE):
  1. Users see explicit failure states for audited upload, processing, and admin actions instead of silent no-op behavior.
  2. Audited backend failures produce actionable logs or structured failure outcomes instead of being swallowed.
  3. High-risk frontend request flows use one canonical auth and error-handling path, so equivalent failures present consistently across pages.
  4. Proven-equivalent duplicate request, helper, or config seams are centralized so reliability fixes land in one place instead of drifting.
**Plans:** 3 plans

Plans:
- [x] 07-01-PLAN.md — Backend silent failure remediation (audio_processing.py)
- [x] 07-02-PLAN.md — Frontend error infrastructure (client.ts consolidation)
- [x] 07-03-PLAN.md — Auth store migration (useAuthStore fetch consolidation)

**UI hint**: yes

### Phase 8: Runtime Hotspot Remediation
**Goal**: Audited runtime hotspots are bounded so common request, queue, polling, and upload paths stay responsive over time.
**Depends on**: Phase 7
**Requirements**: PERF-01, PERF-02, PERF-03, PERF-04
**Success Criteria** (what must be TRUE):
  1. KG lookup and queue actions no longer depend on audited full note collection scans in request paths.
  2. Long-running job and task-status tracking stays bounded during extended use instead of growing without limit in memory.
  3. Audited async request paths avoid blocking the event loop with synchronous external I/O patterns.
  4. Frontend polling and upload flows clean up timers and in-flight requests safely on close, unmount, or navigation.
**Plans:** 2 plans

Plans:
- [x] 08-01-PLAN.md — Remove KG request-path note scans and align bounded note lookup behavior
- [x] 08-02-PLAN.md — Bound audio job status retention and lock in frontend polling cleanup
**UI hint**: yes

### Phase 9: Safe Cleanup & Repo Hygiene
**Goal**: The repo is safer and easier to maintain because proven-safe dead code and stale artifacts are removed only after verification and reliability seams are stable.
**Depends on**: Phase 8
**Requirements**: CLEAN-01, CLEAN-02, CLEAN-03
**Success Criteria** (what must be TRUE):
  1. High-confidence dead code and placeholder components identified in the audit are removed without breaking app or test entrypoints.
  2. Secret-like residue and stale generated artifacts identified in the audit are removed or remediated so checkout and review no longer expose audited leftovers.
  3. Unused or stale test utilities and repo artifacts are either pruned or explicitly quarantined with rationale.
**Plans:** 3 plans

Plans:
- [x] 09-01-PLAN.md — Remove tracked credential leaks and add secret-scan guardrails
- [ ] 09-02-PLAN.md — Purge generated artifacts and retire the deprecated root E2E implementation
- [ ] 09-03-PLAN.md — Refresh docs and planning maps to the cleaned canonical workflows

## Progress Table

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 6. Verification Recovery | 0/5 | Planned | - |
| 7. Failure Hardening & Shared Seams | 0/3 | Planned | - |
| 8. Runtime Hotspot Remediation | 0/2 | Planned | - |
| 9. Safe Cleanup & Repo Hygiene | 0/3 | Planned | - |
