/**
 * ============================================================================
 * FILE: ConfirmDialog.tsx
 * LOCATION: frontend/src/components/ui/ConfirmDialog.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Custom confirmation dialog component. Replaces the native confirm()
 *    function which can be blocked by Chrome popup blockers.
 *
 * ROLE IN PROJECT:
 *    Used for destructive actions like delete confirmation. Provides a
 *    modal dialog with Cancel and Confirm buttons, where Confirm is
 *    styled as the primary action.
 *
 * KEY FEATURES:
 *    - Modal dialog with backdrop
 *    - Close on backdrop click
 *    - Close on Escape key
 *    - Customizable title, message, and actions
 *
 * PROPS:
 *    - isOpen: boolean - Controls dialog visibility
 *    - title: string - Dialog title
 *    - message: string - Confirmation message
 *    - onConfirm: () => void - Confirm callback
 *    - onCancel: () => void - Cancel callback
 *
 * DEPENDENCIES:
 *    - External: None
 *    - Internal: None (uses native <dialog> element)
 *
 * @see: stores/useExplorerStore.ts - For deleteDialog state management
 * @note: Uses native <dialog> element for accessibility
 */
import { useEffect, useRef } from 'react';
import { Trash2, AlertTriangle, Download, X } from 'lucide-react';

interface ConfirmDialogProps {
    isOpen: boolean;
    title: string;
    message: string;
    confirmLabel?: string;
    cancelLabel?: string;
    onConfirm: () => void;
    onCancel: () => void;
    variant?: 'danger' | 'warning' | 'info';
    destructive?: boolean;
}

export function ConfirmDialog({ 
    isOpen, 
    title, 
    message, 
    confirmLabel = 'Confirm', 
    cancelLabel = 'Cancel',
    onConfirm, 
    onCancel,
    variant = 'info',
    destructive = false
}: ConfirmDialogProps) {
    const dialogRef = useRef<HTMLDialogElement>(null);

    useEffect(() => {
        const dialog = dialogRef.current;
        if (!dialog) return;

        if (isOpen) {
            dialog.showModal();
        } else {
            dialog.close();
        }
    }, [isOpen]);

    // Handle escape key
    useEffect(() => {
        const handleKeyDown = (e: KeyboardEvent) => {
            if (e.key === 'Escape' && isOpen) {
                onCancel();
            }
        };
        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [isOpen, onCancel]);

    if (!isOpen) return null;

    const getIcon = () => {
        switch (variant) {
            case 'danger': return <Trash2 className="dialog-icon danger" />;
            case 'warning': return <AlertTriangle className="dialog-icon warning" />;
            case 'info': return <Download className="dialog-icon info" />;
            default: return null;
        }
    };

    return (
        <dialog
            ref={dialogRef}
            className={`confirm-dialog-v2 ${isOpen ? 'open' : ''}`}
            onClick={(e) => {
                // Close on backdrop click
                if (e.target === dialogRef.current) {
                    onCancel();
                }
            }}
        >
            <div className="confirm-dialog-card">
                <button className="dialog-close-btn" onClick={onCancel}>
                    <X size={18} />
                </button>

                <div className="dialog-content-wrapper">
                    <div className={`dialog-icon-container ${variant}`}>
                        {getIcon()}
                    </div>

                    <div className="dialog-text-content">
                        <h3 className="dialog-title">{title}</h3>
                        <p className="dialog-message">{message}</p>

                        <div className="dialog-actions-row">
                            <button className="dialog-btn secondary" onClick={onCancel}>
                                {cancelLabel}
                            </button>
                            <button 
                                className={`dialog-btn primary ${destructive || variant === 'danger' ? 'danger' : ''}`} 
                                onClick={onConfirm}
                            >
                                {confirmLabel}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        </dialog>
    );
}
