# Project Research Summary

**Project:** AURA-NOTES-MANAGER v1.1 Codebase Reliability and Hygiene
**Domain:** Brownfield full-stack reliability and hygiene milestone
**Researched:** 2026-04-06
**Confidence:** HIGH

## Executive Summary

This milestone is not a product expansion; it is a brownfield stabilization pass on an existing React 18 + Vite + FastAPI application with Firestore, Neo4j, and background processing already in place. The research is consistent across stack, feature, architecture, and pitfalls: experts do this kind of work by hardening existing seams first, restoring trust in verification, then making narrowly-scoped runtime and cleanup fixes behind proven contracts. The right v1.1 strategy is to keep the current architecture, add low-friction reliability tooling, and avoid rewrites disguised as hygiene work.

For v1.1, the highest-value work is: recover deterministic tests and CI signal, harden runtime error paths so failures become explicit and diagnosable, remediate audited hang/full-scan/unbounded-state hotspots, then execute evidence-based cleanup of dead code, stale artifacts, secret-like leftovers, and low-risk duplicate drift. The biggest risks are over-deletion, refactoring before baselining behavior, and fixing one layer while contracts drift in another. Mitigation is also consistent across the research: baseline first, organize work by end-to-end flow rather than file type, centralize reliability logic at API/router/query seams, and keep every cleanup step reversible.

## Key Findings

### Recommended Stack

v1.1 should keep the existing product stack and add only tooling that directly improves reliability, diagnosability, and cleanup safety. The research strongly recommends configuration tightening and thin guardrails over framework churn.

**Core technologies:**
- **React 18.3.x + Vite 6.x:** keep the current frontend foundation — reliability gains should come from stricter testing/linting and better data-flow discipline, not migration.
- **FastAPI 0.115.x:** keep the backend runtime — central exception handling, middleware, and bounded async behavior matter more than backend restructuring.
- **Firestore + Neo4j + existing cache:** keep current persistence and focus on bounded queries, indexes, TTLs, and task-state hygiene before considering infra changes.
- **GitHub Actions:** add split verification lanes so fast checks gate cleanup early and heavier suites remain targeted.
- **`typescript-eslint` 8.58.0:** must-have for type-aware async correctness and unused-code signal in a brownfield TS codebase.
- **`eslint-plugin-playwright` 2.10.1 + `eslint-plugin-testing-library` 7.16.2:** must-have to eliminate flaky test patterns and weak assertions.
- **`pytest-timeout` 2.4.0 + `ruff` 0.15.9:** must-have backend hygiene tools for hanging tests and low-friction Python cleanup.
- **`knip` 6.3.0:** must-have report-first dead-code detector; use as evidence, not auto-delete authority.
- **`gitleaks` 8.30.1:** must-have because the audit already found secret-like residue.
- **Optional only if needed:** `python-json-logger`, `asgi-correlation-id`, and `jscpd` for diagnostics/reporting without broad platform expansion.

**Critical version requirements:**
- Pin the recommended lint/test/hygiene tools closely for reproducible CI rollout.
- Do **not** introduce mypy/pyright, new observability platforms, new job orchestration, or framework/database migrations in v1.1.

### Expected Features

The feature research treats this milestone as a reliability release for maintainers and users, not as a new capability launch. The table stakes are all about restoring trust in current behavior and proving cleanup safety.

**Must have (table stakes):**
- **Deterministic test recovery** — fix flaky fixtures, invalid assertions, fixed sleeps, and CI drift so the verification signal becomes trustworthy again.
- **Runtime error-path hardening** — replace silent failures and hangs with explicit API/UI failure states plus actionable logging.
- **Hot-path performance and hang remediation** — address audited slow scans, hanging paths, and unbounded runtime/task growth in known flows.
- **Safe dead-code, stale-artifact, and secret-risk cleanup** — remove only high-confidence leftovers and rotate/remediate exposed secret-like material.
- **Low-risk duplication and config-drift reduction** — consolidate only proven-equivalent helpers/configs that are already causing reliability drift.
- **Release gate alignment** — make build/lint/test gates reflect the actual brownfield product surface.

**Should have (milestone differentiators):**
- **Risk-based test stratification** — fast must-pass lanes plus slower deeper coverage.
- **Regression guardrails for audited hotspots** — bounds/assertions that keep hangs and scan regressions from coming back.
- **Cleanup evidence trail** — lightweight inventory of what was deleted, deferred, and why.

**Defer (v2+ / optional polish):**
- **Failure diagnostics toolkit** beyond targeted logging/traces.
- Any net-new end-user features, broad architectural rewrites, observability platform rollout, or speculative cleanup.

