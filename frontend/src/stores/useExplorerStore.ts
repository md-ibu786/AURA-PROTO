/**
 * ============================================================================
 * FILE: useExplorerStore.ts
 * LOCATION: frontend/src/stores/useExplorerStore.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Central state management store for the file explorer UI using Zustand.
 *    Manages all UI state including navigation, selection, tree expansion,
 *    view mode, clipboard, context menus, and dialogs.
 *
 * ROLE IN PROJECT:
 *    This is the primary state store consumed by all explorer components.
 *    Unlike React Query (which manages server state), this store handles
 *    purely client-side UI concerns like selection and navigation.
 *
 * KEY STATE:
 *    Navigation:
 *    - currentPath: Breadcrumb path of FileSystemNodes
 *    - activeNodeId: Currently focused/active node
 *
 *    Selection (multi-select support):
 *    - selectedIds: Set of selected node IDs
 *    - lastSelectedId: For Shift+click range selection
 *
 *    Tree:
 *    - expandedIds: Set of expanded node IDs in sidebar tree
 *
 *    View:
 *    - viewMode: 'grid' or 'list'
 *    - searchQuery: Filter text for current folder
 *
 *    Context Menu & Dialogs:
 *    - contextMenuPosition, contextMenuNodeId: Right-click menu state
 *    - deleteDialogOpen, nodeToDelete: Confirm delete dialog
 *    - warningDialog: Duplicate name / error warnings
 *    - renamingNodeId: Currently renaming node
 *    - creatingNodeType, creatingParentId: Inline creation state
 *
 * DEPENDENCIES:
 *    - External: zustand
 *    - Internal: ../types (FileSystemNode, HierarchyType)
 *
 * USAGE:
 *    import { useExplorerStore } from '../stores';
 *
 *    // In component
 *    const { selectedIds, select, navigateTo } = useExplorerStore();
 * ============================================================================
 */
import { create } from 'zustand';
import type { FileSystemNode, HierarchyType } from '../types';

export type ViewMode = 'grid' | 'list';

interface ClipboardState {
    nodeIds: string[];
    mode: 'cut' | 'copy' | null;
}

interface ProcessDialogState {
    open: boolean;
    fileIds: string[];
    moduleId: string;
    skippedCount: number;  // Count of already-processed docs that were filtered out
}

interface DeleteDialogState {
    open: boolean;
    fileIds: string[];
    moduleId: string;
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
    creatingParentId: string | null;

    // Actions
    setActiveNode: (node: FileSystemNode | null) => void;
    setCurrentPath: (path: FileSystemNode[]) => void;
    navigateTo: (node: FileSystemNode, ancestors: FileSystemNode[]) => void;
    navigateUp: () => void;

    // Selection Mode
    selectionMode: boolean;
    setSelectionMode: (enabled: boolean) => void;

    // KG Process State
    kgPolling: { moduleId: string | null; isPolling: boolean };
    setKGPolling: (moduleId: string | null, isPolling: boolean) => void;

    processDialog: ProcessDialogState;
    openProcessDialog: (fileIds: string[], moduleId: string, skippedCount?: number) => void;
    closeProcessDialog: () => void;

    // KG Delete State
    deleteMode: boolean;
    setDeleteMode: (enabled: boolean) => void;
    kgDeleteDialog: DeleteDialogState;
    openKGDeleteDialog: (fileIds: string[], moduleId: string) => void;
    closeKGDeleteDialog: () => void;

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

    // Dialog state
    deleteDialogOpen: boolean;
    nodeToDelete: { id: string; type: HierarchyType; label: string } | null;
    openDeleteDialog: (node: { id: string; type: HierarchyType; label: string }) => void;
    closeDeleteDialog: () => void;

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
    startCreating: (type: HierarchyType, parentId: string | null) => void;
    cancelCreating: () => void;

    // Warning Dialog
    warningDialog: {
        isOpen: boolean;
        type: 'duplicate' | 'error';
        message: string;
        entityName?: string;
    };
    warningTimeoutId: NodeJS.Timeout | null;
    openWarningDialog: (type: 'duplicate' | 'error', message: string, entityName?: string) => void;
    closeWarningDialog: () => void;
}

export type UseExplorerStore = ReturnType<typeof useExplorerStore>;

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
    warningDialog: { isOpen: false, type: 'error', message: '' },
    warningTimeoutId: null,

    // Selection Mode
    selectionMode: false,

    // KG State
    kgPolling: { moduleId: null, isPolling: false },
    processDialog: { open: false, fileIds: [], moduleId: '', skippedCount: 0 },

    // KG Delete State
    deleteMode: false,
    kgDeleteDialog: { open: false, fileIds: [], moduleId: '' },

    setSelectionMode: (enabled) => set({ selectionMode: enabled }),

    setDeleteMode: (enabled) => set({ deleteMode: enabled }),

    setKGPolling: (moduleId, isPolling) => set({
        kgPolling: { moduleId, isPolling }
    }),

    openProcessDialog: (fileIds, moduleId, skippedCount = 0) => set({
        processDialog: { open: true, fileIds, moduleId, skippedCount }
    }),

    closeProcessDialog: () => set({
        processDialog: { open: false, fileIds: [], moduleId: '', skippedCount: 0 }
    }),

    openKGDeleteDialog: (fileIds, moduleId) => set({
        kgDeleteDialog: { open: true, fileIds, moduleId }
    }),

    closeKGDeleteDialog: () => set({
        kgDeleteDialog: { open: false, fileIds: [], moduleId: '' }
    }),

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

    // Dialogs
    deleteDialogOpen: false,
    nodeToDelete: null,
    openDeleteDialog: (node) => set({
        deleteDialogOpen: true,
        nodeToDelete: node,
        // Ensure context menu is closed when dialog opens
        contextMenuPosition: null,
        contextMenuNodeId: null
    }),
    closeDeleteDialog: () => set({
        deleteDialogOpen: false,
        nodeToDelete: null
    }),

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

    // Inline creation actions
    startCreating: (type, parentId) => set({ creatingNodeType: type, creatingParentId: parentId }),
    cancelCreating: () => set({ creatingNodeType: null, creatingParentId: null }),

    // Warning Dialog actions
    openWarningDialog: (type, message, entityName) => {
        const { warningTimeoutId } = get();
        if (warningTimeoutId) clearTimeout(warningTimeoutId);

        const timeoutId = setTimeout(() => {
            get().closeWarningDialog();
        }, 5000);

        set({
            warningDialog: {
                isOpen: true,
                type,
                message,
                entityName
            },
            warningTimeoutId: timeoutId
        });
    },

    closeWarningDialog: () => {
        const { warningTimeoutId } = get();
        if (warningTimeoutId) clearTimeout(warningTimeoutId);

        set({
            warningDialog: {
                isOpen: false,
                type: 'error',
                message: ''
            },
            warningTimeoutId: null
        });
    },
}));
