# Knowledge Graph Processing Pipeline — Code Review

**Date:** 2026-05-24
**Scope:** Full KG processing pipeline (backend + frontend)
**Files reviewed:** 16 files across `api/` and `frontend/src/features/kg/`

---

## Summary

The KG pipeline is architecturally sound with good separation of concerns: a multi-stage processing pipeline (chunk → embed → extract → dedup → store), a REST API layer for status/batch/delete operations, and a React frontend with React Query hooks. The retry/resilience patterns around LLM and embedding calls are well-implemented via tenacity. However, there are several correctness and robustness issues — most notably missing transaction protection in Neo4j writes, and synchronous Neo4j calls inside `async def` methods that block the event loop.

**Critical:** 3 | **High:** 7 | **Medium:** 8 | **Low:** 5

---

## Critical Issues

### C1. `await` on synchronous helper methods — potential TypeError

**File:** `api/kg_processor.py`, lines ~1790–1800 (`process_document`)
**File:** `api/kg_processor.py`, `_update_entity_embedding` method

Several helper methods are declared `async def` but call only synchronous Neo4j `session.run()`. When awaited from `process_document`, Python will execute the coroutine correctly, but `session.run()` blocks the event loop — no other async task can proceed until the synchronous Neo4j I/O completes.

More critically, `_update_entity_embedding` (called from `_generate_and_store_entity_embeddings`) uses `await` to invoke it:

```python
await self._update_entity_embedding(session, entity.id, ...)
```

If `session` is a synchronous Neo4j `Session`, the `session.run()` inside is synchronous. This works in CPython but blocks the event loop. Under concurrent document processing, this serializes all Neo4j I/O.

**Severity:** Critical (performance collapse under concurrent load)
**Fix:** Either (a) use the async Neo4j driver (`session = driver.async_session()`) throughout, or (b) wrap sync calls in `asyncio.to_thread()`:

```python
# Option A: async session
async with self.driver.async_session() as session:
    await session.run(query, params)

# Option B: to_thread wrapper
await asyncio.to_thread(session.run, query, params)
```

---

### C2. No transaction protection in `_store_in_neo4j` — partial writes on failure

**File:** `api/kg_processor.py`, `_store_in_neo4j` method (~lines 3150–3200)

The Neo4j write path creates Document → Chunks → Entity nodes → Relationships in separate `session.run()` calls with no transaction wrapping. If the process crashes or an exception is thrown between steps, partial data (e.g., Document + some Chunks but no entities) remains in Neo4j.

The calling code in `process_document` sets `result["status"] = "error"` on exception but performs **no cleanup** of partially written Neo4j data.

**Severity:** Critical (data integrity)
**Fix:** Wrap all Neo4j writes in a single write transaction:

```python
async def _store_in_neo4j(self, document_id, module_id, user_id, chunks, entities):
    def _tx_write(tx):
        # Create document node
        tx.run(doc_query, ...)
        for chunk in chunks:
            tx.run(chunk_query, ...)
            for entity in chunk.entities:
                tx.run(entity_query, ...)
                tx.run(rel_query, ...)

    with self.driver.session() as session:
        session.execute_write(_tx_write)
```

Alternatively, add a cleanup step in the `except` block of `process_document` to delete any partially written data.

---

### C3. Synchronous Neo4j calls block the FastAPI event loop

**File:** `api/graph_manager.py`, all `async def` methods
**File:** `api/kg_processor.py`, all `_create_*` helper methods
**File:** `api/kg/router.py`, `delete_batch` endpoint

All `GraphManager` methods (`delete_document`, `cleanup_orphaned_entities`, `get_subgraph`, etc.) are declared `async def` but use the **synchronous** Neo4j driver (`self.driver.session()` returns a sync `Session`). The `session.run()` call blocks the event loop.

Similarly, `delete_batch` in `router.py` calls `await graph_manager.delete_document(doc_id)` in a loop — each call blocks the event loop, making the endpoint unresponsive to other requests during deletion.

**Severity:** Critical (availability under load)
**Fix:** Use `self.driver.session()` with sync operations wrapped in `asyncio.to_thread`, or use the async Neo4j driver:

```python
async def delete_document(self, doc_id: str) -> tuple[bool, List[str]]:
    def _sync_delete():
        with self.driver.session() as session:
            # ... all sync operations ...
    return await asyncio.to_thread(_sync_delete)
```

---

## High Issues

### H1. `_create_entity_relationship` uses f-string for entity type label — injection risk if enum changes

