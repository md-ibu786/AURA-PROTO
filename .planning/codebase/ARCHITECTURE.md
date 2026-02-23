# System Architecture

**Analysis Date:** 2025-01-21

## High-Level Overview

**Overall Pattern:** Full-stack monorepo with REST API architecture

**Key Characteristics:**
- Python FastAPI backend with Firebase Firestore persistence
- React TypeScript frontend with Vite build tooling
- Neo4j knowledge graph database for entity relationships
- Redis for caching and session management
- Celery for asynchronous task processing
- Firebase Authentication with role-based access control (RBAC)

**Service Boundaries:**
- Frontend (React SPA) ↔ Backend (FastAPI REST API) via HTTP/JSON
- Backend ↔ Firestore (document database) for hierarchy and user data
- Backend ↔ Neo4j (graph database) for knowledge graph entities
- Backend ↔ Redis (cache) for summaries and session data
- Backend ↔ Celery (task queue) for batch processing

## Frontend Architecture

**Pattern:** Component-based architecture with centralized state management

### Layers

**UI Layer:**
- Purpose: Presentational components and user interaction
- Location: `frontend/src/components/`, `frontend/src/pages/`
- Contains: Reusable UI components (buttons, dialogs, forms)
- Depends on: Stores, API clients, types
- Used by: Pages, features

**Feature Layer:**
- Purpose: Feature-specific business logic and composite components
- Location: `frontend/src/features/kg/`
- Contains: Knowledge Graph feature components
- Depends on: UI components, API clients, stores
- Used by: Pages

**State Management Layer:**
- Purpose: Client-side state (UI state, auth state)
- Location: `frontend/src/stores/`
- Contains: Zustand stores (`useExplorerStore`, `useAuthStore`)
- Depends on: Types, API clients
- Used by: All components

**API Client Layer:**
- Purpose: HTTP communication with backend
- Location: `frontend/src/api/`
- Contains: Typed fetch wrappers, API functions
- Depends on: Auth store for token injection
- Used by: React Query hooks, stores

### Data Flow

**User Authentication Flow:**

1. User submits credentials via `LoginPage`
2. `useAuthStore.login()` calls Firebase Auth SDK
3. Firebase returns ID token + user UID
4. Store fetches Firestore user document via `/api/users/me`
5. User object with role stored in Zustand
6. Protected routes check `useAuthStore.isAuthenticated()`
7. All API requests inject token via `getAuthHeader()`

**Hierarchy Navigation Flow:**

1. User selects department in `SidebarTree`
2. `useExplorerStore.navigateTo()` updates `currentPath`
3. React Query fetches children via `explorerApi.getChildren()`
4. API client calls `/api/hierarchy/{id}/children`
5. Backend queries Firestore subcollections
6. Response updates `GridView` or `ListView`
7. Selection state tracked in `selectedIds` Set

**File Upload Flow:**

1. User drags audio file to `UploadDialog`
2. FormData created with file + metadata (moduleId, topic)
3. `audioApi.uploadAndProcess()` POST to `/api/audio/process-pipeline`
4. Backend validates file, generates jobId, starts background task
5. Frontend polls `/api/audio/pipeline-status/{jobId}` every 2s
6. Progress shown in dialog (transcribing → refining → summarizing → PDF)
7. On completion, note created in Firestore, dialog shows success
8. React Query invalidates cache, UI refreshes with new note

### State Management

**Client State (Zustand):**
- UI ephemeral state (selection, dialogs, context menus)
- Auth state (user, role, permissions)
- Navigation state (breadcrumbs, active node)
- View preferences (grid/list mode, search query)

**Server State (React Query):**
- Hierarchy tree data (departments, semesters, subjects, modules, notes)
- User lists (admin dashboard)
- Pipeline status (async job polling)
- Automatic caching with `staleTime: 0` for immediate invalidation
- Single retry on network failures

**Persistence:**
- Auth state: Firebase Auth SDK manages tokens
- View preferences: Local component state (not persisted)
- All data: Backend Firestore (source of truth)

## Backend Architecture

**Pattern:** Layered REST API with domain-driven design

### Layers

**API Router Layer:**
- Purpose: HTTP endpoint definitions and request validation
- Location: `api/routers/`, `api/*.py` (router files)
- Contains: FastAPI route handlers with Pydantic models
- Depends on: Service layer, auth dependencies
- Used by: FastAPI app via `app.include_router()`

