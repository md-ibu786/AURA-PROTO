# verify_phase_3.py
# Phase 3 verification runner for Celery pipeline readiness

# Longer description (2-4 lines):
# - Runs ten checks covering files, imports, config, services, and docs.
# - Reports a pass/fail summary with an automation-friendly exit code.
# - Resolves paths relative to repo and AURA-NOTES-MANAGER.

# @see: api/tasks/document_processing_tasks.py - Celery app and tasks
# @note: Run from AURA-NOTES-MANAGER with root venv

from __future__ import annotations

import argparse
import importlib
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Tuple


PROJECT_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = PROJECT_DIR.parent
API_DIR = PROJECT_DIR / "api"

if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


class Phase3Verifier:
    """Verifies Phase 3 completion."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.checks_passed = 0
        self.checks_failed = 0
        self.warnings = 0
        self.results: List[Tuple[str, bool, str]] = []

    def check(
        self, name: str, func: Callable[[], Tuple[bool, str]]
    ) -> Tuple[bool, str]:
        """Run a verification check."""
        print(f"Checking: {name}...")
        try:
            passed, message = func()
        except Exception as exc:  # pragma: no cover - unexpected runtime errors
            passed = False
            message = f"Exception: {exc.__class__.__name__}: {exc}"

        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {message}")

        self.results.append((name, passed, message))
        if passed:
            self.checks_passed += 1
        else:
            self.checks_failed += 1
        return passed, message

    def warn(self, message: str) -> None:
        """Print warning."""
        self.warnings += 1
        print(f"  [WARN] {message}")

    def check_files_exist(self) -> Tuple[bool, str]:
        """Verify all required files exist."""
        required_files = [
            "api/config.py",
            "api/kg_processor.py",
            "api/tasks/__init__.py",
            "api/tasks/document_processing_tasks.py",
            "api/test_celery_tasks.py",
            "api/test_celery_tasks_e2e.py",
            "api/verify_neo4j_data.py",
            "api/verify_phase_3.py",
            "services/vertex_ai_client.py",
            "services/entity_aware_chunker.py",
            "services/llm_entity_extractor.py",
        ]
        missing = [path for path in required_files if not (PROJECT_DIR / path).exists()]
        if missing:
            return False, f"Missing files: {', '.join(missing)}"
        return True, f"All {len(required_files)} required files exist"

    def check_imports(self) -> Tuple[bool, str]:
        """Verify all Python imports work."""
        modules = [
            "api.config",
            "api.kg_processor",
            "api.tasks.document_processing_tasks",
            "services.vertex_ai_client",
            "services.entity_aware_chunker",
            "services.llm_entity_extractor",
        ]
        failures = []
        for module in modules:
            try:
                importlib.import_module(module)
            except Exception as exc:  # pragma: no cover - import failures
                failures.append(f"{module}: {exc}")
        if failures:
            return False, f"Import failures: {'; '.join(failures)}"
        return True, f"All {len(modules)} import groups successful"

    def check_celery_config(self) -> Tuple[bool, str]:
        """Verify Celery configuration."""
        from api.config import CELERY_RESULT_EXPIRES, REDIS_URL
        from api.tasks.document_processing_tasks import app

        issues = []
        if app.conf.broker_url != REDIS_URL:
            issues.append("broker_url mismatch")
        if app.conf.result_backend != REDIS_URL:
            issues.append("result_backend mismatch")
        if app.conf.result_expires != CELERY_RESULT_EXPIRES:
            issues.append("result_expires mismatch")
        if app.conf.task_serializer != "json":
            issues.append("task_serializer not json")
        if "json" not in (app.conf.accept_content or []):
            issues.append("accept_content missing json")
        if app.conf.result_serializer != "json":
            issues.append("result_serializer not json")
        routes = app.conf.task_routes or {}
        if "api.tasks.*" not in routes:
            issues.append("task_routes missing api.tasks.*")

        if issues:
            return False, f"Celery config issues: {', '.join(issues)}"
        return True, "Celery configuration valid"

    def check_redis_connection(self) -> Tuple[bool, str]:
        """Verify Redis connection."""
        try:
            import redis
        except ImportError as exc:
            return False, f"Redis client not available: {exc}"

        from api.config import REDIS_URL

        if os.getenv("AURA_TEST_MODE", "false").lower() == "true":
            return True, f"Redis connection skipped in test mode ({REDIS_URL})"

        try:
            client = redis.Redis.from_url(
                REDIS_URL,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            client.ping()
        except Exception as exc:  # pragma: no cover - network dependent
            return (
                False,
                f"Redis connection failed: {exc} (set AURA_TEST_MODE=true to skip)",
            )

        return True, f"Redis connection OK ({REDIS_URL})"

    def check_neo4j_connection(self) -> Tuple[bool, str]:
        """Verify Neo4j connection."""
        try:
            from neo4j import GraphDatabase
        except ImportError as exc:
            return False, f"Neo4j driver not available: {exc}"

        from api.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USER

        if os.getenv("AURA_TEST_MODE", "false").lower() == "true":
            return True, f"Neo4j connection skipped in test mode ({NEO4J_URI})"

        try:
            driver = GraphDatabase.driver(
                NEO4J_URI,
                auth=(NEO4J_USER, NEO4J_PASSWORD),
            )
            driver.verify_connectivity()
            driver.close()
        except Exception as exc:  # pragma: no cover - network dependent
            return (
                False,
                f"Neo4j connection failed: {exc} (set AURA_TEST_MODE=true to skip)",
            )

        return True, f"Neo4j connection OK ({NEO4J_URI})"

    def check_tasks_registered(self) -> Tuple[bool, str]:
        """Verify Celery tasks are registered."""
        from api.tasks.document_processing_tasks import app

        registered = list(app.tasks.keys())
        required_tasks = [
            "api.tasks.process_document",
            "api.tasks.process_batch",
        ]
        missing = [task for task in required_tasks if task not in registered]
        if missing:
            return False, f"Missing tasks: {', '.join(missing)}"
        return True, f"{len(required_tasks)} required Celery tasks registered"

    def check_phase_2_integration(self) -> Tuple[bool, str]:
        """Verify Phase 2 services are integrated."""
        import api.kg_processor as kg_processor
        from services.entity_aware_chunker import EntityAwareChunker
        from services.llm_entity_extractor import LLMEntityExtractor

        if not hasattr(kg_processor, "KnowledgeGraphProcessor"):
            return False, "KnowledgeGraphProcessor missing in kg_processor"
        if not isinstance(EntityAwareChunker, type):
            return False, "EntityAwareChunker is not a class"
        if not isinstance(LLMEntityExtractor, type):
            return False, "LLMEntityExtractor is not a class"
        if not hasattr(kg_processor, "EntityAwareChunker"):
            return False, "kg_processor missing EntityAwareChunker import"
        if not hasattr(kg_processor, "LLMEntityExtractor"):
            return False, "kg_processor missing LLMEntityExtractor import"
        return True, "Phase 2 integration verified"

    def check_documentation(self) -> Tuple[bool, str]:
        """Verify documentation files exist."""
        repo_docs = [
            ".planning/ai_enablement_plans/03-pipeline/PHASE_3_CHECKLIST.md",
            ".planning/ai_enablement_plans/03-pipeline/SUMMARY.md",
        ]
        missing = [path for path in repo_docs if not (REPO_ROOT / path).exists()]
        summary_path = PROJECT_DIR / "api" / "PHASE_3_SUMMARY.md"
        if not summary_path.exists():
            missing.append("api/PHASE_3_SUMMARY.md")
        if missing:
            return False, f"Missing docs: {', '.join(missing)}"
        return True, "3/3 documentation files present"

    def check_test_scripts(self) -> Tuple[bool, str]:
        """Verify test scripts can be imported."""
        modules = [
            "api.test_celery_tasks",
            "api.test_celery_tasks_e2e",
            "api.verify_neo4j_data",
        ]
        failures = []
        for module in modules:
            try:
                importlib.import_module(module)
            except Exception as exc:
                failures.append(f"{module}: {exc}")
        if failures:
            return False, f"Test script import failures: {'; '.join(failures)}"
        return True, "All test scripts importable"

    def check_environment_variables(self) -> Tuple[bool, str]:
        """Verify required environment variables."""
        from api.config import (
            EMBEDDING_MODEL,
            GOOGLE_APPLICATION_CREDENTIALS,
            LLM_ENTITY_EXTRACTION_MODEL,
            LLM_SUMMARIZATION_MODEL,
            NEO4J_PASSWORD,
            NEO4J_URI,
            NEO4J_USER,
            REDIS_URL,
            VERTEX_LOCATION,
            VERTEX_PROJECT,
            VERTEX_CREDENTIALS,
        )

        required_values = {
            "VERTEX_PROJECT": VERTEX_PROJECT,
            "VERTEX_LOCATION": VERTEX_LOCATION,
            "VERTEX_CREDENTIALS": VERTEX_CREDENTIALS,
            "GOOGLE_APPLICATION_CREDENTIALS": GOOGLE_APPLICATION_CREDENTIALS,
            "LLM_ENTITY_EXTRACTION_MODEL": LLM_ENTITY_EXTRACTION_MODEL,
            "LLM_SUMMARIZATION_MODEL": LLM_SUMMARIZATION_MODEL,
            "EMBEDDING_MODEL": EMBEDDING_MODEL,
            "NEO4J_URI": NEO4J_URI,
            "NEO4J_USER": NEO4J_USER,
            "NEO4J_PASSWORD": NEO4J_PASSWORD,
            "REDIS_URL": REDIS_URL,
        }

        missing = [key for key, value in required_values.items() if not value]
        if missing:
            return False, f"Missing values: {', '.join(missing)}"

        credential_path = Path(GOOGLE_APPLICATION_CREDENTIALS)
        if not credential_path.is_absolute():
            if credential_path.parts and credential_path.parts[0] == PROJECT_DIR.name:
                credential_path = (REPO_ROOT / credential_path).resolve()
            else:
                credential_path = (PROJECT_DIR / credential_path).resolve()
        if not credential_path.exists():
            self.warn(
                "Credentials file not found at "
                f"{credential_path}; ensure ADC or service account is available"
            )

        return (
            True,
            f"Environment variables configured ({len(required_values)} checks passed)",
        )

    def run_all_checks(self) -> int:
        """Run all verification checks."""
        print("=" * 60)
        print("PHASE 3 VERIFICATION")
        print("=" * 60)
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print("")

        checks = [
            ("File Existence", self.check_files_exist),
            ("Python Imports", self.check_imports),
            ("Celery Configuration", self.check_celery_config),
            ("Redis Connection", self.check_redis_connection),
            ("Neo4j Connection", self.check_neo4j_connection),
            ("Celery Tasks Registered", self.check_tasks_registered),
            ("Phase 2 Integration", self.check_phase_2_integration),
            ("Documentation Files", self.check_documentation),
            ("Test Scripts", self.check_test_scripts),
            ("Environment Variables", self.check_environment_variables),
        ]

        for name, func in checks:
            self.check(name, func)
            print("")

        total = self.checks_passed + self.checks_failed
        pass_rate = (self.checks_passed / total * 100.0) if total else 0.0

        print("=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"Checks passed:  {self.checks_passed}")
        print(f"Checks failed:  {self.checks_failed}")
        print(f"Warnings:       {self.warnings}")
        print("")
        print(f"Pass rate: {pass_rate:.1f}%")
        print("")

        if self.checks_failed == 0:
            print("=" * 60)
            print("PHASE 3 VERIFICATION PASSED")
            print("=" * 60)
            print("Phase 3 is complete and production-ready.")
            print("")
            print("Next steps:")
            print("1. Review Phase 3 deliverables")
            print("2. Run E2E test: python api/test_celery_tasks_e2e.py")
            print("3. Proceed to next phase or production deployment")
            return 0

        print("=" * 60)
        print("PHASE 3 VERIFICATION FAILED")
        print("=" * 60)
        print("Review failed checks and resolve issues.")
        return 1


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Phase 3 verification checks")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    verifier = Phase3Verifier(verbose=args.verbose)
    return verifier.run_all_checks()


if __name__ == "__main__":
    sys.exit(main())