**File:** `api/kg_processor.py`, `_create_entity_relationship` method (~line 3100)

```python
query = f"""
MATCH (source:{source_type} {{id: $source_id, module_id: $module_id}})
MATCH (target:{target_type} {{id: $target_id, module_id: $module_id}})
MERGE (source)-[r:{rel_type}]->(target)
...
"""
```

While `rel_type` is validated against a `valid_rel_types` whitelist (safe), `source_type` and `target_type` come from `entity.entity_type.value` which is currently an `EntityType` enum value. If the enum is ever extended with user-supplied data (e.g., a custom entity type feature), this becomes a Cypher injection vector.

**Severity:** High (security, latent)
**Fix:** Validate entity types against a whitelist before interpolation, or use the label-safe pattern:

```python
ALLOWED_TYPES = {"Topic", "Concept", "Methodology", "Finding", "Definition", "Citation"}
if source_type not in ALLOWED_TYPES or target_type not in ALLOWED_TYPES:
    raise ValueError(f"Invalid entity type: {source_type} or {target_type}")
```

---

### H2. `_update_entity_embedding` uses f-string for entity type in Cypher

**File:** `api/kg_processor.py`, `_update_entity_embedding` method (~line 3140)

```python
query = f"""
MATCH (e:{entity_type} {{id: $entity_id, module_id: $module_id}})
SET e.embedding = $embedding, ...
"""
```

Same f-string injection risk as H1. Entity type is not validated against a whitelist.

**Severity:** High (security, latent)
**Fix:** Add whitelist validation (see H1).

---

### H3. `process_batch` is completely sequential — N× slower than necessary

**File:** `api/kg_processor.py`, `process_batch` method (~line 1500)

```python
for i, doc_id in enumerate(document_ids):
    result = await self.process_document(doc_id, module_id, user_id, ...)
    results.append(result)
```

Documents are processed one-by-one. For a batch of 10 documents, this is ~10× slower than concurrent processing.

**Severity:** High (performance)
**Fix:** Use `asyncio.gather` with a concurrency semaphore:

```python
async def process_batch(self, document_ids, module_id, user_id, ...):
    sem = asyncio.Semaphore(3)  # max 3 concurrent
    async def process_one(doc_id):
        async with sem:
            return await self.process_document(doc_id, module_id, user_id, ...)
    return await asyncio.gather(*[process_one(d) for d in document_ids])
```

---

### H4. `delete_batch` loops sequentially with sync-blocking calls

**File:** `api/kg/router.py`, `delete_batch` endpoint (~line 300)

```python
for doc_id in request.file_ids:
    # ... validation ...
    success, connected_entities = await graph_manager.delete_document(doc_id)
```

Each `delete_document` call blocks the event loop (see C3), and deletions are sequential. For a batch of 20 documents, the endpoint blocks for the entire duration.

**Severity:** High (availability)
**Fix:** Process deletions concurrently using `asyncio.gather` (after fixing C3 to use proper async I/O).

---

### H5. `_parse_entities_response` silently swallows parse errors — returns empty list

**File:** `api/kg_processor.py`, `GeminiClient._parse_entities_response` (~line 490)

```python
except (json.JSONDecodeError, ValueError) as e:
    logger.warning(f"Failed to parse entity response: {e}")
return entities  # Returns empty list
```

If the LLM returns malformed JSON, the method silently returns an empty entity list. The caller in `extract_entities` then logs "Extracted 0 entities" as info — no error is raised. This makes debugging difficult when the LLM consistently produces unparseable output.

**Severity:** High (observability)
**Fix:** Log the raw response for debugging and consider a circuit breaker pattern:

```python
except (json.JSONDecodeError, ValueError) as e:
    logger.warning(f"Failed to parse entity response: {e}")
    logger.debug(f"Raw response (first 500 chars): {response_text[:500]}")
```

---

### H6. `get_entity_by_id` scans ALL entity label types — no index hit

**File:** `api/graph_manager.py`, `get_entity_by_id` method (~line 140)

```python
cypher = """
MATCH (e)
WHERE (e:Topic OR e:Concept OR e:Methodology OR e:Finding)
AND e.id = $entity_id
RETURN ...
"""
```

This uses a label scan (`OR` across 4 labels) instead of using the `id` property index. The same pattern appears in `get_entities_by_name`, `get_entity_neighbors`, and `expand_graph_context`.

**Severity:** High (performance at scale)
**Fix:** Create a composite index or use a union pattern:

