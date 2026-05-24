# Audio Processing Pipeline Review

**Reviewer:** Review Subagent  
**Date:** 2026-05-24  
**Scope:** `api/audio_processing.py`, `frontend/src/api/audioApi.ts`, `api/tasks/document_processing_tasks.py`, `api/models.py`, plus supporting services (`services/stt.py`, `services/coc.py`, `services/summarizer.py`, `services/pdf_generator.py`) and the consuming UI (`UploadDialog.tsx`, `FileSystemNode.ts`)

---

## Review

### BLOCKER — Must Fix Before Production

#### B-1. Summarizer returns error text instead of raising — silent corrupt PDF generation
- **File:** `services/summarizer.py` lines 88–92
- **Severity:** Critical
- **Issue:** `generate_university_notes()` catches exceptions and returns `"Note Generation Failed: {str(e)}"` as a *string* instead of raising. The `_run_pipeline` function in `audio_processing.py` receives this string, treats it as valid notes content, and passes it to `create_pdf()`. The user gets a PDF titled "Lecture Notes" whose body is literally `"Note Generation Failed: ..."`.
- **Evidence:**
  ```python
  # summarizer.py line 90
  except Exception as e:
      ...
      return f"Note Generation Failed: {str(e)}"
  ```
  ```python
  # audio_processing.py _run_pipeline, line ~418
  notes = generate_university_notes(topic, refined)  # gets error string
  # ... proceeds to create_pdf(notes, topic, filepath) with error text
  ```
- **Fix:** Raise the exception instead of returning it, so `_run_pipeline`'s outer `except` catches it and sets the job to error status.

---

#### B-2. CoC (refinement) returns error string on JSON decode failure — same silent corruption
- **File:** `services/coc.py` line 201
- **Severity:** Critical
- **Issue:** `transform_transcript()` returns `"Error: Model failed to return valid JSON."` on JSON parse failure. The pipeline treats this as a valid refined transcript and feeds it to the summarizer. The summarizer then generates notes from an error string.
- **Evidence:**
  ```python
  # coc.py line 199-201
  except json.JSONDecodeError:
      return "Error: Model failed to return valid JSON."
  ```
- **Fix:** Raise a `ValueError` with a descriptive message so the pipeline fails fast.

---

#### B-3. Frontend bypasses auth headers on pipeline requests
- **File:** `frontend/src/components/explorer/UploadDialog.tsx` lines 119–123 and 272–278
- **Severity:** Critical
- **Issue:** `UploadDialog` uses raw `fetch()` to start the pipeline and poll status, bypassing `audioApi.ts`'s `startPipeline()` and `getPipelineStatus()` which go through `fetchFormData`/`fetchApi` in `client.ts`. Those wrappers inject the `Authorization: Bearer <token>` header via `getAuthHeader()`. The raw `fetch()` calls have **no auth headers**, so:
  1. If the backend enforces auth, these requests will fail with 401.
  2. The 401 retry logic from `executeWithRetry` is completely bypassed.
- **Evidence:**
  ```tsx
  // UploadDialog.tsx line 119-123 (polling)
  const response = await fetch(`/api/audio/pipeline-status/${processing.jobId}`);
  
  // UploadDialog.tsx line 272-278 (start)
  const response = await fetch('/api/audio/process-pipeline', {
      method: 'POST',
      body: formData,
  });
  ```
  vs. `audioApi.ts` which properly uses:
  ```typescript
  export async function startPipeline(...) {
      return fetchFormData('/audio/process-pipeline', formData);  // includes auth
  }
  ```
- **Fix:** Replace the raw `fetch()` calls in `UploadDialog.tsx` with imports from `audioApi.ts`.

---

### HIGH — Should Fix Soon

#### H-1. In-memory job store lost on server restart
- **File:** `api/audio_processing.py` line 103
- **Severity:** High
- **Issue:** `job_status_store = {}` is a plain Python dict. If the server restarts (deploy, crash, scaling), all in-progress and recently-completed jobs are silently lost. Users polling a job will get a 404 with no explanation.
- **Evidence:** The comment on line 103 says *"for demo; use Redis in production"* — but this is the production code path.
- **Fix:** Use Redis (already available via `REDIS_URL` in `config.py`) with a TTL matching `JOB_STATUS_TTL_SECONDS`. A simple `redis.set(f"job:{job_id}", json.dumps(data), ex=300)` would be a minimal replacement.

