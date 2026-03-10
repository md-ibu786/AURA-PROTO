# External Integrations

**Analysis Date:** 2026-03-10

## APIs & External Services

**Identity & Firebase:**
- Firebase Authentication - email/password sign-in, ID token issuance, custom claims, and admin user lifecycle
  - SDK/Client: `firebase` in `frontend/src/api/firebaseClient.ts`; `firebase-admin` in `api/config.py`, `api/auth.py`, and `api/auth_sync.py`
  - Auth: frontend `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN`, `VITE_FIREBASE_PROJECT_ID`, `VITE_FIREBASE_APP_ID`; backend credential path via `FIREBASE_CREDENTIALS`, `GOOGLE_APPLICATION_CREDENTIALS`, or `GOOGLE_AUTH_CREDENTIALS` in `frontend/.env.example`, `.env.example`, and `api/config.py`
- Firebase App Check - browser request integrity using reCAPTCHA Enterprise in `frontend/src/api/firebaseClient.ts`
  - SDK/Client: `firebase/app-check`
  - Auth: `VITE_RECAPTCHA_ENTERPRISE_SITE_KEY` in `frontend/.env.example`

**Speech & AI:**
- Deepgram - speech-to-text transcription for uploaded audio in `services/stt.py` and `api/audio_processing.py`
  - SDK/Client: `deepgram-sdk`
  - Auth: `DEEPGRAM_API_KEY`
- Google Vertex AI Gemini - transcript cleanup, summarization, KG extraction, embeddings, and multimodal processing in `services/vertex_ai_client.py`, `services/coc.py`, `services/summarizer.py`, `services/summary_service.py`, `services/embeddings.py`, and `api/kg_processor.py`
  - SDK/Client: `vertexai`, `google-auth`
  - Auth: ADC/service account via `VERTEX_CREDENTIALS`, `GOOGLE_APPLICATION_CREDENTIALS`, and project selection via `VERTEX_PROJECT`, `VERTEX_LOCATION` in `api/config.py`
- Google Generative AI fallback - legacy/non-Vertex Gemini client shim in `services/genai_client.py`
  - SDK/Client: `google.genai` or `google.generativeai` when importable
  - Auth: one of `GOOGLE_API_KEY`, `GOOGLE_GENAI_API_KEY`, `GOOGLE_GENERATIVEAI_API_KEY`, or `GENAI_API_KEY`

**Developer/Test Services:**
- Firebase Emulator Suite - local Firestore/Auth test environment in `firebase.json`, `package.json`, and `frontend/package.json`
  - SDK/Client: Firebase CLI invoked by npm scripts
  - Auth: local emulator, no external secret required

## Data Storage

**Databases:**
- Firebase Firestore - primary operational store for users, hierarchy, notes, and KG task status in `api/config.py`, `api/notes.py`, `api/users.py`, and `firestore.rules`
  - Connection: `USE_REAL_FIREBASE`, `FIREBASE_CREDENTIALS`, `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_AUTH_CREDENTIALS`
  - Client: Firebase Admin SDK / Google Cloud Firestore client in `api/config.py`
- Mock Firestore - in-memory local-development substitute selected when `USE_REAL_FIREBASE=false` in `api/config.py` and implemented in `api/mock_firestore.py`
  - Connection: `USE_REAL_FIREBASE=false`
  - Client: `MockFirestoreClient` via `api/mock_firestore.py`