```cypher
CREATE INDEX entity_id_lookup IF NOT EXISTS
FOR (e:Topic) ON (e.id)

CREATE INDEX entity_id_lookup_concept IF NOT EXISTS
FOR (e:Concept) ON (e.id)
-- etc.
```

Or use a UNION query for better index utilization.

---

### H7. `graph_visualizer.py` `get_entity_neighborhood` uses f-string for depth in Cypher

**File:** `api/graph_visualizer.py`, `get_entity_neighborhood` method (~line 380)

```python
cypher = f"""
...
CALL {{
    WITH center
    MATCH path = (center)-[*1..{depth}]-(neighbor)
    ...
}}
...
"""
```

`depth` is clamped to 1–4 before this call, so it's safe in practice. However, this pattern breaks the rule of parameterized queries and could be missed during future refactoring if the clamping is removed.

**Severity:** High (code smell, latent)
**Fix:** Use `subquery` with parameterized depth, or document the clamping dependency with an assertion.

---

## Medium Issues

### M1. No timeout on LLM calls in `generate_text` and `extract_entities`

**File:** `api/kg_processor.py`, `GeminiClient.generate_text` (~line 420), `extract_entities` (~line 540)

LLM calls have no timeout. A hung Gemini API call will block the entire processing pipeline indefinitely.

**Severity:** Medium
**Fix:** Add `asyncio.wait_for()` with a timeout:

```python
try:
    response = await asyncio.wait_for(
        router.generate(...), timeout=60.0
    )
except asyncio.TimeoutError:
    logger.error(f"LLM call timed out for chunk {chunk_id}")
    raise ExtractionError("LLM timeout")
```

---

### M2. Force-directed layout is O(n²×iterations) — slow for large graphs

**File:** `api/graph_visualizer.py`, `force_directed_layout` (~line 170)

```python
for _ in range(iterations):
    for i, node_a in enumerate(nodes):
        for node_b in nodes[i + 1:]:
            # ... repulsion calculation
```

For 500 nodes × 100 iterations, this is ~12.5M pair calculations per request. This will cause response latency spikes.

**Severity:** Medium
**Fix:** Use a quadtree approximation or limit the max_nodes for force-directed layout to ~200, falling back to circular for larger graphs.

---

### M3. `_generate_entity_id` uses truncated MD5 — collision risk

**File:** `api/kg_processor.py`, `GeminiClient._generate_entity_id` (~line 360)

```python
def _generate_entity_id(self, name: str, chunk_id: str) -> str:
    content = f"{name}:{chunk_id}"
    return f"entity_{hashlib.md5(content.encode()).hexdigest()[:12]}"
```

12 hex characters = 48 bits of entropy. With ~1000 entities per document, birthday paradox gives a collision probability of ~10⁻⁸ per document. Acceptable for small scale but risky for modules with many documents sharing entity names.

More importantly, entity IDs are scoped to `name:chunk_id`. If the same entity name appears in different chunks of the same document, they get different IDs. The deduplication step must correctly merge these — but if dedup fails silently (which it can per M5), duplicate entity nodes persist.

**Severity:** Medium
**Fix:** Use `module_id` instead of `chunk_id` as the scope for deterministic IDs:

```python
def _generate_entity_id(self, name: str, module_id: str) -> str:
    content = f"{name}:{module_id}"
    return f"entity_{hashlib.md5(content.encode()).hexdigest()[:16]}"
```

---

### M4. `ProcessingQueue` component has no dismiss/retry for failed items

**File:** `frontend/src/features/kg/components/ProcessingQueue.tsx`, `QueueItem` component

Failed items show the error message but there is no retry button or dismiss action. Users must navigate away and back, or reload the page to clear failed items from the queue.

**Severity:** Medium (UX)
**Fix:** Add a retry button and dismiss action to failed queue items.

---

### M5. Semantic dedup failure is silently swallowed

**File:** `api/kg_processor.py`, `process_document` (~line 1550)

```python
except Exception as e:
    logger.warning(f"Semantic deduplication failed: {e}")
    result["entities_deduplicated"] = len(all_entities)
```

When dedup fails, `entities_deduplicated` is set to the total entity count (misleadingly indicating no dedup was needed) rather than flagging the failure. The result dict has no `dedup_error` field.

**Severity:** Medium (observability)
**Fix:** Add a `dedup_error` field to the result:

```python
result["entities_deduplicated"] = len(all_entities)
result["dedup_error"] = str(e)
```

