import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fetchApi, DuplicateError } from './client';

global.fetch = vi.fn();

describe('fetchApi', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should throw DuplicateError on 409 with code', async () => {
        (fetch as any).mockResolvedValue({
            ok: false,
            status: 409,
            json: async () => ({
                detail: {
                    code: 'DUPLICATE_NAME',
                    message: 'Already exists'
                }
            })
        });

        await expect(fetchApi('/test')).rejects.toThrow(DuplicateError);
        await expect(fetchApi('/test')).rejects.toThrow('Already exists');
    });

    it('should throw generic Error on 409 without code', async () => {
        (fetch as any).mockResolvedValue({
            ok: false,
            status: 409,
            json: async () => ({
                detail: 'Conflict'
            })
        });

        await expect(fetchApi('/test')).rejects.toThrow('Conflict');
        await expect(fetchApi('/test')).rejects.not.toThrow(DuplicateError);
    });
});
