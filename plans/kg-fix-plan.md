# KG Pipeline Fix Plan

**Generated:** 2026-05-24
**Source:** `reviews/kg-review.md` (23 findings: 3 Critical, 7 High, 8 Medium, 5 Low)
**Scope:** Backend (`api/`) + Frontend (`frontend/src/features/kg/`)

---

## Overview

| Dimension | Detail |
|-----------|--------|
| **Affected files** | `api/kg_processor.py`, `api/graph_manager.py`, `api/kg/router.py`, `api/graph_visualizer.py`, `api/schema_validator.py`, `frontend/src/features/kg/components/ProcessingQueue.tsx`, `frontend/src/features/kg/components/DeleteFromKGDialog.tsx`, `frontend/src/features/kg/hooks/useKGProcessing.ts`, `frontend/src/features/kg/components/FileSelectionBar.tsx` |
| **Total findings** | 23 (3 Critical, 7 High, 8 Medium, 5 Low) |
| **Fix groups** | 10 logical groups |
| **Estimated effort** | 3–4 days (backend-heavy, ~80% backend / ~20% frontend) |
| **Risk profile** | Groups 1–2 are highest risk (Neo4j driver changes, transaction semantics) |

---

## Prerequisites

1. **Neo4j running** — all Neo4j-related fixes require a live instance for validation.
2. **Root venv activated** — `D:\Peter\AURA Twin Proj\AURA-PROJ\.venv\Scripts\activate`
3. **Frontend dev server available** — `cd frontend && npm run dev` (port 5174).
4. **Baseline test run** — record current test pass/fail state before any changes:
   ```bash
   python -m pytest AURA-NOTES-MANAGER/api/tests/ -v --tb=short 2>&1 | tee baseline-backend.txt
   cd AURA-NOTES-MANAGER/frontend && npm test -- --run 2>&1 | tee baseline-frontend.txt
   ```

---

## Fix Groups

### Group 1: Neo4j Event Loop Blocking (C1, C3)

**Rationale:** All `GraphManager` methods and many `kg_processor.py` helpers are declared `async def` but call synchronous `session.run()`, blocking the FastAPI event loop. This is the root infrastructure issue — fixing it unblocks all other async improvements.

**Findings addressed:** C1 (`_update_entity_embedding` blocks), C3 (`GraphManager` + `kg/router.py` block)

#### Change 1.1: Wrap all `GraphManager` sync Neo4j calls in `asyncio.to_thread`

**File:** `api/graph_manager.py`

**Current pattern (repeated in every method):**
```python
async def get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
    try:
        # ...
        with self.driver.session() as session:
            result = session.run(cypher, {"entity_id": entity_id})
            record = result.single()
            # ...
```

**Target pattern:**
```python
async def get_entity_by_id(self, entity_id: str) -> Optional[Entity]:
    try:
        def _sync():
            with self.driver.session() as session:
                result = session.run(cypher, {"entity_id": entity_id})
                record = result.single()
                if record:
                    return Entity(...)
            return None

        return await asyncio.to_thread(_sync)
    except Exception as e:
        logger.warning(f"Failed to get entity by ID {entity_id}: {e}")
        return None
```

**Methods to convert (all in `GraphManager`):**
- `get_entity_by_id` (~line 230)
- `get_entities_by_name` (~line 270)
- `get_entity_neighbors` (~line 340)
- `get_paths_between` (~line 430)
- `get_subgraph` (~line 500)
- `delete_document` (~line 560)
- `cleanup_orphaned_entities` (~line 650)
- `expand_graph_context` (~line 700)

**Add import at top of file:**
```python
import asyncio
```

#### Change 1.2: Wrap `kg_processor.py` sync Neo4j helpers in `asyncio.to_thread`

**File:** `api/kg_processor.py`

All `_create_*` and `_update_*` helper methods that call `session.run()` synchronously need wrapping. The pattern:

**Current:**
```python
async def _create_document_node(self, session, document_id, module_id, user_id, chunks):
    query = "MERGE (d:Document {id: $id}) ..."
    session.run(query, {...})
```

**Target:**
```python
async def _create_document_node(self, session, document_id, module_id, user_id, chunks):
    query = "MERGE (d:Document {id: $id}) ..."
    await asyncio.to_thread(session.run, query, {...})
```

**Methods to convert:**
- `_create_document_node` (~line 3640)
- `_create_chunk_node` (~line 3670)
- `_create_doc_chunk_relationship` (~line 3690)
- `_create_entity_node` (~line 3700)
- `_create_chunk_entity_relationship` (~line 3740)
- `_create_entity_relationship` (~line 3420)
- `_update_entity_embedding` (~line 3555)
- `_store_in_neo4j` (the `session.run` calls within, ~line 3588)

**Note:** `asyncio` is already imported in `kg_processor.py`.

