# AURA-PROTO E2E Tests

Comprehensive end-to-end testing suite for AURA-PROTO using Playwright.

## Overview

This test suite provides complete coverage of:
- **API Testing**: Direct backend endpoint testing
- **UI Testing**: Frontend user interface testing
- **Audio Processing**: Complete pipeline testing (transcription → AI processing → PDF generation)
- **Integration Testing**: Full user workflows

## Test Structure

```
e2e/
├── tests/
│   ├── api.spec.ts           # API endpoint tests (CRUD, hierarchy, notes)
│   ├── explorer.spec.ts      # UI tests (navigation, CRUD, search, upload)
│   └── audio.spec.ts         # Audio processing pipeline tests
├── page-objects/
│   ├── ApiHelper.ts          # API test helpers
│   ├── ExplorerPage.ts       # Page Object for Explorer UI
│   └── index.ts              # Utilities and fixtures
├── data/                     # Test data files (generated)
├── playwright.config.ts      # Playwright configuration
├── package.json              # Dependencies and scripts
└── README.md                 # This file
```

## Prerequisites

### Backend Requirements
- Python 3.9+ with FastAPI running on port 8001
- Firebase Firestore configured
- Service account key: `serviceAccountKey-auth.json` in project root

### Frontend Requirements
- Node.js 16+
- React app running on port 5173

### Environment Variables
Create `.env` in project root:
```env
DEEPGRAM_API_KEY=your_key
GOOGLE_APPLICATION_CREDENTIALS=./serviceAccountKey-auth.json
LLM_KEY=your_google_ai_key
```

## Installation

### 1. Install Playwright Dependencies
```bash
cd e2e
npm install
npx playwright install --with-deps
```

### 2. Verify Installation
```bash
npx playwright --version
```

## Running Tests

### Run All Tests
```bash
cd e2e
npm test
```

### Run Specific Test Suites
```bash
# API tests only
npm run test:api

# UI tests only
npm run test:ui

# Audio processing tests only
npm run test:audio
```

### Run in Headed Mode (Visible Browser)
```bash
npm run test:headed
```

### Run with Debug Output
```bash
npm run test:debug
```

### Run Specific Test File
```bash
npx playwright test tests/api.spec.ts
```

### Run Specific Test by Name
```bash
npx playwright test -g "should create department"
```

## Test Reports

### View HTML Report
```bash
npm run show-report
```

Reports are generated in `../test-results/html-report/`

### JSON Report
Results available in `../test-results/results.json`

## Test Categories

### 1. API Tests (`api.spec.ts`)

**Coverage:**
- Health check
- Department CRUD operations
- Full hierarchy creation (Dept → Semester → Subject → Module)
- Notes operations
- Explorer tree navigation
- Move operations
- Error handling
- Performance benchmarks

**Test Count:** ~25 tests

### 2. UI Tests (`explorer.spec.ts`)

**Coverage:**
- Page load and layout
- Tree navigation and expansion
- CRUD operations via UI
- Context menu operations
- Search functionality
- View switching (Grid/List)
- Upload dialog interactions
- Breadcrumbs
- Error handling
- End-to-end user flows

**Test Count:** ~30 tests

### 3. Audio Processing Tests (`audio.spec.ts`)

**Coverage:**
- Document upload via API
- Voice pipeline initiation
- Status polling
- UI integration
- Error handling
- Performance benchmarks

**Test Count:** ~10 tests

## Page Object Model

### ApiHelper
Programmatic API access for test setup and verification:
```typescript
const api = new ApiHelper(request);
const deptId = await api.createDepartment('Test', 'TST');
const hierarchy = await api.createTestHierarchy();
```

### ExplorerPage
UI interaction methods:
```typescript
const explorer = new ExplorerPage(page);
await explorer.goto();
await explorer.createDepartment('Test', 'TST');
await explorer.expandNode(deptId);
```

## Test Utilities

### generateUniqueTestData()
Creates unique names/codes to avoid conflicts:
```typescript
const data = generateUniqueTestData('dept');
// Returns: { name: 'dept-123456789-456', code: 'DEP-1234' }
```

### retry()
Retries operations with exponential backoff:
```typescript
await retry(() => api.checkHealth(), { maxRetries: 3, delayMs: 1000 });
```

### createTestPdfBuffer()
Generates valid PDF for upload testing.

### createTestAudioBuffer()
Generates minimal WAV file for audio testing.

## Test Data Fixtures

