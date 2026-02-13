/**
 * ============================================================================
 * FILE: fixtures.ts
 * LOCATION: frontend/e2e/fixtures.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Playwright fixtures and API mocks for AURA-NOTES-MANAGER E2E tests.
 *
 * ROLE IN PROJECT:
 *    Provides mock data generators, route interceptors, and auth utilities.
 *    Includes CRUD/status mocks, shared wait helpers, and role-based login.
 *    Aligns mock payloads with FileSystemNode types for consistency.
 *
 * KEY COMPONENTS:
 *    - Auth utilities: loginAsRole, clearAuth, waitForAuth, isAuthenticated
 *    - Mock data: mockExplorerTree, mockDepartment, mockSemester, etc.
 *    - API mocks: mockTreeResponse, mockCrudResponses, mockKGProcessingResponses
 *    - Test fixtures: explorerPage, adminPage, staffPage, studentPage
 *
 * DEPENDENCIES:
 *    - External: @playwright/test
 *    - Internal: Matches FileSystemNode types from src/types
 *
 * USAGE:
 *    import { test, expect, loginAsRole, clearAuth } from './fixtures';
 * ============================================================================
 */

import { test as base, expect, Page, Route } from '@playwright/test';

// ============================================================================
// AUTH UTILITIES
// ============================================================================

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
 * Check if mock authentication is enabled.
 */
export function isMockAuthEnabled(): boolean {
    return process.env.VITE_USE_MOCK_AUTH === 'true';
}

/**
 * Login as a specific role.
 * Uses mock authentication if VITE_USE_MOCK_AUTH is set.
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

    if (isMockAuthEnabled()) {
        // Mock authentication path
        await page.evaluate(
            ({ role }) => {
                // Set mock token
                localStorage.setItem('mock_token', `mock-token-${role}-${Date.now()}`);

                // Set mock user in localStorage
                const mockUser = {
                    id: `mock-${role}-001`,
                    email: `${role}@aura.edu`,
                    displayName: `${role.charAt(0).toUpperCase() + role.slice(1)} User`,
                    role,
                    departmentId: role === 'admin' ? null : 'dept-1',
                    departmentName: role === 'admin' ? null : 'Computer Science',
                    subjectIds: role === 'staff' ? ['subj-1', 'subj-2'] : [],
                    status: 'active',
                };
                localStorage.setItem('mock_user', JSON.stringify(mockUser));
            },
            { role }
        );

        // Navigate to the app to trigger auth initialization with stored mock user
        await page.goto('/');
        await page.waitForLoadState('domcontentloaded');

        // Wait for auth to initialize and any redirects to settle
        await waitForAuth(page);
        await page.waitForLoadState('networkidle');
    } else {
        // Real Firebase authentication path
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
}

/**
 * Clear authentication state.
 * Safely navigates to the app first to avoid SecurityError on about:blank.
 */
