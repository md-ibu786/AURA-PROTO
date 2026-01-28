# End-to-End Celery Pipeline Test Guide

## Overview

This guide documents how to run the end-to-end (E2E) tests for the Celery document processing pipeline in AURA-NOTES-MANAGER. The E2E test verifies the complete workflow from task submission through Redis, Celery worker processing, to final Neo4j persistence.

## Prerequisites

Before running E2E tests, ensure the following services and configurations are in place:

### 1. ✅ Redis Server Running

Redis is required for Celery task queue management.

```bash
# Check if Redis is running
redis-cli ping  # Should return PONG
```

**Configuration:**
- Redis URL: `redis://127.0.0.1:6379/0` (from `api/config.py`)
- Default port: `6379`

**If Redis is not running:**
```bash
# Windows (with Redis installed)
redis-server

# Or using Docker
docker run -d -p 6379:6379 redis:latest
```

### 2. ✅ Neo4j Database Running

Neo4j is required for knowledge graph persistence verification.

```bash
# Check Neo4j at http://localhost:7474
# Default credentials: neo4j/password
```

**Configuration:**
- Neo4j URI: `bolt://127.0.0.1:7687` (from `api/config.py`)
- Default user: `neo4j`
- Default password: `password`

**If Neo4j is not running:**
```bash
# Using Docker
docker run -d -p 7474:7474 -p 7687:7687 \
  -e NEO4J_AUTH=neo4j/password \
  neo4j:latest
```

### 3. ✅ Environment Variables

Ensure the following environment variables are set in `AURA-NOTES-MANAGER/.env`:

```env
# Google Cloud / Vertex AI
VERTEX_PROJECT=lucky-processor-480412-n8
VERTEX_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=./service_account.json

# Neo4j
NEO4J_URI=bolt://127.0.0.1:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# Redis
REDIS_URL=redis://127.0.0.1:6379/0

# Optional: Test Mode (mocks LLM calls)
AURA_TEST_MODE=false
```

### 4. ✅ Python Virtual Environment

**ALWAYS use the root venv** located at `D:\Peter\AURA Twin Proj\AURA-PROJ\.venv\`:

```bash
# Verify venv is active
D:\Peter\AURA Twin Proj\AURA-PROJ\.venv\Scripts\python --version

# Install dependencies if needed
cd AURA-NOTES-MANAGER
../../.venv/Scripts/python -m pip install -r requirements.txt
```

---

## Running Tests

There are three ways to run the E2E tests, depending on your testing needs:

### Option 1: Full E2E Test with Worker (Recommended)

This option runs the complete pipeline with a live Celery worker processing real tasks.

**Terminal 1: Start Celery Worker**
```bash
cd AURA-NOTES-MANAGER
../../.venv/Scripts/celery -A api.tasks worker -l info -Q kg_processing -P solo
```

**Terminal 2: Run E2E Test**
```bash
cd AURA-NOTES-MANAGER
../../.venv/Scripts/python api/test_celery_tasks_e2e.py
```

**Expected behavior:**
- Terminal 1 shows worker logs with task execution details
- Terminal 2 shows test progress through all 7 phases
- Test completes in ~30-60 seconds (depending on document size)

---

### Option 2: Pytest Mode (Individual Phases)

Run individual test phases using pytest for granular testing:

```bash
cd AURA-NOTES-MANAGER

# Run all phases
../../.venv/Scripts/python -m pytest api/test_celery_tasks_e2e.py -v

# Run specific phase
../../.venv/Scripts/python -m pytest api/test_celery_tasks_e2e.py::test_phase_1_redis_connection -v
../../.venv/Scripts/python -m pytest api/test_celery_tasks_e2e.py::test_phase_3_task_submission -v
```

**Available test phases:**
- `test_phase_1_redis_connection`
- `test_phase_2_worker_startup`
- `test_phase_3_task_submission`
- `test_phase_4_progress_tracking`
- `test_phase_5_result_validation`
- `test_phase_6_neo4j_persistence`
- `test_phase_7_error_handling`

⚠️ **Note:** Phases 3-6 depend on each other and should be run sequentially.

---

### Option 3: Test Mode with Mocks (No LLM Calls)

Use this mode to test the pipeline structure without making actual LLM API calls:

```bash
cd AURA-NOTES-MANAGER

# Set test mode environment variable
set AURA_TEST_MODE=true  # Windows
export AURA_TEST_MODE=true  # Linux/Mac

