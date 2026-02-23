# Project Structure

**Analysis Date:** 2025-01-21

## Root Directory Layout

```
AURA-NOTES-MANAGER/
├── api/                    # FastAPI backend application
├── frontend/               # React TypeScript SPA
├── services/               # Shared AI/processing services
├── tests/                  # Backend Python tests
├── e2e/                    # End-to-end Playwright tests
├── .planning/              # GSD project planning documents
├── conductor/              # Project management and guidelines
├── pdfs/                   # Generated PDF storage
├── documentations/         # Legacy documentation files
├── requirements.txt        # Python dependencies
├── package.json            # Root-level Firebase scripts
├── firebase.json           # Firebase emulator configuration
├── firestore.rules         # Firestore security rules
├── conftest.py             # Pytest global configuration
├── .env                    # Environment variables (not committed)
└── serviceAccountKey-auth.json  # Firebase credentials (not committed)
```

## Directory Purposes

### `api/` - Backend Application

**Purpose:** FastAPI REST API server for hierarchy management, authentication, and AI processing

**Structure:**
```
api/
├── main.py                 # Application entry point, router mounting
├── config.py               # Firebase, Neo4j, Redis initialization
├── auth.py                 # Firebase token verification, RBAC dependencies
├── models.py               # Pydantic models for users
├── hierarchy.py            # Read-only hierarchy data access
├── hierarchy_crud.py       # Hierarchy CRUD operations
├── notes.py                # Note creation and management
├── audio_processing.py     # Audio upload and pipeline endpoints
├── explorer.py             # File explorer tree endpoints
├── auth_sync.py            # Firebase Auth sync utilities
├── users.py                # User management endpoints
├── graph_manager.py        # Neo4j graph traversal and queries
├── kg_processor.py         # Knowledge graph entity extraction
├── neo4j_config.py         # Neo4j driver initialization
├── cache.py                # Redis client wrapper
├── limiter.py              # Rate limiting configuration
├── logging_config.py       # Structured logging setup
├── routers/                # Feature-specific API routers
│   ├── summaries.py        # Summary generation endpoints
│   ├── trends.py           # Trend analysis endpoints
│   ├── templates.py        # Template management endpoints
│   ├── schema.py           # Schema validation endpoints
│   └── graph_preview.py    # Graph preview API
├── modules/                # M2KG module management
│   ├── router.py           # Module CRUD endpoints
│   ├── service.py          # Module business logic
│   ├── publishing.py       # Module publishing workflow
│   └── models.py           # Module Pydantic schemas
├── kg/                     # Knowledge Graph processing
│   └── router.py           # KG batch processing endpoints
├── schemas/                # Pydantic schemas for entities
│   ├── analysis.py         # Analysis result schemas
│   ├── feedback.py         # User feedback schemas
│   ├── graph.py            # Graph data structures
│   └── search.py           # Search request/response schemas
├── tasks/                  # Celery background tasks
│   └── document_processing_tasks.py  # Batch KG processing
├── migrations/             # Database schema migrations (if any)
└── hierarchy/              # Hierarchy utilities (package)
```

**Key Files:**
- `main.py`: FastAPI app initialization, CORS, middleware, router inclusion
- `config.py`: Environment variable loading, Firebase/Neo4j/Redis clients
- `auth.py`: `get_current_user()`, `require_admin()`, `require_staff()` dependencies
- `hierarchy_crud.py`: Create/update/delete operations with cascade logic
- `audio_processing.py`: Audio pipeline orchestration, job status tracking
- `graph_manager.py`: `GraphManager` class for Neo4j operations

### `frontend/` - React Frontend

**Purpose:** Single-page application for hierarchy navigation and note management

