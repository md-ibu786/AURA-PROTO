# Technology Stack

**Analysis Date:** 2026-03-10

## Languages

**Primary:**
- Python 3.10 - backend API, KG processing, async tasks, and tooling in `api/main.py`, `api/kg_processor.py`, `api/tasks/document_processing_tasks.py`, and `tools/verify_firebase_config.py`
- TypeScript 5.6 - React frontend, frontend Playwright tests, and typed API client code in `frontend/package.json`, `frontend/src/api/client.ts`, and `frontend/playwright.config.ts`

**Secondary:**
- JavaScript - root Firebase rules tests and emulator helpers in `package.json` and `tests/firestore/rules-test-utils.js`
- Firestore Rules - security policy for Cloud Firestore in `firestore.rules`
- YAML - CI workflow configuration in `.github/workflows/firestore-rules.yml`
- Markdown - operational docs and runbooks in `README.md`, `documentations/api-authentication.md`, and `api/tasks/CELERY_CONFIG.md`

## Runtime

**Environment:**
- Python runtime targets 3.10+; container image is `python:3.10-slim` in `api/Dockerfile`
- Node.js runtime is required for frontend and test tooling; container image is `node:20-slim` in `frontend/Dockerfile`
- Local backend entrypoint is Uvicorn serving FastAPI on port 8001 in `api/main.py`
- Local frontend dev server is Vite on port 5174 with proxying to the backend in `frontend/vite.config.ts`

**Package Manager:**
- `pip` with pinned `requirements.txt` in `requirements.txt`
- `npm` with lockfiles in `package-lock.json`, `frontend/package.json`
- Lockfile: present (`package-lock.json`, `frontend/package-lock.json`)

## Frameworks

**Core:**
- FastAPI 0.115.0 - backend HTTP API and router composition in `requirements.txt` and `api/main.py`
- React 18.3.1 - frontend UI runtime in `frontend/package.json`
- Vite 6.0.5 - frontend build/dev server in `frontend/package.json` and `frontend/vite.config.ts`
- Firebase JS SDK 12.8.0 - browser auth/app-check client in `frontend/package.json` and `frontend/src/api/firebaseClient.ts`
- Firebase Admin SDK 6.5.0 - backend auth and Firestore access in `requirements.txt`, `api/config.py`, and `api/auth_sync.py`

**Testing:**
- Vitest 3.2.4 - frontend unit tests, configured inline in `frontend/vite.config.ts`
- Playwright 1.50.0 - frontend/browser E2E in `frontend/package.json` and `frontend/playwright.config.ts`
- Jest 29.7.0 - Firestore rules tests via emulator in `frontend/package.json` and `package.json`
- Pytest 8.3.3 - backend tests in `requirements.txt` and `api/tests/test_rbac.py`

**Build/Dev:**
- TypeScript compiler 5.6.x - type-check/build pipeline in `frontend/package.json` and `frontend/tsconfig.app.json`
- Tailwind CSS utilities are used in the frontend component layer; utility merger packages are declared in `frontend/package.json` and consumed via `frontend/src/lib/cn.ts`
- Celery 5.4.0 - async KG task execution in `requirements.txt` and `api/tasks/document_processing_tasks.py`
- Docker - separate frontend/backend container definitions in `frontend/Dockerfile` and `api/Dockerfile`
- Firebase CLI / emulators - local Firestore/Auth emulator workflow in `package.json`, `frontend/package.json`, and `firebase.json`

## Key Dependencies

**Critical:**
- `firebase-admin` / `google-cloud-firestore` - primary auth and operational data store access in `api/config.py`, `api/auth.py`, and `api/notes.py`
- `firebase` - frontend sign-in and App Check integration in `frontend/src/api/firebaseClient.ts` and `frontend/src/stores/useAuthStore.ts`
- `neo4j` - knowledge graph storage and traversal in `api/neo4j_config.py`, `api/kg_processor.py`, and `api/graph_manager.py`
- `vertexai` / `google-auth` - Gemini and embedding calls over Vertex AI in `api/config.py` and `services/vertex_ai_client.py`
- `deepgram-sdk` - speech-to-text transcription in `services/stt.py`

**Infrastructure:**
- `redis` - cache client and Celery broker/backend in `api/cache.py` and `api/tasks/document_processing_tasks.py`
- `slowapi` - rate limiting in `api/main.py` and `api/auth_sync.py`
- `python-dotenv` - root env loading in `api/main.py` and `api/config.py`
- `PyMuPDF`, `python-docx`, `tiktoken`, `tenacity`, `numpy`, `json-repair` - document parsing, tokenization, retries, embeddings, and KG pipeline helpers in `requirements.txt` and `api/kg_processor.py`
- `@tanstack/react-query`, `zustand`, `react-router-dom`, `framer-motion`, `lucide-react`, `sonner` - frontend state, routing, motion, and UI behavior in `frontend/package.json`

## Configuration

**Environment:**
- Root backend env is loaded from `.env` by `api/main.py` and `api/config.py`; safe templates exist in `.env.example` and `.env.template`
- Frontend env is consumed via Vite `import.meta.env` in `frontend/src/api/firebaseClient.ts` and `frontend/src/stores/useAuthStore.ts`; safe templates exist in `frontend/.env.example` and `frontend/.env.e2e.example`
- Firebase local test infrastructure is configured through `firebase.json`, `firestore.rules`, and `firestore.indexes.json`
- TypeScript path alias `@/*` is configured in `frontend/tsconfig.app.json` and mirrored in `frontend/vite.config.ts`

**Build:**
- Frontend build/test config lives in `frontend/package.json`, `frontend/vite.config.ts`, `frontend/playwright.config.ts`, and `frontend/tsconfig.app.json`
- Backend runtime/security config lives in `api/main.py`, `api/config.py`, `api/cache.py`, and `api/neo4j_config.py`
- CI config currently covers Firestore rules testing only in `.github/workflows/firestore-rules.yml`

## Platform Requirements

**Development:**
- Python 3.10+ with the root virtualenv expected by `AGENTS.md` and `api/Dockerfile`
- Node.js for frontend, Playwright, Jest, and Firebase emulators; repo docs show Node 16+ in `README.md`, while container config uses Node 20 in `frontend/Dockerfile`
- Local services assumed by default config: backend on `127.0.0.1:8001`, frontend on `5174`, Neo4j on `127.0.0.1:7687`, Redis on `127.0.0.1:6379`, Firestore emulator on `8080`, and Auth emulator on `9099` in `frontend/vite.config.ts`, `api/config.py`, `api/neo4j_config.py`, `api/tasks/CELERY_CONFIG.md`, and `firebase.json`
- Google credentials are required for real Firebase and Vertex AI modes via service-account/ADC paths referenced in `api/config.py`, `.env.example`, and `tools/verify_firebase_config.py`

**Production:**
- Deployment target is not fully codified; the repo provides standalone Docker images for API and frontend in `api/Dockerfile` and `frontend/Dockerfile`
- Production security posture assumes explicit CORS origins and HTTPS headers from `api/main.py`
- Background KG processing assumes Redis plus a separate Celery worker process as documented in `api/tasks/document_processing_tasks.py` and `api/tasks/CELERY_CONFIG.md`

---

*Stack analysis: 2026-03-10*