# Run test
../../.venv/Scripts/python api/test_celery_tasks_e2e.py
```

**What gets mocked:**
- Vertex AI LLM calls (entity extraction, summarization)
- Embedding generation
- External API calls

**What still runs:**
- Redis task queue
- Celery worker
- Neo4j persistence
- Task state management

---

## Test Phases

The E2E test runs through 7 sequential phases:

### Phase 1: Redis Connection ✅
**Purpose:** Verify Redis is running and accessible.

**What it tests:**
- Redis server connectivity
- Ping/pong response
- Connection URL validity

**Success criteria:** Redis responds to `PING` command.

---

### Phase 2: Worker Startup Check 🔍
**Purpose:** Verify Celery worker is running and ready to process tasks.

**What it tests:**
- Worker process detection
- Active worker count
- Worker queue configuration

**Success criteria:** At least one active worker found on `kg_processing` queue.

⚠️ **Note:** This phase is informational. Tests will continue even if no worker is found, but subsequent phases may hang.

---

### Phase 3: Task Submission 📤
**Purpose:** Submit a test document processing task to the queue.

**What it tests:**
- Task creation with test payload
- Task ID generation
- Initial task state (`PENDING`)

**Test payload:**
```python
{
    "document_id": "test_doc_<timestamp>",
    "module_id": "test_module",
    "user_id": "test_user"
}
```

**Success criteria:** Task submitted successfully with valid task ID.

---

### Phase 4: Progress Tracking 📊
**Purpose:** Monitor task progress through all processing stages.

**What it tests:**
- Real-time state updates
- Progress percentage tracking
- Stage transitions
- Task completion detection

**Expected states:**
- `PENDING` → `PROGRESS` → `SUCCESS` (or `FAILURE`)

**Timeout:** 120 seconds (2 minutes)

**Success criteria:** Task reaches `SUCCESS` state within timeout.

---

### Phase 5: Result Validation ✔️
**Purpose:** Verify task result contains expected data structure.

**What it tests:**
- Result retrieval from Redis
- Required fields presence
- Data type validation

**Expected result structure:**
```python
{
    "success": True,
    "document_id": "test_doc_<timestamp>",
    "entity_count": <int>,
    "chunk_count": <int>,
    "message": "Document processed successfully"
}
```

**Success criteria:** All required fields present with correct types.

---

### Phase 6: Neo4j Data Persistence 💾
**Purpose:** Verify processed data was persisted to Neo4j knowledge graph.

**What it tests:**
- Document node creation
- Entity node creation
- `HAS_ENTITY` relationship creation
- Data integrity

**Cypher queries executed:**
```cypher
// Check document node
MATCH (d:Document {document_id: $doc_id}) RETURN d

// Check entity relationships
MATCH (d:Document {document_id: $doc_id})-[:HAS_ENTITY]->(e:Entity)
RETURN count(e) as count
```

**Success criteria:** Document node exists with expected entity relationships.

---

### Phase 7: Error Handling ❌
**Purpose:** Verify pipeline handles invalid inputs gracefully.

**What it tests:**
- Invalid document ID handling
- Error state propagation
- Failure result structure

**Test case:** Submit task with empty `document_id`

**Success criteria:** Task fails gracefully with `FAILURE` state or `success: false` result.

---

## Expected Output

### Successful Test Run

```
============================================================
CELERY PIPELINE END-TO-END TEST
============================================================

============================================================
PHASE 1: Redis Connection
============================================================
[OK] Redis connection successful
   URL: redis://127.0.0.1:6379/0

============================================================
PHASE 2: Worker Startup Check
============================================================
[OK] Found 1 active worker(s):
   - celery@hostname: 0 active tasks

============================================================
PHASE 3: Task Submission
============================================================
Submitting task...
  Document ID: test_doc_1737123456
[OK] Task submitted
   Task ID: 12345678-1234-1234-1234-123456789abc
   State: PENDING

============================================================
PHASE 4: Progress Tracking
============================================================
Monitoring task progress...
  [PENDING]
  [PROGRESS] 10% - Extracting entities
  [PROGRESS] 50% - Generating embeddings
  [PROGRESS] 80% - Persisting to Neo4j
  [SUCCESS] 100% - Complete

[OK] Task completed with state: SUCCESS
   Stages seen: PENDING, PROGRESS, SUCCESS

============================================================
PHASE 5: Result Validation
============================================================
Task result:
  Success: True
  Document ID: test_doc_1737123456
  Entities: 15
  Chunks: 8
[OK] Result validation passed

============================================================
PHASE 6: Neo4j Data Persistence
============================================================
[OK] Document node found in Neo4j
   Entities found in Neo4j: 15

============================================================
PHASE 7: Error Handling
============================================================
Submitting invalid task (missing document_id)...
Task state: FAILURE
[OK] Error handling verified (task failed as expected)

