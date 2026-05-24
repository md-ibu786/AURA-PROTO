/**
 * ============================================================================
 * FILE: ProtectedRoute.tsx
 * LOCATION: frontend/src/components/ProtectedRoute.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Route guard component for protecting pages based on authentication
 *    and role requirements.
 *
 * ROLE IN PROJECT:
 *    Wraps protected routes in App.tsx to enforce authentication and
 *    role-based access control. Redirects to login if unauthenticated.
 *
 * KEY COMPONENTS:
 *    - ProtectedRoute: HOC for route protection
 *
 * DEPENDENCIES:
 *    - External: react, react-router-dom
 *    - Internal: useAuthStore, LoadingSpinner
 * ============================================================================
 */

import { ReactNode } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuthStore, UserRole } from '../stores/useAuthStore';
import { LoadingSpinner } from './LoadingSpinner';

interface ProtectedRouteProps {
    children: ReactNode;
    requiredRole?: UserRole | UserRole[];
    excludedRoles?: UserRole | UserRole[];
    requiredDepartment?: string;
}

export function ProtectedRoute({
    children,
    requiredRole,
    excludedRoles,
    requiredDepartment
}: ProtectedRouteProps) {
    const location = useLocation();
    const user = useAuthStore(s => s.user);
    const isLoading = useAuthStore(s => s.isLoading);
    const isInitialized = useAuthStore(s => s.isInitialized);
    
    // Show loading spinner while auth is initializing
    if (!isInitialized || isLoading) {
        return <LoadingSpinner />;
    }
    
    // Redirect to login if not authenticated
    if (!user) {
        return (
            <Navigate 
                to="/login" 
                state={{ from: location.pathname }} 
                replace 
            />
        );
    }
    
    // Check role requirement
    if (requiredRole) {
        const roles = Array.isArray(requiredRole) ? requiredRole : [requiredRole];
        if (!roles.includes(user.role)) {
            // Redirect to home if role not allowed
            return <Navigate to="/" replace />;
        }
    }

    // Check excluded roles (e.g., prevent admin from accessing explorer)
    if (excludedRoles) {
        const excluded = Array.isArray(excludedRoles) ? excludedRoles : [excludedRoles];
        if (excluded.includes(user.role)) {
            return <Navigate to="/admin" replace />;
        }
    }
    
    // Check department requirement (admins bypass this check)
    if (requiredDepartment && user.role !== 'admin') {
        if (user.departmentId !== requiredDepartment) {
            return <Navigate to="/" replace />;
        }
    }
    
    return <>{children}</>;
}
