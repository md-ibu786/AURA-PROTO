/**
 * ============================================================================
 * FILE: App.tsx
 * LOCATION: frontend/src/App.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Root application component that sets up routing and global UI elements.
 *    Currently renders a single-page application with the ExplorerPage as
 *    the main (and only) route.
 *
 * ROLE IN PROJECT:
 *    Top-level orchestrator for the React frontend. Provides:
 *    - React Router configuration for client-side routing
 *    - Sonner toast notifications (bottom-right, with close button)
 *    - Route hierarchy (currently just ExplorerPage at root path)
 *
 * KEY COMPONENTS:
 *    - BrowserRouter: Client-side routing provider
 *    - Toaster: Global toast notification system from 'sonner'
 *    - Routes/Route: Define application routes
 *
 * DEPENDENCIES:
 *    - External: react-router-dom, sonner
 *    - Internal: pages/ExplorerPage
 *
 * USAGE:
 *    This component is rendered by main.tsx and wraps the entire application.
 *    All pages should be defined as Route elements within the Routes block.
 * ============================================================================
 */
import { useEffect } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from 'sonner'
import ExplorerPage from './pages/ExplorerPage'
import { LoginPage } from './pages/LoginPage'
import AdminDashboard from './pages/AdminDashboard'
import { ProtectedRoute } from './components/ProtectedRoute'
import { initAuthListener } from './stores/useAuthStore'


function App() {
    useEffect(() => {
        const unsubscribe = initAuthListener();
        return () => unsubscribe();
    }, []);

    return (
        <BrowserRouter>
            <Toaster position="bottom-right" richColors closeButton />
            <Routes>
                {/* Public route */}
                <Route path="/login" element={<LoginPage />} />

                {/* Protected routes */}
                <Route path="/admin" element={
                    <ProtectedRoute requiredRole="admin">
                        <AdminDashboard />
                    </ProtectedRoute>
                } />

                <Route path="/*" element={
                    <ProtectedRoute>
                        <ExplorerPage />
                    </ProtectedRoute>
                } />
            </Routes>
        </BrowserRouter>
    )
}

export default App
