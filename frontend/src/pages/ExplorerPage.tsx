/**
 * ============================================================================
 * FILE: ExplorerPage.tsx
 * LOCATION: frontend/src/pages/ExplorerPage.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Main page component for the file explorer interface. Orchestrates the
 *    layout (sidebar + main content), data fetching, and renders the
 *    appropriate view (grid/list) based on current state.
 *
 * ROLE IN PROJECT:
 *    This is the primary "page" that users see. It:
 *    - Fetches the hierarchy tree via React Query
 *    - Computes current folder's children based on navigation path
 *    - Renders Sidebar, Header, and content area (GridView or ListView)
 *    - Handles delete confirmation and warning dialogs
 *
 * KEY COMPONENTS RENDERED:
 *    - Sidebar: Left panel with tree navigation
 *    - Header: Top bar with breadcrumbs, search, view toggle
 *    - GridView/ListView: Main content area (toggleable)
 *    - ContextMenu: Right-click actions
 *    - ConfirmDialog: Delete confirmation
 *    - WarningDialog: Duplicate name warnings
 *
 * DATA FLOW:
 *    1. useQuery fetches tree from /api/explorer/tree
 *    2. getCurrentChildren() extracts children based on currentPath
 *    3. Children passed to GridView/ListView for rendering
 *    4. User interactions update Zustand store → triggers re-render
 *
 * DEPENDENCIES:
 *    - External: @tanstack/react-query, lucide-react
 *    - Internal: stores, api, components (Sidebar, Header, GridView, etc.)
 *
 * USAGE:
 *    This component is rendered at the root route (/*) by App.tsx.
 * ============================================================================
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useExplorerStore } from '../stores';
import { getExplorerTree } from '../api';
import * as api from '../api';
import { Sidebar } from '../components/layout/Sidebar';
import { Header } from '../components/layout/Header';
import { GridView } from '../components/explorer/GridView';
import { ListView } from '../components/explorer/ListView';
import { ContextMenu } from '../components/explorer/ContextMenu';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { WarningDialog } from '../components/ui/WarningDialog';
import type { FileSystemNode } from '../types';
import { Folder } from 'lucide-react';
import { FileSelectionBar } from '../features/kg/components/FileSelectionBar';
import { ProcessDialog } from '../features/kg/components/ProcessDialog';
import { ProcessingQueue } from '../features/kg/components/ProcessingQueue';

export default function ExplorerPage() {
    const {
        viewMode,
        currentPath,
        contextMenuPosition,
        closeContextMenu,
        creatingNodeType,
        deleteDialogOpen,
        nodeToDelete,
        closeDeleteDialog
    } = useExplorerStore();

    const queryClient = useQueryClient();

    // Fetch hierarchy tree
    const { data: tree = [], isLoading, error } = useQuery({
        queryKey: ['explorer', 'tree'],
        queryFn: () => getExplorerTree(5),
    });

    const handleDeleteConfirm = async () => {
        if (!nodeToDelete) return;

        const { id, type } = nodeToDelete;
        closeDeleteDialog();

        try {
            switch (type) {
                case 'department':
                    await api.deleteDepartment(id);
                    break;
                case 'semester':
                    await api.deleteSemester(id);
                    break;
                case 'subject':
                    await api.deleteSubject(id);
                    break;
                case 'module':
                    await api.deleteModule(id);
                    break;
                case 'note':
                    await api.deleteNote(id);
                    break;
            }

            await queryClient.refetchQueries({ queryKey: ['explorer', 'tree'] });
        } catch (error) {
            alert(`Failed to delete: ${(error as Error).message}`);
        }
    };

    // Get current folder's children to display
    const getCurrentChildren = (): FileSystemNode[] => {
        if (currentPath.length === 0) {
            // At root, show departments
            return tree;
        }

        // Find the current node in the tree and return its children
        const currentNode = currentPath[currentPath.length - 1];

        // Helper to find node in tree
        const findNode = (nodes: FileSystemNode[], id: string): FileSystemNode | null => {
            for (const node of nodes) {
                if (node.id === id) return node;
                if (node.children) {
                    const found = findNode(node.children, id);
                    if (found) return found;
                }
            }
            return null;
        };

        const node = findNode(tree, currentNode.id);
        return node?.children || [];
    };

    const children = getCurrentChildren();

    // Close context menu when clicking elsewhere
    const handleBackgroundClick = () => {
        if (contextMenuPosition) {
            closeContextMenu();
        }
    };

    if (error) {
        return (
            <div className="explorer-layout">
                <div className="empty-state">
                    <div className="empty-state-icon">❌</div>
                    <div className="empty-state-title">Error loading data</div>
                    <div className="empty-state-text">{(error as Error).message}</div>
                </div>
            </div>
        );
    }

    return (
        <div className="explorer-layout" onClick={handleBackgroundClick}>
            <Sidebar tree={tree} isLoading={isLoading} />

            <main className="explorer-main">
                <Header />

                <div className="explorer-content">
                    {isLoading ? (
                        <div className="empty-state">
                            <div className="spinner" />
                            <div className="empty-state-text" style={{ marginTop: '16px' }}>Loading...</div>
                        </div>
                    ) : children.length === 0 && !creatingNodeType ? (
                        <div className="empty-state">
                            <Folder className="empty-state-icon" />
                            <div className="empty-state-title">This folder is empty</div>
                            <div className="empty-state-text">
                                {currentPath.length === 0
                                    ? 'Create a department to get started'
                                    : 'Right-click to create a new item'}
                            </div>
                        </div>
                    ) : viewMode === 'grid' ? (
                        <GridView items={children} allItems={tree} />
                    ) : (
                        <ListView items={children} allItems={tree} />
                    )}
                </div>
            </main>

            {contextMenuPosition && <ContextMenu />}

            <ConfirmDialog
                isOpen={deleteDialogOpen}
                title="Confirm Delete"
                message={nodeToDelete ? `Are you sure you want to delete "${nodeToDelete.label}"? This action cannot be undone.` : ''}
                onConfirm={handleDeleteConfirm}
                onCancel={closeDeleteDialog}
            />

            <WarningDialog />

            {/* KG Features */}
            <FileSelectionBar />
            <ProcessDialog />
            <ProcessingQueue />
        </div>
    );
}
