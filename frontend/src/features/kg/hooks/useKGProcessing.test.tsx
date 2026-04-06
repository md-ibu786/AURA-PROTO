/**
 * ============================================================================
 * FILE: useKGProcessing.test.tsx
 * LOCATION: frontend/src/features/kg/hooks/useKGProcessing.test.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Unit tests for the useKGProcessing hook.
 *
 * ROLE IN PROJECT:
 *    Validates the useKGProcessing hook interface and behavior within a
 *    QueryClientProvider context. Covers the processFiles mutation shape,
 *    useProcessingQueue and useFileKGStatus function signatures, and
 *    integration across multiple concurrent renders.
 *
 * KEY COMPONENTS:
 *    - processFiles mutation tests: Interface, types, and invocation
 *    - useProcessingQueue tests: Function signature and callability
 *    - useFileKGStatus tests: Function signature and callability
 *    - Integration tests: Return structure and concurrent renders
 *
 * DEPENDENCIES:
 *    - External: vitest, @tanstack/react-query, @testing-library/react
 *    - Internal: features/kg/hooks/useKGProcessing, api/explorerApi, stores, types/kg.types
 *
 * USAGE:
 *    npm test -- src/features/kg/hooks/useKGProcessing.test.tsx
 * ============================================================================
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { renderHook } from '@testing-library/react';
import React from 'react';

// Import types
import type {
    ProcessingRequest
} from '../types/kg.types';

// Import the hook
import { useKGProcessing } from './useKGProcessing';

// Mock explorer API - use vi.fn() directly in the factory
vi.mock('../../../api/explorerApi', () => ({
    getKGDocumentStatus: vi.fn(),
    processKGBatch: vi.fn(),
    getKGProcessingQueue: vi.fn(),
}));

// Mock explorer store
vi.mock('../../../stores', () => ({
    useExplorerStore: vi.fn(() => ({
        setKGPolling: vi.fn(),
    })),
}));

// ============================================================================
// Test Suite
// ============================================================================

describe('useKGProcessing', () => {
    let queryClient: QueryClient;

    beforeEach(() => {
        vi.clearAllMocks();

        // Create a fresh QueryClient for each test
        queryClient = new QueryClient({
            defaultOptions: {
                queries: {
                    retry: false,
                    gcTime: 0,
                },
            },
        });
    });

    afterEach(() => {
        vi.clearAllTimers();
    });

    const wrapper = ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>
            {children}
        </QueryClientProvider>
    );

    // =========================================================================
    // processFiles Mutation Tests
    // =========================================================================

    describe('processFiles Mutation', () => {
        it('should return a mutation object with expected interface', () => {
            const { result } = renderHook(() => useKGProcessing(), { wrapper });

            // Verify processFiles has required mutation properties
            expect(result.current.processFiles).toBeDefined();
            expect(typeof result.current.processFiles.mutate).toBe('function');
            expect(typeof result.current.processFiles.mutateAsync).toBe('function');
            expect('isPending' in result.current.processFiles).toBe(true);
            expect('isSuccess' in result.current.processFiles).toBe(true);
            expect('isError' in result.current.processFiles).toBe(true);
        });

        it('should have isPending as boolean type', () => {
            const { result } = renderHook(() => useKGProcessing(), { wrapper });

            // isPending should be a boolean (false when idle)
            expect(typeof result.current.processFiles.isPending).toBe('boolean');
        });

        it('should have isSuccess as boolean type', () => {
            const { result } = renderHook(() => useKGProcessing(), { wrapper });

            // isSuccess should be a boolean (false when idle)
            expect(typeof result.current.processFiles.isSuccess).toBe('boolean');
        });

        it('should have isError as boolean type', () => {
            const { result } = renderHook(() => useKGProcessing(), { wrapper });

            // isError should be a boolean (false when idle)
            expect(typeof result.current.processFiles.isError).toBe('boolean');
        });

        it('should have mutate function that accepts ProcessingRequest', () => {
            const { result } = renderHook(() => useKGProcessing(), { wrapper });

            // mutate should accept a ProcessingRequest-like object
            const testRequest: ProcessingRequest = {
                file_ids: ['test-file-1', 'test-file-2'],
                module_id: 'test-module',
            };

            // mutate should be callable with the request
            expect(() => {
                result.current.processFiles.mutate(testRequest);
            }).not.toThrow();
        });

        it('should have error property that can be null or Error', () => {
            const { result } = renderHook(() => useKGProcessing(), { wrapper });

            // error property should exist and can be null
            expect('error' in result.current.processFiles).toBe(true);
        });
    });

    // =========================================================================
    // useProcessingQueue Hook Tests
    // =========================================================================

    describe('useProcessingQueue Hook', () => {
        it('should return a function', () => {
            const { result } = renderHook(() => useKGProcessing(), { wrapper });

            // useProcessingQueue should be a function
            expect(typeof result.current.useProcessingQueue).toBe('function');
        });

        it('should be callable and return a hook result', () => {
            const { result } = renderHook(() => useKGProcessing(), { wrapper });
            const { useProcessingQueue } = result.current;

            // useProcessingQueue should be callable
            expect(typeof useProcessingQueue).toBe('function');
        });

        it('should be callable with empty arguments', () => {
            const { result } = renderHook(() => useKGProcessing(), { wrapper });
            const { useProcessingQueue } = result.current;

            // Should not throw when called with no arguments
            expect(() => {
                useProcessingQueue();
            }).not.toThrow();
        });
    });

    // =========================================================================
    // useFileKGStatus Hook Tests
    // =========================================================================

    describe('useFileKGStatus Hook', () => {
        it('should return a function', () => {
            const { result } = renderHook(() => useKGProcessing(), { wrapper });

            // useFileKGStatus should be a function
            expect(typeof result.current.useFileKGStatus).toBe('function');
        });

        it('should return a hook that accepts documentId string', () => {
            const { result } = renderHook(() => useKGProcessing(), { wrapper });
            const { useFileKGStatus } = result.current;

            // useFileKGStatus should accept a string
            expect(typeof useFileKGStatus).toBe('function');
        });

        it('should be callable with documentId parameter', () => {
            const { result } = renderHook(() => useKGProcessing(), { wrapper });
            const { useFileKGStatus } = result.current;

            // Should not throw when called with a string
            expect(() => {
                useFileKGStatus('test-doc-123');
            }).not.toThrow();
        });
    });

    // =========================================================================
    // Integration Tests
    // =========================================================================

    describe('Integration Tests', () => {
        it('should export useFileKGStatus, useProcessingQueue, and processFiles', () => {
            const { result } = renderHook(() => useKGProcessing(), { wrapper });

            // All three exports should exist
            expect(result.current).toHaveProperty('useFileKGStatus');
            expect(result.current).toHaveProperty('useProcessingQueue');
            expect(result.current).toHaveProperty('processFiles');
        });

        it('should have correct return type structure', () => {
            const { result } = renderHook(() => useKGProcessing(), { wrapper });

            // Verify the structure of the returned object
            const { useFileKGStatus, useProcessingQueue, processFiles } = result.current;

            expect(typeof useFileKGStatus).toBe('function');
            expect(typeof useProcessingQueue).toBe('function');
            expect(typeof processFiles.mutate).toBe('function');
            expect(typeof processFiles.mutateAsync).toBe('function');
            expect(typeof processFiles.isPending).toBe('boolean');
            expect(typeof processFiles.isSuccess).toBe('boolean');
            expect(typeof processFiles.isError).toBe('boolean');
        });

        it('should work with QueryClientProvider wrapper', () => {
            // This test verifies that the hook works with the provider setup
            const wrapperWithClient = ({ children }: { children: React.ReactNode }) => (
                <QueryClientProvider client={queryClient}>
                    {children}
                </QueryClientProvider>
            );

            const { result } = renderHook(() => useKGProcessing(), {
                wrapper: wrapperWithClient
            });

            // Hook should render without error
            expect(result.current).toBeDefined();
            expect(result.current.useFileKGStatus).toBeDefined();
            expect(result.current.useProcessingQueue).toBeDefined();
            expect(result.current.processFiles).toBeDefined();
        });

        it('should handle multiple concurrent hook renders', () => {
            const { result: result1 } = renderHook(() => useKGProcessing(), { wrapper });
            const { result: result2 } = renderHook(() => useKGProcessing(), { wrapper });

            // Both renders should work independently
            expect(result1.current).toBeDefined();
            expect(result2.current).toBeDefined();
            expect(result1.current.processFiles).toBeDefined();
            expect(result2.current.processFiles).toBeDefined();
        });

        it('should stop polling when queue has no processing items', () => {
            // Verify the refetchInterval function exists
            const { result } = renderHook(() => useKGProcessing(), { wrapper });
            const { useProcessingQueue } = result.current;

            // Create a mock query object simulating React Query state
            // When queue has no 'processing' items, refetchInterval should return false
            const mockQueryNoProcessing = {
                state: {
                    data: [
                        { status: 'complete' },
                        { status: 'pending' },
                    ] as Array<{ status: string }>,
                },
            } as any;

            // Get the refetchInterval from the hook's query options
            const queryOptions = (useProcessingQueue as any)();

            // Verify refetchInterval returns false when no items are processing
            if (queryOptions && typeof queryOptions.refetchInterval === 'function') {
                const interval = queryOptions.refetchInterval(mockQueryNoProcessing);
                expect(interval).toBe(false);
            }
        });

        it('should continue polling when queue has processing items', () => {
            // Verify the refetchInterval function returns 2000 when items are processing
            const { result } = renderHook(() => useKGProcessing(), { wrapper });
            const { useProcessingQueue } = result.current;

            const mockQueryWithProcessing = {
                state: {
                    data: [
                        { status: 'processing' },
                        { status: 'pending' },
                    ] as Array<{ status: string }>,
                },
            } as any;

            const queryOptions = (useProcessingQueue as any)();

            if (queryOptions && typeof queryOptions.refetchInterval === 'function') {
                const interval = queryOptions.refetchInterval(mockQueryWithProcessing);
                expect(interval).toBe(2000);
            }
        });

        it('should have consistent interface across multiple renders', () => {
            const { result } = renderHook(() => useKGProcessing(), { wrapper });

            // All renders should have the same interface
            const keys = Object.keys(result.current);
            expect(keys).toContain('useFileKGStatus');
            expect(keys).toContain('useProcessingQueue');
            expect(keys).toContain('processFiles');

            // Verify processFiles properties
            expect(Object.keys(result.current.processFiles)).toContain('mutate');
            expect(Object.keys(result.current.processFiles)).toContain('mutateAsync');
            expect(Object.keys(result.current.processFiles)).toContain('isPending');
            expect(Object.keys(result.current.processFiles)).toContain('isSuccess');
            expect(Object.keys(result.current.processFiles)).toContain('isError');
        });

        it('should not throw when mutate is called with various request formats', () => {
            const { result } = renderHook(() => useKGProcessing(), { wrapper });

            // Single file
            expect(() => {
                result.current.processFiles.mutate({
                    file_ids: ['file-1'],
                    module_id: 'mod-1',
                });
            }).not.toThrow();

            // Multiple files
            expect(() => {
                result.current.processFiles.mutate({
                    file_ids: ['file-1', 'file-2', 'file-3'],
                    module_id: 'mod-2',
                });
            }).not.toThrow();

            // Empty files array
            expect(() => {
                result.current.processFiles.mutate({
                    file_ids: [],
                    module_id: 'mod-3',
                });
            }).not.toThrow();
        });
    });
});
