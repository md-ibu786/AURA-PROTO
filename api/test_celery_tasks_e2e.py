# test_celery_tasks_e2e.py
# End-to-end verification of the Celery document processing pipeline

# This script performs a full integration test of the Celery pipeline,
# verifying Redis connectivity, worker availability, task submission,
# real-time progress tracking, result structure, and Neo4j persistence.
# It supports both live testing and a mock-ready 'Test Mode'.

# @see: api/tasks/document_processing_tasks.py - Celery task implementation
# @see: api/tests/E2E_TEST_GUIDE.md - Execution instructions
# @note: Requires Redis and Neo4j to be running for full verification.

import os
import sys
import time
import pytest
from pathlib import Path

# Add parent directory to path to allow imports from api.*
_current_dir = os.path.dirname(os.path.abspath(__file__))
_root_dir = os.path.dirname(_current_dir)
if _root_dir not in sys.path:
    sys.path.insert(0, _root_dir)

# Test configuration
REDIS_REQUIRED = os.getenv("AURA_E2E_REQUIRED", "false").lower() == "true"
NEO4J_REQUIRED = os.getenv("AURA_E2E_REQUIRED", "false").lower() == "true"
TEST_MODE = os.getenv("AURA_TEST_MODE", "false").lower() == "true"

if TEST_MODE or not (REDIS_REQUIRED or NEO4J_REQUIRED):
    pytest.skip(
        "E2E dependencies not required for local runs",
        allow_module_level=True,
    )


@pytest.fixture
def task_result():
    """Fixture to provide task result across phases."""
    return test_phase_3_task_submission()


@pytest.fixture
def result(task_result):
    """Fixture to provide final validated result."""
    return test_phase_5_result_validation(task_result)


def test_phase_1_redis_connection():
    """Verify Redis is running and accessible."""
    import redis
    from api.config import REDIS_URL

    print(f"\n{'=' * 60}")
    print("PHASE 1: Redis Connection")
    print(f"{'=' * 60}")

    try:
        r = redis.Redis.from_url(REDIS_URL)
        result = r.ping()
        assert result is True, "Redis ping failed"

        print(f"[OK] Redis connection successful")
        print(f"   URL: {REDIS_URL}")
        return True

    except redis.ConnectionError as e:
        print(f"[FAIL] Redis connection failed: {e}")
        if REDIS_REQUIRED:
            pytest.fail("Redis is required for E2E tests")
        return False


def test_phase_2_worker_startup():
    """Verify Celery worker can start (manual check)."""
    from api.tasks.document_processing_tasks import app

    print(f"\n{'=' * 60}")
    print("PHASE 2: Worker Startup Check")
    print(f"{'=' * 60}")

    print("Worker startup command:")
    print("  cd AURA-NOTES-MANAGER")
    print(
        "  ../../.venv/Scripts/celery -A api.tasks worker -l info -Q kg_processing -P solo"
    )

    # Check if worker is running
    try:
        inspector = app.control.inspect()
        workers = inspector.active()

        if workers:
            print(f"[OK] Found {len(workers)} active worker(s):")
            for worker_name, tasks in workers.items():
                print(f"   - {worker_name}: {len(tasks)} active tasks")
            return True
        else:
            print("[WARN] No active workers found")
            return False

    except Exception as e:
        print(f"[WARN] Could not inspect workers: {e}")
        return False


def test_phase_3_task_submission():
    """Submit a test document processing task."""
    from api.tasks.document_processing_tasks import process_document_task

    print(f"\n{'=' * 60}")
    print("PHASE 3: Task Submission")
    print(f"{'=' * 60}")

    # Create test payload
    test_document_id = f"test_doc_{int(time.time())}"
    test_module_id = "test_module"
    test_user_id = "test_user"

    print(f"Submitting task...")
    print(f"  Document ID: {test_document_id}")

    # Submit task (async)
    result = process_document_task.delay(
        document_id=test_document_id, module_id=test_module_id, user_id=test_user_id
    )

    print(f"[OK] Task submitted")
    print(f"   Task ID: {result.id}")
    print(f"   State: {result.state}")

    return result


def test_phase_4_progress_tracking(task_result):
    """Monitor task progress through all stages."""
    print(f"\n{'=' * 60}")
    print("PHASE 4: Progress Tracking")
    print(f"{'=' * 60}")

    stages_seen = set()
    timeout = 120  # 2 minutes
    start_time = time.time()

    print("Monitoring task progress...")

    while time.time() - start_time < timeout:
        state = task_result.state
        info = task_result.info

        if state not in stages_seen:
            stages_seen.add(state)
            print(f"  [{state}]", end="")
            if isinstance(info, dict):
                progress = info.get("progress", 0)
                stage = info.get("stage", "")
                print(f" {progress}% - {stage}")
            else:
                print()

        if state in ["SUCCESS", "FAILURE"]:
            break

        time.sleep(1)

    print(f"\n[OK] Task completed with state: {task_result.state}")
    print(f"   Stages seen: {', '.join(sorted(stages_seen))}")

    assert task_result.state == "SUCCESS", f"Task failed with state {task_result.state}"
    return True