---

#### H-2. Entire audio file held in memory for full pipeline duration
- **File:** `api/audio_processing.py` lines 394–396
- **Severity:** High
- **Issue:** `start_pipeline` reads the entire file into `audio_bytes` (up to 100MB) and passes it to `_run_pipeline` as a background task argument. The bytes remain in memory through all 4 pipeline steps (transcription, refinement, summarization, PDF generation), but only transcription needs them. With concurrent users uploading large files, this can exhaust server memory.
- **Evidence:**
  ```python
  audio_bytes = await file.read()  # Up to 100MB
  # ...
  background_tasks.add_task(_run_pipeline, job_id, audio_bytes, topic, moduleId)
  # audio_bytes stays alive until _run_pipeline returns
  ```
- **Fix:** Write the audio to a temp file, pass the path to `_run_pipeline`, read+delete in the transcription step. Use `tempfile.NamedTemporaryFile(delete=False)`.

---

#### H-3. Race condition in `_cleanup_job_store`
- **File:** `api/audio_processing.py` lines 161–175
- **Severity:** High
- **Issue:** `_cleanup_job_store()` calls `job_status_store.clear()` then iterates to rebuild it. Between `clear()` and the rebuild, any concurrent request reading `job_status_store` sees an empty dict and returns 404 for valid jobs. Python's GIL does not protect multi-step operations.
- **Evidence:**
  ```python
  # line 171
  job_status_store.clear()          # ← All jobs disappear
  for job_id, job_data in active_jobs:
      job_status_store[job_id] = job_data  # ← Slowly rebuilding
  ```
- **Fix:** Build the new dict locally, then atomically replace:
  ```python
  new_store = {}
  for job_id, job_data in active_jobs + terminal_jobs:
      new_store[job_id] = job_data
  job_status_store.clear()
  job_status_store.update(new_store)
  ```
  Or better: use a `threading.Lock` around all reads/writes to `job_status_store`.

---

#### H-4. No timeout on LLM calls (refinement + summarization)
- **File:** `services/coc.py`, `services/summarizer.py`
- **Severity:** High
- **Issue:** Both `transform_transcript` and `generate_university_notes` call `router.generate()` without any timeout. If the Gemini API hangs or is extremely slow, the `_run_pipeline` background task blocks indefinitely. FastAPI's `BackgroundTasks` has no built-in timeout or cancellation mechanism.
- **Fix:** Wrap `_run_sync(router.generate(...))` in a `concurrent.futures.ThreadPoolExecutor` with a timeout, or use `asyncio.wait_for` at the router level. At minimum, add an overall timeout to `_run_pipeline` (e.g., 30 minutes).

---