export async function clearAuth(page: Page): Promise<void> {
    // Ensure we're on the app origin before accessing localStorage
    const currentUrl = page.url();
    if (currentUrl === 'about:blank' || !currentUrl.startsWith('http')) {
        await page.goto('/login');
        await page.waitForLoadState('domcontentloaded');
    }

    if (isMockAuthEnabled()) {
        // Clear mock auth data from localStorage
        try {
            await page.evaluate(() => {
                localStorage.removeItem('mock_token');
                localStorage.removeItem('mock_user');
            });
        } catch {
            // localStorage may not be accessible - navigate first then retry
            await page.goto('/login');
            await page.waitForLoadState('domcontentloaded');
            await page.evaluate(() => {
                localStorage.removeItem('mock_token');
                localStorage.removeItem('mock_user');
            });
        }
    } else {
        // Try to logout via the UI (sidebar "Sign out" button)
        try {
            const logoutButton = page.locator('button:has-text("Sign out"), button:has-text("Logout")');
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
 */
export async function isAuthenticated(page: Page): Promise<boolean> {
    // Check for mock auth
    try {
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
    } catch {
        // localStorage not accessible (about:blank) - not authenticated
        return false;
    }

    // Check for Firebase auth state (Sidebar "Sign out" button)
    const logoutButton = page.locator('button:has-text("Sign out"), button:has-text("Logout")');
    const userMenu = page.locator('[data-testid="user-menu"], .user-menu');

    return (await logoutButton.isVisible().catch(() => false)) ||
           (await userMenu.isVisible().catch(() => false));
}

/**
 * Get current authenticated user info.
 */
export async function getCurrentUser(page: Page): Promise<object | null> {
    // Check mock auth first
    try {
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
    } catch {
        // localStorage not accessible
        return null;
    }

    // Try to get user from UI
    const userDisplayName = page.locator('[data-testid="user-name"], .user-name, .user-display-name');
    if (await userDisplayName.isVisible().catch(() => false)) {
        const name = await userDisplayName.textContent();
        return { displayName: name };
    }

    return null;
}

// ============================================================================
// MOCK DATA GENERATORS
// ============================================================================

/**
 * FileSystemNode types matching the application's type definitions.
 */
export type NodeType = 'department' | 'semester' | 'subject' | 'module' | 'note';

export interface MockNode {
  id: string;
  label: string;
  type: NodeType;
  children?: MockNode[];
  meta?: {
    createdAt?: string;
    updatedAt?: string;
    processingStatus?: 'pending' | 'processing' | 'completed' | 'failed';
  };
}

/**
 * Mock user constant for consistent test data.
 */
export const mockUser = {
  id: 'test-user-001',
  name: 'Test User',
  email: 'test@aura.edu',
};

/**
 * Creates a mock department node.
 */
export function mockDepartment(
  id: string,
  label: string,
  children: MockNode[] = []
): MockNode {
  return {
    id,
    label,
    type: 'department',
    children,
    meta: {
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    },
  };
}

/**
 * Creates a mock semester node.
 */
export function mockSemester(
  id: string,
  label: string,
  children: MockNode[] = []
): MockNode {
  return {
    id,
    label,
    type: 'semester',
    children,
    meta: {
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    },
  };
}

/**
 * Creates a mock subject node.
 */
export function mockSubject(
  id: string,
  label: string,
  children: MockNode[] = []
): MockNode {
  return {
    id,
    label,
    type: 'subject',
    children,
    meta: {
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    },
  };
}

/**
 * Creates a mock module node.
 */
export function mockModule(
  id: string,
  label: string,
  children: MockNode[] = []
): MockNode {
  return {
    id,
    label,
    type: 'module',
    children,
    meta: {
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    },
  };
}

/**
 * Creates a mock note node.
 */
export function mockNote(
  id: string,
  label: string,
  processingStatus: 'pending' | 'processing' | 'completed' | 'failed' = 'pending'
): MockNode {
  return {
    id,
    label,
    type: 'note',
    meta: {
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      processingStatus,
    },
  };
}

/**
 * Creates a complete mock explorer tree for testing.
 */
export function mockExplorerTree(): MockNode[] {
  return [
    mockDepartment('dept-1', 'Computer Science', [
      mockSemester('sem-1', 'Fall 2025', [
        mockSubject('subj-1', 'Data Structures', [
          mockModule('mod-1', 'Module 1: Arrays', [
            mockNote('note-1', 'Lecture 1.pdf', 'completed'),
            mockNote('note-2', 'Lecture 2.pdf', 'pending'),
          ]),
          mockModule('mod-2', 'Module 2: Linked Lists', [
            mockNote('note-3', 'Lab Notes.pdf', 'processing'),
          ]),
        ]),
      ]),
    ]),
    mockDepartment('dept-2', 'Mathematics', [
      mockSemester('sem-2', 'Spring 2026', [
        mockSubject('subj-2', 'Calculus', []),
      ]),
    ]),
  ];
}

// ============================================================================
// API MOCKS
// ============================================================================

/**
 * Helper to mock the explorer tree API response.
 */
export async function mockTreeResponse(page: Page, tree: MockNode[] = mockExplorerTree()): Promise<void> {
  await page.route('**/api/explorer/tree*', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(tree),
    });
  });
}

/**
 * Helper to prime the explorer tree query cache.
 */
export async function primeExplorerTreeCache(page: Page): Promise<void> {
  await page.evaluate(async () => {
    try {
      await fetch('/api/explorer/tree?depth=5');
    } catch (error) {
      console.warn('Failed to prime explorer tree cache', error);
    }
  });
}

/**
 * Helper to mock CRUD API responses.
 */
