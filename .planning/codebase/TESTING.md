# Testing Patterns

**Analysis Date:** 2025-01-24

## Overview

AURA-NOTES-MANAGER employs comprehensive testing across frontend (Vitest + Playwright) and backend (pytest) with distinct strategies for unit, integration, and E2E tests. The test suite emphasizes hermetic testing with mock mode toggles, comprehensive coverage for critical paths, and performance benchmarking for batch operations.

---

## Test Frameworks

### Frontend Testing Stack

**Unit Testing:**
- **Framework:** Vitest 3.2.4
- **Assertion Library:** Vitest built-in + @testing-library/jest-dom
- **React Testing:** @testing-library/react 16.3.1
- **Coverage:** @vitest/coverage-v8

**E2E Testing:**
- **Framework:** Playwright 1.50.0
- **Browsers:** Chromium, Firefox, WebKit
- **Reporting:** HTML + list reporters

**Firestore Rules Testing:**
- **Framework:** Jest 29.7.0 (separate config)
- **Firebase Testing:** @firebase/rules-unit-testing 5.0.0
- **Environment:** Firestore emulator

### Backend Testing Stack

**Unit/Integration Testing:**
- **Framework:** pytest 8.3.3
- **Async Support:** pytest-asyncio 0.24.0
- **Coverage:** pytest-cov 6.0.0
- **Performance:** pytest-benchmark 4.0.0
- **JWT Testing:** PyJWT 2.8.0

**Mocking:**
- `unittest.mock` (Mock, MagicMock, patch, AsyncMock)

---

## Test Commands

### Frontend

**Unit tests:**
```bash
cd frontend
npm test                    # Run all unit tests with Vitest
npm run test:coverage       # Generate coverage report
```

**E2E tests:**
```bash
npm run test:e2e            # Run Playwright tests (headless)
npm run test:e2e:ui         # Run with Playwright UI
npm run test:e2e:headed     # Run with visible browser
```

**Firestore rules tests:**
```bash
npm run test:rules          # Run with Firebase emulator
```

**Watch mode:**
```bash
npx vitest --watch          # Watch mode for unit tests
```

### Backend

**All tests:**
```bash
cd AURA-NOTES-MANAGER
pytest                      # Run all tests
pytest -v                   # Verbose output
pytest -x                   # Stop on first failure
```

**Specific test file:**
```bash
pytest tests/test_auth_integration.py -v
pytest tests/test_kg_router_delete.py::TestFirestoreRetryLogic -v
```

**With coverage:**
```bash
pytest --cov=api --cov-report=term-missing
pytest --cov=api.kg.router --cov-report=html
```

**Performance benchmarks:**
```bash
pytest tests/test_batch_delete_performance.py --benchmark-only
```

### Root Commands

**Firestore rules (from root):**
```bash
firebase emulators:exec --only firestore "npx jest tests/firestore/"
```

---

## Test File Organization

### Frontend Structure

**Unit tests (co-located):**
```
src/
├── api/
│   ├── client.ts
│   └── client.test.ts                      # API client tests
├── stores/
│   ├── useExplorerStore.ts
│   └── useExplorerStore.test.ts           # Store tests
├── components/
│   ├── ui/
│   │   ├── WarningDialog.tsx
│   │   └── WarningDialog.test.tsx         # Component tests
│   └── explorer/
│       ├── ListView.tsx
│       └── __tests__/
│           └── ListView.test.tsx          # Grouped tests
├── features/
│   └── kg/
│       ├── hooks/
│       │   ├── useKGProcessing.ts
│       │   └── useKGProcessing.test.tsx   # Hook tests
│       └── components/
│           ├── ProcessDialog.tsx
│           └── ProcessDialog.test.tsx
└── pages/
    ├── ExplorerPage.tsx
    └── ExplorerPage.test.tsx              # Page tests
```

**Integration tests:**
```
src/integration/
├── WarningDialogFlow.test.tsx
├── StateSync.test.tsx
└── GridViewWarning.test.tsx
```

**E2E tests:**
```
frontend/e2e/
├── fixtures.ts                             # Shared fixtures and helpers
├── auth.setup.ts                           # Auth setup project
├── auth.spec.ts                            # Auth flows
├── explorer.spec.ts                        # Explorer CRUD
├── health.spec.ts                          # Health checks
├── kg-processing.spec.ts                   # KG processing flows
└── rbac.spec.ts                            # Role-based access
```

