#!/usr/bin/env python3
# verify_phase_2.py
# Phase 2 verification script for AI Enablement components

# Verifies implementation of entity-aware chunker, LLM entity extractor,
# KnowledgeGraphProcessor integration, and retry logic without requiring
# live credentials. Uses code inspection and import validation.

# @see: services/entity_aware_chunker.py, services/llm_entity_extractor.py
# @note: Some checks verify code structure to avoid requiring live credentials

import sys
from pathlib import Path
import os

# Setup paths
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
os.chdir(project_root)


def check(name: str, func) -> bool:
    """Run a check and report result."""
    print(f"Checking: {name}...", end=" ")
    try:
        result = func()
        if result is True or result is None:
            print("PASS")
            return True
        else:
            print(f"FAIL: {result}")
            return False
    except Exception as e:
        print(f"FAIL: {e}")
        return False


def check_entity_aware_chunker():
    """Verify entity_aware_chunker.py exists and works."""
    from services.entity_aware_chunker import chunk_text_hierarchical

    chunks = chunk_text_hierarchical("# Test\n\nContent paragraph.", "test")
    if len(chunks) > 0:
        return True
    return "No chunks created"


def check_llm_entity_extractor():
    """Verify llm_entity_extractor.py imports correctly."""
    from services.llm_entity_extractor import extract_entities

    # Just verify import works - actual extraction requires credentials
    return True


def check_kg_processor_integration():
    """Verify KnowledgeGraphProcessor uses EntityAwareChunker."""
    # Read the code to avoid requiring Vertex AI credentials
    kg_processor_path = project_root / "api" / "kg_processor.py"
    content = kg_processor_path.read_text()

    checks = [
        ("EntityAwareChunker" in content, "Missing EntityAwareChunker import"),
        ("self.chunker" in content, "Missing self.chunker attribute"),
        ("entity_aware_chunker" in content, "Missing entity_aware_chunker module"),
    ]

    for condition, error in checks:
        if not condition:
            return error
    return True


def check_retry_logic():
    """Verify retry logic is implemented with tenacity."""
    kg_processor_path = project_root / "api" / "kg_processor.py"
    content = kg_processor_path.read_text()

    checks = [
        (
            "tenacity" in content or "from tenacity" in content,
            "Missing tenacity import",
        ),
        (
            "extract_entities_with_retry" in content,
            "Missing extract_entities_with_retry function",
        ),
    ]

    for condition, error in checks:
        if not condition:
            return error
    return True


def check_import_chain():
    """Verify all Phase 2 modules exist on disk."""
    modules = [
        ("api/kg_processor.py", "KnowledgeGraphProcessor module"),
        ("services/entity_aware_chunker.py", "EntityAwareChunker module"),
        ("services/llm_entity_extractor.py", "LLM Entity Extractor module"),
    ]

    for module_path, name in modules:
        full_path = project_root / module_path
        if not full_path.exists():
            return f"{name} not found at {module_path}"
    return True


def main():
    print("=" * 50)
    print("Phase 2 Verification")
    print("=" * 50)
    print()

    results = [
        check("entity_aware_chunker.py", check_entity_aware_chunker),
        check("llm_entity_extractor.py", check_llm_entity_extractor),
        check("KnowledgeGraphProcessor integration", check_kg_processor_integration),
        check("Retry logic", check_retry_logic),
        check("Import chain", check_import_chain),
    ]

    print()
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Result: {passed}/{total} checks passed")

    if all(results):
        print("Phase 2 COMPLETE")
        return 0
    else:
        print("Phase 2 INCOMPLETE - fix failing checks")
        return 1


if __name__ == "__main__":
    sys.exit(main())
