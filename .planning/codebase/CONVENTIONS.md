# Code Conventions

**Analysis Date:** 2025-01-24

## Overview

AURA-NOTES-MANAGER is a full-stack TypeScript/Python application with React frontend (Vite + TypeScript) and FastAPI backend. The codebase uses strict TypeScript configuration, comprehensive linting, and extensive header documentation patterns for code organization and discoverability.

---

## Naming Patterns

### Files - Frontend (TypeScript/TSX)

**Components:**
- PascalCase: `ExplorerPage.tsx`, `WarningDialog.tsx`, `ListView.tsx`
- Test files: `{ComponentName}.test.tsx` (co-located with source)

**Hooks:**
- camelCase with `use` prefix: `useExplorerStore.ts`, `useKGProcessing.ts`
- Test files: `{hookName}.test.tsx`

**API Modules:**
- camelCase: `client.ts`, `explorerApi.ts`, `audioApi.ts`, `userApi.ts`

**Types:**
- Singular nouns: `user.ts`, `kg.types.ts`

**Utilities/Services:**
- camelCase: `firebaseClient.ts`

### Files - Backend (Python)

**Routers:**
- Snake_case: `hierarchy_crud.py`, `auth_sync.py`, `graph_manager.py`

**Test files:**
- `test_{module_name}.py`: `test_auth_integration.py`, `test_summarizer.py`

**Models/Schemas:**
- `models.py`, `schemas/{domain}.py`: `schemas/graph_preview.py`

**Services:**
- Descriptive: `summarizer.py`, `summary_service.py`

### Functions - Frontend

**Standard functions:**
- camelCase: `fetchApi()`, `getKGDocumentStatus()`, `processKGBatch()`

**React components:**
- PascalCase (function declarations): `function ListView()`, `function WarningDialog()`

**Event handlers:**
- Prefix with `handle` or `on`: `handleClick`, `onClose`, `handleRename`

**Utilities:**
- camelCase verbs: `waitForLoading()`, `mockTreeResponse()`, `primeExplorerTreeCache()`

### Functions - Backend

**Endpoint handlers:**
- Snake_case: `get_current_user()`, `verify_firebase_token()`, `delete_document_recursive()`

**Utility functions:**
- Snake_case verbs: `get_unique_name()`, `get_next_available_number()`, `cleanup_orphaned_entities()`

**Private helpers:**
- Prefix with underscore: `_verify_mock_token()`, `_update_firestore_with_retry()`

### Variables

**Frontend:**
- camelCase: `queryClient`, `selectedIds`, `renamingNodeId`
- Constants: SCREAMING_SNAKE_CASE for true constants (rare)
- Type annotations: PascalCase interfaces/types

**Backend:**
- Snake_case: `mock_driver`, `graph_manager`, `entity_ids`
- Class names: PascalCase `GraphManager`, `SummaryService`, `FirestoreUser`
- Type aliases: PascalCase `UserRole`, `UserStatus`

### Types and Interfaces

**Frontend:**
- PascalCase: `FileSystemNode`, `ProcessingRequest`, `BatchDeleteRequest`
- Literal types: lowercase: `'admin' | 'staff' | 'student'`
- Props interfaces: `{ComponentName}Props`

**Backend (Pydantic):**
- PascalCase: `FirestoreUser`, `CreateUserInput`, `UpdateUserInput`
- Type literals: `Literal["admin", "staff", "student"]`
- Response models: `{Operation}Response`: `TaskStatus`, `CacheInvalidationResponse`

---

## File Organization

### Frontend Structure

**Entry points:**
- `frontend/src/main.tsx`: Application bootstrap, renders App
- `frontend/src/App.tsx`: Router configuration, global UI (Toaster)

