/**
 * ============================================================================
 * FILE: StateSync.test.tsx
 * LOCATION: frontend/src/integration/StateSync.test.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Unit tests for Zustand store state synchronization in the explorer.
 *
 * ROLE IN PROJECT:
 *    Tests explorer store navigation actions including navigateTo, navigateUp,
 *    and state synchronization. Ensures currentPath and activeNodeId are
 *    correctly managed when traversing the hierarchy tree using Vitest.
 *
 * KEY COMPONENTS:
 *    - StateSync tests: Store behavior verification suite
 *    - useExplorerStore: Zustand store under test
 *    - FileSystemNode: Type definitions for tree nodes
 *
 * DEPENDENCIES:
 *    - External: vitest
 *    - Internal: @/stores, @/types
 *
 * USAGE:
 *    npm test -- StateSync.test.tsx
 * ============================================================================
 */

/**
 * @vitest-environment jsdom
 */
import { describe, it, expect, beforeEach } from 'vitest';
import { useExplorerStore } from '../stores';
import type { FileSystemNode } from '../types';

describe('Explorer State Synchronization', () => {
    beforeEach(() => {
        useExplorerStore.setState({
            currentPath: [],
            activeNodeId: null,
            selectedIds: new Set(),
            expandedIds: new Set(),
        });
    });

    it('should update currentPath and activeNodeId when navigating', () => {
        const dept: FileSystemNode = { id: 'dept-1', type: 'department', label: 'CS', parentId: null };
        const ancestors: FileSystemNode[] = [];

        useExplorerStore.getState().navigateTo(dept, ancestors);

        const state = useExplorerStore.getState();
        expect(state.currentPath).toEqual([dept]);
        expect(state.activeNodeId).toBe('dept-1');
    });

    it('should navigate up correctly', () => {
        const dept: FileSystemNode = { id: 'dept-1', type: 'department', label: 'CS', parentId: null };
        const sem: FileSystemNode = { id: 'sem-1', type: 'semester', label: 'Sem 1', parentId: 'dept-1' };

        useExplorerStore.setState({
            currentPath: [dept, sem],
            activeNodeId: 'sem-1'
        });

        useExplorerStore.getState().navigateUp();

        const state = useExplorerStore.getState();
        expect(state.currentPath).toEqual([dept]);
        expect(state.activeNodeId).toBe('dept-1');
    });

    it('should go to root when navigating up from top level', () => {
        const dept: FileSystemNode = { id: 'dept-1', type: 'department', label: 'CS', parentId: null };

        useExplorerStore.setState({
            currentPath: [dept],
            activeNodeId: 'dept-1'
        });

        useExplorerStore.getState().navigateUp();

        const state = useExplorerStore.getState();
        expect(state.currentPath).toEqual([]);
        expect(state.activeNodeId).toBeNull();
    });
});