**Test configuration:**
```
frontend/
├── vitest.config.ts                        # Vitest + coverage config
├── playwright.config.ts                    # Playwright config
├── jest.config.cjs                         # Jest for Firestore rules
└── src/test/setup.ts                       # Vitest global setup
```

### Backend Structure

**Test directory:**
```
tests/
├── test_auth_integration.py                # Auth unit tests
├── test_auth_sync.py                       # User management
├── test_summarizer.py                      # Unit tests
├── test_summarizer_integration.py          # Integration tests
├── test_kg_router_delete.py                # Comprehensive KG tests (30 tests)
├── test_graph_manager_delete.py            # GraphManager tests
├── test_batch_delete_performance.py        # Performance benchmarks
├── test_hierarchy_duplicate_handling.py    # Duplicate name handling
├── test_department_duplicates.py           # Department CRUD
└── test_api_e2e_duplicates.py             # End-to-end flows
```

**API-level tests:**
```
api/tests/
├── test_rbac.py                            # RBAC tests
└── E2E_TEST_GUIDE.md                       # Documentation
```

**Root-level config:**
```
conftest.py                                  # Pytest global config
```

---

## Frontend Unit Tests

### Test Structure

**Vitest describe/it pattern:**
```typescript
describe('useExplorerStore', () => {
    beforeEach(() => {
        // Reset store state before each test
        useExplorerStore.setState({
            selectedIds: new Set(),
            currentPath: [],
            viewMode: 'grid',
        });
    });

    describe('Selection Actions', () => {
        it('should select single item', () => {
            const { select } = useExplorerStore.getState();
            
            act(() => {
                select('item-1');
            });

            const state = useExplorerStore.getState();
            expect(state.selectedIds.has('item-1')).toBe(true);
            expect(state.selectedIds.size).toBe(1);
        });

        it('should toggle selection', () => {
            const { toggleSelect } = useExplorerStore.getState();
            
            act(() => {
                toggleSelect('item-1');
                toggleSelect('item-1');
            });

            expect(useExplorerStore.getState().selectedIds.size).toBe(0);
        });
    });
});
```

### Component Testing

**Render + assertions:**
```typescript
/**
 * @vitest-environment jsdom
 */
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';

describe('WarningDialog', () => {
    beforeEach(() => {
        useExplorerStore.setState({
            warningDialog: { isOpen: false, type: 'error', message: '' }
        });
    });

    afterEach(() => {
        cleanup();
    });

    it('should not render when isOpen is false', () => {
        render(<WarningDialog />);
        expect(screen.queryByTestId('warning-dialog')).toBeNull();
    });

    it('should render correct content when isOpen is true', () => {
        useExplorerStore.setState({
            warningDialog: { 
                isOpen: true, 
                type: 'duplicate', 
                message: 'Department already exists' 
            }
        });

        render(<WarningDialog />);
        
        expect(screen.getByText(/Department already exists/i)).toBeTruthy();
    });

    it('should close dialog when close button is clicked', () => {
        render(<WarningDialog />);
        
        const closeBtn = screen.getByRole('button', { name: /close/i });
        fireEvent.click(closeBtn);

        expect(useExplorerStore.getState().warningDialog.isOpen).toBe(false);
    });
});
```

### Hook Testing

**renderHook from @testing-library/react:**
```typescript
import { renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';

describe('useKGProcessing', () => {
    let queryClient: QueryClient;

    beforeEach(() => {
        queryClient = new QueryClient({
            defaultOptions: {
                queries: { retry: false, gcTime: 0 },
            },
        });
    });

    const wrapper = ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>
            {children}
        </QueryClientProvider>
    );

    it('should process files mutation', async () => {
        const { result } = renderHook(() => useKGProcessing(), { wrapper });
        
        // Test mutation behavior
        expect(result.current.processFiles).toBeDefined();
    });
});
```

---

## Backend Tests

### Test Structure

