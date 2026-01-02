/**
 * Explorer Page - Main file browser interface
 */
import { useQuery } from '@tanstack/react-query';
import { useExplorerStore } from '../stores';
import { getExplorerTree } from '../api';
import { Sidebar } from '../components/layout/Sidebar';
import { Header } from '../components/layout/Header';
import { GridView } from '../components/explorer/GridView';
import { ListView } from '../components/explorer/ListView';
import { ContextMenu } from '../components/explorer/ContextMenu';
import type { FileSystemNode } from '../types';
import { Folder } from 'lucide-react';

export default function ExplorerPage() {
    const { viewMode, currentPath, contextMenuPosition, closeContextMenu, creatingNodeType } = useExplorerStore();

    // Fetch hierarchy tree
    const { data: tree = [], isLoading, error } = useQuery({
        queryKey: ['explorer', 'tree'],
        queryFn: () => getExplorerTree(5),
    });

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
        </div>
    );
}
