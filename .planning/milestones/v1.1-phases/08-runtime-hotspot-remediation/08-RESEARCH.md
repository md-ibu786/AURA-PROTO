# Phase 8: Runtime Hotspot Remediation - Research

**Researched:** 2026-04-06
**Domain:** Firestore request-path performance, bounded runtime state, async responsiveness, frontend polling cleanup
**Confidence:** HIGH

## Summary

Phase 8 addresses audited runtime hotspots in the KG request path and the audio pipeline's in-memory status tracking, while confirming that the previously suspected async-blocking and frontend cleanup risks are much narrower than the audit implied.

**Confirmed findings:**
- `api/kg/router.py` has two request-path hotspots caused by collection-group note scans: one in single-document KG status lookup and one in processing queue retrieval.
- `api/audio_processing.py` keeps job state in an unbounded module-level dictionary (`job_status_store = {}`), so completed/error jobs accumulate forever during long-running sessions.
- No meaningful PERF-03 async-blocking hotspot was confirmed in the audited KG flow because Celery already offloads heavy work and the remaining request handlers are thin orchestration paths.
- Frontend polling/upload cleanup was verified as structurally present in `UploadDialog.tsx` and `useKGProcessing.ts`; the phase should lock this in with regression coverage and explicit request-cancellation handling where needed.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| PERF-01 | Audited KG lookup and queue endpoints avoid full note collection scans in request paths | Confirmed two HIGH severity scan paths in `api/kg/router.py` (`/documents/{id}/status`, `/processing-queue`) |
| PERF-02 | Audited long-running job and task-status stores are bounded so they cannot grow unbounded in memory over time | Confirmed unbounded `job_status_store` in `api/audio_processing.py:140` |
| PERF-03 | Known async request hotspots avoid blocking the event loop with audited synchronous external I/O patterns | No meaningful blocking hotspot confirmed; remediation should preserve thin request handlers and avoid scan-based fallback loops |
| PERF-04 | Audited frontend polling and upload flows clean up timers and in-flight requests safely on close, unmount, or navigation | Code inspection verified interval cleanup in `UploadDialog.tsx` and smart queue polling in `useKGProcessing.ts`; add regression tests and explicit abort semantics |
</phase_requirements>

## Current State Analysis

### 1. KG single-document status lookup performs an audited scan (PERF-01)

**File:** `api/kg/router.py`

**Current behavior:**
- `get_document_kg_status()` first tries a `collection_group('notes')` lookup using a `__name__` prefix range.
- If that fails, it falls back to `list(db.collection_group('notes').stream())` and filters in Python by `doc.id`.

**Impact:**
- Worst-case request cost becomes O(n) across all note documents.
- The fallback loop is synchronous Firestore I/O plus Python iteration inside an async request handler.
- This directly violates PERF-01 and weakens PERF-03 by extending request-thread occupancy.

**Research conclusion:**
- Replace the fallback with indexed or direct-path lookup only.
- Acceptable strategies in this codebase:
  1. Query `collection_group('notes')` by stored `id` field with `limit(1)`.
  2. If a module ID is known, resolve the module once and perform direct `module_ref.collection('notes').document(document_id)` lookup.
- Do **not** retain a stream-all-notes fallback.

### 2. KG processing queue scans every note document (PERF-01)

**File:** `api/kg/router.py`

**Current behavior:**
- `get_processing_queue()` streams all note documents via `db.collection_group('notes').stream()`.
- It then filters for `kg_status == 'processing'` in Python.

**Impact:**
- Queue fetch cost grows with total note count, not with active queue size.
- The frontend's queue polling calls this endpoint repeatedly, so the hotspot compounds over time.

**Research conclusion:**
- Replace Python-side filtering with a server-side `kg_status == 'processing'` collection-group query.
- If Firestore returns an index error, surface a clear operational failure instead of reintroducing a scan fallback.

### 3. KG task helper still relies on broad note lookup logic (PERF-01)

**File:** `api/tasks/document_processing_tasks.py`

**Current behavior:**
- `_find_note_by_id()` uses a scoped direct note lookup when `module_id` is known.
- When `module_id` is absent, it performs a collection-group query by the stored `id` field.

**Impact:**
- This is materially better than a full scan and should remain the canonical bounded fallback.
- Phase 8 should align router lookup behavior with this approach to remove divergence.

**Research conclusion:**
- Centralize or standardize note lookup behavior so router and task code use the same bounded strategy.

### 4. Audio job status tracking is unbounded (PERF-02)

**File:** `api/audio_processing.py`

**Current behavior:**
- `job_status_store = {}` lives for the life of the process.
- Every pipeline run writes multiple intermediate states and the final result into the same store.
- No TTL, max-entry limit, or terminal-state eviction exists.

**Impact:**
- Long-running server sessions accumulate completed and failed jobs indefinitely.
- This creates a process-memory growth path unrelated to active work.

**Research conclusion:**
- Add bounded retention to `job_status_store`.
- Recommended constraints for this brownfield phase:
  - prune terminal jobs older than a configured TTL,
  - cap retained entries with oldest-terminal-first eviction,
  - run cleanup on write and status-read paths.

### 5. Async request-blocking concern was not confirmed as a separate hotspot (PERF-03)

**Files reviewed:** `api/kg/router.py`, `api/tasks/document_processing_tasks.py`

