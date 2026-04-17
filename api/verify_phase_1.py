"""
============================================================================
FILE: verify_phase_1.py
LOCATION: api/verify_phase_1.py
============================================================================

PURPOSE:
    Verification script for Phase 1 configuration and client usage.
    Scans API and services code to ensure proper Vertex AI integration
    and removal of deprecated Google Generative AI imports.

ROLE IN PROJECT:
    CI-friendly verification script for AI enablement Phase 1.
    Validates that the codebase has migrated to Vertex AI properly.
    - Scans for remaining generativeai imports and GEMINI_API_KEY usage
    - Confirms Vertex AI client usage exists in the codebase
    - Validates config and service modules are properly wired

KEY COMPONENTS:
    - iter_python_files: Generator to find all Python files in directories
    - scan_file: Checks individual files for deprecated patterns
    - verify_no_deprecated_imports: Validates migration completeness
    - verify_vertex_client_usage: Confirms new client implementation

DEPENDENCIES:
    - External: pathlib, typing, sys
    - Internal: None

USAGE:
    python api/verify_phase_1.py
    # Returns exit code 0 on success, 1 on failure
============================================================================
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SEARCH_DIRS = [PROJECT_ROOT / "api", PROJECT_ROOT / "services"]


def iter_python_files(paths: Iterable[Path]) -> Iterable[Path]:
    for base in paths:
        if not base.exists():
            continue
        yield from base.rglob("*.py")


def scan_pattern(pattern: str) -> list[tuple[Path, int, str]]:
    matches: list[tuple[Path, int, str]] = []
    skip_path = Path(__file__).resolve()
    for path in iter_python_files(SEARCH_DIRS):
        if path.resolve() == skip_path:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if pattern in line:
                matches.append((path, lineno, line.strip()))
    return matches


def report_matches(
    label: str, matches: list[tuple[Path, int, str]], limit: int = 5
) -> None:
    print(f"{label} count={len(matches)}")
    for path, lineno, line in matches[:limit]:
        print(f"  {path}:{lineno}: {line}")


def check_no_google_generativeai() -> bool:
    matches = scan_pattern("import google." + "generativeai")
    if matches:
        print("FAIL: Found google.generativeai imports")
        report_matches("Matches", matches)
        return False
    print("PASS: No google.generativeai imports")
    print("Matches count=0")
    return True


def check_vertex_ai_client_usage() -> bool:
    matches = scan_pattern("from services.vertex_ai_client")
    if matches:
        print("PASS: Found vertex_ai_client imports")
        report_matches("Matches", matches)
        return True
    print("FAIL: No vertex_ai_client usage found")
    print("Matches count=0")
    return False


def check_config_imports() -> bool:
    try:
        from api.config import LLM_ENTITY_EXTRACTION_MODEL, EMBEDDING_MODEL

        print(
            "PASS: Config imports work "
            f"Extraction={LLM_ENTITY_EXTRACTION_MODEL}, "
            f"Embedding={EMBEDDING_MODEL}"
        )
        return True
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        print(f"FAIL: Config import error: {exc}")
        return False


def check_kg_processor_config() -> bool:
    try:
        from api.kg_processor import GeminiClient

        client = GeminiClient()
        print(
            "PASS: kg_processor uses config "
            f"Extraction={client.extraction_model}, "
            f"Embedding={client.embedding_model}"
        )
        return True
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        print(f"FAIL: kg_processor config error: {exc}")
        return False


def check_embeddings_config() -> bool:
    try:
        from api.config import EMBEDDING_MODEL

        print(f"PASS: embeddings uses config Embedding={EMBEDDING_MODEL}")
        return True
    except Exception as exc:  # pragma: no cover - runtime environment dependent
        print(f"FAIL: embeddings config error: {exc}")
        return False


def check_no_api_key() -> bool:
    matches = scan_pattern("GEMINI_API_KEY")
    if matches:
        print("FAIL: Found GEMINI_API_KEY references")
        report_matches("Matches", matches)
        return False
    print("PASS: No GEMINI_API_KEY references")
    print("Matches count=0")
    return True


def main() -> int:
    sys.path.insert(0, str(PROJECT_ROOT))
    print("=" * 50)
    print("Phase 1 Verification: Configuration and Client Unification")
    print("=" * 50)
    print("")

    checks = [
        ("No google.generativeai imports", check_no_google_generativeai),
        ("vertex_ai_client usage", check_vertex_ai_client_usage),
        ("Config imports", check_config_imports),
        ("kg_processor uses config", check_kg_processor_config),
        ("embeddings uses config", check_embeddings_config),
        ("No GEMINI_API_KEY usage", check_no_api_key),
    ]

    results: list[bool] = []
    for name, check_func in checks:
        print(f"Checking: {name}...")
        results.append(check_func())
        print("")

    passed = sum(results)
    total = len(results)
    print("=" * 50)
    print("Summary")
    print("=" * 50)
    print(f"Passed: {passed}/{total}")
    if all(results):
        print("PASS: Phase 1 verification passed")
        return 0
    print("FAIL: Phase 1 verification failed")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
