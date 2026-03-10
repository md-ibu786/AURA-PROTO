# Testing Patterns

**Analysis Date:** 2026-03-10

## Test Framework

**Runner:**
- Vitest `^3.2.4` for frontend unit and integration tests via `frontend/package.json` and config embedded in `frontend/vite.config.ts`.
- Jest `^29.7.0` for Firestore rules tests in `frontend/jest.config.cjs` and root `jest.config.js`.
- Pytest `8.3.3` for backend and Python integration tests via `requirements.txt` and `conftest.py`.
- Playwright for browser E2E in both `frontend/playwright.config.ts` and `e2e/playwright.config.ts`.

**Assertion Library:**
- Frontend component tests use `@testing-library/react` plus `@testing-library/jest-dom` in `frontend/src/test/setup.ts`.
- Jest Firestore rules suites use `assertSucceeds` and `assertFails` from `@firebase/rules-unit-testing` in `frontend/src/tests/firestore.rules.test.ts` and `tests/firestore/admin.test.js`.
- Python tests use plain `assert`, `pytest.raises`, and FastAPI `TestClient`, as seen in `api/tests/test_rbac.py` and `tests/test_auth_sync.py`.

**Run Commands:**
```bash
cd frontend && npm test                 # Run Vitest in watch/default mode
cd frontend && npm run test:rules       # Run Firestore rules tests against emulator
cd frontend && npm run test:e2e         # Run frontend Playwright suite
pytest                                  # Run Python tests from repo root
pytest --cov=api --cov-report=html      # Generate backend coverage report
cd e2e && npm test                      # Run root Playwright suite
```

## Test File Organization

**Location:**
- Frontend unit and integration tests are mostly colocated with source in `frontend/src/**/*test.ts(x)` such as `frontend/src/api/client.test.ts`, `frontend/src/pages/ExplorerPage.test.tsx`, and `frontend/src/features/kg/components/ProcessDialog.test.tsx`.
- Some frontend tests use dedicated folders like `frontend/src/components/explorer/__tests__/` and `frontend/src/features/kg/components/__tests__/`.
- Firestore rules tests live in two separate locations: TypeScript rules coverage in `frontend/src/tests/firestore.rules.test.ts` and older JavaScript rules suites in `tests/firestore/*.test.js`.
- Python tests live under both `api/tests/` and root `tests/`, with additional ad hoc test modules directly in `api/` such as `api/test_mock_firestore.py` and `api/test_celery_tasks.py`.
- Browser E2E exists in two suites: `frontend/e2e/*.spec.ts` and `e2e/tests/*.spec.ts`.

**Naming:**
- Frontend follows `*.test.tsx` / `*.test.ts` for unit-style files and `*.spec.ts` for Playwright specs.
- Python test files use `test_*.py` naming such as `tests/test_auth_integration.py` and `api/tests/test_rbac.py`.
- Firestore Jest suites use `*.test.js` in `tests/firestore/` and a single `firestore.rules.test.ts` file in `frontend/src/tests/`.

**Structure:**
```text
frontend/src/<feature>.test.ts(x)          # Vitest + Testing Library
frontend/src/tests/firestore.rules.test.ts # Jest + emulator-backed rules tests
frontend/e2e/*.spec.ts                     # Playwright with mocked routes/helpers
api/tests/test_*.py                        # Pytest unit tests for backend modules
tests/test_*.py                            # Pytest integration, router, and regression tests
tests/firestore/*.test.js                  # Older Jest rules tests
e2e/tests/*.spec.ts                        # Separate Playwright suite with page objects
```

## Test Structure

**Suite Organization:**
```typescript
describe('ExplorerPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (useQuery as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockTree,
      isLoading: false,
      error: null,
    });
  });

  describe('Loading State', () => {
    it('shows loading spinner when data is loading', () => {
      renderWithRouter(<ExplorerPage />);
      expect(screen.getByText('Loading...')).toBeInTheDocument();
    });
  });
});
```
Example from `frontend/src/pages/ExplorerPage.test.tsx`.

