/**
 * ============================================================================
 * FILE: userApi.ts
 * LOCATION: frontend/src/api/userApi.ts
 * ============================================================================
 *
 * PURPOSE:
 *    API functions for user management and profile retrieval operations
 *
 * ROLE IN PROJECT:
 *    Provides typed methods to interact with /api/users and /api/auth/me
 *    endpoints. Used by AdminDashboard for user administration and by
 *    the auth store for session hydration and user data fetching.
 *
 * KEY COMPONENTS:
 *    - UserResponse: API response type for user data
 *    - UserCreate/UserUpdate: Input types for user mutations
 *    - getMe(): Fetch current authenticated user
 *    - listUsers(): List all users with optional filters (Admin only)
 *    - createUser/updateUser/deleteUser: CRUD operations (Admin only)
 *
 * DEPENDENCIES:
 *    - External: None
 *    - Internal: ./client.ts (fetchApi, DuplicateError)
 *
 * USAGE:
 *    import { getMe, listUsers, createUser } from '../api/userApi';
 *    const user = await getMe();
 * ============================================================================
 */

import { fetchApi } from './client';

export interface UserResponse {
    id: string;
    email: string;
    displayName: string | null;
    role: 'admin' | 'staff' | 'student';
    departmentId: string | null;
    subjectIds: string[] | null;
    status: 'active' | 'disabled';
    createdAt: string | null;
    updatedAt: string | null;
}

export interface UserCreate {
    email: string;
    password: string;
    displayName: string;
    role: 'admin' | 'staff' | 'student';
    departmentId?: string | null;
    subjectIds?: string[] | null;
}

export interface UserUpdate {
    displayName?: string;
    role?: 'admin' | 'staff' | 'student';
    departmentId?: string | null;
    subjectIds?: string[] | null;
    status?: 'active' | 'disabled';
}

/**
 * Get current authenticated user profile
 */
export async function getMe(): Promise<UserResponse> {
    return fetchApi<UserResponse>('/auth/me');
}

/**
 * List all users (Admin only)
 */
export async function listUsers(role?: string, departmentId?: string): Promise<UserResponse[]> {
    let url = '/users';
    const params = new URLSearchParams();
    if (role) params.append('role', role);
    if (departmentId) params.append('department_id', departmentId);
    
    const queryString = params.toString();
    if (queryString) url += `?${queryString}`;
    
    return fetchApi<UserResponse[]>(url);
}

/**
 * Create a new user (Admin only)
 */
export async function createUser(userData: UserCreate): Promise<UserResponse> {
    return fetchApi<UserResponse>('/users', {
        method: 'POST',
        body: JSON.stringify(userData)
    });
}

/**
 * Get user by ID (Admin only, or self)
 */
export async function getUser(userId: string): Promise<UserResponse> {
    return fetchApi<UserResponse>(`/users/${userId}`);
}

/**
 * Update a user (Admin only)
 */
export async function updateUser(userId: string, updateData: UserUpdate): Promise<UserResponse> {
    return fetchApi<UserResponse>(`/users/${userId}`, {
        method: 'PUT',
        body: JSON.stringify(updateData)
    });
}

/**
 * Delete a user (Admin only)
 */
export async function deleteUser(userId: string): Promise<void> {
    return fetchApi<void>(`/users/${userId}`, {
        method: 'DELETE'
    });
}
