# Phase 10: Chunk Labeling for Document-to-KG Pipeline - Research

**Researched:** 2026-04-23
**Domain:** Knowledge Graph chunk enrichment / semantic chunk classification
**Confidence:** MEDIUM-HIGH

## Summary

Phase 10 introduces **semantic chunk labeling** to the existing Document-to-Knowledge-Graph pipeline. Currently, the pipeline creates `Chunk` and `ParentChunk` nodes in Neo4j with structural metadata (text, token_count, position, embedding) but **no semantic classification of chunk content**. "Chunk labeling" assigns content-type tags (e.g., `definition`, `theorem`, `example`, `introduction`, `methodology`, `finding`) to each chunk, enabling:

1. **Filtered retrieval in RAG** — query only `definition` or `example` chunks
2. **Type-aware entity extraction** — apply different extraction prompts per chunk label
3. **Graph navigation by content type** — browse chunks by semantic category in the explorer
4. **Better chunk merging/restructuring** — group chunks by label for hierarchical summarization

The existing pipeline (`kg_processor.py`, `entity_aware_chunker.py`, Celery tasks, Neo4j schema) is mature but has **no label concept anywhere** — this is a greenfield addition to the data model, processing flow, and API surface.

**Primary recommendation:** Implement a **hybrid labeling strategy** — use structural heuristics (Markdown headers, keyword patterns) for a fast first pass, then use a lightweight LLM call (batch-classify multiple chunks at once) to confirm/refine labels. Store labels as a `chunk_labels` array property on Neo4j `Chunk` nodes and expose label counts/filtering via the existing KG API.

---

## User Constraints (from CONTEXT.md)

> No CONTEXT.md exists for Phase 10. Phase was added to roadmap as a placeholder with no locked decisions. Full discretion applies to approach, scope, and technology choices, subject to project conventions in AGENTS.md.

### AGENTS.md Directives (MUST COMPLY)

| Directive | Impact on Phase 10 |
|-----------|-------------------|
| **File headers mandatory** on all `.py` and `.ts/.tsx` files | All new/modified files must include the standard header block |
| **Python line length: 80 chars max** | All backend code must respect this limit |
| **TypeScript: named exports only, no `default` exports** | Frontend components/hooks must use `export { Foo }` |
| **TypeScript: no `any` type, no type assertions without justification** | Chunk label types must be strongly typed |
| **Error handling: never empty catch blocks, never bare `except:`** | Labeling failures must be logged and gracefully degraded |
| **Tests before or with code** | Unit tests for label classifier, integration tests for pipeline step |
| **Frontend state: Zustand for UI/auth, TanStack Query for server state** | Label data flows through React Query, not Zustand |
| **Python: use root venv, NEVER install globally** | All package installs via `pip install -r requirements.txt` in `.venv` |
| **Research first — verify library behavior** | Any new NLP/classification library must be verified before use |

---

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `google-generativeai` / Vertex AI | (existing) | LLM-based chunk classification | Project already uses Gemini for entity extraction and embeddings [VERIFIED: kg_processor.py] |
| `tiktoken` | (existing) | Token counting for chunk boundaries | Already used in `kg_processor.py` [VERIFIED: codebase] |
| `pydantic` | (existing) | Request/response validation | Used throughout FastAPI layer [VERIFIED: api/modules/models.py] |
| `neo4j` | (existing) | Graph storage with label properties | Existing driver in `neo4j_config.py` [VERIFIED: codebase] |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `pytest-asyncio` | (existing) | Async test support for pipeline tests | For testing `async` labeling methods |
| `unittest.mock` | stdlib | Mock LLM responses in tests | Always for unit tests to avoid API calls |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| LLM batch classification | spaCy/heuristic rules only | Faster but far less accurate for academic documents; LLM is justified given existing infrastructure |
| Adding Neo4j node labels (`:DefinitionChunk`) | Property array `chunk_labels` | Node labels require schema migration and complicate queries; property array is flexible and backward-compatible [CITED: Neo4j Cypher Manual - SET properties] |
| Per-chunk LLM call | Batch classification (1 call per ~5 chunks) | 5x cost reduction with minimal accuracy loss [CITED: MDKeyChunker arxiv 2026] |

**Installation:** No new packages required — all capabilities exist in current stack.

---

## Architecture Patterns

### Recommended Project Structure