**Patterns:**
- Frontend Vitest suites use nested `describe` blocks by behavior area and reset shared mocks in `beforeEach`, as in `frontend/src/pages/ExplorerPage.test.tsx` and `frontend/src/stores/useExplorerStore.test.ts`.
- Store tests drive Zustand actions via `useExplorerStore.getState()` and `act(...)`, seen throughout `frontend/src/stores/useExplorerStore.test.ts`.
- Python tests group behaviors in classes such as `TestTokenVerification`, `TestGetCurrentUser`, and `TestRoleBasedAccess` in `tests/test_auth_integration.py`.
- Async backend tests use `@pytest.mark.asyncio` for coroutine helpers and dependencies, as in `api/tests/test_rbac.py` and `tests/test_kg_router_delete.py`.
- Playwright suites organize by feature and tag blocks with `@smoke`, `@crud`, `@critical`, `@navigation`, and `@edge` in `frontend/e2e/explorer.spec.ts`, `frontend/e2e/auth.spec.ts`, and `frontend/e2e/rbac.spec.ts`.

## Mocking

**Framework:**
- `vi.mock`, `vi.spyOn`, fake timers, and Testing Library wrappers for Vitest in `frontend/src/test/setup.ts`, `frontend/src/api/client.test.ts`, and `frontend/src/stores/useExplorerStore.test.ts`.
- `unittest.mock` (`patch`, `MagicMock`, `AsyncMock`) for Python tests in `tests/test_auth_sync.py`, `tests/test_auth_integration.py`, and `tests/test_batch_delete_performance.py`.
- `page.route(...)` and fixture helpers for Playwright in `frontend/e2e/fixtures.ts` and `frontend/e2e/rbac.spec.ts`.

**Patterns:**
```typescript
vi.mock('../api', () => ({
  getExplorerTree: vi.fn(),
  deleteDepartment: vi.fn(),
}));

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual('@tanstack/react-query');
  return {
    ...actual,
    useQuery: vi.fn(),
    useQueryClient: vi.fn(),
  };
});
```
Pattern from `frontend/src/pages/ExplorerPage.test.tsx`.

```python
with patch("api.auth.get_db", return_value=mock_db), patch(
    "api.auth.verify_firebase_token",
    new=AsyncMock(return_value={"uid": "user-123"}),
):
    user = await get_current_user(credentials)
```
Pattern from `tests/test_auth_integration.py`.

```typescript
await page.route('**/api/users*', async (route) => {
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify([...]),
  });
});
```
Pattern from `frontend/e2e/rbac.spec.ts`.

**What to Mock:**
- Mock backend API calls in frontend unit tests rather than letting components hit real fetch endpoints, following `frontend/src/test/setup.ts` and `frontend/src/pages/ExplorerPage.test.tsx`.
- Mock Firebase/Auth/Firestore/Neo4j clients in Python tests, as in `tests/test_auth_sync.py`, `tests/test_auth_integration.py`, and `tests/test_batch_delete_performance.py`.
- Mock route responses in Playwright for deterministic UI flows, especially admin and explorer data in `frontend/e2e/fixtures.ts` and `frontend/e2e/rbac.spec.ts`.

**What NOT to Mock:**
- Do not mock Zustand state access in store tests; those tests call the real store in `frontend/src/stores/useExplorerStore.test.ts`.
- Do not bypass Firestore rules by mocking rule outcomes; emulator-backed tests in `frontend/src/tests/firestore.rules.test.ts` and `tests/firestore/admin.test.js` load actual `firestore.rules`.
- Do not hit real external Firebase services in default Python test runs; `conftest.py` sets `AURA_TEST_MODE=true`, `REDIS_ENABLED=false`, and `TESTING=true` to keep tests hermetic.

## Fixtures and Factories

**Test Data:**
```typescript
const mockTree: FileSystemNode[] = [
  { id: 'dept-1', label: 'Computer Science', type: 'department', children: [], parentId: null },
  { id: 'dept-2', label: 'Mathematics', type: 'department', children: [], parentId: null },
];
```
Pattern from `frontend/src/pages/ExplorerPage.test.tsx`.

```python
def _make_user(uid: str, role: models.UserRole, ... ) -> models.FirestoreUser:
    return models.FirestoreUser(
        uid=uid,
        email=f'{uid}@example.com',
        displayName='Test User',
        role=role,
        ...
    )
```
Pattern from `api/tests/test_rbac.py`.

```javascript
function createUserData(overrides = {}) {
  return {
    uid: 'test-user-123',
    email: 'test@aura.edu',
    role: 'student',
    status: 'active',
    ...overrides,
  };
}
```
Pattern from `tests/firestore/rules-test-utils.js`.