Predefined test data in `TestData` object:
```typescript
import { TestData } from '../page-objects';

// Valid test data
TestData.departments.valid[0] // { name: 'Computer Science', code: 'CS' }
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: E2E Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd e2e && npm install
          cd ../api && pip install -r requirements.txt

      - name: Install Playwright
        run: cd e2e && npx playwright install --with-deps

      - name: Start backend
        run: cd api && python -m uvicorn main:app --port 8001 &

      - name: Start frontend
        run: cd frontend && npm run dev &

      - name: Wait for services
        run: |
          npx wait-on http://localhost:8001/health
          npx wait-on http://localhost:5173

      - name: Run tests
        run: cd e2e && npm test

      - name: Upload test results
        uses: actions/upload-artifact@v3
        if: always()
        with:
          name: test-results
          path: test-results/
```

## Best Practices

### 1. Test Isolation
Each test should be independent. Use `beforeEach` and `afterEach` for setup/teardown.

### 2. Cleanup
Always clean up test data:
```typescript
test.afterEach(async ({ request }) => {
    if (testDeptId) {
        const api = new ApiHelper(request);
        await api.deleteDepartment(testDeptId);
    }
});
```

### 3. Unique Data
Use `generateUniqueTestData()` to avoid conflicts:
```typescript
const data = generateUniqueTestData('test');
await api.createDepartment(data.name, data.code);
```

### 4. Waiting Strategies
Use proper waiting instead of fixed timeouts:
```typescript
await page.waitForSelector('.tree-node', { state: 'visible' });
await page.waitForLoadState('networkidle');
```

### 5. Assertions
Use specific assertions, not generic checks:
```typescript
// Good
expect(response.ok()).toBe(true);
expect(data.department.id).toBeDefined();

// Avoid
expect(response).toBeTruthy();
```

## Debugging

### 1. Run in Debug Mode
```bash
npm run test:debug
```

### 2. View Trace Files
Traces are saved on first retry. View with:
```bash
npx playwright show-trace path/to/trace.zip
```

### 3. Screenshots
Automatically captured on failure. Check `test-results/screenshots/`.

### 4. Videos
Videos saved for failed tests in `test-results/`.

## Common Issues

### Issue: Tests fail because backend isn't ready
**Solution:** The config already waits for health endpoints. Increase timeout if needed.

### Issue: Port conflicts
**Solution:** Ensure ports 8001 and 5173 are free, or update `playwright.config.ts`.

### Issue: Firestore authentication errors
**Solution:** Verify `serviceAccountKey-auth.json` exists and is valid.

### Issue: Tests timeout during AI processing
**Solution:** AI tests are skipped by default if credentials aren't present. For full testing, add credentials to `.env`.

## Performance Considerations

- Tests run sequentially by default (`fullyParallel: false`) for database consistency
- Use `test.describe.serial()` for related tests that share state
- Clean up data after each test to prevent accumulation
- Use `test.setTimeout()` for long-running operations

## Adding New Tests

### 1. API Test
```typescript
test.describe('My Feature', () => {
    test('should do something', async ({ request }) => {
        const api = new ApiHelper(request);
        // Your test logic
    });
});
```

### 2. UI Test
```typescript
test.describe('My Feature UI', () => {
    test('should interact with UI', async ({ page }) => {
        const explorer = new ExplorerPage(page);
        await explorer.goto();
        // Your test logic
    });
});
```

## Test Coverage Summary

| Component | Tests | Coverage |
|-----------|-------|----------|
| Departments | 5 | CRUD + Cascade |
| Semesters | 3 | CRUD + Hierarchy |
| Subjects | 3 | CRUD + Hierarchy |
| Modules | 3 | CRUD + Hierarchy |
| Notes | 3 | CRUD + Files |
| Explorer Tree | 5 | Navigation + Lazy Loading |
| UI Operations | 10 | CRUD + Context Menu |
| Search | 3 | Filter + Clear |
| Upload | 4 | Document + Voice |
| Audio Pipeline | 5 | Processing + Status |
| Error Handling | 4 | Validation + 404s |
| Performance | 2 | Speed benchmarks |
| **Total** | **51** | **Comprehensive** |

## Maintenance

### Update Tests
When adding new features:
1. Update page objects if UI changes
2. Add new test files if needed
3. Update this README
4. Run full suite before committing

### Review Test Results
After each run:
1. Check HTML report for failures
2. Review trace files for debugging
3. Update tests if UI/API changes

## Support

For issues or questions:
- Check Playwright docs: https://playwright.dev
- Review test logs in `test-results/`
- Use debug mode for detailed output

---

**Last Updated:** 2026-01-03
**Playwright Version:** 1.49.0
**Test Suite Version:** 1.0.0