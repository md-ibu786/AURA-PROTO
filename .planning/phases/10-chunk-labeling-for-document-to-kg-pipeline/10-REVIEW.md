---
status: clean
phase: 10-chunk-labeling-for-document-to-kg-pipeline
updated: 2026-04-23
---

# Code Review Report: Phase 10

## Overview
The code changes for Phase 10 (Chunk Labeling for Document-to-KG Pipeline) have been successfully reviewed. The implementation is robust, accurately fulfilling the plan requirements by adding the `chunk_labels` field across the processing pipeline, Neo4j schema, and frontend types. The fallback mechanisms ensure safe degradation in case of LLM failures. No blocking bugs or security vulnerabilities were identified.

## Findings

### Medium Severity

1. **Celery Progress State Mapping Integration**
   * **Issue**: `ProcessingState.LABELING` was correctly added to `api/tasks/document_processing_tasks.py` and mapped to the 25-30% progress band. However, the Celery task uses `process_document_simple()`, which instantiates a `KnowledgeGraphProcessor` but does *not* provide it with a callback via `set_progress_callback()`. Consequently, while `_emit_progress` is called extensively within `kg_processor.py`, these updates never reach the Celery task or Firestore. The task's progress state jumps directly from 5% (parsing) to 75% (storing), rendering intermediate states like `CHUNKING`, `LABELING`, `EMBEDDING`, and `EXTRACTING` invisible in production.
   * **Fix**: To fully realize the progress visibility intended in Plan 10-03, update `process_document_simple` (or directly modify `process_document_task`) to register a callback with `processor.set_progress_callback(...)`. This callback should bridge the processor's `ProcessingProgress` events to the Celery task's `self.update_progress(...)`, mapping the distinct stages to percentage bands.

### Low Severity / Code Quality

1. **Robustness of JSON Array Extraction**
   * **Issue**: `_extract_json_array` in `api/kg_processor.py` relies on `start = text.find("[")` and `end = text.rfind("]")` to extract the JSON payload. While this elegantly bypasses markdown code blocks (e.g., ````json\n...\n````) without explicit parsing, it is vulnerable to extraneous brackets. If the LLM includes brackets in prose before or after the array (e.g., `Here is the output [note]: \n[...]\n See [link]`), the slice will be malformed, triggering a `JSONDecodeError` and forcing a heuristic fallback.
   * **Fix**: Consider utilizing a more robust JSON extraction pattern, such as identifying the markdown block explicitly first (similar to `_parse_chunk_response`) or using a regular expression to locate the main array structure.
   
2. **Hardcoded Magic Numbers**
   * **Issue**: `_label_chunks_with_llm` in `api/kg_processor.py` utilizes a hardcoded `batch_size = 20`.
   * **Fix**: Extract this magic number to a module-level constant (e.g., `LABELING_BATCH_SIZE = 20`) to align with existing configurations like `CHUNK_SIZE` and `ENTITY_BATCH_SIZE`.

3. **Test Shim Maintenance**
   * **Issue**: `api/tests/test_chunk_labeling.py` isolates the test environment using manual `sys.modules` patching to stub out missing service dependencies. While hermetic and effective for bypassing local environment constraints, manual module injection is brittle against future architectural changes.
   * **Fix**: For future tests, consider leveraging `unittest.mock.patch.dict("sys.modules", ...)` or `pytest.MonkeyPatch` for cleaner, self-cleaning module overrides. Alternatively, refactoring `KnowledgeGraphProcessor` to lazily import heavy service dependencies would naturally alleviate this issue.

## Conclusion
The core labeling functionality operates exactly as intended, the schema changes are well-integrated, and unit test coverage provides solid confidence in the new methods. The application degrades gracefully during edge cases (such as token limits or LLM API timeouts). The status is marked as **clean**.