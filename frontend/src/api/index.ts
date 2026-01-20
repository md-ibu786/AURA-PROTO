/**
 * API Index
 * ========================
 *
 * Barrel export module for all API functions.
 * Re-exports client, explorerApi, and audioApi modules.
 *
 * @see: client.ts - Base fetch wrappers and error classes
 * @see: explorerApi.ts - Hierarchy CRUD operations
 * @see: audioApi.ts - Audio processing pipeline
 */
export * from './client';
export * from './explorerApi';
export * from './audioApi';
