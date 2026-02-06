/**
 * ============================================================================
 * FILE: auth.setup.ts
 * LOCATION: frontend/e2e/auth.setup.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Playwright global setup for authentication. Pre-authenticates test
 *    users and stores auth state for reuse across tests.
 *
 * ROLE IN PROJECT:
 *    Runs before other test projects to set up authenticated browser
 *    state, reducing login overhead in individual tests.
 *
 * KEY COMPONENTS:
 *    - Admin auth state setup
 *    - Auth state file storage for reuse
 *
 * DEPENDENCIES:
 *    - External: @playwright/test
 *    - Internal: fixtures.ts (auth helpers)
 *
 * USAGE:
 *    Configured as 'auth-setup' project in playwright.config.ts
 * ============================================================================
 */

import { test as setup, expect } from '@playwright/test';
import path from 'path';

const AUTH_STATE_DIR = path.join(__dirname, '..', 'playwright-report', '.auth');

/**
 * Set up admin authentication state for test reuse.
 * This runs once and stores the browser state so subsequent
 * tests can skip the login flow.
 */
setup('authenticate as admin', async ({ page }) => {
    const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

    if (useMockAuth) {
        // Mock auth: set localStorage values
        await page.goto('/login');
        await page.waitForLoadState('domcontentloaded');

        await page.evaluate(() => {
            localStorage.setItem(
                'mock_token',
                `mock-token-admin-${Date.now()}`
            );
            localStorage.setItem(
                'mock_user',
                JSON.stringify({
                    id: 'mock-admin-001',
                    email: 'admin@aura.edu',
                    displayName: 'Admin User',
                    role: 'admin',
                    departmentId: null,
                    departmentName: null,
                    subjectIds: [],
                    status: 'active',
                })
            );
        });

        await page.reload();
        await page.waitForLoadState('domcontentloaded');
    } else {
        // Real Firebase auth
        await page.goto('/login');
        await expect(page.locator('#email')).toBeVisible({ timeout: 10000 });

        const email = process.env.E2E_ADMIN_EMAIL || 'admin@aura.edu';
        const password = process.env.E2E_ADMIN_PASSWORD || 'admin123';

        await page.locator('#email').fill(email);
        await page.locator('#password').fill(password);
        await page.locator('button[type="submit"]').click();
        await page.waitForLoadState('networkidle');

        // Verify redirect away from login
        await expect(page).not.toHaveURL(/.*\/login.*/, { timeout: 10000 });
    }

    // Store auth state for reuse
    await page.context().storageState({
        path: path.join(AUTH_STATE_DIR, 'admin.json'),
    });
});

/**
 * Set up staff authentication state for test reuse.
 */
setup('authenticate as staff', async ({ page }) => {
    const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

    if (useMockAuth) {
        await page.goto('/login');
        await page.waitForLoadState('domcontentloaded');

        await page.evaluate(() => {
            localStorage.setItem(
                'mock_token',
                `mock-token-staff-${Date.now()}`
            );
            localStorage.setItem(
                'mock_user',
                JSON.stringify({
                    id: 'mock-staff-001',
                    email: 'staff@aura.edu',
                    displayName: 'Staff User',
                    role: 'staff',
                    departmentId: 'dept-cs',
                    departmentName: 'Computer Science',
                    subjectIds: ['subj-1', 'subj-2'],
                    status: 'active',
                })
            );
        });

        await page.reload();
        await page.waitForLoadState('domcontentloaded');
    } else {
        await page.goto('/login');
        await expect(page.locator('#email')).toBeVisible({ timeout: 10000 });

        const email = process.env.E2E_STAFF_EMAIL || 'staff@aura.edu';
        const password = process.env.E2E_STAFF_PASSWORD || 'staff123';

        await page.locator('#email').fill(email);
        await page.locator('#password').fill(password);
        await page.locator('button[type="submit"]').click();
        await page.waitForLoadState('networkidle');

        await expect(page).not.toHaveURL(/.*\/login.*/, { timeout: 10000 });
    }

    await page.context().storageState({
        path: path.join(AUTH_STATE_DIR, 'staff.json'),
    });
});

/**
 * Set up student authentication state for test reuse.
 */
setup('authenticate as student', async ({ page }) => {
    const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

    if (useMockAuth) {
        await page.goto('/login');
        await page.waitForLoadState('domcontentloaded');

        await page.evaluate(() => {
            localStorage.setItem(
                'mock_token',
                `mock-token-student-${Date.now()}`
            );
            localStorage.setItem(
                'mock_user',
                JSON.stringify({
                    id: 'mock-student-001',
                    email: 'student@aura.edu',
                    displayName: 'Student User',
                    role: 'student',
                    departmentId: 'dept-cs',
                    departmentName: 'Computer Science',
                    subjectIds: [],
                    status: 'active',
                })
            );
        });

        await page.reload();
        await page.waitForLoadState('domcontentloaded');
    } else {
        await page.goto('/login');
        await expect(page.locator('#email')).toBeVisible({ timeout: 10000 });

        const email = process.env.E2E_STUDENT_EMAIL || 'student@aura.edu';
        const password = process.env.E2E_STUDENT_PASSWORD || 'student123';

        await page.locator('#email').fill(email);
        await page.locator('#password').fill(password);
        await page.locator('button[type="submit"]').click();
        await page.waitForLoadState('networkidle');

        await expect(page).not.toHaveURL(/.*\/login.*/, { timeout: 10000 });
    }

    await page.context().storageState({
        path: path.join(AUTH_STATE_DIR, 'student.json'),
    });
});
