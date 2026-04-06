# Architecture Patterns

**Domain:** Brownfield full-stack reliability milestone for AURA-NOTES-MANAGER v1.1
**Researched:** 2026-04-06

## Recommended Architecture

This milestone should be implemented as a **stabilization layer across existing boundaries**, not as a platform rewrite. The app already has the right macro-shape: React/Vite SPA → typed API client → FastAPI routers → Firestore/Neo4j/background processing. v1.1 should harden those seams.

**Recommendation:**
- **Modify** existing request paths, test harnesses, config entrypoints, and error/reporting surfaces.
- **Add** only thin reliability primitives: shared validation/helpers, bounded task/status adapters, deterministic test fixtures, and verification scripts/checklists.
- **Do not add** new product subsystems, parallel APIs, or a new persistence model for this milestone unless required to remove a verified reliability blocker.

```text
Browser UI
  -> React pages/components
  -> typed API client + React Query
  -> FastAPI router layer
  -> service/helper functions
  -> Firestore / Neo4j / file storage / task queue

Cross-cutting reliability additions:
  - explicit auth + error mapping at API edge
  - bounded query/task behavior in hot paths
  - shared logging/observability contracts
  - deterministic unit/integration/E2E verification
  - safe cleanup inventory + rollback notes
```

### Component Boundaries

| Component | Responsibility in v1.1 | Communicates With |
|-----------|-------------------------|-------------------|
| `frontend/src/api/client.ts` and feature API modules | Canonical frontend integration seam; normalize auth, retries, error parsing, request timeouts/cancellation where applicable | React Query hooks, Zustand auth store, FastAPI routes |
| React Query hooks / page orchestration | Own server-state fetch, invalidation, polling, and loading/error states; remove ad hoc fetch duplication | API client, UI components |
| Zustand stores | Keep UI-only state only; do not absorb server reliability logic | Pages, components, auth bootstrap |
| `api/main.py` | Compose routers, middleware, health/readiness, exception handlers, and app startup/shutdown behavior | Routers, config, middleware |
| FastAPI routers (`explorer`, `audio_processing`, `kg`, `users`, etc.) | Validate input, enforce auth, map domain errors to HTTP, delegate work out of handlers | Service/helper modules, auth deps, task queue |
| Service/helper modules (`notes`, `graph_manager`, task helpers, CRUD helpers) | Hold side-effecting domain logic that needs targeted tests and bounded behavior | Firestore, Neo4j, filesystem, Celery-like workers |
| Background processing surfaces (`audio_processing`, `tasks/document_processing_tasks.py`) | Execute long-running work with durable/observable status boundaries | Firestore, Redis/Celery, frontend polling |
| Test harnesses (pytest, Vitest, Playwright) | Verify contracts at three levels: unit, route/component, end-to-end | App entrypoints, fixtures, test data |
| Verification/cleanup scripts (`api/verify_*.py`, repo hygiene checks) | Prove safe deletion/consolidation before removal lands | Git diff, test/build pipeline, maintainers |

## New vs Modified Surfaces

### Modify First

These are the primary brownfield integration points and should take most of the milestone work:

| Surface | Modify Why | Likely Changes |
|--------|------------|----------------|
| `api/main.py` | Current composition layer already centralizes middleware and router mounting | normalize imports, central exception/logging hooks, startup/lifespan cleanup, route registration clarity |
| `api/audio_processing.py` | Contains in-memory job tracking, file writes, and error-prone async flow | bound status lifetime, explicit failure paths, better auth/validation, isolate pipeline helpers |
| `api/kg/router.py` | Contains global note scans and queue/status wiring | replace full scans where possible, isolate membership lookup, tighten auth, preserve batch contract |
| `api/hierarchy_crud.py`, `api/explorer.py`, `api/notes.py` | Hot path CRUD and cascade logic are brownfield risk centers | bounded queries, explicit delete/file cleanup outcomes, contract tests before refactors |
| `frontend/src/api/client.ts` | Existing canonical client already owns auth/error semantics | unify error parsing, remove silent fallback patterns, keep one retry strategy |
| `frontend/src/pages/*` and feature hooks | Existing page orchestration likely contains stale waits and duplicated fetch logic | move server-state semantics into React Query/hooks, simplify page components |
| `frontend/playwright.config.ts`, test fixtures, Vitest/pytest setup | Reliability issues were audited here directly | align ports, remove fixed waits, make fixtures deterministic, disable unhelpful retries in unit tests |

### Add Sparingly

These additions are justified because they reduce risk without creating a second architecture:

| New Addition | Why Add | Where It Fits |
|-------------|---------|---------------|
| Shared API error/exception mapper | Prevent silent failure drift across routers | FastAPI edge, imported by routers or registered globally |
| Shared query keys / invalidation helpers | Reduce frontend duplication and stale-cache regressions | frontend API/query layer |
| Bounded task-status adapter or repository | Replace raw in-memory/global dict usage without rewriting full pipeline | audio/KG background workflow seam |
| Test fixture factories and seed helpers | Make tests deterministic and rollback-safe | pytest/Vitest/Playwright support code |
| Repo cleanup inventory document/script | Distinguish safe removals from uncertain artifacts | tooling / planning / CI checks |

