/**
 * ============================================================================
 * FILE: dialog.tsx
 * LOCATION: frontend/src/components/ui/dialog.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Modal dialog component suite with context-based state management.
 *    Provides Dialog, DialogContent, DialogHeader, DialogFooter,
 *    DialogTitle, and DialogDescription components.
 *
 * ROLE IN PROJECT:
 *    Reusable modal dialog system used for forms and confirmations.
 *    Uses native <dialog> element for accessibility with custom styling.
 *
 * COMPONENTS:
 *    - Dialog: Context provider wrapper
 *    - DialogContent: Modal content container with close button
 *    - DialogHeader: Title area container
 *    - DialogFooter: Action buttons area
 *    - DialogTitle: Accessible heading
 *    - DialogDescription: Helper text
 *
 * KEY FEATURES:
 *    - Native <dialog> element for accessibility
 *    - Backdrop click to close
 *    - Backdrop blur effect
 *    - Animations (fade-in, zoom-in, slide-in)
 *
 * PROPS:
 *    Dialog:
 *    - open?: boolean - Initial visibility
 *    - onOpenChange?: (open: boolean) => void - State setter
 *
 *    DialogContent:
 *    - children: React.ReactNode
 *    - className?: string - Additional classes
 *
 * DEPENDENCIES:
 *    - External: React, lucide-react (X icon)
 *    - Internal: lib/cn, DialogContext
 *
 * @see: DialogContext.tsx - State management context
 * @note: Uses native <dialog> with backdrop blur and animations
 */
import * as React from "react"
import { X } from "lucide-react"
import { cn } from "@/lib/cn"
import { DialogContext } from "./DialogContext"

interface DialogProps {
    open?: boolean;
    onOpenChange?: (open: boolean) => void;
    children: React.ReactNode;
}

export function Dialog({ open = false, onOpenChange = () => { }, children }: DialogProps) {
    return (
        <DialogContext.Provider value={{ open, onOpenChange }}>
            {children}
        </DialogContext.Provider>
    )
}

export function DialogContent({ children, className }: { children: React.ReactNode; className?: string }) {
    const { open, onOpenChange } = React.useContext(DialogContext);
    const dialogRef = React.useRef<HTMLDialogElement>(null);

    React.useEffect(() => {
        const dialog = dialogRef.current;
        if (!dialog) return;

        if (open) {
            dialog.showModal();
        } else {
            dialog.close();
        }
    }, [open]);

    // Close on backdrop click
    const handleClick = (e: React.MouseEvent) => {
        if (e.target === dialogRef.current) {
            onOpenChange(false);
        }
    };

    if (!open) return null;

    return (
        <dialog
            ref={dialogRef}
            className={cn(
                "backdrop:bg-black/70 backdrop:backdrop-blur-sm fixed left-[50%] top-[50%] z-50 grid w-full max-w-lg translate-x-[-50%] translate-y-[-50%] gap-4 p-6 shadow-lg duration-200 sm:rounded-lg",
                "bg-[#111111] border border-[#2a2a2a] text-white",
                "open:animate-in open:fade-in-0 open:zoom-in-95 open:slide-in-from-left-1/2 open:slide-in-from-top-48",
                className
            )}
            onClick={handleClick}
            onClose={() => onOpenChange(false)}
        >
            {children}
            <button
                className="absolute right-4 top-4 rounded-sm opacity-70 ring-offset-background transition-opacity hover:opacity-100 focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-2 disabled:pointer-events-none data-[state=open]:bg-accent data-[state=open]:text-muted-foreground"
                onClick={() => onOpenChange(false)}
            >
                <X className="h-4 w-4" />
                <span className="sr-only">Close</span>
            </button>
        </dialog>
    )
}

export function DialogHeader({
    className,
    ...props
}: React.HTMLAttributes<HTMLDivElement>) {
    return (
        <div
            className={cn(
                "flex flex-col space-y-1.5 text-center sm:text-left",
                className
            )}
            {...props}
        />
    )
}

export function DialogFooter({
    className,
    ...props
}: React.HTMLAttributes<HTMLDivElement>) {
    return (
        <div
            className={cn(
                "flex flex-col-reverse sm:flex-row sm:justify-end sm:space-x-2",
                className
            )}
            {...props}
        />
    )
}

export function DialogTitle({
    className,
    ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
    return (
        <h2
            className={cn(
                "text-lg font-semibold leading-none tracking-tight",
                className
            )}
            {...props}
        />
    )
}

export function DialogDescription({
    className,
    ...props
}: React.HTMLAttributes<HTMLParagraphElement>) {
    return (
        <p
            className={cn("text-sm text-muted-foreground", className)}
            {...props}
        />
    )
}
