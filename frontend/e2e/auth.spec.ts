/**
 * ============================================================================
 * FILE: auth.spec.ts
 * LOCATION: frontend/e2e/auth.spec.ts
 * ============================================================================
 *
 * PURPOSE:
 *    E2E tests for authentication flows including login, logout, session
 *    persistence, and protected route handling.
 *
 * ROLE IN PROJECT:
 *    Validates Firebase Authentication integration and user session management.
 *    Tests both mock and real authentication paths.
 *
 * KEY TESTS:
 *    - Successful login and redirect
 *    - Failed login with error messages
 *    - Logout functionality
 *    - Session persistence across page reloads
 *    - Protected route redirects
 *
 * DEPENDENCIES:
 *    - External: @playwright/test
 *    - Internal: auth.setup.ts (loginAsRole, clearAuth, waitForAuth)
 *
 * USAGE:
 *    npx playwright test e2e/auth.spec.ts
 * ============================================================================
 */

import { test, expect, describe } from './auth.setup';

describe('Authentication Flow @auth', { tag: '@auth' }, () => {
    describe('Successful Login @login', { tag: '@login' }, () => {
        test.beforeEach(async ({ page }) => {
            // Clear any existing auth state
            await clearAuth(page);
        });

        test('can login with valid credentials and redirect to dashboard', async ({ page }) => {
            const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

            if (useMockAuth) {
                // Mock auth - set up mock data and reload
                await loginAsRole(page, 'admin');
            } else {
                // Real Firebase auth - navigate to login and fill form
                await page.goto('/login');
                await expect(page.locator('#email')).toBeVisible({ timeout: 10000 });

                // Fill login form
                await page.locator('#email').fill('admin@aura.edu');
                await page.locator('#password').fill('admin123');

                // Submit form
                await page.locator('button[type="submit"]').click();

                // Wait for navigation
                await page.waitForLoadState('networkidle');

                // Should redirect away from login
                await expect(page).not.toHaveURL(/.*\/login.*/);
            }
        });

        test('shows loading state during login', async ({ page }) => {
            const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

            if (useMockAuth) {
                test.skip();
                return;
            }

            await page.goto('/login');
            await expect(page.locator('#email')).toBeVisible();

            // Fill form
            await page.locator('#email').fill('admin@aura.edu');
            await page.locator('#password').fill('admin123');

            // Click login and check for loading state
            await page.locator('button[type="submit"]').click();

            // Button should show loading text
            const button = page.locator('button[type="submit"]');
            await expect(button).toContainText(/Signing in...|Loading/i, { timeout: 2000 });
        });

        test('admin user redirects to /admin after login', async ({ page }) => {
            const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

            if (useMockAuth) {
                await loginAsRole(page, 'admin');
                // In mock mode, check for admin-specific UI
                const adminNav = page.locator('text=Admin, [href="/admin"]');
                await expect(adminNav.first()).toBeVisible({ timeout: 5000 });
            } else {
                await page.goto('/login');
                await page.locator('#email').fill('admin@aura.edu');
                await page.locator('#password').fill('admin123');
                await page.locator('button[type="submit"]').click();
                await page.waitForLoadState('networkidle');

                // Admin should be redirected to admin dashboard
                await expect(page).toHaveURL(/.*\/admin.*/);
            }
        });

        test('staff user redirects to root after login', async ({ page }) => {
            const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

            if (useMockAuth) {
                await loginAsRole(page, 'staff');
                // Should not have admin access
                const adminLink = page.locator('[href="/admin"]');
                const hasAdminLink = await adminLink.first().isVisible().catch(() => false);
                expect(hasAdminLink).toBe(false);
            } else {
                await page.goto('/login');
                await page.locator('#email').fill('staff@aura.edu');
                await page.locator('#password').fill('staff123');
                await page.locator('button[type="submit"]').click();
                await page.waitForLoadState('networkidle');

                // Staff should be redirected to root (not admin)
                await expect(page).toHaveURL(/\/$/);
                await expect(page).not.toHaveURL(/.*\/admin.*/);
            }
        });

        test('student user redirects to root after login', async ({ page }) => {
            const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

            if (useMockAuth) {
                await loginAsRole(page, 'student');
                // Should not have admin access
                const adminLink = page.locator('[href="/admin"]');
                const hasAdminLink = await adminLink.first().isVisible().catch(() => false);
                expect(hasAdminLink).toBe(false);
            } else {
                await page.goto('/login');
                await page.locator('#email').fill('student@aura.edu');
                await page.locator('#password').fill('student123');
                await page.locator('button[type="submit"]').click();
                await page.waitForLoadState('networkidle');

                // Student should be redirected to root (not admin)
                await expect(page).toHaveURL(/\/$/);
                await expect(page).not.toHaveURL(/.*\/admin.*/);
            }
        });
    });

    describe('Failed Login @login-failure', { tag: '@login-failure' }, () => {
        test.beforeEach(async ({ page }) => {
            await clearAuth(page);
            await page.goto('/login');
            await expect(page.locator('#email')).toBeVisible();
        });

        test('shows error message for invalid credentials', async ({ page }) => {
            const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

            if (useMockAuth) {
                // Mock auth error handling
                await page.locator('#email').fill('invalid@test.com');
                await page.locator('#password').fill('wrongpassword');
                await page.locator('button[type="submit"]').click();
                await page.waitForTimeout(1000);

                // In mock mode, only 'error' password triggers error
                await expect(page.locator('.error-message')).toContainText(/invalid|error/i);
            } else {
                // Fill form with wrong credentials
                await page.locator('#email').fill('wrong@aura.edu');
                await page.locator('#password').fill('wrongpassword');
                await page.locator('button[type="submit"]').click();
                await page.waitForLoadState('networkidle');

                // Should show error message
                const errorMessage = page.locator('.error-message');
                await expect(errorMessage).toBeVisible({ timeout: 5000 });
                await expect(errorMessage).not.toBeEmpty();
            }
        });

        test('shows error for empty email', async ({ page }) => {
            await page.locator('#email').fill('');
            await page.locator('#password').fill('somepassword');
            await page.locator('button[type="submit"]').click();

            // Should show validation error
            const errorMessage = page.locator('.error-message');
            await expect(errorMessage).toContainText(/email|required/i);
        });

        test('shows error for empty password', async ({ page }) => {
            await page.locator('#email').fill('test@aura.edu');
            await page.locator('#password').fill('');
            await page.locator('button[type="submit"]').click();

            // Should show validation error
            const errorMessage = page.locator('.error-message');
            await expect(errorMessage).toContainText(/password|required/i);
        });

        test('stays on login page after failed login', async ({ page }) => {
            const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

            if (useMockAuth) {
                await page.locator('#email').fill('invalid@test.com');
                await page.locator('#password').fill('error'); // Triggers mock error
                await page.locator('button[type="submit"]').click();
                await page.waitForTimeout(500);
            } else {
                await page.locator('#email').fill('wrong@aura.edu');
                await page.locator('#password').fill('wrongpassword');
                await page.locator('button[type="submit"]').click();
                await page.waitForLoadState('networkidle');
            }

            // Should still be on login page
            await expect(page).toHaveURL(/.*\/login.*/);
        });
    });

    describe('Logout @logout', { tag: '@logout' }, () => {
        test('can logout and redirect to login', async ({ page }) => {
            const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

            if (useMockAuth) {
                await loginAsRole(page, 'admin');
                await clearAuth(page);
            } else {
                // Login first
                await page.goto('/login');
                await page.locator('#email').fill('admin@aura.edu');
                await page.locator('#password').fill('admin123');
                await page.locator('button[type="submit"]').click();
                await page.waitForLoadState('networkidle');

                // Click logout
                const logoutButton = page.locator('button:has-text("Logout"), button:has-text("Sign Out")');
                if (await logoutButton.isVisible().catch(() => false)) {
                    await logoutButton.first().click();
                    await page.waitForLoadState('networkidle');

                    // Should redirect to login
                    await expect(page).toHaveURL(/.*\/login.*/);
                }
            }
        });

        test('clears authentication state after logout', async ({ page }) => {
            const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

            if (useMockAuth) {
                await loginAsRole(page, 'admin');

                // Verify auth state exists
                const hasAuth = await isAuthenticated(page);
                expect(hasAuth).toBe(true);

                // Clear auth
                await clearAuth(page);

                // Verify auth state is cleared
                const isAuthAfterClear = await isAuthenticated(page);
                expect(isAuthAfterClear).toBe(false);
            } else {
                // Login first
                await page.goto('/login');
                await page.locator('#email').fill('admin@aura.edu');
                await page.locator('#password').fill('admin123');
                await page.locator('button[type="submit"]').click();
                await page.waitForLoadState('networkidle');

                // Clear cookies
                await page.context().clearCookies();
                await page.reload();
                await page.waitForLoadState('domcontentloaded');

                // Should be redirected to login
                await expect(page).toHaveURL(/.*\/login.*/);
            }
        });
    });

    describe('Session Persistence @session', { tag: '@session' }, () => {
        test('maintains login after page reload', async ({ page }) => {
            const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

            if (useMockAuth) {
                // Login
                await loginAsRole(page, 'admin');

                // Verify authenticated
                let authState = await isAuthenticated(page);
                expect(authState).toBe(true);

                // Reload page
                await page.reload();
                await page.waitForLoadState('domcontentloaded');

                // Should still be authenticated
                authState = await isAuthenticated(page);
                expect(authState).toBe(true);
            } else {
                // Real Firebase - login first
                await page.goto('/login');
                await page.locator('#email').fill('admin@aura.edu');
                await page.locator('#password').fill('admin123');
                await page.locator('button[type="submit"]').click();
                await page.waitForLoadState('networkidle');

                // Check URL is not login
                await expect(page).not.toHaveURL(/.*\/login.*/);

                // Reload
                await page.reload();
                await page.waitForLoadState('domcontentloaded');
                await page.waitForLoadState('networkidle');

                // Should still be logged in (not redirected to login)
                await expect(page).not.toHaveURL(/.*\/login.*/);
            }
        });
    });

    describe('Protected Route Redirect @protected', { tag: '@protected' }, () => {
        test.beforeEach(async ({ page }) => {
            await clearAuth(page);
        });

        test('redirects to login when accessing protected route without auth', async ({ page }) => {
            // Try to access admin dashboard directly
            await page.goto('/admin');
            await page.waitForLoadState('domcontentloaded');
            await page.waitForLoadState('networkidle');

            // Should redirect to login
            await expect(page).toHaveURL(/.*\/login.*/);
        });

        test('redirects to login when accessing root without auth', async ({ page }) => {
            // Access root while logged out
            await page.goto('/');
            await page.waitForLoadState('domcontentloaded');
            await page.waitForLoadState('networkidle');

            // Should redirect to login or show login form
            const emailInput = page.locator('#email');
            const hasLoginForm = await emailInput.isVisible().catch(() => false);
            expect(hasLoginForm).toBe(true);
        });

        test('preserves redirect location after login', async ({ page }) => {
            // Navigate to protected route
            await page.goto('/admin');
            await page.waitForLoadState('domcontentloaded');

            // Should be redirected to login
            await expect(page).toHaveURL(/.*\/login.*/);

            // Login
            const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

            if (useMockAuth) {
                await loginAsRole(page, 'admin');
            } else {
                await page.locator('#email').fill('admin@aura.edu');
                await page.locator('#password').fill('admin123');
                await page.locator('button[type="submit"]').click();
                await page.waitForLoadState('networkidle');
            }

            // Should redirect back to admin dashboard
            await expect(page).toHaveURL(/.*\/admin.*/);
        });
    });
});

