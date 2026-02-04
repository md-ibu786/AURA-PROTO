/**
 * ============================================================================
 * FILE: user.ts
 * LOCATION: frontend/src/types/user.ts
 * ============================================================================
 *
 * PURPOSE:
 *    TypeScript type definitions for Firestore user documents
 *
 * ROLE IN PROJECT:
 *    Defines the shape of user data stored in Firestore users collection
 *    Used by auth store, API client, and UI components
 *
 * KEY COMPONENTS:
 *    - UserRole: Supported role enum values
 *    - UserStatus: Supported account status values
 *    - FirestoreUser: Canonical Firestore user document shape
 *    - CreateUserInput: Input shape for user creation
 *    - UpdateUserInput: Input shape for user updates
 *
 * DEPENDENCIES:
 *    - External: None
 *    - Internal: None
 *
 * USAGE:
 *    import { FirestoreUser, UserRole } from '../types/user';
 * ============================================================================
 */

export type UserRole = 'admin' | 'staff' | 'student';
export type UserStatus = 'active' | 'disabled';

export interface FirestoreUser {
    uid: string;
    email: string;
    displayName?: string;
    role: UserRole;
    status: UserStatus;
    departmentId: string | null;
    subjectIds: string[];
    createdAt: string; // ISO 8601 timestamp
    updatedAt: string; // ISO 8601 timestamp
    _v?: number; // Schema version
}

export interface CreateUserInput {
    email: string;
    displayName?: string;
    role: UserRole;
    status?: UserStatus;
    departmentId?: string | null;
    subjectIds?: string[];
}

export interface UpdateUserInput {
    email?: string;
    displayName?: string;
    role?: UserRole;
    status?: UserStatus;
    departmentId?: string | null;
    subjectIds?: string[];
}
