# Audio Processing Pipeline — Fix Plan

**Source:** `reviews/audio-review.md` (2026-05-24)
**Created:** 2026-05-24
**Estimated Effort:** ~3–4 hours (3 blockers + 4 highs + 6 mediums + 5 lows)

---

## Overview

The review identified **3 blockers, 4 highs, 6 mediums, and 5 lows** across the audio processing pipeline. The blockers cause silent data corruption — error strings get embedded into generated PDFs. The highs involve data loss on restart, memory exhaustion, race conditions, and missing auth. This plan groups fixes by area for efficient implementation.

**Affected Files:**
| File | Issues |
|------|--------|
| `services/summarizer.py` | B-1 |
| `services/coc.py` | B-2 |
| `frontend/src/components/explorer/UploadDialog.tsx` | B-3, H-6, M-5, M-6 |
| `api/audio_processing.py` | H-1, H-2, H-3, H-5, M-1, M-2, M-4, L-3, L-5 |
| `services/stt.py` | L-1 |
| `api/tests/test_audio_processing.py` | L-4 |

---

## Prerequisites

1. Backend dev server running (`python -m uvicorn main:app --reload --port 8001`)
2. Frontend dev server running (`npm run dev` in `frontend/`)
3. Redis instance available (for H-1; check `REDIS_URL` in `api/config.py`)
4. `pytest` passing before changes (baseline)

---

## Fix Groups

### Group 1: Silent Corruption — Error Strings as Valid Output (B-1, B-2)

**Rationale:** The two most critical bugs share the same pattern: a service catches an exception and returns an error *string* instead of raising. The pipeline treats the string as valid content and generates a corrupt PDF. Fix both services, then the pipeline's existing `except` blocks handle them correctly.

#### B-1 — `services/summarizer.py:113-121`

**Before:**
```python
    except Exception as e:
        logger.warning(
            "Summarization failed via ModelRouter, provider=%s model=%s: %s",
            cfg["provider"],
            cfg["model"],
            e,
            exc_info=True,
        )
        return f"Note Generation Failed: {str(e)}"
```

**After:**
```python
    except Exception as e:
        logger.error(
            "Summarization failed via ModelRouter, provider=%s model=%s: %s",
            cfg["provider"],
            cfg["model"],
            e,
            exc_info=True,
        )
        raise RuntimeError(f"Note generation failed: {str(e)}") from e
```

**Validation:** `_run_pipeline`'s outer `except Exception as e` at `audio_processing.py:586` catches this and sets job status to `"error"`.

#### B-2 — `services/coc.py:256-257`

**Before:**
```python
    except json.JSONDecodeError:
        return "Error: Model failed to return valid JSON."
```

**After:**
```python
    except json.JSONDecodeError as e:
        logger.error("Failed to parse audit response as JSON: %s", e, exc_info=True)
        raise ValueError(f"AI refinement returned invalid JSON: {e}") from e
```

**Validation:** `transform_transcript` is called at `audio_processing.py:520` inside `_run_pipeline`'s try block; the `ValueError` propagates to the outer except.

---

### Group 2: Frontend Auth Bypass & Polling (B-3, H-6, M-6)

**Rationale:** All three issues are in `UploadDialog.tsx`'s fetch logic. Replace raw `fetch()` with `audioApi.ts` wrappers (which inject auth), and fix the polling error handling.

#### B-3 — `UploadDialog.tsx:119-121` (polling) and `:272-275` (start)

**Before (polling, line 120-121):**
```tsx
const response = await fetch(`/api/audio/pipeline-status/${processing.jobId}`);
const data = await response.json();
```

**After (polling):**
```tsx
import { startPipeline, getPipelineStatus } from '../../api/audioApi';
// ...
const data = await getPipelineStatus(processing.jobId);
```

**Before (start, line 272-277):**
```tsx
const response = await fetch('/api/audio/process-pipeline', {
    method: 'POST',
    body: formData,
});
const data = await response.json();

if (!response.ok) {
    throw new Error(data.detail || 'Failed to start processing');
}
```

**After (start):**
```tsx
const data = await startPipeline(selectedFile!, topic, moduleId);
```

Remove the manual `formData` construction (lines 265-271) since `startPipeline` handles it.

#### H-6 — `UploadDialog.tsx:151-153` — polling never stops on 404

**Before:**
```tsx
} catch (err) {
    console.error('Status poll error:', err);
}
```