---

### M6. `_parse_document` does 6 filesystem checks before Firestore fallback

**File:** `api/kg_processor.py`, `_parse_document` (~line 1700)

```python
possible_paths = [
    f"uploads/{document_id}.pdf",
    f"uploads/{document_id}.docx",
    f"uploads/{document_id}.txt",
    f"documents/{document_id}.pdf",
    f"documents/{document_id}.docx",
    f"documents/{document_id}.txt",
]
for path in possible_paths:
    if os.path.exists(path):
        return await self._parse_file(path)
```

This checks 6 filesystem paths sequentially before falling back to Firestore. Each `os.path.exists` call is an I/O syscall. This is also a path traversal risk if `document_id` contains `../`.

**Severity:** Medium (security + performance)
**Fix:** Sanitize `document_id` and remove filesystem fallback in favor of Firestore-only lookup:

```python
document_id = os.path.basename(document_id)  # Strip path components
```

---

### M7. `_store_in_neo4j` creates entity nodes from `chunk.entities` only — misses standalone entities

**File:** `api/kg_processor.py`, `_store_in_neo4j` method (~line 3170)

```python
for chunk in chunks:
    for entity in chunk.entities:
        await self._create_entity_node(session, entity, module_id)
```

Only entities attached to chunks are stored. But `all_entities` (the global deduplicated list) may contain entities that were not attached to any chunk (e.g., from template extraction or cross-chunk dedup). These entities are lost.

**Severity:** Medium (data loss)
**Fix:** Store all entities from `all_entities`, not just `chunk.entities`:

```python
# Store all entities
for entity in all_entities:
    await self._create_entity_node(session, entity, module_id)

# Then create chunk-entity relationships
for chunk in chunks:
    for entity in chunk.entities:
        relevance_score = entity.properties.get("confidence", 0.7)
        await self._create_chunk_entity_relationship(
            session, chunk.id, entity.id, relevance_score
        )
```

---

### M8. `useProcessingQueue` polling has no stale-while-revalidate

**File:** `frontend/src/features/kg/hooks/useKGProcessing.ts`, `useProcessingQueue` hook

```typescript
refetchInterval: (query) => {
    const queue = query.state.data as Array<{ status: string }> | undefined;
    const hasActiveItems = queue?.some(item => item.status === 'processing');
    return hasActiveItems ? 2000 : false;
},
```

The polling stops when no items have `status === 'processing'`. But items with `status === 'pending'` (just queued, not yet started) will also stop polling. If a task is queued but the Celery worker hasn't picked it up yet, the queue shows stale data.

**Severity:** Medium (UX)
**Fix:** Also poll when there are pending items:

```typescript
const hasActiveItems = queue?.some(
    item => item.status === 'processing' || item.status === 'pending'
);
```

---

## Low Issues

### L1. `get_module_graph` in `graph_visualizer.py` uses `UNWIND` on entities — Cartesian product risk

**File:** `api/graph_visualizer.py`, `get_module_graph` method (~line 300)

```cypher
UNWIND entities as e1
OPTIONAL MATCH (e1)-[r]->(e2)
WHERE e2 IN entities
```

For modules with many entities, the `UNWIND` + `OPTIONAL MATCH` pattern produces an intermediate Cartesian product. The `LIMIT 100` in the subquery helps, but the UNWIND happens after.

**Severity:** Low
**Fix:** Move the `LIMIT` to after the entity collection, or use `CALL { ... } IN TRANSACTIONS` for large modules.

---

### L2. `FileSelectionBar` is a dead component

**File:** `frontend/src/features/kg/components/FileSelectionBar.tsx`

The component returns `null` and has no functionality. The file header says "Placeholder component kept for potential future use."

**Severity:** Low (dead code)
**Fix:** Remove the file or add a TODO comment explaining when it will be reactivated.

---

### L3. `graph_visualizer.py` CSV export has unescaped quotes in labels

**File:** `api/graph_visualizer.py`, `_export_csv` method (~line 680)

```python
output.write(
    f'"{node.id}","{node.label}","{node.type}","{node.color or ""}",{node.size},...'
)
```

If `node.label` contains a double quote (`"`), the CSV output will be malformed.

**Severity:** Low
**Fix:** Escape double quotes in CSV values:

```python
def _csv_escape(val: str) -> str:
    return val.replace('"', '""')

output.write(
    f'"{_csv_escape(node.id)}","{_csv_escape(node.label)}",...'
)
```

---

