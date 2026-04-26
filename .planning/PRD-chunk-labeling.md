# PRD: Chunk Labeling for AURA-NOTES-MANAGER Document-to-KG Pipeline

## Document Information
- **Status**: FINAL (Approved for Implementation)
- **Scope**: Backend (Document Processor -> Neo4j Schema)
- **Classification**: Production-grade, one-shot implementation
- **Pre-requisite**: Neo4j database wipe + document re-upload via updated pipeline
- **Related PRD**: AURA-CHAT/.planning/PRD-granular-citations.md (citation logic consumes these labels)

---

## 1. Executive Summary

### 1.1 The Problem
AURA-NOTES-MANAGER processes documents into Neo4j knowledge graphs but stores chunks without human-readable topic labels. When AURA-CHAT (the RAG chat interface) retrieves chunks for citation, it cannot display meaningful chunk labels to users. The chunks are anonymous text blobs — users cannot quickly identify which chunk covers "Zeroth Law" versus "First Law" without reading the full text.

### 1.2 The Vision
Every chunk stored in Neo4j must have an AI-generated `label` field containing a concise 3-5 word topic description. When AURA-CHAT retrieves these chunks, it can display meaningful labels in the citation panel (e.g., `[1] Zeroth law`, `[2] First law`), enabling users to verify sources at a glance.

### 1.3 Key Principles
1. **One-shot labeling**: Labels are generated once during document ingestion and stored permanently in Neo4j.
2. **AI-generated, not heuristic**: LLM batch labeling produces accurate semantic summaries. Heuristic fallback exists but is not the primary path.
3. **Child chunks only**: Parent chunks exist for context expansion but are never directly cited or labeled.
4. **Pipeline resilience**: If LLM labeling fails, the document still processes successfully with heuristic fallback labels.
5. **Cross-repo consistency**: The labeling approach mirrors AURA-CHAT exactly, ensuring both repos produce interchangeable chunk data.

---

## 2. Architecture Overview

### 2.1 Current Pipeline (Before)

```
Document Upload
    |
    v
Text Extraction (PDF/DOCX/TXT)
    |
    v
Chunking (EntityAwareChunker or Hierarchical)
    |
    v
Embedding Generation
    |
    v
Entity Extraction
    |
    v
Neo4j Storage (Chunk nodes: id, text, index, embedding)
```

**Chunk node in Neo4j**:
```cypher
(c:Chunk {id: "chunk_doc1_0", text: "AI is at the heart...", index: 0, embedding: [...]})
```

### 2.2 Target Pipeline (After)

```
Document Upload
    |
    v
Text Extraction (PDF/DOCX/TXT)
    |
    v
Chunking (EntityAwareChunker or Hierarchical)
    |
    v
Label Generation (Batch LLM call)
    |
    v
Embedding Generation
    |
    v
Entity Extraction
    |
    v
Neo4j Storage (Chunk nodes: id, text, label, index, embedding)
```

**Chunk node in Neo4j**:
```cypher
(c:Chunk {id: "chunk_doc1_0", text: "AI is at the heart...", label: "AI in Industry 4.0", index: 0, embedding: [...]})
```

---

## 3. Backend Changes

### 3.1 Phase 1: Chunk Dataclass Update

**File**: `api/kg_processor.py`

**Current `Chunk` dataclass** (line 321-331):
```python
@dataclass
class Chunk:
    """Represents a text chunk with embedding."""
    id: str
    text: str
    index: int
    token_count: int
    embedding: Optional[List[float]] = None
    entities: List[Entity] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
```

**New `Chunk` dataclass**:
```python
@dataclass
class Chunk:
    """Represents a text chunk with embedding and topic label."""
    id: str
    text: str
    index: int
    token_count: int
    embedding: Optional[List[float]] = None
    entities: List[Entity] = field(default_factory=list)
    properties: Dict[str, Any] = field(default_factory=dict)
    label: Optional[str] = None   # NEW: AI-generated topic label
```

**Why add `label` here?** The `Chunk` dataclass is the canonical representation throughout the pipeline. Adding `label` at this level ensures it flows naturally from chunking → labeling → embedding → Neo4j insertion.

---

### 3.2 Phase 2: Label Generation Logic

**File**: `api/kg_processor.py`

**Where to insert**: After chunking (line ~1045), before embedding generation (line ~1051).