============================================================
[OK] END-TO-END TEST PASSED
============================================================
```

---

## Troubleshooting

### ❌ Issue: Redis Connection Failed

**Error message:**
```
[FAIL] Redis connection failed: Error 10061 connecting to 127.0.0.1:6379. No connection could be made...
```

**Solution:**
1. Verify Redis is running: `redis-cli ping`
2. Check Redis port: `netstat -an | findstr 6379`
3. Start Redis server: `redis-server` or Docker command
4. Verify `REDIS_URL` in `.env` matches your Redis configuration

---

### ❌ Issue: No Active Workers Found

**Warning message:**
```
[WARN] No active workers found. Testing may hang or fail.
```

**Solution:**
1. Start Celery worker in separate terminal:
   ```bash
   cd AURA-NOTES-MANAGER
   ../../.venv/Scripts/celery -A api.tasks worker -l info -Q kg_processing -P solo
   ```
2. Verify worker is listening on `kg_processing` queue
3. Check for import errors in worker logs

---

### ❌ Issue: Task Timeout (Phase 4)

**Error message:**
```
Task did not complete within 120 seconds
```

**Possible causes:**
1. **Worker not running** → Start worker (see above)
2. **Worker crashed** → Check worker logs for errors
3. **LLM API timeout** → Check Vertex AI credentials and quota
4. **Large document** → Increase timeout in test file

**Solution:**
```python
# In test_celery_tasks_e2e.py, line 136
timeout = 300  # Increase from 120 to 300 seconds
```

---

### ❌ Issue: Import Errors

**Error message:**
```
ModuleNotFoundError: No module named 'api.tasks'
```

**Solution:**
1. Verify you're using the root venv:
   ```bash
   ../../.venv/Scripts/python api/test_celery_tasks_e2e.py
   ```
2. Install dependencies:
   ```bash
   ../../.venv/Scripts/python -m pip install -r requirements.txt
   ```
3. Check `sys.path` includes parent directory (handled by test file)

---

### ❌ Issue: Neo4j Connection Failed

**Error message:**
```
[FAIL] Neo4j check failed: Unable to retrieve routing information
```

**Solution:**
1. Verify Neo4j is running: Visit `http://localhost:7474`
2. Check credentials in `.env`:
   ```env
   NEO4J_URI=bolt://127.0.0.1:7687
   NEO4J_USER=neo4j
   NEO4J_PASSWORD=password
   ```
3. Test connection manually:
   ```python
   from neo4j import GraphDatabase
   driver = GraphDatabase.driver("bolt://127.0.0.1:7687", auth=("neo4j", "password"))
   driver.verify_connectivity()
   ```

---

### ❌ Issue: Vertex AI Authentication Failed

**Error message:**
```
google.auth.exceptions.DefaultCredentialsError: Could not automatically determine credentials
```

**Solution:**
1. Verify `service_account.json` exists in `AURA-NOTES-MANAGER/`
2. Check `.env` has correct path:
   ```env
   GOOGLE_APPLICATION_CREDENTIALS=./service_account.json
   ```
3. Alternatively, use test mode to skip LLM calls:
   ```bash
   set AURA_TEST_MODE=true
   ```

---

## Additional Resources

- **Test file:** `AURA-NOTES-MANAGER/api/test_celery_tasks_e2e.py`
- **Task implementation:** `AURA-NOTES-MANAGER/api/tasks/document_processing_tasks.py`
- **Configuration:** `AURA-NOTES-MANAGER/api/config.py`
- **Planning doc:** `.planning/ai_enablement_plans/03-pipeline/03-03-PLAN.xml`

---

## Quick Reference Commands

```bash
# Start Redis (Docker)
docker run -d -p 6379:6379 redis:latest

# Start Neo4j (Docker)
docker run -d -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:latest

# Start Celery Worker
cd AURA-NOTES-MANAGER
../../.venv/Scripts/celery -A api.tasks worker -l info -Q kg_processing -P solo

# Run E2E Test (Full)
cd AURA-NOTES-MANAGER
../../.venv/Scripts/python api/test_celery_tasks_e2e.py

# Run E2E Test (Test Mode)
cd AURA-NOTES-MANAGER
set AURA_TEST_MODE=true
../../.venv/Scripts/python api/test_celery_tasks_e2e.py

# Run with Pytest
cd AURA-NOTES-MANAGER
../../.venv/Scripts/python -m pytest api/test_celery_tasks_e2e.py -v
```

---

**Last Updated:** 2026-01-28  
**Maintained by:** Documentation Agent