**Feature-based organization:**
```
src/
├── api/                    # API client layer
│   ├── client.ts           # Base fetch utilities, DuplicateError
│   ├── explorerApi.ts      # Hierarchy/explorer endpoints
│   ├── audioApi.ts         # Audio processing endpoints
│   ├── userApi.ts          # User management endpoints
│   └── firebaseClient.ts   # Firebase SDK initialization
├── components/
│   ├── explorer/           # Explorer-specific components
│   ├── layout/             # Header, Sidebar
│   └── ui/                 # Reusable UI primitives (dialog, button)
├── features/               # Feature modules (KG processing)
│   └── kg/
│       ├── components/     # KG-specific UI
│       ├── hooks/          # KG-specific React Query hooks
│       └── types/          # KG type definitions
├── hooks/                  # Global custom hooks
├── pages/                  # Route-level components
├── stores/                 # Zustand state management
├── test/                   # Test setup and utilities
├── tests/                  # Firestore rules tests
└── types/                  # Global type definitions
```

**Key patterns:**
- Co-located tests: Place `.test.tsx` files next to implementation
- Feature modules for bounded contexts: `features/kg/`
- Shared UI in `components/ui/`

### Backend Structure

**Entry point:**
- `api/main.py`: FastAPI app, middleware, router mounting

**Module organization:**
```
api/
├── main.py                 # App entry, CORS, rate limiting
├── auth.py                 # Firebase token verification, RBAC
├── auth_sync.py            # User management endpoints
├── config.py               # Firebase client initialization
├── models.py               # Pydantic user models
├── routers/                # Feature routers (summaries, trends, etc.)
├── schemas/                # Pydantic request/response schemas
├── kg/                     # Knowledge graph feature module
│   └── router.py
├── hierarchy/              # Hierarchy management module
│   ├── router.py
│   └── models.py
├── modules/                # Module publishing feature
│   ├── router.py
│   ├── models.py
│   └── service.py
├── tasks/                  # Celery background tasks
└── migrations/             # Schema migrations
```

**Key patterns:**
- Routers in `routers/` or feature packages (`kg/router.py`)
- Shared schemas in `schemas/{domain}.py`
- Services in feature packages (`modules/service.py`)

### Test Organization

**Frontend:**
- Unit tests: Co-located `.test.tsx` files
- Integration tests: `src/integration/*.test.tsx`
- E2E tests: `frontend/e2e/*.spec.ts` (Playwright)
- Test setup: `src/test/setup.ts` (Vitest global config)

**Backend:**
- Unit tests: `tests/test_{module}.py`
- Integration tests: Same directory, suffix-based
- E2E tests: `api/tests/test_{feature}_e2e.py`
- Fixtures: `conftest.py` (pytest configuration)

---

## Import Patterns

### Frontend Import Order

**Standard order:**
1. External dependencies (React, libraries)
2. Internal API modules (`@/api/...`)
3. Internal components (`@/components/...`)
4. Internal stores (`@/stores/...`)
5. Internal types (`@/types/...`)
6. Styles (if any)

**Example from `ListView.tsx`:**
```typescript
import { useExplorerStore } from '../../stores';
import * as React from 'react';
import { useQueryClient } from '@tanstack/react-query';
import type { FileSystemNode } from '../../types';
import { Building2, Calendar, BookOpen } from 'lucide-react';
```

**Path aliases:**
- `@/*` resolves to `src/*` (configured in `tsconfig.app.json` and `vite.config.ts`)
- Prefer absolute imports for cross-feature references
- Relative imports for same-feature files

**Type imports:**
- Use `import type` for type-only imports (enforced by TypeScript isolatedModules)

### Backend Import Order

**Standard order:**
1. Standard library (`os`, `logging`, `datetime`)
2. External dependencies (`fastapi`, `pydantic`, `firebase_admin`)
3. Internal imports with try/except for module vs script execution

**Example from `auth.py`:**
```python
import os

from firebase_admin import auth
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

try:
    from config import get_auth, get_db
    from models import FirestoreUser
except ImportError:
    from api.config import get_auth, get_db
    from api.models import FirestoreUser
```

**Pattern for dual-mode imports:**
```python
# Supports both 'python api/main.py' and 'from api.main import app'
try:
    from config import db
except ImportError:
    from api.config import db
```

---

## TypeScript Patterns

### Configuration

