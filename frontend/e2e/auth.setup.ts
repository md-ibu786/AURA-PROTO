/**
 * ============================================================================
 * FILE: auth.setup.ts
 * LOCATION: frontend/e2e/auth.setup.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Playwright authentication setup and helper functions for Firebase RBAC
 *    E2E testing. Provides programmatic login, logout, and role-based helpers.
 *
 * ROLE IN PROJECT:
 *    Authentication utilities used by all E2E tests that require user login.
 *    Supports mock authentication (VITE_USE_MOCK_AUTH=true) and real Firebase.
 *
 * KEY COMPONENTS:
 *    - loginAsRole: Login with specific role credentials
 *    - clearAuth: Logout and clear authentication state
 *    - waitForAuth: Wait for auth state to initialize
 *    - mockUserData: Role-specific mock user data
 *
 * DEPENDENCIES:
 *    - External: @playwright/test
 *    - Internal: fixtures.ts (for mockTreeResponse, etc.)
 *
 * USAGE:
 *    import { loginAsRole, clearAuth } from './auth.setup';
 *    await loginAsRole(page, 'admin');
 *    await clearAuth(page);
 * ============================================================================
 */

import { test as base, type Page, type Locator, expect } from '@playwright/test';

// Role type definition
export type UserRole = 'admin' | 'staff' | 'student';

// Test user credentials (loaded from environment variables)
interface TestUser {
    email: string;
    password: string;
    role: UserRole;
    displayName: string;
}

// Test user configuration
const testUsers: Record<UserRole, TestUser> = {
    admin: {
        email: process.env.E2E_ADMIN_EMAIL || 'admin@aura.edu',
        password: process.env.E2E_ADMIN_PASSWORD || 'admin123',
        role: 'admin',
        displayName: 'Admin User',
    },
    staff: {
        email: process.env.E2E_STAFF_EMAIL || 'staff@aura.edu',
        password: process.env.E2E_STAFF_PASSWORD || 'staff123',
        role: 'staff',
        displayName: 'Staff User',
    },
    student: {
        email: process.env.E2E_STUDENT_EMAIL || 'student@aura.edu',
        password: process.env.E2E_STUDENT_PASSWORD || 'student123',
        role: 'student',
        displayName: 'Student User',
    },
};

/**
 * Mock user data for testing without real Firebase auth.
 * Used when VITE_USE_MOCK_AUTH=true.
 */
export const mockUserData: Record<UserRole, object> = {
    admin: {
        id: 'mock-admin-001',
        email: 'admin@aura.edu',
        displayName: 'Admin User',
        role: 'admin',
        departmentId: null,
        departmentName: null,
        subjectIds: [],
        status: 'active',
    },
    staff: {
        id: 'mock-staff-001',
        email: 'staff@aura.edu',
        displayName: 'Staff User',
        role: 'staff',
        departmentId: 'dept-cs',
        departmentName: 'Computer Science',
        subjectIds: ['subj-1', 'subj-2'],
        status: 'active',
    },
    student: {
        id: 'mock-student-001',
        email: 'student@aura.edu',
        displayName: 'Student User',
        role: 'student',
        departmentId: 'dept-cs',
        departmentName: 'Computer Science',
        subjectIds: [],
        status: 'active',
    },
};

/**
 * Login as a specific role.
 * Uses mock authentication if VITE_USE_MOCK_AUTH is set.
 *
 * @param page - Playwright page instance
 * @param role - User role to login as
 * @param options - Login options (mock credentials override)
 */
export async function loginAsRole(
    page: Page,
    role: UserRole,
    options?: { email?: string; password?: string }
): Promise<void> {
    const user = testUsers[role];
    const email = options?.email || user.email;
    const password = options?.password || user.password;

    // Navigate to login page
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded');

    // Check if mock auth is enabled
    const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

    if (useMockAuth) {
        // Mock authentication path
        await performMockLogin(page, email, password, role);
    } else {
        // Real Firebase authentication path
        await performRealLogin(page, email, password);
    }
}

/**
 * Perform login with mock authentication.
 */
async function performMockLogin(
    page: Page,
    email: string,
    password: string,
    role: UserRole
): Promise<void> {
    // Set mock auth state in localStorage
    await page.evaluate(
        ({ email, role }) => {
            // Set mock token
            localStorage.setItem('mock_token', `mock-token-${role}-${Date.now()}`);

            // Set mock user in localStorage
            const mockUser = {
                id: `mock-${role}-001`,
                email,
                displayName: `${role.charAt(0).toUpperCase() + role.slice(1)} User`,
                role,
                departmentId: role === 'admin' ? null : 'dept-cs',
                departmentName: role === 'admin' ? null : 'Computer Science',
                subjectIds: role === 'staff' ? ['subj-1', 'subj-2'] : [],
                status: 'active',
            };
            localStorage.setItem('mock_user', JSON.stringify(mockUser));
        },
        { email, role }
    );

    // Reload page to pick up mock auth state
    await page.reload();
    await page.waitForLoadState('domcontentloaded');

    // Wait for auth to initialize
    await waitForAuth(page);
}

/**
 * Perform login with real Firebase authentication.
 */