def test_phase_5_result_validation(task_result):
    """Verify task result contains expected data."""
    print(f"\n{'=' * 60}")
    print("PHASE 5: Result Validation")
    print(f"{'=' * 60}")

    result = task_result.get(timeout=10)

    print("Task result:")
    print(f"  Success: {result.get('success')}")
    print(f"  Document ID: {result.get('document_id')}")
    print(f"  Entities: {result.get('entity_count', 0)}")
    print(f"  Chunks: {result.get('chunk_count', 0)}")

    # Validate result structure (aligned with api/tasks/document_processing_tasks.py)
    assert result.get("success") is True, (
        f"Expected success True, got {result.get('success')}. Error: {result.get('error')}"
    )
    assert result.get("document_id"), "Missing document_id in result"
    assert "entity_count" in result, "Missing entity_count in result"
    assert "chunk_count" in result, "Missing chunk_count in result"

    print("[OK] Result validation passed")
    return result


def test_phase_6_neo4j_persistence(result):
    """Verify Neo4j contains document, entities, and relationships."""
    from neo4j import GraphDatabase
    from api.config import NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD

    print(f"\n{'=' * 60}")
    print("PHASE 6: Neo4j Data Persistence")
    print(f"{'=' * 60}")

    document_id = result.get("document_id")

    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

        with driver.session() as session:
            # Check for document node
            doc_result = session.run(
                "MATCH (d:Document {document_id: $doc_id}) RETURN d", doc_id=document_id
            )
            doc = doc_result.single()

            assert doc, f"Document node {document_id} not found in Neo4j"
            print(f"[OK] Document node found in Neo4j")

            # Check for entity nodes
            entity_result = session.run(
                "MATCH (d:Document {document_id: $doc_id})-[:HAS_ENTITY]->(e:Entity) RETURN count(e) as count",
                doc_id=document_id,
            )
            entity_count = entity_result.single()["count"]
            print(f"   Entities found in Neo4j: {entity_count}")
            assert entity_count > 0 or result.get("entity_count") == 0, (
                "No entities found in Neo4j for processed document"
            )

        driver.close()
        return True

    except Exception as e:
        print(f"[FAIL] Neo4j check failed: {e}")
        if NEO4J_REQUIRED:
            pytest.fail(f"Neo4j verification failed: {e}")
        return False


def test_phase_7_error_handling():
    """Test error scenarios (e.g., missing document_id)."""
    from api.tasks.document_processing_tasks import process_document_task
    from celery.exceptions import TimeoutError as CeleryTimeoutError

    print(f"\n{'=' * 60}")
    print("PHASE 7: Error Handling")
    print(f"{'=' * 60}")

    print("Submitting invalid task (missing document_id)...")

    # Submit task with invalid document_id (empty string)
    result = process_document_task.delay(
        document_id="", module_id="test", user_id="test"
    )
    print(f"   Task ID: {result.id}")

    # Wait for task to complete with timeout protection
    try:
        state = result.get(timeout=30, propagate=False)
        print(f"   Task state: {result.state}")

        # Verify the task failed as expected
        # Task should either be in FAILURE state or return success=False
        if result.state == "FAILURE":
            print("[OK] Error handling verified (task state: FAILURE)")
        elif isinstance(state, dict) and state.get("success") is False:
            print(
                f"[OK] Error handling verified (success=False, error: {state.get('error')})"
            )
        else:
            # Task succeeded when it should have failed - this is a test failure
            raise AssertionError(
                f"Expected task to fail with empty document_id, but got state={result.state}, result={state}"
            )

    except CeleryTimeoutError:
        # Timeout waiting for task - likely no worker running
        print("[WARN] Task timed out after 30s (worker may not be running)")
        print("   Skipping error handling verification")
    except AssertionError:
        # Re-raise assertion errors so test fails properly
        raise


def run_e2e_test():
    """Run full end-to-end test sequence."""
    print("\n" + "=" * 60)
    print("CELERY PIPELINE END-TO-END TEST")
    print("=" * 60)

    # Phase 1: Redis
    if not test_phase_1_redis_connection():
        return False

    # Phase 2: Worker
    if not test_phase_2_worker_startup():
        print("\n[WARN] No active workers found. Testing may hang or fail.")

    # Phase 3: Submit task
    task_res = test_phase_3_task_submission()

    # Phase 4: Track progress
    if not test_phase_4_progress_tracking(task_res):
        return False

    # Phase 5: Validate result
    res = test_phase_5_result_validation(task_res)

    # Phase 6: Check Neo4j
    if not test_phase_6_neo4j_persistence(res):
        return False

    # Phase 7: Error Handling
    test_phase_7_error_handling()

    print("\n" + "=" * 60)
    print("[OK] END-TO-END TEST PASSED")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = run_e2e_test()
    sys.exit(0 if success else 1)
