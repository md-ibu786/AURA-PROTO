/**
 * Confirmation Dialog Component
 * Custom dialog to replace native confirm() which can be blocked by Chrome
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