```
api/
├── kg_processor.py              # Add labeling step to process_document()
├── services/
│   ├── chunk_labeler.py         # NEW: ChunkLabeler class (hybrid heuristic + LLM)
│   └── entity_aware_chunker.py  # MINOR: pass section hints to labeler
├── schemas/
│   └── neo4j_schema.py          # MINOR: add 'chunk_labels' to CHUNK properties
├── tasks/
│   └── document_processing_tasks.py  # MINOR: add 'labeling' progress stage
└── kg/
    └── router.py                # MINOR: add label_count to status response
frontend/src/
├── features/kg/
│   ├── types/kg.types.ts        # MINOR: add label fields to KGStatusResponse
│   └── components/              # MINOR: display label chips in ProcessDialog
└── api/explorerApi.ts           # MINOR: add label-aware query params
```

### Pattern 1: Hybrid Chunk Labeling
**What:** First pass uses structural heuristics (Markdown headers, numbered lists, bold terms), second pass uses a single LLM call classifying up to 5 chunks at once.
**When to use:** Default for all documents. Heuristics alone are insufficient for academic text; pure LLM is too expensive.
**Example:**
```python
# Source: Derived from MDKeyChunker pattern [CITED: arxiv 2603.23533]
class ChunkLabeler:
    """Hybrid chunk labeler with heuristic + LLM confirmation."""

    # Fast heuristic labels based on section headers / keywords
    HEURISTIC_PATTERNS = {
        'definition': [r'\bdefin(?:ition|e)\b', r'\bis defined as\b'],
        'theorem': [r'\btheorem\b', r'\bproof\b'],
        'example': [r'\bexample\b', r'\be\.g\.\b'],
        'introduction': [r'^(intro|overview|background)', r'\bin this (paper|section)\b'],
        'methodology': [r'\bmethod(?:ology)?\b', r'\bapproach\b', r'\bprocedure\b'],
        'finding': [r'\bresult\b', r'\bfinding\b', r'\bconclusion\b'],
    }

    async def label_chunks(
        self, chunks: List[Chunk]
    ) -> List[Tuple[Chunk, List[str]]]:
        # Pass 1: heuristics
        heuristic_labels = [self._heuristic_label(c) for c in chunks]
        # Pass 2: LLM batch confirmation (only for ambiguous chunks)
        return await self._llm_confirm_labels(chunks, heuristic_labels)
```

### Pattern 2: Label Storage as Property Array
**What:** Store labels on Neo4j `Chunk` nodes as `chunk_labels: ['definition', 'example']` (List of String).
**When to use:** All chunk nodes. Arrays are indexable in Neo4j 5.x and backward-compatible with existing queries.
**Why not node labels:** Neo4j node labels (`:Chunk:Definition`) are structural and cannot be parameterized in MERGE without dynamic Cypher, which the project avoids for security. Property arrays are query-friendly:
```cypher
MATCH (c:Chunk {module_id: $module_id})
WHERE 'definition' IN c.chunk_labels
RETURN c
```

### Anti-Patterns to Avoid
- **Anti-pattern: Storing labels in Firestore instead of Neo4j** — Labels are graph-native metadata; duplicating them in Firestore creates a sync hazard.
- **Anti-pattern: One LLM call per chunk** — At 800 tokens per chunk and current pricing, this 5x-10x's processing cost with minimal accuracy gain vs. batching.
- **Anti-pattern: Hard-coded enum for all possible labels** — Academic documents vary wildly; use a controlled vocabulary (configurable list) but allow the LLM to suggest new labels with a confidence threshold.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM prompt formatting for classification | Custom prompt templating | Existing `GeminiClient.generate_text()` in `kg_processor.py` | Already has retry, model resolution from SettingsStore, and error handling [VERIFIED: kg_processor.py] |
| Neo4j schema migration management | Ad-hoc `session.run()` patches | Existing `api/schemas/neo4j_schema.py` + migration scripts in `api/migrations/` | Project already has schema alignment migrations [VERIFIED: api/migrations/003_schema_alignment.py] |
| Batch progress tracking | Custom pub/sub | Existing Celery task progress in `document_processing_tasks.py` | `update_document_status()` already handles step/progress [VERIFIED: document_processing_tasks.py] |
| Embedding for label similarity | Custom vector math | Existing `EmbeddingService.embed_batch()` | Already generates 768-dim vectors with retry logic [VERIFIED: kg_processor.py] |

**Key insight:** The pipeline is already instrumented for adding a new processing stage. The hard parts (async orchestration, retry, progress tracking, Neo4j storage) are solved. The phase is primarily about the *classification logic* and *schema extension*, not infrastructure.

---

## Runtime State Inventory