**Current behavior:**
- Heavy KG work is already dispatched to Celery.
- Request handlers mostly validate input, read Firestore state, and enqueue tasks.

**Impact:**
- The real risk is not long CPU-bound work in the request thread; it is unbounded Firestore scan behavior.

**Research conclusion:**
- PERF-03 should be satisfied by preserving thin request handlers and removing scan-based fallback loops.
- No new queueing system or async rewrite is recommended.

### 6. Frontend polling cleanup is structurally present but should be locked down (PERF-04)

**Files reviewed:**
- `frontend/src/components/explorer/UploadDialog.tsx`
- `frontend/src/features/kg/hooks/useKGProcessing.ts`
- `frontend/src/stores/useExplorerStore.ts`

**Current behavior:**
- `UploadDialog.tsx` clears its polling interval on completion, on error, on close, and on unmount.
- `useKGProcessing.ts` uses React Query `refetchInterval` only while queue items remain in `processing` state.
- `useExplorerStore.ts` tracks `kgPolling` state but does not itself create timers.

**Impact:**
- Timer cleanup is already present.
- The remaining phase value is regression coverage and explicit abort behavior for in-flight fetches when dialog lifecycle ends.

**Research conclusion:**
- PERF-04 does not require a broad frontend rewrite.
- Add tests around close/unmount cleanup and, if needed, wire `AbortController` into upload/status polling fetches to ensure requests are canceled instead of merely ignored.

## Standard Stack

### Core (Already in Use)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | 0.115.0 | Async API routing | Existing backend request surface |
| Firebase Admin / google-cloud-firestore | project standard | Firestore reads/writes | Existing system of record |
| Celery + Redis | project standard | Background KG processing | Heavy work already offloaded |
| Pytest | 8.x | Backend regression coverage | Existing backend test stack |
| Vitest + React Testing Library | project standard | Frontend cleanup regression tests | Existing frontend test stack |

### Recommendation

**No new dependencies recommended.**

Phase 8 is a targeted remediation phase. The codebase already has the right building blocks; it needs bounded query and retention behavior, not new infrastructure.

## Architecture Patterns

### Pattern 1: Bounded Firestore note lookup

**Use when:** resolving a note document in request or task paths.

**Preferred order:**
1. Scoped direct path lookup when `module_id` is known.
2. Collection-group equality query on the stored `id` field with `limit(1)` when only `document_id` is known.
3. No stream-all-notes fallback.

### Pattern 2: Server-side queue filtering

**Use when:** listing active KG queue items.

**Implementation rule:**
- Query only `kg_status == 'processing'` at Firestore level.
- Never stream all notes and filter in Python for a polled endpoint.

### Pattern 3: Bounded in-memory status retention

**Use when:** tracking long-running audio jobs.

**Implementation rule:**
- Separate active jobs from evictable terminal jobs conceptually.
- Cleanup runs before writes and reads.
- Evict terminal jobs by age first, then by oldest-completed order when exceeding cap.

### Pattern 4: Cleanup verified by tests, not just inspection

**Use when:** UI logic relies on timers, polling, or in-flight fetches.

**Implementation rule:**
- Keep current timer cleanup behavior.
- Add regression tests for dialog close/unmount and queue idle transitions.
- Use explicit abort semantics where a request could outlive its owner component.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Background processing in request thread | New ad hoc async worker logic | Existing Celery task dispatch | Heavy work is already offloaded |
| Queue filtering in Python | `stream()` all notes then `if kg_status` | Firestore query on `kg_status` | Keeps polled endpoint bounded |
| Infinite runtime caches | Raw module dict with no cleanup | TTL + max-entry bounded store logic | Meets PERF-02 without new infra |
| Frontend lifecycle assumptions | "Looks cleaned up" by inspection | Vitest regression tests + AbortController | Prevents silent cleanup regressions |

## Common Pitfalls

### Pitfall 1: Replacing one scan with another disguised scan

**What goes wrong:** code removes `stream()` fallback from one endpoint but keeps Python-side filtering elsewhere.

**How to avoid:** grep for `collection_group("notes").stream()` and require every remaining use to be justified outside active request paths.

### Pitfall 2: Evicting active jobs from the status store

**What goes wrong:** retention logic removes pending/processing jobs under memory pressure.

**How to avoid:** only terminal states (`complete`, `error`) are eligible for TTL or age eviction.

### Pitfall 3: Declaring frontend cleanup “done” without request cancellation

**What goes wrong:** interval cleanup exists, but in-flight fetches still resolve after the dialog closes.

**How to avoid:** add tests for close/unmount and ignore/cancel `AbortError` intentionally.

## Recommendation

Create two execution plans:

1. **Plan 01 — KG lookup and queue remediation**
   - Remove request-path full scans from `api/kg/router.py`
   - Align task lookup behavior in `api/tasks/document_processing_tasks.py`
   - Add backend regression tests proving no scan fallback remains

2. **Plan 02 — Bounded audio job state + frontend cleanup regression coverage**
   - Bound `job_status_store` retention in `api/audio_processing.py`
   - Add backend tests for eviction/TTL behavior
   - Add frontend cleanup tests and explicit abort handling where needed

No separate execute plan is recommended for PERF-03 because research did not confirm a distinct blocking hotspot beyond the scan behavior addressed in Plan 01.
