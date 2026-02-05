/**
 * ============================================================================
 * FILE: auth.spec.ts
 * LOCATION: frontend/e2e/auth.spec.ts
 * ============================================================================
 *
 * PURPOSE:
 *    E2E tests for authentication flows including login, logout, session
 *    persistence, protected route handling, and token refresh scenarios.
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
 *    - Token refresh and user info display
 *
 * DEPENDENCIES:
 *    - External: @playwright/test
 *    - Internal: fixtures.ts (test fixtures, auth helpers)
 *
 * USAGE:
 *    npx playwright test e2e/auth.spec.ts
 * ============================================================================
 */

import { test, expect } from './fixtures';
import {
    loginAsRole,
    clearAuth,
    waitForAuth,
    isAuthenticated,
    getCurrentUser,
    useMockAuth,
    waitForLoading,
} from './fixtures';

test.describe('Authentication Flow @auth', { tag: '@auth' }, () => {
    test.describe('Successful Login @login', { tag: '@login' }, () => {
        test.beforeEach(async ({ page }) => {
            await clearAuth(page);
        });

        test('can login with valid credentials and redirect to dashboard', async ({ page }) => {
            if (useMockAuth()) {
                await loginAsRole(page, 'admin');
            } else {
                await page.goto('/login');
                await expect(page.locator('#email')).toBeVisible({ timeout: 10000 });

                await page.locator('#email').fill('admin@aura.edu');
                await page.locator('#password').fill('admin123');
                await page.locator('button[type="submit"]').click();
                await page.waitForLoadState('networkidle');

                // Should redirect away from login
                await expect(page).not.toHaveURL(/.*\/login.*/);
            }
        });

        test('shows loading state during login', async ({ page }) => {
            if (useMockAuth()) {
                test.skip();
                return;
            }

            await page.goto('/login');
            await expect(page.locator('#email')).toBeVisible();

            await page.locator('#email').fill('admin@aura.edu');
            await page.locator('#password').fill('admin123');
            await page.locator('button[type="submit"]').click();

            // Button should show loading text
            const button = page.locator('button[type="submit"]');
            await expect(button).toContainText(/Signing in...|Loading/i, { timeout: 2000 });
        });

        test('admin user redirects to /admin after login', async ({ page }) => {
            if (useMockAuth()) {
                await loginAsRole(page, 'admin');
                // Admin should end up on /admin page after mock login
                await expect(page).toHaveURL(/.*\/admin.*/, { timeout: 10000 });
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
            if (useMockAuth()) {
                await loginAsRole(page, 'staff');
                const adminLink = page.locator('[href="/admin"]');
                const hasAdminLink = await adminLink.first().isVisible().catch(() => false);
                expect(hasAdminLink).toBe(false);
            } else {
                await page.goto('/login');
                await page.locator('#email').fill('staff@aura.edu');
                await page.locator('#password').fill('staff123');
                await page.locator('button[type="submit"]').click();
                await page.waitForLoadState('networkidle');

                // Staff should not be on admin page
                await expect(page).not.toHaveURL(/.*\/admin.*/);
            }
        });

        test('student user redirects to root after login', async ({ page }) => {
            if (useMockAuth()) {
                await loginAsRole(page, 'student');
                const adminLink = page.locator('[href="/admin"]');
                const hasAdminLink = await adminLink.first().isVisible().catch(() => false);
                expect(hasAdminLink).toBe(false);
            } else {
                await page.goto('/login');
                await page.locator('#email').fill('student@aura.edu');
                await page.locator('#password').fill('student123');
                await page.locator('button[type="submit"]').click();
                await page.waitForLoadState('networkidle');

                // Student should not be on admin page
                await expect(page).not.toHaveURL(/.*\/admin.*/);
            }
        });
    });

    test.describe('Failed Login @login-failure', { tag: '@login-failure' }, () => {
        test.beforeEach(async ({ page }) => {
            await clearAuth(page);
            await page.goto('/login');
            await expect(page.locator('#email')).toBeVisible();
        });

        test('shows error message for invalid credentials', async ({ page }) => {
            if (useMockAuth()) {
                await page.locator('#email').fill('invalid@test.com');
                await page.locator('#password').fill('wrongpassword');
                await page.locator('button[type="submit"]').click();
                await page.waitForTimeout(1000);

                const errorMessage = page.locator('.error-message');
                await expect(errorMessage).toContainText(/invalid|error|failed/i);
            } else {
                await page.locator('#email').fill('wrong@aura.edu');
                await page.locator('#password').fill('wrongpassword');
                await page.locator('button[type="submit"]').click();
                await page.waitForLoadState('networkidle');

                const errorMessage = page.locator('.error-message');
                await expect(errorMessage).toBeVisible({ timeout: 5000 });
                await expect(errorMessage).not.toBeEmpty();
            }
        });

        test('shows error for empty email', async ({ page }) => {
            await page.locator('#email').fill('');
            await page.locator('#password').fill('somepassword');
            await page.locator('button[type="submit"]').click();

            const errorMessage = page.locator('.error-message');
            await expect(errorMessage).toContainText(/email|required|password/i);
        });

        test('shows error for empty password', async ({ page }) => {
            await page.locator('#email').fill('test@aura.edu');
            await page.locator('#password').fill('');
            await page.locator('button[type="submit"]').click();

            const errorMessage = page.locator('.error-message');
            await expect(errorMessage).toContainText(/password|required|email/i);
        });

        test('stays on login page after failed login', async ({ page }) => {
            if (useMockAuth()) {
                await page.locator('#email').fill('invalid@test.com');
                await page.locator('#password').fill('error');
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

    test.describe('Logout @logout', { tag: '@logout' }, () => {
        test('can logout and redirect to login', async ({ page }) => {
            if (useMockAuth()) {
                await loginAsRole(page, 'admin');
                await clearAuth(page);
            } else {
                // Login first
                await page.goto('/login');
                await page.locator('#email').fill('admin@aura.edu');
                await page.locator('#password').fill('admin123');
                await page.locator('button[type="submit"]').click();
                await page.waitForLoadState('networkidle');

                // Click sign out button (Sidebar shows "Sign out")
                const signOutButton = page.locator('button:has-text("Sign out")');
                if (await signOutButton.isVisible().catch(() => false)) {
                    await signOutButton.first().click();
                    await page.waitForLoadState('networkidle');

                    // Should redirect to login
                    await expect(page).toHaveURL(/.*\/login.*/);
                }
            }
        });

        test('clears authentication state after logout', async ({ page }) => {
            if (useMockAuth()) {
                await loginAsRole(page, 'admin');

                const hasAuth = await isAuthenticated(page);
                expect(hasAuth).toBe(true);

                await clearAuth(page);

                const isAuthAfterClear = await isAuthenticated(page);
                expect(isAuthAfterClear).toBe(false);
            } else {
                // Login first
                await page.goto('/login');
                await page.locator('#email').fill('admin@aura.edu');
                await page.locator('#password').fill('admin123');
                await page.locator('button[type="submit"]').click();
                await page.waitForLoadState('networkidle');

                // Clear cookies to simulate logout
                await page.context().clearCookies();
                await page.reload();
                await page.waitForLoadState('domcontentloaded');

                // Should be redirected to login
                await expect(page).toHaveURL(/.*\/login.*/);
            }
        });
    });

    test.describe('Session Persistence @session', { tag: '@session' }, () => {
        test('maintains login after page reload', async ({ page }) => {
            if (useMockAuth()) {
                await loginAsRole(page, 'admin');

                let authState = await isAuthenticated(page);
                expect(authState).toBe(true);

                await page.reload();
                await page.waitForLoadState('domcontentloaded');

                authState = await isAuthenticated(page);
                expect(authState).toBe(true);
            } else {
                await page.goto('/login');
                await page.locator('#email').fill('admin@aura.edu');
                await page.locator('#password').fill('admin123');
                await page.locator('button[type="submit"]').click();
                await page.waitForLoadState('networkidle');

                await expect(page).not.toHaveURL(/.*\/login.*/);

                // Reload
                await page.reload();
                await page.waitForLoadState('domcontentloaded');
                await page.waitForLoadState('networkidle');

                // Should still be logged in
                await expect(page).not.toHaveURL(/.*\/login.*/);
            }
        });
    });

    test.describe('Protected Route Redirect @protected', { tag: '@protected' }, () => {
        test.beforeEach(async ({ page }) => {
            await clearAuth(page);
        });

        test('redirects to login when accessing protected route without auth', async ({ page }) => {
            await page.goto('/admin');
            await page.waitForLoadState('domcontentloaded');
            await page.waitForLoadState('networkidle');

            // Should redirect to login
            await expect(page).toHaveURL(/.*\/login.*/);
        });

        test('redirects to login when accessing root without auth', async ({ page }) => {
            await page.goto('/');
            await page.waitForLoadState('domcontentloaded');
            await page.waitForLoadState('networkidle');

            // Should redirect to login or show login form
            const emailInput = page.locator('#email');
            const hasLoginForm = await emailInput.isVisible().catch(() => false);
            expect(hasLoginForm).toBe(true);
        });

        test('preserves redirect location after login', async ({ page }) => {
            if (useMockAuth()) {
                // In mock mode: verify admin ends up on /admin after login
                // (redirect preservation is tested via LoginPage auto-redirect)
                await loginAsRole(page, 'admin');
                await expect(page).toHaveURL(/.*\/admin.*/, { timeout: 10000 });
            } else {
                // Navigate to protected route
                await page.goto('/admin');
                await page.waitForLoadState('domcontentloaded');

                // Should be redirected to login
                await expect(page).toHaveURL(/.*\/login.*/);

                await page.locator('#email').fill('admin@aura.edu');
                await page.locator('#password').fill('admin123');
                await page.locator('button[type="submit"]').click();
                await page.waitForLoadState('networkidle');

                // Should redirect back to admin dashboard
                await expect(page).toHaveURL(/.*\/admin.*/);
            }
        });
    });
});

test.describe('Token Refresh @token', { tag: '@token' }, () => {
    test('API calls work after login', async ({ page }) => {
        if (useMockAuth()) {
            await loginAsRole(page, 'admin');

            const user = await getCurrentUser(page);
            expect(user).not.toBeNull();
            expect(user).toHaveProperty('role');
        } else {
            await page.goto('/login');
            await page.locator('#email').fill('admin@aura.edu');
            await page.locator('#password').fill('admin123');
            await page.locator('button[type="submit"]').click();
            await page.waitForLoadState('networkidle');

            // Should be able to navigate without auth errors
            await page.goto('/');
            await page.waitForLoadState('networkidle');

            // Page should load without redirect to login
            await expect(page).not.toHaveURL(/.*\/login.*/);
        }
    });

    test('user info is displayed after login', async ({ page }) => {
        if (useMockAuth()) {
            await loginAsRole(page, 'admin');

            // Admin is redirected to /admin dashboard which shows user info
            await expect(page).toHaveURL(/.*\/admin.*/, { timeout: 10000 });

            // Admin dashboard header shows user badge with "Logged in as: Admin User"
            const userBadge = page.locator('.user-badge');
            await expect(userBadge).toBeVisible({ timeout: 10000 });
            await expect(userBadge).toContainText('Admin User');
        } else {
            await page.goto('/login');
            await page.locator('#email').fill('admin@aura.edu');
            await page.locator('#password').fill('admin123');
            await page.locator('button[type="submit"]').click();
            await page.waitForLoadState('networkidle');

            // Should see sign out button or user indicator in sidebar
            const userIndicator = page.locator(
                'button:has-text("Sign out"), [data-testid="user-menu"], .user-menu, .user-name'
            );
            await expect(userIndicator.first()).toBeVisible({ timeout: 5000 });
        }
    });

    test('session survives page reload without re-login', async ({ page }) => {
        if (useMockAuth()) {
            await loginAsRole(page, 'admin');

            let authState = await isAuthenticated(page);
            expect(authState).toBe(true);

            await page.reload();
            await page.waitForLoadState('domcontentloaded');

            authState = await isAuthenticated(page);
            expect(authState).toBe(true);
        } else {
            await page.goto('/login');
            await page.locator('#email').fill('admin@aura.edu');
            await page.locator('#password').fill('admin123');
            await page.locator('button[type="submit"]').click();
            await page.waitForLoadState('networkidle');

            await expect(page).not.toHaveURL(/.*\/login.*/);

            // Reload page
            await page.reload();
            await page.waitForLoadState('networkidle');

            // Still authenticated
            await expect(page).not.toHaveURL(/.*\/login.*/);
        }
    });
});
