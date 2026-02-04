/**
 * ============================================================================
 * FILE: useAuthStore.ts
 * LOCATION: frontend/src/stores/useAuthStore.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Authentication state management using Zustand. Handles user login/logout,
 *    role-based access control, and Firebase Auth state synchronization.
 *
 * ROLE IN PROJECT:
 *    Central auth store used by all components that need auth state.
 *    Provides role checks (isAdmin, isStaff, isStudent) and department access.
 *
 * KEY STATE:
 *    - user: Current user info (id, email, role, departmentId)
 *    - isLoading: Auth state loading indicator
 *    - isAuthenticated: Whether user is logged in
 *
 * KEY ACTIONS:
 *    - login(email, password): Sign in with Firebase
 *    - logout(): Sign out
 *    - refreshUser(): Refresh user data from backend
 *
 * DEPENDENCIES:
 *    - External: zustand, firebase/auth
 *    - Internal: api/firebaseClient, api/client
 *
 * USAGE:
 *    import { useAuthStore } from '../stores/useAuthStore';
 *    const { user, isAdmin, login, logout } = useAuthStore();
 * ============================================================================
 */

import { create } from 'zustand';
import {
    signInWithEmailAndPassword,
    signOut,
    onAuthStateChanged,
    type User as FirebaseUser
} from 'firebase/auth';
import { auth } from '../api/firebaseClient';
import type { FirestoreUser, UserRole, UserStatus } from '../types/user';

export type { UserRole };

// User info interface
type FirestoreUserBase = Omit<
    FirestoreUser,
    'uid' | 'createdAt' | 'updatedAt' | 'displayName' | 'subjectIds' | '_v'
>;

export interface AuthUser extends FirestoreUserBase {
    id: string;
    displayName: string | null;
    departmentName: string | null;
    subjectIds: string[] | null;
    status: UserStatus;
}

type FirebaseTokenProvider = Pick<FirebaseUser, 'getIdToken'>;

// Auth state interface
interface AuthState {
    // State
    user: AuthUser | null;
    firebaseUser: FirebaseTokenProvider | null;
    isLoading: boolean;
    isInitialized: boolean;
    error: string | null;

    // Computed (as functions)
    isAuthenticated: () => boolean;
    isAdmin: () => boolean;
    isStaff: () => boolean;
    isStudent: () => boolean;
    canManageHierarchy: () => boolean;
    canManageModules: (departmentId?: string) => boolean;
    canUploadNotes: (departmentId?: string) => boolean;
    canReadNotes: (departmentId?: string) => boolean;

    // Actions
    login: (email: string, password: string) => Promise<void>;
    logout: () => Promise<void>;
    refreshUser: () => Promise<void>;
    setUser: (user: AuthUser | null) => void;
    setFirebaseUser: (user: FirebaseTokenProvider | null) => void;
    setLoading: (loading: boolean) => void;
    setError: (error: string | null) => void;
    setInitialized: (initialized: boolean) => void;
    getIdToken: () => Promise<string | null>;
}

// API base URL
const API_BASE = '/api';

