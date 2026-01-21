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