**After:**
```tsx
} catch (err: unknown) {
    console.error('Status poll error:', err);
    // If the job is not found (expired/evicted), stop polling and show error
    if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
    }
    const message = err instanceof Error ? err.message : 'Job expired or not found';
    toast.error(message);
    setError(message);
}
```

**Note:** When using `getPipelineStatus` from `audioApi.ts`, a 404 will throw via `fetchApi`'s error handling, so the catch block fires correctly.

#### M-6 — `UploadDialog.tsx:120-121` — no `response.ok` check before `.json()`

This is **resolved by B-3**: `getPipelineStatus` uses `fetchApi` which checks `response.ok` and throws on non-2xx responses.

**Validation:** Start the pipeline, then manually delete the job from the store (or wait 5 min for TTL). Confirm the UI shows "Job expired or not found" toast instead of a perpetual spinner.

---

### Group 3: Frontend Type Fix (M-5)

#### M-5 — `UploadDialog.tsx:69`

**Before:**
```tsx
noteId?: number;
```

**After:**
```tsx
noteId?: string;
```

**Validation:** `tsc --noEmit` passes. Backend returns string Firestore IDs (see `audio_processing.py:581`).

---

### Group 4: In-Memory Job Store (H-1, H-3)

**Rationale:** H-1 (lost on restart) and H-3 (race condition) are both in the job store. Replace the dict with Redis if available, otherwise fix the race condition in the dict-based store.

#### H-1 — `audio_processing.py:140`

**Before:**
```python
job_status_store = {}
```

**After (Redis-backed):**
```python
import redis
import json

_redis_client = None

def _get_redis():
    global _redis_client
    if _redis_client is None:
        redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
        _redis_client = redis.from_url(redis_url, decode_responses=True)
    return _redis_client

def _set_job(job_id: str, data: dict) -> None:
    """Store job data with TTL."""
    data["updated_at"] = time.time()
    try:
        _get_redis().set(f"job:{job_id}", json.dumps(data), ex=JOB_STATUS_TTL_SECONDS)
    except Exception:
        logger.warning("Redis unavailable, falling back to in-memory store")
        job_status_store[job_id] = data

def _get_job(job_id: str) -> Optional[dict]:
    """Retrieve job data."""
    try:
        raw = _get_redis().get(f"job:{job_id}")
        return json.loads(raw) if raw else None
    except Exception:
        return job_status_store.get(job_id)

def _delete_job(job_id: str) -> None:
    try:
        _get_redis().delete(f"job:{job_id}")
    except Exception:
        job_status_store.pop(job_id, None)
```

Then replace all `job_status_store[job_id] = ...` with `_set_job(job_id, ...)`, `job_status_store[job_id]` reads with `_get_job(job_id)`, and `job_status_store` checks with `_get_job(job_id) is not None`.

**Fallback:** If Redis is unavailable, keep the in-memory dict but add a `threading.Lock`:

```python
import threading
_job_store_lock = threading.Lock()

# All reads/writes wrapped in:
with _job_store_lock:
    job_status_store[job_id] = data
```

#### H-3 — `audio_processing.py:212-216` — race condition in `_cleanup_job_store`

**Resolved by H-1** if Redis is adopted (Redis operations are atomic; TTL handles expiry natively).

If keeping the dict fallback, fix the clear-rebuild race:

**Before:**
```python
    job_status_store.clear()
    for job_id, job_data in active_jobs:
        job_status_store[job_id] = job_data
    for job_id, job_data in terminal_jobs:
        job_status_store[job_id] = job_data
```

**After:**
```python
    new_store = {}
    for job_id, job_data in active_jobs:
        new_store[job_id] = job_data
    for job_id, job_data in terminal_jobs:
        new_store[job_id] = job_data
    with _job_store_lock:
        job_status_store.clear()
        job_status_store.update(new_store)
```

**Validation:** Run `pytest api/test_audio_processing.py`. Simulate concurrent requests with `asyncio.gather` or `concurrent.futures.ThreadPoolExecutor` to verify no 404s during cleanup.

---

### Group 5: Memory & Resource Management (H-2, H-5)

#### H-2 — `audio_processing.py:610,632` — entire file in memory for full pipeline

**Before:**
```python
audio_bytes = await file.read()
# ...
background_tasks.add_task(_run_pipeline, job_id, audio_bytes, topic, moduleId)
```