**Structure:**
```
frontend/
├── src/
│   ├── main.tsx            # React app entry point, QueryClient setup
│   ├── App.tsx             # Root component, routing configuration
│   ├── vite-env.d.ts       # Vite type declarations
│   ├── pages/              # Top-level page components
│   │   ├── ExplorerPage.tsx      # Main file explorer view
│   │   ├── LoginPage.tsx         # Authentication page
│   │   └── AdminDashboard.tsx    # User management dashboard
│   ├── components/         # Reusable UI components
│   │   ├── explorer/       # File explorer specific components
│   │   │   ├── SidebarTree.tsx         # Left sidebar hierarchy tree
│   │   │   ├── GridView.tsx            # Grid layout for folders/notes
│   │   │   ├── ListView.tsx            # List layout for folders/notes
│   │   │   ├── ContextMenu.tsx         # Right-click context menu
│   │   │   ├── UploadDialog.tsx        # Audio/document upload modal
│   │   │   ├── SelectionActionBar.tsx  # Bulk action toolbar
│   │   │   └── SelectionOverlay.tsx    # Multi-select overlay
│   │   ├── layout/         # Layout components
│   │   ├── ui/             # Shadcn UI primitives
│   │   ├── LoadingSpinner.tsx    # Loading indicator
│   │   └── ProtectedRoute.tsx    # Auth guard wrapper
│   ├── features/           # Feature-specific modules
│   │   └── kg/             # Knowledge Graph feature
│   │       ├── components/ # KG-specific UI components
│   │       ├── hooks/      # KG-specific React hooks
│   │       └── types/      # KG-specific TypeScript types
│   ├── stores/             # Zustand state stores
│   │   ├── index.ts        # Store exports
│   │   ├── useExplorerStore.ts   # Explorer UI state
│   │   └── useAuthStore.ts       # Authentication state
│   ├── api/                # Backend API clients
│   │   ├── client.ts       # Core fetch wrapper with auth
│   │   ├── explorerApi.ts  # Hierarchy API functions
│   │   ├── audioApi.ts     # Audio processing API functions
│   │   ├── userApi.ts      # User management API functions
│   │   ├── firebaseClient.ts  # Firebase SDK initialization
│   │   └── index.ts        # API exports
│   ├── hooks/              # Custom React hooks
│   ├── lib/                # Utility libraries
│   │   └── cn.ts           # Tailwind class name merger
│   ├── types/              # TypeScript type definitions
│   │   ├── FileSystemNode.ts   # Core hierarchy types
│   │   ├── user.ts             # User and role types
│   │   └── index.ts            # Type exports
│   ├── styles/             # Global CSS files
│   │   ├── index.css       # Tailwind directives, global styles
│   │   └── explorer.css    # Explorer-specific styles
│   ├── test/               # Frontend test utilities
│   └── tests/              # Frontend unit tests
├── index.html              # HTML entry point
├── vite.config.ts          # Vite bundler configuration
├── tsconfig.json           # TypeScript compiler options
├── tsconfig.app.json       # App-specific TypeScript config
├── tsconfig.node.json      # Node-specific TypeScript config
├── eslint.config.js        # ESLint rules
├── playwright.config.ts    # Playwright E2E test config
├── package.json            # Node dependencies and scripts
└── .env                    # Frontend environment variables
```

**Key Files:**
- `src/main.tsx`: React.render(), QueryClientProvider setup
- `src/App.tsx`: BrowserRouter, route definitions, ProtectedRoute guards
- `src/stores/useExplorerStore.ts`: Selection, navigation, dialogs, clipboard state
- `src/stores/useAuthStore.ts`: User, role, login/logout, permission checks
- `src/api/client.ts`: `fetchApi()`, `fetchBlob()`, auth header injection
- `src/components/explorer/SidebarTree.tsx`: Recursive tree rendering
- `src/pages/ExplorerPage.tsx`: Main explorer layout with sidebar + content area

### `services/` - Shared AI Services

**Purpose:** AI service integrations used by backend API

