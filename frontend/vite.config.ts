/// <reference types="vitest/config" />
/**
 * ============================================================================
 * FILE: vite.config.ts
 * LOCATION: frontend/vite.config.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Vite configuration with React, Tailwind CSS, and API proxy setup
 *
 * ROLE IN PROJECT:
 *    Configures the frontend build tool with plugins, path aliases, and
 *    development server settings. Proxies API requests to backend on port 8001
 *
 * KEY COMPONENTS:
 *    - React plugin: JSX/TSX transformation and HMR
 *    - TailwindCSS plugin: JIT compilation of utility classes
 *    - Path alias @: Maps to src/ directory
 *    - Proxy: Routes /api and /chat-api to backend server
 *
 * DEPENDENCIES:
 *    - External: vite, @vitejs/plugin-react, @tailwindcss/vite
 *    - Internal: None
 *
 * USAGE:
 *    npm run dev     - Start dev server on port 5174
 *    npm run build   - Production build
 * ============================================================================
 */
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
    plugins: [react(), tailwindcss()],
    css: {
        // Suppress warnings about escaped characters in Tailwind utility classes
        // (e.g., .bg-primary\/10, .backdrop-blur-\[1px\])
        lightningcss: {
            unusedSymbols: [],
        } as any,
    },
    resolve: {
        alias: {
            '@': path.resolve(__dirname, './src'),
        },
    },
    server: {
        port: 5174,
        host: true,  // Expose to all network interfaces
        proxy: {
            '/api': {
                target: 'http://127.0.0.1:8001',
                changeOrigin: true,
            },
            '/chat-api': {
                target: 'http://127.0.0.1:8000',
                changeOrigin: true,
                rewrite: (path) => path.replace(/^\/chat-api/, ''),
            },
            '/departments': {
                target: 'http://127.0.0.1:8001',
                changeOrigin: true,
            },
            '/semesters': {
                target: 'http://127.0.0.1:8001',
                changeOrigin: true,
            },
            '/subjects': {
                target: 'http://127.0.0.1:8001',
                changeOrigin: true,
            },
            '/pdfs': {
                target: 'http://127.0.0.1:8001',
                changeOrigin: true,
            },
            '/health': {
                target: 'http://127.0.0.1:8001',
                changeOrigin: true,
            },
            '/ready': {
                target: 'http://127.0.0.1:8001',
                changeOrigin: true,
            },
        },
    },
    test: {
        globals: true,
        environment: 'jsdom',
        setupFiles: ['./src/test/setup.ts'],
        include: ['src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}'],
        exclude: ['src/tests/firestore.rules.test.ts'],
        coverage: {
            provider: 'v8',
            reporter: ['text', 'json', 'html'],
            include: ['src/**/*.{ts,tsx}'],
            exclude: [
                'src/test/**',
                'src/**/*.d.ts',
                'src/main.tsx',
                'src/vite-env.d.ts',
            ],
        },
    },
    build: {
        chunkSizeWarningLimit: 1200, // Suppress chunk size warning (KB)
    },
})
