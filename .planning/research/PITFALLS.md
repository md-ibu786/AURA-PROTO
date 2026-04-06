# Domain Pitfalls

**Domain:** Brownfield reliability and hygiene milestone for a full-stack app
**Researched:** 2026-04-06

## Critical Pitfalls

Mistakes here commonly turn a “cleanup” milestone into a regression milestone.

### Pitfall 1: Deleting by smell instead of by evidence
**What goes wrong:** Teams remove files, helpers, configs, endpoints, scripts, or test assets because they look unused, duplicated, or stale.
**Why it happens:** Brownfield repos have weak ownership, hidden operators, undocumented scripts, and low-confidence search results. “No import found” is treated as proof.
**Consequences:** Hidden admin flows, CI jobs, local tooling, cron-like tasks, or emergency scripts break after merge. Rollbacks become messy because multiple deletions shipped together.
**Prevention:** Require a deletion rubric: search references, inspect runtime/config usage, check CI/dev scripts, and classify each candidate as high-confidence removable vs uncertain. Delete only high-confidence items in this milestone; quarantine uncertain items behind a review list.
**Detection:** Removal PRs with large delete counts but little validation; rationale like “seems unused”; no explicit owner sign-off; no before/after verification artifact.
**Absorb in roadmap phases:** Audit/Baseline, Safe Cleanup, Release Verification.

### Pitfall 2: Refactoring before establishing behavior baselines
**What goes wrong:** Teams “clean up” runtime paths, async flows, or component boundaries before they have characterization tests, golden outputs, or route-level smoke coverage.
**Why it happens:** The code is obviously messy, so cleanup feels urgent. But in brownfield systems, messy code often encodes real edge-case behavior.
**Consequences:** Hidden compatibility breaks, changed error semantics, altered timing, broken role-specific flows, and regressions that appear only in integrated environments.
**Prevention:** Build a baseline first: smoke tests for critical journeys, API contract assertions for known endpoints, and characterization coverage for risky modules before structural cleanup. Small behavior-preserving steps beat “one clean refactor.”
**Detection:** PRs claiming “no functional change” without new tests; large movement/renames plus logic edits; failing ability to compare before vs after behavior.
**Absorb in roadmap phases:** Baseline Verification, Test Stabilization, Runtime Hardening.

### Pitfall 3: Treating flaky tests as purely test-code problems
**What goes wrong:** Teams patch around failures with retries, longer sleeps, looser assertions, or skips without checking for actual isolation, data, async, or runtime issues.
**Why it happens:** Flake pressure is immediate, and retries make CI green faster than root-cause analysis.
**Consequences:** CI becomes cosmetically green while real regressions and race conditions remain. Trust in test results collapses.
**Prevention:** Triage flakes by cause class: state leakage, fixed-time waits, external dependency drift, shared data, ordering dependency, thread/process leakage, or real product race. Allow quarantine only with owner, expiry, and issue link.
**Detection:** Rising retry counts, `waitForTimeout`/fixed sleeps, broad `xfail`/skip usage, “rerun and it passes” culture, failures that vanish in isolation.
**Absorb in roadmap phases:** Test Stabilization, Observability/Debuggability, Release Verification.

### Pitfall 4: Partial fixes that clean one layer while leaving cross-layer contracts drifting
**What goes wrong:** Frontend, backend, and E2E fixes are done independently, so payload shapes, status handling, auth assumptions, seed data, and selectors drift.
**Why it happens:** Work is bucketed by file type instead of by end-to-end behavior. Each layer looks “fixed” locally.
**Consequences:** Integration regressions surface late: UI assumes old fields, backend silently changes defaults, tests assert outdated copy, fixtures no longer match runtime reality.
**Prevention:** Organize work around system flows, not file categories. For each audited issue, define impacted contracts and required validations across frontend, backend, and E2E. Keep fixtures and seeds versioned with the behavior they represent.
**Detection:** Separate PRs for frontend and backend “cleanup” with no shared validation plan; passing unit tests but broken end-to-end smoke; fixture drift.
**Absorb in roadmap phases:** Contract Alignment, Integration Verification, Test Data/Fixture Repair.

### Pitfall 5: Replacing silent failures without replacing observability gaps
**What goes wrong:** Teams remove empty catches or broad exception swallowing, but do not add structured logging, correlation context, actionable user errors, or failure surfacing in tests.
**Why it happens:** “Don’t swallow errors” is implemented as “throw more,” without operational visibility design.
**Consequences:** Failures move from invisible to noisy-but-opaque. Debugging remains slow, and production issues become harder to triage across services.
**Prevention:** Pair error-path cleanup with observability rules: log once at the right boundary, attach request/job context, preserve user-safe messaging, and add tests for expected failure semantics. Prefer explicit failure states over silent null/default fallthrough.
**Detection:** More exceptions reaching logs but still no request IDs, actor context, task IDs, or domain classification; support cannot map UI errors to backend traces.
**Absorb in roadmap phases:** Runtime Hardening, Error Handling Cleanup, Observability.

