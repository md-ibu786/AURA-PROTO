/**
 * ============================================================================
 * FILE: DialogContext.tsx
 * LOCATION: frontend/src/components/ui/DialogContext.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    React context for managing dialog open/close state. Provides a
 *    lightweight context for child components to communicate with
 *    their parent Dialog container.
 *
 * ROLE IN PROJECT:
 *    Enables DialogContent components to access and modify the parent
 *    Dialog's open state without prop drilling.
 *
 * CONTEXT TYPE:
 *    - open: boolean - Current dialog visibility
 *    - onOpenChange: (open: boolean) => void - State setter
 *
 * DEPENDENCIES:
 *    - External: React
 *    - Internal: None
 *
 * @see: dialog.tsx - Uses this context for DialogContent
 */
import * as React from "react"

interface DialogContextType {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export const DialogContext = React.createContext<DialogContextType>({
    open: false,
    onOpenChange: () => { }
});
