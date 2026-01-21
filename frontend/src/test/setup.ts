/**
 * ============================================================================
 * FILE: setup.ts
 * LOCATION: frontend/src/test/setup.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Global test setup for Vitest. Configures test environment with mocks,
 *    DOM matchers, and cleanup routines for React Testing Library.
 *
 * ROLE IN PROJECT:
 *    Called before every test file via vitest.config.ts setupFiles.
 *    Provides:
 *    - @testing-library/jest-dom matchers (toBeInTheDocument, etc.)
 *    - Mock for window.matchMedia (responsive tests)
 *    - Mock for API client (fetchApi, fetchFormData)
 *    - Auto cleanup after each test
 *
 * MOCKS:
 *    - window.matchMedia: Required for components using CSS media queries
 *    - API client: Prevents actual network calls in unit tests
 *
 * @see: vitest.config.ts - References this file
 * @see: api/client.ts - API functions mocked here
 */
import '@testing-library/jest-dom';
import { afterEach, vi, beforeAll } from 'vitest';
import { cleanup } from '@testing-library/react';

// Cleanup after each test
afterEach(() => {
    cleanup();
    vi.clearAllMocks();
});

// Mock window.matchMedia for responsive component tests
beforeAll(() => {
    Object.defineProperty(window, 'matchMedia', {
        writable: true,
        value: vi.fn().mockImplementation((query: string) => ({
            matches: false,
            media: query,
            onchange: null,
            addListener: vi.fn(), // Deprecated
            removeListener: vi.fn(), // Deprecated
            addEventListener: vi.fn(),
            removeEventListener: vi.fn(),
            dispatchEvent: vi.fn(),
        })),
    });
});

// Mock fetch globally with a basic implementation
beforeAll(() => {
    global.fetch = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
        return Promise.resolve({
            ok: true,
            status: 200,
            json: () => Promise.resolve({}),
        } as Response);
    });
});

// Mock React Query hooks used in components
vi.mock('@tanstack/react-query', async () => {
    const actual = await vi.importActual('@tanstack/react-query');
    return {
        ...actual,
        useQuery: vi.fn(() => ({
            data: undefined,
            isLoading: false,
            error: null,
            refetch: vi.fn(),
        })),
        useMutation: vi.fn(() => ({
            mutate: vi.fn(),
            mutateAsync: vi.fn(),
            isPending: false,
            isSuccess: false,
            isError: false,
            error: null,
        })),
        useQueryClient: vi.fn(() => ({
            invalidateQueries: vi.fn(),
            refetchQueries: vi.fn(),
        })),
    };
});

// Set global timeout
vi.setConfig({ testTimeout: 10000 });
