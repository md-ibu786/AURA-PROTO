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

import { useState, type FormEvent } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuthStore } from '../stores/useAuthStore';

export function LoginPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const { login, isLoading, error } = useAuthStore();

    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [localError, setLocalError] = useState<string | null>(null);

    // Get redirect path from location state, or default based on role
    const from = (location.state as { from?: string })?.from || '/';

    const handleSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setLocalError(null);

        if (!email || !password) {
            setLocalError('Please enter email and password');
            return;
        }

        try {
            await login(email, password);

            // Get user role to determine redirect
            const user = useAuthStore.getState().user;
            // Force navigation to root for non-admins
            // ExplorerPage will handle the redirection to department
            if (user?.role === 'admin') {
                navigate('/admin', { replace: true });
            } else {
                navigate('/', { replace: true });
            }
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
                        />
                    </div>

                    {displayError && (
                        <div className="error-message">
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

            <style>{`
                .login-page {
                    min-height: 100vh;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    background: #000000;
                    padding: 20px;
                }

                .login-container {
                    background: #0a0a0a;
                    backdrop-filter: blur(10px);
                    border-radius: 16px;
                    padding: 40px;
                    width: 100%;
                    max-width: 400px;
                    border: 1px solid #222;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
                }

                .login-header {
                    text-align: center;
                    margin-bottom: 32px;
                }

                .login-header h1 {
                    font-size: 2.5rem;
                    font-weight: 700;
                    color: #FFD400;
                    margin: 0 0 8px 0;
                    letter-spacing: 4px;
                }

                .login-header p {
                    color: rgba(255, 255, 255, 0.6);
                    font-size: 0.875rem;
                    margin: 0;
                }

                .login-form {
                    display: flex;
                    flex-direction: column;
                    gap: 20px;
                }

                .form-group {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                }

                .form-group label {
                    color: rgba(255, 255, 255, 0.8);
                    font-size: 0.875rem;
                    font-weight: 500;
                }

                .form-group input {
                    padding: 12px 16px;
                    border-radius: 8px;
                    border: 1px solid #333;
                    background: #111;
                    color: #fff;
                    font-size: 1rem;
                    transition: all 0.2s ease;
                }

                .form-group input::placeholder {
                    color: rgba(255, 255, 255, 0.4);
                }

                .form-group input:focus {
                    outline: none;
                    border-color: #FFD400;
                    background: #1a1a1a;
                    box-shadow: 0 0 0 2px rgba(255, 212, 0, 0.2);
                }

                .form-group input:disabled {
                    opacity: 0.6;
                    cursor: not-allowed;
                }

                .error-message {
                    background: rgba(239, 68, 68, 0.1);
                    border: 1px solid rgba(239, 68, 68, 0.3);
                    color: #f87171;
                    padding: 12px;
                    border-radius: 8px;
                    font-size: 0.875rem;
                    text-align: center;
                }

                .login-button {
                    padding: 14px;
                    border-radius: 8px;
                    border: none;
                    background: #FFD400;
                    color: #000;
                    font-size: 1rem;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    margin-top: 8px;
                }

                .login-button:hover:not(:disabled) {
                    transform: translateY(-1px);
                    box-shadow: 0 4px 12px rgba(255, 212, 0, 0.4);
                    background: #ffe033;
                }

                .login-button:disabled {
                    opacity: 0.6;
                    cursor: not-allowed;
                }

                .login-footer {
                    margin-top: 24px;
                    text-align: center;
                }

                .login-footer p {
                    color: rgba(255, 255, 255, 0.4);
                    font-size: 0.75rem;
                    margin: 0;
                }
            `}</style>
        </div>
    );
}

export default LoginPage;