**pytest class-based organization:**
```python
class TestTokenVerification:
    """Tests for token verification logic."""

    @pytest.mark.asyncio
    async def test_verify_mock_token_success(self) -> None:
        """Test that mock tokens still work when USE_REAL_FIREBASE=false."""
        with patch.dict("os.environ", {"USE_REAL_FIREBASE": "false"}):
            token = "mock-token-admin"
            result = await verify_firebase_token(token)

            assert result["uid"] == "mock-admin-user"
            assert result["email"] == "admin@aura.edu"
            assert result["role"] == "admin"

    @pytest.mark.asyncio
    async def test_verify_mock_token_invalid(self) -> None:
        """Test that invalid mock tokens are rejected."""
        with patch.dict("os.environ", {"USE_REAL_FIREBASE": "false"}):
            with pytest.raises(HTTPException) as exc_info:
                await verify_firebase_token("invalid-token")

            assert exc_info.value.status_code == 401
```

### Comprehensive Test Suite Example

**From `test_kg_router_delete.py` (30 tests, 1,175 lines):**

```python
class TestBatchDeleteRequestValidation:
    """Tests for BatchDeleteRequest Pydantic model validation."""

    def test_valid_batch_request_creates_model(self) -> None:
        """Test: Valid request data creates model successfully."""
        request = BatchDeleteRequest(
            file_ids=["file-1", "file-2"],
            module_id="module-123"
        )
        assert request.file_ids == ["file-1", "file-2"]
        assert request.module_id == "module-123"

    def test_missing_file_ids_raises_validation_error(self) -> None:
        """Test: Missing file_ids field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            BatchDeleteRequest(module_id="module-123")
        
        errors = exc_info.value.errors()
        assert any(e["loc"] == ("file_ids",) for e in errors)


class TestSuccessfulDeletion:
    """Tests for successful batch deletion workflows."""

    @pytest.mark.asyncio
    async def test_delete_single_document_success(self, mock_db, mock_graph_manager):
        """Test: Single document deletion returns deleted_count=1."""
        # Setup mocks...
        
        response = await delete_batch(request, mock_db, mock_graph_manager)
        
        assert response.deleted_count == 1
        assert len(response.failed) == 0
        assert "1 file(s) deleted" in response.message
```

### Fixtures

**pytest fixtures for reusable setup:**
```python
@pytest.fixture
def mock_driver():
    """Create a mock Neo4j driver."""
    return MagicMock()

@pytest.fixture
def graph_manager(mock_driver):
    """Create GraphManager with mocked driver."""
    return GraphManager(mock_driver)

@pytest.fixture
def mock_db():
    """Mock Firestore client."""
    db = MagicMock()
    # Configure mock behavior...
    return db
```

**Usage:**
```python
def test_with_fixtures(mock_db, graph_manager):
    # Fixtures auto-injected by pytest
    assert mock_db is not None
    assert graph_manager is not None
```

---

## E2E Tests

### Playwright Configuration

**Config file (`playwright.config.ts`):**
```typescript
export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,           // Sequential for DB consistency
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
    { name: 'firefox', use: { ...devices['Desktop Firefox'] } },
    { name: 'webkit', use: { ...devices['Desktop Safari'] } },
  ],
  
  webServer: {
    command: 'npm run dev',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: !process.env.CI,
  },
});
```

### E2E Test Pattern

**Page object pattern with fixtures:**
```typescript
import { test, expect, type Locator, mockTreeResponse, waitForLoading } from './fixtures';

test.describe('Explorer Page Layout @critical', { tag: '@critical' }, () => {
  test.beforeEach(async ({ page }) => {
    await mockTreeResponse(page);
    await page.goto('/');
    await waitForLoading(page);
  });

  test('displays main layout elements', async ({ page }) => {
    const sidebar = page.locator('.explorer-sidebar, aside');
    await expect(sidebar.first()).toBeVisible();

    const mainContent = page.locator('.explorer-main, main');
    await expect(mainContent.first()).toBeVisible();
  });

  test('has responsive layout', async ({ page }) => {
    // Desktop view
    await page.setViewportSize({ width: 1280, height: 720 });
    const sidebarDesktop = page.locator('.explorer-sidebar');
    await expect(sidebarDesktop.first()).toBeVisible();

    // Mobile view
    await page.setViewportSize({ width: 375, height: 667 });
    const mainContent = page.locator('.explorer-main');
    await expect(mainContent.first()).toBeVisible();
  });
});
```

