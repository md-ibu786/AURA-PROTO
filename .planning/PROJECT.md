# AURA-NOTES-MANAGER

**Status:** v1.1 Complete (2026-04-06)
**Last updated:** 2026-04-06 after phase 09 completion

---

## What This Is

AURA-NOTES-MANAGER is a full-stack departmental note and hierarchy management system with role-based access, document/audio processing, and knowledge graph workflows. It serves admins, staff, and students through an explorer-style UI, backend APIs, and supporting admin/settings/usage tools.

---

## Core Value

**Reliable, role-aware management of departmental learning content and processing workflows.**

The system must let the right users browse, manage, process, and validate departmental content without unsafe access, flaky behavior, or opaque failures.

---

## Current Milestone: v1.1 Codebase Reliability and Hygiene

**Goal:** Eliminate the audited runtime, test, performance, dead-code, duplication, and repo-cleanup issues with a safe-first cleanup strategy.

**Target features:**
- Fix broken and flaky tests, invalid assertions, and mismatched fixtures
- Remove hanging and performance risks in backend and frontend hot paths
- Replace silent failure patterns and tighten observability and error handling
- Remove high-confidence dead code and stale artifacts
- Clean up duplicate or drift-prone setup where the fix is low risk

---

## Requirements

### Validated

- ✓ Users can authenticate and access role-appropriate application routes and APIs — v1.0
- ✓ Users can browse and manage hierarchical department, semester, subject, module, and note data — pre-v1.1 existing product behavior
- ✓ Staff can upload and process documents or audio through backend processing flows — pre-v1.1 existing product behavior
- ✓ Users can view knowledge graph processing state and batch operations in the explorer flow — pre-v1.1 existing product behavior
- ✓ Admins can access user, settings, and usage-management surfaces — pre-v1.1 existing product behavior

### Active

- [ ] Known runtime hanging, blocking, and full-scan hotspots are removed or bounded
- [ ] Frontend, backend, and E2E tests reflect current behavior and run deterministically
- [ ] Silent failure paths are replaced with explicit handling and observability

### Validated in Phase 08

- ✓ KG note lookup paths use bounded Firestore queries instead of full-collection scans
- ✓ Job status store has TTL-based eviction and max-entry bounds
- ✓ Frontend polling cleanup verified with regression tests

### Validated in Phase 09

- ✓ Committed credential files removed from repository tracking
- ✓ Gitleaks CI guardrail added to prevent future secret leaks
- ✓ Human credential rotation checkpoint completed
- ✓ Generated coverage and test report artifacts purged
- ✓ Deprecated root E2E implementation removed (tombstone retained)
- ✓ Explicit .gitignore patterns for cleaned artifact classes
- ✓ Operator docs refreshed to reflect cleaned canonical workflows
- ✓ Planning codebase maps updated to remove stale references

### Out of Scope

- New end-user product features unrelated to the audit findings — this milestone is stabilization and cleanup
- Broad architectural rewrites without direct linkage to audited issues — safe-first delivery takes priority
- Deleting uncertain runtime artifacts with weak evidence — defer until usage is confirmed

---

## Context

### Current State

- Frontend: React 18, TypeScript, Vite, Zustand, TanStack Query, Playwright, Vitest
- Backend: FastAPI with Firebase/Firestore, Neo4j, Redis-adjacent caching, and AI processing integrations
- Existing product areas include explorer navigation, user/admin management, settings, usage reporting, document/audio processing, and KG operations
- The current planning docs were stale and still framed the project primarily as an authentication milestone, so this milestone resets planning artifacts around the actual codebase

### Audit Context Driving v1.1

- Runtime hotspots were found in async request paths, KG note lookup scans, and unbounded in-memory task stores
- E2E suites contain broken fixture imports, tautological assertions, and heavy fixed-time waits
- Several dead-code, orphaned-file, duplicate-config, and duplicate-helper candidates were identified
- Repo hygiene issues include duplicate test stacks, stale generated artifacts, and a secret-like legacy credential file

---

## Constraints

- **Tech stack**: Must stay within the current FastAPI + React/Vite architecture — avoid unnecessary platform changes
- **Safety**: Prefer safe removals and low-risk cleanup over broad rewrites — user explicitly chose safe-first cleanup
- **Behavior preservation**: Existing shipped capabilities must keep working while reliability improves — cleanup cannot regress core flows
- **Verification**: Changes should be backed by targeted tests, lint/build checks, or equivalent validation where feasible

---

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Scope v1.1 around all audited issue buckets | User wants the milestone to address the full audit, not a subset | — Pending |
| Use safe-first cleanup rather than aggressive deletion | Reduces risk in a brownfield codebase with stale planning docs and possible hidden consumers | — Pending |
| Continue milestone numbering to v1.1 | Follows shipped v1.0 milestone and reflects an incremental stabilization release | — Pending |

---

## Evolution

This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? -> Move to Out of Scope with reason
2. Requirements validated? -> Move to Validated with phase reference
3. New requirements emerged? -> Add to Active
4. Decisions to log? -> Add to Key Decisions
5. "What This Is" still accurate? -> Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check - still the right priority?
3. Audit Out of Scope - reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-04-06 after milestone v1.1 start*