### Do Not Add in v1.1

- No new frontend state management system
- No backend microservice split
- No broad Firestore-to-new-database migration
- No new user-facing workflows just to justify cleanup
- No duplicate “v2 reliability” routes beside existing ones unless a temporary compatibility shim is required

## Data Flow for Reliability Work

### 1. Runtime hardening flow

1. Request enters `frontend/src/api/client.ts`.
2. Auth header, request parsing, and client-side error normalization happen once.
3. FastAPI router validates input and enforces auth at router/route dependency level.
4. Router delegates to a helper/service function for Firestore/Neo4j/filesystem work.
5. Service returns explicit success/failure shape or raises a typed error.
6. Router maps that to stable HTTP responses.
7. React Query invalidates/refetches canonical keys; UI shows explicit error/loading states.

**Why this matters:** reliability bugs usually happen when steps 2, 4, or 6 are bypassed and each feature invents its own behavior.

### 2. Long-running job flow

1. Frontend triggers upload/KG action via typed API module.
2. FastAPI validates request quickly and returns a job/task ID.
3. Worker/background function owns the long-running side effect.
4. Status is written to one canonical status surface.
5. Frontend polls through React Query with bounded intervals and stop conditions.
6. Completion invalidates the relevant explorer/KG queries.

**Rule for v1.1:** do not hold reliability logic in page components. Put it in API/query/task seams.

## Patterns to Follow

### Pattern 1: Harden existing seams before extracting internals
**What:** Stabilize handler contracts, logging, and tests before splitting files.
**When:** Large brownfield files with active production behavior.
**Example:**
```python
@router.post('/process-batch')
async def process_batch(request: BatchProcessingRequest, user=Depends(require_staff)):
    try:
        task_id = await kg_service.queue_batch(request, user.user_id)
        return BatchProcessingResponse(...)
    except KnownValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
```

### Pattern 2: Server state stays in React Query; UI state stays in Zustand
**What:** Keep network lifecycle, polling, and invalidation out of ad hoc component state.
**When:** Explorer, upload, KG queue, admin views.
**Example:**
```typescript
const queueQuery = useQuery({
  queryKey: ['kg', 'queue'],
  queryFn: getKGProcessingQueue,
  refetchInterval: (query) => query.state.data?.length ? 5000 : false,
});
```

### Pattern 3: Router-level dependencies for auth and shared policy
**What:** Apply auth/security dependencies at router include or router declaration level where possible.
**When:** Existing route groups that should never be public.
**Example:**
```python
router = APIRouter(
    prefix='/kg',
    tags=['KG Processing'],
    dependencies=[Depends(require_staff)],
)
```