**Fixtures for reusable helpers:**
```typescript
// fixtures.ts
export async function mockTreeResponse(page: Page) {
    await page.route('**/api/explorer/tree', async (route) => {
        await route.fulfill({
            status: 200,
            body: JSON.stringify(mockTreeData),
        });
    });
}

export async function waitForLoading(page: Page) {
    await page.waitForSelector('[data-loading="false"]', { timeout: 5000 });
}
```

---

## Mocking Patterns

### Frontend Mocks

**Global test setup (`src/test/setup.ts`):**
```typescript
// Mock API client
vi.mock('../api/client', async () => {
    const actual = await vi.importActual('../api/client');
    return {
        ...actual,
        fetchApi: vi.fn(actual.fetchApi),
        fetchFormData: vi.fn(actual.fetchFormData),
    };
});

// Mock window.matchMedia
Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
    })),
});

// Mock React Query hooks
vi.mock('@tanstack/react-query', async () => {
    const actual = await vi.importActual('@tanstack/react-query');
    return {
        ...actual,
        useQuery: vi.fn(() => ({
            data: undefined,
            isLoading: false,
            error: null,
        })),
        useMutation: vi.fn(() => ({
            mutate: vi.fn(),
            isPending: false,
        })),
    };
});
```

**Per-test mocks:**
```typescript
it('should throw DuplicateError on 409', async () => {
    const mockResponse = {
        ok: false,
        status: 409,
        json: vi.fn().mockResolvedValue({
            detail: { code: 'DUPLICATE_NAME', message: 'Already exists' }
        })
    };

    vi.spyOn(global, 'fetch').mockResolvedValue(mockResponse as Response);

    await expect(fetchApi('/test')).rejects.toThrow(DuplicateError);
    
    vi.restoreAllMocks();
});
```

**Icon mocks:**
```typescript
vi.mock('lucide-react', () => ({
    AlertTriangle: () => <div data-testid="alert-icon" />,
    X: () => <div data-testid="close-icon" />
}));
```

### Backend Mocks

**Environment variable mocking:**
```python
@pytest.mark.asyncio
async def test_verify_mock_token_success() -> None:
    """Test mock token verification."""
    with patch.dict("os.environ", {"USE_REAL_FIREBASE": "false"}):
        result = await verify_firebase_token("mock-token-admin")
        assert result["uid"] == "mock-admin-user"
```

**Firestore client mocking:**
```python
def test_delete_document_success(self):
    mock_db = MagicMock()
    mock_doc = MagicMock()
    mock_doc.get.return_value.exists = True
    mock_doc.get.return_value.to_dict.return_value = {
        "name": "Test Department",
        "kg_status": "ready",
        "module_id": "module-123"
    }
    
    mock_db.collection.return_value.document.return_value = mock_doc
    
    # Use mock_db in test...
```

**Service mocking with patch:**
```python
@patch('services.summarizer.get_genai_model')
@patch('services.summarizer.get_model')
def test_generate_notes_with_genai(self, mock_get_model, mock_get_genai):
    mock_genai_model = Mock()
    mock_response = Mock()
    mock_response.text = "Mocked notes content"
    mock_genai_model.generate_content.return_value = mock_response
    mock_get_genai.return_value = mock_genai_model
    
    result = generate_university_notes("Topic", "Transcript")
    
    assert result == "Mocked notes content"
    mock_get_genai.assert_called_once_with("gemini-3-flash-preview")
```

**AsyncMock for async functions:**
```python
@pytest.mark.asyncio
async def test_async_operation():
    mock_session = MagicMock()
    mock_driver.session.return_value.__enter__.return_value = mock_session
    
    def mock_run(query, *args, **kwargs):
        result = MagicMock()
        result.data.return_value = []
        return result
    
    mock_session.run = mock_run
    
    await graph_manager.cleanup_orphaned_entities(["entity-1"])
```

---

## Test Coverage

### Frontend Coverage Configuration

**Vitest config (`vite.config.ts`):**
```typescript
test: {
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
    },
}
```

**Coverage output:**
- Text report: Terminal
- HTML report: `frontend/coverage/index.html`
- JSON report: `frontend/coverage/coverage-final.json`

### Backend Coverage Configuration

**Run with pytest-cov:**
```bash
pytest --cov=api --cov-report=term-missing
pytest --cov=api.kg.router --cov-report=html
```

**Coverage output:**
- Text report: Terminal with missing lines
- HTML report: `htmlcov/index.html`

### Coverage Status

