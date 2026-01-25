/**
 * ============================================================================
 * FILE: DeleteFromKGDialog.tsx
 * LOCATION: frontend/src/features/kg/components/DeleteFromKGDialog.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Modal confirmation dialog for deleting documents from the Knowledge Graph.
 *    Displays warning about data loss and requires explicit confirmation.
 *
 * ROLE IN PROJECT:
 *    Shown when users select KG-processed notes in delete mode and click
 *    "Delete from KG". Confirms the destructive action and shows what will
 *    be removed:
 *    - Document nodes and all relationships
 *    - All chunk nodes (parent and child)
 *    - Orphaned entities (Topic, Concept, Methodology, Finding)
 *
 * KEY FEATURES:
 *    - Lists what will be deleted from the KG
 *    - Shows document count to be deleted
 *    - Handles success/error states
 *    - Cleans up selection mode on close
 *
 * STATE:
 *    - isDeleting: Loading state during API call
 *    - isComplete: Success state after deletion
 *    - error: Error message if deletion fails
 *
 * DEPENDENCIES:
 *    - External: lucide-react (icons)
 *    - Internal: stores/useExplorerStore, hooks/useKGProcessing
 *
 * @see: hooks/useKGProcessing.ts - deleteFiles mutation
 * @see: stores/useExplorerStore.ts - kgDeleteDialog state
 * @note: Matches ProcessDialog styling for consistency
 */
import React from 'react';
import { useExplorerStore } from '../../../stores';
import { useKGProcessing } from '../hooks/useKGProcessing';
import { Loader2, Trash2, X, AlertCircle, CheckCircle, AlertTriangle } from 'lucide-react';

export function DeleteFromKGDialog() {
    const {
        kgDeleteDialog,
        closeKGDeleteDialog,
        clearSelection,
        setSelectionMode,
        setDeleteMode
    } = useExplorerStore();

    const { deleteFiles } = useKGProcessing();
    const [isDeleting, setIsDeleting] = React.useState(false);
    const [isComplete, setIsComplete] = React.useState(false);
    const [error, setError] = React.useState<string | null>(null);
    const [deletedCount, setDeletedCount] = React.useState(0);
    const [failedCount, setFailedCount] = React.useState(0);

    const handleSubmit = () => {
        setIsDeleting(true);
        setError(null);

        deleteFiles.mutate({
            file_ids: kgDeleteDialog.fileIds,
            module_id: kgDeleteDialog.moduleId
        }, {
            onSuccess: (data) => {
                setIsDeleting(false);
                setIsComplete(true);
                setDeletedCount(data.deleted_count);
                setFailedCount(data.failed.length);
            },
            onError: (err: Error) => {
                setIsDeleting(false);
                setError(err.message || 'Deletion failed');
            }
        });
    };

    const handleClose = () => {
        if (isComplete) {
            clearSelection();
            setSelectionMode(false);
            setDeleteMode(false);
        }
        setIsDeleting(false);
        setIsComplete(false);
        setError(null);
        setDeletedCount(0);
        setFailedCount(0);
        closeKGDeleteDialog();
    };

    if (!kgDeleteDialog.open) return null;

    return (
        <div className="dialog-overlay" onClick={handleClose}>
            <div className="dialog upload-dialog" onClick={(e) => e.stopPropagation()}>
                <div className="dialog-header">
                    <h2 className="dialog-title">
                        {isComplete ? 'Deletion Complete' : 'Delete from Knowledge Graph'}
                    </h2>
                    <button className="dialog-close" onClick={handleClose}>
                        <X size={20} />
                    </button>
                </div>

                <div className="dialog-body">
                    {error && (
                        <div className="upload-error">
                            <AlertCircle size={16} />
                            {error}
                        </div>
                    )}

                    {isComplete ? (
                        <div className="processing-status">
                            <div className="processing-icon">
                                <CheckCircle size={48} className="text-success" />
                            </div>
                            <div className="processing-label">
                                Deletion Complete
                            </div>
                            <div className="processing-message">
                                {deletedCount} document(s) have been removed from the Knowledge Graph.
                                {failedCount > 0 && (
                                    <><br />{failedCount} document(s) failed to delete.</>
                                )}
                                <br />Their status has been reset to "pending".
                            </div>
                            <div className="processing-actions">
                                <button className="btn btn-primary" onClick={handleClose}>
                                    Done
                                </button>
                            </div>
                        </div>
                    ) : (
                        <>
                            <div style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 'var(--spacing-sm)',
                                padding: 'var(--spacing-sm) var(--spacing-md)',
                                background: 'rgba(239, 68, 68, 0.1)',
                                border: '1px solid rgba(239, 68, 68, 0.3)',
                                borderRadius: 'var(--radius-sm)',
                                marginBottom: 'var(--spacing-md)',
                                fontSize: '13px',
                                color: '#ef4444'
                            }}>
                                <AlertTriangle size={16} />
                                This action cannot be undone
                            </div>

                            <p className="text-secondary" style={{ marginBottom: 'var(--spacing-md)' }}>
                                Remove <span className="text-accent">{kgDeleteDialog.fileIds.length}</span> document(s) from the Knowledge Graph?
                            </p>

                            <div style={{
                                background: 'var(--color-bg-tertiary)',
                                borderRadius: 'var(--radius-md)',
                                padding: 'var(--spacing-md)',
                                marginBottom: 'var(--spacing-lg)'
                            }}>
                                <p className="text-muted" style={{ marginBottom: 'var(--spacing-sm)', fontSize: '13px' }}>
                                    This will permanently delete:
                                </p>
                                <ul style={{
                                    listStyle: 'none',
                                    padding: 0,
                                    margin: 0,
                                    display: 'flex',
                                    flexDirection: 'column',
                                    gap: 'var(--spacing-xs)'
                                }}>
                                    <li className="flex items-center gap-sm" style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                                        <span style={{ color: '#ef4444' }}>•</span>
                                        Document nodes and all relationships
                                    </li>
                                    <li className="flex items-center gap-sm" style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                                        <span style={{ color: '#ef4444' }}>•</span>
                                        All chunk nodes (text segments)
                                    </li>
                                    <li className="flex items-center gap-sm" style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                                        <span style={{ color: '#ef4444' }}>•</span>
                                        Orphaned entities (topics, concepts)
                                    </li>
                                    <li className="flex items-center gap-sm" style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                                        <span style={{ color: '#ef4444' }}>•</span>
                                        Vector embeddings
                                    </li>
                                </ul>
                            </div>

                            <p className="text-muted" style={{ fontSize: '12px', marginBottom: 'var(--spacing-md)' }}>
                                Note: The original PDF files will not be deleted. Documents can be re-processed later.
                            </p>

                            <div className="upload-actions">
                                <button className="btn btn-secondary" onClick={handleClose}>
                                    Cancel
                                </button>
                                <button
                                    className="btn"
                                    style={{
                                        background: '#ef4444',
                                        color: 'white',
                                        border: 'none'
                                    }}
                                    onClick={handleSubmit}
                                    disabled={isDeleting}
                                >
                                    {isDeleting ? (
                                        <>
                                            <Loader2 size={16} className="spinning" />
                                            Deleting...
                                        </>
                                    ) : (
                                        <>
                                            <Trash2 size={16} />
                                            Delete from KG
                                        </>
                                    )}
                                </button>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
}
