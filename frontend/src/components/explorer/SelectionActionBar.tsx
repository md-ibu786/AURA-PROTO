// SelectionActionBar.tsx
// Floating action bar for bulk operations on selected items

// Appears at the bottom of the screen when items are selected in the explorer.
// Provides actions for Download, Delete (Firestore), Vectorize (KG), and Delete KG.
// Restricted to module context to ensure bulk actions are performed in valid scopes.

// @see: useExplorerStore.ts - For selection state
// @see: SelectionOverlay.tsx - For selection logic
// @note: Renders null if currentModuleId is not resolved or context is invalid.

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useExplorerStore } from '../../stores/useExplorerStore';
import { useQueryClient } from '@tanstack/react-query';
import {
    Download,
    Trash2,
    Sparkles,
    X,
    ExternalLink,
    Loader2,
    Database
} from 'lucide-react';
import type { FileSystemNode } from '../../types';
import { deleteNoteCascade } from '../../api/explorerApi';

export const SelectionActionBar: React.FC = () => {
    const {
        selectedIds,
        clearSelection,
        openBulkDownloadDialog,
        openProcessDialog,
        openKGDeleteDialog,
        currentPath
    } = useExplorerStore();

    const queryClient = useQueryClient();
    const [isDeleting, setIsDeleting] = useState(false);
    const [deleteProgress, setDeleteProgress] = useState<{ current: number; total: number } | null>(null);

    const isInsideModule = currentPath.length > 0 && currentPath[currentPath.length - 1].type === 'module';

    if (selectedIds.size === 0 || !isInsideModule) return null;

    const count = selectedIds.size;
    const currentModuleId = currentPath[currentPath.length - 1]?.id;

    if (!currentModuleId) return null;

    // Helper to find nodes in tree by IDs
    const findNodesByIds = (nodes: FileSystemNode[], ids: Set<string>): FileSystemNode[] => {
        const found: FileSystemNode[] = [];
        const traverse = (list: FileSystemNode[]) => {
            for (const node of list) {
                if (ids.has(node.id)) {
                    found.push(node);
                }
                if (node.children) {
                    traverse(node.children);
                }
            }
        };
        traverse(nodes);
        return found;
    };

    // Check if any selected notes can be vectorized (not already processed)
    const tree = queryClient.getQueryData<FileSystemNode[]>(['explorer', 'tree']) || [];
    const selectedNodes = findNodesByIds(tree, selectedIds);
    const selectedNotes = selectedNodes.filter(n => n.type === 'note');
    const hasUnprocessedNotes = selectedNotes.some(n => {
        const status = n.meta?.kg_status;
        return !status || status === 'pending' || status === 'failed';
    });

    const handleDownload = () => {
        const tree = queryClient.getQueryData<FileSystemNode[]>(['explorer', 'tree']) || [];
        const nodes = findNodesByIds(tree, selectedIds);
        const notes = nodes.filter(n => n.type === 'note' && n.meta?.pdfFilename);

        if (notes.length === 0) {
            alert('No downloadable PDF notes selected.');
            return;
        }

        openBulkDownloadDialog(notes.map(n => ({
            id: n.id,
            type: n.type,
            label: n.label,
            meta: n.meta
        })));
    };

    const handleOpen = () => {
        const tree = queryClient.getQueryData<FileSystemNode[]>(['explorer', 'tree']) || [];
        const nodes = findNodesByIds(tree, selectedIds);
        const notes = nodes.filter(n => n.type === 'note' && n.meta?.pdfFilename);

        if (notes.length === 0) {
            alert('No openable PDF notes selected.');
            return;
        }

        // Open all synchronously to stay within the user gesture window as much as possible
        notes.forEach(note => {
            window.open(`/pdfs/${note.meta!.pdfFilename}`, `_blank_${note.id}`);
        });

        clearSelection();
    };

    const handleDelete = async () => {
        const tree = queryClient.getQueryData<FileSystemNode[]>(['explorer', 'tree']) || [];
        const nodes = findNodesByIds(tree, selectedIds);
        const noteIds = nodes.filter(n => n.type === 'note').map(n => n.id);

        if (noteIds.length === 0) return;

        setIsDeleting(true);
        setDeleteProgress({ current: 0, total: noteIds.length });

        let successCount = 0;
        let failedCount = 0;

        for (let i = 0; i < noteIds.length; i++) {
            setDeleteProgress({ current: i + 1, total: noteIds.length });

            try {
                const result = await deleteNoteCascade(noteIds[i]);
                if (result.document_deleted) {
                    successCount++;
                } else {
                    failedCount++;
                }
            } catch (error) {
                console.error(`Failed to delete note ${noteIds[i]}:`, error);
                failedCount++;
            }
        }

        // Invalidate queries to refresh the tree
        queryClient.invalidateQueries({ queryKey: ['explorer', 'tree'] });
        queryClient.invalidateQueries({ queryKey: ['kg', 'queue'] });

        setIsDeleting(false);
        setDeleteProgress(null);
        clearSelection();

        // Show result notification
        if (failedCount === 0) {
            alert(`Successfully deleted ${successCount} note(s) with complete cleanup.`);
        } else {
            alert(`Deleted ${successCount} note(s), ${failedCount} failed.`);
        }
    };

    const handleVectorize = () => {
        // Separate already processed notes from unprocessed ones
        // Only process notes that are: not processed yet, pending, or failed
        const unprocessedNotes = selectedNotes.filter(n => {
            const status = n.meta?.kg_status;
            return !status || status === 'pending' || status === 'failed';
        });
        const skippedCount = selectedNotes.length - unprocessedNotes.length;

        if (unprocessedNotes.length === 0) {
            alert('All selected documents are already vectorized.');
            return;
        }

        openProcessDialog(
            unprocessedNotes.map(n => n.id),
            currentModuleId,
            skippedCount
        );
    };

    const handleDeleteKG = () => {
        openKGDeleteDialog(Array.from(selectedIds), currentModuleId);
    };

    return (
        <AnimatePresence>
            <motion.div
                className="selection-action-bar-container"
                initial={{ y: 100, x: '-50%', opacity: 0 }}
                animate={{ y: 0, x: '-50%', opacity: 1 }}
                exit={{ y: 100, x: '-50%', opacity: 0 }}
                transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            >
                <div className="selection-action-bar">
                    <div className="selection-info">
                        <span className="selection-count">
                            {deleteProgress
                                ? `Deleting ${deleteProgress.current}/${deleteProgress.total}...`
                                : `${count} selected`
                            }
                        </span>
                        {!isDeleting && (
                            <button
                                onClick={clearSelection}
                                className="selection-clear-btn"
                                title="Clear selection"
                            >
                                <X size={14} />
                            </button>
                        )}
                    </div>

                    <div className="selection-actions">
                        <button
                            onClick={handleOpen}
                            className="selection-action-btn"
                            disabled={isDeleting}
                        >
                            <ExternalLink />
                            <span>Open</span>
                        </button>

                        <button
                            onClick={handleDownload}
                            className="selection-action-btn"
                            disabled={isDeleting}
                        >
                            <Download />
                            <span>Download</span>
                        </button>

                        <button
                            onClick={handleVectorize}
                            className="selection-action-btn accent"
                            disabled={isDeleting || !hasUnprocessedNotes}
                            title={!hasUnprocessedNotes ? 'All selected documents are already vectorized' : ''}
                        >
                            <Sparkles />
                            <span>Vectorize</span>
                        </button>

                        <button
                            onClick={handleDeleteKG}
                            className="selection-action-btn"
                            disabled={isDeleting}
                        >
                            <Database size={16} />
                            <span>Delete KG</span>
                        </button>

                        <div className="selection-separator" />

                        <button
                            onClick={handleDelete}
                            className="selection-action-btn danger"
                            disabled={isDeleting}
                        >
                            {isDeleting ? (
                                <>
                                    <Loader2 size={16} className="spinning" />
                                    <span>Cleaning up...</span>
                                </>
                            ) : (
                                <>
                                    <Trash2 />
                                    <span>Delete</span>
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </motion.div>
        </AnimatePresence>
    );
};