#### Change 1.3: Wrap `delete_batch` loop calls

**File:** `api/kg/router.py`

The `delete_batch` endpoint calls `await graph_manager.delete_document(doc_id)` in a loop. After Change 1.1 makes `delete_document` truly async, this is already fixed. No additional change needed here — just verify.

**Validation:**
```bash
# Run backend tests
python -m pytest AURA-NOTES-MANAGER/api/tests/ -v -k "graph" --tb=short

# Manual: start server, hit multiple endpoints concurrently
# Verify no "BlockingError" or event loop warnings in logs
```

---

### Group 2: Neo4j Transaction Protection (C2, M7)

**Rationale:** `_store_in_neo4j` writes Document → Chunks → Entities in separate `session.run()` calls with no transaction. If the process crashes mid-write, partial data persists. Additionally, only entities attached to chunks are stored — standalone entities from dedup are lost.

**Findings addressed:** C2 (no transaction protection), M7 (standalone entities lost)

#### Change 2.1: Wrap `_store_in_neo4j` in a write transaction

**File:** `api/kg_processor.py`, method `_store_in_neo4j` (~line 3588)

**Current:**
```python
async def _store_in_neo4j(self, document_id, module_id, user_id, chunks, entities):
    if not self.driver:
        raise ValueError("Neo4j driver not available")

    with self.driver.session() as session:
        await self._create_document_node(session, document_id, module_id, user_id, chunks)
        for chunk in chunks:
            await self._create_chunk_node(session, chunk, module_id)
            await self._create_doc_chunk_relationship(session, document_id, chunk.id)
            for entity in chunk.entities:
                await self._create_entity_node(session, entity, module_id)
                relevance_score = entity.properties.get("confidence", 0.7)
                await self._create_chunk_entity_relationship(session, chunk.id, entity.id, relevance_score)
```

**Target:**
```python
async def _store_in_neo4j(self, document_id, module_id, user_id, chunks, all_entities):
    """Store document, chunks, and ALL entities in Neo4j within a transaction."""
    if not self.driver:
        raise ValueError("Neo4j driver not available")

    def _tx_write(tx):
        # Step 1: Document node
        tx.run("""
            MERGE (d:Document {id: $id})
            SET d.module_id = $module_id,
                d.user_id = $user_id,
                d.chunk_count = $chunk_count,
                d.updated_at = $updated_at
        """, {
            "id": document_id,
            "module_id": module_id,
            "user_id": user_id,
            "chunk_count": len(chunks),
            "updated_at": datetime.utcnow().isoformat(),
        })

        # Step 2: Chunks + doc-chunk relationships
        for chunk in chunks:
            tx.run("""
                MERGE (c:Chunk {id: $id})
                SET c.text = $text, c.chunk_labels = $chunk_labels,
                    c.token_count = $token_count, c.index = $index,
                    c.module_id = $module_id, c.embedding = $embedding
            """, { ... })
            tx.run("""
                MATCH (d:Document {id: $doc_id})
                MATCH (c:Chunk {id: $chunk_id})
                MERGE (d)-[r:HAS_CHUNK]->(c)
            """, {"doc_id": document_id, "chunk_id": chunk.id})

        # Step 3: ALL entities (not just chunk.entities) — fixes M7
        for entity in all_entities:
            tx.run(f"""
                MERGE (e:{entity.entity_type.value} {{id: $id}})
                ON CREATE SET e.created_at = $created_at
                SET e.name = $name, e.definition = $definition,
                    e.module_id = $module_id, e.confidence = $confidence,
                    e.embedding = $embedding, e.updated_at = $updated_at
            """, { ... })

        # Step 4: Chunk-entity relationships
        for chunk in chunks:
            for entity in chunk.entities:
                tx.run("""
                    MATCH (c:Chunk {id: $chunk_id})
                    MATCH (e) WHERE e.id = $entity_id
                    MERGE (c)-[r:CONTAINS_ENTITY]->(e)
                    SET r.relevance_score = $relevance_score
                """, {
                    "chunk_id": chunk.id,
                    "entity_id": entity.id,
                    "relevance_score": entity.properties.get("confidence", 0.7),
                })

    def _sync_store():
        with self.driver.session() as session:
            session.execute_write(_tx_write)

    await asyncio.to_thread(_sync_store)
```

**Key changes:**
1. Single `execute_write` transaction — all-or-nothing.
2. Parameter `entities` renamed to `all_entities` — stores ALL extracted entities, not just those attached to chunks.
3. Chunk-entity relationships still come from `chunk.entities` (the linking step).

#### Change 2.2: Update `_store_in_neo4j` call site to pass `all_entities`

**File:** `api/kg_processor.py`, `process_document` method (~line 1550)

