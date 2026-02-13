/**
 * ============================================================================
 * FILE: SelectionActionBar.tsx
 * LOCATION: frontend/src/components/explorer/SelectionActionBar.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Floating action bar for bulk actions on selected explorer items.
 *
 * ROLE IN PROJECT:
 *    Provides module-scoped bulk operations (open, download, delete, KG).
 *    Coordinates with explorer selection state to act on chosen notes.
 *
 * KEY COMPONENTS:
 *    - SelectionActionBar: Renders bulk action buttons and selection count.
 *    - handleDownload: Downloads a single note or a zip of multiple notes.
 *
 * DEPENDENCIES:
 *    - External: react, framer-motion, lucide-react, @tanstack/react-query
 *    - Internal: stores/useExplorerStore, stores/useAuthStore, api/explorerApi,
 *      types
 *
 * USAGE:
 *    <SelectionActionBar />
 * ============================================================================
 */

import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useExplorerStore } from '../../stores/useExplorerStore';
import { useAuthStore } from '../../stores/useAuthStore';
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
import { useMobileBreakpoint } from '../../hooks/useMobileBreakpoint';
import type { FileSystemNode } from '../../types';
import { deleteNoteCascade, downloadNotesZip } from '../../api/explorerApi';

export const SelectionActionBar: React.FC = () => {
    const {
        selectedIds,
        clearSelection,
        openProcessDialog,
        openKGDeleteDialog,
        currentPath
    } = useExplorerStore();

    const { user } = useAuthStore();
    const isStaff = user?.role === 'staff';

    const queryClient = useQueryClient();
    const isMobile = useMobileBreakpoint();
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

    const handleDownload = async () => {
        const tree = queryClient.getQueryData<FileSystemNode[]>(['explorer', 'tree']) || [];
        const nodes = findNodesByIds(tree, selectedIds);
        const notes = nodes.filter(n => n.type === 'note' && n.meta?.pdfFilename);

        if (notes.length === 0) {
            alert('No downloadable PDF notes selected.');
            return;
        }

        const subjectName = currentPath.find(node => node.type === 'subject')?.label;
        const moduleName = currentPath.find(node => node.type === 'module')?.label;

        const buildZipFilename = (
            subjectLabel?: string,
            moduleLabel?: string
        ): string => {
            const sanitize = (value: string): string => {
                const trimmed = value.trim();
                const withoutInvalid = trimmed.replace(/[\\/:*?"<>|]/g, '-');
                const compactSpaces = withoutInvalid.replace(/\s+/g, ' ');
                return compactSpaces.replace(/[. ]+$/g, '');
            };

            const safeSubject = subjectLabel ? sanitize(subjectLabel) : '';
            const safeModule = moduleLabel ? sanitize(moduleLabel) : '';

            if (!safeSubject || !safeModule) {
                return 'notes.zip';
            }

            return `notes-${safeSubject}-${safeModule}.zip`;
        };

        let didStartDownload = false;

        if (notes.length === 1) {
            const pdfFilename = notes[0].meta?.pdfFilename;
            if (!pdfFilename) return;

            const link = document.createElement('a');
            link.href = `/api/pdfs/${pdfFilename}`;
            link.download = pdfFilename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            didStartDownload = true;
        } else {
            try {
                const filenames = notes
                    .map(note => note.meta?.pdfFilename)
                    .filter((filename): filename is string => Boolean(filename));

                const { blob } = await downloadNotesZip(
                    filenames,
                    subjectName,
                    moduleName
                );
                const objectUrl = window.URL.createObjectURL(blob);
                const link = document.createElement('a');
                link.href = objectUrl;
                link.download = buildZipFilename(subjectName, moduleName);
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                window.URL.revokeObjectURL(objectUrl);
                didStartDownload = true;
            } catch (error) {
                console.error('Bulk download failed:', error);
                const message = error instanceof Error
                    ? error.message
                    : 'Bulk download failed. Please try again.';
                alert(message);
            }
        }

        if (didStartDownload) {
            clearSelection();
        }
    };

    const handleOpen = () => {
        const tree = queryClient.getQueryData<FileSystemNode[]>(['explorer', 'tree']) || [];
        const nodes = findNodesByIds(tree, selectedIds);
        const notes = nodes.filter(n => n.type === 'note' && n.meta?.pdfFilename);

        if (notes.length === 0) {
            alert('No openable PDF notes selected.');
            return;
        }

        if (notes.length > 3) {
            // Warn user about opening many tabs
            const confirmed = confirm(`You are about to open ${notes.length} PDF files in new tabs. Continue?`);
            if (!confirmed) {
                return;
            }
        }

        // Open all PDFs (inline view)
        // Note: Browsers may block multiple popups. Users need to allow popups for this site.
        let openedCount = 0;
        notes.forEach((note, index) => {
            // Small delay between openings to help browsers handle multiple tabs
            // Use authenticated API endpoint for inline viewing
            const pdfFilename = note.meta?.pdfFilename;
            if (!pdfFilename) return;
            const newWindow = window.open(
                `/api/pdfs/${pdfFilename}?inline=1`,
                `_blank_${index}`
            );
            if (newWindow) {
                openedCount++;
            }
        });

        // Notify user if some windows were blocked
        if (openedCount < notes.length) {
            alert(`Opened ${openedCount} of ${notes.length} PDFs.\n\nSome files may have been blocked by your browser's popup blocker. Please allow popups for this site to open multiple files.`);
        }

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
                                ? `${deleteProgress.current}/${deleteProgress.total}...`
                                : isMobile ? `${count}` : `${count} selected`
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
                            <ExternalLink size={isMobile ? 18 : undefined} />
                            {!isMobile && <span>Open</span>}
                        </button>

                        <button
                            onClick={handleDownload}
                            className="selection-action-btn"
                            disabled={isDeleting}
                        >
                            <Download size={isMobile ? 18 : undefined} />
                            {!isMobile && <span>Download</span>}
                        </button>

                        {isStaff && (
                            <>
                                <button
                                    onClick={handleVectorize}
                                    className="selection-action-btn accent"
                                    disabled={isDeleting || !hasUnprocessedNotes}
                                    title={!hasUnprocessedNotes ? 'All selected documents are already vectorized' : ''}
                                >
                                    <Sparkles size={isMobile ? 18 : undefined} />
                                    {!isMobile && <span>Vectorize</span>}
                                </button>

                                <button
                                    onClick={handleDeleteKG}
                                    className="selection-action-btn"
                                    disabled={isDeleting}
                                >
                                    <Database size={isMobile ? 18 : undefined} />
                                    {!isMobile && <span>Delete KG</span>}
                                </button>

                                <div className="selection-separator" />

                                <button
                                    onClick={handleDelete}
                                    className="selection-action-btn danger"
                                    disabled={isDeleting}
                                >
                                    {isDeleting ? (
                                        <>
                                            <Loader2 size={isMobile ? 18 : 16} className="spinning" />
                                            <span>Cleaning up...</span>
                                        </>
                                    ) : (
                                        <>
                                            <Trash2 size={isMobile ? 18 : undefined} />
                                            {!isMobile && <span>Delete</span>}
                                        </>
                                    )}
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </motion.div>
        </AnimatePresence>
    );
};
