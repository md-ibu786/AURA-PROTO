# Phase 6: Verification Recovery - Research

**Researched:** 2026-04-06
**Phase Goal:** Maintainers can trust the active verification workflow to reflect current product behavior and fail fast on audited breakage.

---

## Executive Summary

Phase 6 addresses five requirements (TEST-01, TEST-02, TEST-03, TEST-04, DRIFT-02) focused on establishing a trustworthy, deterministic verification baseline. The codebase has **duplicate E2E test stacks** (`frontend/e2e/` and `e2e/`), **non-deterministic waits** (fixed `waitForTimeout` calls), and **configuration drift** between the two Playwright setups. This research identifies the specific issues and recommends a consolidation strategy.

---

## Current State Analysis

### 1. Duplicate E2E Test Stacks (DRIFT-02)

**Finding:** Two separate Playwright E2E test directories exist with overlapping but inconsistent coverage.

| Aspect | `frontend/e2e/` | `e2e/` (root) |
|--------|-----------------|---------------|
| Package | Part of frontend | Standalone package `aura-proto-e2e` |
| Config | `frontend/playwright.config.ts` | `e2e/playwright.config.ts` |
| Base URL | `http://127.0.0.1:5174` | `http://127.0.0.1:5173` |
| Auth Setup | `auth.setup.ts` with storage state | None |
| Fixtures | `fixtures.ts` with mock helpers | `page-objects/` with Page Object Model |
| Mock Auth | `VITE_USE_MOCK_AUTH=true` by default | No mock auth support |
| Web Server | Frontend only | Both backend (8001) and frontend (5173) |
| Tests | auth, rbac, explorer, kg-processing, health, settings | api, explorer, audio |

**Conflicts:**
- Different ports: `5174` vs `5173` (Vite default)
- Different auth approaches: mock-first vs real Firebase
- Different patterns: Fixtures vs Page Object Model
- Separate `package.json` files with different Playwright versions (`^1.50.0` vs `^1.49.0`)

### 2. Auth and RBAC Suite Issues (TEST-01)

**Finding:** The `frontend/e2e/` auth and RBAC tests work with mock auth but have wiring issues:

1. **auth.setup.ts references:** The `playwright.config.ts` defines an `auth-setup` project matching `/auth\.setup\.ts/`, but tests in `auth.spec.ts` and `rbac.spec.ts` import from `./fixtures` which has its own `loginAsRole()` function. The stored auth state files (`admin.json`, `staff.json`, `student.json`) are written but **not consumed** by the test projects.

2. **Broken fixture wiring:** Tests use `import { test, expect } from './fixtures'` but the base `@playwright/test` exports are re-exported from fixtures, creating potential confusion. The `auth.setup.ts` uses `import { test as setup } from '@playwright/test'` directly, not the extended fixtures.

3. **Dependency chain unclear:** The `auth-setup` project should run before browser projects, but `depends: ['auth-setup']` is not specified in chromium/firefox/webkit projects.

### 3. Non-Deterministic Waits (TEST-02)

**Finding:** Both test stacks use fixed `waitForTimeout()` calls instead of deterministic waits.

**In `frontend/e2e/fixtures.ts`:**
```typescript
// Lines 155-159: loginAsRole uses fixed wait after navigation
await waitForAuth(page);
await page.waitForLoadState('networkidle');

// Line 719: waitForLoading has a hardcoded 10s timeout
await expect(spinner.first()).not.toBeVisible({ timeout: 10000 });
```

**In `e2e/page-objects/ExplorerPage.ts`:**
```typescript
// Line 127: waitForExplorerLoad - arbitrary 500ms sleep
await this.page.waitForTimeout(500); // Extra time for async tree loading

// Lines 137-138, 153-154, 168-169, 174-175, 197-198, etc.
await this.page.waitForTimeout(300); // Allow for rendering
await this.page.waitForTimeout(500); // After CRUD operations
```

