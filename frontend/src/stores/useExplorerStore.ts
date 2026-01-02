/**
 * Explorer Store using Zustand
 * Manages UI state for the file explorer
 */
import { create } from 'zustand';
import type { FileSystemNode, HierarchyType } from '../types';

export type ViewMode = 'grid' | 'list';

interface ClipboardState {
    nodeIds: string[];
    mode: 'cut' | 'copy' | null;
}

interface ExplorerState {
    // Navigation
    currentPath: FileSystemNode[];
    activeNodeId: string | null;

    // Selection
    selectedIds: Set<string>;
    lastSelectedId: string | null;

    // Tree state
    expandedIds: Set<string>;

    // View
    viewMode: ViewMode;
    searchQuery: string;

    // Clipboard
    clipboard: ClipboardState;

    // Context menu
    contextMenuPosition: { x: number; y: number } | null;
    contextMenuNodeId: string | null;
    renamingNodeId: string | null;

    // Inline creation
    creatingNodeType: HierarchyType | null;
    creatingParentId: number | null;

    // Actions
    setActiveNode: (node: FileSystemNode | null) => void;
    setCurrentPath: (path: FileSystemNode[]) => void;
    navigateTo: (node: FileSystemNode, ancestors: FileSystemNode[]) => void;
    navigateUp: () => void;

    // Selection actions
    select: (id: string) => void;
    toggleSelect: (id: string) => void;
    rangeSelect: (id: string, allIds: string[]) => void;
    clearSelection: () => void;
    selectAll: (ids: string[]) => void;

    // Tree actions
    expand: (id: string) => void;
    collapse: (id: string) => void;
    toggleExpand: (id: string) => void;

    // View actions
    setViewMode: (mode: ViewMode) => void;
    setSearchQuery: (query: string) => void;

    // Clipboard actions
    setClipboard: (nodeIds: string[], mode: 'cut' | 'copy') => void;
    clearClipboard: () => void;

    // Context menu actions
    openContextMenu: (x: number, y: number, nodeId: string) => void;
    closeContextMenu: () => void;

    // Rename action
    setRenamingNodeId: (id: string | null) => void;

    // Inline creation actions
    startCreating: (type: HierarchyType, parentId: number | null) => void;
    cancelCreating: () => void;
}

export const useExplorerStore = create<ExplorerState>((set, get) => ({
    // Initial state
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
    renamingNodeId: null,
    creatingNodeType: null,
    creatingParentId: null,

    // Navigation
    setActiveNode: (node) => set({
        activeNodeId: node?.id ?? null
    }),

    setCurrentPath: (path) => set({
        currentPath: path,
        creatingNodeType: null,
        creatingParentId: null,
    }),

    navigateTo: (node, ancestors) => {
        const path = [...ancestors, node];
        set({
            currentPath: path,
            activeNodeId: node.id,
            selectedIds: new Set(),
            lastSelectedId: null,
            creatingNodeType: null,
            creatingParentId: null,
        });
    },

    navigateUp: () => {
        const { currentPath } = get();
        if (currentPath.length > 1) {
            const newPath = currentPath.slice(0, -1);
            const parentNode = newPath[newPath.length - 1];
            set({
                currentPath: newPath,
                activeNodeId: parentNode?.id ?? null,
                selectedIds: new Set(),
                lastSelectedId: null,
                creatingNodeType: null,
                creatingParentId: null,
            });
        } else if (currentPath.length === 1) {
            // Go to root
            set({
                currentPath: [],
                activeNodeId: null,
                selectedIds: new Set(),
                lastSelectedId: null,
                creatingNodeType: null,
                creatingParentId: null,
            });
        }
    },

    // Selection
    select: (id) => set({
        selectedIds: new Set([id]),
        lastSelectedId: id,
    }),

    toggleSelect: (id) => {
        const { selectedIds } = get();
        const newSelected = new Set(selectedIds);
        if (newSelected.has(id)) {
            newSelected.delete(id);
        } else {
            newSelected.add(id);
        }
        set({
            selectedIds: newSelected,
            lastSelectedId: id,
        });
    },

    rangeSelect: (id, allIds) => {
        const { lastSelectedId, selectedIds } = get();
        if (!lastSelectedId) {
            set({ selectedIds: new Set([id]), lastSelectedId: id });
            return;
        }

        const startIdx = allIds.indexOf(lastSelectedId);
        const endIdx = allIds.indexOf(id);

        if (startIdx === -1 || endIdx === -1) {
            set({ selectedIds: new Set([id]), lastSelectedId: id });
            return;
        }

        const [from, to] = startIdx < endIdx ? [startIdx, endIdx] : [endIdx, startIdx];
        const rangeIds = allIds.slice(from, to + 1);

        set({
            selectedIds: new Set([...selectedIds, ...rangeIds]),
        });
    },

    clearSelection: () => set({
        selectedIds: new Set(),
        lastSelectedId: null,
    }),

    selectAll: (ids) => set({
        selectedIds: new Set(ids),
        lastSelectedId: ids[ids.length - 1] ?? null,
    }),

    // Tree
    expand: (id) => {
        const { expandedIds } = get();
        const newExpanded = new Set(expandedIds);
        newExpanded.add(id);
        set({ expandedIds: newExpanded });
    },

    collapse: (id) => {
        const { expandedIds } = get();
        const newExpanded = new Set(expandedIds);
        newExpanded.delete(id);
        set({ expandedIds: newExpanded });
    },

    toggleExpand: (id) => {
        const { expandedIds } = get();
        if (expandedIds.has(id)) {
            get().collapse(id);
        } else {
            get().expand(id);
        }
    },

    // View
    setViewMode: (mode) => set({ viewMode: mode }),
    setSearchQuery: (query) => set({ searchQuery: query }),

    // Clipboard
    setClipboard: (nodeIds, mode) => set({
        clipboard: { nodeIds, mode },
    }),

    clearClipboard: () => set({
        clipboard: { nodeIds: [], mode: null },
    }),

    // Context menu
    openContextMenu: (x, y, nodeId) => set({
        contextMenuPosition: { x, y },
        contextMenuNodeId: nodeId,
    }),

    closeContextMenu: () => set({
        contextMenuPosition: null,
        contextMenuNodeId: null,
    }),

    setRenamingNodeId: (id) => set({ renamingNodeId: id }),

    // Inline creation
    startCreating: (type, parentId) => set({ creatingNodeType: type, creatingParentId: parentId }),
    cancelCreating: () => set({ creatingNodeType: null, creatingParentId: null }),
}));
