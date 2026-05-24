/**
 * ============================================================================
 * FILE: ProcessDialog.tsx
 * LOCATION: frontend/src/features/kg/components/ProcessDialog.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Modal confirmation dialog for starting Knowledge Graph batch processing.
 *    Displays information about what will happen during processing and
 *    provides confirm/cancel actions.
 *
 * ROLE IN PROJECT:
 *    Shown when users select multiple notes and click "Process" in selection
 *    mode. Confirms the action and shows a summary of processing actions:
 *    - Extract entities (concepts, topics)
 *    - Generate relationships
 *    - Create vector embeddings
 *    - Update the module's Knowledge Graph
 *
 * KEY FEATURES:
 *    - Lists processing actions that will be performed
 *    - Shows document count to be processed
 *    - Handles success/error states
 *    - Cleans up selection mode on close
 *
 * STATE:
 *    - isProcessing: Loading state during API call
 *    - isComplete: Success state after queueing
 *    - error: Error message if processing fails
 *
 * DEPENDENCIES:
 *    - External: lucide-react (icons)
 *    - Internal: stores/useExplorerStore, hooks/useKGProcessing
 *
 * @see: hooks/useKGProcessing.ts - processFiles mutation
 * @see: stores/useExplorerStore.ts - processDialog state
 * @note: Matches UploadDialog styling for consistency
 */
import React from 'react';
import { useExplorerStore } from '../../../stores';
import { useKGProcessing } from '../hooks/useKGProcessing';
import { Loader2, Zap, X, AlertCircle, CheckCircle, Info } from 'lucide-react';

export function ProcessDialog() {
    const {
        processDialog,
        closeProcessDialog,
        clearSelection,
        setSelectionMode
    } = useExplorerStore();

    const { processFiles } = useKGProcessing();
    const [isProcessing, setIsProcessing] = React.useState(false);
    const [isComplete, setIsComplete] = React.useState(false);
    const [error, setError] = React.useState<string | null>(null);

    const handleSubmit = () => {
        setIsProcessing(true);
        setError(null);

        processFiles.mutate({
            file_ids: processDialog.fileIds,
            module_id: processDialog.moduleId
        }, {
            onSuccess: () => {
                setIsProcessing(false);
                setIsComplete(true);
            },
            onError: (err: Error) => {
                setIsProcessing(false);
                setError(err.message || 'Processing failed');
            }
        });
    };

    const handleClose = () => {
        if (isComplete) {
            clearSelection();
            setSelectionMode(false);
        }
        setIsProcessing(false);
        setIsComplete(false);
        setError(null);
        closeProcessDialog();
    };

    if (!processDialog.open) return null;

    return (
        <div className="dialog-overlay" onClick={handleClose}>
            <div className="dialog upload-dialog" onClick={(e) => e.stopPropagation()}>
                <div className="dialog-header">
                    <h2 className="dialog-title">
                        {isComplete ? 'Processing Started' : 'Process Documents'}
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
                                {processFiles.data?.task_id ? (
                                    <CheckCircle size={48} className="text-success" />
                                ) : (
                                    <Info size={48} className="text-warning" />
                                )}
                            </div>
                            <div className="processing-label">
                                {processFiles.data?.task_id
                                    ? 'Documents Queued!'
                                    : 'Nothing to Process'}
                            </div>
                            <div className="processing-message">
                                {processFiles.data?.task_id ? (
                                    <>
                                        {processFiles.data.documents_queued} document(s) have been queued for Knowledge Graph processing.
                                        {processFiles.data.documents_skipped > 0 && (
                                            <><br />{processFiles.data.documents_skipped} already-processed document(s) were skipped.</>
                                        )}
                                        <br />Processing will continue in the background.
                                    </>
                                ) : (
                                    <>
                                        All selected documents are already processed or could not be found.
                                        <br />No new tasks were dispatched.
                                    </>
                                )}
                            </div>
                            <div className="processing-actions">
                                <button className="btn btn-primary" onClick={handleClose}>
                                    Done
                                </button>
                            </div>
                        </div>
                    ) : (
                        <>
                            <p className="text-secondary" style={{ marginBottom: 'var(--spacing-md)' }}>
                                Queue <span className="text-accent">{processDialog.fileIds.length}</span> document(s) for Knowledge Graph processing?
                            </p>

                            {processDialog.skippedCount > 0 && (
                                <div style={{
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 'var(--spacing-sm)',
                                    padding: 'var(--spacing-sm) var(--spacing-md)',
                                    background: 'rgba(34, 197, 94, 0.1)',
                                    border: '1px solid rgba(34, 197, 94, 0.3)',
                                    borderRadius: 'var(--radius-sm)',
                                    marginBottom: 'var(--spacing-md)',
                                    fontSize: '13px',
                                    color: '#22c55e'
                                }}>
                                    <Info size={16} />
                                    {processDialog.skippedCount} document(s) already processed — will be skipped
                                </div>
                            )}

                            <div style={{
                                background: 'var(--color-bg-tertiary)',
                                borderRadius: 'var(--radius-md)',
                                padding: 'var(--spacing-md)',
                                marginBottom: 'var(--spacing-lg)'
                            }}>
                                <p className="text-muted" style={{ marginBottom: 'var(--spacing-sm)', fontSize: '13px' }}>
                                    This action will:
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
                                        <span style={{ color: 'var(--color-primary)' }}>•</span>
                                        Extract entities (concepts, topics)
                                    </li>
                                    <li className="flex items-center gap-sm" style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                                        <span style={{ color: 'var(--color-primary)' }}>•</span>
                                        Generate relationships
                                    </li>
                                    <li className="flex items-center gap-sm" style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                                        <span style={{ color: 'var(--color-primary)' }}>•</span>
                                        Create vector embeddings
                                    </li>
                                    <li className="flex items-center gap-sm" style={{ fontSize: '13px', color: 'var(--color-text-secondary)' }}>
                                        <span style={{ color: 'var(--color-primary)' }}>•</span>
                                        Update the module's Knowledge Graph
                                    </li>
                                </ul>
                            </div>

                            <div className="upload-actions">
                                <button className="btn btn-secondary" onClick={handleClose}>
                                    Cancel
                                </button>
                                <button
                                    className="btn btn-primary"
                                    onClick={handleSubmit}
                                    disabled={isProcessing}
                                >
                                    {isProcessing ? (
                                        <>
                                            <Loader2 size={16} className="spinning" />
                                            Processing...
                                        </>
                                    ) : (
                                        <>
                                            <Zap size={16} />
                                            Start Processing
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