**Current:**
```python
await self._store_in_neo4j(document_id, module_id, user_id, chunks, all_entities)
```

This already passes `all_entities` — verify the parameter name matches. If the current call passes `entities` (the chunk-scoped list), change it to `all_entities`.

#### Change 2.3: Add cleanup on error in `process_document`

**File:** `api/kg_processor.py`, `process_document` `except` block (~line 1600)

**Current:**
```python
except Exception as e:
    logger.error(f"Document processing failed for {document_id}: {e}")
    result["status"] = "error"
    result["error"] = str(e)
```

**Target — add partial-write cleanup:**
```python
except Exception as e:
    logger.error(f"Document processing failed for {document_id}: {e}")
    result["status"] = "error"
    result["error"] = str(e)
    # Attempt cleanup of any partially written data
    try:
        graph_manager = GraphManager(self.driver)
        success, _ = await graph_manager.delete_document(document_id)
        if success:
            logger.info(f"Cleaned up partial data for {document_id}")
        else:
            logger.warning(f"Partial data cleanup failed for {document_id}")
    except Exception as cleanup_err:
        logger.warning(f"Cleanup attempt failed for {document_id}: {cleanup_err}")
```

**Validation:**
```bash
python -m pytest AURA-NOTES-MANAGER/api/tests/ -v -k "store or neo4j" --tb=short
# Manual: kill process mid-write, verify no partial data in Neo4j
```

---

### Group 3: Cypher Injection Prevention (H1, H2)

**Rationale:** `_create_entity_relationship` and `_update_entity_embedding` interpolate entity types into Cypher queries via f-strings. Currently safe (enum-gated), but any future extension accepting user-supplied types would be a Cypher injection vector.

**Findings addressed:** H1 (`_create_entity_relationship`), H2 (`_update_entity_embedding`)

#### Change 3.1: Add `ALLOWED_ENTITY_TYPES` constant to `kg_processor.py`

**File:** `api/kg_processor.py`, near `EntityType` enum (~line 295)

**Add after the `EntityType` enum:**
```python
# Whitelist for safe Cypher label interpolation
ALLOWED_ENTITY_TYPES: set[str] = {e.value for e in EntityType}
# {"Topic", "Concept", "Methodology", "Finding", "Definition", "Citation"}
```

#### Change 3.2: Validate entity types before Cypher interpolation in `_create_entity_relationship`

**File:** `api/kg_processor.py`, `_create_entity_relationship` (~line 3420)

**Add at start of method (after the `valid_rel_types` check):**
```python
if source_type not in ALLOWED_ENTITY_TYPES:
    raise ValueError(f"Invalid source entity type: {source_type}")
if target_type not in ALLOWED_ENTITY_TYPES:
    raise ValueError(f"Invalid target entity type: {target_type}")
```

#### Change 3.3: Validate entity type before Cypher interpolation in `_update_entity_embedding`

**File:** `api/kg_processor.py`, `_update_entity_embedding` (~line 3555)

**Add at start of method:**
```python
if entity_type not in ALLOWED_ENTITY_TYPES:
    raise ValueError(f"Invalid entity type: {entity_type}")
```

#### Change 3.4: Validate entity type in `_create_entity_node`

**File:** `api/kg_processor.py`, `_create_entity_node` (~line 3700)

**Add at start of method:**
```python
if entity.entity_type.value not in ALLOWED_ENTITY_TYPES:
    raise ValueError(f"Invalid entity type: {entity.entity_type.value}")
```

**Validation:**
```bash
python -m pytest AURA-NOTES-MANAGER/api/tests/ -v -k "entity" --tb=short
# Manual: attempt to create entity with type "Injected; DETACH DELETE" — should raise ValueError
```

---

### Group 4: Concurrent Batch Processing (H3, H4)

**Rationale:** `process_batch` processes documents sequentially (N× slower). `delete_batch` loops sequentially with sync-blocking calls. Both benefit from concurrency after Group 1 fixes the async issue.

**Findings addressed:** H3 (`process_batch` sequential), H4 (`delete_batch` sequential)

#### Change 4.1: Convert `process_batch` to concurrent with semaphore

**File:** `api/kg_processor.py`, `process_batch` method (~line 1603)

**Current:**
```python
async def process_batch(self, document_ids, module_id, user_id, document_map=None):
    results = []
    doc_map = document_map or {}
    total = len(document_ids)
    for i, doc_id in enumerate(document_ids):
        self._emit_progress("batch", i + 1, total, f"Processing document {i + 1}/{total}: {doc_id}")
        doc_data = doc_map.get(doc_id)
        result = await self.process_document(doc_id, module_id, user_id, document_data=doc_data)
        results.append(result)
    return results
```