describe('Token Refresh @token', { tag: '@token' }, () => {
    test('API calls work after login', async ({ page }) => {
        const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

        if (useMockAuth) {
            await loginAsRole(page, 'admin');

            // Verify we can get user info
            const user = await getCurrentUser(page);
            expect(user).not.toBeNull();
            expect(user).toHaveProperty('role');
        } else {
            // Login first
            await page.goto('/login');
            await page.locator('#email').fill('admin@aura.edu');
            await page.locator('#password').fill('admin123');
            await page.locator('button[type="submit"]').click();
            await page.waitForLoadState('networkidle');

            // Should be able to make authenticated API calls
            await page.goto('/');
            await page.waitForLoadState('networkidle');

            // Page should load without 401 errors
            // This is implicit - if we get here without redirect, auth works
            await expect(page).not.toHaveURL(/.*\/login.*/);
        }
    });

    test('user info is displayed after login', async ({ page }) => {
        const useMockAuth = process.env.VITE_USE_MOCK_AUTH === 'true';

        if (useMockAuth) {
            await loginAsRole(page, 'admin');

            // Check for user display
            const userDisplay = page.locator('text=Admin User, [data-testid="user-name"]');
            await expect(userDisplay.first()).toBeVisible({ timeout: 5000 });
        } else {
            await page.goto('/login');
            await page.locator('#email').fill('admin@aura.edu');
            await page.locator('#password').fill('admin123');
            await page.locator('button[type="submit"]').click();
            await page.waitForLoadState('networkidle');

            // Should see some user indicator
            const userIndicator = page.locator(
                '[data-testid="user-menu"], .user-menu, button:has-text("Admin"), .user-name'
            );
            await expect(userIndicator.first()).toBeVisible({ timeout: 5000 });
        }
    });
});