**Frontend:**
- Comprehensive unit tests for stores, hooks, and critical components
- Integration tests for complex flows (warning dialogs, state sync)
- E2E tests for user journeys (auth, CRUD, KG processing)

**Backend:**
- **Outstanding example:** `test_kg_router_delete.py` - 30 tests covering:
  - Request/response validation (6 tests)
  - Successful deletion workflows (2 tests)
  - Partial failure scenarios (4 tests)
  - Firestore retry logic with timing (5 tests)
  - Orphan cleanup deduplication (4 tests)
  - Error handling (4 tests)
  - Edge cases (3 tests)
  - Full integration (1 test)

**Documented test suites:**
- `README_TESTS.md`: Comprehensive guide to `/kg/delete-batch` tests
- `TEST_SUITE_COMPLETE.md`: Full test suite overview
- `TESTING_SUMMARY.md`: Testing strategy summary

---

## Testing Anti-Patterns to Avoid

### Don't Mock What You're Testing

**Bad:**
```typescript
// Don't mock the function under test
vi.mock('./useExplorerStore', () => ({
    useExplorerStore: vi.fn(() => ({ select: vi.fn() }))
}));

// Test becomes meaningless
it('should select', () => {
    const { select } = useExplorerStore();
    select('id');
    expect(select).toHaveBeenCalled(); // ❌ Circular reasoning
});
```

**Good:**
```typescript
// Test actual implementation
it('should select', () => {
    const { select } = useExplorerStore.getState();
    
    act(() => select('item-1'));
    
    const state = useExplorerStore.getState();
    expect(state.selectedIds.has('item-1')).toBe(true); // ✓ Real assertion
});
```

### Don't Skip Cleanup

**Bad:**
```typescript
it('test 1', () => {
    render(<Component />);
    // No cleanup - state leaks to next test
});

it('test 2', () => {
    render(<Component />); // ❌ Polluted by test 1
});
```

**Good:**
```typescript
afterEach(() => {
    cleanup();           // React Testing Library cleanup
    vi.clearAllMocks();  // Clear all mocks
});
```

### Don't Use waitFor When Not Needed

**Bad:**
```typescript
it('renders text', async () => {
    render(<Component />);
    await waitFor(() => {
        expect(screen.getByText('Hello')).toBeInTheDocument(); // ❌ Unnecessary async
    });
});
```

**Good:**
```typescript
it('renders text', () => {
    render(<Component />);
    expect(screen.getByText('Hello')).toBeInTheDocument(); // ✓ Synchronous
});
```

---

## Test Organization Best Practices

### Group Related Tests

**Use describe blocks for logical grouping:**
```typescript
describe('useExplorerStore', () => {
    describe('Selection Actions', () => {
        it('should select single item', () => { /* ... */ });
        it('should toggle selection', () => { /* ... */ });
        it('should clear selection', () => { /* ... */ });
    });

    describe('Navigation Actions', () => {
        it('should navigate to path', () => { /* ... */ });
        it('should go back', () => { /* ... */ });
    });
});
```

### Descriptive Test Names

**Pattern: "should [expected behavior] when [condition]"**

```typescript
it('should return deleted_count=1 when single document deleted successfully', () => {});
it('should retry with exponential backoff when Firestore update fails', () => {});
it('should skip cleanup when no successful deletions', () => {});
```

### One Assertion Per Concept

**Prefer:**
```typescript
it('should update selected IDs', () => {
    expect(state.selectedIds.has('item-1')).toBe(true);
});

it('should update last selected ID', () => {
    expect(state.lastSelectedId).toBe('item-1');
});
```

**Over:**
```typescript
it('should update selection state', () => {
    expect(state.selectedIds.has('item-1')).toBe(true);
    expect(state.lastSelectedId).toBe('item-1');
    expect(state.selectionMode).toBe(true);
    expect(state.clipboard).toEqual({ nodeIds: [], mode: null });
    // ❌ Too many unrelated assertions
});
```

---

## Hermetic Testing

### Test Mode Flags

**Backend (conftest.py):**
```python
# Pytest configuration for hermetic tests
import os

os.environ.setdefault("AURA_TEST_MODE", "true")
os.environ.setdefault("REDIS_ENABLED", "false")
os.environ.setdefault("TESTING", "true")
```

