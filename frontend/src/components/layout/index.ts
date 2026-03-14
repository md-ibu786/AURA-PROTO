/**
 * ============================================================================
 * FILE: index.ts
 * LOCATION: frontend/src/components/layout/index.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Barrel export module for layout components - re-exports Sidebar and Header
 *
 * ROLE IN PROJECT:
 *    Central entry point for layout components used by pages and app structure.
 *    Enables clean imports like `import { Sidebar, Header } from './layout'`.
 *
 * KEY COMPONENTS:
 *    - Sidebar: Left panel with collapsible tree navigation
 *    - Header: Top bar with breadcrumbs, search, and action controls
 *
 * DEPENDENCIES:
 *    - External: None
 *    - Internal: ./Sidebar.tsx, ./Header.tsx
 *
 * USAGE:
 *    import { Sidebar, Header } from '../components/layout';
 * ============================================================================
 */

export { Sidebar } from './Sidebar';
export { Header } from './Header';