**Structure:**
```
services/
├── genai_client.py         # Google Generative AI client wrapper
├── vertex_ai_client.py     # Vertex AI client for embeddings
├── stt.py                  # Deepgram speech-to-text service
├── summarizer.py           # AI-powered note summarization
├── summary_service.py      # Summary caching and retrieval
├── coc.py                  # Transcript refinement service
├── pdf_generator.py        # PDF generation from markdown
├── llm_entity_extractor.py # Entity extraction from text
├── entity_aware_chunker.py # Smart text chunking for KG
├── entity_deduplicator.py  # Entity deduplication logic
├── trend_analyzer.py       # Trend detection in notes
├── embeddings.py           # Vector embedding generation
├── chunking_utils.py       # Text chunking utilities
├── extraction_templates.py # Prompt templates for extraction
├── document_parsers/       # Document parsing modules
│   └── docx_parser.py      # Microsoft Word document parser
└── multimodal/             # Multimodal processing (images, audio)
    ├── processor.py        # Main multimodal processor
    ├── audio.py            # Audio processing
    ├── image.py            # Image processing
    ├── ocr.py              # Optical character recognition
    └── config.py           # Multimodal configuration
```

**Key Files:**
- `stt.py`: Deepgram API integration for audio transcription
- `summarizer.py`: Gemini-based note generation from transcripts
- `pdf_generator.py`: PyMuPDF PDF creation with formatting
- `llm_entity_extractor.py`: Extract entities from documents for KG

### `tests/` - Backend Tests

**Purpose:** Pytest test suite for backend API and services

**Structure:**
```
tests/
├── test_audio_validation.py        # Audio upload validation tests
├── test_auth_integration.py        # Authentication flow tests
├── test_auth_sync.py               # Firebase Auth sync tests
├── test_batch_delete_performance.py  # Performance benchmarks
├── test_department_duplicates.py   # Duplicate name handling tests
├── test_graph_manager_delete.py    # Graph deletion tests
├── test_graph_preview.py           # Graph preview API tests
├── test_hierarchy_duplicate_handling.py  # Hierarchy name conflicts
├── test_kg_router_delete.py        # KG deletion endpoint tests
├── test_summarizer.py              # Summarization unit tests
├── test_summarizer_functional.py   # Summarization integration tests
├── test_summarizer_integration.py  # End-to-end summarization tests
├── firestore/                      # Firestore rules tests
├── integration/                    # Integration test suites
├── security/                       # Security and auth tests
├── performance/                    # Performance benchmarks
├── benchmark/                      # Benchmark utilities
└── comparison/                     # A/B comparison tests
```

**Key Files:**
- `test_auth_integration.py`: Role-based access control verification
- `test_hierarchy_duplicate_handling.py`: Unique name validation
- `test_graph_manager_delete.py`: Cascade delete verification

### `e2e/` - End-to-End Tests

**Purpose:** Playwright browser automation tests

**Structure:**
```
e2e/
├── tests/                  # Test spec files
├── page-objects/           # Page Object Model classes
├── data/                   # Test fixtures and seed data
├── playwright.config.ts    # Playwright configuration
├── package.json            # E2E test dependencies
└── README.md               # E2E testing guide
```

**Key Files:**
- `tests/*.spec.ts`: Browser test scenarios
- `playwright.config.ts`: Browser targets, timeouts, retries

### `.planning/` - GSD Planning Documents

**Purpose:** Project planning and phase execution tracking

**Structure:**
```
.planning/
├── codebase/               # Codebase analysis documents (this file!)
│   ├── ARCHITECTURE.md     # System architecture
│   └── STRUCTURE.md        # File structure (this document)
├── phases/                 # Implementation phase plans
│   ├── 01-backend-auth-foundation/
│   ├── 02-backend-user-management/
│   ├── 03-frontend-auth-state/
│   ├── 04-frontend-auth-ui/
│   └── 05-seed-data-integration/
├── firebase-rbac-migration/  # Firebase RBAC migration project
│   └── phases/
└── mobile-responsive/      # Mobile responsiveness project
    └── phases/
```