**New method**:
```python
async def _generate_chunk_labels(self, chunks: List[Chunk]) -> None:
    """Generate AI labels for chunks in-place using batch LLM call."""
    if not chunks:
        return
    
    # Extract chunk texts
    chunk_texts = [c.text for c in chunks]
    
    # Generate labels via batch LLM call
    labels = await self._label_chunks_with_llm(chunk_texts)
    
    # Apply labels to chunks
    for chunk, label in zip(chunks, labels):
        chunk.label = label
    
    logger.info(f"Generated labels for {len(chunks)} chunks")

async def _label_chunks_with_llm(self, chunk_texts: List[str]) -> List[str]:
    """Call LLM to generate topic labels for a batch of chunk texts."""
    if not chunk_texts:
        return []
    
    # Batch size limit: max 20 chunks per call
    BATCH_SIZE = 20
    all_labels = []
    
    for i in range(0, len(chunk_texts), BATCH_SIZE):
        batch = chunk_texts[i:i + BATCH_SIZE]
        batch_labels = await self._label_single_batch(batch)
        all_labels.extend(batch_labels)
    
    return all_labels

async def _label_single_batch(self, chunk_texts: List[str]) -> List[str]:
    """Generate labels for a single batch of chunks (max 20)."""
    # Build prompt with truncated excerpts
    excerpts = []
    for idx, text in enumerate(chunk_texts, 1):
        truncated = text[:200]  # Truncate to 200 chars to prevent token overflow
        excerpts.append(f"Excerpt {idx}: \"{truncated}\"")
    
    prompt = f"""You are labeling excerpts from an academic document.
For each excerpt below, generate a concise 3-5 word topic label.
Respond ONLY as a JSON array of strings in the same order as the excerpts.

{"\\n".join(excerpts)}

Expected output format:
["Label 1", "Label 2", "Label 3"]
"""
    
    try:
        # Use the existing Gemini client
        model = get_model()
        response = model.generate_content(prompt)
        response_text = response.text if hasattr(response, "text") else str(response)
        
        # Extract JSON array from response
        labels = self._extract_json_array(response_text)
        
        # Validate label count matches chunk count
        if len(labels) != len(chunk_texts):
            logger.warning(
                f"Label mismatch: expected {len(chunk_texts)}, got {len(labels)}. "
                "Falling back to heuristic labels."
            )
            return [self._heuristic_label(text) for text in chunk_texts]
        
        # Validate each label is a non-empty string
        valid_labels = []
        for label, text in zip(labels, chunk_texts):
            if isinstance(label, str) and label.strip():
                valid_labels.append(label.strip())
            else:
                valid_labels.append(self._heuristic_label(text))
        
        return valid_labels
        
    except Exception as e:
        logger.warning(f"LLM label generation failed: {e}. Falling back to heuristic.")
        return [self._heuristic_label(text) for text in chunk_texts]

def _extract_json_array(self, text: str) -> List[str]:
    """Extract JSON array from LLM response text."""
    import json
    
    # Try to find JSON array in the text
    start = text.find("[")
    end = text.rfind("]")
    
    if start == -1 or end == -1 or end <= start:
        return []
    
    try:
        return json.loads(text[start:end+1])
    except json.JSONDecodeError:
        return []

def _heuristic_label(self, text: str) -> str:
    """Generate a fallback label from the first sentence of the text."""
    first_sentence = text.split(".")[0].strip()
    return (first_sentence[:60] + "...") if len(first_sentence) > 60 else first_sentence
```

**Integration into `process_document`**:

Insert label generation call after chunk creation:
```python
# After line 1045 (result["chunk_count"] = len(chunks))
# Before line 1047 (self._emit_progress("embeddings", ...))

# Generate chunk labels (NEW)
await self._generate_chunk_labels(chunks)
```

---

### 3.3 Phase 3: Neo4j Schema Update

**File**: `api/kg_processor.py`

**Current `_create_chunk_node` method** (line 3515-3534):
```python
async def _create_chunk_node(self, session, chunk: Chunk, module_id: str):
    """Create Chunk node with embedding and module_id."""
    query = """
    MERGE (c:Chunk {id: $id})
    SET c.text = $text,
        c.token_count = $token_count,
        c.index = $index,
        c.module_id = $module_id,
        c.embedding = $embedding
    RETURN c.id
    """
    params = {
        "id": chunk.id,
        "text": chunk.text[:10000],
        "token_count": chunk.token_count,
        "index": chunk.index,
        "module_id": module_id,
        "embedding": chunk.embedding,
    }
    session.run(query, params)
```

