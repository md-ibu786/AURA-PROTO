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

export function LoginPage() {
    const navigate = useNavigate();
    const location = useLocation();
    const { login, isLoading, error, user } = useAuthStore();

    // Redirect if already authenticated
    useEffect(() => {
        if (user) {
            const from = (location.state as { from?: string })?.from;
            if (from) {
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
                    background: #0a0a0a;
                    padding: 20px;
                    position: relative;
                    overflow: hidden;
                }

                .login-page::before {
                    content: '';
                    position: absolute;
                    top: 5%;
                    left: 10%;
                    width: 600px;
                    height: 600px;
                    background: radial-gradient(circle, rgba(255, 212, 0, 0.2) 0%, transparent 70%);
                    border-radius: 50%;
                    pointer-events: none;
                    z-index: 0;
                }

                .login-page::after {
                    content: '';
                    position: absolute;
                    bottom: 0%;
                    right: 5%;
                    width: 500px;
                    height: 500px;
                    background: radial-gradient(circle, rgba(255, 212, 0, 0.15) 0%, transparent 70%);
                    border-radius: 50%;
                    pointer-events: none;
                    z-index: 0;
                }

                .login-container {
                    position: relative;
                    z-index: 1;
                    background: rgba(10, 10, 10, 0.95);
                    backdrop-filter: blur(10px);
                    border-radius: 16px;
                    padding: 32px;
                    width: 100%;
                    max-width: 448px;
                    border: 1px solid #222;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
                }

                .login-header {
                    text-align: center;
                    margin-bottom: 32px;
                }

                .logo-container {
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    width: 80px;
                    height: 80px;
                    border-radius: 16px;
                    background: rgba(255, 212, 0, 0.1);
                    border: 1px solid rgba(255, 212, 0, 0.2);
                    margin-bottom: 16px;
                    padding: 8px;
                }

                .login-logo {
                    width: 100%;
                    height: 100%;
                    object-fit: contain;
                }

                .login-header h1 {
                    font-size: 1.5rem;
                    font-weight: 700;
                    color: #FFD400;
                    margin: 0 0 4px 0;
                    letter-spacing: 0;
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
                    padding: 12px 16px;
                    border-radius: 8px;
                    border: none;
                    background: #FFD400;
                    color: #000;
                    font-size: 1rem;
                    font-weight: 600;
                    cursor: pointer;
                    transition: all 0.2s ease;
                    margin-top: 4px;
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
                    color: rgba(82, 82, 82, 1);
                    font-size: 0.75rem;
                    margin: 0;
                }
            `}</style>
        </div>
    );
}

export default LoginPage;
