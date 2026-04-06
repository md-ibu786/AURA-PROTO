# Testing Patterns

**Analysis Date:** 2026-03-13

## Test Framework Overview

| Layer | Framework | Runner | Location |
|-------|-----------|--------|----------|
| Frontend Unit | Vitest | `npm test` | `frontend/src/**/*.test.ts(x)` |
| Frontend Component | React Testing Library | Vitest | `frontend/src/**/*.test.tsx` |
| Firestore Rules | Jest | `npm run test:rules` | `frontend/src/tests/firestore.rules.test.ts` |
| E2E | Playwright | `npm run test:e2e` | `frontend/e2e/*.spec.ts` |
| Backend | pytest | `pytest` | `tests/test_*.py`, `api/tests/test_*.py` |

## Frontend Testing (Vitest)

**Configuration:**
- Config: `frontend/vite.config.ts` (test section)
- Setup file: `frontend/src/test/setup.ts`
- Environment: `jsdom`
- Globals: enabled

**Run Commands:**
```bash
# Run all unit tests (from frontend/)
npm test

# Run with UI
npm test -- --ui

# Run specific test file
npm test -- src/api/client.test.ts

# Run with grep pattern
npm test -- --grep "DuplicateError"

# Coverage
npm test -- --coverage
```

**Test File Organization:**
```
frontend/src/
├── api/
│   ├── client.ts           # Source
│   └── client.test.ts      # Co-located test
├── stores/
│   ├── useExplorerStore.ts
│   └── useExplorerStore.test.ts
└── test/
    └── setup.ts            # Global setup
```

**Test Structure Pattern:**
```typescript
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchApi, DuplicateError } from './client';

describe('fetchApi', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.restoreAllMocks();
    });

    it('should throw DuplicateError on 409 with code', async () => {
        const mockResponse = {
            ok: false,
            status: 409,
            json: vi.fn().mockResolvedValue({
                detail: {
                    code: 'DUPLICATE_NAME',
                    message: 'Already exists'
                }
            })
        };

        vi.spyOn(global, 'fetch').mockResolvedValue(mockResponse as unknown as Response);

        await expect(fetchApi('/test')).rejects.toThrow(DuplicateError);
        await expect(fetchApi('/test')).rejects.toThrow('Already exists');

        vi.restoreAllMocks();
    });
});
```

**Mocking Patterns:**
```typescript
// Module mock with partial actual implementation
vi.mock('../api/client', async () => {
    const actual = await vi.importActual<typeof import('../api/client')>('../api/client');
    return {
        ...actual,
        fetchApi: vi.fn(actual.fetchApi),
        fetchFormData: vi.fn(actual.fetchFormData),
    };
});

// Global mock setup (in setup.ts)
beforeAll(() => {
    global.fetch = vi.fn().mockImplementation(() => {
        return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve({}),
        } as Response);
    }) as unknown as typeof global.fetch;
});

// React Query hooks mock
const mockUseQuery = vi.fn(() => ({
    data: undefined,
    isLoading: false,
    error: null,
    refetch: vi.fn(),
}));

vi.mock('@tanstack/react-query', async () => {
    const actual = await vi.importActual('@tanstack/react-query');
    return {
        ...actual,
        useQuery: mockUseQuery,
        useMutation: mockUseMutation,
    };
});
```

**Zustand Store Testing:**
```typescript
import { useExplorerStore } from './useExplorerStore';
import { act } from 'react';

describe('useExplorerStore', () => {
    beforeEach(() => {
        // Reset to initial state
        useExplorerStore.setState({
            currentPath: [],
            selectedIds: new Set(),
            // ... other state
        });
    });

    it('should select a single item', () => {
        act(() => {
            useExplorerStore.getState().select('item-1');
        });

        const state = useExplorerStore.getState();
        expect(state.selectedIds.has('item-1')).toBe(true);
    });
});
```

## Firestore Rules Testing (Jest)

**Configuration:**
- Config: `frontend/jest.config.cjs`
- Test file: `frontend/src/tests/firestore.rules.test.ts`
- Environment: `node`

**Run Commands:**
```bash
# Run with Firebase emulator
npm run test:rules

# Run directly (requires emulator running)
npm run test:rules:run
```

## E2E Testing (Playwright)

**Configuration:**
- Frontend E2E: `frontend/playwright.config.ts`

**Run Commands (from frontend/):**
```bash
# Run all E2E tests
npm run test:e2e

# Run with UI
npm run test:e2e:ui

# Run headed (visible browser)
npm run test:e2e:headed

# Run specific spec
npx playwright test e2e/explorer.spec.ts
```

# Run specific test types
npm run test:api      # API endpoint tests only
npm run test:ui       # UI interaction tests only
npm run test:audio    # Audio processing tests only
```

**Test Structure Pattern:**
```typescript
import { test, expect } from '@playwright/test';
import { ApiHelper } from '../page-objects/ApiHelper';

test.describe('API - Departments CRUD', () => {
    let api: ApiHelper;
    let createdDeptId: string;

    test.beforeEach(async ({ request }) => {
        api = new ApiHelper(request);
    });

    test.afterEach(async () => {
        // Cleanup: Delete department if it was created
        if (createdDeptId) {
            await api.deleteDepartment(createdDeptId);
            createdDeptId = '';
        }
    });

    test('Create a new department', async () => {
        const name = `E2E Dept ${Date.now()}`;
        const code = `E2E${Date.now() % 1000}`;

        const id = await api.createDepartment(name, code);
        createdDeptId = id;

        expect(id).toBeDefined();
        expect(id.length).toBeGreaterThan(0);
    });
});
```

**Page Object Pattern:**
```typescript
// e2e/page-objects/ApiHelper.ts
export class ApiHelper {
    readonly request: APIRequestContext;