**Service Layer:**
- Purpose: Business logic and orchestration
- Location: `api/modules/service.py`, `services/`
- Contains: Module management, document processing, AI services
- Depends on: Data access layer, external services
- Used by: Router layer

**Data Access Layer:**
- Purpose: Database queries and persistence
- Location: `api/hierarchy.py`, `api/config.py`, `api/graph_manager.py`
- Contains: Firestore operations, Neo4j queries, Redis caching
- Depends on: Database clients
- Used by: Service layer, router layer

**External Services Layer:**
- Purpose: Third-party API integrations
- Location: `services/`
- Contains: AI clients (Gemini, Vertex AI), STT (Deepgram), PDF generation
- Depends on: Configuration, API keys
- Used by: Service layer

### Key Abstractions

**Hierarchy Tree:**
- Purpose: Represents educational content structure
- Pattern: Nested Firestore subcollections
- Structure: `departments/{id}/semesters/{id}/subjects/{id}/modules/{id}/notes/{id}`
- Files: `api/hierarchy.py` (read), `api/hierarchy_crud.py` (write)
- Operations: Drill-down queries, cascade deletes, path validation

**Knowledge Graph:**
- Purpose: Entity relationship graph for semantic search
- Pattern: Neo4j property graph
- Nodes: Entity (name, type, definition, module_id)
- Edges: DEFINES, DEPENDS_ON, USES, SUPPORTS, CONTRADICTS, REFERENCES
- Files: `api/graph_manager.py`, `api/kg/router.py`
- Operations: Multi-hop traversal, subgraph extraction, batch processing

**Audio Pipeline:**
- Purpose: Audio-to-notes processing workflow
- Pattern: Background task with status polling
- Steps: Upload → Transcribe (Deepgram) → Refine (AI) → Summarize (AI) → PDF → Database
- Files: `api/audio_processing.py`, `services/stt.py`, `services/summarizer.py`
- State: In-memory job store (production: Celery + Redis)

**User & RBAC:**
- Purpose: Role-based access control
- Pattern: Firebase Auth token verification + Firestore user docs
- Roles: admin (full access), staff (department-scoped), student (read-only)
- Files: `api/auth.py`, `api/users.py`
- Operations: Token verification, role enforcement via dependencies

### Entry Points

**Main Application:**
- Location: `api/main.py`
- Triggers: `uvicorn main:app --reload --port 8000`
- Responsibilities: 
  - Load environment variables
  - Initialize Firebase Admin SDK
  - Configure CORS middleware
  - Mount all routers
  - Set up rate limiting
  - Serve static PDF files

**Celery Worker:**
- Location: `api/tasks/document_processing_tasks.py`
- Triggers: `celery -A api.tasks worker`
- Responsibilities:
  - Batch KG processing
  - Long-running document analysis
  - Task result caching in Redis

**Health Checks:**
- `GET /health`: Liveness probe (app running)
- `GET /ready`: Readiness probe (Firestore connected)
- `GET /health/redis`: Cache availability check

### Error Handling

**Strategy:** HTTP status codes + JSON error details

**Patterns:**
- 401 Unauthorized: Invalid/missing Firebase token
- 403 Forbidden: Insufficient role permissions
- 404 Not Found: Resource doesn't exist
- 409 Conflict: Duplicate name (code: DUPLICATE_NAME)
- 422 Validation Error: Pydantic validation failed
- 500 Internal Server Error: Unexpected exceptions
- 503 Service Unavailable: Firestore/Neo4j connection lost

**Implementation:**
- `HTTPException` raised in routers
- `DuplicateError` custom exception for name conflicts
- Middleware catches all unhandled exceptions
- Frontend `client.ts` parses `detail` field from response

## Data Flow

### Create Note Flow (Audio Upload)

1. **Frontend** → Upload audio file via `UploadDialog`
2. **API Router** (`audio_processing.py:process_pipeline`) → Validate file size/format
3. **Background Task** (`_run_pipeline()`) → Save file to temp, start processing
4. **STT Service** (`services/stt.py`) → Transcribe with Deepgram API
5. **Refinement Service** (`services/coc.py`) → Clean transcript with Gemini
6. **Summarization Service** (`services/summarizer.py`) → Generate notes with Vertex AI
7. **PDF Service** (`services/pdf_generator.py`) → Create PDF with PyMuPDF
8. **Notes Module** (`api/notes.py`) → Create Firestore note document
9. **Response** → Return noteId + pdfUrl to frontend
10. **Frontend** → Poll `/api/audio/pipeline-status/{jobId}` until complete
11. **React Query** → Invalidate cache, refetch hierarchy tree

