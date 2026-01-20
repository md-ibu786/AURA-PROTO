import * as React from "react"
import { cn } from "@/lib/cn"

export interface ButtonProps
    extends React.ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link"
    size?: "default" | "sm" | "lg" | "icon"
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
    ({ className, variant = "default", ...props }, ref) => {
        // Map to global CSS classes where applicable
        const mapVariant = () => {
            switch (variant) {
                case 'default': return 'btn btn-primary';
                case 'outline': return 'btn btn-secondary';
                case 'ghost': return 'btn btn-ghost';
                default: return 'btn btn-primary';
            }
        }

        return (
            <button
                className={cn(mapVariant(), className)}
                ref={ref}
                {...props}
            />
        )
    }
)
Button.displayName = "Button"

export { Button }