### Pitfall 6: Consolidating duplicates that are only superficially similar
**What goes wrong:** Teams merge configs, helpers, fixtures, API clients, or setup paths because they look redundant, but they actually differ for historical reasons.
**Why it happens:** Duplication is visible; behavioral nuance is not.
**Consequences:** Environment-specific breakage, hidden coupling, loss of escape hatches, or one-size-fits-none abstractions that are harder to maintain than the original duplication.
**Prevention:** Consolidate only when behavior is proven equivalent or intentionally normalized. Capture differences first; if semantics differ, keep separate wrappers with shared lower-level primitives instead of forcing full unification.
**Detection:** “Deduplicate” PRs with semantic edits hidden inside helper extraction; post-merge environment-specific failures; many call sites needing custom flags after the merge.
**Absorb in roadmap phases:** Duplication Review, Low-Risk Consolidation, Post-Consolidation Verification.

### Pitfall 7: Fixing hot paths without representative load or boundedness checks
**What goes wrong:** Teams optimize obvious slow code or hanging paths, but only validate correctness under tiny local datasets and happy-path timing.
**Why it happens:** Brownfield performance bugs are often data-shape dependent: full scans, unbounded in-memory stores, missing cancellation, or blocking calls hidden in async paths.
**Consequences:** “Optimized” code still hangs in production-like scenarios, or new shortcuts introduce correctness bugs under concurrent or larger workloads.
**Prevention:** For each hotspot, define the bound being enforced: max scan scope, timeout, queue retention, pagination, concurrency cap, or cache policy. Validate with representative fixture sizes and worst-case scenarios, not just unit tests.
**Detection:** Performance claims without measurement; no before/after timing or memory evidence; fixes only tested with toy datasets.
**Absorb in roadmap phases:** Runtime Hotspot Remediation, Performance Verification, Capacity Guardrails.

### Pitfall 8: Using repo hygiene as a grab bag for unrelated rewrites
**What goes wrong:** “Cleanup” becomes a license to reformat, rename, move, abstract, and modernize broadly while also fixing audited issues.
**Why it happens:** Hygiene work lowers the social barrier to invasive change.
**Consequences:** Reviewability collapses, root-cause attribution becomes impossible, and rollback risk spikes because bug fixes and style churn ship together.
**Prevention:** Separate mechanical cleanup, behavior fixes, and structural refactors into distinct change sets. The milestone should optimize for proof and reversibility, not maximal tidiness.
**Detection:** Huge PRs mixing lint churn, dead-code deletion, test rewrites, and runtime logic changes; reviewers cannot identify which change fixed which audit finding.
**Absorb in roadmap phases:** Milestone Planning, Change Isolation, Release Verification.

## Moderate Pitfalls

### Pitfall 9: Fixing tests against implementation details instead of user-visible behavior
**What goes wrong:** Tests are updated to match DOM structure, CSS classes, internals, mock call counts, or fragile text fragments rather than the real user outcome.
**Prevention:** Prefer user-facing selectors, contract assertions, and role/behavior-based checks. Use tool-supported locators and web-first assertions for UI flows.
**Detection:** Frequent selector churn after harmless UI refactors; assertions on internals that users never see.
**Absorb in roadmap phases:** Test Stabilization, E2E Repair.

### Pitfall 10: Leaving test data ownership ambiguous
**What goes wrong:** Fixtures, Firestore/DB state, auth identities, and sample files drift separately across frontend, backend, and E2E suites.
**Prevention:** Define canonical test data owners, shared seed strategy, and fixture lifecycle rules. Version fixtures with the flows they support.
**Detection:** Multiple near-duplicate fixtures representing the same domain object; E2E failures after unrelated backend schema tweaks.
**Absorb in roadmap phases:** Test Data/Fixture Repair, Integration Verification.

### Pitfall 11: Quarantining failures permanently
**What goes wrong:** Skips, xfails, retries, and TODO suppressions are added but never revisited.
**Prevention:** Every quarantine needs an owner, ticket, expiry date, and exit condition. Keep quarantine counts visible.
**Detection:** Growing skip/xfail lists; “temporary” suppressions older than the milestone.
**Absorb in roadmap phases:** Test Stabilization, Release Governance.

