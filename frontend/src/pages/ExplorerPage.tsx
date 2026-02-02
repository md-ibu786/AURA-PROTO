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
 *    - External: @tanstack/react-query, lucide-react, jszip, sonner
 *    - Internal: stores, api, components (Sidebar, Header, GridView, etc.)
 *
 * USAGE:
 *    This component is rendered at the root route (/*) by App.tsx.
 * ============================================================================
 */
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useExplorerStore } from '../stores';
import { getExplorerTree, deleteNoteCascade } from '../api';
import * as api from '../api';
import JSZip from 'jszip';
import { toast } from 'sonner';
import { Sidebar } from '../components/layout/Sidebar';
import { Header } from '../components/layout/Header';
import { GridView } from '../components/explorer/GridView';
import { ListView } from '../components/explorer/ListView';
import { SelectionOverlay } from '../components/explorer/SelectionOverlay';
import { SelectionActionBar } from '../components/explorer/SelectionActionBar';
import { ContextMenu } from '../components/explorer/ContextMenu';

import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { WarningDialog } from '../components/ui/WarningDialog';
import type { FileSystemNode } from '../types';
import { Folder } from 'lucide-react';
import { FileSelectionBar } from '../features/kg/components/FileSelectionBar';
import { ProcessDialog } from '../features/kg/components/ProcessDialog';
import { DeleteFromKGDialog } from '../features/kg/components/DeleteFromKGDialog';
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
        closeDeleteDialog,
        bulkDeleteDialogOpen,
        nodesToDelete,
        closeBulkDeleteDialog,
        bulkDownloadDialogOpen,
        nodesToDownload,
        closeBulkDownloadDialog,
        clearSelection
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
                    await deleteNoteCascade(id);
                    break;
            }

            await queryClient.refetchQueries({ queryKey: ['explorer', 'tree'] });
        } catch (error) {
            alert(`Failed to delete: ${(error as Error).message}`);
        }
    };

    const handleBulkDeleteConfirm = async () => {
        if (nodesToDelete.length === 0) return;

        closeBulkDeleteDialog();

        try {
            await Promise.allSettled(nodesToDelete.map(node => {
                switch (node.type) {
                    case 'department': return api.deleteDepartment(node.id);
                    case 'semester': return api.deleteSemester(node.id);
                    case 'subject': return api.deleteSubject(node.id);
                    case 'module': return api.deleteModule(node.id);
                    case 'note': return deleteNoteCascade(node.id);
                    default: return Promise.resolve();
                }
            }));

            await queryClient.refetchQueries({ queryKey: ['explorer', 'tree'] });
            clearSelection();
        } catch (error) {
            alert(`Bulk delete failed: ${(error as Error).message}`);
        }
    };

    const handleBulkDownloadConfirm = async () => {
        const notes = nodesToDownload.filter(n => n.type === 'note' && n.meta?.pdfFilename);
        closeBulkDownloadDialog();

        if (notes.length === 0) return;

        const downloadToastId = toast.loading(`Preparing ZIP for ${notes.length} notes...`);

        const zip = new JSZip();
        
        // Get naming context: [..., subject, module]
        const moduleNode = currentPath[currentPath.length - 1];
        const subjectNode = currentPath[currentPath.length - 2];
        const fileName = `${subjectNode?.label || 'Subject'}-${moduleNode?.label || 'Module'}-notes.zip`;

        try {
            // Fetch all PDFs in parallel
            const fetchPromises = notes.map(async (note) => {
                const response = await fetch(`/pdfs/${note.meta!.pdfFilename}`);
                if (!response.ok) throw new Error(`Failed to fetch ${note.label}`);
                const blob = await response.blob();
                // Ensure unique filenames in zip if multiple notes have same label
                const name = note.label.toLowerCase().endsWith('.pdf') ? note.label : `${note.label}.pdf`;
                zip.file(name, blob);
            });

            await Promise.all(fetchPromises);
            toast.loading('Generating ZIP file...', { id: downloadToastId });

            const content = await zip.generateAsync({ type: 'blob' });
            
            const link = document.createElement('a');
            link.href = URL.createObjectURL(content);
            link.download = fileName;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(link.href);
            
            toast.success(`Download started: ${fileName}`, { id: downloadToastId });
            clearSelection();
        } catch (error) {
            toast.error(`Bulk download failed: ${(error as Error).message}`, { id: downloadToastId });
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

    if (import.meta.env.DEV) {
        (window as { __auraStore?: typeof useExplorerStore }).__auraStore = useExplorerStore;
    }

    return (
        <div className="explorer-layout" onClick={handleBackgroundClick}>
            <Sidebar tree={tree} isLoading={isLoading} />

            <main className="explorer-main">
                <Header />

                <SelectionOverlay>
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
                </SelectionOverlay>

            </main>

            {contextMenuPosition && <ContextMenu />}

            <ConfirmDialog
                isOpen={deleteDialogOpen}
                title="Confirm Delete"
                message={nodeToDelete ? `Are you sure you want to delete "${nodeToDelete.label}"? This action cannot be undone.${nodeToDelete.type === 'note' ? ' Any associated Knowledge Graph data will also be removed.' : ''}` : ''}
                onConfirm={handleDeleteConfirm}
                onCancel={closeDeleteDialog}
                variant="danger"
                confirmLabel="Delete"
                destructive
            />

            <ConfirmDialog
                isOpen={bulkDeleteDialogOpen}
                title="Confirm Bulk Delete"
                message={`Are you sure you want to delete ${nodesToDelete.length} items? This action cannot be undone and will remove them from the primary database.${nodesToDelete.some(n => n.type === 'note') ? ' Notes will have their Knowledge Graph data cleaned up first.' : ''}`}
                onConfirm={handleBulkDeleteConfirm}
                onCancel={closeBulkDeleteDialog}
                variant="danger"
                confirmLabel="Delete All"
                destructive
            />

            <ConfirmDialog
                isOpen={bulkDownloadDialogOpen}
                title="Download as ZIP"
                message={`You are about to bundle ${nodesToDownload.length} notes into a single ZIP file for download.`}
                onConfirm={handleBulkDownloadConfirm}
                onCancel={closeBulkDownloadDialog}
                variant="info"
                confirmLabel="Download ZIP"
            />

            <WarningDialog />


            {/* KG Features */}
            <FileSelectionBar />
            <ProcessDialog />
            <DeleteFromKGDialog />
            <ProcessingQueue />

            {/* Bulk Actions */}
            <SelectionActionBar />
        </div>

    );
}