**Location:**
- Shared Vitest setup lives in `frontend/src/test/setup.ts`.
- Playwright fixtures and API mocks live in `frontend/e2e/fixtures.ts`.
- Firestore rules helpers live in `tests/firestore/rules-test-utils.js`.
- Backend tests often define fake classes and helper builders inline, as in `api/tests/test_rbac.py`.

## Coverage

**Requirements:**
- Frontend coverage is configured but not enforced by threshold; `frontend/vite.config.ts` enables V8 coverage with `text`, `json`, and `html` reporters.
- Backend coverage is available through `pytest --cov=api --cov-report=html` from the project guidance in `AGENTS.md`; no minimum threshold is configured in the repo.
- Firestore rules coverage is breadth-oriented rather than percentage-oriented, with a very large suite in `frontend/src/tests/firestore.rules.test.ts` and additional legacy coverage in `tests/firestore/*.test.js`.

**View Coverage:**
```bash
cd frontend && vitest run --coverage
pytest --cov=api --cov-report=html
```

## Test Types

**Unit Tests:**
- Frontend component, hook, API wrapper, and store tests in `frontend/src/**/*.test.ts(x)` use jsdom and Testing Library; examples include `frontend/src/api/client.test.ts`, `frontend/src/stores/useExplorerStore.test.ts`, and `frontend/src/features/kg/hooks/useKGProcessing.test.tsx`.
- Backend helper and dependency tests in `api/tests/test_rbac.py`, `api/test_mock_firestore.py`, and `tests/test_batch_delete_performance.py` isolate individual functions with mocks.

**Integration Tests:**
- Frontend integration-style tests combine multiple real components/providers, such as `frontend/src/integration/WarningDialogFlow.test.tsx` and `frontend/src/integration/GridViewWarning.test.tsx`.
- Backend integration tests use `fastapi.testclient.TestClient` plus dependency overrides in `tests/test_auth_sync.py` and route-level behavior checks in `tests/test_auth_integration.py`.
- Firestore emulator tests in `frontend/src/tests/firestore.rules.test.ts` and `tests/firestore/admin.test.js` validate real rule evaluation against seeded documents.

**E2E Tests:**
- `frontend/e2e/*.spec.ts` is the primary browser suite for auth, RBAC, explorer, KG processing, and health using frontend-local Playwright config and mock-friendly helpers.
- `e2e/tests/*.spec.ts` is a second Playwright suite with page objects in `e2e/page-objects/`, its own package, and optional server startup in `e2e/playwright.config.ts`.

## Common Patterns

**Async Testing:**
```python
@pytest.mark.asyncio
async def test_verify_firebase_token_mock_admin(monkeypatch: pytest.MonkeyPatch) -> None:
    claims = await auth_module.verify_firebase_token('mock-token-admin-001')
    assert claims['role'] == 'admin'
```
Pattern from `api/tests/test_rbac.py`.

```typescript
await waitFor(() => {
  expect(screen.getByText(/already exists/i)).toBeTruthy();
});
```
Pattern from `frontend/src/integration/WarningDialogFlow.test.tsx`.

**Error Testing:**
```typescript
await expect(fetchApi('/test')).rejects.toThrow(DuplicateError);
await expect(fetchApi('/test')).rejects.toThrow('Already exists');
```
Pattern from `frontend/src/api/client.test.ts`.

```python
with pytest.raises(HTTPException) as exc_info:
    await get_current_user(credentials)
assert exc_info.value.status_code == 403
```
Pattern from `tests/test_auth_integration.py`.

## Practical Guidance

- Add new frontend unit tests beside the source file unless the area already uses `__tests__`, matching files like `frontend/src/components/ui/WarningDialog.test.tsx` and `frontend/src/components/explorer/__tests__/ListView.test.tsx`.
- Add new backend tests under `api/tests/` for focused module tests or `tests/` for broader integration/regression coverage, matching `api/tests/test_rbac.py` and `tests/test_auth_sync.py`.
- Use `frontend/src/test/setup.ts` assumptions when writing Vitest tests: global `fetch`, React Query hooks, and `matchMedia` are already mocked.
- Prefer emulator-backed rules tests for Firestore permission changes and keep them in `frontend/src/tests/firestore.rules.test.ts` unless you are specifically extending the older `tests/firestore/*.test.js` harness.
- Prefer tagged Playwright specs in `frontend/e2e/` for UI flows; use the separate root `e2e/` suite only when following its existing page-object structure in `e2e/page-objects/`.

---

*Testing analysis: 2026-03-10*