**Usage in code:**
```python
async def verify_firebase_token(token: str) -> dict:
    use_real_firebase = os.getenv("USE_REAL_FIREBASE", "false").lower() == "true"
    is_testing = os.getenv("TESTING", "false").lower() == "true"

    if is_testing and not use_real_firebase:
        return _verify_mock_token(token)  # Use mock in tests
    
    # Real Firebase verification...
```

**Frontend (Playwright):**
```typescript
// playwright.config.ts
if (!process.env.VITE_USE_MOCK_AUTH) {
    process.env.VITE_USE_MOCK_AUTH = 'true';  // Default to mock auth
}

export default defineConfig({
    webServer: {
        env: {
            VITE_USE_MOCK_AUTH: 'true',  // Force mock auth in E2E
        },
    },
});
```

### Avoiding External Dependencies

**Skip Neo4j in test mode:**
```python
# api/neo4j_config.py
AURA_TEST_MODE = os.getenv("AURA_TEST_MODE", "false").lower() == "true"

if AURA_TEST_MODE:
    neo4j_driver = None  # Skip initialization
else:
    neo4j_driver = initialize_neo4j()
```

**Mock Firestore responses:**
```python
def test_with_mock_firestore():
    mock_db = MagicMock()
    # Configure mock instead of real Firestore
```

---

## Performance Testing

### Benchmark Tests

**pytest-benchmark example:**
```python
class TestBatchDeletePerformance:
    """Performance tests for batch deletion operations."""

    @pytest.mark.asyncio
    async def test_cleanup_called_once_per_batch(self, graph_manager):
        """
        Test: cleanup_orphaned_entities() called only once for batch.
        
        Proves O(1) complexity improvement (not O(N) per-document cleanup).
        """
        cleanup_call_count = {"count": 0}

        def mock_run(query, *args, **kwargs):
            if "WHERE e.id IN" in query:
                cleanup_call_count["count"] += 1
            return MagicMock()

        # Execute batch cleanup with 100 entity IDs
        entity_ids = [f"entity-{i}" for i in range(100)]
        await graph_manager.cleanup_orphaned_entities(entity_ids)

        # Verify cleanup ran exactly once (not 100 times)
        assert cleanup_call_count["count"] == 1
```

### Timing Verification

**Exponential backoff testing:**
```python
@pytest.mark.asyncio
async def test_retry_timing_exponential_backoff(self):
    """Test: Exponential backoff timing (0.5s → 1s → 2s)."""
    retry_times = []
    
    with patch('asyncio.sleep') as mock_sleep:
        mock_sleep.side_effect = lambda delay: retry_times.append(delay)
        
        # Trigger retries...
        
        assert len(retry_times) == 2  # 2 retries
        assert retry_times[0] == 0.5  # First retry
        assert retry_times[1] == 1.0  # Second retry
```

---

## Continuous Integration

### CI Configuration

**GitHub Actions (inferred from playwright.config.ts):**
```typescript
forbidOnly: !!process.env.CI,       // Fail if test.only in CI
retries: process.env.CI ? 2 : 0,    // Retry flaky tests in CI
workers: process.env.CI ? 1 : undefined,  // Sequential in CI
```

**Expected CI workflow:**
```yaml
# .github/workflows/test.yml (example)
jobs:
  test-frontend:
    steps:
      - run: npm test
      - run: npm run test:e2e
  
  test-backend:
    steps:
      - run: pytest --cov=api
```

---

## Test Documentation

### Inline Test Documentation

**Comprehensive docstrings:**
```python
class TestFirestoreRetryLogic:
    """
    Tests for _update_firestore_with_retry() exponential backoff.
    
    Validates:
    - Success on 1st attempt (1 DB call, 0 sleeps)
    - Success on 2nd attempt (2 calls, 1 sleep)
    - Failure after max retries (3 attempts, 2 sleeps)
    - Exponential backoff timing: 0.5s → 1s → 2s
    - Warning logs on retry attempts
    - Critical log on final failure
    """
```

### Test Plan Documents

**Available documentation:**
- `README_TESTS.md`: Quick start guide for `/kg/delete-batch` tests
- `TEST_PLAN_DELETE_BATCH.md`: Detailed test objectives
- `TEST_SUITE_COMPLETE.md`: Complete test suite overview
- `TESTING_SUMMARY.md`: High-level testing strategy

---

*Testing analysis: 2025-01-24*
