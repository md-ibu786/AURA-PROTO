# Technology Stack

**Analysis Date:** 2025-01-20

## Languages

**Primary:**
- Python 3.10+ - Backend API and services
- TypeScript 5.6.2 - Frontend application and type system
- JavaScript (ES2020+) - Build tooling and test configuration

**Secondary:**
- Cypher - Neo4j graph database queries (in `api/NEO4J_QUERIES.md`)
- Markdown - Documentation and formatted content

## Runtime

**Environment:**
- Python 3.10+ (backend runtime)
  - Virtual environment: `.venv/`
  - Package manager: pip
- Node.js 20+ (frontend runtime)
  - Package manager: npm
  - Lockfile: `package-lock.json` (present)

**Package Managers:**
- pip (Python backend)
  - Requirements: `requirements.txt`
  - Development dependencies included
- npm (JavaScript/TypeScript frontend)
  - Config: `frontend/package.json`
  - Lockfile: `frontend/package-lock.json` (present)

## Frameworks

**Core Backend:**
- FastAPI 0.115.0 - REST API framework
  - Entry point: `api/main.py`
  - Router pattern for modular endpoints
  - Pydantic for request/response validation
- Uvicorn[standard] 0.32.0 - ASGI web server
  - Run command: `uvicorn main:app --reload --port 8001`

**Core Frontend:**
- React 18.3.1 - UI library
  - Entry point: `frontend/src/main.tsx`
  - React Router DOM 7.1.0 for routing
- Vite 6.0.5 - Build tool and dev server
  - Config: `frontend/vite.config.ts`
  - Dev server port: 5174
  - Build output: `frontend/dist/`

**UI Component Libraries:**
- Radix UI (@radix-ui/react-slot 1.2.4) - Headless components
- Framer Motion 12.24.12 - Animation library
- Lucide React 0.468.0 - Icon library
- Tailwind CSS (via tailwind-merge 3.4.0) - Utility-first CSS
- Class Variance Authority 0.7.1 - Component variants
- Sonner 2.0.7 - Toast notifications

**State Management:**
- Zustand 5.0.2 - Lightweight state management
- TanStack React Query 5.62.0 - Server state management
  - Includes devtools (5.62.0)

**Testing:**
- Backend:
  - pytest 8.3.3 - Test framework
    - pytest-asyncio 0.24.0 - Async test support
    - pytest-cov 6.0.0 - Coverage reporting
    - pytest-benchmark 4.0.0 - Performance testing
  - Config: `conftest.py`
- Frontend:
  - Vitest 3.2.4 - Unit test framework
    - Config: `frontend/vite.config.ts` (integrated)
    - Coverage: @vitest/coverage-v8 3.2.4
  - Playwright 1.50.0 - E2E testing
    - Config: `frontend/playwright.config.ts`
  - Jest 29.7.0 - Firestore rules testing
    - Config: `frontend/jest.config.cjs`
    - @firebase/rules-unit-testing 5.0.0
- Testing Library:
  - @testing-library/react 16.3.1
  - @testing-library/dom 10.4.1
  - @testing-library/jest-dom 6.9.1

**Build/Dev:**
- Vite 6.0.5 - Frontend bundler
  - @vitejs/plugin-react 4.3.4
- TypeScript 5.6.2 - Type checking
  - Configs: `frontend/tsconfig.json`, `tsconfig.app.json`, `tsconfig.node.json`
- ESLint 9.17.0 - Linting
  - Config: `frontend/eslint.config.js`
  - typescript-eslint 8.18.2
  - eslint-plugin-react-hooks 5.1.0
  - eslint-plugin-react-refresh 0.4.16

## Key Dependencies

**Critical:**
- firebase-admin 6.5.0 - Backend Firebase SDK
  - Location: `api/config.py`
  - Service account key: `serviceAccountKey-auth.json`
- firebase 12.8.0 - Frontend Firebase SDK
  - Location: `frontend/src/api/firebaseClient.ts`
  - Auth, Firestore, App Check integration
- google-cloud-firestore 2.16.0 - Async Firestore client
  - Used in: `api/config.py`

**AI/ML:**
- google-generativeai 0.8.3 - Gemini API client (legacy compatibility)
  - Location: `services/genai_client.py`
- vertexai 1.64.0 - Google Vertex AI SDK
  - Primary AI client: `services/vertex_ai_client.py`
  - Models: Gemini 2.5 Flash Lite (text), text-embedding-004 (embeddings)
- deepgram-sdk 3.5.0 - Speech-to-text service
  - Location: `services/stt.py`
- google-auth 2.35.0 - Google Cloud authentication

**Database:**
- neo4j 5.25.0 - Graph database driver
  - Config: `api/neo4j_config.py`
  - Connection pooling, Cypher query execution
- redis 5.2.0 - Cache client
  - Config: `api/cache.py`
  - TTL-based caching for summaries and embeddings

**Task Queue:**
- celery 5.4.0 - Distributed task processing
  - Config: `api/tasks/__init__.py`
  - Queue: kg_processing
  - Worker command: `celery -A api.tasks worker -l info -Q kg_processing`

