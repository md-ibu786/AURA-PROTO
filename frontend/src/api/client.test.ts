/**
 * ============================================================================
 * FILE: client.test.ts
 * LOCATION: frontend/src/api/client.test.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Unit tests for the API client fetch wrapper and error handling
 *
 * ROLE IN PROJECT:
 *    Validates the fetchApi function behavior including error handling
 *    for 409 conflicts (DuplicateError), authentication failures (AuthError),
 *    and generic error responses. Ensures consistent API error handling
 *    across the application.
 *
 * KEY COMPONENTS:
 *    - fetchApi tests: Validates response parsing and error throwing
 *    - DuplicateError tests: Validates 409 conflict detection
 *    - AuthError tests: Validates auth failure propagation
 *    - Mock setup: vi.spyOn for global fetch and useAuthStore mocking
 *
 * DEPENDENCIES:
 *    - External: vitest (describe, it, expect, vi, beforeEach, afterEach)
 *    - Internal: ./client.ts (fetchApi, DuplicateError, AuthError)
 *    - Internal: ./errors.ts (AuthError exported from client.ts)
 *
 * USAGE:
 *    npm test -- src/api/client.test.ts
 * ============================================================================
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { fetchApi, DuplicateError, AuthError } from './client';
import { useAuthStore } from '../stores/useAuthStore';

// Mock useAuthStore for auth-related tests
vi.mock('../stores/useAuthStore', () => ({
    useAuthStore: {
        getState: vi.fn(() => ({
            getIdToken: vi.fn().mockResolvedValue('test-token'),
        })),
    },
}));

describe('fetchApi', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.restoreAllMocks();
    });

    afterEach(() => {
        vi.clearAllMocks();
    });

    it('should throw DuplicateError on 409 with code', async () => {
        const mockResponse = {
            ok: false,
            status: 409,
            json: vi.fn().mockResolvedValue({
                detail: {
                    code: 'DUPLICATE_NAME',
                    message: 'Already exists'
                }
            })
        };

        vi.spyOn(global, 'fetch').mockResolvedValue(mockResponse as unknown as Response);

        await expect(fetchApi('/test')).rejects.toThrow(DuplicateError);
        await expect(fetchApi('/test')).rejects.toThrow('Already exists');

        vi.restoreAllMocks();
    });

    it('should throw generic Error on 409 without code', async () => {
        const mockResponse = {
            ok: false,
            status: 409,
            json: vi.fn().mockResolvedValue({
                detail: 'Conflict'
            })
        };

        vi.spyOn(global, 'fetch').mockResolvedValue(mockResponse as unknown as Response);

        await expect(fetchApi('/test')).rejects.toThrow('Conflict');
        await expect(fetchApi('/test')).rejects.not.toThrow(DuplicateError);

        vi.restoreAllMocks();
    });

    it('should successfully fetch data with auth token', async () => {
        const mockData = { id: 1, name: 'test' };
        const mockResponse = {
            ok: true,
            json: vi.fn().mockResolvedValue(mockData),
        };

        vi.spyOn(global, 'fetch').mockResolvedValue(mockResponse as unknown as Response);

        const result = await fetchApi('/test');
        expect(result).toEqual(mockData);

        vi.restoreAllMocks();
    });
});

describe('AuthError', () => {
    it('should include cause when provided', () => {
        const cause = new Error('Original error');
        const authError = new AuthError('Token failed', cause);

        expect(authError.cause).toBe(cause);
        expect(authError.message).toBe('Token failed');
        expect(authError.name).toBe('AuthError');
    });

    it('should work without cause', () => {
        const authError = new AuthError('Auth failed');

        expect(authError.cause).toBeUndefined();
        expect(authError.message).toBe('Auth failed');
        expect(authError.name).toBe('AuthError');
    });
});

describe('getAuthHeader auth failure handling', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.restoreAllMocks();
    });

    it('should throw AuthError when token retrieval fails', async () => {
        // Mock getIdToken to throw
        const mockGetIdToken = vi.fn().mockRejectedValue(new Error('Token service unavailable'));
        vi.spyOn(useAuthStore, 'getState').mockReturnValue({
            getIdToken: mockGetIdToken,
        } as unknown as ReturnType<typeof useAuthStore.getState>);

        await expect(fetchApi('/protected-endpoint')).rejects.toThrow(AuthError);
    });

    it('should throw AuthError when 401 retry token refresh fails', async () => {
        // First call returns token, 401 happens, then token refresh fails
        const mockGetIdToken = vi.fn()
            .mockResolvedValueOnce('initial-token')
            .mockRejectedValueOnce(new Error('Refresh failed'));

        vi.spyOn(useAuthStore, 'getState').mockReturnValue({
            getIdToken: mockGetIdToken,
        } as unknown as ReturnType<typeof useAuthStore.getState>);

        const mockResponse401 = {
            ok: false,
            status: 401,
            json: vi.fn().mockResolvedValue({ detail: 'Unauthorized' }),
        };

        vi.spyOn(global, 'fetch').mockResolvedValueOnce(mockResponse401 as unknown as Response);

        await expect(fetchApi('/protected-endpoint')).rejects.toThrow(AuthError);
    });
});
