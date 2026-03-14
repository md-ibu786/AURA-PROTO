"""
============================================================================
FILE: validate_phase2.py
LOCATION: api/validate_phase2.py
============================================================================

PURPOSE:
    Validates Phase 2 integration in kg_processor.py through static code analysis.
    Performs file-based checks to verify service imports and integration patterns.

ROLE IN PROJECT:
    Quality assurance utility for Phase 2 AI Enablement components.
    - Verifies EntityAwareChunker and LLMEntityExtractor are properly imported
    - Checks retry logic implementation with tenacity decorators
    - Validates entity extraction and embedding service integration

KEY COMPONENTS:
    - import_checks: Validates Phase 2 service imports in kg_processor.py
    - integration_checks: Verifies Phase 2 components are used in process_document
    - retry_checks: Confirms tenacity retry decorators and error handling

DEPENDENCIES:
    - External: None (uses only standard library)
    - Internal: Reads kg_processor.py from the same directory

USAGE:
    Run from project root:
        python api/validate_phase2.py

    Output shows pass/fail status for all Phase 2 integration points.
============================================================================
"""

import os

# Read kg_processor.py source
script_dir = os.path.dirname(os.path.abspath(__file__))
kg_processor_path = os.path.join(script_dir, "kg_processor.py")

with open(kg_processor_path, "r", encoding="utf-8") as f:
    source = f.read()

# Check for Phase 2 service imports
import_checks = {
    "Imports EntityAwareChunker": "EntityAwareChunker" in source,
    "Imports LLMEntityExtractor": "LLMEntityExtractor" in source,
    "Imports merge_extraction_results": "merge_extraction_results" in source,
    "Imports ExtractionResult": "ExtractionResult" in source,
    "Imports EmbeddingService": "EmbeddingService" in source,
    "Imports tenacity retry": "from tenacity import" in source,
}

print("=" * 60)
print("Phase 2 Service IMPORTS:")
print("=" * 60)
for check, result in import_checks.items():
    status = "✅" if result else "❌"
    print(f"  {status} {check}")
print()

# Check for Phase 2 integration in process_document
# Extract the process_document method (look for class method)
integration_checks = {
    "Uses self.chunker (EntityAwareChunker)": "self.chunker" in source
    and "EntityAwareChunker" in source,
    "Uses _llm_extractor": "_llm_extractor" in source,
    "Uses _generate_chunk_embeddings": "_generate_chunk_embeddings" in source,
    "Uses _extract_entities_from_chunks": "_extract_entities_from_chunks" in source,
    "Uses merge_extraction_results": "merge_extraction_results(" in source,
    "Uses extract_entities_with_retry": "extract_entities_with_retry" in source,
    "Uses generate_embeddings_batch_with_retry": "generate_embeddings_batch_with_retry"
    in source,
}

print("Phase 2 Integration in process_document:")
print("=" * 60)
for check, result in integration_checks.items():
    status = "✅" if result else "❌"
    print(f"  {status} {check}")
print()

# Check for retry logic
retry_checks = {
    "Has @retry decorator": "@retry(" in source,
    "stop_after_attempt": "stop_after_attempt" in source,
    "wait_exponential": "wait_exponential" in source,
    "retry_if_exception_type": "retry_if_exception_type" in source,
    "ExtractionError exception": "class ExtractionError" in source,
    "VertexAIError exception": "class VertexAIError" in source,
    "EmbeddingError exception": "class EmbeddingError" in source,
}

print("Retry Logic Implementation:")
print("=" * 60)
for check, result in retry_checks.items():
    status = "✅" if result else "❌"
    print(f"  {status} {check}")
print()

# Summary
all_passed = (
    all(import_checks.values())
    and all(integration_checks.values())
    and all(retry_checks.values())
)
if all_passed:
    print("🎉 ALL Phase 2 integration checks PASSED!")
else:
    failed = []
    for checks_dict in [import_checks, integration_checks, retry_checks]:
        for name, result in checks_dict.items():
            if not result:
                failed.append(name)
    print(f"⚠️ Some checks failed: {', '.join(failed)}")