**New `_create_chunk_node` method**:
```python
async def _create_chunk_node(self, session, chunk: Chunk, module_id: str):
    """Create Chunk node with embedding, label, and module_id."""
    query = """
    MERGE (c:Chunk {id: $id})
    SET c.text = $text,
        c.label = $label,
        c.token_count = $token_count,
        c.index = $index,
        c.module_id = $module_id,
        c.embedding = $embedding
    RETURN c.id
    """
    params = {
        "id": chunk.id,
        "text": chunk.text[:10000],
        "label": chunk.label or "",  # NEW: Store label (empty string if None)
        "token_count": chunk.token_count,
        "index": chunk.index,
        "module_id": module_id,
        "embedding": chunk.embedding,
    }
    session.run(query, params)
```

**Why store empty string for missing labels?** Neo4j properties with empty string are queryable (unlike null/missing properties), making it easier to identify unlabeled chunks during debugging.

---

### 3.4 Phase 4: Data Wipe and Re-upload

**Action**: Wipe Neo4j and re-upload all documents.

```bash
# Run the wipe script (if available) or manually clear chunks
python scripts/wipe_graph.py  # Or equivalent for NOTES-MANAGER
```

**Why wipe?**
- Existing Chunk nodes have no `label` property.
- Unlike AURA-CHAT, NOTES-MANAGER does not have a standalone wipe script. You may need to run a Cypher query:
  ```cypher
  MATCH (c:Chunk) SET c.label = ""
  ```
  However, this leaves all existing chunks unlabeled. A full wipe and re-upload is cleaner.

**Alternative (if wipe is not feasible)**:
Run a backfill script that queries all Chunk nodes, extracts first sentences, and sets `label`:
```python
# One-time backfill script
with neo4j_driver.session() as session:
    result = session.run("MATCH (c:Chunk) WHERE c.label IS NULL RETURN c.id, c.text")
    for record in result:
        text = record["c.text"]
        label = text.split(".")[0][:60]
        session.run(
            "MATCH (c:Chunk {id: $id}) SET c.label = $label",
            {"id": record["c.id"], "label": label}
        )
```

**Recommendation**: For production consistency, prefer a full wipe + re-upload. For staging/development, the backfill script is acceptable.

---

## 4. Files Modified

| File | Changes |
|------|---------|
| `api/kg_processor.py` | Add `label` field to `Chunk` dataclass; add `_generate_chunk_labels`, `_label_chunks_with_llm`, `_label_single_batch`, `_extract_json_array`, `_heuristic_label` methods; update `_create_chunk_node` Cypher query |

---

## 5. Testing Strategy

### 5.1 Unit Tests

**Test 1: Label generation with mock LLM**
- Mock `get_model().generate_content()` to return a JSON array.
- Verify chunks receive correct labels.
- Verify label count matches chunk count.

**Test 2: LLM mismatch fallback**
- Mock LLM to return fewer labels than chunks.
- Verify fallback to heuristic labels.

**Test 3: LLM failure fallback**
- Mock LLM to raise an exception.
- Verify chunks still get heuristic labels and processing completes.

**Test 4: Neo4j node creation**
- Create a Chunk with a label.
- Verify `_create_chunk_node` stores the label in Neo4j.
- Query Neo4j and assert `c.label` equals the expected value.

### 5.2 Integration Tests

**Test 5: End-to-end document processing**
- Upload a test PDF.
- Verify all created Chunk nodes have non-empty `label` properties.
- Verify labels are semantically relevant (spot-check manually or with embedding similarity).

---

## 6. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| LLM label generation adds latency to document processing | Upload takes longer | Batch processing (20 chunks/call) minimizes calls; async execution prevents blocking |
| LLM costs increase with batch labeling | Higher API bills | Batch size limit (20) + excerpt truncation (200 chars) keeps token count low |
| Labels are inconsistent across similar chunks | User confusion | This is acceptable — labels are hints, not strict categories |
| Existing chunks without labels break AURA-CHAT queries | Missing label field | Backfill script or full wipe ensures all chunks have labels |

---

## 7. Cross-Repo Alignment

This PRD is the **companion** to `AURA-CHAT/.planning/PRD-granular-citations.md`. Both repos must produce chunks with the same schema:

| Property | AURA-CHAT | AURA-NOTES-MANAGER |
|----------|-----------|-------------------|
| `id` | `chunk_{doc_id}_{index}` | `chunk_{doc_id}_{index}` |
| `text` | Chunk text | Chunk text |
| `label` | AI-generated or heuristic | AI-generated or heuristic |
| `index` | Numeric position | Numeric position |
| `embedding` | 768-dim vector | 768-dim vector |

**If both repos write to the same Neo4j instance**, their Chunk nodes must have identical property names. This PRD ensures `label` exists on both.

---

*End of PRD*
