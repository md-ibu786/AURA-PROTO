/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/react';
import { ListView } from '../ListView';
import { useExplorerStore } from '../../../stores';

// Mock lucide-react icons to avoid import errors
vi.mock('lucide-react', () => ({
    Building2: () => <div data-testid="icon-building2" />,
    Calendar: () => <div data-testid="icon-calendar" />,
    BookOpen: () => <div data-testid="icon-bookopen" />,
    Package: () => <div data-testid="icon-package" />,
    FileText: () => <div data-testid="icon-filetext" />,
    CheckSquare: () => <div data-testid="icon-checksquare" />,
    Square: () => <div data-testid="icon-square" />,
    RotateCcw: () => <div data-testid="icon-rotate" />,
}));

// Mock @tanstack/react-query
vi.mock('@tanstack/react-query', () => ({
    useQueryClient: () => ({
        invalidateQueries: vi.fn(),
    }),
}));

describe('ListView - Selection Constraints', () => {
    const mockToggleSelect = vi.fn();
    const mockSelect = vi.fn();

    // Sample data: notes with KG-ready variants
    const sampleNotes = [
        {
            id: 'note-1',
            label: 'Processed Note',
            type: 'note' as const,
            meta: { kg_status: 'ready' },
            pdfFilename: 'note1.pdf',
        },
        {
            id: 'note-2',
            label: 'Unprocessed Note',
            type: 'note' as const,
            meta: { kg_status: 'pending' },
            pdfFilename: 'note2.pdf',
        },
        {
            id: 'note-3',
            label: 'Failed Note',
            type: 'note' as const,
            meta: { kg_status: 'failed' },
            pdfFilename: 'note3.pdf',
        },
    ];

    beforeEach(() => {
        vi.clearAllMocks();
        useExplorerStore.setState({
            selectedIds: new Set<string>(),
            selectionMode: false,
            deleteMode: false,
            searchQuery: '',
            renamingNodeId: null,
            currentPath: [],
            toggleSelect: mockToggleSelect,
            select: mockSelect,
            rangeSelect: vi.fn(),
            navigateTo: vi.fn(),
            openContextMenu: vi.fn(),
            setRenamingNodeId: vi.fn(),
            openWarningDialog: vi.fn(),
            warningDialog: { isOpen: false, type: 'error', message: '' },
            warningTimeoutId: null,
            items: [],
            expandedFolders: new Set<string>(),
            rootDepartments: [],
            viewMode: 'grid',
            contextMenuPosition: null,
            isDeleteDialogOpen: false,
            deleteTargets: [],
            renamingTargets: [],
        });
    });

    afterEach(() => {
        cleanup();
    });

    describe('Process Mode (deleteMode = false)', () => {
        it('disables KG-ready notes in process mode', () => {
            useExplorerStore.setState({
                selectionMode: true,
                deleteMode: false,
            });

            render(<ListView items={sampleNotes} allItems={sampleNotes} />);

            const processedNoteRow = screen
                .getAllByText('Processed Note')[0]
                ?.closest('.list-row');

            expect(processedNoteRow).toHaveClass('kg-disabled');
        });

        it('enables non-KG-ready notes in process mode', () => {
            useExplorerStore.setState({
                selectionMode: true,
                deleteMode: false,
            });

            render(<ListView items={sampleNotes} allItems={sampleNotes} />);

            const unprocessedNoteRow = screen
                .getAllByText('Unprocessed Note')[0]
                ?.closest('.list-row');

            expect(unprocessedNoteRow).not.toHaveClass('kg-disabled');
        });

        it('shows correct tooltip for disabled items', () => {
            useExplorerStore.setState({
                selectionMode: true,
                deleteMode: false,
            });

            render(<ListView items={sampleNotes} allItems={sampleNotes} />);

            const processedNoteRow = screen
                .getAllByText('Processed Note')[0]
                ?.closest('.list-row');

            expect(processedNoteRow).toHaveAttribute(
                'title',
                expect.stringContaining('Already processed')
            );
        });

        it('clicking disabled note does not trigger toggleSelect', () => {
            useExplorerStore.setState({
                selectionMode: true,
                deleteMode: false,
            });

            render(<ListView items={sampleNotes} allItems={sampleNotes} />);

            const processedNoteRow = screen
                .getAllByText('Processed Note')[0]
                ?.closest('.list-row') as HTMLElement;

            fireEvent.click(processedNoteRow);

            expect(mockToggleSelect).not.toHaveBeenCalledWith('note-1');
        });

        it('clicking enabled note triggers toggleSelect', () => {
            useExplorerStore.setState({
                selectionMode: true,
                deleteMode: false,
            });

            render(<ListView items={sampleNotes} allItems={sampleNotes} />);

            const unprocessedNoteRow = screen
                .getAllByText('Unprocessed Note')[0]
                ?.closest('.list-row') as HTMLElement;

            fireEvent.click(unprocessedNoteRow);

            expect(mockToggleSelect).toHaveBeenCalledWith('note-2');
        });
    });

    describe('Delete Mode (deleteMode = true)', () => {
        it('enables KG-ready notes in delete mode', () => {
            useExplorerStore.setState({
                selectionMode: true,
                deleteMode: true,
            });

            render(<ListView items={sampleNotes} allItems={sampleNotes} />);

            const processedNoteRow = screen
                .getAllByText('Processed Note')[0]
                ?.closest('.list-row');

            expect(processedNoteRow).not.toHaveClass('kg-disabled');
        });

        it('disables non-KG-ready notes in delete mode', () => {
            useExplorerStore.setState({
                selectionMode: true,
                deleteMode: true,
            });

            render(<ListView items={sampleNotes} allItems={sampleNotes} />);

            const unprocessedNoteRow = screen
                .getAllByText('Unprocessed Note')[0]
                ?.closest('.list-row');

            expect(unprocessedNoteRow).toHaveClass('kg-disabled');
        });

        it('shows correct tooltip for disabled items in delete mode', () => {
            useExplorerStore.setState({
                selectionMode: true,
                deleteMode: true,
            });

            render(<ListView items={sampleNotes} allItems={sampleNotes} />);

            const unprocessedNoteRow = screen
                .getAllByText('Unprocessed Note')[0]
                ?.closest('.list-row');

            expect(unprocessedNoteRow).toHaveAttribute(
                'title',
                expect.stringContaining('Not processed')
            );
        });

        it('clicking disabled note in delete mode does not trigger toggleSelect', () => {
            useExplorerStore.setState({
                selectionMode: true,
                deleteMode: true,
            });

            render(<ListView items={sampleNotes} allItems={sampleNotes} />);

            const unprocessedNoteRow = screen
                .getAllByText('Unprocessed Note')[0]
                ?.closest('.list-row') as HTMLElement;

            fireEvent.click(unprocessedNoteRow);

            expect(mockToggleSelect).not.toHaveBeenCalledWith('note-2');
        });

        it('clicking enabled note in delete mode triggers toggleSelect', () => {
            useExplorerStore.setState({
                selectionMode: true,
                deleteMode: true,
            });

            render(<ListView items={sampleNotes} allItems={sampleNotes} />);

            const processedNoteRow = screen
                .getAllByText('Processed Note')[0]
                ?.closest('.list-row') as HTMLElement;

            fireEvent.click(processedNoteRow);

            expect(mockToggleSelect).toHaveBeenCalledWith('note-1');
        });
    });

    describe('Visual Indicators', () => {
        it('shows kg-disabled CSS class for disabled items', () => {
            useExplorerStore.setState({
                selectionMode: true,
                deleteMode: false,
            });

            render(<ListView items={sampleNotes} allItems={sampleNotes} />);

            const processedNoteRow = screen
                .getAllByText('Processed Note')[0]
                ?.closest('.list-row');

            expect(processedNoteRow?.className).toMatch(/kg-disabled/);
        });

        it('does not show kg-disabled class for enabled items', () => {
            useExplorerStore.setState({
                selectionMode: true,
                deleteMode: false,
            });

            render(<ListView items={sampleNotes} allItems={sampleNotes} />);

            const unprocessedNoteRow = screen
                .getAllByText('Unprocessed Note')[0]
                ?.closest('.list-row');

            expect(unprocessedNoteRow?.className).not.toMatch(/kg-disabled/);
        });
    });

    describe('Non-Selection Mode', () => {
        it('allows selection in non-selection mode regardless of KG status', () => {
            useExplorerStore.setState({
                selectionMode: false,
                deleteMode: false,
            });

            render(<ListView items={sampleNotes} allItems={sampleNotes} />);

            const processedNoteRow = screen
                .getAllByText('Processed Note')[0]
                ?.closest('.list-row') as HTMLElement;

            fireEvent.click(processedNoteRow);

            expect(mockSelect).toHaveBeenCalledWith('note-1');
        });

        it('does not show kg-disabled class in non-selection mode', () => {
            useExplorerStore.setState({
                selectionMode: false,
                deleteMode: false,
            });

            render(<ListView items={sampleNotes} allItems={sampleNotes} />);

            const processedNoteRow = screen
                .getAllByText('Processed Note')[0]
                ?.closest('.list-row');

            expect(processedNoteRow).not.toHaveClass('kg-disabled');
        });
    });

    describe('Edge Cases', () => {
        it('handles empty items list', () => {
            useExplorerStore.setState({
                selectionMode: true,
                deleteMode: false,
            });

            const { container } = render(
                <ListView items={[]} allItems={[]} />
            );

            expect(container.querySelector('.list-view')).toBeInTheDocument();
        });

        it('handles items without kg_status metadata', () => {
            useExplorerStore.setState({
                selectionMode: true,
                deleteMode: false,
            });

            const itemsNoMeta = sampleNotes.map((item) => ({
                ...item,
                meta: {},
            }));

            render(<ListView items={itemsNoMeta} allItems={itemsNoMeta} />);

            expect(screen.getByText('Processed Note')).toBeInTheDocument();
        });
    });
});