**Document Processing:**
- PyMuPDF >=1.27.0 - PDF parsing
- fpdf2 2.7.9 - PDF generation
  - Location: `services/pdf_generator.py`
- python-docx >=0.8.11 - Word document parsing
- jszip 3.10.1 - Frontend ZIP handling

**Utilities:**
- python-multipart 0.0.9 - File upload handling
- python-dotenv 1.0.0 - Environment variable loading
- slowapi - Rate limiting for FastAPI
  - Location: `api/main.py`
- requests 2.32.3 - HTTP client
- numpy >=2.4.0 - Numerical operations
- tiktoken >=0.12.0 - Token counting
- json-repair 0.35.0 - JSON parsing/fixing
- tenacity >=8.0.0 - Retry logic
- PyJWT 2.8.0 - JWT token handling (testing)

## Configuration

**Environment:**
Backend (`.env`):
- `FIREBASE_CREDENTIALS` - Path to service account key
- `USE_REAL_FIREBASE` - Toggle real vs. mock Firebase
- `ENVIRONMENT` - deployment environment (development/staging/production)
- `ALLOWED_ORIGINS` - CORS configuration
- `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` - Graph database connection
- `REDIS_HOST`, `REDIS_PORT`, `REDIS_DB` - Cache connection
- `VERTEX_PROJECT`, `VERTEX_LOCATION` - Google Cloud config
- `GOOGLE_APPLICATION_CREDENTIALS` - GCP service account
- `DEEPGRAM_API_KEY` - Speech-to-text API key
- `AURA_TEST_MODE` - Enable test mode (skips external API calls)

Frontend (`frontend/.env`):
- `VITE_FIREBASE_API_KEY` - Firebase Web API key
- `VITE_FIREBASE_AUTH_DOMAIN` - Auth domain
- `VITE_FIREBASE_PROJECT_ID` - Firebase project ID
- `VITE_FIREBASE_STORAGE_BUCKET` - Storage bucket
- `VITE_FIREBASE_MESSAGING_SENDER_ID` - FCM sender ID
- `VITE_FIREBASE_APP_ID` - Firebase app ID
- `VITE_RECAPTCHA_ENTERPRISE_SITE_KEY` - App Check key
- `VITE_USE_MOCK_AUTH` - Toggle mock authentication for testing

**Build:**
- `frontend/vite.config.ts` - Vite build configuration
  - Path aliases: `@/*` → `./src/*`
  - Proxy: `/api` → `http://127.0.0.1:8001`
  - Test configuration with vitest
- `frontend/tsconfig.json` - TypeScript project references
- `frontend/tsconfig.app.json` - App TypeScript config
  - Target: ES2020, JSX: react-jsx
  - Strict mode enabled
- `jest.config.js` - Root-level Firestore rules testing
- `frontend/jest.config.cjs` - Frontend Jest config
- `frontend/playwright.config.ts` - E2E test configuration
  - Test directory: `frontend/e2e/`
  - Sequential execution (fullyParallel: false)
  - Base URL: `http://127.0.0.1:5173`

**Firebase:**
- `firebase.json` - Firebase emulator configuration
  - Firestore emulator port: 8080
  - Auth emulator port: 9099
  - UI port: 4000
- `firestore.rules` - Firestore security rules
  - Role-based access control (admin/staff/student)
  - Custom claims for authorization
- `firestore.indexes.json` - Composite indexes
  - Collections: departments, semesters, subjects, modules, notes, users

## Platform Requirements

**Development:**
- Python 3.10+ with pip
- Node.js 20+ with npm
- Firebase CLI (for emulators)
  - Install: `npm install -g firebase-tools`
- Neo4j database (local or cloud)
  - Connection via bolt:// or neo4j+s:// protocol
- Redis server (optional, graceful fallback)
  - Default: localhost:6379

**Production:**
- Deployment target: Containerized (Docker)
  - Backend Dockerfile: `api/Dockerfile`
    - Base: python:3.10-slim
    - Port: 8001
  - Frontend Dockerfile: `frontend/Dockerfile`
    - Base: node:20-slim
    - Port: 3001
- Firebase project with:
  - Firestore database
  - Authentication enabled
  - App Check with reCAPTCHA Enterprise
- Google Cloud Platform project:
  - Vertex AI API enabled
  - Service account with credentials
- Neo4j database (AuraDB or self-hosted)
- Redis cache (optional but recommended)
- Deepgram API account for transcription

**Run Commands:**
```bash
# Backend development
cd api
python -m uvicorn main:app --reload --port 8001

# Frontend development
cd frontend
npm run dev

# Celery worker
celery -A api.tasks worker -l info -Q kg_processing

# Firebase emulators
firebase emulators:start --only firestore,auth

# Testing
pytest                        # Backend tests
npm run test                  # Frontend unit tests
npm run test:e2e             # Frontend E2E tests
firebase emulators:exec --only firestore "npx jest tests/firestore/"  # Rules tests
```

---

*Stack analysis: 2025-01-20*