async function performRealLogin(
    page: Page,
    email: string,
    password: string
): Promise<void> {
    // Fill in login form
    const emailInput = page.locator('#email');
    const passwordInput = page.locator('#password');
    const loginButton = page.locator('button[type="submit"]');

    await expect(emailInput).toBeVisible({ timeout: 10000 });
    await emailInput.fill(email);
    await passwordInput.fill(password);

    // Submit login form
    await loginButton.click();

    // Wait for navigation or error
    await page.waitForLoadState('networkidle');

    // Check for error message
    const errorMessage = page.locator('.error-message');
    if (await errorMessage.isVisible().catch(() => false)) {
        throw new Error(`Login failed: ${await errorMessage.textContent()}`);
    }
}

/**
 * Clear authentication state.
 * Logs out user and clears localStorage/mock data.
 *
 * @param page - Playwright page instance
 */
export async function clearAuth(page: Page): Promise<void> {
    // Check if using mock auth
    const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

    if (useMockAuth) {
        // Clear mock auth data from localStorage
        await page.evaluate(() => {
            localStorage.removeItem('mock_token');
            localStorage.removeItem('mock_user');
        });
    } else {
        // Try to logout via the UI
        try {
            const logoutButton = page.locator('button:has-text("Logout"), button:has-text("Sign Out")');
            if (await logoutButton.first().isVisible().catch(() => false)) {
                await logoutButton.first().click();
                await page.waitForLoadState('networkidle');
            }
        } catch {
            // Ignore logout errors - user might already be logged out
        }
    }

    // Clear storage and reload
    await page.context().clearCookies();
    await page.reload();
    await page.waitForLoadState('domcontentloaded');
}

/**
 * Wait for authentication state to initialize.
 * Checks for loading state to complete.
 *
 * @param page - Playwright page instance
 */
export async function waitForAuth(page: Page): Promise<void> {
    // Wait for page to be fully loaded
    await page.waitForLoadState('domcontentloaded');

    // Wait for any loading indicators to disappear
    const loadingSelector = '[data-loading="true"], .spinner, .loading';
    try {
        await page.waitForFunction((selector) => {
            const elements = document.querySelectorAll(selector);
            return Array.from(elements).every((el) => !el.isConnected || getComputedStyle(el).display === 'none');
        }, loadingSelector, { timeout: 10000 });
    } catch {
        // Loading state might not exist - that's OK
    }

    // Wait for network to be idle
    await page.waitForLoadState('networkidle');
}

/**
 * Check if user is currently authenticated.
 *
 * @param page - Playwright page instance
 * @returns True if user appears to be logged in
 */
export async function isAuthenticated(page: Page): Promise<boolean> {
    // Check for mock auth
    const mockUser = await page.evaluate(() => {
        try {
            const user = localStorage.getItem('mock_user');
            return user ? JSON.parse(user) : null;
        } catch {
            return null;
        }
    });

    if (mockUser) {
        return true;
    }

    // Check for Firebase auth state
    // Look for authenticated UI elements
    const logoutButton = page.locator('button:has-text("Logout"), button:has-text("Sign Out")');
    const userMenu = page.locator('[data-testid="user-menu"], .user-menu');

    return (await logoutButton.isVisible().catch(() => false)) ||
           (await userMenu.isVisible().catch(() => false));
}

/**
 * Get current authenticated user info.
 *
 * @param page - Playwright page instance
 * @returns User info object or null if not authenticated
 */
export async function getCurrentUser(page: Page): Promise<object | null> {
    // Check mock auth first
    const mockUser = await page.evaluate(() => {
        try {
            const user = localStorage.getItem('mock_user');
            return user ? JSON.parse(user) : null;
        } catch {
            return null;
        }
    });

    if (mockUser) {
        return mockUser;
    }

    // Try to get user from UI
    const userDisplayName = page.locator('[data-testid="user-name"], .user-name, .user-display-name');
    if (await userDisplayName.isVisible().catch(() => false)) {
        const name = await userDisplayName.textContent();
        return { displayName: name };
    }

    return null;
}

/**
 * Extended test fixture with authentication helpers.
 */
export const test = base.extend<{
    authenticatedPage: Page;
    adminPage: Page;
    staffPage: Page;
    studentPage: Page;
}>({
    // Authenticated page fixture - starts logged in as admin
    authenticatedPage: async ({ page }, use) => {
        const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

        if (useMockAuth) {
            await loginAsRole(page, 'admin');
        }

        await use(page);

        // Cleanup
        await clearAuth(page);
    },

    // Admin page fixture
    adminPage: async ({ page }, use) => {
        const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

        if (useMockAuth) {
            await loginAsRole(page, 'admin');
        }

        await use(page);

        await clearAuth(page);
    },

    // Staff page fixture
    staffPage: async ({ page }, use) => {
        const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

        if (useMockAuth) {
            await loginAsRole(page, 'staff');
        }

        await use(page);

        await clearAuth(page);
    },

    // Student page fixture
    studentPage: async ({ page }, use) => {
        const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

        if (useMockAuth) {
            await loginAsRole(page, 'student');
        }

        await use(page);

        await clearAuth(page);
    },
});

export { expect };
