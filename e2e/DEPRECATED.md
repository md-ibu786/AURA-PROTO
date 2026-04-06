# DEPRECATED: Root E2E Test Stack

**Status:** Removed as of Phase 9 (Safe Cleanup & Repo Hygiene)
**Active Stack:** `frontend/e2e/`

## Why This Directory Is Deprecated

This root-level `e2e/` directory was removed because it conflicts with the frontend E2E test stack:

| Aspect | Root e2e/ (Removed) | frontend/e2e/ (Active) |
|--------|---------------------|------------------------|
| Port | 5173 | 5174 (via Vite proxy) |
| Playwright | ^1.49.0 | ^1.50.0 |
| Auth | Real Firebase | Mock-first with fallback |
| Fixtures | Basic | Extended with auth helpers |

Maintaining two stacks created confusion and reliability drift (DRIFT-02).

## What Was Migrated (Phase 6)

The following files were migrated to `frontend/e2e/` before this directory was removed:

- `page-objects/ApiHelper.ts` → `frontend/e2e/page-objects/ApiHelper.ts`
- `page-objects/ExplorerPage.ts` → `frontend/e2e/page-objects/ExplorerPage.ts` (rewritten with deterministic waits)
- `tests/api.spec.ts` → `frontend/e2e/api.spec.ts`
- `tests/audio.spec.ts` → `frontend/e2e/audio.spec.ts`

## What Was Removed (Phase 9)

The following files were removed in Phase 9:

- `e2e/README.md` - Obsolete, active stack documented elsewhere
- `e2e/data/hierarchy.json` - No active code paths reference this file
- `e2e/package.json` - Older Playwright version, superseded by frontend/
- `e2e/package-lock.json` - Associated with removed package.json
- `e2e/playwright.config.ts` - Uses wrong port and lacks auth setup
- `e2e/run-tests.sh` - Deprecated, superseded by npm scripts in frontend/
- `e2e/page-objects/*.ts` - Migrated to frontend/e2e/page-objects/
- `e2e/tests/*.spec.ts` - Migrated to frontend/e2e/

## Current State

This directory now contains only this tombstone file. The directory structure is preserved to maintain git history.

## Running Tests

Use the frontend E2E stack:

```bash
cd frontend
npm run test:e2e        # Run all E2E tests
npm run test:e2e:ui     # Run with Playwright UI
npm run test:e2e:headed # Run with visible browser
```

**Do NOT run tests from this directory or any parent directory.**

## Verification

After Phase 9 cleanup:
- `git ls-files "e2e/*"` returns only this file
- `frontend/e2e/` contains the active Playwright test implementation
- `.gitignore` patterns prevent re-commit of generated artifacts
