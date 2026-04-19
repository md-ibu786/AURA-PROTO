# Phase: Audio-to-Notes Pipeline LLM Configuration

**Researched:** 2026-04-19
**Domain:** Audio processing pipeline configuration (Refinement & Summarization services)
**Confidence:** HIGH

## Summary

This research documents the implementation approach for making the audio-to-notes pipeline's **refinement** and **summarization** services configurable via the Settings page. Currently, summarization is already backend-configurable but not exposed in the frontend, while refinement (coc.py) uses a hardcoded model and needs to be migrated to the configurable pattern.

**Primary recommendation:** Follow the existing patterns in `summarizer.py` and `llm_entity_extractor.py`—add use cases to the frontend type definitions and UI, then migrate coc.py from hardcoded `get_model()` to `resolve_use_case_config()` + `get_default_router().generate()` pattern.

---

## Current State Analysis

### Frontend (Type Definitions)
**File:** `frontend/src/types/settings.ts` [VERIFIED: codebase]

```typescript
export type UseCase = 'chat' | 'embeddings' | 'entity_extraction' | 'gatekeeper' | 'relationship_extraction';
```

**Gap:** Missing `'refinement'` and `'summarization'` use cases.

### Frontend (UI Configuration)
**File:** `frontend/src/features/settings/components/DefaultModelSection.tsx` [VERIFIED: codebase]

```typescript
const USE_CASES: { id: UseCase; label: string; description: string }[] = [
    { id: 'chat', label: 'Chat Model', description: 'Used for conversational responses and RAG' },
    { id: 'embeddings', label: 'Embeddings Model', description: 'Used for document indexing and vector search' },
    { id: 'entity_extraction', label: 'Entity Extraction Model', description: 'Used for building knowledge graphs from documents' },
    { id: 'gatekeeper', label: 'Gatekeeper Model', description: 'Used for query validation and access control' },
    { id: 'relationship_extraction', label: 'Relationship Extraction Model', description: 'Used for extracting relationships between entities in documents' }
];

const USE_CASE_MODEL_TYPES: Record<UseCase, 'generation' | 'embedding'> = {
    chat: 'generation',
    embeddings: 'embedding',
    entity_extraction: 'generation',
    gatekeeper: 'generation',
    relationship_extraction: 'generation',
};
```

**Gap:** Missing entries for `refinement` and `summarization`.

### Backend (Refinement Service - Needs Migration)
**File:** `services/coc.py` (Chain of Custody) [VERIFIED: codebase]

**Current implementation (line 96):**
```python
model = get_model(model_name="models/gemini-2.5-pro")
```

**Pattern to migrate to:**
- Import `get_default_router` and `resolve_use_case_config` from `model_router`
- Replace hardcoded model with runtime config resolution
- Use `router.generate()` with provider/model from config

### Backend (Summarization Service - Already Configurable)
**File:** `services/summarizer.py` [VERIFIED: codebase]

**Already correctly implemented (lines 35, 43, 101-111):**
```python
from model_router import get_default_router, resolve_use_case_config

def generate_university_notes(topic: str, cleaned_transcript: str) -> str:
    cfg = resolve_use_case_config("summarization")
    router = get_default_router()
    response = _run_sync(
        router.generate(
            model=cfg["model"],
            contents=note_taking_prompt,
            provider=cfg["provider"],
            temperature=1.0,
            top_p=0.95,
            max_output_tokens=32000,
        )
    )
```

**Status:** Backend already supports `summarization` use case—only frontend exposure needed.

---

## Standard Stack (No Changes Required)

This phase uses existing project patterns:

| Pattern | Location | Status |
|---------|----------|--------|
| `resolve_use_case_config()` | `model_router` module | Already exists |
| `get_default_router()` | `model_router` module | Already exists |
| `UseCase` type | `frontend/src/types/settings.ts` | Needs extension |
| `USE_CASES` array | `DefaultModelSection.tsx` | Needs extension |

---

## Architecture Patterns

### Pattern 1: Backend Config Migration (for coc.py)

**Source:** `services/llm_entity_extractor.py` lines 458-473 [VERIFIED: codebase]

```python
from model_router import get_default_router, resolve_use_case_config

# Resolve provider/model from SettingsStore at call time
cfg = resolve_use_case_config("refinement")  # Use case name
router = get_default_router()

# Generate response via ModelRouter with explicit provider
response = await router.generate(
    model=cfg["model"],
    contents=prompt,
    provider=cfg["provider"],
    temperature=0.0,  # Deterministic for refinement
    max_output_tokens=32000,
)
```

**Key differences from current coc.py:**
1. Replace `get_model()` with `resolve_use_case_config()` + `get_default_router()`
2. Remove hardcoded model name
3. Use `router.generate()` instead of `generate_content()`
4. Call-time resolution ensures fresh config per request

### Pattern 2: Frontend Type Extension

**Source:** `frontend/src/types/settings.ts` [VERIFIED: codebase]

```typescript
export type UseCase = 'chat' | 'embeddings' | 'entity_extraction' | 'gatekeeper' | 'relationship_extraction' | 'refinement' | 'summarization';
```

### Pattern 3: Frontend UI Extension

**Source:** `frontend/src/features/settings/components/DefaultModelSection.tsx` [VERIFIED: codebase]

**USE_CASES array entries to add:**
```typescript
{ id: 'refinement', label: 'Refinement Model', description: 'Used for transcript cleaning and academic formatting' },
{ id: 'summarization', label: 'Summarization Model', description: 'Used for generating structured university-grade notes' }
```