**Strict mode enabled** (`tsconfig.app.json`):
```json
{
  "strict": true,
  "noUnusedLocals": true,
  "noUnusedParameters": true,
  "noFallthroughCasesInSwitch": true,
  "noUncheckedSideEffectImports": true
}
```

### Type Definitions

**Prefer interfaces for object shapes:**
```typescript
export interface FirestoreUser {
    uid: string;
    email: string;
    displayName?: string;
    role: UserRole;
}
```

**Use type aliases for unions:**
```typescript
export type UserRole = 'admin' | 'staff' | 'student';
export type UserStatus = 'active' | 'disabled';
```

**Generic types for reusable patterns:**
```typescript
type BlobResponse = {
    blob: Blob;
    filename: string;
}
```

### React Patterns

**Function components with typed props:**
```typescript
interface ListViewProps {
    items: FileSystemNode[];
    allItems: FileSystemNode[];
}

export function ListView({ items, allItems }: ListViewProps) {
    // ...
}
```

**Hooks with explicit return types:**
```typescript
export function useKGProcessing() {
    const queryClient = useQueryClient();
    
    const { mutate: processFiles } = useMutation<
        ProcessingResponse,
        Error,
        ProcessingRequest
    >({
        mutationFn: processKGBatch,
        // ...
    });
    
    return { processFiles, /* ... */ };
}
```

**State with type inference:**
```typescript
const [renameValue, setRenameValue] = React.useState('');  // inferred as string
const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
```

---

## Python Patterns

### Type Annotations

**Function signatures with type hints:**
```python
async def verify_firebase_token(token: str) -> dict:
    """Verify a Firebase ID token and return decoded claims."""
    # ...
```

**Pydantic models for validation:**
```python
class FirestoreUser(pydantic.BaseModel):
    uid: str = pydantic.Field(..., description="Firebase Auth UID")
    email: str = pydantic.Field(..., description="User email address")
    role: UserRole = pydantic.Field(..., description="User role")
    status: UserStatus = pydantic.Field("active", description="Account status")
```

**Type aliases for domain concepts:**
```python
UserRole = typing.Literal["admin", "staff", "student"]
UserStatus = typing.Literal["active", "disabled"]
```

### FastAPI Patterns

**Dependency injection for auth:**
```python
@router.get("/api/users")
async def list_users(user: FirestoreUser = Depends(require_admin)):
    """List all users. Admin only."""
    # ...
```

**Response models for validation:**
```python
@router.post("/v1/summaries/document/{document_id}", response_model=DocumentSummary)
async def summarize_document(
    document_id: str,
    length: SummaryLength = Query(default=SummaryLength.STANDARD),
    service: SummaryService = Depends(get_summary_service)
) -> DocumentSummary:
    # ...
```

**Pydantic field aliases for camelCase/snake_case:**
```python
class CreateUserInput(pydantic.BaseModel):
    displayName: typing.Optional[str] = pydantic.Field(
        None,
        validation_alias=pydantic.AliasChoices("displayName", "display_name"),
    )
```

---

## Error Handling Patterns

### Frontend

**Custom error classes:**
```typescript
export class DuplicateError extends Error {
    code: string;
    constructor(message: string, code: string) {
        super(message);
        this.code = code;
        this.name = 'DuplicateError';
    }
}
```

**Centralized error parsing in API client:**
```typescript
export async function fetchApi(url: string, options?: RequestInit) {
    const response = await fetch(url, options);
    
    if (!response.ok) {
        const errorData = await response.json();
        
        if (response.status === 409 && errorData.detail?.code) {
            throw new DuplicateError(errorData.detail.message, errorData.detail.code);
        }
        
        throw new Error(errorData.detail || 'Request failed');
    }
    
    return response.json();
}
```

**Try-catch in React Query mutations:**
```typescript
const { mutate } = useMutation({
    mutationFn: processKGBatch,
    onSuccess: () => {
        toast.success('Processing started');
    },
    onError: (error: Error) => {
        toast.error(error.message);
    }
});
```

### Backend

**HTTPException for API errors:**
```python
if not decoded_token:
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )
```