export async function mockCrudResponses(page: Page): Promise<void> {
  // Mock create department
  await page.route('**/api/explorer/departments', async (route: Route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON();
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: `dept-${Date.now()}`,
          label: body.name || body.label,
          type: 'department',
        }),
      });
    } else {
      await route.continue();
    }
  });

  await page.route('**/api/explorer/semesters', async (route: Route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON();
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: `sem-${Date.now()}`,
          label: body.name || body.label,
          type: 'semester',
        }),
      });
    } else {
      await route.continue();
    }
  });

  await page.route('**/api/explorer/subjects', async (route: Route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON();
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: `subj-${Date.now()}`,
          label: body.name || body.label,
          type: 'subject',
        }),
      });
    } else {
      await route.continue();
    }
  });

  await page.route('**/api/explorer/modules', async (route: Route) => {
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON();
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: `mod-${Date.now()}`,
          label: body.name || body.label,
          type: 'module',
        }),
      });
    } else {
      await route.continue();
    }
  });

  // Mock delete operations
  await page.route('**/api/explorer/departments/*', async (route: Route) => {
    if (route.request().method() === 'DELETE') {
      await route.fulfill({ status: 204 });
    } else if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: route.request().url().split('/').pop(),
          label: body.name || body.label,
          type: 'department',
        }),
      });
    } else {
      await route.continue();
    }
  });

  await page.route('**/api/explorer/semesters/*', async (route: Route) => {
    if (route.request().method() === 'DELETE') {
      await route.fulfill({ status: 204 });
    } else if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: route.request().url().split('/').pop(),
          label: body.name || body.label,
          type: 'semester',
        }),
      });
    } else {
      await route.continue();
    }
  });

  await page.route('**/api/explorer/subjects/*', async (route: Route) => {
    if (route.request().method() === 'DELETE') {
      await route.fulfill({ status: 204 });
    } else if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: route.request().url().split('/').pop(),
          label: body.name || body.label,
          type: 'subject',
        }),
      });
    } else {
      await route.continue();
    }
  });

  await page.route('**/api/explorer/modules/*', async (route: Route) => {
    if (route.request().method() === 'DELETE') {
      await route.fulfill({ status: 204 });
    } else if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: route.request().url().split('/').pop(),
          label: body.name || body.label,
          type: 'module',
        }),
      });
    } else {
      await route.continue();
    }
  });

  await page.route('**/api/explorer/notes/*', async (route: Route) => {
    if (route.request().method() === 'DELETE') {
      await route.fulfill({ status: 204 });
    } else if (route.request().method() === 'PUT') {
      const body = route.request().postDataJSON();
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: route.request().url().split('/').pop(),
          label: body.title || body.name || body.label,
          type: 'note',
        }),
      });
    } else {
      await route.continue();
    }
  });
}

/**
 * Helper to mock KG processing API responses.
 */
export async function mockKGProcessingResponses(page: Page): Promise<void> {
  await page.route('**/api/kg/process', async (route: Route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          success: true,
          message: 'Documents queued for processing',
          jobIds: ['job-1', 'job-2'],
        }),
      });
    } else {
      await route.continue();
    }
  });

  await page.route('**/api/kg/status/*', async (route: Route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'completed',
        progress: 100,
      }),
    });
  });
}

/**
 * Waits for loading state to complete.
 */
export async function waitForLoading(page: Page): Promise<void> {
  // Wait for any spinners to disappear
  const spinner = page.locator('.spinner, [data-loading="true"], [aria-busy="true"]');

  // First check if spinner exists
  const spinnerCount = await spinner.count();
  if (spinnerCount > 0) {
    await expect(spinner.first()).not.toBeVisible({ timeout: 10000 });
  }

  // Also wait for network to be idle
  await page.waitForLoadState('networkidle');
}

/**
 * Waits for a specific API response.
 */
export async function waitForApiResponse(
  page: Page,
  urlPattern: string | RegExp
): Promise<void> {
  await page.waitForResponse(urlPattern, { timeout: 10000 });
}

// ============================================================================
// TEST FIXTURES
// ============================================================================

/**
 * Extended test fixture with pre-configured mocks and auth helpers.
 */
export const test = base.extend<{
  explorerPage: Page;
  authenticatedPage: Page;
  adminPage: Page;
  staffPage: Page;
  studentPage: Page;
}>({
  // Explorer page fixture - base for all tests
  explorerPage: async ({ page }, runTest) => {
    // Set up default mocks
    await mockTreeResponse(page);
    await mockCrudResponses(page);

    // Navigate to the app
    await page.goto('/');
    await waitForLoading(page);

    await runTest(page);
  },

  // Authenticated page fixture - starts logged in as admin
  authenticatedPage: async ({ page }, runTest) => {
    if (isMockAuthEnabled()) {
      await loginAsRole(page, 'admin');
    }

    await runTest(page);

    // Cleanup
    await clearAuth(page);
  },

  // Admin page fixture
  adminPage: async ({ page }, runTest) => {
    if (isMockAuthEnabled()) {
      await loginAsRole(page, 'admin');
    }

    await runTest(page);

    await clearAuth(page);
  },

  // Staff page fixture
  staffPage: async ({ page }, runTest) => {
    if (isMockAuthEnabled()) {
      await loginAsRole(page, 'staff');
    }

    await runTest(page);

    await clearAuth(page);
  },

  // Student page fixture
  studentPage: async ({ page }, runTest) => {
    if (isMockAuthEnabled()) {
      await loginAsRole(page, 'student');
    }

    await runTest(page);

    await clearAuth(page);
  },
});

export { expect };
