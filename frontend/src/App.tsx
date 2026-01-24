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
 *    - Internal: pages/ExplorerPage, features/kg-query/pages/KGQueryPage
 *
 * USAGE:
 *    This component is rendered by main.tsx and wraps the entire application.
 *    All pages should be defined as Route elements within the Routes block.
 * ============================================================================
 */
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Toaster } from 'sonner'
import ExplorerPage from './pages/ExplorerPage'
import { KGQueryPage } from './features/kg-query/pages/KGQueryPage'

function App() {
    return (
        <BrowserRouter>
            <Toaster position="bottom-right" richColors closeButton />
            <Routes>
                <Route path="/kg-query" element={<KGQueryPage />} />
                <Route path="/*" element={<ExplorerPage />} />
            </Routes>
        </BrowserRouter>
    )
}

export default App
