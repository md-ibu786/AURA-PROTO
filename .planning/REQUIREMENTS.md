# Requirements: AURA-NOTES-MANAGER

**Defined:** 2026-04-07
**Core Value:** Reliable, role-aware management of departmental learning content and processing workflows.

## v1 Requirements

Requirements carried forward from v1.1 milestone.

### Validated (v1.0 + v1.1)

- [x] Users can authenticate and access role-appropriate application routes and APIs — v1.0
- [x] Users can browse and manage hierarchical department, semester, subject, module, and note data — v1.0
- [x] Staff can upload and process documents or audio through backend processing flows — v1.0
- [x] Users can view knowledge graph processing state and batch operations in the explorer flow — v1.0
- [x] Admins can access user, settings, and usage-management surfaces — v1.0
- [x] Verification infrastructure runs deterministically with meaningful assertions — v1.1
- [x] Error handling is explicit with centralized error classes — v1.1
- [x] Runtime hotspots are bounded (Firestore queries, TTL eviction, polling cleanup) — v1.1
- [x] Repo hygiene maintained (no credential leaks, clean artifact handling) — v1.1

## v2 Requirements

Deferred from v1.1 for future milestones.

### Audio-to-Notes Pipeline

- **AUD-01**: Admin can configure the LLM models used for transcript refinement (coc.py) and note summarization (summarizer.py) via the Settings page, consistent with all other LLM service configuration.

### Diagnostics and Auditability

- **OBS-01**: Team can trace audited request and background-task failures with structured correlation data.
- **OBS-02**: Cleanup changes produce a formal evidence trail of what was deleted, deferred, or retained and why.

## Out of Scope

Explicitly excluded from current planning.

| Feature | Reason |
|---------|--------|
| New end-user features unrelated to current priorities | Awaiting scope definition for v1.2 |
| Broad platform migrations or architectural rewrites | Safe-first brownfield delivery takes priority |
| Aggressive deletion with weak evidence | Hidden consumers remain a known brownfield risk |

---

*Requirements defined: 2026-04-07*
*Last updated: 2026-04-19 (added AUD-01 for audio pipeline model config)*