**USE_CASE_MODEL_TYPES entries to add:**
```typescript
refinement: 'generation',
summarization: 'generation',
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| LLM routing | Custom model selection logic | `resolve_use_case_config()` + `get_default_router()` | Centralized config, runtime updates, provider-agnostic |
| Model initialization | Direct `get_model()` calls | Router pattern with call-time resolution | Allows live config changes without restart |

---

## Common Pitfalls

### Pitfall 1: Import Path Errors
**What goes wrong:** Using wrong import path for `model_router`
**Why it happens:** The `model_router` package location isn't obvious from the codebase
**How to avoid:** Use the exact pattern from existing files:
```python
from model_router import get_default_router, resolve_use_case_config
```

### Pitfall 2: Async/Sync Mismatch
**What goes wrong:** `coc.py` uses synchronous `generate_content()` but router pattern is async
**Why it happens:** `llm_entity_extractor.py` uses `await router.generate()`, `summarizer.py` uses `_run_sync()` wrapper
**How to avoid:** Follow `summarizer.py` pattern—use `_run_sync()` from `model_router.compat` for synchronous contexts:
```python
from model_router.compat import _run_sync

response = _run_sync(router.generate(...))
```

### Pitfall 3: Missing Model Type
**What goes wrong:** Adding use case but not updating `USE_CASE_MODEL_TYPES`
**Why it happens:** Frontend filters models by type ('generation' vs 'embedding')
**How to avoid:** Always add entry to both `USE_CASES` and `USE_CASE_MODEL_TYPES`—both are required.

---

## File Change Checklist

### Frontend Changes

| # | File | Change | Line(s) |
|---|------|--------|---------|
| 1 | `frontend/src/types/settings.ts` | Add `'refinement' \| 'summarization'` to UseCase type | Line 32 |
| 2 | `frontend/src/features/settings/components/DefaultModelSection.tsx` | Add refinement entry to USE_CASES array | After line 51 |
| 3 | `frontend/src/features/settings/components/DefaultModelSection.tsx` | Add summarization entry to USE_CASES array | After line 51 |
| 4 | `frontend/src/features/settings/components/DefaultModelSection.tsx` | Add `refinement: 'generation'` to USE_CASE_MODEL_TYPES | After line 59 |
| 5 | `frontend/src/features/settings/components/DefaultModelSection.tsx` | Add `summarization: 'generation'` to USE_CASE_MODEL_TYPES | After line 59 |

### Backend Changes

| # | File | Change | Line(s) |
|---|------|--------|---------|
| 6 | `services/coc.py` | Add import: `from model_router import get_default_router, resolve_use_case_config` | After line 39 |
| 7 | `services/coc.py` | Add import: `from model_router.compat import _run_sync` | After line 39 |
| 8 | `services/coc.py` | Replace `model = get_model(...)` with config resolution | Line 96 |
| 9 | `services/coc.py` | Replace `generate_content()` calls with `router.generate()` pattern | Lines 144-148, 223-227 |

### Verification Steps

- [ ] Frontend type check passes: `cd frontend && npm run build`
- [ ] Backend tests pass: `pytest services/test_coc.py` (if exists) or general suite
- [ ] Settings page shows new use cases in dropdown
- [ ] Config changes persist and are read by backend services

---

## Integration Considerations

### ModelRouter Integration
The project uses a centralized `model_router` package (imported from `model_router`) that:
- Resolves use case configs from SettingsStore at runtime
- Routes to appropriate provider (vertex_ai, openrouter, ollama)
- Provides `_run_sync()` helper for sync contexts

### Temperature Settings
Different use cases have different temperature requirements:
- **Refinement:** Uses `temperature=0.0` for deterministic output
- **Summarization:** Uses `temperature=1.0, top_p=0.95` for creative but structured output
- These are hardcoded per use case, not configurable via settings

### Existing Test Coverage
**File:** `api/tests/test_consumer_wiring.py` [VERIFIED: codebase]

Tests already verify that `summarization` use case resolves correctly via `resolve_use_case_config()`. Similar test coverage should be added for `refinement` after migration.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `model_router` package is available at runtime | Architecture Patterns | Import errors would occur if package path differs |
| A2 | `refinement` use case string is not already used elsewhere | File Change Checklist | Would cause conflicts if already defined |
| A3 | Both services require 'generation' model type | Pattern 3 | UI would filter incorrectly if embedding type needed |

---

## Sources

### Primary (HIGH confidence)
- `frontend/src/types/settings.ts` - UseCase type definition
- `frontend/src/features/settings/components/DefaultModelSection.tsx` - UI configuration patterns
- `services/summarizer.py` - Reference implementation for summarization use case
- `services/coc.py` - Current hardcoded implementation to migrate
- `services/llm_entity_extractor.py` - Reference pattern for router.generate() usage
- `api/tests/test_consumer_wiring.py` - Verification of existing use case patterns

### Secondary (MEDIUM confidence)
- `services/vertex_ai_client.py` - Shows model_router import patterns

---

## Metadata

**Research date:** 2026-04-19
**Valid until:** 2026-05-19 (30 days for stable configuration patterns)
**Confidence breakdown:**
- Standard stack: HIGH - Existing patterns verified in 4+ files
- Architecture: HIGH - Clear migration path from hardcoded to configurable
- Pitfalls: MEDIUM - Based on code analysis, runtime testing needed

**Next step:** Proceed with PLAN.md creation using the File Change Checklist above.
