/**
 * ============================================================================
 * FILE: useExplorerStore.test.ts
 * LOCATION: frontend/src/stores/useExplorerStore.test.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Unit tests for useExplorerStore Zustand store. Tests all state
 *    management actions including selection, navigation, view mode,
 *    clipboard, context menu, dialogs, and KG processing state.
 *
 * TEST COVERAGE:
 *    - Initial state verification
 *    - Selection actions (select, toggle, range, clear, selectAll)
 *    - Navigation actions
 *    - View mode and search query
 *    - Clipboard operations
 *    - Context menu state
 *    - Delete/Warning dialog management
 *    - KG process dialog state
 *
 * @see: useExplorerStore.ts - Store under test
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useExplorerStore } from './useExplorerStore';
import { act } from 'react';
import type { FileSystemNode } from '../types';

describe('useExplorerStore', () => {
    beforeEach(() => {
        useExplorerStore.setState({
            currentPath: [],
            activeNodeId: null,
            selectedIds: new Set(),
            lastSelectedId: null,
            expandedIds: new Set(),
            viewMode: 'grid',
            searchQuery: '',
            clipboard: { nodeIds: [], mode: null },
            contextMenuPosition: null,
            contextMenuNodeId: null,
            deleteDialogOpen: false,
            nodeToDelete: null,
            renamingNodeId: null,
            creatingNodeType: null,
            creatingParentId: null,
            selectionMode: false,
            kgPolling: { moduleId: null, isPolling: false },
            processDialog: { open: false, fileIds: [], moduleId: '' },
            warningDialog: { isOpen: false, type: 'error', message: '' },
            warningTimeoutId: null,
        });
    });

    describe('Initial State', () => {
        it('has correct initial values', () => {
            const state = useExplorerStore.getState();
            expect(state.currentPath).toEqual([]);
            expect(state.activeNodeId).toBeNull();
            expect(state.selectedIds.size).toBe(0);
            expect(state.viewMode).toBe('grid');
            expect(state.searchQuery).toBe('');
            expect(state.selectionMode).toBe(false);
        });
    });

    describe('Delete Dialog Actions', () => {
        it('should open delete dialog and set node to delete', () => {
            const node = { id: '1', type: 'department' as const, label: 'CS' };
            
            act(() => {
                useExplorerStore.getState().openDeleteDialog(node);
            });

            const state = useExplorerStore.getState();
            expect(state.deleteDialogOpen).toBe(true);
            expect(state.nodeToDelete).toEqual(node);
        });

        it('should close delete dialog and clear node to delete', () => {
            const node = { id: '1', type: 'department' as const, label: 'CS' };
            useExplorerStore.setState({ deleteDialogOpen: true, nodeToDelete: node });

            act(() => {
                useExplorerStore.getState().closeDeleteDialog();
            });

            const state = useExplorerStore.getState();
            expect(state.deleteDialogOpen).toBe(false);
            expect(state.nodeToDelete).toBeNull();
        });
    });

    describe('Rename Actions', () => {
        it('should set renaming node id', () => {
            act(() => {
                useExplorerStore.getState().setRenamingNodeId('123');
            });

            expect(useExplorerStore.getState().renamingNodeId).toBe('123');
        });

        it('should clear renaming node id', () => {
            useExplorerStore.setState({ renamingNodeId: '123' });

            act(() => {
                useExplorerStore.getState().setRenamingNodeId(null);
            });

            expect(useExplorerStore.getState().renamingNodeId).toBeNull();
        });
    });

    describe('Inline Creation Actions', () => {
        it('should start creating with type and parent id', () => {
            act(() => {
                useExplorerStore.getState().startCreating('semester', 'dept-1');
            });

            const state = useExplorerStore.getState();
            expect(state.creatingNodeType).toBe('semester');
            expect(state.creatingParentId).toBe('dept-1');
        });

        it('should cancel creating', () => {
            useExplorerStore.setState({ creatingNodeType: 'semester', creatingParentId: 'dept-1' });

            act(() => {
                useExplorerStore.getState().cancelCreating();
            });

            const state = useExplorerStore.getState();
            expect(state.creatingNodeType).toBeNull();
            expect(state.creatingParentId).toBeNull();
        });
    });

    describe('Warning Dialog Actions', () => {
        it('should open warning dialog with type and message', () => {
            act(() => {
                useExplorerStore.getState().openWarningDialog('duplicate', 'Name exists', 'Dept A');
            });

            const state = useExplorerStore.getState();
            expect(state.warningDialog.isOpen).toBe(true);
            expect(state.warningDialog.type).toBe('duplicate');
            expect(state.warningDialog.message).toBe('Name exists');
            expect(state.warningDialog.entityName).toBe('Dept A');
        });

        it('should close warning dialog', () => {
            useExplorerStore.setState({
                warningDialog: {
                    isOpen: true,
                    type: 'duplicate',
                    message: 'Name exists'
                }
            });

            act(() => {
                useExplorerStore.getState().closeWarningDialog();
            });

            const state = useExplorerStore.getState();
            expect(state.warningDialog.isOpen).toBe(false);
        });
    });

    describe('Selection Actions', () => {
        it('should select a single item', () => {
            act(() => {
                useExplorerStore.getState().select('item-1');
            });

            const state = useExplorerStore.getState();
            expect(state.selectedIds.has('item-1')).toBe(true);
            expect(state.selectedIds.size).toBe(1);
            expect(state.lastSelectedId).toBe('item-1');
        });

        it('should toggle selection on and off', () => {
            act(() => {
                useExplorerStore.getState().toggleSelect('item-1');
            });
            expect(useExplorerStore.getState().selectedIds.has('item-1')).toBe(true);

            act(() => {
                useExplorerStore.getState().toggleSelect('item-1');
            });
            expect(useExplorerStore.getState().selectedIds.has('item-1')).toBe(false);
        });

        it('should clear all selections', () => {
            useExplorerStore.setState({
                selectedIds: new Set(['item-1', 'item-2', 'item-3']),
                lastSelectedId: 'item-3'
            });

            act(() => {
                useExplorerStore.getState().clearSelection();
            });

            const state = useExplorerStore.getState();
            expect(state.selectedIds.size).toBe(0);
            expect(state.lastSelectedId).toBeNull();
        });

        it('should select all provided ids', () => {
            const ids = ['item-1', 'item-2', 'item-3'];
            
            act(() => {
                useExplorerStore.getState().selectAll(ids);
            });

            const state = useExplorerStore.getState();
            expect(state.selectedIds.size).toBe(3);
            expect(state.lastSelectedId).toBe('item-3');
        });

        it('should perform range selection', () => {
            const allIds = ['a', 'b', 'c', 'd', 'e'];
            useExplorerStore.setState({ lastSelectedId: 'b' });

            act(() => {
                useExplorerStore.getState().rangeSelect('d', allIds);
            });

            const state = useExplorerStore.getState();
            expect(state.selectedIds.has('b')).toBe(true);
            expect(state.selectedIds.has('c')).toBe(true);
            expect(state.selectedIds.has('d')).toBe(true);
        });
    });

    describe('View Mode Actions', () => {
        it('should set view mode to list', () => {
            act(() => {
                useExplorerStore.getState().setViewMode('list');
            });

            expect(useExplorerStore.getState().viewMode).toBe('list');
        });

        it('should update search query', () => {
            act(() => {
                useExplorerStore.getState().setSearchQuery('test query');
            });

            expect(useExplorerStore.getState().searchQuery).toBe('test query');
        });
    });

    describe('Clipboard Actions', () => {
        it('should set clipboard with copy mode', () => {
            act(() => {
                useExplorerStore.getState().setClipboard(['item-1', 'item-2'], 'copy');
            });

            const state = useExplorerStore.getState();
            expect(state.clipboard.nodeIds).toEqual(['item-1', 'item-2']);
            expect(state.clipboard.mode).toBe('copy');
        });

        it('should clear clipboard', () => {
            useExplorerStore.setState({
                clipboard: { nodeIds: ['item-1'], mode: 'cut' }
            });

            act(() => {
                useExplorerStore.getState().clearClipboard();
            });

            const state = useExplorerStore.getState();
            expect(state.clipboard.nodeIds).toEqual([]);
            expect(state.clipboard.mode).toBeNull();
        });
    });

    describe('Context Menu Actions', () => {
        it('should open context menu at position', () => {
            act(() => {
                useExplorerStore.getState().openContextMenu(100, 200, 'node-1');
            });

            const state = useExplorerStore.getState();
            expect(state.contextMenuPosition).toEqual({ x: 100, y: 200 });
            expect(state.contextMenuNodeId).toBe('node-1');
        });

        it('should close context menu', () => {
            useExplorerStore.setState({
                contextMenuPosition: { x: 100, y: 200 },
                contextMenuNodeId: 'node-1'
            });

            act(() => {
                useExplorerStore.getState().closeContextMenu();
            });

            const state = useExplorerStore.getState();
            expect(state.contextMenuPosition).toBeNull();
            expect(state.contextMenuNodeId).toBeNull();
        });
    });

    describe('KG Process Dialog Actions', () => {
        it('should open process dialog with file ids and module id', () => {
            act(() => {
                useExplorerStore.getState().openProcessDialog(['file-1', 'file-2'], 'mod-123');
            });

            const state = useExplorerStore.getState();
            expect(state.processDialog.open).toBe(true);
            expect(state.processDialog.fileIds).toEqual(['file-1', 'file-2']);
            expect(state.processDialog.moduleId).toBe('mod-123');
        });

        it('should close process dialog', () => {
            useExplorerStore.setState({
                processDialog: { open: true, fileIds: ['file-1'], moduleId: 'mod-1' }
            });

            act(() => {
                useExplorerStore.getState().closeProcessDialog();
            });

            const state = useExplorerStore.getState();
            expect(state.processDialog.open).toBe(false);
            expect(state.processDialog.fileIds).toEqual([]);
        });

        it('should set KG polling state', () => {
            act(() => {
                useExplorerStore.getState().setKGPolling('mod-123', true);
            });

            const state = useExplorerStore.getState();
            expect(state.kgPolling.moduleId).toBe('mod-123');
            expect(state.kgPolling.isPolling).toBe(true);
        });

        it('should toggle selection mode', () => {
            act(() => {
                useExplorerStore.getState().setSelectionMode(true);
            });

            expect(useExplorerStore.getState().selectionMode).toBe(true);

            act(() => {
                useExplorerStore.getState().setSelectionMode(false);
            });

            expect(useExplorerStore.getState().selectionMode).toBe(false);
        });
    });

    describe('Tree Expansion Actions', () => {
        it('should expand a node', () => {
            act(() => {
                useExplorerStore.getState().expand('node-1');
            });

            expect(useExplorerStore.getState().expandedIds.has('node-1')).toBe(true);
        });

        it('should collapse a node', () => {
            useExplorerStore.setState({ expandedIds: new Set(['node-1', 'node-2']) });

            act(() => {
                useExplorerStore.getState().collapse('node-1');
            });

            const state = useExplorerStore.getState();
            expect(state.expandedIds.has('node-1')).toBe(false);
            expect(state.expandedIds.has('node-2')).toBe(true);
        });

        it('should toggle expand state', () => {
            act(() => {
                useExplorerStore.getState().toggleExpand('node-1');
            });
            expect(useExplorerStore.getState().expandedIds.has('node-1')).toBe(true);

            act(() => {
                useExplorerStore.getState().toggleExpand('node-1');
            });
            expect(useExplorerStore.getState().expandedIds.has('node-1')).toBe(false);
        });
    });

    describe('Navigation Actions', () => {
        it('should set current path', () => {
            const path: FileSystemNode[] = [
                { id: 'dept-1', name: 'CS', type: 'department', children: [] }
            ];

            act(() => {
                useExplorerStore.getState().setCurrentPath(path);
            });

            expect(useExplorerStore.getState().currentPath).toEqual(path);
        });

        it('should navigate to node with ancestors', () => {
            const parent: FileSystemNode = { id: 'dept-1', name: 'CS', type: 'department', children: [] };
            const child: FileSystemNode = { id: 'sem-1', name: 'Sem 1', type: 'semester', children: [] };

            act(() => {
                useExplorerStore.getState().navigateTo(child, [parent]);
            });

            const state = useExplorerStore.getState();
            expect(state.currentPath).toEqual([parent, child]);
            expect(state.activeNodeId).toBe('sem-1');
            expect(state.selectedIds.size).toBe(0);
        });

        it('should navigate up one level', () => {
            const grandparent: FileSystemNode = { id: 'dept-1', name: 'CS', type: 'department', children: [] };
            const parent: FileSystemNode = { id: 'sem-1', name: 'Sem 1', type: 'semester', children: [] };
            
            useExplorerStore.setState({
                currentPath: [grandparent, parent],
                activeNodeId: 'sem-1'
            });

            act(() => {
                useExplorerStore.getState().navigateUp();
            });

            const state = useExplorerStore.getState();
            expect(state.currentPath).toEqual([grandparent]);
            expect(state.activeNodeId).toBe('dept-1');
        });

        it('should navigate to root when at first level', () => {
            const node: FileSystemNode = { id: 'dept-1', name: 'CS', type: 'department', children: [] };
            
            useExplorerStore.setState({
                currentPath: [node],
                activeNodeId: 'dept-1'
            });

            act(() => {
                useExplorerStore.getState().navigateUp();
            });

            const state = useExplorerStore.getState();
            expect(state.currentPath).toEqual([]);
            expect(state.activeNodeId).toBeNull();
        });
    });
});
