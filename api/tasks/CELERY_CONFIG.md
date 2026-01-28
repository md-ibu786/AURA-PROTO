# Celery Configuration Documentation

## Overview
Celery configuration for AURA-NOTES-MANAGER knowledge graph processing tasks.

## Configuration Location
- **File:** `api/tasks/document_processing_tasks.py` (lines 196-228)
- **Rationale:** Single-file configuration keeps task and config co-located

## Key Settings

| Setting | Value | Rationale |
|---------|-------|-----------|
| Broker | Redis (127.0.0.1:6379/0) | Fast, reliable message queue |
| Result Backend | Redis (same instance) | Persistent result storage |
| Serializer | JSON | Human-readable, secure |
| Task Acks | Late (after completion) | Ensures re-queue on failure |
| Prefetch | 1 task per worker | Prevents starvation on long tasks |
| Result Expires | 3600s (1 hour) | Balance between visibility and storage |
| Time Limit (doc) | 1800s (30 min) | Prevents hanging tasks on large files |
| Soft Limit (doc) | 1500s (25 min) | Allows graceful cleanup |
| Time Limit (batch) | 3600s (1 hour) | Batch processing has longer window |
| Soft Limit (batch) | 3000s (50 min) | Allows graceful cleanup |

## Best Practices Compliance

| Setting | Value | Status |
|---------|-------|--------|
| `task_serializer` | `json` | ✅ Pass |
| `accept_content` | `['json']` | ✅ Pass |
| `result_serializer` | `json` | ✅ Pass |
| `task_acks_late` | `True` | ✅ Pass |
| `task_reject_on_worker_lost` | `True` | ✅ Pass |
| `worker_prefetch_multiplier` | `1` | ✅ Pass |
| `result_expires` | `3600` | ✅ Pass |
| `task_track_started` | `True` | ✅ Pass |
| `task_time_limit` | `1800/3600` | ✅ Pass (set in task decorators) |
| `task_soft_time_limit` | `1500/3000` | ✅ Pass (set in task decorators) |

## Queue Structure
- **Default Queue:** `kg_processing`
- **Route:** All `api.tasks.*` → `kg_processing` queue

## Environment Variables
```env
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_DB=0
CELERY_RESULT_EXPIRES=3600
```

## Config File Integration
- `api/config.py` exposes:
  - `REDIS_URL` - Combined Redis connection string
  - `CELERY_RESULT_EXPIRES` - Result expiration time

## Worker Commands

### Development
```bash
# From AURA-NOTES-MANAGER directory
celery -A api.tasks.document_processing_tasks worker -l info -Q kg_processing -P solo --concurrency=2
```

### Production
```bash
celery -A api.tasks.document_processing_tasks worker -l warning -Q kg_processing -P solo --concurrency=4
```

## Task Definitions

### `process_document_task`
- **Name:** `api.tasks.process_document`
- **Time Limit:** 30 minutes (hard), 25 minutes (soft)
- **Max Retries:** 5
- **Auto-retry:** ConnectionError, TimeoutError

### `process_batch_task`
- **Name:** `api.tasks.process_batch`
- **Time Limit:** 1 hour (hard), 50 minutes (soft)
- **Max Retries:** 3
- **Auto-retry:** ConnectionError, TimeoutError

## Monitoring
- Task states tracked in Redis (1-hour TTL)
- Progress updates via `self.update_state()`
- Firestore document status synced in real-time
- Processing states: PENDING → PARSING → CHUNKING → EMBEDDING → EXTRACTING → STORING → COMPLETED

## Error Handling
- **Validation errors:** Not retried (fail fast)
- **Connection errors:** Auto-retry with exponential backoff
- **Timeout errors:** Auto-retry with exponential backoff
- **Soft time limit:** Allows graceful cleanup before hard kill
- **Max retries exceeded:** Task fails permanently, Firestore updated

## Troubleshooting

### Redis Connection Issues
```bash
# Check Redis is running
redis-cli ping

# Start Redis (Windows with Docker)
docker run -d -p 6379:6379 redis:alpine

# Check Redis config in Python
python -c "from api.config import REDIS_URL; print(REDIS_URL)"
```

### Task Not Found
```bash
# Verify task registration
python -c "from api.tasks.document_processing_tasks import app; print([t for t in app.tasks.keys() if 'document' in t])"
```

---
**Verified:** 2026-01-28
**Plan:** 03-01-PLAN.xml (Phase 3 - Celery Pipeline Verification)
