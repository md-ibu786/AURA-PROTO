// useAuthStore.ts
// Zustand store for authentication state management with session persistence
//
// Centralizes user authentication state, role-based access control helpers,
// and session persistence via localStorage. Works with mock auth backend.
//
// @see: api/auth.py - Backend auth endpoints
// @note: Avoids Firebase SDK; uses custom mock auth implementation.

import { create } from 'zustand';

const API_BASE = '/api';

export type UserRole = 'admin' | 'staff' | 'student';

export interface AuthUser {
    id: string;
    email: string;
    displayName: string | null;
    role: UserRole;
    departmentId: string | null;
    subjectIds: string[] | null;
    status: string;
}

interface AuthState {
    // State
    user: AuthUser | null;
    token: string | null;
    isLoading: boolean;
    isInitialized: boolean;
    error: string | null;
    
    // Computed (as functions)
    isAuthenticated: () => boolean;
    isAdmin: () => boolean;
    isStaff: () => boolean;
    isStudent: () => boolean;
    canManageHierarchy: () => boolean;
    canUploadNotes: (departmentId?: string) => boolean;
    canReadNotes: (departmentId?: string) => boolean;
    
    // Actions
    login: (email: string, password: string) => Promise<void>;
    logout: () => void;
    refreshUser: () => Promise<void>;
    setUser: (user: AuthUser | null) => void;
    setToken: (token: string | null) => void;
    setLoading: (loading: boolean) => void;
    setError: (error: string | null) => void;
    setInitialized: (initialized: boolean) => void;
    getToken: () => string | null;
}

export const useAuthStore = create<AuthState>((set, get) => ({
    // Initial state
    user: null,
    token: null,
    isLoading: false,
    isInitialized: false,
    error: null,
    
    // Computed functions
    isAuthenticated: () => get().user !== null,
    isAdmin: () => get().user?.role === 'admin',
    isStaff: () => get().user?.role === 'staff',
    isStudent: () => get().user?.role === 'student',
    
    canManageHierarchy: () => get().user?.role === 'admin',
    
    canUploadNotes: (departmentId?: string) => {
        const { user } = get();
        if (!user) return false;
        if (user.role === 'admin') return false;  // Admins don't upload
        if (user.role === 'student') return false;
        if (user.role === 'staff') {
            if (!departmentId) return true;
            return user.departmentId === departmentId;
        }
        return false;
    },
    
    canReadNotes: (departmentId?: string) => {
        const { user } = get();
        if (!user) return false;
        if (user.role === 'admin') return true;  // Admins read all
        if (!departmentId) return true;
        return user.departmentId === departmentId;
    },
    
    // Actions
    login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });
        
        try {
            const response = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || 'Login failed');
            }
            
            const data = await response.json();
            const { token, user: userData } = data;
            
            const authUser: AuthUser = {
                id: userData.id,
                email: userData.email,
                displayName: userData.displayName || 'User',
                role: userData.role as UserRole,
                departmentId: userData.departmentId || null,
                subjectIds: userData.subjectIds || null,
                status: userData.status || 'active'
            };
            
            // Persist to localStorage
            localStorage.setItem('auth_token', token);
            localStorage.setItem('auth_user', JSON.stringify(authUser));
            
            set({
                user: authUser,
                token,
                isLoading: false,
                error: null
            });
            
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Login failed';
            set({
                user: null,
                token: null,
                isLoading: false,
                error: errorMessage
            });
            throw error;
        }
    },

    logout: () => {
        localStorage.removeItem('auth_token');
        localStorage.removeItem('auth_user');
        set({
            user: null,
            token: null,
            isLoading: false,
            error: null
        });
    },

    refreshUser: async () => {
        const token = get().token || localStorage.getItem('auth_token');
        if (!token) {
            set({ isLoading: false });
            return;
        }
        
        try {
            const response = await fetch(`${API_BASE}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                // Token invalid - clear auth state
                get().logout();
                return;
            }
            
            const userData = await response.json();
            
            const authUser: AuthUser = {
                id: userData.id,
                email: userData.email,
                displayName: userData.displayName || 'User',
                role: userData.role as UserRole,
                departmentId: userData.departmentId || null,
                subjectIds: userData.subjectIds || null,
                status: userData.status || 'active'
            };
            
            localStorage.setItem('auth_user', JSON.stringify(authUser));
            set({ user: authUser, isLoading: false });
            
        } catch (error) {
            console.error('Failed to refresh user:', error);
            get().logout();
        }
    },

    setUser: (user) => set({ user }),
    setToken: (token) => set({ token }),
    setLoading: (isLoading) => set({ isLoading }),
    setError: (error) => set({ error }),
    setInitialized: (isInitialized) => set({ isInitialized }),
    getToken: () => get().token,
}));

/**
 * Initialize authentication state from localStorage.
 * Call this in App.tsx useEffect on mount.
 * Returns a cleanup function (no-op for mock auth).
 */
export function initAuthListener(): () => void {
    const store = useAuthStore.getState();
    
    // Check for existing session in localStorage
    const storedToken = localStorage.getItem('auth_token');
    const storedUserStr = localStorage.getItem('auth_user');
    
    if (storedToken && storedUserStr) {
        try {
            const storedUser = JSON.parse(storedUserStr) as AuthUser;
            store.setToken(storedToken);
            store.setUser(storedUser);
            store.setInitialized(true);
            
            // Refresh user data from server
            store.refreshUser();
            
        } catch (e) {
            console.error('Failed to restore auth session:', e);
            localStorage.removeItem('auth_token');
            localStorage.removeItem('auth_user');
            store.setInitialized(true);
        }
    } else {
        store.setInitialized(true);
    }
    
    // Return cleanup function (no-op for mock auth)
    return () => {};
}
