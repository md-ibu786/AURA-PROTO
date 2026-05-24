/**
 * ============================================================================
 * FILE: ErrorBoundary.tsx
 * LOCATION: frontend/src/components/ErrorBoundary.tsx
 * ============================================================================
 *
 * PURPOSE:
 *    React error boundary class component that catches render errors and
 *    displays a fallback UI instead of a white screen.
 *
 * ROLE IN PROJECT:
 *    Wraps application routes to prevent single component crashes from
 *    taking down the entire app. Provides per-route isolation.
 *
 * KEY COMPONENTS:
 *    - ErrorBoundary: Class component with getDerivedStateFromError,
 *      componentDidCatch, and retry button.
 *
 * DEPENDENCIES:
 *    - External: react, lucide-react
 *    - Internal: None
 *
 * USAGE:
 *    <ErrorBoundary>
 *        <SomeComponent />
 *    </ErrorBoundary>
 * ============================================================================
 */
import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertCircle, RefreshCw } from 'lucide-react';

interface Props {
    children: ReactNode;
    fallback?: ReactNode;
}

interface State {
    hasError: boolean;
    error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
    state: State = { hasError: false, error: null };

    static getDerivedStateFromError(error: Error): State {
        return { hasError: true, error };
    }

    componentDidCatch(error: Error, errorInfo: ErrorInfo) {
        console.error('ErrorBoundary caught:', error, errorInfo);
    }

    render() {
        if (this.state.hasError) {
            if (this.props.fallback) return this.props.fallback;

            return (
                <div className="min-h-screen flex items-center justify-center bg-primary-theme p-4">
                    <div className="text-center space-y-4 max-w-md">
                        <AlertCircle className="w-12 h-12 text-destructive mx-auto" />
                        <h2 className="text-xl font-bold text-primary">Something went wrong</h2>
                        <p className="text-secondary text-sm">{this.state.error?.message}</p>
                        <button
                            onClick={() => this.setState({ hasError: false, error: null })}
                            className="btn btn-primary inline-flex items-center gap-2"
                        >
                            <RefreshCw className="w-4 h-4" />
                            Try again
                        </button>
                    </div>
                </div>
            );
        }
        return this.props.children;
    }
}