**In `e2e/tests/explorer.spec.ts`:**
```typescript
// Line 169: Fixed 1000ms wait after createDepartment
await explorerPage.waitForTimeout(1000);
```

**Impact:** Tests are flaky on slower machines or CI, pass tautologically when the wait is longer than needed, and hide real performance issues.

### 4. Timeout and Fail-Fast Configuration (TEST-03)

**Finding:** Current timeout configurations vary and don't surface failures early.

| Config | `frontend/playwright.config.ts` | `e2e/playwright.config.ts` |
|--------|--------------------------------|---------------------------|
| Global timeout | 30s | 60s |
| Expect timeout | 5s | 15s |
| Action timeout | Not set | 10s |
| Navigation timeout | Not set | 30s |
| maxFailures | 10 (CI only) | Not set |

**Issues:**
1. No `--fail-fast` or low `maxFailures` for quick feedback during development
2. Inconsistent timeouts make debugging difficult
3. No test hang detection (no global test timeout guardian)

### 5. Active Verification Stack Source of Truth (TEST-04)

**Finding:** No single canonical verification workflow exists.

**Documentation conflicts:**
- `AGENTS.md` describes `npm run test:e2e` in `frontend/`
- `AGENTS.md` also describes `npm test` in `e2e/`
- Root `conftest.py` suggests pytest for backend but doesn't integrate with E2E

**npm scripts overlap:**
- `frontend/package.json`: `"test:e2e": "playwright test"`
- `e2e/package.json`: `"test": "npx playwright test"`

---

## Recommended Approach

### Strategy: Consolidate to `frontend/e2e/` as Canonical Stack

**Rationale:**
1. `frontend/e2e/` has richer auth/RBAC coverage needed for the product
2. Mock auth support enables hermetic CI testing
3. Fixtures pattern can incorporate Page Object Model from `e2e/`
4. Frontend-first testing aligns with user-facing verification goals

### Implementation Recommendations

#### R1. Merge Page Objects into Fixtures (TEST-01, DRIFT-02)

Move `e2e/page-objects/ExplorerPage.ts` and `e2e/page-objects/ApiHelper.ts` into `frontend/e2e/` and update imports. Deprecate root `e2e/` directory.

**Files to migrate:**
- `e2e/page-objects/ExplorerPage.ts` → `frontend/e2e/page-objects/ExplorerPage.ts`
- `e2e/page-objects/ApiHelper.ts` → `frontend/e2e/page-objects/ApiHelper.ts`
- `e2e/tests/explorer.spec.ts` patterns → merge into `frontend/e2e/explorer.spec.ts`
- `e2e/tests/api.spec.ts` → `frontend/e2e/api.spec.ts`
- `e2e/tests/audio.spec.ts` → `frontend/e2e/audio.spec.ts`

#### R2. Fix Auth Setup Wiring (TEST-01)

Update `frontend/playwright.config.ts`:
```typescript
projects: [
  {
    name: 'auth-setup',
    testMatch: /auth\.setup\.ts/,
  },
  {
    name: 'chromium',
    use: { 
      ...devices['Desktop Chrome'],
      storageState: './playwright-report/.auth/admin.json',
    },
    dependencies: ['auth-setup'],
  },
  // ... firefox, webkit similarly
]
```

#### R3. Replace Fixed Waits with Deterministic Waits (TEST-02)

**Pattern to use:**
```typescript
// BEFORE: await this.page.waitForTimeout(500);
// AFTER:
await expect(this.treeContainer).toBeVisible();
await this.page.waitForLoadState('networkidle');

// For CRUD operations, wait for the specific element to appear:
await expect(this.page.getByText(deptName)).toBeVisible({ timeout: 10000 });
```

**Assertions should be meaningful:**
```typescript
// BEFORE: tautological check
const exists = await explorerPage.verifyNodeExists(deptName);
expect(exists).toBe(true);

// AFTER: direct assertion
await expect(explorerPage.page.getByText(deptName)).toBeVisible();
```

