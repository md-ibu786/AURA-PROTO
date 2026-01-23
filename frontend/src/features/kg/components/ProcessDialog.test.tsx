/**
 * ============================================================================
 * FILE: ProcessDialog.test.tsx
 * LOCATION: frontend/src/features/kg/components/ProcessDialog.test.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Unit tests for ProcessDialog component. Tests dialog open/close behavior,
 *    form submission, success/error states, and integration with the store.
 *
 * TEST COVERAGE:
 *    - Dialog rendering and visibility
 *    - Submit button interactions
 *    - Success and error states
 *    - Loading states during processing
 *    - Cancel functionality
 *    - API integration via mutation
 *
 * @see: ProcessDialog.tsx - Component under test
 * @see: hooks/useKGProcessing.ts - Hook providing processFiles mutation
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { act } from 'react';
import { ProcessDialog } from './ProcessDialog';
import { useExplorerStore, type UseExplorerStore } from '../../../stores';
import { useKGProcessing } from '../hooks/useKGProcessing';

// Mock the store
vi.mock('../../../stores', () => ({
    useExplorerStore: vi.fn(),
}));

// Mock the hook
vi.mock('../hooks/useKGProcessing', () => ({
    useKGProcessing: vi.fn(),
}));

// Type for mocked store (extends store type with mock methods)
type MockedExplorerStore = UseExplorerStore & {
    mockReturnValue: (value: Partial<UseExplorerStore>) => void;
};

// Type for mocked useKGProcessing hook (actual return type + mock method)
type MockedKGProcessingHook = {
    processFiles: {
        mutate: ReturnType<typeof vi.fn>;
        isPending: boolean;
    };
};

type MockedKGProcessing = MockedKGProcessingHook & {
    mockReturnValue: (value: MockedKGProcessingHook) => void;
};

describe('ProcessDialog', () => {
    const mockCloseProcessDialog = vi.fn();
    const mockClearSelection = vi.fn();
    const mockSetSelectionMode = vi.fn();
    const mockMutate = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();

        // Default store state - dialog closed
        (useExplorerStore as unknown as MockedExplorerStore).mockReturnValue({
            processDialog: { open: false, fileIds: [], moduleId: '' },
            closeProcessDialog: mockCloseProcessDialog,
            clearSelection: mockClearSelection,
            setSelectionMode: mockSetSelectionMode,
        });

        // Default hook state
        (useKGProcessing as unknown as MockedKGProcessing).mockReturnValue({
            processFiles: {
                mutate: mockMutate,
                isPending: false,
            },
        });
    });

    describe('Visibility', () => {
        it('returns null when dialog is closed', () => {
            const { container } = render(<ProcessDialog />);
            expect(container.firstChild).toBeNull();
        });

        it('renders dialog when open is true', () => {
            (useExplorerStore as unknown as MockedExplorerStore).mockReturnValue({
                processDialog: { open: true, fileIds: ['file-1', 'file-2'], moduleId: 'mod-1' },
                closeProcessDialog: mockCloseProcessDialog,
                clearSelection: mockClearSelection,
                setSelectionMode: mockSetSelectionMode,
            });

            render(<ProcessDialog />);
            expect(screen.getByText('Process Documents')).toBeInTheDocument();
        });

        it('displays correct file count', () => {
            (useExplorerStore as unknown as MockedExplorerStore).mockReturnValue({
                processDialog: { open: true, fileIds: ['file-1', 'file-2', 'file-3'], moduleId: 'mod-1' },
                closeProcessDialog: mockCloseProcessDialog,
                clearSelection: mockClearSelection,
                setSelectionMode: mockSetSelectionMode,
            });

            render(<ProcessDialog />);
            expect(screen.getByText('3')).toBeInTheDocument();
        });
    });

    describe('Processing Actions List', () => {
        it('displays all processing action items', () => {
            (useExplorerStore as unknown as MockedExplorerStore).mockReturnValue({
                processDialog: { open: true, fileIds: ['file-1'], moduleId: 'mod-1' },
                closeProcessDialog: mockCloseProcessDialog,
                clearSelection: mockClearSelection,
                setSelectionMode: mockSetSelectionMode,
            });

            render(<ProcessDialog />);
            expect(screen.getByText(/Extract entities/)).toBeInTheDocument();
            expect(screen.getByText(/Generate relationships/)).toBeInTheDocument();
            expect(screen.getByText(/Create vector embeddings/)).toBeInTheDocument();
            expect(screen.getByText(/Update the module's Knowledge Graph/)).toBeInTheDocument();
        });
    });

    describe('Submit Behavior', () => {
        it('calls processFiles.mutate on confirm', () => {
            (useExplorerStore as unknown as MockedExplorerStore).mockReturnValue({
                processDialog: { open: true, fileIds: ['file-1', 'file-2'], moduleId: 'mod-1' },
                closeProcessDialog: mockCloseProcessDialog,
                clearSelection: mockClearSelection,
                setSelectionMode: mockSetSelectionMode,
            });

            render(<ProcessDialog />);
            fireEvent.click(screen.getByText('Start Processing'));

            expect(mockMutate).toHaveBeenCalledWith(
                { file_ids: ['file-1', 'file-2'], module_id: 'mod-1' },
                expect.any(Object)
            );
        });

        it('shows loading state during processing', () => {
            (useExplorerStore as unknown as MockedExplorerStore).mockReturnValue({
                processDialog: { open: true, fileIds: ['file-1'], moduleId: 'mod-1' },
                closeProcessDialog: mockCloseProcessDialog,
                clearSelection: mockClearSelection,
                setSelectionMode: mockSetSelectionMode,
            });

            // Simulate clicking submit
            render(<ProcessDialog />);
            fireEvent.click(screen.getByText('Start Processing'));
            
            // The button should show loading text
            expect(screen.getByText('Processing...')).toBeInTheDocument();
        });
    });

    describe('Cancel Behavior', () => {
        it('closes dialog on cancel click', () => {
            (useExplorerStore as unknown as MockedExplorerStore).mockReturnValue({
                processDialog: { open: true, fileIds: ['file-1'], moduleId: 'mod-1' },
                closeProcessDialog: mockCloseProcessDialog,
                clearSelection: mockClearSelection,
                setSelectionMode: mockSetSelectionMode,
            });

            render(<ProcessDialog />);
            fireEvent.click(screen.getByText('Cancel'));

            expect(mockCloseProcessDialog).toHaveBeenCalled();
        });

        it('closes dialog on overlay click', () => {
            (useExplorerStore as unknown as MockedExplorerStore).mockReturnValue({
                processDialog: { open: true, fileIds: ['file-1'], moduleId: 'mod-1' },
                closeProcessDialog: mockCloseProcessDialog,
                clearSelection: mockClearSelection,
                setSelectionMode: mockSetSelectionMode,
            });

            render(<ProcessDialog />);
            fireEvent.click(screen.getByRole('button', { name: '' })); // Close button (X)

            expect(mockCloseProcessDialog).toHaveBeenCalled();
        });
    });

    describe('Success State', () => {
        it('shows success message after processing completes', async () => {
            // Simulate successful mutation
            let onSuccessCallback: (() => void) | undefined;
            mockMutate.mockImplementation((_data, callbacks) => {
                onSuccessCallback = callbacks.onSuccess;
            });

            (useExplorerStore as unknown as MockedExplorerStore).mockReturnValue({
                processDialog: { open: true, fileIds: ['file-1', 'file-2'], moduleId: 'mod-1' },
                closeProcessDialog: mockCloseProcessDialog,
                clearSelection: mockClearSelection,
                setSelectionMode: mockSetSelectionMode,
            });

            render(<ProcessDialog />);
            fireEvent.click(screen.getByText('Start Processing'));

            // Trigger success callback
            if (onSuccessCallback) {
                act(() => {
                    onSuccessCallback?.();
                });
            }

            await waitFor(() => {
                expect(screen.getByText('Documents Queued!')).toBeInTheDocument();
            });
        });

        it('shows correct document count in success message', async () => {
            let onSuccessCallback: (() => void) | undefined;
            mockMutate.mockImplementation((_data, callbacks) => {
                onSuccessCallback = callbacks.onSuccess;
            });

            (useExplorerStore as unknown as MockedExplorerStore).mockReturnValue({
                processDialog: { open: true, fileIds: ['f1', 'f2', 'f3'], moduleId: 'mod-1' },
                closeProcessDialog: mockCloseProcessDialog,
                clearSelection: mockClearSelection,
                setSelectionMode: mockSetSelectionMode,
            });

            render(<ProcessDialog />);
            fireEvent.click(screen.getByText('Start Processing'));
            
            if (onSuccessCallback) {
                act(() => {
                    onSuccessCallback?.();
                });
            }

            await waitFor(() => {
                expect(screen.getByText(/3 document\(s\) have been queued/)).toBeInTheDocument();
            });
        });
    });

    describe('Error State', () => {
        it('displays error message on failure', async () => {
            let onErrorCallback: ((err: Error) => void) | undefined;
            mockMutate.mockImplementation((_data, callbacks) => {
                onErrorCallback = callbacks.onError;
            });

            (useExplorerStore as unknown as MockedExplorerStore).mockReturnValue({
                processDialog: { open: true, fileIds: ['file-1'], moduleId: 'mod-1' },
                closeProcessDialog: mockCloseProcessDialog,
                clearSelection: mockClearSelection,
                setSelectionMode: mockSetSelectionMode,
            });

            render(<ProcessDialog />);
            fireEvent.click(screen.getByText('Start Processing'));

            if (onErrorCallback) {
                act(() => {
                    onErrorCallback?.(new Error('Network error'));
                });
            }

            await waitFor(() => {
                expect(screen.getByText('Network error')).toBeInTheDocument();
            });
        });
    });
});
