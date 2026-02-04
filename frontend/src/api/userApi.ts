// userApi.ts
// API functions for user management and profile retrieval

// Provides functions to interact with the /api/users and /api/auth/me
// endpoints. These functions are primarily used by the Admin Dashboard
// for user administration and by the auth store for session hydration.

// @see: client.ts - Base fetch wrappers and error classes
// @note: Admin functions require the 'admin' role on the backend

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