### Knowledge Graph Processing Flow

1. **Frontend** → User clicks "Process Documents" in KG dialog
2. **API Router** (`api/kg/router.py:process_batch`) → Validate document IDs
3. **Celery Task** (`document_processing_tasks.py`) → Queue batch job
4. **Task Worker** → For each document:
   - Fetch PDF from Firestore storage
   - Extract text with PyMuPDF
   - Chunk text with `entity_aware_chunker.py`
   - Extract entities with `llm_entity_extractor.py` (Gemini)
   - Deduplicate entities with `entity_deduplicator.py`
   - Create nodes + relationships in Neo4j via `graph_manager.py`
5. **Firestore Update** → Set `kg_status: 'ready'` on note document
6. **Response** → Return job status to frontend
7. **Frontend** → Show progress, update KG status badges

### RBAC Authorization Flow

1. **Frontend** → User makes authenticated request
2. **Auth Store** → Injects `Authorization: Bearer {token}` header
3. **Backend** (`auth.py:verify_firebase_token`) → Verify token with Firebase Admin SDK
4. **Firestore Query** → Fetch user document from `users/{uid}`
5. **Permission Check** → Validate role + department access
   - `require_admin()`: role == 'admin'
   - `require_staff()`: role in ['admin', 'staff']
   - `can_modify_note()`: user.departmentId matches note's department
6. **Router** → Process request if authorized, else raise 403
7. **Response** → Return data or error to frontend

## Cross-Cutting Concerns

### Logging

**Approach:** Structured logging with Python `logging` module

**Patterns:**
- Logger per module: `logger = logging.getLogger(__name__)`
- Configuration: `api/logging_config.py` sets format and levels
- Levels: DEBUG (dev), INFO (production), ERROR (exceptions)
- Output: Console (development), file rotation (production)

### Validation

**Approach:** Pydantic models for all API inputs/outputs

**Patterns:**
- Request validation: FastAPI auto-validates against Pydantic models
- Response validation: Return Pydantic models from routes
- Custom validators: `@validator` decorators for business rules
- Type safety: TypeScript types mirror Pydantic models

### Authentication

**Approach:** Firebase Auth + custom RBAC

**Patterns:**
- Token verification: Firebase Admin SDK verifies JWT signatures
- User lookup: Firestore stores role + permissions
- Dependency injection: `Depends(get_current_user)` for protected routes
- Token refresh: Frontend retries with refreshed token on 401

### Caching

**Approach:** Redis for frequently accessed data

**Patterns:**
- Summary caching: 24-hour TTL on generated summaries
- Embedding caching: Persist vector embeddings to avoid re-computation
- Session caching: Pipeline job status stored in Redis
- Graceful degradation: `RedisClient` falls back to no-op if unavailable

### Rate Limiting

**Approach:** SlowAPI middleware

**Patterns:**
- Auth endpoints: 5 requests/minute (prevent brute force)
- General API: 100 requests/minute
- IP-based limiting: Uses client IP address
- Response: 429 Too Many Requests with Retry-After header

## API Layer

### REST API Design

**Base URL:** `http://localhost:8000`
**Prefix:** `/api` for all endpoints (legacy endpoints at root)

**Endpoint Patterns:**

**Hierarchy CRUD:**
- `GET /api/hierarchy/{id}/children` - Get child nodes
- `POST /api/{type}s` - Create new entity (departments, semesters, subjects, modules)
- `PUT /api/{type}s/{id}` - Update entity
- `DELETE /api/{type}s/{id}` - Delete entity (cascade)
- `DELETE /api/notes/{id}/cascade` - Delete note + KG data

**Audio Processing:**
- `POST /api/audio/process-pipeline` - Upload + process audio file
- `GET /api/audio/pipeline-status/{jobId}` - Poll job status
- `POST /api/audio/upload-document` - Upload PDF/DOC directly

