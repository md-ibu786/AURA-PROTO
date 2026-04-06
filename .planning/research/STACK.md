# Technology Stack

**Project:** AURA-NOTES-MANAGER v1.1 Codebase Reliability and Hygiene
**Researched:** 2026-04-06

## Recommended Stack

This milestone should **keep the current React 18 + Vite + FastAPI architecture** and add only low-friction tooling that directly addresses the audit buckets: flaky tests, hanging paths, silent failures, dead code, duplicate drift, and repo hygiene.

### Core Framework
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| React | 18.3.x existing | Frontend app runtime | **Keep.** No framework change is justified for a stabilization milestone. |
| Vite | 6.x existing | Frontend build/test integration | **Keep.** Vitest and Playwright already fit this stack. Prefer config tightening over tool churn. |
| FastAPI | 0.115.x existing | Backend API runtime | **Keep.** Reliability gains come from middleware, exception handling, and bounded async behavior, not a backend rewrite. |

### Database
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| Firestore | existing | Primary document storage | **Keep.** Out of scope to swap persistence for a hygiene milestone. |
| Neo4j | existing | KG storage | **Keep.** Address scan hotspots with query/index fixes before considering data-layer changes. |
| Redis / existing cache layer | existing | Bounded caching / task-state support | **Keep and tighten.** Prefer TTLs and bounded keys over introducing new infra. |

### Infrastructure
| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| GitHub Actions / existing CI | existing | Verification pipeline | **Must-have workflow addition.** Add separate fast lanes for lint/typecheck/unit and slower lanes for E2E/smoke so cleanup stays safe without blocking on the heaviest suite every push. |
| Gitleaks | 8.30.1 | Secret scanning for repo hygiene | **Must-have.** The audit already found a secret-like leftover; this is a direct, low-cost guardrail. |
| JSON logging via stdlib logging + `python-json-logger` | 4.1.0 | Structured backend logs | **Optional but recommended.** Good fit if logs are currently ad hoc; lower cost than full APM. |
| Request correlation via `asgi-correlation-id` | 4.3.4 | Trace one request across middleware/handlers | **Optional.** Useful once backend logs are centralized; not required if simple request IDs are added manually first. |

### Supporting Libraries
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `typescript-eslint` | 8.58.0 | Type-aware linting for unhandled promises, unsafe async usage, unused vars, and bad assertions | **Must-have.** Enable `recommendedTypeChecked` and reliability-focused rules such as `no-floating-promises` and `no-misused-promises`. This directly targets brownfield async/runtime bugs. |
| `eslint-plugin-playwright` | 2.10.1 | Lint E2E tests for flaky patterns | **Must-have.** Use to ban `waitForTimeout`-style patterns and other unstable Playwright usage. |
| `eslint-plugin-testing-library` | 7.16.2 | Lint RTL/Vitest test code for invalid patterns | **Must-have.** Good for catching tautological or non-user-centric test assertions with low integration cost. |
| `pytest-timeout` | 2.4.0 | Kill hanging backend tests and cap session duration | **Must-have.** Direct fix for hanging tests and blocking paths; configure globally with targeted overrides. |
| `ruff` | 0.15.9 | Fast Python linting/formatting and unused import cleanup | **Must-have.** Best cost/benefit addition for Python hygiene; catches obvious correctness issues without heavy setup. |
| `knip` | 6.3.0 | Detect unused TS/JS files, exports, and dependencies | **Must-have.** Best low-risk dead-code detector for the frontend/tooling side. Run in report mode first; only delete high-confidence findings. |
| `jscpd` | 4.0.8 | Detect copy/paste duplication | **Optional.** Use only for reporting and targeted consolidation. Do not let it trigger broad refactors in this milestone. |

## Workflow Additions

### Must-Have Verification Patterns

1. **Type-aware frontend linting**
   - Turn on `typescript-eslint` typed linting.
   - Add targeted rules for async correctness and unused code.
   - Run on changed files locally and full tree in CI.

2. **Test determinism guardrails**
   - Replace fixed sleeps in Playwright with locators, auto-waiting, and web-first assertions.
   - Use Vitest built-ins (`testTimeout`, `hookTimeout`, `clearMocks`, `restoreMocks`, `expect.poll`) instead of adding a second JS unit-test stack.
   - Add `pytest-timeout` global defaults plus per-test overrides for known slow integration cases.

3. **Dead-code and hygiene reporting**
   - Run `knip` in CI as a non-blocking report first, then make it blocking only after baseline cleanup.
   - Run `gitleaks` on PRs and on the full repo history at least once during milestone cleanup.

4. **Backend error observability**
   - Add centralized FastAPI exception handlers for `HTTPException`, validation errors, and unexpected exceptions.
   - Add request/response logging middleware with duration and status code.
   - Prefer structured logs and request IDs over a new SaaS monitoring platform.

### Optional but Good Additions

