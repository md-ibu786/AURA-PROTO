# Roadmap: AURA-NOTES-MANAGER

**Last updated:** 2026-04-07 after v1.1 milestone completion

---

## Milestones

- ✅ **v1.0 Authentication System** — Phases 1-5 (shipped 2026-03-08)
- ✅ **v1.1 Codebase Reliability and Hygiene** — Phases 6-9 (shipped 2026-04-06)
- 📋 **v1.2** — Planned

---

## Phases

<details>
<summary>✅ v1.1 Codebase Reliability and Hygiene (Phases 6-9) — SHIPPED 2026-04-06</summary>

- [x] Phase 6: Verification Recovery (5/5 plans) — completed 2026-04-06
- [x] Phase 7: Failure Hardening & Shared Seams (3/3 plans) — completed 2026-04-06
- [x] Phase 8: Runtime Hotspot Remediation (2/2 plans) — completed 2026-04-06
- [x] Phase 9: Safe Cleanup & Repo Hygiene (3/3 plans) — completed 2026-04-06

</details>

### 📋 v1.2 (Planned)

- [x] Phase 10: Chunk Labeling for Document-to-KG Pipeline (completed 2026-04-23)
- [ ] Phase 11: [To be defined]

---

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-5 | v1.0 | Complete | ✓ Complete | 2026-03-08 |
| 6. Verification Recovery | v1.1 | 5/5 | ✓ Complete | 2026-04-06 |
| 7. Failure Hardening | v1.1 | 3/3 | ✓ Complete | 2026-04-06 |
| 8. Runtime Hotspots | v1.1 | 2/2 | ✓ Complete | 2026-04-06 |
| 9. Safe Cleanup | v1.1 | 3/3 | ✓ Complete | 2026-04-06 |
| 10. Chunk Labeling | v1.2 | 3/3 | Complete    | 2026-04-23 |

### Phase 10: Chunk Labeling for Document-to-KG Pipeline

**Goal:** Add AI-generated topic labels to every document chunk in the Neo4j knowledge graph so chunks carry 1–3 concise semantic labels; expose labels through frontend TypeScript types; and track labeling as a distinct Celery processing stage.
**Requirements**: CHK-01, CHK-02, CHK-03, CHK-04, CHK-05, CHK-06, CHK-07
**Depends on:** Phase 9
**Plans:** 3/3 plans complete

Plans:
- [x] 10-01-PLAN.md — Chunk Labeling Backend Core (dataclass, LLM generation, Neo4j schema, pipeline integration)
- [x] 10-02-PLAN.md — Chunk Labeling Unit Tests (mocks, fallback coverage, JSON extraction)
- [x] 10-03-PLAN.md — Frontend Types and Processing Stage (TypeScript types, Celery LABELING state)

---

**Milestones:** v1.0 (Auth), v1.1 (Reliability), v1.2 (Next)

For archived milestone details, see `.planning/milestones/`.