> This phase is a **greenfield feature addition** — no renames, no migrations of existing data, no string replacements. The only runtime consideration is Neo4j schema state.

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | Neo4j `Chunk` nodes exist with no `chunk_labels` property | **Schema addition only** — existing chunks remain valid (property will be null/empty). No data migration required because labels are additive metadata. |
| Live service config | None | None |
| OS-registered state | None | None |
| Secrets/env vars | None | None |
| Build artifacts | None | None |

**Backward compatibility:** Existing `Chunk` nodes without `chunk_labels` are fully valid. Queries using `WHERE 'definition' IN c.chunk_labels` will simply not match them. The frontend should treat missing `chunk_labels` as `[]`.

---

## Common Pitfalls

### Pitfall 1: LLM Classification Drift
**What goes wrong:** Different LLM models (Vertex AI vs. OpenRouter vs. Ollama) produce inconsistent label names — `definition` vs `Definition` vs `defn`.
**Why it happens:** No normalization of LLM output; the project already supports multiple model providers via `model_router.py`.
**How to avoid:** Normalize all labels to lowercase snake_case (`definition`, `methodology`). Reject labels not in the controlled vocabulary unless `auto_expand_vocabulary` is enabled. Store the vocabulary in `api/config.py` or a new `chunk_label_config.py`.
**Warning signs:** Integration tests pass with Vertex AI but fail with Ollama because label strings differ.

