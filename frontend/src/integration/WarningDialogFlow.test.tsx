/**
 * @vitest-environment jsdom
 */
import { render, screen, fireEvent, waitFor, cleanup } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { SidebarTree } from '../components/explorer/SidebarTree';
import { WarningDialog } from '../components/ui/WarningDialog';
import { useExplorerStore } from '../stores';
import * as api from '../api';

// Mock dependencies
vi.mock('../api', async (importOriginal) => {
    const actual = await importOriginal<typeof import('../api')>();
    return {
        ...actual,
        createDepartment: vi.fn(),
    };
});
// Mock Lucide to avoid rendering issues
vi.mock('lucide-react', () => ({
    AlertTriangle: () => <div data-testid="alert-icon" />,
    X: () => <div data-testid="close-icon" />,
    ChevronRight: () => <div />,
    ChevronDown: () => <div />,
    Building2: () => <div />,
    Calendar: () => <div />,
    BookOpen: () => <div />,
    Package: () => <div />,
    FileText: () => <div />
}));

const queryClient = new QueryClient();

describe('Warning Dialog Integration', () => {
    beforeEach(() => {
        useExplorerStore.setState({
            creatingNodeType: 'department',
            creatingParentId: null,
            warningDialog: { isOpen: false, type: 'error', message: '' },
            warningTimeoutId: null,
            expandedIds: new Set(),
            currentPath: [],
            activeNodeId: null,
            selectedIds: new Set()
        });
        vi.clearAllMocks();
    });

    afterEach(() => {
        cleanup();
    });

    it('should show warning dialog when creating duplicate department', async () => {
        // Mock API failure
        vi.spyOn(api, 'createDepartment').mockRejectedValue(
            new api.DuplicateError('Department exists', 'DUPLICATE_NAME')
        );

        render(
            <QueryClientProvider client={queryClient}>
                <SidebarTree nodes={[]} level={0} ancestors={[]} />
                <WarningDialog />
            </QueryClientProvider>
        );

        // Find input (SidebarTree renders it if creatingNodeType='department' and level=0)
        const input = screen.getByPlaceholderText('New department');
        fireEvent.change(input, { target: { value: 'Existing Dept' } });
        fireEvent.keyDown(input, { key: 'Enter', code: 'Enter' });

        // Wait for dialog
        await waitFor(() => {
            expect(screen.getByText('Duplicate Name')).toBeTruthy();
            expect(screen.getByText('Department exists')).toBeTruthy();
        });
    });
});
