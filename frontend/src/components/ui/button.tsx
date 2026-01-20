/**
 * ============================================================================
 * FILE: button.tsx
 * LOCATION: frontend/src/components/ui/button.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Reusable Button component with variant support. Provides consistent
 *    button styling with support for default, destructive, outline,
 *    secondary, ghost, and link variants.
 *
 * ROLE IN PROJECT:
 *    Standardized button component used throughout the application.
 *    Maps to global CSS button classes for consistent theming.
 *
 * PROPS:
 *    - variant: 'default' | 'destructive' | 'outline' | 'secondary' | 'ghost' | 'link'
 *    - size: 'default' | 'sm' | 'lg' | 'icon'
 *    - All standard HTML button attributes
 *
 * VARIANT MAPPING:
 *    - default -> btn btn-primary
 *    - outline -> btn btn-secondary
 *    - ghost -> btn btn-ghost
 *
 * DEPENDENCIES:
 *    - External: React
 *    - Internal: lib/cn (className utility)
 *
 * @see: lib/cn.ts - ClassName utility for Tailwind merging
 * @note: Maps to global CSS classes, not Tailwind utilities directly
 */
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