**Target:**
```python
async def process_batch(self, document_ids, module_id, user_id, document_map=None):
    results = []
    doc_map = document_map or {}
    total = len(document_ids)
    sem = asyncio.Semaphore(3)  # Max 3 concurrent documents

    async def _process_one(index: int, doc_id: str):
        async with sem:
            self._emit_progress(
                "batch", index + 1, total,
                f"Processing document {index + 1}/{total}: {doc_id}"
            )
            doc_data = doc_map.get(doc_id)
            return await self.process_document(
                doc_id, module_id, user_id, document_data=doc_data
            )

    tasks = [_process_one(i, doc_id) for i, doc_id in enumerate(document_ids)]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Convert exceptions to error result dicts
    final_results = []
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            final_results.append({
                "document_id": document_ids[i],
                "status": "error",
                "error": str(result),
            })
        else:
            final_results.append(result)

    logger.info(f"Batch processing complete: {len(final_results)} documents")
    return final_results
```

#### Change 4.2: Convert `delete_batch` to concurrent

**File:** `api/kg/router.py`, `delete_batch` endpoint (~line 300)

**Current:** Sequential `for` loop calling `await graph_manager.delete_document(doc_id)`.

**Target:**
```python
async def _delete_one(doc_id: str):
    """Delete a single document and return (doc_id, success, entity_ids, error)."""
    note_ref = tasks_find_note_by_id(doc_id, module_id=request.module_id)
    if not note_ref:
        return (doc_id, False, [], "not found")

    note = note_ref.get()
    doc_data = note.to_dict()
    if doc_data is None:
        return (doc_id, False, [], "no data")

    # ... module_id validation, kg_status check ...

    try:
        success, connected_entities = await graph_manager.delete_document(doc_id)
        if not success:
            return (doc_id, False, [], "neo4j delete failed")
    except Exception as e:
        return (doc_id, False, [], str(e))

    firestore_success = await _update_firestore_with_retry(note_ref, doc_id)
    return (doc_id, True, connected_entities, None if firestore_success else "firestore sync failed")

# Execute concurrently
tasks = [_delete_one(doc_id) for doc_id in request.file_ids]
results = await asyncio.gather(*tasks, return_exceptions=True)

# Aggregate results
deleted_count = 0
failed_ids = []
all_connected_entity_ids = []
for result in results:
    if isinstance(result, Exception):
        continue
    doc_id, success, entity_ids, error = result
    if success:
        deleted_count += 1
        all_connected_entity_ids.extend(entity_ids)
    else:
        failed_ids.append(doc_id)

# Orphan cleanup once after all deletions (existing pattern, preserved)
if all_connected_entity_ids:
    unique_entity_ids = list(set(all_connected_entity_ids))
    orphans_deleted = await graph_manager.cleanup_orphaned_entities(unique_entity_ids)
```

**Validation:**
```bash
python -m pytest AURA-NOTES-MANAGER/api/tests/ -v -k "batch" --tb=short
# Manual: process 5 documents, verify all complete and no race conditions in Neo4j
```

---

### Group 5: Observability & Error Handling (H5, M1, M5)

**Rationale:** Silent failures make debugging impossible. LLM calls have no timeout. Dedup failures are swallowed without surfacing in the result.

**Findings addressed:** H5 (`_parse_entities_response` swallows errors), M1 (no LLM timeout), M5 (dedup failure swallowed)

#### Change 5.1: Log raw LLM response on parse failure

**File:** `api/kg_processor.py`, `_parse_entities_response` (~line 621)

**Current:**
```python
except (json.JSONDecodeError, ValueError) as e:
    logger.warning(f"Failed to parse entity response: {e}")
```

**Target:**
```python
except (json.JSONDecodeError, ValueError) as e:
    logger.warning(f"Failed to parse entity response: {e}")
    logger.debug(f"Raw response (first 500 chars): {response_text[:500]}")
```

#### Change 5.2: Add timeout to LLM calls

**File:** `api/kg_processor.py`, `GeminiClient.generate_text` (~line 590)

**Current:**
```python
async def generate_text(self, prompt, max_tokens=2048):
    try:
        cfg = resolve_use_case_config("entity_extraction")
        router = get_default_router()
        response = await router.generate(...)
        return response.text
    except Exception as e:
        logger.error(f"Text generation failed: {e}")
        return ""
```

**Target:**
```python
LLM_CALL_TIMEOUT = 60.0  # seconds

async def generate_text(self, prompt, max_tokens=2048):
    try:
        cfg = resolve_use_case_config("entity_extraction")
        router = get_default_router()
        response = await asyncio.wait_for(
            router.generate(...),
            timeout=LLM_CALL_TIMEOUT,
        )
        return response.text
    except asyncio.TimeoutError:
        logger.error(f"LLM call timed out after {LLM_CALL_TIMEOUT}s")
        return ""
    except Exception as e:
        logger.error(f"Text generation failed: {e}")
        return ""
```

