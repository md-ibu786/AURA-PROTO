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
import { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useExplorerStore } from '../stores';
import { useAuthStore } from '../stores/useAuthStore';
import { getExplorerTree } from '../api';
import * as api from '../api';
import { Sidebar } from '../components/layout/Sidebar';
import { Header } from '../components/layout/Header';
import { GridView } from '../components/explorer/GridView';
import { ListView } from '../components/explorer/ListView';
import { ContextMenu } from '../components/explorer/ContextMenu';
import { SelectionOverlay } from '../components/explorer/SelectionOverlay';
import { SelectionActionBar } from '../components/explorer/SelectionActionBar';
import { ConfirmDialog } from '../components/ui/ConfirmDialog';
import { WarningDialog } from '../components/ui/WarningDialog';
import { ProcessDialog } from '../features/kg/components/ProcessDialog';
import { DeleteFromKGDialog } from '../features/kg/components/DeleteFromKGDialog';
import { ProcessingQueue } from '../features/kg/components/ProcessingQueue';
import type { FileSystemNode } from '../types';
import { Folder } from 'lucide-react';

export default function ExplorerPage() {
    const navigate = useNavigate();
    const {
        viewMode,
        currentPath,
        contextMenuPosition,
        closeContextMenu,
        creatingNodeType,
        deleteDialogOpen,
        nodeToDelete,
        closeDeleteDialog,
        navigateTo
    } = useExplorerStore();

    // Get user role and department
    const { user, isAdmin } = useAuthStore();
    const hasRedirected = useRef(false);

    const queryClient = useQueryClient();

    // Redirect admins to admin dashboard - they don't use explorer
    useEffect(() => {
        if (isAdmin()) {
            navigate('/admin', { replace: true });
        }
    }, [isAdmin, navigate]);

    // Fetch hierarchy tree
    const { data: tree = [], isLoading, error } = useQuery({
        queryKey: ['explorer', 'tree'],
        queryFn: () => getExplorerTree(5),
    });

    // Auto-navigate staff/students to appropriate starting level
    // Staff with subjectIds: start at root (shows filtered departments containing their subjects)
    // Students: navigate directly to their department's semesters view
    useEffect(() => {
        if (
            !isLoading &&
            tree.length > 0 &&
            !isAdmin() &&
            currentPath.length === 0 &&
            !hasRedirected.current
        ) {
            // Students: navigate to their department to show semesters
            if (user?.role === 'student' && user?.departmentId) {
                const userDept = tree.find(dept => dept.id === user.departmentId);
                if (userDept) {
                    console.log("Auto-navigating student to department:", userDept.label);
                    navigateTo(userDept, []);
                    hasRedirected.current = true;
                }
            }
            // Staff with subjectIds: stay at root level (getCurrentChildren will show filtered departments)
            // Staff without subjectIds but with department: stay at root (getCurrentChildren will show semesters)
            // No auto-navigation needed - the getCurrentChildren logic handles the default view
        }
    }, [isLoading, tree, user, isAdmin, currentPath.length, navigateTo]);

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

    // Filter tree for non-admins to only show their department or subjects
    const getFilteredTree = (): FileSystemNode[] => {
        if (isAdmin()) {
            return tree;
        }

        // Check if staff has subjectIds (multi-department access)
        if (user?.role === 'staff' && user?.subjectIds && user.subjectIds.length > 0) {
            const subjectIdsSet = new Set(user.subjectIds);

            // Recursively filter tree to only include user's subjects
            const filterBySubjects = (nodes: FileSystemNode[]): FileSystemNode[] => {
                const result: FileSystemNode[] = [];

                for (const node of nodes) {
                    if (node.type === 'subject') {
                        // Include subject if it's in the user's subjectIds
                        if (subjectIdsSet.has(node.id)) {
                            result.push(node);
                        }
                    } else if (node.children) {
                        // Recursively filter children
                        const filteredChildren = filterBySubjects(node.children);
                        // Only include this node if it has matching subjects
                        if (filteredChildren.length > 0) {
                            result.push({
                                ...node,
                                children: filteredChildren,
                            });
                        }
                    }
                }

                return result;
            };

            return filterBySubjects(tree);
        }

        if (!user?.departmentId) {
            // Fail safe: if non-admin has no department, show nothing
            return [];
        }
        // Non-admins: only show their department
        return tree.filter(dept => dept.id === user.departmentId);
    };

    const filteredTree = getFilteredTree();

    // Get current folder's children to display
    const getCurrentChildren = (): FileSystemNode[] => {
        if (currentPath.length === 0) {
            // At root level
            const isStaffWithSubjects = user?.role === 'staff' && user?.subjectIds && user.subjectIds.length > 0;

            if (isAdmin()) {
                // Admins at root: show departments
                return filteredTree;
            } else if (isStaffWithSubjects) {
                // Staff with subjects at root: show departments that have their subjects
                return filteredTree;
            } else if (user?.departmentId) {
                // Students at root with department: show semesters of their department directly
                const userDept = filteredTree.find(dept => dept.id === user.departmentId);
                return userDept?.children || [];
            }
            // No access: show nothing
            return [];
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

        const node = findNode(filteredTree, currentNode.id);
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
            <Sidebar tree={filteredTree} isLoading={isLoading} />

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
                                {isAdmin() && (
                                    <div className="empty-state-text">
                                        {currentPath.length === 0
                                            ? 'Create a department to get started'
                                            : 'Right-click to create a new item'}
                                    </div>
                                )}
                            </div>
                        ) : viewMode === 'grid' ? (
                            <GridView items={children} allItems={tree} />
                        ) : (
                            <ListView items={children} allItems={tree} />
                        )}
                    </div>
                </SelectionOverlay>

                <SelectionActionBar />
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
            <ProcessDialog />
            <DeleteFromKGDialog />
            <ProcessingQueue />
        </div>
    );
}