#### R4. Standardize Timeouts and Add Fail-Fast (TEST-03)

Unified `playwright.config.ts`:
```typescript
export default defineConfig({
  timeout: 30_000,           // 30s per test
  expect: { timeout: 5_000 }, // 5s for assertions
  maxFailures: process.env.CI ? 5 : 3,  // Fail fast
  
  use: {
    actionTimeout: 10_000,
    navigationTimeout: 15_000,
  },
});
```

Add hang detection script in `package.json`:
```json
"test:e2e": "playwright test --timeout=30000",
"test:e2e:ci": "playwright test --timeout=30000 --max-failures=5"
```

#### R5. Establish Single Source of Truth (TEST-04)

1. **Archive** `e2e/` directory (rename to `e2e.archived/` or delete after migration)
2. **Update AGENTS.md** to document only `frontend/e2e/` as the canonical E2E location
3. **Update CI** (if any) to run only `npm run test:e2e` from `frontend/`
4. **Standardize port** to `5173` (Vite default) everywhere

---

## Validation Architecture

### Verification Commands

| Layer | Command | Timeout | Fail Condition |
|-------|---------|---------|----------------|
| Frontend Unit | `npm test` (vitest) | 60s | Any test failure |
| Frontend E2E | `npm run test:e2e` | 30s/test | Any test failure, >3 failures total |
| Backend Unit | `pytest` | 60s | Any test failure |
| Type Check | `npm run build` | 120s | tsc errors |

### Test Hygiene Gates

Before accepting a phase as complete:
1. All E2E tests pass on Chromium (primary)
2. No `waitForTimeout()` calls with fixed values >100ms without justification comment
3. All assertions use `expect()` with specific matchers (no `toBe(true)` on existence checks)
4. Auth setup project runs before browser projects

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Migration breaks working tests | Medium | High | Run both stacks in parallel during migration, diff coverage |
| Mock auth diverges from real auth | Low | Medium | Keep real auth tests for smoke testing |
| Page Object refactor introduces bugs | Low | Medium | Preserve existing selectors, add new ones |
| Fixed waits hide real app slowness | Medium | High | Remove waits incrementally, monitor for new flakiness |

---

## Files Involved

### To Modify
- `frontend/playwright.config.ts` — Fix auth setup wiring, standardize timeouts
- `frontend/e2e/fixtures.ts` — Remove fixed waits, improve deterministic helpers
- `frontend/e2e/auth.spec.ts` — Verify auth setup integration works
- `frontend/e2e/rbac.spec.ts` — Verify RBAC flows use stored auth state
- `frontend/e2e/explorer.spec.ts` — Merge patterns from root e2e, remove fixed waits

### To Create
- `frontend/e2e/page-objects/ExplorerPage.ts` — Migrated from `e2e/`
- `frontend/e2e/page-objects/ApiHelper.ts` — Migrated from `e2e/`
- `frontend/e2e/api.spec.ts` — Migrated from `e2e/tests/`
- `frontend/e2e/audio.spec.ts` — Migrated from `e2e/tests/`

### To Archive/Delete
- `e2e/` — Entire directory after successful migration

### To Update (Documentation)
- `AGENTS.md` — Single source of truth for test commands

---

## Requirement Mapping

| Requirement | Research Finding | Recommended Action |
|-------------|------------------|-------------------|
| TEST-01 | Auth setup wiring broken, stored state not consumed | R2: Fix auth setup project dependencies |
| TEST-02 | 15+ instances of `waitForTimeout()` with fixed values | R3: Replace with `expect()` assertions |
| TEST-03 | No fail-fast, inconsistent timeouts | R4: Standardize config, add maxFailures |
| TEST-04 | Two conflicting E2E stacks | R5: Archive root e2e/, document frontend/e2e/ |
| DRIFT-02 | Duplicate configs, different ports/patterns | R1: Consolidate to frontend/e2e/ |

---

*Research completed: 2026-04-06*