**After:**
```python
import tempfile

# Write to temp file
tmp = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename or ".bin")[1])
try:
    content = await file.read()
    tmp.write(content)
    tmp.flush()
    tmp.close()
    temp_path = tmp.name
except Exception:
    tmp.close()
    os.unlink(tmp.name)
    raise

background_tasks.add_task(_run_pipeline, job_id, temp_path, topic, moduleId)
```

Then in `_run_pipeline`, change the signature to accept `temp_path: str` instead of `audio_bytes: bytes`:

```python
def _run_pipeline(job_id: str, temp_path: str, topic: str, module_id: Optional[str]):
    try:
        # Step 1: Transcribe — read file, then delete immediately
        with open(temp_path, "rb") as f:
            audio_bytes = f.read()
        os.unlink(temp_path)
        temp_path = None  # Prevent double-delete

        result = process_audio_file(audio_bytes)
        del audio_bytes  # Free memory before LLM steps
        # ... rest of pipeline
    except Exception as e:
        # ... error handling
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)
```

**Validation:** Upload a 50MB file. Monitor process memory during the refinement/summarization steps — it should drop after transcription.

#### H-5 — `audio_processing.py` — no audio duration validation

Add after transcription in `_run_pipeline` (after line 506):

```python
# Validate audio duration from transcript metadata
duration_seconds = result.get("duration", 0)
MAX_AUDIO_DURATION_SECONDS = 3 * 3600  # 3 hours
if duration_seconds > MAX_AUDIO_DURATION_SECONDS:
    raise ValueError(
        f"Audio duration ({duration_seconds / 3600:.1f} hours) exceeds "
        f"maximum allowed ({MAX_AUDIO_DURATION_SECONDS / 3600:.0f} hours). "
        f"Please upload a shorter recording."
    )
```

**Note:** This requires `process_audio_file` (from `stt.py`) to return `duration` in its result dict. If it doesn't, add an `ffprobe` pre-check:

```python
import subprocess, json as _json

def _get_audio_duration(file_path: str) -> float:
    """Get audio duration in seconds using ffprobe."""
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", file_path],
            capture_output=True, text=True, timeout=30,
        )
        info = _json.loads(result.stdout)
        return float(info["format"]["duration"])
    except Exception:
        return 0  # Unknown duration — don't block
```

**Validation:** Upload a >3 hour audio file (or mock the duration). Confirm it fails with a clear error message before hitting Deepgram.

---

### Group 6: Input Validation & Error Messages (M-1, M-4)

#### M-1 — `audio_processing.py:302-311` — extension-only validation

**Before:**
```python
file_ext = os.path.splitext(file.filename or "")[1].lower()
if file_ext not in allowed_extensions:
    raise HTTPException(...)
```

**After:**
```python
file_ext = os.path.splitext(file.filename or "")[1].lower()
if file_ext not in allowed_extensions:
    raise HTTPException(...)

# Content-type check (secondary validation)
ALLOWED_AUDIO_MIMES = {"audio/mpeg", "audio/wav", "audio/x-m4a", "audio/ogg", "audio/flac", "application/octet-stream"}
if file.content_type and file.content_type not in ALLOWED_AUDIO_MIMES:
    raise HTTPException(
        status_code=400,
        detail=f"Invalid content type '{file.content_type}'. Expected audio file.",
    )
```

Apply similarly to `upload_document` endpoint (line 302).

#### M-4 — `audio_processing.py` — error messages leak internal details

Replace all `str(e)` in HTTP responses with generic messages. Log full details server-side.

**Example (line 637):**
```python
# Before
raise HTTPException(status_code=500, detail=str(e))

# After
logger.error(f"Pipeline start failed: {e}", exc_info=True)
raise HTTPException(status_code=500, detail="Failed to start processing pipeline. Please try again.")
```

Apply to all `HTTPException` and response `error` fields in:
- `start_pipeline` (line 637)
- `upload_document` (line 307-311)
- `transcribe_audio` endpoint
- `refine_transcript` endpoint (line 418)
- `summarize_transcript` endpoint (line 436)
- `generate_pdf_endpoint` endpoint (line 487)

---

### Group 7: Filename Collision & Deduplication (M-2, L-5)

#### M-2 — `audio_processing.py:543-548` and `:450-461`

**Before:**
```python
timestamp = int(time.time())
# ...
filename = f"{safe_title}_{timestamp}.pdf"
```

