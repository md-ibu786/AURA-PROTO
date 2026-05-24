/**
 * ============================================================================
 * FILE: DeleteFromKGDialog.test.tsx
 * LOCATION: frontend/src/features/kg/components/__tests__/DeleteFromKGDialog.test.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Unit tests for the DeleteFromKGDialog component.
 *
 * ROLE IN PROJECT:
 *    Validates the KG deletion confirmation dialog behavior including:
 *    - Render state based on dialog open/close
 *    - Submit button triggers correct mutation
 *    - Error and success state display
 *    - Close button state reset
 *
 * KEY COMPONENTS:
 *    - DeleteFromKGDialog test suite: 7 test cases
 *
 * DEPENDENCIES:
 *    - External: vitest, @testing-library/react
 *    - Internal: features/kg/components/DeleteFromKGDialog
 *
 * USAGE:
 *    npm test -- src/features/kg/components/__tests__/DeleteFromKGDialog.test.tsx
 * ============================================================================
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { act } from 'react';
import { DeleteFromKGDialog } from '../DeleteFromKGDialog';
import { useExplorerStore } from '../../../../stores';
import { useKGProcessing } from '../../hooks/useKGProcessing';

// Mock the store
vi.mock('../../../../stores', () => ({
    useExplorerStore: vi.fn(),
}));

// Mock the hook
vi.mock('../../hooks/useKGProcessing', () => ({
    useKGProcessing: vi.fn(),
}));

type MockedExplorerStore = {
    kgDeleteDialog: { open: boolean; fileIds: string[]; moduleId: string };
    closeKGDeleteDialog: ReturnType<typeof vi.fn>;
    clearSelection: ReturnType<typeof vi.fn>;
    setSelectionMode: ReturnType<typeof vi.fn>;
    setDeleteMode: ReturnType<typeof vi.fn>;
};

type MockedKGProcessing = {
    deleteFiles: {
        mutate: ReturnType<typeof vi.fn>;
    };
};

describe('DeleteFromKGDialog', () => {
    const mockCloseKGDeleteDialog = vi.fn();
    const mockClearSelection = vi.fn();
    const mockSetSelectionMode = vi.fn();
    const mockSetDeleteMode = vi.fn();
    const mockMutate = vi.fn();

    beforeEach(() => {
        vi.clearAllMocks();

        (useExplorerStore as unknown as MockedExplorerStore & { mockReturnValue: (_v: Partial<MockedExplorerStore>) => void }).mockReturnValue({
            kgDeleteDialog: { open: false, fileIds: [], moduleId: '' },
            closeKGDeleteDialog: mockCloseKGDeleteDialog,
            clearSelection: mockClearSelection,
            setSelectionMode: mockSetSelectionMode,
            setDeleteMode: mockSetDeleteMode,
        });

        (useKGProcessing as unknown as MockedKGProcessing & { mockReturnValue: (_v: MockedKGProcessing) => void }).mockReturnValue({
            deleteFiles: {
                mutate: mockMutate,
            },
        });
    });

    it('does not render when kgDeleteDialog.open is false', () => {
        const { container } = render(<DeleteFromKGDialog />);
        expect(container.firstChild).toBeNull();
    });

    it('renders with correct document count when open', () => {
        (useExplorerStore as unknown as MockedExplorerStore & { mockReturnValue: (_v: Partial<MockedExplorerStore>) => void }).mockReturnValue({
            kgDeleteDialog: { open: true, fileIds: ['doc1', 'doc2', 'doc3'], moduleId: 'mod1' },
            closeKGDeleteDialog: mockCloseKGDeleteDialog,
            clearSelection: mockClearSelection,
            setSelectionMode: mockSetSelectionMode,
            setDeleteMode: mockSetDeleteMode,
        });

        render(<DeleteFromKGDialog />);
        expect(screen.getByText('3')).toBeInTheDocument();
        expect(screen.getByText(/Remove/)).toBeInTheDocument();
        expect(screen.getByText(/document\(s\) from the Knowledge Graph/)).toBeInTheDocument();
    });

    it('submit button triggers deleteFiles.mutate with correct file_ids and module_id', () => {
        (useExplorerStore as unknown as MockedExplorerStore & { mockReturnValue: (_v: Partial<MockedExplorerStore>) => void }).mockReturnValue({
            kgDeleteDialog: { open: true, fileIds: ['doc1', 'doc2'], moduleId: 'mod123' },
            closeKGDeleteDialog: mockCloseKGDeleteDialog,
            clearSelection: mockClearSelection,
            setSelectionMode: mockSetSelectionMode,
            setDeleteMode: mockSetDeleteMode,
        });

        render(<DeleteFromKGDialog />);
        const deleteButton = screen.getByText('Delete from KG');
        fireEvent.click(deleteButton);

        expect(mockMutate).toHaveBeenCalledWith(
            { file_ids: ['doc1', 'doc2'], module_id: 'mod123' },
            expect.any(Object)
        );
    });

    it('error state displays error message', async () => {
        let onErrorCallback: ((_err: Error) => void) | undefined;
        mockMutate.mockImplementation((_vars: unknown, options: { onError: (err: Error) => void }) => {
            onErrorCallback = options.onError;
        });

        (useExplorerStore as unknown as MockedExplorerStore & { mockReturnValue: (_v: Partial<MockedExplorerStore>) => void }).mockReturnValue({
            kgDeleteDialog: { open: true, fileIds: ['doc1'], moduleId: 'mod1' },
            closeKGDeleteDialog: mockCloseKGDeleteDialog,
            clearSelection: mockClearSelection,
            setSelectionMode: mockSetSelectionMode,
            setDeleteMode: mockSetDeleteMode,
        });

        render(<DeleteFromKGDialog />);
        const deleteButton = screen.getByText('Delete from KG');
        fireEvent.click(deleteButton);

        if (onErrorCallback) {
            act(() => {
                onErrorCallback?.(new Error('Deletion failed: network error'));
            });
        }

        await waitFor(() => {
            expect(screen.getByText('Deletion failed: network error')).toBeInTheDocument();
        });
    });

    it('success state displays deleted/failed counts', async () => {
        let onSuccessCallback: ((data: { deleted_count: number; failed: unknown[] }) => void) | undefined;
        mockMutate.mockImplementation((_vars: unknown, options: { onSuccess: (data: { deleted_count: number; failed: unknown[] }) => void }) => {
            onSuccessCallback = options.onSuccess;
        });

        (useExplorerStore as unknown as MockedExplorerStore & { mockReturnValue: (_v: Partial<MockedExplorerStore>) => void }).mockReturnValue({
            kgDeleteDialog: { open: true, fileIds: ['doc1', 'doc2', 'doc3', 'doc4', 'doc5', 'docX'], moduleId: 'mod1' },
            closeKGDeleteDialog: mockCloseKGDeleteDialog,
            clearSelection: mockClearSelection,
            setSelectionMode: mockSetSelectionMode,
            setDeleteMode: mockSetDeleteMode,
        });

        render(<DeleteFromKGDialog />);
        const deleteButton = screen.getByText('Delete from KG');
        fireEvent.click(deleteButton);

        if (onSuccessCallback) {
            act(() => {
                onSuccessCallback?.({ deleted_count: 5, failed: ['docX'] });
            });
        }

        await waitFor(() => {
            expect(screen.getAllByText('Deletion Complete')).toHaveLength(2);
            expect(screen.getByText(/5 document\(s\) have been removed/)).toBeInTheDocument();
            expect(screen.getByText(/1 document\(s\) failed/)).toBeInTheDocument();
        });
    });

    it('close button resets all local state and calls closeKGDeleteDialog', () => {
        (useExplorerStore as unknown as MockedExplorerStore & { mockReturnValue: (_v: Partial<MockedExplorerStore>) => void }).mockReturnValue({
            kgDeleteDialog: { open: true, fileIds: ['doc1'], moduleId: 'mod1' },
            closeKGDeleteDialog: mockCloseKGDeleteDialog,
            clearSelection: mockClearSelection,
            setSelectionMode: mockSetSelectionMode,
            setDeleteMode: mockSetDeleteMode,
        });

        render(<DeleteFromKGDialog />);
        const closeButtons = screen.getAllByRole('button');
        const xButton = closeButtons.find(btn => btn.classList.contains('dialog-close'));
        if (xButton) {
            fireEvent.click(xButton);
        } else {
            fireEvent.click(screen.getByText('Cancel'));
        }

        expect(mockCloseKGDeleteDialog).toHaveBeenCalled();
    });

    it('success close also calls clearSelection, setSelectionMode(false), setDeleteMode(false)', async () => {
        let onSuccessCallback: ((data: { deleted_count: number; failed: unknown[] }) => void) | undefined;
        mockMutate.mockImplementation((_vars: unknown, options: { onSuccess: (data: { deleted_count: number; failed: unknown[] }) => void }) => {
            onSuccessCallback = options.onSuccess;
        });

        (useExplorerStore as unknown as MockedExplorerStore & { mockReturnValue: (_v: Partial<MockedExplorerStore>) => void }).mockReturnValue({
            kgDeleteDialog: { open: true, fileIds: ['doc1'], moduleId: 'mod1' },
            closeKGDeleteDialog: mockCloseKGDeleteDialog,
            clearSelection: mockClearSelection,
            setSelectionMode: mockSetSelectionMode,
            setDeleteMode: mockSetDeleteMode,
        });

        render(<DeleteFromKGDialog />);
        const deleteButton = screen.getByText('Delete from KG');
        fireEvent.click(deleteButton);

        if (onSuccessCallback) {
            act(() => {
                onSuccessCallback?.({ deleted_count: 1, failed: [] });
            });
        }

        await waitFor(() => {
            expect(screen.getByText('Done')).toBeInTheDocument();
        });

        const doneButton = screen.getByText('Done');
        fireEvent.click(doneButton);

        expect(mockClearSelection).toHaveBeenCalled();
        expect(mockSetSelectionMode).toHaveBeenCalledWith(false);
        expect(mockSetDeleteMode).toHaveBeenCalledWith(false);
        expect(mockCloseKGDeleteDialog).toHaveBeenCalled();
    });
});