### Pattern 4: Contract-first cleanup
**What:** Before deleting or consolidating, capture a contract test and ownership note.
**When:** Dead code candidates, duplicate helpers, stale routes, generated artifacts.
**Example:**
```text
capture current behavior -> add focused test -> remove dead path -> run targeted suite -> keep rollback note in PR
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Architecture-by-cleanup rewrite
**What:** Using a hygiene milestone to reorganize half the codebase.
**Why bad:** High regression risk; rollback becomes impossible because behavior and structure changed together.
**Instead:** Make the runtime/test fix first, then optionally extract isolated helpers.

### Anti-Pattern 2: Duplicating reliability logic in every feature
**What:** Each router/component handles auth, retries, polling, and errors differently.
**Why bad:** Brownfield drift gets worse, not better.
**Instead:** Centralize at the API client, router dependency, and task-status seams.

### Anti-Pattern 3: Deleting “probably dead” code without a consumer check
**What:** Remove routes/files/scripts because they look unused.
**Why bad:** Brownfield repos often have hidden operators, fixtures, or manual workflows.
**Instead:** Tag as safe-remove only after search, test coverage, and owner-confidence review.

### Anti-Pattern 4: Treating flaky tests as a test-only problem
**What:** Patch tests with retries/timeouts instead of fixing data/setup contracts.
**Why bad:** It hides runtime ambiguity and makes CI slower.
**Instead:** Fix ports, fixtures, selectors, waits, auth mode, and deterministic seed/cleanup.

## Safe Build Order

This order is optimized for dependency awareness and rollback safety.

1. **Establish verification baseline**
   - Align ports/config, inventory failing suites, freeze current hot paths.
   - Add missing smoke checks for critical explorer/auth/upload/KG flows.
   - Reason: every later cleanup needs a trustworthy tripwire.

2. **Stabilize entrypoints and cross-cutting seams**
   - `api/main.py`, frontend API client, test configs, auth/bootstrap seams.
   - Add explicit error mapping, router auth coverage, consistent config.
   - Reason: fixes the shared surface area before touching domain logic.

3. **Fix backend runtime hotspots in-place**
   - Tackle full scans, unbounded task stores, hanging async paths.
   - Keep route contracts stable; extract only small helper seams if needed.
   - Reason: lowers production risk early while preserving API compatibility.

4. **Fix frontend data-flow reliability**
   - Move stale page-level fetch/poll logic into query hooks and canonical invalidation.
   - Remove silent catches and ambiguous UI states.
   - Reason: depends on stable backend contracts from steps 2-3.

5. **Repair test architecture**
   - Replace fixed sleeps with Playwright web-first assertions, fix fixtures/imports, tighten unit test setup, add targeted route/component tests.
   - Reason: test fixes are more durable after runtime seams are stabilized.

6. **Execute safe cleanup and deduplication**
   - Remove high-confidence dead code, stale artifacts, duplicate low-risk setup.
   - One category at a time, each behind passing targeted verification.
   - Reason: cleanup is safest when behavior contracts are already covered.

7. **Final verification and rollback notes**
   - Run targeted + full suites feasible for the repo, build/lint, and document what changed versus what was deferred.
   - Reason: a stabilization milestone is incomplete without explicit proof.

## Rollback and Release Safety

- Prefer **contract-preserving internal changes** over endpoint/schema changes.
- If a cleanup touches route shape, keep a temporary compatibility shim for the milestone unless the old path is proven dead.
- Land hot-path performance fixes separately from dead-code deletions when possible.
- Keep task/status-store changes behind a narrow adapter so reverting does not require undoing unrelated router changes.
- Treat secret-like files and generated artifacts as a separate cleanup stream with explicit approval/evidence.

## Operational Touchpoints

| Touchpoint | Why It Matters in v1.1 | Failure Mode if Ignored |
|-----------|-------------------------|--------------------------|
| Health/readiness endpoints | Catch deployment-time config drift and dependency failure | app starts but core subsystems are broken |
| Auth dependencies on routers | Backend is the real trust boundary | frontend-only protection leaves sensitive routes exposed |
| File storage + served PDFs | Cleanup and auth changes can break downloads or leak files | inaccessible notes or unintended public access |
| Firestore query patterns | Full scans cause latency and hanging behavior | slow explorer/KG endpoints, expensive reads |
| Background task status persistence | In-memory stores break on restart/multi-process | stuck polling, lost job state |
| Test fixtures and ports | E2E drift creates false negatives and retry culture | flaky CI, low trust in verification |

## Scalability Considerations

| Concern | At 100 users | At 10K users | At 1M users |
|---------|--------------|--------------|-------------|
| Firestore query efficiency | Current paths mostly tolerable | full scans become visible latency/cost issue | unacceptable without indexed lookups and bounded pagination |
| Background status tracking | in-memory stores may pass locally | restart/multi-instance failures become common | must be durable/shared |
| Test execution speed | manual triage possible | flaky suites block delivery | CI economics demand deterministic, sharded, contract-focused tests |
| Cleanup discipline | ad hoc deletions recoverable | hidden consumers cause recurring regressions | requires inventory, ownership, and automated policy checks |

## Where Reliability Milestones Usually Go Wrong

1. **Too much refactor bundled with bug fixes**
   - Result: no clean rollback path.
2. **Verification added last instead of first**
   - Result: cleanup decisions are made without evidence.
3. **Cross-cutting issues fixed locally instead of centrally**
   - Result: duplicate retry/error/auth behavior survives.
4. **Performance fixes ignore data contracts**
   - Result: faster code but different semantics.
5. **Dead-code deletion assumes no hidden consumers**
   - Result: broken ops scripts, fixtures, or manual admin flows.
6. **Flaky E2E tests patched with sleeps/retries**
   - Result: slow CI and unresolved product timing bugs.

## Sources

- HIGH — FastAPI bigger applications / `APIRouter` / router-level dependencies: https://fastapi.tiangolo.com/tutorial/bigger-applications/
- HIGH — FastAPI dependency injection and dependency behavior: https://github.com/fastapi/fastapi/blob/master/docs/en/docs/reference/dependencies.md
- HIGH — FastAPI lifespan recommendation: https://github.com/fastapi/fastapi/blob/master/docs/en/docs/release-notes.md
- HIGH — TanStack Query v5 quick start and invalidation/testing guidance: https://github.com/tanstack/query/blob/v5.90.3/docs/framework/react/quick-start.md
- HIGH — TanStack Query testing guidance (`retry: false` in tests): https://github.com/tanstack/query/blob/v5.90.3/docs/framework/react/guides/testing.md
- HIGH — Playwright best practices: isolation, locators, web-first assertions, CI guidance: https://playwright.dev/docs/best-practices
- HIGH — Current repo architecture and concern audit: `.planning/codebase/ARCHITECTURE.md`, `.planning/codebase/CONCERNS.md`, `.planning/codebase/TESTING.md`, `.planning/PROJECT.md`
