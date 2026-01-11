/**
 * ============================================================================
 * FILE: main.tsx
 * LOCATION: frontend/src/main.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    React application entry point. Initializes the root React component,
 *    configures React Query for server state management, and sets up
 *    strict mode for development-time checks.
 *
 * ROLE IN PROJECT:
 *    This is the bootstrap file for the frontend. It:
 *    - Creates the root React DOM render target
 *    - Configures QueryClient for data fetching and caching
 *    - Wraps the App in necessary providers (QueryClientProvider)
 *    - Imports global CSS styles
 *
 * KEY CONFIGURATION:
 *    - staleTime: 0 (always refetch on invalidation for real-time updates)
 *    - retry: 1 (single retry on failed requests)
 *
 * DEPENDENCIES:
 *    - External: react, react-dom, @tanstack/react-query
 *    - Internal: App.tsx, styles/index.css, styles/explorer.css
 *
 * USAGE:
 *    This file is automatically executed when the Vite dev server starts
 *    or when the production build is loaded in a browser.
 * ============================================================================
 */
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import App from './App'
import './styles/index.css'
import './styles/explorer.css'

const queryClient = new QueryClient({
    defaultOptions: {
        queries: {
            staleTime: 0, // Always refetch on invalidation for immediate UI updates
            retry: 1,
        },
    },
})

createRoot(document.getElementById('root')!).render(
    <StrictMode>
        <QueryClientProvider client={queryClient}>
            <App />
        </QueryClientProvider>
    </StrictMode>,
)