**After:**
```python
import uuid
# ...
filename = f"{safe_title}_{uuid.uuid4().hex[:8]}.pdf"
```

Apply to both `_run_pipeline` (line 548) and `generate_pdf_endpoint` (line 453).

#### L-5 — Extract shared filename helper

```python
def _make_pdf_filename(topic: str) -> str:
    """Generate a safe, unique PDF filename from a topic string."""
    safe_title = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in topic)
    safe_title = safe_title.replace(" ", "_")[:50]
    return f"{safe_title}_{uuid.uuid4().hex[:8]}.pdf"
```

Replace the duplicated logic at lines 544-548, 450-455, and 320-325 with `_make_pdf_filename(topic)`.

---

### Group 8: Low-Priority Fixes (L-1, L-3, L-4)

#### L-1 — `services/stt.py:111` — docstring timeout mismatch

Update docstring to say "Defaults to 600 (10 minutes)" to match the actual default at line 137.

#### L-3 — `audio_processing.py:497-539` — hardcoded progress percentages

Replace with time-based interpolation or add sub-step callbacks. Minimal fix — add a comment explaining the rationale and consider a weighted approach:

```python
# Weighted progress: transcription (60%), refinement (20%), summarization (10%), PDF (10%)
# Since transcription is the longest step, allocate more progress range
```

#### L-4 — `api/tests/test_audio_processing.py:53-54` — fragile patch target

Change `import audio_processing as ap_module` to `import api.audio_processing as ap_module` and update all mock targets to use `api.audio_processing.` prefix consistently.

---

## Verification Checklist

- [ ] **B-1:** Trigger summarizer failure (e.g., invalid model config). Confirm job status is `"error"`, not a PDF with error text.
- [ ] **B-2:** Trigger JSON decode failure in CoC (e.g., mock LLM to return non-JSON). Confirm job status is `"error"`.
- [ ] **B-3:** Start pipeline via UploadDialog. Confirm `Authorization` header is present in network tab for both start and polling requests.
- [ ] **H-1:** Restart backend server while a job is in progress. Confirm the job can be recovered or returns a clear error (not silent 404).
- [ ] **H-2:** Upload 50MB+ file. Monitor memory — should drop after transcription step completes.
- [ ] **H-3:** Simulate concurrent cleanup calls. No 404s for valid jobs during cleanup.
- [ ] **H-6:** Let a job expire (5 min TTL). Confirm UI shows "Job expired" toast, not infinite spinner.
- [ ] **M-1:** Upload a `.txt` file renamed to `.mp3`. Confirm it's rejected.
- [ ] **M-2:** Two concurrent uploads with same topic. Confirm both get unique PDF filenames.
- [ ] **M-5:** `tsc --noEmit` passes. `noteId` is typed as `string`.
- [ ] **M-6:** Trigger a non-2xx response during polling. Confirm no `.json()` parse crash.
- [ ] **L-1:** Docstring matches actual default.
- [ ] **L-5:** No duplicated filename logic.
- [ ] **All:** `npm run build` passes (frontend). `pytest` passes (backend). `npm run lint` passes.

---

## Risk Notes

1. **Redis dependency (H-1):** If Redis is not available in all environments, the fallback to in-memory + `threading.Lock` must be tested. Consider making Redis optional with a config flag.
2. **Temp file cleanup (H-2):** The `finally` block in `_run_pipeline` must handle the case where the temp file was already deleted (transcription succeeded) vs. never created (error before file write). Use `temp_path = None` sentinel.
3. **`ffprobe` availability (H-5):** Duration validation via `ffprobe` requires it to be installed on the server. If unavailable, fall back to post-transcription duration check only.
4. **Auth header injection (B-3):** Verify that `fetchFormData` in `client.ts` correctly handles `FormData` content-type (must not set `Content-Type` manually — browser sets multipart boundary). Check that `startPipeline` in `audioApi.ts` works identically to the raw `fetch`.
5. **Error message sanitization (M-4):** Don't over-sanitize — developers need actionable errors in logs. Only strip details from client-facing responses.
6. **Breaking change risk (B-1, B-2):** Changing return-to-raise changes the contract of `generate_university_notes` and `transform_transcript`. Any direct callers of these functions (outside `_run_pipeline`) will now see exceptions instead of error strings. Search for all call sites before merging.
