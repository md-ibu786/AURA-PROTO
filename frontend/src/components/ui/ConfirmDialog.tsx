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

interface ConfirmDialogProps {
    isOpen: boolean;
    title: string;
    message: string;
    onConfirm: () => void;
    onCancel: () => void;
}

export function ConfirmDialog({ isOpen, title, message, onConfirm, onCancel }: ConfirmDialogProps) {
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

    return (
        <dialog
            ref={dialogRef}
            className="confirm-dialog"
            onClick={(e) => {
                // Close on backdrop click
                if (e.target === dialogRef.current) {
                    onCancel();
                }
            }}
        >
            <div className="confirm-dialog-content">
                <h3 className="confirm-dialog-title">{title}</h3>
                <p className="confirm-dialog-message">{message}</p>
                <div className="confirm-dialog-actions">
                    <button className="confirm-dialog-btn cancel" onClick={onCancel}>
                        Cancel
                    </button>
                    <button className="confirm-dialog-btn confirm" onClick={onConfirm}>
                        Delete
                    </button>
                </div>
            </div>
        </dialog>
    );
}
