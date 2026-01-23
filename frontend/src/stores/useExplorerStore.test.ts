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

    // ============================================================================
    // Additional Store Tests (completing 23 missing tests)
    // ============================================================================

    describe('Active Node Actions', () => {
        it('should set active node', () => {
            const node: FileSystemNode = { id: 'dept-1', name: 'CS', type: 'department', children: [] };

            act(() => {
                useExplorerStore.getState().setActiveNode(node);
            });

            expect(useExplorerStore.getState().activeNodeId).toBe('dept-1');
        });

        it('should clear active node when null is passed', () => {
            useExplorerStore.setState({ activeNodeId: 'dept-1' });

            act(() => {
                useExplorerStore.getState().setActiveNode(null);
            });

            expect(useExplorerStore.getState().activeNodeId).toBeNull();
        });

        it('should only set active node without affecting selection', () => {
            const node: FileSystemNode = { id: 'dept-1', name: 'CS', type: 'department', children: [] };
            useExplorerStore.setState({
                selectedIds: new Set(['item-1', 'item-2']),
                lastSelectedId: 'item-2',
            });

            act(() => {
                useExplorerStore.getState().setActiveNode(node);
            });

            const state = useExplorerStore.getState();
            expect(state.activeNodeId).toBe('dept-1');
            // setActiveNode does NOT clear selections (only navigateTo does)
            expect(state.selectedIds.size).toBe(2);
        });
    });

    describe('Multi-Select Edge Cases', () => {
        it('should handle toggle when nothing was previously selected', () => {
            useExplorerStore.setState({ selectedIds: new Set(), lastSelectedId: null });

            act(() => {
                useExplorerStore.getState().toggleSelect('new-item');
            });

            const state = useExplorerStore.getState();
            expect(state.selectedIds.has('new-item')).toBe(true);
            expect(state.lastSelectedId).toBe('new-item');
        });

        it('should preserve existing selections during toggle', () => {
            useExplorerStore.setState({
                selectedIds: new Set(['existing-1', 'existing-2']),
                lastSelectedId: 'existing-2',
            });

            act(() => {
                useExplorerStore.getState().toggleSelect('new-item');
            });

            const state = useExplorerStore.getState();
            expect(state.selectedIds.has('existing-1')).toBe(true);
            expect(state.selectedIds.has('existing-2')).toBe(true);
            expect(state.selectedIds.has('new-item')).toBe(true);
            expect(state.selectedIds.size).toBe(3);
        });

        it('should handle range select with no previous selection', () => {
            useExplorerStore.setState({ lastSelectedId: null, selectedIds: new Set() });

            act(() => {
                useExplorerStore.getState().rangeSelect('c', ['a', 'b', 'c', 'd', 'e']);
            });

            const state = useExplorerStore.getState();
            expect(state.selectedIds.has('c')).toBe(true);
            expect(state.selectedIds.size).toBe(1);
        });

        it('should handle range select when lastSelectedId not in allIds', () => {
            useExplorerStore.setState({
                lastSelectedId: 'not-in-list',
                selectedIds: new Set(['not-in-list']),
            });

            act(() => {
                useExplorerStore.getState().rangeSelect('c', ['a', 'b', 'c', 'd', 'e']);
            });

            const state = useExplorerStore.getState();
            expect(state.selectedIds.has('c')).toBe(true);
            expect(state.selectedIds.size).toBe(1);
        });

        it('should select all in correct order', () => {
            const ids = ['z', 'a', 'm'];

            act(() => {
                useExplorerStore.getState().selectAll(ids);
            });

            const state = useExplorerStore.getState();
            expect(state.selectedIds.has('z')).toBe(true);
            expect(state.selectedIds.has('a')).toBe(true);
            expect(state.selectedIds.has('m')).toBe(true);
            expect(state.lastSelectedId).toBe('m'); // Last in array
        });

        it('should handle empty selectAll call', () => {
            act(() => {
                useExplorerStore.getState().selectAll([]);
            });

            const state = useExplorerStore.getState();
            expect(state.selectedIds.size).toBe(0);
            expect(state.lastSelectedId).toBeNull();
        });
    });

    describe('Tree Expansion Edge Cases', () => {
        it('should handle expand on already expanded node', () => {
            useExplorerStore.setState({ expandedIds: new Set(['node-1']) });

            act(() => {
                useExplorerStore.getState().expand('node-1');
            });

            expect(useExplorerStore.getState().expandedIds.has('node-1')).toBe(true);
        });

        it('should handle collapse on already collapsed node', () => {
            useExplorerStore.setState({ expandedIds: new Set() });

            act(() => {
                useExplorerStore.getState().collapse('node-1');
            });

            expect(useExplorerStore.getState().expandedIds.has('node-1')).toBe(false);
        });

        it('should toggle expand from expanded to collapsed', () => {
            useExplorerStore.setState({ expandedIds: new Set(['node-1']) });

            act(() => {
                useExplorerStore.getState().toggleExpand('node-1');
            });

            expect(useExplorerStore.getState().expandedIds.has('node-1')).toBe(false);
        });

        it('should toggle expand from collapsed to expanded', () => {
            useExplorerStore.setState({ expandedIds: new Set() });

            act(() => {
                useExplorerStore.getState().toggleExpand('node-1');
            });

            expect(useExplorerStore.getState().expandedIds.has('node-1')).toBe(true);
        });

        it('should expand multiple nodes independently', () => {
            act(() => {
                useExplorerStore.getState().expand('node-1');
                useExplorerStore.getState().expand('node-2');
                useExplorerStore.getState().expand('node-3');
            });

            const state = useExplorerStore.getState();
            expect(state.expandedIds.has('node-1')).toBe(true);
            expect(state.expandedIds.has('node-2')).toBe(true);
            expect(state.expandedIds.has('node-3')).toBe(true);
            expect(state.expandedIds.size).toBe(3);
        });
    });

    describe('Clipboard Edge Cases', () => {
        it('should handle cut mode', () => {
            act(() => {
                useExplorerStore.getState().setClipboard(['item-1', 'item-2'], 'cut');
            });

            const state = useExplorerStore.getState();
            expect(state.clipboard.nodeIds).toEqual(['item-1', 'item-2']);
            expect(state.clipboard.mode).toBe('cut');
        });

        it('should handle copy mode', () => {
            act(() => {
                useExplorerStore.getState().setClipboard(['item-1'], 'copy');
            });

            const state = useExplorerStore.getState();
            expect(state.clipboard.nodeIds).toEqual(['item-1']);
            expect(state.clipboard.mode).toBe('copy');
        });

        it('should replace clipboard contents on new set', () => {
            useExplorerStore.setState({
                clipboard: { nodeIds: ['old-1'], mode: 'copy' }
            });

            act(() => {
                useExplorerStore.getState().setClipboard(['new-1', 'new-2'], 'cut');
            });

            const state = useExplorerStore.getState();
            expect(state.clipboard.nodeIds).toEqual(['new-1', 'new-2']);
            expect(state.clipboard.mode).toBe('cut');
        });
    });

    describe('Dialog State Edge Cases', () => {
        it('should clear context menu when delete dialog opens', () => {
            useExplorerStore.setState({
                contextMenuPosition: { x: 100, y: 200 },
                contextMenuNodeId: 'node-1',
            });

            const node = { id: '1', type: 'department' as const, label: 'CS' };
            act(() => {
                useExplorerStore.getState().openDeleteDialog(node);
            });

            const state = useExplorerStore.getState();
            expect(state.deleteDialogOpen).toBe(true);
            expect(state.contextMenuPosition).toBeNull();
            expect(state.contextMenuNodeId).toBeNull();
        });

        it('should handle opening process dialog multiple times', () => {
            act(() => {
                useExplorerStore.getState().openProcessDialog(['file-1'], 'mod-1');
            });

            act(() => {
                useExplorerStore.getState().openProcessDialog(['file-2', 'file-3'], 'mod-2');
            });

            const state = useExplorerStore.getState();
            expect(state.processDialog.open).toBe(true);
            expect(state.processDialog.fileIds).toEqual(['file-2', 'file-3']);
            expect(state.processDialog.moduleId).toBe('mod-2');
        });
    });

    // ============================================================================
    // warningTimeoutId Tests (critical missing tests)
    // ============================================================================

    describe('Warning Timeout Tests', () => {
        beforeEach(() => {
            vi.useFakeTimers();
        });

        afterEach(() => {
            vi.useRealTimers();
        });

        it('should have null warningTimeoutId initially', () => {
            const state = useExplorerStore.getState();
            expect(state.warningTimeoutId).toBeNull();
        });

        it('should set warningTimeoutId when opening warning dialog', () => {
            act(() => {
                useExplorerStore.getState().openWarningDialog('error', 'Test message');
            });

            const state = useExplorerStore.getState();
            expect(state.warningTimeoutId).not.toBeNull();
            expect(state.warningDialog.isOpen).toBe(true);
        });

        it('should clear warningTimeoutId when closing warning dialog', () => {
            act(() => {
                useExplorerStore.getState().openWarningDialog('error', 'Test message');
            });

            const timeoutId = useExplorerStore.getState().warningTimeoutId;
            expect(timeoutId).not.toBeNull();

            act(() => {
                useExplorerStore.getState().closeWarningDialog();
            });

            const state = useExplorerStore.getState();
            expect(state.warningTimeoutId).toBeNull();
            expect(state.warningDialog.isOpen).toBe(false);
        });

        it('should clear existing timeout when opening new warning', () => {
            act(() => {
                useExplorerStore.getState().openWarningDialog('error', 'First message');
            });

            const firstTimeoutId = useExplorerStore.getState().warningTimeoutId;

            act(() => {
                useExplorerStore.getState().openWarningDialog('duplicate', 'Second message');
            });

            const secondTimeoutId = useExplorerStore.getState().warningTimeoutId;
            // Should be a different timeout ID
            expect(secondTimeoutId).not.toBe(firstTimeoutId);
            expect(secondTimeoutId).not.toBeNull();
        });

        it('should clear timeout on unmount equivalent (via closeWarningDialog)', () => {
            act(() => {
                useExplorerStore.getState().openWarningDialog('error', 'Test message');
            });

            const timeoutId = useExplorerStore.getState().warningTimeoutId;
            const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout');

            act(() => {
                useExplorerStore.getState().closeWarningDialog();
            });

            expect(clearTimeoutSpy).toHaveBeenCalledWith(timeoutId);
            clearTimeoutSpy.mockRestore();
        });

        it('should auto-close warning dialog after 5 seconds', () => {
            act(() => {
                useExplorerStore.getState().openWarningDialog('error', 'Auto-close message');
            });

            expect(useExplorerStore.getState().warningDialog.isOpen).toBe(true);

            // Fast-forward time by 5 seconds
            act(() => {
                vi.advanceTimersByTime(5000);
            });

            const state = useExplorerStore.getState();
            expect(state.warningDialog.isOpen).toBe(false);
            expect(state.warningTimeoutId).toBeNull();
        });

        it('should clear timeout if it exists before setting new one', () => {
            act(() => {
                useExplorerStore.getState().openWarningDialog('error', 'First');
            });

            const firstTimeoutId = useExplorerStore.getState().warningTimeoutId;
            const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout');

            act(() => {
                useExplorerStore.getState().openWarningDialog('error', 'Second');
            });

            expect(clearTimeoutSpy).toHaveBeenCalledWith(firstTimeoutId);
            clearTimeoutSpy.mockRestore();
        });

        it('should handle closeWarningDialog when no timeout is set', () => {
            useExplorerStore.setState({ warningTimeoutId: null });

            const clearTimeoutSpy = vi.spyOn(global, 'clearTimeout');

            act(() => {
                useExplorerStore.getState().closeWarningDialog();
            });

            // Should not call clearTimeout when timeoutId is null
            expect(clearTimeoutSpy).not.toHaveBeenCalled();
            clearTimeoutSpy.mockRestore();
        });
    });

    // ============================================================================
    // KG Polling Tests
    // ============================================================================

    describe('KG Polling Tests', () => {
        it('should have initial polling state as false', () => {
            const state = useExplorerStore.getState();
            expect(state.kgPolling.moduleId).toBeNull();
            expect(state.kgPolling.isPolling).toBe(false);
        });

        it('should set polling state correctly', () => {
            act(() => {
                useExplorerStore.getState().setKGPolling('mod-123', true);
            });

            const state = useExplorerStore.getState();
            expect(state.kgPolling.moduleId).toBe('mod-123');
            expect(state.kgPolling.isPolling).toBe(true);
        });

        it('should stop polling when set to false', () => {
            useExplorerStore.setState({
                kgPolling: { moduleId: 'mod-123', isPolling: true }
            });

            act(() => {
                useExplorerStore.getState().setKGPolling('mod-123', false);
            });

            const state = useExplorerStore.getState();
            expect(state.kgPolling.isPolling).toBe(false);
        });

        it('should clear moduleId when polling is stopped', () => {
            useExplorerStore.setState({
                kgPolling: { moduleId: 'mod-123', isPolling: true }
            });

            act(() => {
                useExplorerStore.getState().setKGPolling(null, false);
            });

            const state = useExplorerStore.getState();
            expect(state.kgPolling.moduleId).toBeNull();
            expect(state.kgPolling.isPolling).toBe(false);
        });
    });
});