### Architecture Approach

Architecture guidance is clear: v1.1 should be implemented as a stabilization layer across existing boundaries. The product already has the correct macro-shape; the milestone should harden the seams between frontend API usage, FastAPI router/service boundaries, background task status, and test harnesses.

**Major components:**
1. **Frontend API client + feature API modules** — the canonical seam for auth, error parsing, request cancellation/timeouts, and consistent retries.
2. **React Query hooks / page orchestration** — own server-state fetching, polling, invalidation, and user-visible loading/error states; remove ad hoc page-level fetch logic.
3. **FastAPI app composition in `api/main.py`** — centralize middleware, health/readiness, exception handling, and startup/shutdown behavior.
4. **Routers and service/helper modules** — routers validate/auth/map errors; helpers own side effects and bounded query/task behavior.
5. **Background processing surfaces** — long-running jobs must expose one canonical, bounded, observable status surface.
6. **Test harnesses and verification scripts** — prove current contracts before cleanup and verify each removal/consolidation stream safely.

**Key patterns to follow:**
- Harden seams before extracting internals.
- Keep server state in React Query and UI-only state in Zustand.
- Enforce auth and policy at router level.
- Use contract-first cleanup: capture behavior, then delete/consolidate.

### Critical Pitfalls

The pitfall research is highly aligned with the feature and architecture findings: most failure modes come from acting on cleanup instinct without evidence.

1. **Deleting by smell instead of evidence** — require a deletion rubric, owner confidence, and targeted verification before removing anything.
2. **Refactoring before baselining behavior** — establish smoke/contract/characterization coverage before structural edits.
3. **Treating flaky tests as test-only problems** — fix isolation, waits, data, ports, and runtime ambiguity instead of masking with retries or sleeps.
4. **Cross-layer contract drift** — organize work by user flow so frontend, backend, and E2E changes stay aligned.
5. **Unsilencing failures without observability** — pair error-path cleanup with structured logs, request/task context, and explicit failure semantics.

## Implications for Roadmap

Based on the combined research, v1.1 should be planned as five tightly-scoped phases. This order is the safest for a brownfield repo because every later cleanup action depends on trustworthy verification and stable cross-layer contracts.

### Phase 1: Baseline Verification and Release Gates
**Rationale:** Nothing else is safe until the team can prove current behavior and trust CI again.
**Delivers:** aligned ports/config, failing-suite inventory, critical smoke coverage, split CI lanes, quarantine policy, and baseline verification artifacts.
**Addresses:** release gate alignment, deterministic test recovery.
**Avoids:** refactoring before baselines, permanent quarantines, local-only confidence.

### Phase 2: Cross-Cutting Runtime and Error Hardening
**Rationale:** Shared reliability logic should be fixed centrally before touching domain hotspots.
**Delivers:** hardened `frontend/src/api/client.ts`, centralized FastAPI exception handling/middleware in `api/main.py`, stable auth/error mapping, and explicit user-safe failure states.
**Addresses:** runtime error-path hardening; foundation for diagnostics and stable contracts.
**Uses:** existing React/Vite/FastAPI stack plus optional structured logging primitives if current logs are too weak.
**Avoids:** cross-layer contract drift, noisy opaque failures, duplicated reliability logic.

### Phase 3: Hotspot and Boundedness Remediation
**Rationale:** Audited hangs, scans, and unbounded task/status behavior are the highest runtime risks once shared seams are stable.
**Delivers:** bounded query patterns, task-status retention limits/adapters, fixes for known audio/KG/explorer hot paths, and before/after evidence for performance or hang reduction.
**Addresses:** hot-path performance and hang remediation.
**Implements:** router/service/task seam hardening in `api/audio_processing.py`, `api/kg/router.py`, `api/explorer.py`, `api/hierarchy_crud.py`, and related helpers.
**Avoids:** “performance fixes” without representative bounds proof.

### Phase 4: Deterministic Test and Fixture Stabilization
**Rationale:** After runtime behavior is stabilized, test repair becomes durable instead of cosmetic.
**Delivers:** Playwright fixed-wait removal, locator/web-first assertions, Vitest/pytest timeout and setup cleanup, canonical fixtures/seeds, and targeted contract tests around risky flows.
**Addresses:** deterministic test recovery, regression guardrails, test data/fixture repair.
**Uses:** `eslint-plugin-playwright`, `eslint-plugin-testing-library`, `pytest-timeout`, and test-harness config tightening.
**Avoids:** retry-and-timeout masking, implementation-detail testing, fixture ownership drift.