**Knowledge Graph:**
- `POST /api/v1/kg/process-batch` - Batch process documents for KG
- `GET /api/v1/kg/documents/{id}/status` - Get KG processing status
- `GET /api/v1/kg/processing-queue` - List queued documents

**User Management:**
- `GET /api/users` - List all users (admin only)
- `POST /api/users` - Create new user (admin only)
- `GET /api/users/me` - Get current user profile
- `PUT /api/users/{id}` - Update user (admin only)

**M2KG Modules:**
- `POST /api/v1/modules` - Create module (staff only)
- `GET /api/v1/modules` - List modules with filters
- `PUT /api/v1/modules/{id}` - Update module
- `POST /api/v1/modules/{id}/publish` - Publish module to students

**Response Format:**

Success (200):
```json
{
  "id": "abc123",
  "type": "subject",
  "label": "CS101 - Data Structures",
  "meta": { "code": "CS101" }
}
```

Error (4xx/5xx):
```json
{
  "detail": "Invalid hierarchy for note"
}
```

Duplicate Error (409):
```json
{
  "detail": {
    "code": "DUPLICATE_NAME",
    "message": "A subject named 'Calculus' already exists"
  }
}
```

### Authentication Flow

**Token Format:** Firebase JWT in Authorization header

**Request:**
```
GET /api/users/me
Authorization: Bearer eyJhbGciOiJSUzI1NiIs...
```

**Token Claims:**
```json
{
  "uid": "user123",
  "email": "staff@test.com",
  "exp": 1737500000
}
```

**Backend Processing:**
1. `HTTPBearer` extracts token
2. `verify_firebase_token()` validates signature
3. `get_current_user()` fetches Firestore user doc
4. Returns `FirestoreUser` object to route handler

### Pagination

**Not Currently Implemented:** All queries return full result sets

**Future Pattern (planned):**
- Query params: `?page=1&limit=50`
- Response: `{ items: [...], total: 150, page: 1, pages: 3 }`

## Key Design Patterns

### Repository Pattern (Data Access)

**Location:** `api/hierarchy.py`, `api/graph_manager.py`

**Purpose:** Abstract database operations from business logic

**Implementation:**
- `get_all_departments()` → Firestore query wrapper
- `GraphManager.get_entity()` → Neo4j query wrapper
- Swap database without changing routers

### Dependency Injection (Auth)

**Location:** `api/auth.py`

**Purpose:** Centralize auth logic in reusable dependencies

**Implementation:**
```python
@router.delete("/api/modules/{id}")
def delete_module(
    id: str,
    user: FirestoreUser = Depends(require_staff)
):
    # user already verified + role-checked
    ...
```

### Background Task Pattern (Async Processing)

**Location:** `api/audio_processing.py`

**Purpose:** Non-blocking long-running operations

**Implementation:**
- Generate unique jobId
- Start background task with `BackgroundTasks`
- Store status in `job_status_store` dict
- Frontend polls `/pipeline-status/{jobId}`
- Production: Use Celery + Redis for distributed workers

### Middleware Chain (Security)

**Location:** `api/main.py`

**Purpose:** Apply cross-cutting concerns to all requests

**Order:**
1. `SlowAPIMiddleware` → Rate limiting
2. `CORSMiddleware` → CORS headers
3. `SecurityHeadersMiddleware` → Security headers (X-Frame-Options, CSP)

**Processing:** Last added = First executed (reverse order)

### Factory Pattern (Service Initialization)

**Location:** `api/modules/router.py`, `api/config.py`

**Purpose:** Lazy initialization of expensive services

**Implementation:**
```python
def get_module_service() -> ModuleService:
    """Dependency for getting ModuleService instance."""
    return ModuleService()
```

### Observer Pattern (State Sync)

**Location:** `frontend/src/stores/useAuthStore.ts`

**Purpose:** React to Firebase auth state changes

**Implementation:**
```typescript
export function initAuthListener() {
    return onIdTokenChanged(auth, async (user) => {
        if (user) {
            await refreshUser();
        } else {
            setUser(null);
        }
    });
}
```

### Optimistic UI Updates

**Location:** Frontend React Query mutations

**Purpose:** Instant feedback before server confirmation

**Implementation:**
- Mutation triggers
- UI updates immediately (optimistic)
- On success: Invalidate cache, refetch
- On error: Rollback + show toast notification

---

*Architecture analysis: 2025-01-21*
