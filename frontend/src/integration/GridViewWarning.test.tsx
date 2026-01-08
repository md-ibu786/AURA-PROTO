/**
 * @vitest-environment jsdom
 */
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { GridView } from '../components/explorer/GridView';
import { WarningDialog } from '../components/ui/WarningDialog';
import { useExplorerStore } from '../stores';
import * as api from '../api';

// Mock dependencies
vi.mock('../api', async (importOriginal) => {
    const actual = await importOriginal<typeof import('../api')>();
    return {
        ...actual,
        createDepartment: vi.fn(),
        renameNode: vi.fn(),
    };
});

// Mock Lucide to avoid rendering issues
vi.mock('lucide-react', () => ({
    AlertTriangle: () => <div data-testid="alert-icon" />,
    X: () => <div data-testid="close-icon" />,
    Building2: () => <div />,
    Calendar: () => <div />,
    BookOpen: () => <div />,
    FileText: () => <div />,
    FolderOpen: () => <div />
}));

const queryClient = new QueryClient();

describe('GridView Warning Integration', () => {
    beforeEach(() => {
        useExplorerStore.setState({
            creatingNodeType: 'department',
            creatingParentId: null,
            warningDialog: { isOpen: false, type: 'error', message: '' },
            warningTimeoutId: null,
            selectedIds: new Set(),
            viewMode: 'grid',
            searchQuery: '',
        });
        vi.clearAllMocks();
    });

    afterEach(() => {
        cleanup();
    });

    it('should show warning dialog when creating duplicate department in GridView', async () => {
        // Mock API failure
        vi.spyOn(api, 'createDepartment').mockRejectedValue(
            new api.DuplicateError('Department exists', 'DUPLICATE_NAME')
        );

        render(
            <QueryClientProvider client={queryClient}>
                <GridView items={[]} allItems={[]} />
                <WarningDialog />
            </QueryClientProvider>
        );

        // Find input (GridView renders it if creatingNodeType='department')
        const input = screen.getByPlaceholderText(/New Department/i);
        fireEvent.change(input, { target: { value: 'Existing Dept' } });
        fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

        // Wait for dialog
        await waitFor(() => {
            expect(screen.getByText('Duplicate Name')).toBeTruthy();
            expect(screen.getByText('Department exists')).toBeTruthy();
        });
    });

    it('should show warning dialog when renaming to duplicate name in GridView', async () => {
        const item = { id: 'dept-1', type: 'department' as const, label: 'Dept 1' };
        
        useExplorerStore.setState({
            renamingNodeId: 'dept-1',
            creatingNodeType: null
        });

        // Mock API failure
        vi.spyOn(api, 'renameNode').mockRejectedValue(
            new api.DuplicateError('Name taken', 'DUPLICATE_NAME')
        );

        render(
            <QueryClientProvider client={queryClient}>
                <GridView items={[item]} allItems={[item]} />
                <WarningDialog />
            </QueryClientProvider>
        );

        // Find rename input
        const input = screen.getByDisplayValue('Dept 1');
        fireEvent.change(input, { target: { value: 'Existing Dept' } });
        fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

        // Wait for dialog
        await waitFor(() => {
            expect(screen.getByText('Duplicate Name')).toBeTruthy();
            expect(screen.getByText('Name taken')).toBeTruthy();
        });
    });
});