**Key Files:**
- `ROADMAP.md`: High-level project roadmap
- `BRIEF.md`: Project brief and success criteria
- `ISSUES.md`: Known issues and blockers

### `conductor/` - Project Guidelines

**Purpose:** Development guidelines and project documentation

**Structure:**
```
conductor/
├── product.md              # Product overview
├── product-guidelines.md   # Development guidelines
├── tech-stack.md           # Technology stack documentation
├── workflow.md             # Development workflow
├── tracks.md               # Feature tracks
└── setup_state.json        # Setup state tracking
```

## Frontend Structure (`frontend/`)

### Pages Layer

**Location:** `frontend/src/pages/`

**Contains:** Top-level route components

**Naming:** `{Feature}Page.tsx` (e.g., `ExplorerPage.tsx`, `LoginPage.tsx`)

**Responsibilities:**
- Layout composition (header + sidebar + content)
- Route-level data fetching
- Page-specific state initialization

**Example:**
```typescript
// ExplorerPage.tsx
export default function ExplorerPage() {
    return (
        <div className="explorer-layout">
            <Sidebar />
            <MainContent />
        </div>
    );
}
```

### Components Layer

**Location:** `frontend/src/components/`

**Organization:**
- `components/explorer/` - File explorer UI
- `components/layout/` - Layout primitives
- `components/ui/` - Shadcn UI components

**Naming:** `{Component}.tsx` (PascalCase)

**Responsibilities:**
- Presentational logic
- Event handling
- Composition of smaller components

**Example:**
```typescript
// GridView.tsx
export function GridView({ nodes }: { nodes: FileSystemNode[] }) {
    return (
        <div className="grid grid-cols-4 gap-4">
            {nodes.map(node => <FolderCard key={node.id} node={node} />)}
        </div>
    );
}
```

### Stores Layer

**Location:** `frontend/src/stores/`

**Organization:**
- `useExplorerStore.ts` - Explorer UI state
- `useAuthStore.ts` - Authentication state
- `index.ts` - Re-exports all stores

**Naming:** `use{Feature}Store.ts`

**Responsibilities:**
- Client-side state management
- State mutation actions
- Computed values (selectors)

**Example:**
```typescript
// useExplorerStore.ts
export const useExplorerStore = create<ExplorerState>((set) => ({
    selectedIds: new Set(),
    select: (id) => set((state) => {
        state.selectedIds.add(id);
        return { selectedIds: new Set(state.selectedIds) };
    }),
}));
```

### API Layer

**Location:** `frontend/src/api/`

**Organization:**
- `client.ts` - Core fetch utilities
- `explorerApi.ts` - Hierarchy API calls
- `audioApi.ts` - Audio processing API calls
- `userApi.ts` - User management API calls
- `firebaseClient.ts` - Firebase SDK setup

**Naming:** `{feature}Api.ts`

**Responsibilities:**
- HTTP request/response handling
- Error parsing
- Type-safe API functions

**Example:**
```typescript
// explorerApi.ts
export async function getChildren(nodeId: string): Promise<FileSystemNode[]> {
    return fetchApi<FileSystemNode[]>(`/hierarchy/${nodeId}/children`);
}
```

### Types Layer

**Location:** `frontend/src/types/`

**Organization:**
- `FileSystemNode.ts` - Core hierarchy types
- `user.ts` - User and auth types
- `index.ts` - Re-exports all types

**Naming:** `{Domain}.ts`

**Responsibilities:**
- TypeScript interfaces and types
- Type guards
- Enums and constants

**Example:**
```typescript
// FileSystemNode.ts
export type HierarchyType = 'department' | 'semester' | 'subject' | 'module' | 'note';

export interface FileSystemNode {
    id: string;
    type: HierarchyType;
    label: string;
    parentId: string | null;
    children?: FileSystemNode[];
    meta?: FileSystemNodeMeta;
}
```

