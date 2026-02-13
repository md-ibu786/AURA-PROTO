/**
 * ============================================================================
 * FILE: useMobileBreakpoint.ts
 * LOCATION: frontend/src/hooks/useMobileBreakpoint.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Custom hook to detect mobile viewport using matchMedia API.
 *
 * ROLE IN PROJECT:
 *    Provides reactive boolean indicating if viewport is at or below
 *    mobile breakpoint (768px). Used by mobile-responsive components.
 *
 * KEY COMPONENTS:
 *    - useMobileBreakpoint: Returns isMobile boolean based on viewport width
 *    - MOBILE_BREAKPOINT: Exported constant (768px) for use in CSS/JS
 *
 * DEPENDENCIES:
 *    - External: React (useState, useEffect)
 *    - Internal: stores/useExplorerStore.ts (for mobileMenuOpen state)
 *
 * USAGE:
 *    import { useMobileBreakpoint, MOBILE_BREAKPOINT } from '../hooks';
 *
 *    const { isMobile } = useMobileBreakpoint();
 * ============================================================================
 */

import { useState, useEffect } from 'react';

export const MOBILE_BREAKPOINT = 768;

export function useMobileBreakpoint(): boolean {
    const [isMobile, setIsMobile] = useState<boolean>(() => {
        if (typeof window === 'undefined') {
            return false;
        }
        return window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT}px)`).matches;
    });

    useEffect(() => {
        if (typeof window === 'undefined') {
            return;
        }

        const mediaQuery = window.matchMedia(
            `(max-width: ${MOBILE_BREAKPOINT}px)`
        );

        const handleChange = (event: MediaQueryListEvent): void => {
            setIsMobile(event.matches);
        };

        mediaQuery.addEventListener('change', handleChange);

        return () => {
            mediaQuery.removeEventListener('change', handleChange);
        };
    }, []);

    return isMobile;
}
