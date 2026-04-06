/**
 * ============================================================================
 * FILE: errors.ts
 * LOCATION: frontend/src/api/errors.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Centralized error class definitions for API client error handling.
 *    Provides typed errors that can be caught and handled specifically.
 *
 * ROLE IN PROJECT:
 *    Foundation layer for explicit error handling across all API calls.
 *    Enables callers to distinguish between error types (auth, duplicate, network)
 *    and respond appropriately.
 *
 * KEY COMPONENTS:
 *    - DuplicateError: Thrown for 409 conflicts with DUPLICATE_NAME code
 *    - AuthError: Thrown when authentication operations fail (token retrieval, refresh)
 *    - NetworkError: Thrown for network-level failures
 *
 * DEPENDENCIES:
 *    - External: None
 *    - Internal: None
 *
 * USAGE:
 *    import { DuplicateError, AuthError, NetworkError } from './errors';
 *    try {
 *        await fetchApi(...)
 *    } catch (e) {
 *        if (e instanceof AuthError) { ... }
 *        else if (e instanceof DuplicateError) { ... }
 *    }
 * ============================================================================
 */

/**
 * Error thrown when a 409 response indicates duplicate resource name.
 * Provides the error code for programmatic handling.
 */
export class DuplicateError extends Error {
    code: string;

    constructor(message: string, code: string) {
        super(message);
        this.name = 'DuplicateError';
        this.code = code;
    }
}

/**
 * Error thrown when authentication operations fail.
 * Includes token retrieval failures and refresh failures.
 * The optional cause property preserves the original error for debugging.
 */
export class AuthError extends Error {
    cause?: unknown;

    constructor(message: string, cause?: unknown) {
        super(message);
        this.name = 'AuthError';
        this.cause = cause;
    }
}

/**
 * Error thrown for network-level failures.
 * Used when requests fail before reaching the server or when
 * the server is unreachable.
 */
export class NetworkError extends Error {
    constructor(message: string) {
        super(message);
        this.name = 'NetworkError';
    }
}