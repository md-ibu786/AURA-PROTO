/**
 * ============================================================================
 * FILE: LoadingSpinner.tsx
 * LOCATION: frontend/src/components/LoadingSpinner.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Full-screen loading spinner for auth initialization and page loads.
 *
 * DEPENDENCIES:
 *    - External: react
 * ============================================================================
 */

export function LoadingSpinner() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-primary-theme">
            <div className="flex flex-col items-center gap-4">
                <div 
                    className="animate-spin rounded-full h-12 w-12 border-b-2" 
                    style={{ borderColor: 'transparent', borderBottomColor: 'var(--color-primary)' }}
                />
                <p className="text-secondary font-medium">Loading...</p>
            </div>
        </div>
    );
}
