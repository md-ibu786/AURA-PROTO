# External Integrations

**Analysis Date:** 2025-01-20

## APIs & External Services

**AI/ML Services:**
- Google Vertex AI - LLM and embeddings
  - SDK: `vertexai` 1.64.0
  - Models Used:
    - `gemini-2.5-flash-lite` - Entity extraction and summarization
    - `text-embedding-004` - Vector embeddings
  - Auth: Google Application Default Credentials (ADC)
  - Environment Variables:
    - `VERTEX_PROJECT` - GCP project ID (default: `lucky-processor-480412-n8`)
    - `VERTEX_LOCATION` - Region (default: `us-central1`)
    - `GOOGLE_APPLICATION_CREDENTIALS` - Path to service account JSON
  - Implementation: `services/vertex_ai_client.py`
  - Usage:
    - Entity extraction: `services/llm_entity_extractor.py`
    - Note summarization: `services/summarizer.py`
    - Transcript refinement: `services/coc.py`
    - Embeddings: `services/embeddings.py`
  - Safety: Disabled for academic content (`block_none_safety_settings()`)

- Google Generative AI (Legacy) - Backup Gemini client
  - SDK: `google-generativeai` 0.8.3
  - Implementation: `services/genai_client.py`
  - Auth: API key via environment variables
    - `GOOGLE_API_KEY` or `GOOGLE_GENAI_API_KEY` or `GENAI_API_KEY`
  - Note: Provides backward compatibility shim; delegates to Vertex AI

- Deepgram - Speech-to-text transcription
  - SDK: `deepgram-sdk` 3.5.0
  - Implementation: `services/stt.py`
  - Auth: API key
    - Environment variable: `DEEPGRAM_API_KEY`
  - Usage: Transcribes uploaded audio files in audio processing pipeline
  - Endpoint: `POST /api/audio/transcribe`
  - Supported formats: .mp3, .wav, .m4a, .ogg, .flac
  - File size limit: 100MB max

**Search & Data Retrieval:**
- Web Search - External web search capability
  - Package: `web-search` 0.6.2
  - Implementation location: Not detected in current API codebase
  - Note: Listed in root `package.json` dependencies

## Data Storage

**Databases:**

**Firestore (Primary Document Store):**
- Type: NoSQL document database
- Provider: Google Firebase
- Backend SDK: `firebase-admin` 6.5.0
  - Sync client: `firebase_admin.firestore`
  - Async client: `google-cloud-firestore` 2.16.0 (`AsyncClient`)
- Frontend SDK: `firebase` 12.8.0
  - Client location: `frontend/src/api/firebaseClient.ts`
- Auth: Service account key
  - Backend: `FIREBASE_CREDENTIALS` env var → `serviceAccountKey-auth.json`
  - Frontend: Firebase config object with API keys
- Configuration:
  - Database initialization: `api/config.py`
  - Security rules: `firestore.rules`
  - Indexes: `firestore.indexes.json`
- Collections:
  - `departments` - Academic departments
  - `semesters` - Semester hierarchy (subcollection of departments)
  - `subjects` - Subjects within semesters
  - `modules` - Course modules within subjects
  - `notes` - Lecture notes and documents
  - `users` - User profiles and permissions
- Emulator Support:
  - Port: 8080 (configured in `firebase.json`)
  - UI: Port 4000
  - Test mode: `AURA_TEST_MODE=true` for hermetic testing
- Testing:
  - Rules testing: `@firebase/rules-unit-testing` 5.0.0
  - Location: `tests/firestore/` (root), `frontend/src/tests/`
  - Run: `firebase emulators:exec --only firestore "npx jest tests/firestore/"`