### L4. `schema_validator.py` caches are not thread-safe

**File:** `api/schema_validator.py`, `_get_database_*` methods

The cached properties (`_cached_indices`, `_cached_constraints`, etc.) are stored as instance attributes. If multiple requests call `validate_schema()` concurrently on the same `SchemaValidator` instance, race conditions on the cache could produce inconsistent results.

**Severity:** Low
**Fix:** Use `functools.lru_cache` or add a lock around cache reads/writes.

---

### L5. `GraphOptions` has `max_nodes: int = 500, ge=1, le=2000` but no enforcement in force_directed_layout

**File:** `api/graph_visualizer.py`

The `GraphOptions.max_nodes` field limits nodes during filtering, but the `force_directed_layout` function does not check the node count. If a caller bypasses `GraphOptions` and passes >500 nodes directly to the layout function, performance will degrade.

**Severity:** Low
**Fix:** Add a node count guard in `force_directed_layout`:

```python
if len(nodes) > 500:
    logger.warning(f"Force-directed layout on {len(nodes)} nodes, consider using circular layout")
```

---

## Frontend Component Assessment

### Test Coverage

| Component | Test File | Coverage |
|-----------|-----------|----------|
| `KGStatusBadge` | `KGStatusBadge.test.tsx` | ✅ Comprehensive (status, size, label, colors) |
| `ProcessDialog` | `ProcessDialog.test.tsx` | ✅ Good (visibility, submit, cancel, success, error) |
| `ProcessingQueue` | `ProcessingQueue.test.tsx` | ✅ Good (visibility, display, progress, colors, errors) |
| `DeleteFromKGDialog` | None | ❌ No tests |
| `FileSelectionBar` | `FileSelectionBar.test.tsx` | N/A (dead component) |

**Note:** `DeleteFromKGDialog` has no tests. This is a destructive operation dialog that should have test coverage for the confirmation flow, error handling, and state cleanup.

### Missing Test for `DeleteFromKGDialog`

**File:** `frontend/src/features/kg/components/DeleteFromKGDialog.tsx`

The dialog performs a destructive deletion operation but has no unit tests. Critical paths to test:
- Dialog opens/closes correctly
- Submit triggers `deleteFiles.mutate` with correct parameters
- Error state is displayed when deletion fails
- Selection mode is cleaned up on success

**Severity:** Medium (test coverage gap)

---

## Positive Observations

1. **Good retry/resilience patterns**: The tenacity-decorated `extract_entities_with_retry` and `generate_embeddings_batch_with_retry` provide proper retry with exponential backoff. This is well-designed.

2. **Proper semantic deduplication pipeline**: The dedup step uses embeddings + union-find clustering, which is a solid approach. The 0.85 cosine threshold is reasonable.

3. **Clean frontend architecture**: The React Query hooks with smart polling (only poll when items are processing) avoid unnecessary network traffic. The type definitions in `kg.types.ts` are clean and match the API responses.

4. **Delete batch has proper orphan cleanup**: The `delete_batch` endpoint correctly collects connected entity IDs and performs a single batch orphan cleanup after all deletions, preventing unnecessary Neo4j scans.

5. **Entity type whitelist in `graph_preview.py`**: The `ALLOWED_ENTITY_TYPES` set prevents Cypher injection in the entity type filter. This is the right pattern.

6. **Idempotent batch processing**: Both `process_batch` and the Celery task check `kg_status == "ready"` before processing, preventing duplicate work.

7. **Firestore retry with exponential backoff in `_update_firestore_with_retry`**: The delete-batch endpoint properly handles the critical failure case where Neo4j deletion succeeds but Firestore update fails.

---

## Recommended Priority Order

1. **C3** — Fix sync Neo4j blocking the event loop (infrastructure fix, affects all async endpoints)
2. **C2** — Add transaction protection to `_store_in_neo4j` (data integrity)
3. **C1** — Convert to async Neo4j sessions (performance under concurrent load)
4. **H1 + H2** — Add entity type whitelist validation (security hardening)
5. **H3** — Enable concurrent batch processing (performance)
6. **M7** — Fix entity storage to include all extracted entities (data completeness)
7. **M1** — Add LLM call timeouts (resilience)
8. **M5** — Surface dedup failure in result (observability)
9. **H5** — Log raw LLM response on parse failure (debuggability)
10. **All other items** — Address in subsequent sprints

---

*Review completed by automated review agent on 2026-05-24. Only this review file was created; no source files were modified.*
