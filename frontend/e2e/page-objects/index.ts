/**
 * ============================================================================
 * FILE: index.ts
 * LOCATION: frontend/e2e/page-objects/index.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Barrel export for E2E page objects
 *
 * ROLE IN PROJECT:
 *    Single import point for all page objects used in E2E tests.
 *    Consolidates exports for cleaner imports across test files.
 *
 * KEY COMPONENTS:
 *    - ExplorerPage: Page Object Model for Explorer UI interactions
 *    - ApiHelper: API request utilities for direct backend testing
 *
 * DEPENDENCIES:
 *    - External: None
 *    - Internal: ExplorerPage, ApiHelper (page objects)
 *
 * USAGE:
 *    import { ExplorerPage, ApiHelper } from './page-objects';
 * ============================================================================
 */

export { ExplorerPage } from './ExplorerPage';
export { ApiHelper } from './ApiHelper';