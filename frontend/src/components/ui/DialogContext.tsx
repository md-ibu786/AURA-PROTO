import * as React from "react"

interface DialogContextType {
    open: boolean;
    onOpenChange: (open: boolean) => void;
}

export const DialogContext = React.createContext<DialogContextType>({
    open: false,
    onOpenChange: () => { }
});
