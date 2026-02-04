/**
 * ============================================================================
 * FILE: ExplorerPage.test.tsx
 * LOCATION: frontend/src/pages/ExplorerPage.test.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Unit tests for ExplorerPage component. Tests page layout, data fetching,
 *    navigation, view modes, empty states, loading states, error handling,
 *    and integration with sub-components.
 *
 * TEST COVERAGE:
 *    - Layout rendering (sidebar, header, content)
 *    - Data loading states
 *    - Error states
 *    - Empty folder states
 *    - Grid/List view modes
 *    - Delete confirmation dialog
 *    - KG feature components
 *    - Background click to close context menu
 *
 * @see: ExplorerPage.tsx - Component under test
 * @see: stores/useExplorerStore.ts - State store
 * @see: stores/useAuthStore.ts - Auth store
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import '@testing-library/jest-dom';
import ExplorerPage from './ExplorerPage';
import { useExplorerStore } from '../stores';
import { useAuthStore } from '../stores/useAuthStore';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import type { FileSystemNode } from '../types';

// Mock the stores
vi.mock('../stores', () => ({
    useExplorerStore: vi.fn(),
}));

vi.mock('../stores/useAuthStore', () => ({
    useAuthStore: vi.fn(),
}));

// Mock React Query
vi.mock('@tanstack/react-query', async () => {
    const actual = await vi.importActual('@tanstack/react-query');
    return {
        ...actual,
        useQuery: vi.fn(),
        useQueryClient: vi.fn(),
    };
});

// Mock API
vi.mock('../api', () => ({
    getExplorerTree: vi.fn(),
    deleteDepartment: vi.fn(),
    deleteSemester: vi.fn(),
    deleteSubject: vi.fn(),
    deleteModule: vi.fn(),
    deleteNote: vi.fn(),
}));

// Mock child components to isolate tests
vi.mock('../components/layout/Sidebar', () => ({
    Sidebar: ({ isLoading }: { isLoading: boolean }) => (
        <div data-testid="sidebar">{isLoading ? 'Loading sidebar...' : 'Sidebar'}</div>
    ),
}));

vi.mock('../components/layout/Header', () => ({
    Header: () => <div data-testid="header">Header</div>,
}));

vi.mock('../components/explorer/GridView', () => ({
    GridView: ({ items }: { items: FileSystemNode[] }) => (
        <div data-testid="grid-view">Grid: {items.length} items</div>
    ),
}));

vi.mock('../components/explorer/ListView', () => ({
    ListView: ({ items }: { items: FileSystemNode[] }) => (
        <div data-testid="list-view">List: {items.length} items</div>
    ),
}));

vi.mock('../components/explorer/ContextMenu', () => ({
    ContextMenu: () => <div data-testid="context-menu">Context Menu</div>,
}));

vi.mock('../components/ui/ConfirmDialog', () => ({
    ConfirmDialog: ({ isOpen, title }: { isOpen: boolean; title: string }) =>
        isOpen ? <div data-testid="confirm-dialog">{title}</div> : null,
}));

vi.mock('../components/ui/WarningDialog', () => ({
    WarningDialog: () => <div data-testid="warning-dialog">Warning</div>,
}));

vi.mock('../features/kg/components/FileSelectionBar', () => ({
    FileSelectionBar: () => <div data-testid="file-selection-bar">Selection Bar</div>,
}));

vi.mock('../features/kg/components/ProcessDialog', () => ({
    ProcessDialog: () => <div data-testid="process-dialog">Process Dialog</div>,
}));

vi.mock('../features/kg/components/ProcessingQueue', () => ({
    ProcessingQueue: () => <div data-testid="processing-queue">Processing Queue</div>,
}));

vi.mock('../features/kg/components/DeleteFromKGDialog', () => ({
    DeleteFromKGDialog: () => <div data-testid="delete-kg-dialog">Delete KG Dialog</div>,
}));


describe('ExplorerPage', () => {
    const mockCloseContextMenu = vi.fn();
    const mockCloseDeleteDialog = vi.fn();
    const mockRefetchQueries = vi.fn();
    const mockNavigate = vi.fn();

    const defaultStoreState = {
        viewMode: 'grid' as const,
        currentPath: [],
        contextMenuPosition: null,
        closeContextMenu: mockCloseContextMenu,
        creatingNodeType: null,
        deleteDialogOpen: false,
        nodeToDelete: null,
        closeDeleteDialog: mockCloseDeleteDialog,
        navigateTo: vi.fn(),
    };

    const defaultAuthState = {
        user: { id: '1', role: 'admin', departmentId: undefined },
        isAdmin: () => true,
    };

    const mockTree: FileSystemNode[] = [
        { id: 'dept-1', label: 'Computer Science', type: 'department', children: [], parentId: null },
        { id: 'dept-2', label: 'Mathematics', type: 'department', children: [], parentId: null },
    ];

    const renderWithRouter = (component: React.ReactElement) => {
        return render(<BrowserRouter>{component}</BrowserRouter>);
    };

    beforeEach(() => {
        vi.clearAllMocks();

        (useExplorerStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(defaultStoreState);

        (useAuthStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue(defaultAuthState);

        (useQuery as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
            data: mockTree,
            isLoading: false,
            error: null,
        });

        (useQueryClient as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
            refetchQueries: mockRefetchQueries,
        });

        (vi.fn() as unknown as ReturnType<typeof vi.fn>).mockReturnValue(mockNavigate);
    });

    describe('Layout Rendering', () => {
        it('renders main layout with sidebar, header, and content', () => {
            renderWithRouter(<ExplorerPage />);

            expect(screen.getByTestId('sidebar')).toBeInTheDocument();
            expect(screen.getByTestId('header')).toBeInTheDocument();
            expect(screen.getByTestId('grid-view')).toBeInTheDocument();
        });

        it('renders warning dialog component', () => {
            renderWithRouter(<ExplorerPage />);
            expect(screen.getByTestId('warning-dialog')).toBeInTheDocument();
        });
    });

    describe('Loading State', () => {
        it('shows loading spinner when data is loading', () => {
            (useQuery as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
                data: [],
                isLoading: true,
                error: null,
            });

            renderWithRouter(<ExplorerPage />);
            expect(screen.getByText('Loading...')).toBeInTheDocument();
        });

        it('passes loading state to sidebar', () => {
            (useQuery as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
                data: [],
                isLoading: true,
                error: null,
            });

            renderWithRouter(<ExplorerPage />);
            expect(screen.getByText('Loading sidebar...')).toBeInTheDocument();
        });
    });

    describe('Error State', () => {
        it('displays error message when query fails', () => {
            (useQuery as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
                data: [],
                isLoading: false,
                error: new Error('Network error'),
            });

            renderWithRouter(<ExplorerPage />);
            expect(screen.getByText('Error loading data')).toBeInTheDocument();
            expect(screen.getByText('Network error')).toBeInTheDocument();
        });
    });

    describe('Empty State', () => {
        it('shows empty state when folder has no children', () => {
            (useQuery as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
                data: [],
                isLoading: false,
                error: null,
            });

            renderWithRouter(<ExplorerPage />);
            expect(screen.getByText('This folder is empty')).toBeInTheDocument();
        });

        it('shows root-specific message at root level', () => {
            (useQuery as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
                data: [],
                isLoading: false,
                error: null,
            });

            (useExplorerStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
                ...defaultStoreState,
                currentPath: [],
            });

            renderWithRouter(<ExplorerPage />);
            expect(screen.getByText('Create a department to get started')).toBeInTheDocument();
        });

        it('shows general message when not at root', () => {
            const parentNode: FileSystemNode = { id: 'dept-1', label: 'CS', type: 'department', children: [], parentId: null };

            (useQuery as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
                data: [parentNode],
                isLoading: false,
                error: null,
            });

            (useExplorerStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
                ...defaultStoreState,
                currentPath: [parentNode],
            });

            renderWithRouter(<ExplorerPage />);
            expect(screen.getByText('Right-click to create a new item')).toBeInTheDocument();
        });
    });

    describe('View Modes', () => {
        it('renders GridView when viewMode is grid', () => {
            (useExplorerStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
                ...defaultStoreState,
                viewMode: 'grid',
            });

            renderWithRouter(<ExplorerPage />);
            expect(screen.getByTestId('grid-view')).toBeInTheDocument();
            expect(screen.queryByTestId('list-view')).not.toBeInTheDocument();
        });

        it('renders ListView when viewMode is list', () => {
            (useExplorerStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
                ...defaultStoreState,
                viewMode: 'list',
            });

            renderWithRouter(<ExplorerPage />);
            expect(screen.getByTestId('list-view')).toBeInTheDocument();
            expect(screen.queryByTestId('grid-view')).not.toBeInTheDocument();
        });

        it('passes correct item count to view component', () => {
            renderWithRouter(<ExplorerPage />);
            expect(screen.getByText('Grid: 2 items')).toBeInTheDocument();
        });
    });

    describe('Context Menu', () => {
        it('renders context menu when position is set', () => {
            (useExplorerStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
                ...defaultStoreState,
                contextMenuPosition: { x: 100, y: 200 },
            });

            renderWithRouter(<ExplorerPage />);
            expect(screen.getByTestId('context-menu')).toBeInTheDocument();
        });

        it('does not render context menu when position is null', () => {
            renderWithRouter(<ExplorerPage />);
            expect(screen.queryByTestId('context-menu')).not.toBeInTheDocument();
        });

        it('closes context menu on background click', () => {
            (useExplorerStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
                ...defaultStoreState,
                contextMenuPosition: { x: 100, y: 200 },
            });

            renderWithRouter(<ExplorerPage />);

            const layout = document.querySelector('.explorer-layout');
            if (layout) {
                fireEvent.click(layout);
            }

            expect(mockCloseContextMenu).toHaveBeenCalled();
        });
    });

    describe('Delete Dialog', () => {
        it('renders delete confirmation dialog when open', () => {
            (useExplorerStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
                ...defaultStoreState,
                deleteDialogOpen: true,
                nodeToDelete: { id: '1', type: 'department', label: 'CS' },
            });

            renderWithRouter(<ExplorerPage />);
            expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument();
        });

        it('does not render delete dialog when closed', () => {
            renderWithRouter(<ExplorerPage />);
            expect(screen.queryByTestId('confirm-dialog')).not.toBeInTheDocument();
        });
    });

    describe('Navigation', () => {
        it('displays children of current path node', () => {
            const childNodes: FileSystemNode[] = [
                { id: 'sem-1', label: 'Semester 1', type: 'semester', children: [], parentId: 'dept-1' },
                { id: 'sem-2', label: 'Semester 2', type: 'semester', children: [], parentId: 'dept-1' },
            ];

            const parentNode: FileSystemNode = {
                id: 'dept-1',
                label: 'CS',
                type: 'department',
                children: childNodes,
                parentId: null,
            };

            (useQuery as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
                data: [parentNode],
                isLoading: false,
                error: null,
            });

            (useExplorerStore as unknown as ReturnType<typeof vi.fn>).mockReturnValue({
                ...defaultStoreState,
                currentPath: [parentNode],
            });

            renderWithRouter(<ExplorerPage />);
            expect(screen.getByText('Grid: 2 items')).toBeInTheDocument();
        });

        it('displays root departments when currentPath is empty', () => {
            renderWithRouter(<ExplorerPage />);
            expect(screen.getByText('Grid: 2 items')).toBeInTheDocument();
        });
    });
});
