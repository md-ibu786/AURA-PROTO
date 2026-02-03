/**
 * ============================================================================
 * FILE: LoginPage.tsx
 * LOCATION: frontend/src/pages/LoginPage.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Login page with email/password authentication form.
 *
 * ROLE IN PROJECT:
 *    Entry point for unauthenticated users. Validates credentials via
 *    /api/auth/login and redirects to appropriate page on success.
 *
 * KEY COMPONENTS:
 *    - LoginPage: Main login form component
 *
 * DEPENDENCIES:
 *    - External: react, react-router-dom, sonner
 *    - Internal: useAuthStore
 * ============================================================================
 */

import { useState, FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { toast } from 'sonner';
import { useAuthStore } from '../stores/useAuthStore';

export function LoginPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const { login, isLoading, error } = useAuthStore();
    
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    
    // Get redirect path from location state, default to home
    const from = (location.state as { from?: string })?.from || '/';
    
    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        
        if (!email || !password) {
            toast.error('Please enter email and password');
            return;
        }
        
        try {
            await login(email, password);
            toast.success('Login successful');
            
            // Redirect based on role
            const user = useAuthStore.getState().user;
            if (user?.role === 'admin') {
                navigate('/admin', { replace: true });
            } else {
                navigate(from, { replace: true });
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : 'Login failed';
            toast.error(message);
        }
    };
    
    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-100">
            <div className="max-w-md w-full bg-white rounded-lg shadow-md p-8">
                <h1 className="text-2xl font-bold text-center mb-6">
                    AURA Notes Manager
                </h1>
                <h2 className="text-lg text-gray-600 text-center mb-8">
                    Sign in to your account
                </h2>
                
                <form onSubmit={handleSubmit} className="space-y-6">
                    <div>
                        <label 
                            htmlFor="email" 
                            className="block text-sm font-medium text-gray-700"
                        >
                            Email
                        </label>
                        <input
                            id="email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            placeholder="you@example.com"
                            required
                            disabled={isLoading}
                        />
                    </div>
                    
                    <div>
                        <label 
                            htmlFor="password" 
                            className="block text-sm font-medium text-gray-700"
                        >
                            Password
                        </label>
                        <input
                            id="password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                            placeholder="••••••••"
                            required
                            disabled={isLoading}
                        />
                    </div>
                    
                    {error && (
                        <div className="text-red-600 text-sm text-center">
                            {error}
                        </div>
                    )}
                    
                    <button
                        type="submit"
                        disabled={isLoading}
                        className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isLoading ? 'Signing in...' : 'Sign in'}
                    </button>
                </form>
                
                <div className="mt-6 text-center text-sm text-gray-500">
                    <p>Test accounts:</p>
                    <p>admin@test.com / Admin123!</p>
                    <p>staff@test.com / Staff123!</p>
                    <p>student@test.com / Student123!</p>
                </div>
            </div>
        </div>
    );
}

export default LoginPage;