- `jscpd` report to identify the few duplicate helpers/configs worth consolidating.
- `python-json-logger` if current logs are too inconsistent for triage.
- `asgi-correlation-id` if request tracing across async paths is hard to follow.
- Playwright trace/video only on retry/failure, not always-on, to keep CI artifact cost bounded.

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Python linting | Ruff | Pylint-only enforcement | Pylint is useful but slower/noisier for a brownfield cleanup. Ruff gives more immediate signal with less setup friction. |
| TS dead-code detection | Knip | broad manual deletion or deprecated tools like depcheck-only workflows | Knip is stronger for unused files/exports/deps in TypeScript projects; manual deletion is riskier. |
| Secret scanning | Gitleaks | ad hoc grep/manual review | The audit already found a secret-like artifact; manual review is not enough. |
| Test reliability | Tighten Playwright/Vitest/pytest configs | Add a new JS or Python test framework | Overkill. The existing stack is already sufficient; config and fixture cleanup is the right move. |
| Observability | Structured logs + request IDs + centralized handlers | Sentry/New Relic/OpenTelemetry/Prometheus-Grafana rollout | Too much integration and operational scope for a safe-first hygiene milestone unless there is already an adopted platform. |
| Duplication cleanup | Targeted `jscpd` reports + manual review | Automatic large-scale dedupe/refactor | High rewrite risk; this milestone should consolidate only obvious, low-risk duplicates. |
| Async/background reliability | Bound current task storage and use existing infra | Introduce Celery/Temporal/Kafka as new mandatory runtime dependency | Too invasive for this milestone unless an audited issue proves current architecture cannot be made safe without it. |
| Python typing | Ruff + targeted runtime-safe fixes | Full mypy/pyright rollout | Likely too noisy in an under-typed brownfield codebase; defer to a later quality milestone. |

## Explicitly Do **Not** Add in v1.1

- **No framework migrations**: no Next.js, no backend rewrite, no DB swap.
- **No full observability platform rollout**: no OpenTelemetry collector, Prometheus/Grafana stack, or APM vendor unless already in place.
- **No new job orchestration platform** purely for cleanup.
- **No broad typing initiative** (`mypy`, `pyright`) as a gate for this milestone.
- **No SonarQube/CodeClimate-style platform adoption** just to catch issues already covered by targeted linters and CI checks.
- **No aggressive auto-deletion** from dead-code tools; treat reports as evidence, not truth.
- **Do not replace Firestore rules Jest coverage during this milestone** unless the current suite is proven unsalvageable. Duplicate stacks should be reduced only where the migration risk is low.

## Installation

```bash
# Frontend/dev reliability tooling
npm install -D typescript-eslint@^8.58.0 eslint-plugin-playwright@^2.10.1 eslint-plugin-testing-library@^7.16.2 knip@^6.3.0 jscpd@^4.0.8

# Backend reliability tooling
pip install ruff==0.15.9 pytest-timeout==2.4.0 python-json-logger==4.1.0 asgi-correlation-id==4.3.4

# Secret scanning (prefer pinned binary or CI action)
# Use Gitleaks v8.30.1 from the official release or GitHub Action
```

## Sources

- Playwright docs: `page.waitForTimeout()` is discouraged; use locator actions and web-first assertions instead — https://playwright.dev/docs/api/class-page
- Playwright best practices via Context7 (`/microsoft/playwright.dev`) — HIGH confidence
- TypeScript-ESLint typed linting docs (`recommendedTypeChecked`, `projectService`, `no-floating-promises`) — https://typescript-eslint.io / Context7 `/typescript-eslint/typescript-eslint` — HIGH confidence
- Vitest v4 docs for timeouts, retries, config, and `expect.poll` — https://vitest.dev / Context7 `/vitest-dev/vitest/v4.0.7` — HIGH confidence
- `pytest-timeout` docs for global and per-test timeout config — https://github.com/pytest-dev/pytest-timeout / PyPI latest 2.4.0 — HIGH confidence
- Ruff docs and PyPI latest 0.15.9 — https://docs.astral.sh/ruff/ and https://pypi.org/project/ruff/ — HIGH confidence
- Knip docs and npm latest 6.3.0 — https://knip.dev and https://www.npmjs.com/package/knip — MEDIUM-HIGH confidence
- FastAPI docs for custom exception handlers and middleware — https://fastapi.tiangolo.com/tutorial/handling-errors/ and Context7 `/fastapi/fastapi/0.128.0` — HIGH confidence
- `python-json-logger` PyPI latest 4.1.0 — https://pypi.org/project/python-json-logger/ — MEDIUM confidence
- `asgi-correlation-id` PyPI latest 4.3.4 — https://pypi.org/project/asgi-correlation-id/ — MEDIUM confidence
- Gitleaks official releases latest v8.30.1 — https://github.com/gitleaks/gitleaks/releases — HIGH confidence
- JSCPD npm latest 4.0.8 — https://www.npmjs.com/package/jscpd — MEDIUM confidence