**Also apply to `extract_entities` method (~line 710):**
```python
response = await asyncio.wait_for(
    router.generate(...),
    timeout=LLM_CALL_TIMEOUT,
)
```

**Add constant near top of file:**
```python
LLM_CALL_TIMEOUT = 60.0  # Timeout for LLM API calls in seconds
```

#### Change 5.3: Surface dedup failure in result dict

**File:** `api/kg_processor.py`, `process_document` dedup error handling (~line 1525)

**Current:**
```python
except Exception as e:
    logger.warning(f"Semantic deduplication failed: {e}")
    result["entities_deduplicated"] = len(all_entities)
```

**Target:**
```python
except Exception as e:
    logger.warning(f"Semantic deduplication failed: {e}")
    result["entities_deduplicated"] = len(all_entities)
    result["dedup_error"] = str(e)
```

**Also update the result dict initialization (~line 890) to include:**
```python
"dedup_error": None,
```

**Validation:**
```bash
python -m pytest AURA-NOTES-MANAGER/api/tests/ -v --tb=short
# Verify: trigger a malformed LLM response, check debug logs contain raw response
# Verify: result dict contains dedup_error field when dedup fails
```

---

### Group 6: Query Optimization & Performance Guards (H6, H7, M2, L1, L5)

**Rationale:** Multiple queries use label-scan patterns (`OR` across 4+ labels) instead of index-backed lookups. Force-directed layout has no node count guard.

**Findings addressed:** H6 (no index hit), H7 (f-string depth), M2 (O(n²) layout), L1 (Cartesian product), L5 (no node count guard)

#### Change 6.1: Create per-label indexes for entity ID lookups

**File:** `api/schemas/neo4j_schema.py` (add new index definitions)

**Add to `VECTOR_INDICES` or create a new `ENTITY_LOOKUP_INDICES` list:**
```python
ENTITY_LOOKUP_INDICES = [
    {"name": "entity_id_topic", "label": "Topic", "property": "id"},
    {"name": "entity_id_concept", "label": "Concept", "property": "id"},
    {"name": "entity_id_methodology", "label": "Methodology", "property": "id"},
    {"name": "entity_id_finding", "label": "Finding", "property": "id"},
    {"name": "entity_id_definition", "label": "Definition", "property": "id"},
    {"name": "entity_id_citation", "label": "Citation", "property": "id"},
]
```

**Then in `graph_manager.py` methods, use UNION queries for better index utilization:**

**Current (`get_entity_by_id`):**
```python
cypher = """
MATCH (e)
WHERE (e:Topic OR e:Concept OR e:Methodology OR e:Finding)
AND e.id = $entity_id
RETURN ...
"""
```

**Target:**
```python
cypher = """
CALL {
    MATCH (e:Topic {id: $entity_id}) RETURN e
    UNION
    MATCH (e:Concept {id: $entity_id}) RETURN e
    UNION
    MATCH (e:Methodology {id: $entity_id}) RETURN e
    UNION
    MATCH (e:Finding {id: $entity_id}) RETURN e
}
WITH e
RETURN e.id as id, e.name as name, labels(e)[0] as entity_type,
       e.definition as definition, e.module_id as module_id,
       e.confidence as confidence, e.mention_count as mention_count
LIMIT 1
"""
```

**Apply same pattern to:**
- `get_entities_by_name` (~line 270)
- `get_entity_neighbors` (~line 340)
- `expand_graph_context` (~line 700)

#### Change 6.2: Add assertion for depth dependency in `get_entity_neighborhood`

**File:** `api/graph_visualizer.py`, `get_entity_neighborhood` (~line 1009)

**Current:**
```python
depth = max(1, min(4, depth))
# ... f-string uses {depth}
```

**Target — add assertion documenting the safety dependency:**
```python
depth = max(1, min(4, depth))
# SAFETY: depth is clamped to [1, 4] above. The f-string interpolation
# below is safe ONLY because of this clamping. If the clamping is removed,
# switch to parameterized query or APOC variable-length paths.
assert 1 <= depth <= 4, f"Depth must be 1-4, got {depth}"
```

#### Change 6.3: Add node count guard to `force_directed_layout`

**File:** `api/graph_visualizer.py`, `force_directed_layout` (~line 225)

**Add after the `if not nodes: return nodes` check:**
```python
MAX_FORCE_DIRECTED_NODES = 500
if len(nodes) > MAX_FORCE_DIRECTED_NODES:
    logger.warning(
        f"Force-directed layout requested for {len(nodes)} nodes "
        f"(max recommended: {MAX_FORCE_DIRECTED_NODES}). "
        f"Consider using circular layout for better performance."
    )
```

#### Change 6.4: Move `LIMIT` before `UNWIND` in `get_module_graph`

