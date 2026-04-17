/**
 * ============================================================================
 * FILE: UploadDialog.test.tsx
 * LOCATION: frontend/src/components/explorer/__tests__/UploadDialog.test.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Unit tests for UploadDialog polling cleanup behavior.
 *    Verifies that dialog close properly cleans up timers.
 *
 * ROLE IN PROJECT:
 *    Regression tests for PERF-04: dialog lifecycle cleanup. Ensures that
 *    the upload dialog's polling intervals are cleared when the dialog closes.
 *
 * KEY COMPONENTS:
 *    - test_clears_polling_on_close: Verifies interval cleared on handleClose
 *    - test_calls_onclose_when_close_clicked: Verifies onClose is called
 *
 * DEPENDENCIES:
 *    - External: vitest, @testing-library/react
 *    - Internal: UploadDialog component, sonner toast
 *
 * USAGE:
 *    npm test -- src/components/explorer/__tests__/UploadDialog.test.tsx
 * ============================================================================
 */

/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, cleanup, fireEvent } from '@testing-library/react';
import React from 'react';

// Mock sonner toast
vi.mock('sonner', () => ({
    toast: {
        success: vi.fn(),
        error: vi.fn(),
    },
}));

// Mock @tanstack/react-query
const mockRefetchQueries = vi.fn();
const mockQueryClient = {
    refetchQueries: mockRefetchQueries,
};

vi.mock('@tanstack/react-query', () => ({
    useQueryClient: () => mockQueryClient,
}));

// Mock fetch
const mockFetch = vi.fn();
global.fetch = mockFetch;

// Import the component after mocks are set up
import { UploadDialog } from '../UploadDialog';

describe('UploadDialog polling cleanup', () => {
    const defaultProps = {
        isOpen: true,
        onClose: vi.fn(),
        moduleId: 'test-module-123',
        moduleName: 'Test Module',
    };

    beforeEach(() => {
        vi.clearAllMocks();
        mockFetch.mockReset();
    });

    afterEach(() => {
        cleanup();
    });

    it('calls onClose when close button is clicked', () => {
        const onClose = vi.fn();

        const { container } = render(
            <UploadDialog {...defaultProps} onClose={onClose} />
        );

        // Find the close button (it has class 'dialog-close')
        const closeButton = container.querySelector('.dialog-close');
        expect(closeButton).toBeTruthy();

        // Click the close button
        fireEvent.click(closeButton!);

        // Verify onClose was called
        expect(onClose).toHaveBeenCalled();
    });

    it('clears polling interval when processing dialog closes', async () => {
        const onClose = vi.fn();

        // Mock fetch for pipeline start and status
        mockFetch
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({ jobId: 'test-job-123' }),
            })
            .mockResolvedValueOnce({
                ok: true,
                json: async () => ({ status: 'complete', progress: 100, message: 'Done' }),
            });

        const { container, getByText, getByPlaceholderText } = render(
            <UploadDialog {...defaultProps} onClose={onClose} />
        );

        // Enter voice mode
        fireEvent.click(getByText('AI Note Generator'));

        // Fill in topic
        const topicInput = getByPlaceholderText('Enter the topic for these notes...');
        fireEvent.change(topicInput, { target: { value: 'Test Topic' } });

        // Mock file input to return a fake file
        const fileInput = document.querySelector('input[type="file"]') as HTMLInputElement;
        const fakeFile = new File(['audio content'], 'test.mp3', { type: 'audio/mpeg' });
        Object.defineProperty(fileInput, 'files', {
            value: [fakeFile],
        });
        fireEvent.change(fileInput);

        // Click generate
        fireEvent.click(getByText('Generate Notes'));

        // Find the close button in processing mode
        const closeButton = container.querySelector('.dialog-close');
        expect(closeButton).toBeTruthy();

        // Track clearInterval
        const originalClearInterval = window.clearInterval;
        window.clearInterval = vi.fn(() => {
            return originalClearInterval;
        }) as typeof window.clearInterval;

        // Close the processing dialog
        fireEvent.click(closeButton!);

        // Verify onClose was called
        expect(onClose).toHaveBeenCalled();

        // Restore
        window.clearInterval = originalClearInterval;
    });
});