- Neo4j - knowledge graph persistence, traversal, vector index checks, and subgraph retrieval in `api/neo4j_config.py`, `api/kg_processor.py`, and `api/graph_manager.py`
  - Connection: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`
  - Client: official `neo4j` Python driver

**File Storage:**
- Local filesystem only - uploaded documents and generated PDFs are written under `pdfs/` and served by FastAPI from `api/main.py` and `api/audio_processing.py`

**Caching:**
- Redis - summary caching and async task broker/result backend in `api/cache.py`, `services/summary_service.py`, and `api/tasks/document_processing_tasks.py`

## Authentication & Identity

**Auth Provider:**
- Firebase Auth with backend token verification and Firestore-backed RBAC in `frontend/src/stores/useAuthStore.ts`, `api/auth.py`, and `documentations/api-authentication.md`
  - Implementation: frontend signs in with Firebase JS SDK, sends Bearer ID token to FastAPI, backend verifies with Firebase Admin SDK, then loads role/status from Firestore
- Mock auth mode exists for local dev/E2E in `frontend/src/stores/useAuthStore.ts`, `api/auth.py`, and `frontend/playwright.config.ts`
  - Implementation: mock tokens in localStorage plus backend mock-token acceptance when `TESTING=true` and real Firebase is disabled

## Monitoring & Observability

**Error Tracking:**
- None detected as an external SaaS service

**Logs:**
- Python logging/structured logger usage in `api/main.py`, `api/logging_config.py`, `api/tasks/document_processing_tasks.py`, and `services/summary_service.py`
- Frontend uses browser console warnings/errors for auth and App Check failures in `frontend/src/api/firebaseClient.ts` and `frontend/src/api/client.ts`

## CI/CD & Deployment

**Hosting:**
- Not explicitly wired to a managed host; repo supplies Docker images for backend and frontend in `api/Dockerfile` and `frontend/Dockerfile`

**CI Pipeline:**
- GitHub Actions runs Firestore security-rules tests on push/PR in `.github/workflows/firestore-rules.yml`

## Environment Configuration

**Required env vars:**
- Backend/Firebase: `USE_REAL_FIREBASE`, `ENVIRONMENT`, `ALLOWED_ORIGINS`, `FIREBASE_CREDENTIALS`, `GOOGLE_APPLICATION_CREDENTIALS`, `GOOGLE_AUTH_CREDENTIALS`, `TESTING`, `FIREBASE_PROJECT_ID` in `.env.example`, `api/main.py`, and `api/config.py`
- Vertex/Gemini: `VERTEX_PROJECT`, `VERTEX_LOCATION`, `VERTEX_CREDENTIALS`, `LLM_ENTITY_EXTRACTION_MODEL`, `LLM_SUMMARIZATION_MODEL`, `EMBEDDING_MODEL`, `AURA_TEST_MODE` in `api/config.py` and `services/vertex_ai_client.py`
- Deepgram: `DEEPGRAM_API_KEY` in `services/stt.py`
- Neo4j/Redis/Celery: `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD`, `REDIS_URL`, `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB`, `REDIS_PASSWORD`, `CELERY_RESULT_EXPIRES` in `.env.template`, `api/config.py`, `api/cache.py`, and `api/tasks/CELERY_CONFIG.md`
- Frontend Firebase/App Check: `VITE_FIREBASE_API_KEY`, `VITE_FIREBASE_AUTH_DOMAIN`, `VITE_FIREBASE_PROJECT_ID`, `VITE_FIREBASE_STORAGE_BUCKET`, `VITE_FIREBASE_MESSAGING_SENDER_ID`, `VITE_FIREBASE_APP_ID`, `VITE_RECAPTCHA_ENTERPRISE_SITE_KEY`, `VITE_USE_MOCK_AUTH` in `frontend/.env.example` and `frontend/src/api/firebaseClient.ts`
- E2E: `E2E_ADMIN_EMAIL`, `E2E_ADMIN_PASSWORD`, `E2E_STAFF_EMAIL`, `E2E_STAFF_PASSWORD`, `E2E_STUDENT_EMAIL`, `E2E_STUDENT_PASSWORD`, `PLAYWRIGHT_BASE_URL` in `frontend/.env.e2e.example` and `frontend/e2e/fixtures.ts`

**Secrets location:**
- Root `.env` file present - contains backend environment configuration
- `frontend/.env` file present - contains frontend environment configuration
- Safe templates are in `.env.example`, `.env.template`, `frontend/.env.example`, and `frontend/.env.e2e.example`
- Firebase service-account JSON files are expected at repo-relative paths referenced by `.env.example`, `api/config.py`, and `tools/verify_firebase_config.py`

## Webhooks & Callbacks

**Incoming:**
- None detected; the repo exposes REST endpoints only in `api/main.py`, `api/auth_sync.py`, and `api/audio_processing.py`

**Outgoing:**
- No webhook dispatchers detected; outbound calls are SDK/API requests to Firebase, Deepgram, Vertex AI, Neo4j, and Redis from `api/config.py`, `services/stt.py`, `services/vertex_ai_client.py`, `api/neo4j_config.py`, and `api/cache.py`

---

*Integration audit: 2026-03-10*