## Backend Structure (`api/`)

### Router Layer

**Location:** `api/*.py` (root level), `api/routers/`

**Organization:**
- `hierarchy_crud.py` - Hierarchy CRUD operations
- `audio_processing.py` - Audio pipeline
- `explorer.py` - Tree navigation
- `users.py` - User management
- `routers/summaries.py` - Summary endpoints
- `routers/trends.py` - Trend analysis

**Naming:** `{feature}.py` or `{feature}_router.py`

**Responsibilities:**
- FastAPI route definitions
- Request validation (Pydantic models)
- Response serialization
- Dependency injection for auth

**Example:**
```python
# hierarchy_crud.py
@router.post("/api/subjects", status_code=201)
def create_subject(
    payload: SubjectCreate,
    user: FirestoreUser = Depends(require_staff)
):
    # Business logic
    return subject
```

### Service Layer

**Location:** `api/modules/service.py`, `services/`

**Organization:**
- `api/modules/service.py` - Module business logic
- `services/summarizer.py` - Summarization service
- `services/stt.py` - Speech-to-text service

**Naming:** `{feature}_service.py` or `service.py` in feature package

**Responsibilities:**
- Business logic orchestration
- Multi-step workflows
- External service coordination
- Error handling

**Example:**
```python
# modules/service.py
class ModuleService:
    def create(self, user_id: str, data: ModuleCreate) -> ModuleResponse:
        # Validate, create, audit log
        return module
```

### Data Access Layer

**Location:** `api/hierarchy.py`, `api/config.py`, `api/graph_manager.py`

**Organization:**
- `hierarchy.py` - Firestore hierarchy queries
- `graph_manager.py` - Neo4j graph operations
- `cache.py` - Redis caching
- `config.py` - Database client initialization

**Naming:** `{database}.py` or `{domain}.py`

**Responsibilities:**
- Database queries
- Connection management
- Data transformation
- Transaction handling

**Example:**
```python
# hierarchy.py
def get_all_departments() -> List[Dict[str, Any]]:
    docs = db.collection('departments').order_by('name').stream()
    return [{'id': doc.id, 'label': doc.get('name'), **doc.to_dict()} for doc in docs]
```

## Test Organization

### Backend Tests (`tests/`)

**Organization:**
```
tests/
├── test_{feature}.py       # Unit tests for specific features
├── integration/            # Integration tests (multi-component)
├── security/               # Security and auth tests
├── performance/            # Performance benchmarks
└── firestore/              # Firestore rules tests
```

**Naming:** `test_{feature}.py` or `test_{feature}_{aspect}.py`

**Patterns:**
- Unit tests: Single function/class isolation
- Integration tests: Multiple components, real database
- E2E tests: Full request/response cycle

**Example:**
```python
# test_hierarchy_duplicate_handling.py
def test_create_duplicate_subject_returns_409():
    # Setup: Create first subject
    # Test: Try to create duplicate
    # Assert: 409 response with DUPLICATE_NAME code
```

### Frontend Tests (`frontend/src/tests/`)

**Organization:**
```
frontend/src/
├── components/
│   └── explorer/
│       └── __tests__/
│           └── SidebarTree.test.tsx
├── stores/
│   └── useExplorerStore.test.ts
└── test/
    └── setup.ts            # Test environment setup
```

**Naming:** `{Component}.test.tsx` or `{module}.test.ts`

**Patterns:**
- Component tests: React Testing Library
- Store tests: Direct Zustand store testing
- Integration tests: Multiple components together

**Example:**
```typescript
// useExplorerStore.test.ts
describe('useExplorerStore', () => {
    it('should select a node', () => {
        const { select, selectedIds } = useExplorerStore.getState();
        select('node123');
        expect(selectedIds.has('node123')).toBe(true);
    });
});
```

### E2E Tests (`e2e/`)

