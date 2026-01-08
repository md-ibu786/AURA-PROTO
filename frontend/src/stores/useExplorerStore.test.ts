import { describe, it, expect, beforeEach } from 'vitest';
import { useExplorerStore } from './useExplorerStore';
import { act } from 'react';

describe('useExplorerStore', () => {
    beforeEach(() => {
        useExplorerStore.setState({
            currentPath: [],
            activeNodeId: null,
            selectedIds: new Set(),
            deleteDialogOpen: false,
            nodeToDelete: null,
            renamingNodeId: null,
            creatingNodeType: null,
            creatingParentId: null,
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
});