**File:** `api/graph_visualizer.py`, `get_module_graph` (~line 593)

**Current Cypher:**
```cypher
UNWIND entities as e1
OPTIONAL MATCH (e1)-[r]->(e2)
WHERE e2 IN entities
```

**Target — limit entity set before UNWIND:**
```cypher
WITH m, entities[0..200] as limited_entities, documents
UNWIND limited_entities as e1
OPTIONAL MATCH (e1)-[r]->(e2)
WHERE e2 IN limited_entities
```

**Validation:**
```bash
python -m pytest AURA-NOTES-MANAGER/api/tests/ -v -k "graph" --tb=short
# Manual: query module graph with 500+ entities, verify response time < 2s
```

---

### Group 7: Input Sanitization (M6)

**Rationale:** `_parse_document` checks 6 filesystem paths using unsanitized `document_id`. If `document_id` contains `../`, this is a path traversal vulnerability.

**Findings addressed:** M6 (path traversal + unnecessary filesystem checks)

#### Change 7.1: Sanitize `document_id` in `_parse_document`

**File:** `api/kg_processor.py`, `_parse_document` (~line 1863)

**Add at the start of the method (after doc_data check):**
```python
# Sanitize document_id to prevent path traversal
import re
if not re.match(r'^[a-zA-Z0-9_-]+$', document_id):
    logger.warning(f"Invalid document_id format: {document_id}")
    raise ValueError(f"Invalid document ID: {document_id}")
```

#### Change 7.2: Remove or consolidate filesystem fallback paths

**Current:** 6 paths checked sequentially before Firestore.

**Target — reduce to Firestore-first with single fallback:**
```python
# Try Firestore first (primary source)
try:
    from config import db
    # ... existing Firestore lookup logic ...
except Exception as e:
    logger.warning(f"Failed to fetch document from Firestore: {e}")

# Only try filesystem if document_id is clean and a file_path hint exists
if file_path and os.path.exists(file_path):
    return await self._parse_file(file_path)

raise FileNotFoundError(f"Document not found: {document_id}")
```

**Rationale:** The 6-path filesystem scan is a legacy pattern. Firestore is the primary document store. If a file path is known, it's passed explicitly via `file_path`.

**Validation:**
```bash
python -m pytest AURA-NOTES-MANAGER/api/tests/ -v -k "parse" --tb=short
# Manual: pass document_id="../../../etc/passwd" — should raise ValueError
```

---

### Group 8: Frontend UX Fixes (M4, M8, L2)

**Rationale:** Failed queue items have no retry/dismiss. Polling stops for pending items. Dead component clutters codebase.

**Findings addressed:** M4 (no retry/dismiss), M8 (polling stops for pending), L2 (dead FileSelectionBar)

#### Change 8.1: Add retry and dismiss to `ProcessingQueue` failed items

**File:** `frontend/src/features/kg/components/ProcessingQueue.tsx`

**Current `QueueItem` — error display only:**
```tsx
{item.error && (
    <div className="text-[10px] text-red-500 flex items-center gap-1 mt-1">
        <AlertCircle className="h-3 w-3" />
        {item.error}
    </div>
)}
```

**Target — add retry and dismiss buttons:**
```tsx
{item.error && (
    <>
        <div className="text-[10px] text-red-500 flex items-center gap-1 mt-1">
            <AlertCircle className="h-3 w-3" />
            {item.error}
        </div>
        <div className="flex gap-2 mt-1">
            <button
                className="text-[10px] text-blue-500 hover:underline"
                onClick={() => handleRetry(item.document_id, item.module_id)}
            >
                Retry
            </button>
            <button
                className="text-[10px] text-zinc-400 hover:underline"
                onClick={() => handleDismiss(item.document_id)}
            >
                Dismiss
            </button>
        </div>
    </>
)}
```

**Add to `ProcessingQueue` component:**
```tsx
const { processFiles } = useKGProcessing();
const queryClient = useQueryClient();

const handleRetry = (documentId: string, moduleId: string) => {
    processFiles.mutate({ file_ids: [documentId], module_id: moduleId });
};

const handleDismiss = (documentId: string) => {
    queryClient.setQueryData(['kg', 'queue'], (old: ProcessingQueueItem[] | undefined) =>
        old?.filter(item => item.document_id !== documentId) ?? []
    );
};
```

**Add imports:**
```tsx
import { useQueryClient } from '@tanstack/react-query';
import { useKGProcessing } from '../hooks/useKGProcessing';
```

#### Change 8.2: Fix polling to include pending items

**File:** `frontend/src/features/kg/hooks/useKGProcessing.ts`

**Current:**
```typescript
refetchInterval: (query) => {
    const queue = query.state.data as Array<{ status: string }> | undefined;
    const hasActiveItems = queue?.some(item => item.status === 'processing');
    return hasActiveItems ? 2000 : false;
},
```

