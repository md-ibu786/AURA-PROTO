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
 *    for 409 conflicts with DuplicateError, and generic error responses.
 *    Ensures consistent API error handling across the application.
 *
 * KEY COMPONENTS:
 *    - fetchApi tests: Validates response parsing and error throwing
 *    - DuplicateError tests: Validates 409 conflict detection
 *    - Mock setup: vi.spyOn for global fetch mocking
 *
 * DEPENDENCIES:
 *    - External: vitest (describe, it, expect, vi, beforeEach)
 *    - Internal: ./client.ts (fetchApi, DuplicateError)
 *
 * USAGE:
 *    npm test -- src/api/client.test.ts
 * ============================================================================
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchApi, DuplicateError } from './client';

describe('fetchApi', () => {
    beforeEach(() => {
        vi.clearAllMocks();
        vi.restoreAllMocks();
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
});