#### H-5. No audio duration/length validation — unbounded API cost
- **File:** `api/audio_processing.py`
- **Severity:** High
- **Issue:** Only file size is checked (100MB max). A 100MB WAV file could be ~90 minutes of audio; a compressed 100MB MP3 could be 10+ hours. Each minute of audio costs Deepgram credits plus two Gemini API calls (refinement + summarization). There is no guard against a user uploading a 6-hour lecture recording.
- **Fix:** After transcription (when duration is known from Deepgram's response), check the audio duration and fail gracefully if it exceeds a threshold (e.g., 3 hours). Alternatively, validate duration via a quick ffprobe call before sending to Deepgram.

---

#### H-6. Frontend polling never stops on 404 (job expired/evicted)
- **File:** `frontend/src/components/explorer/UploadDialog.tsx` lines 114–147
- **Severity:** High
- **Issue:** When the job is evicted from the in-memory store (TTL = 5 minutes), the backend returns 404. The frontend's `pollStatus` catch block only logs the error — it does not stop polling or show an error to the user. The user sees a perpetual "Processing..." spinner.
- **Evidence:**
  ```tsx
  } catch (err) {
      console.error('Status poll error:', err);
      // No setMode, no setError, no clearInterval
  }
  ```
- **Fix:** Check `response.status` inside `pollStatus`. If 404, stop polling and show "Job expired or not found" error.

---

### MEDIUM — Fix When Convenient

#### M-1. File extension only — no content-type or magic byte validation
- **File:** `api/audio_processing.py` lines 230–235, 185–192
- **Severity:** Medium
- **Issue:** Audio and document files are validated only by extension. A renamed text file (`notes.mp3`) passes validation and wastes Deepgram API credits. `UploadFile.content_type` is never checked.
- **Fix:** Check `file.content_type` against expected MIME types as a second validation layer. For audio, also verify the first few bytes match known magic bytes (e.g., ID3 for MP3, RIFF for WAV).

---

#### M-2. PDF filename collision risk
- **File:** `api/audio_processing.py` lines 320–325 and 440–445
- **Severity:** Medium
- **Issue:** PDFs are named `{safe_title}_{timestamp}.pdf` where `timestamp = int(time.time())`. Two concurrent requests processing the same topic within the same second produce identical filenames, causing file overwrites.
- **Fix:** Use `uuid.uuid4().hex[:8]` in the filename, or use the job ID.

---

#### M-3. No cancellation support for in-progress jobs
- **Severity:** Medium
- **Issue:** Once started, a pipeline job cannot be cancelled. FastAPI `BackgroundTasks` provides no cancellation API. The frontend has no cancel button. If a user closes the dialog, the backend keeps running (consuming Deepgram/Gemini credits) until completion.
- **Fix:** Check a cancellation flag (in Redis) at each pipeline step boundary. Add a cancel button to the frontend that calls a cancel endpoint.

---

#### M-4. Error messages leak internal details
- **File:** `api/audio_processing.py` multiple endpoints
- **Severity:** Medium
- **Issue:** Raw `str(e)` is returned to the client in error responses. This can expose internal file paths, connection strings, stack traces, and library versions.
- **Evidence:**
  ```python
  raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
  return TranscribeResponse(success=False, error=f"Transcription failed: {error_msg}")
  ```
- **Fix:** Return generic messages to the client; log the full exception server-side.

---

#### M-5. Frontend `ProcessingState.noteId` type mismatch
- **File:** `frontend/src/components/explorer/UploadDialog.tsx` line 52
- **Severity:** Medium
- **Issue:** `ProcessingState` defines `noteId?: number` but the backend returns a string (Firestore document ID). The canonical type in `FileSystemNode.ts` (`PipelineStatus`) correctly defines `noteId?: string`.
- **Fix:** Change to `noteId?: string` in `UploadDialog.tsx`'s `ProcessingState`.

---

#### M-6. Frontend poll status does not handle non-JSON error responses
- **File:** `frontend/src/components/explorer/UploadDialog.tsx` line 121–122
- **Severity:** Medium
- **Issue:** `const data = await response.json()` is called without first checking `response.ok`. If the server returns a non-JSON error (e.g., 502 from a reverse proxy), `.json()` throws a parse error that is caught by the outer `catch` but gives a confusing error message.
- **Fix:** Check `response.ok` before calling `.json()`.

---

### LOW — Nice to Have

#### L-1. stt.py docstring timeout mismatch
- **File:** `services/stt.py` lines 111 vs 137
- **Severity:** Low
- **Issue:** Docstring says *"Defaults to 10800 (3 hours)"* but actual default is `600.0` (10 minutes).
- **Fix:** Update docstring to say "Defaults to 600 (10 minutes)".

---

#### L-2. No orphaned PDF cleanup
- **Severity:** Low
- **Issue:** If the pipeline fails *after* creating the PDF but *before* saving the note record (e.g., Firestore error), the PDF file remains on disk with no database reference. No garbage collection mechanism exists.
- **Fix:** Periodic job to scan `pdfs/` and cross-reference with Firestore note records, or save the note record *before* PDF generation.

---

#### L-3. `_run_pipeline` progress percentages are hardcoded and don't reflect actual step durations
- **File:** `api/audio_processing.py` lines 399–448
- **Severity:** Low
- **Issue:** Progress jumps from 10→35→60→85→100 regardless of actual time spent. A 2-hour transcription might show 10% for 20 minutes, then jump to 60% when refinement finishes in 30 seconds. This gives a misleading progress experience.
- **Fix:** Use time-based progress interpolation within steps, or at minimum use more granular progress callbacks from the LLM/STT services.

---

#### L-4. `test_audio_processing.py` patches at `api.audio_processing` but imports as `audio_processing`
- **File:** `api/tests/test_audio_processing.py` lines 53–54 vs 72–77
- **Severity:** Low
- **Issue:** Module is imported as `import audio_processing as ap_module` but mocks target `api.audio_processing.process_audio_file`. This works due to Python's module resolution but is fragile.
- **Fix:** Use consistent patch target with the import path.

---

#### L-5. Duplicate code for safe filename generation
- **File:** `api/audio_processing.py` lines 320–325 and 440–445 (PDF gen), lines 250–255 (doc upload)
- **Severity:** Low
- **Issue:** The same safe-title + timestamp filename generation logic is repeated in three places.
- **Fix:** Extract to a shared helper function.

---

## Summary Table

| ID | Severity | File | Issue |
|----|----------|------|-------|
| B-1 | **Critical** | `services/summarizer.py` | Returns error text instead of raising — corrupt PDF generated |
| B-2 | **Critical** | `services/coc.py` | Returns error string on JSON failure — pipeline proceeds with garbage |
| B-3 | **Critical** | `UploadDialog.tsx` | Bypasses `audioApi.ts` — no auth headers on pipeline requests |
| H-1 | High | `audio_processing.py` | In-memory job store lost on restart |
| H-2 | High | `audio_processing.py` | 100MB audio held in memory for full pipeline duration |
| H-3 | High | `audio_processing.py` | Race condition in `_cleanup_job_store` (clear + rebuild) |
| H-4 | High | `coc.py`, `summarizer.py` | No timeout on LLM calls |
| H-5 | High | `audio_processing.py` | No audio duration validation — unbounded API cost |
| H-6 | High | `UploadDialog.tsx` | Polling never stops on 404 — infinite spinner |
| M-1 | Medium | `audio_processing.py` | Extension-only validation, no content-type check |
| M-2 | Medium | `audio_processing.py` | PDF filename collision on concurrent same-second requests |
| M-3 | Medium | Pipeline-wide | No cancellation support for in-progress jobs |
| M-4 | Medium | `audio_processing.py` | Error messages leak internal details |
| M-5 | Medium | `UploadDialog.tsx` | `noteId` typed as `number` but backend returns `string` |
| M-6 | Medium | `UploadDialog.tsx` | No `response.ok` check before `.json()` in polling |
| L-1 | Low | `services/stt.py` | Docstring says 3hr timeout, actual default is 10min |
| L-2 | Low | Pipeline-wide | No orphaned PDF cleanup |
| L-3 | Low | `audio_processing.py` | Hardcoded progress jumps misleading |
| L-4 | Low | `test_audio_processing.py` | Fragile patch target path |
| L-5 | Low | `audio_processing.py` | Duplicated safe-filename logic (3 locations) |

---

## What's Already Good

- **File headers:** All files follow the mandatory header convention consistently.
- **Fallback imports:** Service imports in `audio_processing.py` gracefully degrade when dependencies are missing (lines 68–100).
- **DB failure handling:** The pipeline correctly treats PDF generation as the critical path and logs DB failures as warnings (tested in `test_audio_processing.py`).
- **Input validation:** File size limits, empty file checks, and extension validation are present.
- **Cleanup mechanism:** `_cleanup_job_store` has a reasonable design with TTL + max-entry eviction — the race condition is the implementation bug, not a design flaw.
- **Type definitions:** `FileSystemNode.ts` has clean, well-documented types that mirror the backend Pydantic models.
- **Deepgram SDK usage:** `stt.py` properly supports SDK v5 with timeout configuration and paragraph extraction fallback.
- **Document processing tasks:** `document_processing_tasks.py` has excellent Celery configuration (acks_late, retry backoff, soft/hard time limits, idempotency checks).