**Neo4j (Knowledge Graph):**
- Type: Graph database
- Provider: Neo4j (AuraDB or self-hosted)
- SDK: `neo4j` 5.25.0 (official Python driver)
- Connection:
  - URI: `NEO4J_URI` env var (bolt:// or neo4j+s://)
  - Auth: `NEO4J_USER`, `NEO4J_PASSWORD`
- Configuration: `api/neo4j_config.py`
  - Singleton driver pattern
  - Connection pooling
  - Test mode aware (skips init in `AURA_TEST_MODE`)
- Schema:
  - Nodes: Entity types (Topic, Concept, Methodology, Finding, ParentChunk)
  - Relationships: `ENTITY_RELATIONSHIP_TYPES` (DEFINES, DEPENDS_ON, USES, etc.)
  - Vector indices: parent_chunk_vector_index, topic_vector_index, concept_vector_index, methodology_vector_index, finding_vector_index
  - Fulltext indices: chunk_fulltext_index
- Usage:
  - Knowledge graph processing: `api/kg_processor.py`
  - Entity extraction: `services/llm_entity_extractor.py`
  - Graph visualization: `api/graph_visualizer.py`
  - Cypher queries: `api/NEO4J_QUERIES.md`
- Routers:
  - `api/kg/__init__.py` - KG management endpoints
  - `api/routers/graph_preview.py` - Graph preview API

**Redis (Cache Layer):**
- Type: In-memory key-value store
- Provider: Redis (local or cloud)
- SDK: `redis` 5.2.0
- Connection:
  - Host: `REDIS_HOST` env var (default: localhost)
  - Port: `REDIS_PORT` env var (default: 6379)
  - DB: `REDIS_DB` env var (default: 0)
  - Password: `REDIS_PASSWORD` env var (optional)
- Configuration: `api/cache.py`
  - Singleton client wrapper (`RedisClient`)
  - Graceful degradation when unavailable
  - JSON serialization support
  - Default TTL: 24 hours (86400 seconds)
- Usage:
  - Summary caching: `services/summary_service.py`
  - Embedding caching: Performance optimization
- Test mode: `REDIS_ENABLED=false` to disable
- Health check: Available in `api/main.py`

**File Storage:**
- Local filesystem
  - PDFs: `pdfs/` directory (mounted as static files)
  - Posters: `posters/` directory
  - Generated documents: Stored locally, served via FastAPI StaticFiles
  - Document uploads: Temporary storage during processing
- Static file serving:
  - Mount point: `api/main.py` (FastAPI StaticFiles)
  - Access: `/pdfs/{filename}`

**Caching:**
- Redis (see Redis section above)
- In-memory caches:
  - Job status store: `api/audio_processing.py` (temporary, should use Redis in production)
  - Mock Firestore: `api/mock_firestore.py` (testing only)

## Authentication & Identity

**Auth Provider:**
- Firebase Authentication
  - Backend SDK: `firebase-admin` (auth module)
  - Frontend SDK: `firebase` (getAuth)
  - Implementation:
    - Backend: `api/auth.py`, `api/auth_sync.py`
    - Frontend: `frontend/src/api/firebaseClient.ts`
  - Auth methods: Email/password, custom tokens
  - Token verification: Firebase Admin SDK
  - Custom claims:
    - `role` - User role (admin/staff/student)
    - `status` - Account status (active/inactive)
    - `departmentId` - User's department
  - Emulator support:
    - Port: 9099 (configured in `firebase.json`)
    - Test mode: `VITE_USE_MOCK_AUTH=true` for frontend testing

**App Check (Security):**
- Provider: Firebase App Check with reCAPTCHA Enterprise
- Frontend implementation: `frontend/src/api/firebaseClient.ts`
  - SDK: `firebase/app-check`
  - Provider: `ReCaptchaEnterpriseProvider`
  - Environment variable: `VITE_RECAPTCHA_ENTERPRISE_SITE_KEY`
- Purpose: Verify requests come from legitimate app instances

**Authorization:**
- Role-Based Access Control (RBAC)
  - Roles: admin, staff, student
  - Custom claims in Firebase ID tokens
  - Firestore security rules: `firestore.rules`
    - Helper functions: `isAdmin()`, `isStaff()`, `isStudent()`
    - Per-collection access rules
  - Backend middleware: Token verification in API endpoints
- Department-level permissions:
  - Users scoped to specific departments
  - Cross-department access restricted
  - Admins have global access

## Monitoring & Observability

**Error Tracking:**
- Local logging framework
  - Backend: `api/logging_config.py`
    - Structured logging with `get_logger(name)`
    - Log levels configurable
  - Frontend: Console logging, development only

**Logs:**
- Backend: Python logging to stdout/stderr
  - FastAPI request logging
  - Uvicorn server logs
  - Custom loggers per module
- Frontend: Browser console
  - Development mode: Verbose
  - Production: Minimal

**Metrics:**
- Not detected (no dedicated metrics collection service)
- Health checks:
  - `GET /health_check` - API liveness
  - `GET /readiness_check` - Firestore connectivity check

**Tracing:**
- Not detected (no distributed tracing integration)

## CI/CD & Deployment

**Hosting:**
- Containerized deployment (Docker)
  - Backend: `api/Dockerfile` (Python 3.10-slim, port 8001)
  - Frontend: `frontend/Dockerfile` (Node 20-slim, port 3001)
- Firebase Hosting: Configured via `firebase.json`
  - Firestore rules deployment
  - Firestore indexes deployment

**CI Pipeline:**
- GitHub Actions (potential - `.github/` directory present)
  - Configuration not examined (per security policy)

**Build Artifacts:**
- Backend: No build step, direct Python execution
- Frontend: Vite production build
  - Output: `frontend/dist/`
  - Command: `npm run build`

**Environment Management:**
- Development: `.env` files (not committed)
- Templates: `.env.example`, `frontend/.env.example`
- Environment flag: `ENVIRONMENT` env var (development/staging/production)
- Test mode: `AURA_TEST_MODE`, `TESTING`, `VITE_USE_MOCK_AUTH`

## Environment Configuration

**Required Backend Environment Variables:**
Core:
- `USE_REAL_FIREBASE` - Toggle real Firebase (true/false)
- `ENVIRONMENT` - Deployment environment (development/staging/production)
- `ALLOWED_ORIGINS` - CORS allowed origins (comma-separated)

Firebase:
- `FIREBASE_CREDENTIALS` - Path to service account key JSON
- `FIREBASE_PROJECT_ID` - Firebase project ID

Google Cloud:
- `VERTEX_PROJECT` - GCP project ID for Vertex AI
- `VERTEX_LOCATION` - GCP region (default: us-central1)
- `GOOGLE_APPLICATION_CREDENTIALS` - Path to GCP service account JSON

External Services:
- `DEEPGRAM_API_KEY` - Deepgram speech-to-text API key
- `NEO4J_URI` - Neo4j connection URI
- `NEO4J_USER` - Neo4j username
- `NEO4J_PASSWORD` - Neo4j password
- `REDIS_HOST` - Redis server host (default: localhost)
- `REDIS_PORT` - Redis port (default: 6379)
- `REDIS_DB` - Redis database number (default: 0)
- `REDIS_PASSWORD` - Redis password (optional)

Testing:
- `AURA_TEST_MODE` - Skip external API calls (true/false)
- `TESTING` - Enable test mode (true/false)
- `REDIS_ENABLED` - Enable Redis in tests (default: false)

**Required Frontend Environment Variables:**
Firebase:
- `VITE_FIREBASE_API_KEY` - Firebase Web API key
- `VITE_FIREBASE_AUTH_DOMAIN` - Firebase auth domain
- `VITE_FIREBASE_PROJECT_ID` - Firebase project ID
- `VITE_FIREBASE_STORAGE_BUCKET` - Firebase storage bucket
- `VITE_FIREBASE_MESSAGING_SENDER_ID` - FCM sender ID
- `VITE_FIREBASE_APP_ID` - Firebase app ID
- `VITE_RECAPTCHA_ENTERPRISE_SITE_KEY` - reCAPTCHA site key for App Check

Testing:
- `VITE_USE_MOCK_AUTH` - Use mock authentication (true/false)

**Secrets Location:**
- Service account keys: Root directory (gitignored)
  - `serviceAccountKey-auth.json` - Current Firebase service account
  - `serviceAccountKey-old.json` - Legacy/backup key
- Environment files: `.env` (gitignored)
- Templates: `.env.example`, `frontend/.env.example` (committed)

**Configuration Files:**
- `config.json` - Application configuration (structure not examined)
- `firebase.json` - Firebase emulator and deployment config
- `firestore.rules` - Firestore security rules (deployed to Firebase)
- `firestore.indexes.json` - Firestore composite indexes (deployed to Firebase)

## Webhooks & Callbacks

**Incoming:**
- None detected
- API endpoints are request-response only
- No webhook listeners configured

**Outgoing:**
- None detected
- No external webhook calls
- No event-driven integrations to third-party services

## Background Processing

**Task Queue:**
- Celery 5.4.0
  - Broker: Redis
  - Worker configuration: `api/tasks/__init__.py`
  - Queue name: `kg_processing`
  - Tasks:
    - `process_document_task` - Single document KG processing
    - `process_batch_task` - Batch document processing
  - Worker start: `celery -A api.tasks worker -l info -Q kg_processing`
  - Progress tracking: `get_task_progress(task_id)`
  - Task cancellation: `cancel_task(task_id)`

**Job Processing:**
- Audio pipeline: Background tasks in `api/audio_processing.py`
  - In-memory job store (should migrate to Redis)
  - Status polling: `GET /api/audio/pipeline-status/{job_id}`
  - Pipeline steps: transcribe → refine → summarize → generate PDF

## Internal Service Communication

**Architecture:**
- Monolithic application with modular routers
- Frontend-to-backend: HTTP REST API
  - Base URL: `http://127.0.0.1:8001` (proxied in development)
  - Proxy configuration: `frontend/vite.config.ts`
  - CORS enabled: Configured in `api/main.py`

**API Routers:**
Mounted in `api/main.py`:
- `/api/crud` - Hierarchy CRUD operations (`hierarchy_crud.py`)
- `/api/explorer` - File explorer functionality (`explorer.py`)
- `/api/audio` - Audio processing pipeline (`audio_processing.py`)
- `/api/auth` - Authentication sync (`auth_sync.py`)
- `/api/users` - User management (`users.py`)
- `/modules` - Module operations (`api/modules/__init__.py`)
- `/kg` - Knowledge graph operations (`api/kg/__init__.py`)
- `/hierarchy` - Hierarchy management (`api/hierarchy/__init__.py`)
- `/api/summaries` - Summary endpoints (`api/routers/summaries.py`)
- `/api/trends` - Trend analysis (`api/routers/trends.py`)
- `/api/templates` - Template management (`api/routers/templates.py`)
- `/api/schema` - Schema operations (`api/routers/schema.py`)
- `/api/graph-preview` - Graph preview (`api/routers/graph_preview.py`)

**Middleware:**
- CORS: `CORSMiddleware` from FastAPI
  - Allowed origins: `ALLOWED_ORIGINS` env var
- Rate limiting: `SlowAPIMiddleware`
  - Configuration: `api/limiter.py`
- Request logging: Custom middleware (if present in `api/main.py`)

**Static File Serving:**
- PDFs: `/pdfs/{filename}` → `pdfs/` directory
- Configuration: FastAPI `StaticFiles` mount in `api/main.py`

**Inter-service Dependencies:**
- Services layer: `services/` directory
  - Document parsers: `services/document_parsers/`
  - Multimodal processing: `services/multimodal/`
- Shared utilities:
  - Schema validation: `api/schema_validator.py`
  - Models: `api/models.py`
  - Validators: `api/validators.py`

**Database Access Patterns:**
- Firestore: Direct SDK calls via `config.db` and `config.async_db`
- Neo4j: Driver sessions via `neo4j_config.neo4j_driver`
- Redis: Wrapper client via `cache.redis_client`

---

*Integration audit: 2025-01-20*
