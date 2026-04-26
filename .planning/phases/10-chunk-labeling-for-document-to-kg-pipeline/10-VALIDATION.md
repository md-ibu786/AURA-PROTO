---
phase: 10
slug: chunk-labeling-for-document-to-kg-pipeline
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-23
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x + vitest |
| **Config file** | `conftest.py` (root) / `vitest.config.ts` (frontend) |
| **Quick run command** | `pytest api/test_kg_processor.py -v` / `npm test -- src/features/kg` |
| **Full suite command** | `pytest` / `npm test` |
| **Estimated runtime** | ~45 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest api/test_kg_processor.py -v`
- **After every plan wave:** Run `pytest` / `npm test`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | TBD | T-10-01 / — | Input validation on chunk content | unit | `pytest api/test_chunk_labeler.py -v` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `api/test_chunk_labeler.py` — stubs for chunk labeling module
- [ ] `api/test_kg_processor_labeling.py` — integration tests for labeling in pipeline
- [ ] `frontend/src/features/kg/components/ChunkLabelBadge.test.tsx` — component stubs

*Wave 0 installs test infrastructure before implementation begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Label accuracy on real documents | TBD | Requires human judgment on semantic quality | Process 5 sample PDFs, verify labels match content |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
