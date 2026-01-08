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