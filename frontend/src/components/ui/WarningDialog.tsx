/**
 * ============================================================================
 * FILE: WarningDialog.tsx
 * LOCATION: frontend/src/components/ui/WarningDialog.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Toast-style warning dialog for duplicate name errors. Animated with
 *    framer-motion for smooth entry/exit animations at the top of the screen.
 *
 * ROLE IN PROJECT:
 *    Displays temporary warnings for duplicate hierarchy names. Unlike
 *    ConfirmDialog, this is a dismissible toast that auto-closes after
 *    5 seconds via the store.
 *
 * KEY FEATURES:
 *    - Fixed position at top of screen
 *    - Framer-motion animations (slide down from top)
 *    - Alert icon with warning styling
 *    - Auto-dismiss via warningTimeoutId in store
 *
 * STATE:
 *    - warningDialog.isOpen: boolean
 *    - warningDialog.type: 'duplicate' | 'error'
 *    - warningDialog.message: string
 *    - warningDialog.entityName: string (for message construction)
 *
 * DEPENDENCIES:
 *    - External: lucide-react (icons), framer-motion (animations)
 *    - Internal: stores/useExplorerStore
 *
 * @see: stores/useExplorerStore.ts - For warningDialog state and timeouts
 * @note: Auto-closes after 5 seconds if not dismissed manually
 */
import { useExplorerStore } from '../../stores';
import { AlertTriangle, X } from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

export function WarningDialog() {
    const { warningDialog, closeWarningDialog } = useExplorerStore();
    const { isOpen, entityName } = warningDialog;

    const mainMessage = `The file named "${entityName || 'Item'}" already exists`;
    const subtitle = "Department names must be unique";

    return (
        <AnimatePresence>
            {isOpen && (
                <motion.div
                    data-testid="warning-dialog"
                    initial={{ y: -100, x: '-50%', opacity: 0 }}
                    animate={{ y: 0, x: '-50%', opacity: 1 }}
                    exit={{ y: -100, x: '-50%', opacity: 0 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                    className="warning-dialog-container"
                >
                    <div className="warning-dialog">
                        <div className="warning-dialog-content">
                            <AlertTriangle className="warning-dialog-icon" size={20} data-testid="alert-icon" />
                            <div className="warning-dialog-text">
                                <h3 className="warning-dialog-title">{mainMessage}</h3>
                                <p className="warning-dialog-subtitle">{subtitle}</p>
                            </div>
                        </div>
                        <button
                            type="button"
                            className="warning-dialog-close"
                            onClick={closeWarningDialog}
                            aria-label="Close"
                        >
                            <X size={18} />
                        </button>
                    </div>
                </motion.div>
            )}
        </AnimatePresence>
    );
}
