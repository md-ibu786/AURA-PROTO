/**
 * ============================================================================
 * FILE: index.ts
 * LOCATION: frontend/src/types/index.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Barrel export for all TypeScript type definitions
 *
 * ROLE IN PROJECT:
 *    Centralizes exports for shared types across the frontend
 *    Simplifies import paths for stores, components, and API clients
 *
 * KEY COMPONENTS:
 *    - FileSystemNode exports
 *    - Firestore user type exports
 *
 * DEPENDENCIES:
 *    - External: None
 *    - Internal: ./FileSystemNode, ./user
 *
 * USAGE:
 *    import { FirestoreUser } from './types';
 * ============================================================================
 */
export * from './FileSystemNode';
export * from './user';