**Target:**
```typescript
refetchInterval: (query) => {
    const queue = query.state.data as Array<{ status: string }> | undefined;
    const hasActiveItems = queue?.some(
        item => item.status === 'processing' || item.status === 'pending'
    );
    return hasActiveItems ? 2000 : false;
},
```

#### Change 8.3: Remove dead `FileSelectionBar` component

**File:** `frontend/src/features/kg/components/FileSelectionBar.tsx`

**Action:** Delete the file entirely, and remove any imports of it from other files.

**Check for imports:**
```bash
grep -r "FileSelectionBar" frontend/src/
```

**Also delete:** `frontend/src/features/kg/components/FileSelectionBar.test.tsx`

**Validation:**
```bash
cd AURA-NOTES-MANAGER/frontend && npm run build
cd AURA-NOTES-MANAGER/frontend && npm test -- --run
```

---

### Group 9: Data Quality (M3, L3)

**Rationale:** Entity ID generation uses `chunk_id` scoping, causing duplicate entities across chunks. CSV export has unescaped quotes.

**Findings addressed:** M3 (entity ID collision/fragmentation), L3 (CSV injection)

#### Change 9.1: Change entity ID scope from `chunk_id` to `module_id`

**File:** `api/kg_processor.py`, `_generate_entity_id` (~line 534)

**Current:**
```python
def _generate_entity_id(self, name: str, chunk_id: str) -> str:
    content = f"{name}:{chunk_id}"
    return f"entity_{hashlib.md5(content.encode()).hexdigest()[:12]}"
```

**Target:**
```python
def _generate_entity_id(self, name: str, module_id: str) -> str:
    """Generate deterministic entity ID scoped to module.

    Using module_id instead of chunk_id ensures the same entity name
    within a module always gets the same ID, reducing dedup burden.
    """
    content = f"{name.lower().strip()}:{module_id}"
    return f"entity_{hashlib.md5(content.encode()).hexdigest()[:16]}"
```

**Impact:** All callers of `_generate_entity_id` must be updated to pass `module_id` instead of `chunk_id`. Search for all call sites:

```bash
grep -n "_generate_entity_id" api/kg_processor.py
```

**Call sites to update:**
- `_parse_entities_response` (~line 670) — needs `module_id` parameter added
- `_mock_entities` (~line 555) — needs `module_id` parameter added
- Any template extraction code

**Warning:** This changes all entity IDs. Existing Neo4j data will have old IDs. A migration or re-processing of all documents is required after this change.

#### Change 9.2: Escape double quotes in CSV export

**File:** `api/graph_visualizer.py`, `_export_csv` (~line 1305)

**Add helper function:**
```python
@staticmethod
def _csv_escape(val: str) -> str:
    """Escape double quotes in CSV values."""
    return val.replace('"', '""')
```

**Update `_export_csv` method:**
```python
def _export_csv(self, graph: VisualizationGraph) -> bytes:
    output = io.StringIO()
    esc = self._csv_escape

    output.write("# NODES\n")
    output.write("id,label,type,color,size,x,y\n")
    for node in graph.nodes:
        output.write(
            f'"{esc(node.id)}","{esc(node.label)}","{esc(node.type)}",'
            f'"{esc(node.color or "")}",{node.size},{node.x or 0},{node.y or 0}\n'
        )

    output.write("\n# EDGES\n")
    output.write("source,target,type,weight,color\n")
    for edge in graph.edges:
        output.write(
            f'"{esc(edge.source)}","{esc(edge.target)}","{esc(edge.type)}",'
            f'{edge.weight},"{esc(edge.color or "")}"\n'
        )

    return output.getvalue().encode("utf-8")
```

**Validation:**
```bash
python -m pytest AURA-NOTES-MANAGER/api/tests/ -v --tb=short
# Manual: process document, verify entity IDs are 16-char hex
# Manual: export graph with label containing '"' — verify valid CSV
```

---

### Group 10: Thread Safety & Test Coverage (L4, test gap)

**Rationale:** `SchemaValidator` caches are not thread-safe. `DeleteFromKGDialog` has no tests despite being a destructive operation.

**Findings addressed:** L4 (cache race conditions), missing `DeleteFromKGDialog` tests

#### Change 10.1: Add thread safety to `SchemaValidator` caches

**File:** `api/schema_validator.py`