### Phase 5: Safe Cleanup, Drift Reduction, and Final Verification
**Rationale:** Deletion and deduplication should be last, once contracts and verification tripwires exist.
**Delivers:** high-confidence dead-code removal, stale artifact cleanup, secret-risk remediation, low-risk dedupe/config normalization, cleanup evidence trail, and final integrated verification/rollback notes.
**Addresses:** safe dead-code cleanup, low-risk duplication/config-drift reduction.
**Uses:** `knip`, `gitleaks`, optional `jscpd`, and repo cleanup inventory scripts/docs.
**Avoids:** deleting by smell, over-consolidating non-equivalent duplicates, and grab-bag rewrite churn.

### Phase Ordering Rationale

- **Verification must come first** because cleanup without a trusted signal is guesswork.
- **Shared seams precede feature-specific fixes** because auth/error/query drift is cross-cutting.
- **Runtime hotspot remediation precedes broad test cleanup** so tests can be fixed against stable behavior, not moving targets.
- **Cleanup comes last** because dead-code deletion and dedupe are safest only after contracts are protected.
- **Each phase should map to end-to-end flows** (explorer, upload/audio, KG, auth/admin) rather than isolated file buckets.

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 3: Hotspot and Boundedness Remediation** — needs repo-specific confirmation of the worst Firestore scans, Neo4j hotspots, and background task durability limits.
- **Phase 5: Safe Cleanup, Drift Reduction, and Final Verification** — hidden consumers of scripts/routes/artifacts remain the biggest brownfield uncertainty and need evidence review.

Phases with standard patterns (likely skip deeper research-phase):
- **Phase 1: Baseline Verification and Release Gates** — well-documented CI/test stabilization patterns.
- **Phase 2: Cross-Cutting Runtime and Error Hardening** — standard FastAPI middleware/exception and frontend API-client normalization patterns.
- **Phase 4: Deterministic Test and Fixture Stabilization** — Playwright, Vitest, pytest guidance is strong and current.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Mostly official docs and conservative “keep current stack, add low-friction tooling” guidance. |
| Features | HIGH | Strong fit to milestone scope and backed by official Playwright, pytest, FastAPI, and GitHub security guidance. |
| Architecture | HIGH | Recommendations are brownfield-specific and aligned with both official framework guidance and current repo shape. |
| Pitfalls | MEDIUM-HIGH | Strong general brownfield patterns plus official testing guidance; some prevention advice is synthesized rather than framework-prescriptive. |

**Overall confidence:** HIGH

### Gaps to Address

- **Hotspot exactness:** the summary knows the classes of audited bottlenecks, but requirement scoping should confirm the concrete endpoints, query shapes, and worst-case datasets before Phase 3 commitments.
- **Hidden consumer uncertainty:** dead code, stale scripts, and duplicate configs need repo-level ownership review before deletion.
- **Task-status durability:** if current in-memory/background status handling breaks across restart or multi-process execution, planning may need a slightly deeper design decision than a thin adapter.
- **Log maturity baseline:** decide during planning whether plain centralized logging is enough or whether structured JSON/request correlation is required for v1.1 acceptance.

## Sources

### Primary (HIGH confidence)
- Playwright docs and best practices — locator-first interaction, auto-waiting, discouraged fixed sleeps, isolation, CI guidance.
- TypeScript-ESLint docs / Context7 `/typescript-eslint/typescript-eslint` — typed linting, `recommendedTypeChecked`, async-safety rules.
- Vitest docs / Context7 `/vitest-dev/vitest/v4.0.7` — timeout, retry, polling, and test configuration guidance.
- pytest docs and `pytest-timeout` docs — flaky test causes, timeout configuration, deterministic testing expectations.
- FastAPI docs / Context7 `/fastapi/fastapi/0.128.0` — exception handling, middleware, router/dependency structure, bigger-app patterns.
- GitHub secret scanning docs and Gitleaks official releases — secret-risk detection and remediation expectations.
- Repo-local planning docs: `.planning/PROJECT.md`, `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/CONCERNS.md`, `.planning/codebase/TESTING.md`.

### Secondary (MEDIUM confidence)
- Knip docs — dead-code detection strategy for TS projects.
- Ruff docs — Python linting/cleanup approach.
- `python-json-logger`, `asgi-correlation-id`, and JSCPD package docs — optional additions for targeted diagnostics/reporting.
- Martin Fowler and Semaphore brownfield/flaky-test guidance — useful supporting principles for legacy cleanup and test stabilization.

### Tertiary (LOW confidence)
- None material to the main milestone recommendation; most uncertainty is repo-specific, not source-quality driven.

---
*Research completed: 2026-04-06*
*Ready for roadmap: yes*
