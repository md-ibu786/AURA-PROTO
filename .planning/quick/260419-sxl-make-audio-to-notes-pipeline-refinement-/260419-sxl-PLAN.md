# PLAN: Audio-to-Notes Pipeline LLM Configuration

**Created:** 2026-04-19
**Scope:** Make refinement & summarization LLM services configurable via Settings page

---

## Task 1: Extend Frontend UseCase Type & UI

**Files:**
- `frontend/src/types/settings.ts` (line 32)
- `frontend/src/features/settings/components/DefaultModelSection.tsx` (lines 46-60)

**Changes:**

1. In `settings.ts`, extend the UseCase union:
```typescript
export type UseCase = 'chat' | 'embeddings' | 'entity_extraction' | 'gatekeeper' | 'relationship_extraction' | 'refinement' | 'summarization';
```

2. In `DefaultModelSection.tsx`, add two entries to `USE_CASES` array (before the closing `]` on line 52):
```typescript
{ id: 'refinement', label: 'Refinement Model', description: 'Used for transcript cleaning and academic formatting' },
{ id: 'summarization', label: 'Summarization Model', description: 'Used for generating structured university-grade notes' }
```

3. In `DefaultModelSection.tsx`, add two entries to `USE_CASE_MODEL_TYPES` (before the closing `}` on line 60):
```typescript
refinement: 'generation',
summarization: 'generation',
```

**Verification:** `cd frontend && npm run build` — type check must pass with zero errors.

---

## Task 2: Migrate coc.py from Hardcoded Model to Configurable Router

**File:** `services/coc.py`

**Changes:**

1. **Update imports** (lines 34-39) — replace `get_model` with router imports:
```python
from services.vertex_ai_client import (
    GenerationConfig,
    block_none_safety_settings,
)
from model_router import get_default_router, resolve_use_case_config
from model_router.compat import _run_sync
```

2. **Replace hardcoded model** (line 96) — remove `model = get_model(...)` and add config resolution at the start of `transform_transcript()`:
```python
cfg = resolve_use_case_config("refinement")
```

3. **Replace first `generate_content()` call** (lines 144-149) — transformation phase:
```python
router = get_default_router()
response = _run_sync(
    router.generate(
        model=cfg["model"],
        contents=prompt,
        provider=cfg["provider"],
        temperature=0.0,
        max_output_tokens=32000,
    )
)
```
Note: `block_none_safety_settings()` is no longer needed since the router handles safety settings internally. The response object from `router.generate()` has a `.text` attribute, so the downstream `getattr(response, "text", None)` logic still works.

4. **Replace second `generate_content()` call** (lines 222-228) — audit phase:
```python
audit_response = _run_sync(
    router.generate(
        model=cfg["model"],
        contents=audit_prompt,
        provider=cfg["provider"],
        temperature=0.0,
        max_output_tokens=32000,
    )
)
```

**Verification:** Backend tests pass with `pytest`. The `resolve_use_case_config("refinement")` call must resolve correctly (the model_router package already supports arbitrary use case strings).

---

## Task 3: Verify Full Integration

**Steps:**
1. Run `cd frontend && npm run build` — confirm zero type errors
2. Run backend tests: `pytest` from project root with venv activated
3. If `api/tests/test_consumer_wiring.py` exists, verify it passes (existing test for `summarization` use case pattern)

---

## Summary

| # | Task | Files | Risk |
|---|------|-------|------|
| 1 | Extend UseCase type & UI | `settings.ts`, `DefaultModelSection.tsx` | LOW — additive type union + UI entries |
| 2 | Migrate coc.py to router pattern | `services/coc.py` | MEDIUM — replacing sync `generate_content()` with `_run_sync(router.generate())` |
| 3 | Verify integration | N/A | LOW — build + test checks |

**Total scope:** 3 files modified, 0 files created.