### Pitfall 12: Fixing the code path but not the diagnostic path
**What goes wrong:** Runtime issues are resolved, but no tracing, logs, metrics, or reproducible failure artifacts are added.
**Prevention:** Any reliability fix should leave behind better diagnostics: trace capture for E2E, structured backend logs, and clear failure messages.
**Detection:** The same class of incident remains expensive to debug even after the fix.
**Absorb in roadmap phases:** Observability, Release Verification.

## Minor Pitfalls

### Pitfall 13: Over-relying on local success criteria
**What goes wrong:** Changes are declared safe because they pass on one developer machine.
**Prevention:** Require CI, clean-environment runs, and at least one integrated smoke path before closing an issue.
**Detection:** “Works on my machine” confidence with no artifact from CI or staging-like validation.
**Absorb in roadmap phases:** CI Reliability, Release Verification.

### Pitfall 14: Hiding uncertainty in milestone reporting
**What goes wrong:** Uncertain deletions, partial contract knowledge, and unverified assumptions are written up as resolved.
**Prevention:** Track “removed,” “deferred,” and “suspected but unverified” separately. Brownfield cleanup needs an explicit uncertainty register.
**Detection:** Closed issue counts rise faster than verified evidence.
**Absorb in roadmap phases:** Audit/Baseline, Milestone Review.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Audit/Baseline | Misclassifying dead code and duplicate setup as safe deletions | Create evidence-backed inventory with confidence levels and owner review before removal |
| Baseline Verification | Refactoring before preserving observed behavior | Add smoke tests, characterization tests, and contract snapshots before structural edits |
| Test Stabilization | Converting red CI to green via waits/retries/skips | Require root-cause tagging, quarantine policy, and deterministic replacements for sleeps |
| Test Data/Fixture Repair | Fixing assertions while leaving data drift unresolved | Establish canonical seeds/fixtures and align them with current runtime contracts |
| Contract Alignment | Frontend/backend/E2E repaired independently | Validate per user flow across all layers, not per file category |
| Runtime Hotspot Remediation | “Performance fix” without load-bound proof | Define bounds, measure before/after, and test worst-case fixture sizes |
| Error Handling Cleanup | Unsilencing failures without observability | Add structured logging, request/task context, and explicit user-safe error semantics |
| Safe Cleanup | Over-deletion of stale-looking artifacts | Delete only high-confidence items; defer uncertain artifacts into a tracked backlog |
| Low-Risk Consolidation | Merging duplicates that encode hidden semantics | Normalize only proven-equivalent behavior; otherwise share primitives, not whole abstractions |
| Release Verification | Shipping mixed cleanup and logic changes together | Keep change sets reviewable and add integrated smoke validation plus rollback clarity |

## Prevention Strategies to Build Into the Roadmap

1. **Start with evidence, not cleanup instinct.** Inventory all candidates for deletion, consolidation, and hotspot remediation with confidence labels.
2. **Baseline critical behavior before touching structure.** Characterization tests and smoke checks should precede invasive cleanup.
3. **Triage by user flow.** Explorer/auth/admin/processing/KG flows should each have cross-layer validation.
4. **Make flake handling explicit.** Root-cause labels, quarantine rules, expiry dates, and deterministic replacements should be milestone policy.
5. **Require boundedness proof for runtime fixes.** Any hang/full-scan/task-store fix needs measurable bounds and representative data validation.
6. **Pair reliability fixes with diagnostics.** The milestone should improve future debuggability, not only current pass rates.
7. **Keep cleanup reversible.** Separate deletion, refactor, and logic-fix PRs so each can be reviewed and rolled back independently.
8. **Track uncertainty openly.** Unknown consumers, suspicious files, and deferred deletions should remain visible inputs for later phases.

## Sources

- `.planning/PROJECT.md` (project-specific milestone scope) — HIGH confidence
- Playwright Best Practices: https://playwright.dev/docs/best-practices — HIGH confidence
- Playwright Auto-waiting / discouraged timeout waits: https://playwright.dev/docs/actionability — HIGH confidence
- pytest flaky tests documentation: https://docs.pytest.org/en/stable/explanation/flaky.html — HIGH confidence
- Martin Fowler, *Refactoring code that accesses external services*: https://martinfowler.com/articles/refactoring-external-service.html — MEDIUM confidence for general brownfield refactoring guidance
- Semaphore, *Addressing Flaky Tests in Legacy Codebases*: https://semaphore.io/blog/flaky-legacy (2024-03-21) — MEDIUM confidence