**Option A (simplest) — add `threading.Lock`:**
```python
import threading

class SchemaValidator:
    def __init__(self, driver):
        self.driver = driver
        self._cached_indices: Optional[Dict[str, Any]] = None
        self._cached_constraints: Optional[Dict[str, Any]] = None
        self._cached_labels: Optional[Set[str]] = None
        self._cached_rel_types: Optional[Set[str]] = None
        self._cache_lock = threading.Lock()

    def _get_database_indices(self) -> Dict[str, Dict[str, Any]]:
        with self._cache_lock:
            if self._cached_indices is not None:
                return self._cached_indices
            with self.driver.session() as session:
                result = session.run("SHOW INDEXES")
                self._cached_indices = {
                    record["name"]: dict(record) for record in result
                }
            return self._cached_indices
```

**Apply same pattern to `_get_database_constraints`, `_get_database_labels`, `_get_database_relationship_types`.**

#### Change 10.2: Add unit tests for `DeleteFromKGDialog`

**File:** `frontend/src/features/kg/components/__tests__/DeleteFromKGDialog.test.tsx` (new)

**Test cases:**
1. Dialog does not render when `kgDeleteDialog.open` is `false`
2. Dialog renders with correct document count when open
3. Submit button triggers `deleteFiles.mutate` with correct `file_ids` and `module_id`
4. Error state displays error message from mutation
5. Success state displays deleted/failed counts
6. Close button resets all local state and calls `closeKGDeleteDialog`
7. Success close also calls `clearSelection`, `setSelectionMode(false)`, `setDeleteMode(false)`

**Validation:**
```bash
cd AURA-NOTES-MANAGER/frontend && npm test -- --run
cd AURA-NOTES-MANAGER/frontend && npm run build
```

---

## Verification Checklist

### After Each Group

| Group | Verification |
|-------|-------------|
| 1 (Async) | `python -m pytest api/tests/ -v` — no BlockingWarning in logs |
| 2 (Transactions) | Manual: kill mid-process, check Neo4j for partial data |
| 3 (Injection) | Unit test: reject invalid entity types |
| 4 (Concurrency) | Process 5 docs concurrently, verify all complete |
| 5 (Observability) | Trigger parse failure, verify debug log has raw response |
| 6 (Optimization) | Query with 500+ entities, verify < 2s response |
| 7 (Sanitization) | Pass `../` in document_id, verify ValueError |
| 8 (Frontend) | `npm run build && npm test -- --run` |
| 9 (Data Quality) | Process doc, verify deterministic entity IDs |
| 10 (Tests) | `npm test -- --run` — all new tests pass |

### Full Regression After All Groups

```bash
# Backend
cd D:\Peter\AURA Twin Proj\AURA-PROJ
.venv\Scripts\activate
python -m pytest AURA-NOTES-MANAGER/api/tests/ -v --tb=short

# Frontend
cd AURA-NOTES-MANAGER/frontend
npm run build
npm test -- --run
npm run lint

# Type check
npx tsc --noEmit
```

---

## Risk Notes

| Risk | Mitigation |
|------|-----------|
| **Group 1 (async wrapping)** may change error propagation semantics | Test all error paths manually; `asyncio.to_thread` preserves exceptions |
| **Group 2 (transactions)** — if a single entity has invalid data, the entire batch rolls back | Validate entity data before entering transaction; add per-entity try/except inside the transaction if partial success is acceptable |
| **Group 4 (concurrency)** — concurrent Neo4j writes may hit lock contention | Semaphore limit of 3 is conservative; monitor Neo4j deadlock logs |
| **Group 9 (entity ID change)** — all existing entity IDs change | Requires full re-processing of all documents or a migration script that maps old IDs to new IDs |
| **Group 3 (whitelist)** — `Definition` and `Citation` entity types exist in the enum but are not used in `graph_manager.py` queries | Verify all entity types are handled in UNION queries if expanding beyond Topic/Concept/Methodology/Finding |
| **Group 6 (UNION queries)** — UNION queries are verbose and may hit Neo4j query length limits for many labels | Current 6 types is well within limits; monitor if more types are added |
| **General** — changes to `_store_in_neo4j` transaction semantics may affect existing Celery task callers | Verify `process_batch_task` in `api/tasks/document_processing_tasks.py` works with updated signatures |

---

## Dependency Graph

```
Group 1 (Async) ──► Group 4 (Concurrency)
     │
     ▼
Group 2 (Transactions)
     
Group 3 (Injection) ── independent
Group 5 (Observability) ── independent
Group 6 (Optimization) ── independent (but benefits from Group 1)
Group 7 (Sanitization) ── independent
Group 8 (Frontend) ── independent
Group 9 (Data Quality) ── independent (but coordinate with Group 2)
Group 10 (Tests) ── depends on Group 8 (DeleteFromKGDialog changes)
```

**Recommended execution order:**
1. Group 1 → Group 2 → Group 4 (Neo4j infrastructure, must be sequential)
2. Group 3 → Group 5 → Group 7 (backend hardening, can be parallel)
3. Group 6 → Group 9 (optimization, can be parallel)
4. Group 8 → Group 10 (frontend, sequential)