**Organization:**
```
e2e/
├── tests/
│   ├── auth.spec.ts        # Authentication flows
│   ├── explorer.spec.ts    # File explorer interactions
│   └── upload.spec.ts      # File upload flows
└── page-objects/
    ├── LoginPage.ts        # Login page POM
    └── ExplorerPage.ts     # Explorer page POM
```

**Naming:** `{feature}.spec.ts`

**Patterns:**
- Page Object Model for reusability
- Test data fixtures in `data/`
- Browser contexts for isolation

**Example:**
```typescript
// tests/auth.spec.ts
test('should login as staff user', async ({ page }) => {
    await page.goto('/login');
    await page.fill('[name="email"]', 'staff@test.com');
    await page.fill('[name="password"]', 'Staff123!');
    await page.click('button[type="submit"]');
    await expect(page).toHaveURL('/');
});
```

## Configuration Files

### Root Configuration

**Environment Variables:**
- `.env` - Main environment configuration (not committed)
- `.env.example` - Template for `.env` file

**Firebase:**
- `firebase.json` - Emulator configuration
- `firestore.rules` - Security rules
- `firestore.indexes.json` - Composite index definitions
- `serviceAccountKey-auth.json` - Service account credentials (not committed)

**Python:**
- `requirements.txt` - Python dependencies
- `conftest.py` - Pytest global configuration

**Node:**
- `package.json` - Root scripts for Firebase emulator

### Frontend Configuration

**Build & Dev:**
- `vite.config.ts` - Vite bundler, dev server, test runner
- `tsconfig.json` - TypeScript compiler options
- `eslint.config.js` - Linting rules

**Testing:**
- `playwright.config.ts` - E2E test configuration
- `jest.config.cjs` - Jest test configuration (Firestore rules tests)

**Package Management:**
- `package.json` - Frontend dependencies and scripts
- `package-lock.json` - Locked dependency versions

### Backend Configuration

**Python:**
- `requirements.txt` - Production dependencies
- `conftest.py` - Test environment setup

**Logging:**
- `api/logging_config.py` - Structured logging configuration

**Database:**
- `api/config.py` - Firebase, Neo4j, Redis initialization
- `api/neo4j_config.py` - Neo4j driver configuration
- `api/cache.py` - Redis client configuration

## Key Entry Points

### Backend Entry Points

**Main Application:**
- **File:** `api/main.py`
- **Command:** `uvicorn main:app --reload --port 8000`
- **Purpose:** Start FastAPI server
- **Responsibilities:**
  - Load environment variables from `.env`
  - Initialize Firebase Admin SDK
  - Configure CORS middleware
  - Mount all API routers
  - Set up rate limiting
  - Serve static PDF files

**Celery Worker:**
- **File:** `api/tasks/document_processing_tasks.py`
- **Command:** `celery -A api.tasks worker --loglevel=info`
- **Purpose:** Background task processing
- **Responsibilities:**
  - Process document batches for KG
  - Handle long-running operations
  - Store results in Redis

### Frontend Entry Points

**Development Server:**
- **File:** `frontend/src/main.tsx`
- **Command:** `npm run dev` (runs Vite)
- **Purpose:** Start React app
- **Responsibilities:**
  - Mount React app to DOM
  - Initialize QueryClient
  - Set up global providers

**Production Build:**
- **File:** `frontend/src/main.tsx`
- **Command:** `npm run build` → `dist/`
- **Purpose:** Create optimized bundle
- **Output:** Static files in `frontend/dist/`

### Test Entry Points

**Backend Tests:**
- **Command:** `pytest tests/`
- **Config:** `conftest.py`
- **Coverage:** `pytest --cov=api tests/`

**Frontend Tests:**
- **Command:** `npm test` (runs Vitest)
- **Config:** `vite.config.ts` (test section)

**E2E Tests:**
- **Command:** `npm run test:e2e` (in `e2e/`)
- **Config:** `e2e/playwright.config.ts`

## Where to Add New Code

### New API Endpoint

