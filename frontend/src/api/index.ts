/**
 * ============================================================================
 * FILE: index.ts
 * LOCATION: frontend/src/api/index.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Barrel export module for all API client modules
 *
 * ROLE IN PROJECT:
 *    Centralizes exports for all API interaction modules. Provides single
 *    import point for fetch wrappers, CRUD operations, and error handling
 *
 * KEY COMPONENTS:
 *    - client: Base fetch wrappers, DuplicateError class, request helpers
 *    - explorerApi: Hierarchy CRUD operations (create, read, update, delete)
 *    - audioApi: Audio file upload and processing pipeline
 *    - userApi: User management and Firebase authentication
 *
 * DEPENDENCIES:
 *    - External: None
 *    - Internal: ./client, ./explorerApi, ./audioApi, ./userApi
 *
 * USAGE:
 *    import { fetchApi, DuplicateError, createNode } from '@/api';
 * ============================================================================
 */
export * from './client';
export * from './explorerApi';
export * from './audioApi';
export * from './userApi';