export const useAuthStore = create<AuthState>((set, get) => ({
    // Initial state
    user: null,
    firebaseUser: null,
    isLoading: true,
    isInitialized: false,
    error: null,

    // Computed functions
    isAuthenticated: () => get().user !== null,

    isAdmin: () => get().user?.role === 'admin',

    isStaff: () => get().user?.role === 'staff',

    isStudent: () => get().user?.role === 'student',

    canManageHierarchy: () => get().user?.role === 'admin',

    canManageModules: (departmentId?: string) => {
        const { user } = get();
        if (!user) return false;
        if (user.role === 'admin') return false; // Admins can't manage modules
        if (user.role === 'staff') {
            // Staff can manage modules in their department
            if (!departmentId) return true; // General permission
            return user.departmentId === departmentId;
        }
        return false;
    },

    canUploadNotes: (departmentId?: string) => {
        const { user } = get();
        if (!user) return false;
        if (user.role === 'admin') return false; // Admins can't upload notes
        if (user.role === 'student') return false; // Students can't upload
        if (user.role === 'staff') {
            if (!departmentId) return true;
            return user.departmentId === departmentId;
        }
        return false;
    },

    canReadNotes: (departmentId?: string) => {
        const { user } = get();
        if (!user) return false;
        if (user.role === 'admin') return true; // Admins can read all
        if (!departmentId) return true; // General permission
        return user.departmentId === departmentId;
    },

    // Actions
    login: async (email: string, password: string) => {
        set({ isLoading: true, error: null });

        try {
            // MOCK LOGIN via Backend Endpoint
            console.log("Using BACKEND MOCK LOGIN for", email);

            // Call the new mock login endpoint
            const res = await fetch(`${API_BASE}/auth/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || "Login failed");
            }

            const data = await res.json();
            const { token, user: userData } = data;

            // Map backend user to AuthUser
            const authUser: AuthUser = {
                id: userData.id,
                email: userData.email,
                displayName: userData.displayName || 'User',
                role: userData.role,
                departmentId: userData.departmentId,
                departmentName: null,
                subjectIds: userData.subjectIds || null,
                status: 'active'
            };

            // Store in LocalStorage
            localStorage.setItem('mock_token', token);
            localStorage.setItem('mock_user', JSON.stringify(authUser));

            set({
                user: authUser,
                firebaseUser: null,
                isLoading: false,
                error: null,
            });

            // Create dummy firebase user for refresh logic if needed
            const dummyAuth: FirebaseTokenProvider = {
                getIdToken: async () => token
            };

            set({ firebaseUser: dummyAuth });

            // Trigger refresh to ensure fresh state (optional, but good practice)
            await get().refreshUser();

        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Login failed';
            set({
                user: null,
                isLoading: false,
                error: errorMessage
            });
            throw error;
        }
    },

    logout: async () => {
        set({ isLoading: true });
        try {
            // Clear Mock Data
            localStorage.removeItem('mock_token');
            localStorage.removeItem('mock_user');

            await signOut(auth); // Keep calling this in case mixed mode, but it won't hurt

            set({
                user: null,
                firebaseUser: null,
                isLoading: false,
                error: null
            });
        } catch (error) {
            set({ isLoading: false });
            throw error;
        }
    },

    refreshUser: async () => {
        const { firebaseUser } = get();
        if (!firebaseUser) {
            set({ user: null, isLoading: false });
            return;
        }

        try {
            const idToken = await firebaseUser.getIdToken();

            const response = await fetch(`${API_BASE}/auth/me`, {
                headers: {
                    'Authorization': `Bearer ${idToken}`,
                },
            });

            if (!response.ok) {
                // User might not be registered in the system
                set({ user: null, isLoading: false });
                return;
            }

            const userData = await response.json();

            const newUser: AuthUser = {
                id: userData.id,
                email: userData.email,
                displayName: userData.display_name,
                role: userData.role,
                departmentId: userData.department_id,
                departmentName: userData.department_name,
                subjectIds: userData.subject_ids || null,
                status: userData.status,
            };

            // Sync to localStorage if we are in mock mode
            if (localStorage.getItem('mock_token')) {
                localStorage.setItem('mock_user', JSON.stringify(newUser));
            }

            set({
                user: newUser,
                isLoading: false,
            });
        } catch (error) {
            console.error('Failed to refresh user:', error);
            set({ user: null, isLoading: false });
        }
    },

    setUser: (user) => set({ user }),
    setFirebaseUser: (user) => set({ firebaseUser: user }),
    setLoading: (loading) => set({ isLoading: loading }),
    setError: (error) => set({ error }),
    setInitialized: (initialized) => set({ isInitialized: initialized }),

    getIdToken: async () => {
        // MOCK AUTH IMPLEMENTATION
        const mockToken = localStorage.getItem('mock_token');
        if (mockToken) return mockToken;

        const { firebaseUser } = get();
        if (!firebaseUser) return null;
        return firebaseUser.getIdToken();
    },
}));

// Initialize auth state listener
// This should be called once when the app starts
export function initAuthListener() {
    const store = useAuthStore.getState();

    // MOCK AUTH INITIALIZATION
    const mockToken = localStorage.getItem('mock_token');
    const mockUserStr = localStorage.getItem('mock_user');

    if (mockToken && mockUserStr) {
        try {
            const mockUser = JSON.parse(mockUserStr);
            store.setUser(mockUser);
            store.setFirebaseUser(null);
            store.setInitialized(true);
            console.log("Mock session restored, refreshing profile...");
            // Ensure profile is up to date (gets departmentId correctly)
            store.refreshUser();
            return () => { }; // No real subscription to unsubscribe
        } catch (e) {
            console.error("Failed to restore mock session", e);
            localStorage.removeItem('mock_token');
            localStorage.removeItem('mock_user');
        }
    }

    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
        // Only run real firebase logic if we are NOT in mock mode (cleaned up above)
        if (firebaseUser) {
            store.setFirebaseUser(firebaseUser);
            await store.refreshUser();
        } else {
            // Note: If we had a mock session, we wouldn't reach here due to early return above?
            // Actually, locally we might want to support both or fallback.
            // But since 'onAuthStateChanged' fires async, we must be careful not to overwrite our synchronous mock restore.
            // If we are strictly "mock mode", we can ignore this.

            // If we didn't find a mock token safely, we rely on firebase.
            if (!localStorage.getItem('mock_token')) {
                store.setUser(null);
                store.setFirebaseUser(null);
                store.setLoading(false);
            }
        }

        store.setInitialized(true);
    });

    return unsubscribe;
}