### Pitfall 2: Labeling Becomes the Bottleneck
**What goes wrong:** Batch LLM classification adds 2-5 seconds per document, making KG processing feel slow.
**Why it happens:** Synchronous LLM calls in the chunking stage block the entire pipeline.
**How to avoid:** Run labeling **after** chunk storage in Neo4j, as a background enrichment step. The Celery task can mark chunks as `labeled: false` and a subsequent task (or the same task after a yield) fills in labels. Alternatively, batch-classify all chunks of a document in a single LLM call (up to the model's context window).
**Warning signs:** `kg_processed_at` timestamps increase by >30% after deploying labeling.

### Pitfall 3: Front-End Type Mismatches
**What goes wrong:** Backend returns `chunk_labels` as `List[str]`, but frontend TypeScript interface declares it as `string | undefined`.
**Why it happens:** Rapid backend/frontend iteration without updating shared types.
**How to avoid:** Update `frontend/src/features/kg/types/kg.types.ts` **before** modifying the API. Add a Zod or runtime validation if desired (project currently uses Pydantic on backend only).
**Warning signs:** TypeScript build errors in `frontend/` after backend deployment.

### Pitfall 4: Heuristic Rules Over-Fit to English
**What goes wrong:** Heuristic patterns (`\btheorem\b`, `\bproof\b`) fail for documents in other languages or domains (e.g., medical, legal).
**Why it happens:** The project is currently English-focused (computer science academic notes), but the KG pipeline may eventually process other domains.
**How to avoid:** Make heuristic patterns configurable per `module_id` or document type, and ensure the LLM fallback always runs so no chunk is left unlabeled due to regex mismatch.

---

## Code Examples

### Adding chunk_labels to Neo4j schema
```python
# Source: api/schemas/neo4j_schema.py pattern
NodeType.CHUNK: [
    "id",
    "document_id",
    "module_id",
    "parent_chunk_id",
    "text",
    "tokens",
    "position",
    "embedding",
    "chunk_labels",        # NEW: List[str] of semantic labels
    "label_confidence",    # NEW: Float (min confidence across labels)
    "created_at",
]
```

### Updating chunk nodes with labels
```python
# Source: Neo4j Cypher Manual [CITED: neo4j.com/docs/cypher-manual/current/clauses/set/]
query = """
MATCH (c:Chunk {id: $chunk_id, module_id: $module_id})
SET c.chunk_labels = $labels,
    c.label_confidence = $confidence
RETURN c.id
"""
session.run(query, {
    "chunk_id": chunk.id,
    "module_id": module_id,
    "labels": ["definition", "example"],
    "confidence": 0.85,
})
```

### Batch LLM classification prompt
```python
# Source: Adapted from MDKeyChunker single-call enrichment pattern [CITED: arxiv 2603.23533]
CHUNK_LABEL_PROMPT = """
You are a document structure analyst. For each text chunk below,
assign 1-3 semantic labels from this vocabulary:
[introduction, definition, theorem, proof, example, exercise,
 methodology, finding, conclusion, citation, figure, table, other].

Return ONLY a JSON array. Do not add markdown formatting.
[
  {"chunk_index": 0, "labels": ["definition"], "confidence": 0.95},
  {"chunk_index": 1, "labels": ["example", "theorem"], "confidence": 0.88}
]

Chunks:
{chunks_json}
"""
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Fixed-size chunking with no metadata | Semantic chunking + metadata enrichment (MDKeyChunker, GraphRAG) | 2024-2026 | Chunks now carry structured metadata (title, summary, labels, keys) for filtered retrieval |
| Per-chunk LLM calls | Single-call batch enrichment with rolling context | 2026 (arxiv) | ~5x cost reduction, better consistency via rolling dictionaries |
| Node labels for chunk types (`:DefinitionChunk`) | Property arrays (`chunk_labels: ['definition']`) | 2024-2025 | Property graphs favor flexible properties over rigid node labels for multi-valued classification |

**Deprecated/outdated:**
- **Manual rule-based chunking without LLM fallback:** Modern pipelines use LLM as a fallback or confirmation layer because academic document structures are too varied for regex alone.
- **Storing chunk metadata only in vector DB:** Projects now store chunk metadata directly in the graph (Neo4j) alongside entities, not in a separate vector store.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | "Chunk labeling" means assigning semantic content-type labels (definition, theorem, etc.) to text chunks | Summary | If user intended "labeling" as something else (e.g., GUI labels, manual user tags), the entire research is off-target |
| A2 | The project does NOT require retroactive labeling of existing Neo4j chunks | Runtime State Inventory | If existing chunks must be back-filled, a data migration task and Celery backfill job are needed |
| A3 | Labels should be stored as a property array on Neo4j Chunk nodes, not as separate node labels | Architecture Patterns | If user prefers node labels (`:DefinitionChunk`), schema queries and migrations become significantly more complex |
| A4 | The existing LLM infrastructure (`GeminiClient`, `model_router.py`) is sufficient for classification calls | Standard Stack | If classification requires a different model or fine-tuning, additional model config in Settings page is needed |
| A5 | No new npm/pip packages are needed | Standard Stack | If a specialized NLP library (e.g., `spacy`) is desired, installation and venv management steps must be added |

---

## Open Questions

1. **Should chunk labeling be mandatory or optional per document?**
   - What we know: The pipeline currently has `use_hierarchical_chunking`, `use_llm_extraction` as optional flags.
   - What's unclear: Whether labeling should be always-on or toggled via `options` in `BatchProcessingRequest`.
   - Recommendation: Add `enable_chunk_labeling: bool = True` to `process_document()` with a feature flag defaulting to True. This mirrors existing optional pipeline stages.

2. **Should labels be editable by users after processing?**
   - What we know: The frontend has no chunk-level editing UI today.
   - What's unclear: Whether staff should be able to correct misclassified chunk labels.
   - Recommendation: Defer user-editable labels to a later phase (v1.3+). Phase 10 should focus on automated labeling only.

3. **How should labels affect the existing Graph Visualizer?**
   - What we know: `api/graph_visualizer.py` renders chunk nodes with label `f"Chunk {position}"`.
   - What's unclear: Whether chunk nodes should be color-coded by label in the visualization.
   - Recommendation: Minor visualizer update to show label chips (e.g., `Chunk 3 [definition]`) — low effort, high UX value.

4. **What is the controlled vocabulary for labels?**
   - What we know: Documents are academic lecture notes for computer science/engineering.
   - What's unclear: Exact list of labels (e.g., should `code_snippet` be a label? `diagram_description`?).
   - Recommendation: Start with a conservative vocabulary: `introduction`, `definition`, `theorem`, `proof`, `example`, `exercise`, `methodology`, `finding`, `conclusion`, `citation`, `other`. Allow LLM to suggest new labels with a confidence threshold, but store only those matching the vocabulary.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Python | Backend | ✓ | 3.14.3 | — |
| Node.js | Frontend build/tests | ✓ | 23.3.0 | — |
| npm | Frontend package management | ✓ | 10.9.0 | — |
| Neo4j | KG storage | Unknown | — | Cannot test graph writes without it |
| Redis | Celery broker | Unknown | — | In-memory broker for local dev only |
| pytest | Backend tests | ✗ (not in PATH) | — | Use `.venv\Scripts\pytest` after activating venv |
| vitest | Frontend unit tests | ✓ (via `npm test`) | — | — |
| Vertex AI / Gemini | LLM classification | Unknown (needs API key) | — | `AURA_TEST_MODE=true` mocks responses |

**Missing dependencies with no fallback:**
- Neo4j instance for integration testing — planner must include a mock-driver test path or require local Neo4j.

**Missing dependencies with fallback:**
- pytest not in global PATH — fallback is to activate `.venv` first (per AGENTS.md).

---

## Validation Architecture

> `.planning/config.json` does not explicitly set `workflow.nyquist_validation` to false, so this section is included.

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (backend), Vitest (frontend) |
| Config file | `conftest.py` (backend), `frontend/vitest.config.ts` (frontend) |
| Quick run command | `pytest api/test_kg_processor.py -v` |
| Full suite command | `pytest` (project root with venv) |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CHK-01 | ChunkLabeler assigns at least one label per chunk | unit | `pytest api/services/test_chunk_labeler.py` | ❌ Wave 0 |
| CHK-02 | Labels are stored on Neo4j Chunk nodes | integration | `pytest api/test_kg_processor.py::test_label_storage` | ❌ Wave 0 |
| CHK-03 | Batch LLM classification produces normalized labels | unit | `pytest api/services/test_chunk_labeler.py::test_batch_normalize` | ❌ Wave 0 |
| CHK-04 | Pipeline progress includes "labeling" stage | unit | `pytest api/tasks/test_document_processing_tasks.py` | ❌ Wave 0 |
| CHK-05 | Frontend KG types include `chunk_labels` field | type-check | `cd frontend && npm run build` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** `pytest api/services/test_chunk_labeler.py -x`
- **Per wave merge:** `pytest` (full backend suite)
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] `api/services/test_chunk_labeler.py` — covers CHK-01, CHK-03
- [ ] `api/test_kg_processor.py` — add `test_label_storage` (CHK-02)
- [ ] `api/tasks/test_document_processing_tasks.py` — verify labeling stage in progress (CHK-04)
- [ ] `frontend/src/features/kg/types/kg.types.ts` — extend `KGStatusResponse` with label fields (CHK-05)

---

## Security Domain

> `security_enforcement` is not explicitly disabled in config. This phase touches input validation and LLM output parsing.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V5 Input Validation | **yes** | Labels from LLM must be sanitized (length limits, character whitelist) before Cypher query parameters |
| V6 Cryptography | no | No new crypto |
| V7 Error Handling | **yes** | Labeling failures must not crash the Celery task; must be caught and logged |

### Known Threat Patterns for This Stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| LLM output injection into Cypher | Tampering | Strictly parameterize all Cypher queries; never interpolate labels into query strings. Use `$labels` parameters only. [VERIFIED: existing codebase uses parameterized queries in `kg_processor.py`] |
| Excessive LLM cost from batch sizing | Denial of Service | Cap batch size (max 5 chunks per classification call), enforce max label length (50 chars), max labels per chunk (5) |
| Label enumeration / fuzzing | Information Disclosure | Labels are not sensitive; no mitigation needed beyond standard input validation |

---

## Sources

### Primary (HIGH confidence)
- `api/kg_processor.py` — Full pipeline code, Chunk dataclass, Neo4j storage methods
- `api/schemas/neo4j_schema.py` — Canonical node property definitions
- `api/tasks/document_processing_tasks.py` — Celery task progress tracking
- `api/kg/router.py` — KG API endpoints and response models
- `services/entity_aware_chunker.py` — Existing chunking logic
- `frontend/src/features/kg/types/kg.types.ts` — Frontend type contracts

### Secondary (MEDIUM confidence)
- Neo4j Cypher Manual — SET clause for property arrays [CITED: neo4j.com/docs/cypher-manual/current/clauses/set/]
- MDKeyChunker (arxiv 2603.23533) — Single-call LLM enrichment pattern [CITED: arxiv 2603.23533]
- "Chunking Strategies to Improve LLM RAG Pipeline Performance" (weaviate.io, 2025) — Semantic chunking best practices [CITED: weaviate.io/blog/chunking-strategies-for-rag]
- "Knowledge Graphs Are Back" (tianpan.co, 2026) — GraphRAG pipeline architecture patterns [CITED: tianpan.co/blog/2026-04-13]

### Tertiary (LOW confidence)
- General RAG/KG community patterns from Exa semantic search — used to confirm that property-array labels are preferred over node labels in modern Neo4j property graphs.

---

## Metadata

**Confidence breakdown:**
- Standard stack: **HIGH** — all libraries already in use; no new dependencies needed
- Architecture: **MEDIUM-HIGH** — pattern is well-established, but exact integration points require care given the large `kg_processor.py` file
- Pitfalls: **MEDIUM-HIGH** — based on concrete risks observed in the codebase (multi-provider LLM, async Celery tasks, 80-char line limit)

**Research date:** 2026-04-23
**Valid until:** 2026-05-23 (stable domain; only risk is LLM API pricing changes)
