/**
 * ============================================================================
 * FILE: index.ts
 * LOCATION: frontend/src/stores/index.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Barrel export module for all state management stores
 *
 * ROLE IN PROJECT:
 *    Centralizes store exports for cleaner imports across the application.
 *    Provides single entry point for accessing Zustand stores
 *
 * KEY COMPONENTS:
 *    - useExplorerStore: Zustand store for explorer UI state
 *
 * DEPENDENCIES:
 *    - External: None
 *    - Internal: ./useExplorerStore
 *
 * USAGE:
 *    import { useExplorerStore } from '@/stores';
 * ============================================================================
 */
export { useExplorerStore } from './useExplorerStore';