**Specific exception handling with logging:**
```python
try:
    decoded_token = auth_client.verify_id_token(token, clock_skew_seconds=10)
    return decoded_token
except auth.InvalidIdTokenError as exc:
    logger.warning(f"Invalid token error: {exc}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Invalid authentication token: {str(exc)}",
    )
except auth.ExpiredIdTokenError as exc:
    logger.warning(f"Expired token error: {exc}")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=f"Authentication token has expired: {str(exc)}",
    )
```

**Graceful degradation in services:**
```python
def generate_university_notes(topic: str, transcript: str) -> str:
    try:
        model = get_genai_model("gemini-3-flash-preview")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Note generation failed: {e}")
        return f"Note Generation Failed: {str(e)}"
```

---

## State Management Patterns

### Zustand Stores (Frontend)

**Store definition with actions:**
```typescript
export const useExplorerStore = create<ExplorerStore>((set, get) => ({
    // State
    selectedIds: new Set<string>(),
    currentPath: [],
    viewMode: 'grid',
    
    // Actions
    select: (id: string) => set({ selectedIds: new Set([id]) }),
    toggleSelect: (id: string) => set((state) => {
        const newSet = new Set(state.selectedIds);
        newSet.has(id) ? newSet.delete(id) : newSet.add(id);
        return { selectedIds: newSet };
    }),
    clearSelection: () => set({ selectedIds: new Set() }),
}));
```

**Usage in components:**
```typescript
function ListView() {
    const { selectedIds, select, toggleSelect } = useExplorerStore();
    // ...
}
```

### React Query for Server State

**Query hooks with refetch intervals:**
```typescript
const { data: queueStatus } = useQuery({
    queryKey: ['kg-processing-queue', moduleId],
    queryFn: () => getKGProcessingQueue(moduleId),
    refetchInterval: (data) => 
        data?.status === 'processing' ? 2000 : false,
    enabled: !!moduleId && isPolling,
});
```

**Mutation hooks with optimistic updates:**
```typescript
const { mutate: renameNode } = useMutation({
    mutationFn: (params: { id: string; newName: string }) => 
        renameEntity(params.id, params.newName),
    onSuccess: () => {
        queryClient.invalidateQueries(['explorer-tree']);
        toast.success('Renamed successfully');
    }
});
```

---

## API Communication Patterns

### Authentication

**Token in Authorization header:**
```typescript
export async function fetchApi(url: string, options: RequestInit = {}) {
    const token = useAuthStore.getState().token;
    
    const headers = {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options.headers,
    };
    
    return fetch(url, { ...options, headers });
}
```

**Dependency-based auth in backend:**
```python
security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> FirestoreUser:
    token = credentials.credentials
    decoded = await verify_firebase_token(token)
    # ... lookup user in Firestore
    return user
```

### Request/Response Patterns

**FormData for file uploads:**
```typescript
export async function uploadAudio(file: File, moduleId: string) {
    const formData = new FormData();
    formData.append('audio_file', file);
    formData.append('module_id', moduleId);
    
    return fetchFormData('/api/audio/upload', formData);
}
```

**JSON for structured data:**
```typescript
export async function processKGBatch(request: ProcessingRequest) {
    return fetchApi('/kg/process', {
        method: 'POST',
        body: JSON.stringify(request),
    });
}
```

**Blob downloads:**
```typescript
export async function downloadPDF(noteId: string): Promise<BlobResponse> {
    const response = await fetchBlob(`/api/notes/${noteId}/pdf`);
    return response;
}
```

---

## Documentation Practices

### File Headers

**All files include comprehensive headers:**

**Frontend example:**
```typescript
/**
 * ============================================================================
 * FILE: ListView.tsx
 * LOCATION: frontend/src/components/explorer/ListView.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Table-style list view for displaying explorer items.
 *
 * ROLE IN PROJECT:
 *    Provides a compact explorer view with selection, rename, and navigation
 *    behavior aligned with the GridView component.
 *
 * KEY COMPONENTS:
 *    - ListView: Renders rows and handles click/double-click actions.
 *    - typeIcons: Maps hierarchy types to row icons.
 *
 * DEPENDENCIES:
 *    - External: react, lucide-react, @tanstack/react-query
 *    - Internal: stores/useExplorerStore, api/explorerApi, types
 *
 * USAGE:
 *    <ListView items={currentFolderChildren} allItems={fullTree} />
 * ============================================================================
 */
```

