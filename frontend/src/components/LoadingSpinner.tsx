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
        <div className="min-h-screen flex items-center justify-center bg-gray-100">
            <div className="flex flex-col items-center gap-4">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600" />
                <p className="text-gray-600">Loading...</p>
            </div>
        </div>
    );
}

export { LoadingSpinner as default };
