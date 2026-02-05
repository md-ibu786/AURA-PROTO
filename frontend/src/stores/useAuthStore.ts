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
    onIdTokenChanged,
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
    getIdToken: (forceRefresh?: boolean) => Promise<string | null>;
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

        if (import.meta.env.VITE_USE_MOCK_AUTH === 'true') {
            try {
                // Simulate network delay
                await new Promise(resolve => setTimeout(resolve, 800));

                if (password === 'error') {
                     throw new Error('Mock invalid credentials');
                }

                const mockUser: AuthUser = {
                    id: 'mock-user-123',
                    email,
                    displayName: 'Mock User',
                    role: 'admin',
                    departmentId: null,
                    departmentName: null,
                    subjectIds: null,
                    status: 'active'
                };

                set({ user: mockUser, isLoading: false, error: null });
                return;
            } catch (error) {
                 set({ isLoading: false, error: 'Invalid mock credentials' });
                 throw error;
            }
        }

        try {
            const credentials = await signInWithEmailAndPassword(
                auth,
                email,
                password
            );
            const firebaseUser = credentials.user;

            set({ firebaseUser });

            const idToken = await firebaseUser.getIdToken();
            const syncResponse = await fetch(`${API_BASE}/auth/sync`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${idToken}`,
                },
                body: JSON.stringify({
                    displayName: firebaseUser.displayName ?? '',
                }),
            });

            if (!syncResponse.ok) {
                const err = await syncResponse.json().catch(() => ({
                    detail: 'Login failed',
                }));
                throw new Error(err.detail || 'Login failed');
            }

            await get().refreshUser();
            set({ isLoading: false, error: null });

        } catch (error: unknown) {
            let errorMessage = 'Login failed';

            const errorRecord = typeof error === 'object' && error !== null
                ? (error as Record<string, unknown>)
                : null;
            const errorCode = errorRecord && typeof errorRecord.code === 'string'
                ? errorRecord.code
                : null;
            const errorText = errorRecord && typeof errorRecord.message === 'string'
                ? errorRecord.message
                : error instanceof Error
                    ? error.message
                    : null;

            if (errorCode) {
                switch (errorCode) {
                    case 'auth/invalid-email':
                        errorMessage = 'Invalid email address';
                        break;
                    case 'auth/user-disabled':
                        errorMessage = 'Account has been disabled';
                        break;
                    case 'auth/user-not-found':
                        errorMessage = 'No account found with this email';
                        break;
                    case 'auth/wrong-password':
                        errorMessage = 'Incorrect password';
                        break;
                    case 'auth/too-many-requests':
                        errorMessage = 'Too many attempts. Try again later';
                        break;
                    case 'auth/network-request-failed':
                        errorMessage = 'Network error. Check connection';
                        break;
                    default:
                        errorMessage = errorText || 'Login failed';
                }
            } else if (errorText) {
                errorMessage = errorText;
            }

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
        
        if (import.meta.env.VITE_USE_MOCK_AUTH === 'true') {
            set({
                user: null,
                firebaseUser: null,
                isLoading: false,
                error: null
            });
            return;
        }

        try {
            await signOut(auth);

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
                if (response.status === 401) {
                    const syncResponse = await fetch(`${API_BASE}/auth/sync`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${idToken}`,
                        },
                        body: JSON.stringify({}),
                    });

                    if (syncResponse.ok) {
                        const retryResponse = await fetch(`${API_BASE}/auth/me`, {
                            headers: {
                                'Authorization': `Bearer ${idToken}`,
                            },
                        });

                        if (retryResponse.ok) {
                            const retryUserData = await retryResponse.json();
                            const retryUser: AuthUser = {
                                id: retryUserData.id,
                                email: retryUserData.email,
                                displayName: retryUserData.display_name,
                                role: retryUserData.role,
                                departmentId: retryUserData.department_id,
                                departmentName: retryUserData.department_name,
                                subjectIds: retryUserData.subject_ids || null,
                                status: retryUserData.status,
                            };

                            set({
                                user: retryUser,
                                isLoading: false,
                            });
                            return;
                        }
                    }
                }

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

    getIdToken: async (forceRefresh = false) => {
        if (import.meta.env.VITE_USE_MOCK_AUTH === 'true') {
             return localStorage.getItem('mock_token') || 'mock-token-admin';
        }
        const { firebaseUser } = get();
        if (!firebaseUser) return null;
        return firebaseUser.getIdToken(forceRefresh);
    },
}));

// Initialize auth state listener
// This should be called once when the app starts
export function initAuthListener() {
    const store = useAuthStore.getState();

    if (import.meta.env.VITE_USE_MOCK_AUTH === 'true') {
        store.setLoading(false);
        store.setInitialized(true);
        return () => {};
    }

    const unsubscribe = onIdTokenChanged(auth, async (firebaseUser) => {
        if (firebaseUser) {
            store.setFirebaseUser(firebaseUser);
            await store.refreshUser();
        } else {
            store.setUser(null);
            store.setFirebaseUser(null);
            store.setLoading(false);
        }

        store.setInitialized(true);
    });

    return unsubscribe;
}