    constructor(request: APIRequestContext) {
        this.request = request;
    }

    async createDepartment(name: string, code: string = 'TEST'): Promise<string> {
        const response = await this.request.post(`${API_BASE}/api/departments`, {
            data: { name, code }
        });
        expect(response.ok()).toBeTruthy();
        const data = await response.json();
        return data.department.id;
    }
}
```

**Key Playwright Settings:**
- `fullyParallel: false` - Sequential execution for DB consistency
- `workers: 1` - Single worker to prevent data conflicts
- `retries: process.env.CI ? 2 : 0` - Retry on CI only
- `screenshot: 'only-on-failure'` - Screenshots on failure
- `video: 'retain-on-failure'` - Video on failure

## Backend Testing (pytest)

**Configuration:**
- Root config: `conftest.py`
- Test discovery: `tests/test_*.py`, `api/tests/test_*.py`

**Run Commands:**
```bash
# Run all backend tests (from project root, with venv activated)
pytest

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=api --cov-report=html

# Run specific test file
pytest api/tests/test_rbac.py

# Run specific test function
pytest api/tests/test_rbac.py::test_verify_firebase_token_mock_admin

# Run tests matching pattern
pytest -k "test_verify"
```

**Test Environment Setup:**
```python
# conftest.py
import os

os.environ.setdefault("AURA_TEST_MODE", "true")
os.environ.setdefault("REDIS_ENABLED", "false")
os.environ.setdefault("TESTING", "true")
```

**Test Structure Pattern:**
```python
"""
============================================================================
FILE: test_rbac.py
LOCATION: api/tests/test_rbac.py
============================================================================
"""
import pytest
import api.auth as auth_module

class FakeAuthClient:
    """Fake Firebase auth client."""

    def __init__(self, result, exc=None):
        self._result = result
        self._exc = exc

    def verify_id_token(self, token, clock_skew_seconds):
        if self._exc:
            raise self._exc
        return self._result


@pytest.mark.asyncio
async def test_verify_firebase_token_mock_admin(monkeypatch):
    """Mock admin token returns decoded claims."""
    monkeypatch.setenv('TESTING', 'true')
    monkeypatch.setenv('USE_REAL_FIREBASE', 'false')
    
    claims = await auth_module.verify_firebase_token('mock-token-admin-001')
    assert claims['uid'] == '001'
    assert claims['role'] == 'admin'
```

**Mocking Patterns:**
```python
# Monkeypatch environment
monkeypatch.setenv('TESTING', 'false')
monkeypatch.setenv('USE_REAL_FIREBASE', 'true')

# Mock function
async def _verify_token(_):
    return {'uid': 'user-1', 'role': 'admin'}
monkeypatch.setattr(auth_module, 'verify_firebase_token', _verify_token)

# Mock Firestore
class FakeDb:
    def __init__(self, docs_by_id):
        self._docs_by_id = docs_by_id

    def collection(self, name):
        return FakeCollection(self._docs_by_id)

monkeypatch.setattr(auth_module, 'get_db', lambda: FakeDb(docs))
```

**Parameterized Tests:**
```python
@pytest.mark.parametrize(
    ('exc_name', 'detail_prefix'),
    [
        ('InvalidIdTokenError', 'Invalid authentication token:'),
        ('ExpiredIdTokenError', 'Authentication token has expired:'),
        ('RevokedIdTokenError', 'Authentication token has been revoked:'),
    ],
)
async def test_verify_firebase_token_real_error_mapping(
    monkeypatch, exc_name, detail_prefix
):
    """Real-branch errors map to HTTP 401 responses."""
    # Test implementation
```

**Class-Based Organization:**
```python
class TestTokenVerification:
    """Tests for token verification logic."""

    @pytest.mark.asyncio
    async def test_verify_mock_token_success(self):
        """Test that mock tokens still work when USE_REAL_FIREBASE=false."""
        with patch.dict("os.environ", {"USE_REAL_FIREBASE": "false"}):
            result = await verify_firebase_token(token)
            assert result["uid"] == "mock-admin-user"
```

## Coverage

**Frontend (V8):**
```typescript
// vite.config.ts
coverage: {
    provider: 'v8',
    reporter: ['text', 'json', 'html'],
    include: ['src/**/*.{ts,tsx}'],
    exclude: [
        'src/test/**',
        'src/**/*.d.ts',
        'src/main.tsx',
        'src/vite-env.d.ts',
    ],
}
```

**View Coverage:**
```bash
# Frontend (runs with vitest)
npm test -- --coverage

# Backend
pytest --cov=api --cov-report=html
```

## Common Testing Patterns

**Async Testing:**
```typescript
// TypeScript - use async/await
it('should fetch data', async () => {
    const result = await fetchApi('/endpoint');
    expect(result).toBeDefined();
});
```

```python
# Python - use pytest-asyncio
@pytest.mark.asyncio
async def test_async_function():
    result = await async_function()
    assert result is not None
```

**Error Testing:**
```typescript
// TypeScript
await expect(fetchApi('/test')).rejects.toThrow(DuplicateError);
```

```python
# Python
with pytest.raises(HTTPException) as exc_info:
    await verify_firebase_token("invalid-token")
assert exc_info.value.status_code == 401
```

**Fake/Mock Objects:**
- Use fakes for complex dependencies (FakeDb, FakeAuthClient)
- Use mocks for simple function replacement
- Prefer dependency injection over monkeypatching when possible

## Test Isolation

**Frontend:**
- `afterEach(cleanup)` in setup.ts
- `vi.clearAllMocks()` after each test
- Store state reset in beforeEach

**Backend:**
- `monkeypatch` automatically reverts changes
- Each test gets fresh environment
- Database cleanup in afterEach/afterAll

---

*Testing analysis: 2026-03-13*