**Primary code:** `api/{feature}.py` or `api/routers/{feature}.py`
**Tests:** `tests/test_{feature}.py`
**Types:** `api/schemas/{feature}.py` (if complex)

**Example:** Adding a "favorites" feature
1. Create `api/favorites.py` with router
2. Add Pydantic models for request/response
3. Mount router in `api/main.py`: `app.include_router(favorites_router)`
4. Create `tests/test_favorites.py` for endpoint tests

### New Frontend Page

**Primary code:** `frontend/src/pages/{Feature}Page.tsx`
**Route:** Add to `frontend/src/App.tsx` in `<Routes>`
**Types:** Add interfaces to `frontend/src/types/`

**Example:** Adding a "settings" page
1. Create `frontend/src/pages/SettingsPage.tsx`
2. Add route in `App.tsx`: `<Route path="/settings" element={<SettingsPage />} />`
3. Add navigation link in layout component

### New UI Component

**Primary code:** `frontend/src/components/{category}/{Component}.tsx`
**Tests:** `frontend/src/components/{category}/__tests__/{Component}.test.tsx`
**Storybook:** (if added) `frontend/src/components/{category}/{Component}.stories.tsx`

**Example:** Adding a "SearchBar" component
1. Create `frontend/src/components/layout/SearchBar.tsx`
2. Export from `frontend/src/components/layout/index.ts`
3. Import and use in page components

### New AI Service

**Primary code:** `services/{service}_service.py`
**Config:** Add env vars to `.env.example`
**Tests:** `tests/test_{service}_service.py`

**Example:** Adding "translation" service
1. Create `services/translation_service.py`
2. Add `TRANSLATION_API_KEY` to `.env.example`
3. Use in `api/audio_processing.py` or router

### New Background Task

**Primary code:** `api/tasks/{task_name}_tasks.py`
**Trigger:** Call from router with `process_batch_task.delay()`
**Config:** Celery settings in `api/config.py`

**Example:** Adding "batch transcription" task
1. Create `api/tasks/transcription_tasks.py`
2. Define Celery task with `@celery_app.task`
3. Call from `api/audio_processing.py`

### New Database Model

**Firestore:**
- **Schema:** Document in `documentations/firestore-schema.md`
- **CRUD:** Add functions to `api/{entity}.py`
- **Rules:** Update `firestore.rules` with access control

**Neo4j:**
- **Queries:** Add to `api/graph_manager.py`
- **Schema:** Document in `api/NEO4J_QUERIES.md`

## Special Directories

### `pdfs/`

**Purpose:** Storage for generated PDF files
**Generated:** Yes (by `services/pdf_generator.py`)
**Committed:** No (in `.gitignore`)
**Served by:** `app.mount("/pdfs", StaticFiles(directory=pdfs_dir))` in `api/main.py`

### `node_modules/`

**Purpose:** Node.js dependencies
**Generated:** Yes (by `npm install`)
**Committed:** No (in `.gitignore`)
**Location:** Root and `frontend/node_modules/`

### `.venv/`

**Purpose:** Python virtual environment
**Generated:** Yes (by `python -m venv .venv`)
**Committed:** No (in `.gitignore`)

### `.planning/`

**Purpose:** GSD project planning documents
**Generated:** Yes (by GSD commands)
**Committed:** Yes (project documentation)

### `htmlcov/`

**Purpose:** Python test coverage reports
**Generated:** Yes (by `pytest --cov`)
**Committed:** No (in `.gitignore`)

### `dist/`

**Purpose:** Frontend production build output
**Generated:** Yes (by `npm run build`)
**Committed:** No (in `.gitignore`)
**Location:** `frontend/dist/`

### `test-results/`

**Purpose:** Playwright test results and artifacts
**Generated:** Yes (by `playwright test`)
**Committed:** No (in `.gitignore`)
**Location:** Root and `e2e/test-results/`

---

*Structure analysis: 2025-01-21*