**Backend example:**
```python
"""
============================================================================
FILE: auth.py
LOCATION: api/auth.py
============================================================================

PURPOSE:
    Firebase Authentication utilities for verifying ID tokens and extracting
    user role information for role-based access control (RBAC).

ROLE IN PROJECT:
    Provides FastAPI dependencies for protected endpoints. All endpoints that
    require authentication or specific roles should use these dependencies.

KEY COMPONENTS:
    - verify_firebase_token(): Verify Firebase ID token
    - get_current_user(): FastAPI dependency returning current user with role
    - require_admin(): Dependency that ensures user is an admin
    - require_staff(): Dependency that ensures user is staff (or admin)

DEPENDENCIES:
    - External: firebase_admin.auth, fastapi
    - Internal: config.py (Firestore client)

USAGE:
    from auth import get_current_user, require_admin
    
    @app.get("/api/users")
    async def list_users(user = Depends(require_admin)):
        ...
============================================================================
"""
```

### Inline Comments

**Use `@see` for cross-references:**
```typescript
// @see: useExplorerStore.ts - Store under test
// @see: api/client.ts - API functions mocked here
```

**Use `@note` for important caveats:**
```typescript
// @note: Use 127.0.0.1 not localhost to avoid IPv6 issues
// @note: Large modules (>10 docs) may use background processing
```

**Explain complex logic:**
```python
# Manual cascade TODO: Files cleanup (omitted for brevity, requires iterating notes)
```

### JSDoc/TSDoc for Public APIs

**Minimal usage - headers are preferred:**
```typescript
/**
 * Dependency to get SummaryService instance.
 *
 * Creates a new SummaryService with the global Neo4j driver.
 *
 * Returns:
 *     SummaryService: Configured summary service instance.
 */
async def get_summary_service() -> SummaryService:
    # ...
```

---

## Linting and Formatting

### Frontend

**ESLint configuration** (`eslint.config.js`):
- Based on `@eslint/js` recommended
- TypeScript ESLint recommended rules
- React Hooks recommended-latest
- Custom rule: `react-refresh/only-export-components`

**No Prettier** - formatting via ESLint only

**Run linting:**
```bash
npm run lint
```

### Backend

**No explicit linter config detected**

Conventions observed:
- Line length: ~80-100 characters
- Indentation: 4 spaces
- Blank lines between functions
- Docstrings for all public functions

---

## Environment Configuration

### Frontend

**Environment variables:**
- Prefix: `VITE_*` (Vite convention)
- `VITE_USE_MOCK_AUTH`: Enable mock auth for testing
- Firebase config in `firebaseClient.ts`

**Files:**
- `.env` (gitignored)
- `.env.example` (template)
- `.env.e2e.example` (E2E template)

### Backend

**Environment variables:**
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to service account key
- `USE_REAL_FIREBASE`: Toggle real vs mock Firebase
- `TESTING`: Test mode flag (skips external services)
- `REDIS_ENABLED`: Enable/disable Redis caching
- `AURA_TEST_MODE`: Hermetic test mode

**Loading:**
```python
from dotenv import load_dotenv
load_dotenv(env_path, override=True)
```

**Files:**
- `.env` (gitignored - NEVER commit or read)
- `.env.example` (template)

---

## Comments and Code Quality

### When to Comment

**Always document:**
- File headers (purpose, role, dependencies)
- Complex algorithms or business logic
- Workarounds and TODOs
- Public API functions

**Rarely comment:**
- Self-explanatory code
- Variable declarations (use descriptive names)

### TODO Patterns

**Single TODO found in codebase:**
```python
# Manual cascade TODO: Files cleanup (omitted for brevity, requires iterating notes)
```

**Pattern: Explain what's missing and why**

---

*Convention analysis: 2025-01-24*
