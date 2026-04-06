# ⚠️ DEPRECATED: Root E2E Test Stack

**Status:** Deprecated as of Phase 6 (Verification Recovery)
**Active Stack:** `frontend/e2e/`

## Why This Directory Is Deprecated

This root-level `e2e/` directory conflicts with the frontend E2E test stack:

| Aspect | Root e2e/ | frontend/e2e/ (Active) |
|--------|-----------|------------------------|
| Port | 5173 | 5174 (via Vite proxy) |
| Playwright | ^1.49.0 | ^1.50.0 |
| Auth | Real Firebase | Mock-first with fallback |
| Fixtures | Basic | Extended with auth helpers |

Maintaining two stacks creates confusion and reliability drift (DRIFT-02).

## What Was Migrated

The following files were migrated to `frontend/e2e/`:

- `page-objects/ApiHelper.ts` → `frontend/e2e/page-objects/ApiHelper.ts`
- `page-objects/ExplorerPage.ts` → `frontend/e2e/page-objects/ExplorerPage.ts` (rewritten with deterministic waits)
- `tests/api.spec.ts` → `frontend/e2e/api.spec.ts`
- `tests/audio.spec.ts` → `frontend/e2e/audio.spec.ts`

## What Was NOT Migrated

- `tests/explorer.spec.ts` - Duplicate of `frontend/e2e/explorer.spec.ts`
- `playwright.config.ts` - Uses wrong port and lacks auth setup
- `package.json` - Older Playwright version

## Safe to Delete?

This directory can be deleted once the team confirms:
1. All migrated tests pass in `frontend/e2e/`
2. No CI pipelines reference this directory
3. No team members are actively using this directory

Until then, leave it in place to avoid breaking unknown consumers.

## Running Tests

Use the frontend E2E stack:

```bash
cd frontend
npm run test:e2e        # Run all E2E tests
npm run test:e2e:ui     # Run with Playwright UI
npm run test:e2e:headed # Run with visible browser
```

Do NOT run tests from this directory.