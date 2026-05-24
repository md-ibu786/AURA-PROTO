/**
 * ============================================================================
 * FILE: LoginPage.tsx
 * LOCATION: frontend/src/pages/LoginPage.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    Login page for user authentication. Displays email/password form
 *    and handles Firebase Auth sign-in.
 *
 * ROLE IN PROJECT:
 *    Entry point for unauthenticated users. Redirects to appropriate
 *    page after successful login based on user role.
 *
 * DEPENDENCIES:
 *    - External: react, react-router-dom
 *    - Internal: stores/useAuthStore
 *
 * USAGE:
 *    Route: /login
 * ============================================================================
 */

import { useState, useEffect, type FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/useAuthStore';
import '../styles/login.css';

export function LoginPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const login = useAuthStore(s => s.login);
    const isLoading = useAuthStore(s => s.isLoading);
    const error = useAuthStore(s => s.error);
    const user = useAuthStore(s => s.user);

    // Redirect if already authenticated
    useEffect(() => {
        if (user) {
            const from = (location.state as { from?: string })?.from;
            if (from && from !== '/login') {
                navigate(from, { replace: true });
            } else if (user.role === 'admin') {
                navigate('/admin', { replace: true });
            } else {
                navigate('/', { replace: true });
            }
        }
    }, [user, navigate, location.state]);

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [localError, setLocalError] = useState<string | null>(null);

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setLocalError(null);

        if (!email || !password) {
            setLocalError('Please enter email and password');
            return;
        }

        try {
            await login(email, password);
            // Navigation is handled by the useEffect watching `user`
        } catch (err) {
            // Error is handled by the store
            console.error('Login failed:', err);
        }
    };

    const displayError = localError || error;

    return (
        <div className="login-page">
            <div className="login-container">
                <div className="login-header">
                    <div className="logo-container">
                        <img
                            src="/logo.png"
                            alt="AURA Notes Manager Logo"
                            className="login-logo"
                        />
                    </div>
                    <h1>AURA</h1>
                    <p>Academic Notes Management System</p>
                </div>

                <form onSubmit={handleSubmit} className="login-form">
                    <div className="form-group">
                        <label htmlFor="email">Email</label>
                        <input
                            id="email"
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="Enter your email"
                            disabled={isLoading}
                            autoComplete="email"
                            required
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">Password</label>
                        <input
                            id="password"
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder="Enter your password"
                            disabled={isLoading}
                            autoComplete="current-password"
                            required
                        />
                    </div>

                    {displayError && (
                        <div
                            className="error-message"
                            role="alert"
                            aria-live="assertive"
                        >
                            {displayError}
                        </div>
                    )}

                    <button
                        type="submit"
                        className="login-button"
                        disabled={isLoading}
                    >
                        {isLoading ? 'Signing in...' : 'Sign In'}
                    </button>
                </form>

                <div className="login-footer">
                    <p>Contact your administrator if you need access.</p>
                </div>
            </div>


        </div>
    );
}

