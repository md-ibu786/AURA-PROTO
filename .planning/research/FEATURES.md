# Feature Landscape

**Domain:** Brownfield reliability and hygiene milestone for an existing production-like full-stack app
**Researched:** 2026-04-06

## Table Stakes

Features users and maintainers expect from a dedicated stabilization release. Missing = the milestone did not actually stabilize the product.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Deterministic test recovery | A reliability milestone must restore trust in the verification signal before any cleanup can ship safely. | High | **User-visible:** fewer regressions escaping to users. **Developer-visible:** frontend, backend, and E2E suites run consistently; broken fixtures, invalid assertions, and fixed sleeps are replaced with stable checks. Playwright explicitly recommends isolated tests, locator-based interactions, and web-first assertions over manual waits/assertions; pytest documents flaky tests as a trust-eroding CI problem caused by uncontrolled state. |
| Runtime error-path hardening | Stabilization work must remove silent failures and convert opaque breakage into explicit, diagnosable outcomes. | Medium | **User-visible:** failures surface as clear messages/states instead of hangs or no-ops. **Developer-visible:** FastAPI handlers raise/translate failures consistently, logs expose actionable context, and frontend error states stop swallowing exceptions. |
| Hot-path performance and hang remediation | Users expect the app to stay responsive in explorer, processing, and KG flows; a stabilization milestone that leaves known hotspots untouched is incomplete. | High | **User-visible:** key screens/actions stop freezing, timing out, or degrading under realistic data volume. **Developer-visible:** bounded async work, removal of full scans in known hotspots, and elimination of unbounded in-memory task growth. Scope this to audited bottlenecks, not speculative optimization. |
| Safe dead-code, stale-artifact, and secret-risk cleanup | Brownfield hygiene work is expected to remove high-confidence leftovers that increase risk, confusion, or accidental exposure. | Medium | **User-visible:** smaller chance of broken legacy paths and accidental exposure. **Developer-visible:** orphaned files, stale generated artifacts, and secret-like leftovers are removed or rotated with evidence; GitHub secret scanning guidance supports immediate credential rotation when exposed secrets are found. |
| Low-risk duplication and config-drift reduction | Reliability work should reduce obvious duplicated helpers/configs that cause inconsistent behavior and audit drift. | Medium | **User-visible:** fewer environment-specific inconsistencies. **Developer-visible:** one clear source of truth for low-risk duplicated setup, fewer parallel helper implementations, and less maintenance drag. Keep consolidation narrow and evidence-based. |
| Release gate alignment for the current codebase | A stabilization milestone should leave behind a repeatable way to prove the app still works after cleanup. | Medium | **User-visible:** more confidence that shipped fixes stay fixed. **Developer-visible:** build/lint/test expectations match actual product behavior, CI gates reflect current routes/workflows, and audited issue classes become release blockers instead of tribal knowledge. |

## Differentiators

Useful additions that make the milestone meaningfully better than a basic cleanup pass, but are not required to claim the release is stable.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Failure diagnostics toolkit | Turns failures from "repro locally and guess" into fast diagnosis. | Medium | **User-visible:** quicker recovery from production-like issues. **Developer-visible:** trace capture for flaky E2E failures, structured logging around processing/KG flows, and enough context to identify where a request stalled or failed. |
| Risk-based test stratification | Makes the suite fast enough to use continuously without reducing safety. | Medium | **User-visible:** faster fix turnaround because safe changes merge sooner. **Developer-visible:** clear split between must-pass smoke/regression tests and slower deeper coverage; quarantine is temporary and explicit, not permanent hiding. |
| Regression guardrails for audited hotspots | Prevents the same classes of hangs, scans, and cleanup regressions from reappearing next month. | Medium | **User-visible:** reliability improvements persist after the milestone. **Developer-visible:** targeted performance assertions, task-store bounds, or focused checks around known hot paths and error states. |
| Cleanup evidence trail | Makes brownfield cleanup reviewable and reversible. | Low | **User-visible:** safer rollout of cleanup changes. **Developer-visible:** concise inventory of what was deleted/consolidated and why, plus validation notes for uncertain artifacts deferred out of scope. |

## Anti-Features

Features to explicitly NOT build in this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Net-new end-user features | This milestone is for stabilization; new product scope dilutes verification and increases regression risk. | Preserve current shipped behavior and spend scope on reliability defects already identified. |
| Broad architectural rewrites or platform migrations | Rewrites hide risk inside "cleanup" and break the safe-first constraint in a brownfield codebase. | Apply surgical fixes to audited hotspots inside the current React/Vite + FastAPI architecture. |
| Test-count vanity work | More tests are not the goal; brittle or implementation-detail tests increase maintenance and false confidence. | Replace broken tests with behavior-level coverage that matches user-visible outcomes and stable contracts. |
| Retry-and-timeout masking | Extra sleeps, blanket retries, and catch-all suppression make CI greener while leaving root causes in place. | Remove uncontrolled waits, isolate state, and fix actual race conditions or hangs. |
| Aggressive deletion with weak evidence | Brownfield repos often have hidden consumers; speculative removal creates outage risk. | Remove only high-confidence dead code/artifacts now; mark uncertain items for later verification. |
| Noisy observability sprawl | Over-instrumentation creates cost and noise without improving diagnosis. | Add targeted logging/tracing around audited failure paths and hotspots only. |

## Feature Dependencies

```text
Release gate alignment → Deterministic test recovery → Safe dead-code cleanup
Release gate alignment → Deterministic test recovery → Low-risk duplication/config-drift reduction
Runtime error-path hardening → Failure diagnostics toolkit
Runtime error-path hardening → Hot-path performance and hang remediation
Deterministic test recovery → Regression guardrails for audited hotspots
Cleanup evidence trail → Safe dead-code cleanup
Cleanup evidence trail → Low-risk duplication/config-drift reduction
```

## MVP Recommendation

Prioritize:
1. **Deterministic test recovery**
2. **Runtime error-path hardening**
3. **Hot-path performance and hang remediation**
4. **Safe dead-code, stale-artifact, and secret-risk cleanup**
5. **Low-risk duplication and config-drift reduction**

Defer: **Failure diagnostics toolkit** — valuable, but only after the baseline stabilization categories above are under control.

## Milestone-Scoping Guidance

For requirements, scope work as concrete categories rather than generic "code quality":

1. **Verification signal recovery** — fix broken/flaky tests, fixtures, assertions, waits, and CI mismatches.
2. **Failure-surface hardening** — replace silent failure paths with explicit API/UI handling and actionable logs.
3. **Hotspot remediation** — remove audited hangs, full scans, and unbounded runtime growth in known paths.
4. **Safe cleanup** — remove high-confidence dead code, stale artifacts, and secret-like leftovers.
5. **Drift reduction** — consolidate low-risk duplicate setup/config/helpers where divergence is already causing reliability problems.
6. **Optional milestone polish** — traces, targeted regression guardrails, and cleanup evidence docs.

## Sources

- Project context: `.planning/PROJECT.md` — HIGH confidence
- Playwright Best Practices: https://playwright.dev/docs/best-practices — HIGH confidence
- Playwright Auto-waiting / Actionability: https://playwright.dev/docs/actionability — HIGH confidence
- pytest Flaky Tests: https://docs.pytest.org/en/stable/explanation/flaky.html — HIGH confidence
- FastAPI Handling Errors: https://fastapi.tiangolo.com/tutorial/handling-errors/ — HIGH confidence
- GitHub Secret Scanning: https://docs.github.com/en/code-security/secret-scanning/introduction/about-secret-scanning — HIGH confidence
