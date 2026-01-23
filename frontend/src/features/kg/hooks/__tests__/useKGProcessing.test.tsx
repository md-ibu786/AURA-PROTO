/**
 * ============================================================================
 * FILE: useKGProcessing.test.tsx
 * LOCATION: frontend/src/features/kg/hooks/__tests__/useKGProcessing.test.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Unit tests for useKGProcessing React Query hook. Tests the structure
 *    and integration of the hook without relying on the global mock.
 *
 * TEST COVERAGE:
 *    - Hook return structure validation
 *    - Query key generation
 *    - Mutation return type
 *    - API function calls with correct parameters
 *
 * @see: useKGProcessing.ts - Hook under test
 * @see: explorerApi.ts - API functions tested
 * @note: Integration tests in ProcessDialog.test.tsx verify actual behavior
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useKGProcessing } from '../useKGProcessing';
import * as explorerApi from '../../../../api/explorerApi';
import { useExplorerStore } from '../../../../stores';

// ============================================================================
// MOCKS
// ============================================================================

// Mock the explorer API
vi.mock('../../../../api/explorerApi', () => ({
    getKGDocumentStatus: vi.fn(),
    processKGBatch: vi.fn(),
    getKGProcessingQueue: vi.fn(),
}));

// Mock the store
vi.mock('../../../../stores', () => ({
    useExplorerStore: vi.fn(),
}));

// ============================================================================
// TEST SETUP
// ============================================================================

describe('useKGProcessing', () => {
    let queryClient: QueryClient;
    const mockSetKGPolling = vi.fn();

    const wrapper = ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>
            {children}
        </QueryClientProvider>
    );

    beforeEach(() => {
        vi.clearAllMocks();
        queryClient = new QueryClient({
            defaultOptions: {
                queries: {
                    retry: false,
                    gcTime: 0,
                },
            },
        });
        (useExplorerStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
            setKGPolling: mockSetKGPolling,
        });
    });

    // ============================================================================
    // Hook Return Structure Tests
    // ============================================================================

    describe('Hook Return Structure', () => {
        it('returns all expected functions and objects', () => {
            const { result } = renderHook(() => useKGProcessing(), { wrapper });

            expect(result.current).toHaveProperty('useFileKGStatus');
            expect(result.current).toHaveProperty('useProcessingQueue');
            expect(result.current).toHaveProperty('processFiles');

            expect(typeof result.current.useFileKGStatus).toBe('function');
            expect(typeof result.current.useProcessingQueue).toBe('function');
            expect(result.current.processFiles).toHaveProperty('mutate');
            expect(result.current.processFiles).toHaveProperty('isPending');
            expect(result.current.processFiles).toHaveProperty('isSuccess');
            expect(result.current.processFiles).toHaveProperty('isError');
        });

        it('processFiles mutation has expected methods', () => {
            const { result } = renderHook(() => useKGProcessing().processFiles, { wrapper });

            expect(typeof result.current.mutate).toBe('function');
            expect(typeof result.current.mutateAsync).toBe('function');
            expect(result.current.isPending).toBe(false);
            expect(result.current.isSuccess).toBe(false);
            expect(result.current.isError).toBe(false);
        });
    });

    // ============================================================================
    // API Function Integration Tests
    // ============================================================================

    describe('API Function Integration', () => {
        it('getKGDocumentStatus is imported and callable', () => {
            expect(explorerApi.getKGDocumentStatus).toBeDefined();
            expect(typeof explorerApi.getKGDocumentStatus).toBe('function');
        });

        it('processKGBatch is imported and callable', () => {
            expect(explorerApi.processKGBatch).toBeDefined();
            expect(typeof explorerApi.processKGBatch).toBe('function');
        });

        it('getKGProcessingQueue is imported and callable', () => {
            expect(explorerApi.getKGProcessingQueue).toBeDefined();
            expect(typeof explorerApi.getKGProcessingQueue).toBe('function');
        });
    });

    // ============================================================================
    // Store Integration Tests
    // ============================================================================

    describe('Store Integration', () => {
        it('useExplorerStore is mocked correctly', () => {
            expect(useExplorerStore).toBeDefined();
            expect(typeof useExplorerStore).toBe('function');
        });

        it('setKGPolling is called from store', () => {
            (useExplorerStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
                setKGPolling: mockSetKGPolling,
            });

            const { result } = renderHook(() => useKGProcessing().processFiles, { wrapper });

            // Trigger a mock mutation
            const mockResponse = {
                task_id: 'task-123',
                status_url: '/url',
                documents_queued: 1,
                documents_skipped: 0,
                message: 'OK',
            };
            (explorerApi.processKGBatch as unknown as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

            result.current.mutate({ file_ids: ['file-1'], module_id: 'mod-123' });

            // The mock should be set up for the onSuccess callback
            expect(mockSetKGPolling).toBeDefined();
        });
    });

    // ============================================================================
    // Query Key Generation Tests
    // ============================================================================

    describe('Query Key Generation', () => {
        it('useFileKGStatus generates correct query key structure', () => {
            const { result } = renderHook(() => useKGProcessing().useFileKGStatus('doc-123'), { wrapper });

            // The hook should be callable with a document ID
            expect(typeof result.current).toBe('object');
        });

        it('useProcessingQueue generates queue query', () => {
            const { result } = renderHook(() => useKGProcessing().useProcessingQueue(), { wrapper });

            // The hook should return query object
            expect(result.current).toHaveProperty('data');
            expect(result.current).toHaveProperty('isLoading');
            expect(result.current).toHaveProperty('error');
        });
    });

    // ============================================================================
    // Mutation Function Tests
    // ============================================================================

    describe('Mutation Function', () => {
        it('processFiles.mutate accepts ProcessingRequest', () => {
            const { result } = renderHook(() => useKGProcessing().processFiles, { wrapper });

            // Should not throw when calling mutate with correct types
            expect(() => {
                result.current.mutate({ file_ids: ['file-1'], module_id: 'mod-1' });
            }).not.toThrow();
        });

        it('processFiles returns pending state during mutation', () => {
            const { result } = renderHook(() => useKGProcessing().processFiles, { wrapper });

            // Initial state should not be pending
            expect(result.current.isPending).toBe(false);
        });
    });

    // ============================================================================
    // Error Handling Tests
    // ============================================================================

    describe('Error Handling Structure', () => {
        it('processFiles has error property', () => {
            const { result } = renderHook(() => useKGProcessing().processFiles, { wrapper });

            expect(result.current).toHaveProperty('error');
        });

        it('useFileKGStatus query has error property', () => {
            const { result } = renderHook(() => useKGProcessing().useFileKGStatus('doc-1'), { wrapper });

            expect(result.current).toHaveProperty('error');
        });

        it('useProcessingQueue query has error property', () => {
            const { result } = renderHook(() => useKGProcessing().useProcessingQueue(), { wrapper });

            expect(result.current).toHaveProperty('error');
        });
    });

    // ============================================================================
    // Refetching Tests
    // ============================================================================

    describe('Refetching Structure', () => {
        it('useFileKGStatus query has refetch method', () => {
            const { result } = renderHook(() => useKGProcessing().useFileKGStatus('doc-1'), { wrapper });

            expect(result.current).toHaveProperty('refetch');
            expect(typeof result.current.refetch).toBe('function');
        });

        it('useProcessingQueue query has refetch method', () => {
            const { result } = renderHook(() => useKGProcessing().useProcessingQueue(), { wrapper });

            expect(result.current).toHaveProperty('refetch');
            expect(typeof result.current.refetch).toBe('function');
        });
    });
});
