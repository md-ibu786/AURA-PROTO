/**
 * ============================================================================
 * FILE: ProcessingQueue.test.tsx
 * LOCATION: frontend/src/features/kg/components/ProcessingQueue.test.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Unit tests for ProcessingQueue component. Tests queue display, progress
 *    bars, status colors, empty state, loading state, and error display.
 *
 * TEST COVERAGE:
 *    - Empty queue (hidden when no items)
 *    - Loading state
 *    - Error state
 *    - Queue item rendering
 *    - Progress bar display
 *    - Status color coding
 *    - Error message display per item
 *
 * @see: ProcessingQueue.tsx - Component under test
 * @see: hooks/useKGProcessing.ts - useProcessingQueue hook
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ProcessingQueue } from './ProcessingQueue';
import { useKGProcessing } from '../hooks/useKGProcessing';
import type { ProcessingQueueItem } from '../types/kg.types';

// Mock the hook
vi.mock('../hooks/useKGProcessing', () => ({
    useKGProcessing: vi.fn(),
}));

describe('ProcessingQueue', () => {
    const mockUseProcessingQueue = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();

        (useKGProcessing as ReturnType<typeof vi.fn>).mockReturnValue({
            useProcessingQueue: mockUseProcessingQueue,
        });
    });

    describe('Visibility States', () => {
        it('returns null when loading', () => {
            mockUseProcessingQueue.mockReturnValue({
                data: undefined,
                isLoading: true,
                error: null,
            });

            const { container } = render(<ProcessingQueue />);
            expect(container.firstChild).toBeNull();
        });

        it('returns null when queue is empty', () => {
            mockUseProcessingQueue.mockReturnValue({
                data: [],
                isLoading: false,
                error: null,
            });

            const { container } = render(<ProcessingQueue />);
            expect(container.firstChild).toBeNull();
        });

        it('returns null when queue is undefined', () => {
            mockUseProcessingQueue.mockReturnValue({
                data: undefined,
                isLoading: false,
                error: null,
            });

            const { container } = render(<ProcessingQueue />);
            expect(container.firstChild).toBeNull();
        });

        it('displays error message when query fails', () => {
            mockUseProcessingQueue.mockReturnValue({
                data: undefined,
                isLoading: false,
                error: new Error('Failed to fetch'),
            });

            render(<ProcessingQueue />);
            expect(screen.getByText('Failed to load queue')).toBeInTheDocument();
        });
    });

    describe('Queue Display', () => {
        it('renders queue panel when items exist', () => {
            const mockQueue: ProcessingQueueItem[] = [
                {
                    document_id: 'doc-1',
                    file_name: 'test-file.pdf',
                    status: 'processing',
                    progress: 50,
                    step: 'Extracting entities',
                },
            ];

            mockUseProcessingQueue.mockReturnValue({
                data: mockQueue,
                isLoading: false,
                error: null,
            });

            render(<ProcessingQueue />);
            expect(screen.getByText('Processing (1)')).toBeInTheDocument();
        });

        it('displays correct queue count', () => {
            const mockQueue: ProcessingQueueItem[] = [
                { document_id: 'doc-1', file_name: 'file1.pdf', status: 'processing', progress: 30, step: 'Step 1' },
                { document_id: 'doc-2', file_name: 'file2.pdf', status: 'processing', progress: 60, step: 'Step 2' },
                { document_id: 'doc-3', file_name: 'file3.pdf', status: 'pending', progress: 0, step: 'Waiting' },
            ];

            mockUseProcessingQueue.mockReturnValue({
                data: mockQueue,
                isLoading: false,
                error: null,
            });

            render(<ProcessingQueue />);
            expect(screen.getByText('Processing (3)')).toBeInTheDocument();
        });

        it('displays file names for each queue item', () => {
            const mockQueue: ProcessingQueueItem[] = [
                { document_id: 'doc-1', file_name: 'document-alpha.pdf', status: 'processing', progress: 50, step: 'Step' },
                { document_id: 'doc-2', file_name: 'notes-beta.txt', status: 'ready', progress: 100, step: 'Complete' },
            ];

            mockUseProcessingQueue.mockReturnValue({
                data: mockQueue,
                isLoading: false,
                error: null,
            });

            render(<ProcessingQueue />);
            expect(screen.getByText('document-alpha.pdf')).toBeInTheDocument();
            expect(screen.getByText('notes-beta.txt')).toBeInTheDocument();
        });
    });

    describe('Progress Display', () => {
        it('shows progress percentage', () => {
            const mockQueue: ProcessingQueueItem[] = [
                { document_id: 'doc-1', file_name: 'file.pdf', status: 'processing', progress: 75, step: 'Embedding' },
            ];

            mockUseProcessingQueue.mockReturnValue({
                data: mockQueue,
                isLoading: false,
                error: null,
            });

            render(<ProcessingQueue />);
            expect(screen.getByText('75%')).toBeInTheDocument();
        });

        it('shows current step', () => {
            const mockQueue: ProcessingQueueItem[] = [
                { document_id: 'doc-1', file_name: 'file.pdf', status: 'processing', progress: 50, step: 'Generating embeddings' },
            ];

            mockUseProcessingQueue.mockReturnValue({
                data: mockQueue,
                isLoading: false,
                error: null,
            });

            render(<ProcessingQueue />);
            expect(screen.getByText('Generating embeddings')).toBeInTheDocument();
        });
    });

    describe('Status Colors', () => {
        it('applies processing status color', () => {
            const mockQueue: ProcessingQueueItem[] = [
                { document_id: 'doc-1', file_name: 'file.pdf', status: 'processing', progress: 50, step: 'Step' },
            ];

            mockUseProcessingQueue.mockReturnValue({
                data: mockQueue,
                isLoading: false,
                error: null,
            });

            render(<ProcessingQueue />);
            const statusText = screen.getByText('processing');
            expect(statusText).toHaveClass('text-amber-500');
        });

        it('applies failed status color', () => {
            const mockQueue: ProcessingQueueItem[] = [
                { document_id: 'doc-1', file_name: 'file.pdf', status: 'failed', progress: 30, step: 'Failed', error: 'Timeout' },
            ];

            mockUseProcessingQueue.mockReturnValue({
                data: mockQueue,
                isLoading: false,
                error: null,
            });

            render(<ProcessingQueue />);
            const statusText = screen.getByText('failed');
            expect(statusText).toHaveClass('text-red-500');
        });

        it('applies ready status color', () => {
            const mockQueue: ProcessingQueueItem[] = [
                { document_id: 'doc-1', file_name: 'file.pdf', status: 'ready', progress: 100, step: 'Complete' },
            ];

            mockUseProcessingQueue.mockReturnValue({
                data: mockQueue,
                isLoading: false,
                error: null,
            });

            render(<ProcessingQueue />);
            const statusText = screen.getByText('ready');
            expect(statusText).toHaveClass('text-green-500');
        });
    });

    describe('Error Display', () => {
        it('displays error message for failed items', () => {
            const mockQueue: ProcessingQueueItem[] = [
                { 
                    document_id: 'doc-1', 
                    file_name: 'file.pdf', 
                    status: 'failed', 
                    progress: 20, 
                    step: 'Failed',
                    error: 'Connection timeout' 
                },
            ];

            mockUseProcessingQueue.mockReturnValue({
                data: mockQueue,
                isLoading: false,
                error: null,
            });

            render(<ProcessingQueue />);
            expect(screen.getByText('Connection timeout')).toBeInTheDocument();
        });

        it('does not display error section when no error', () => {
            const mockQueue: ProcessingQueueItem[] = [
                { document_id: 'doc-1', file_name: 'file.pdf', status: 'processing', progress: 50, step: 'Step' },
            ];

            mockUseProcessingQueue.mockReturnValue({
                data: mockQueue,
                isLoading: false,
                error: null,
            });

            render(<ProcessingQueue />);
            // The error text should not be present
            expect(screen.queryByText('Connection timeout')).not.toBeInTheDocument();
        });
    });
});
