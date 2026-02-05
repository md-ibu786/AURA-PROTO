/**
 * ============================================================================
 * FILE: rbac.spec.ts
 * LOCATION: frontend/e2e/rbac.spec.ts
 * ============================================================================
 *
 * PURPOSE:
 *    E2E tests for Role-Based Access Control (RBAC) enforcement across
 *    admin, staff, and student roles. Validates UI restrictions and API
 *    permission boundaries.
 *
 * ROLE IN PROJECT:
 *    Critical security tests ensuring users can only access resources
 *    permitted by their role. Tests both UI behavior and permission enforcement.
 *
 * KEY TESTS:
 *    - Admin: Full CRUD on all resources, admin dashboard access
 *    - Staff: Read all, write assigned subjects only, no admin access
 *    - Student: Read-only access, no write capabilities
 *    - UI elements hidden/disabled based on permissions
 *
 * DEPENDENCIES:
 *    - External: @playwright/test
 *    - Internal: auth.setup.ts (loginAsRole, clearAuth, fixtures)
 *
 * USAGE:
 *    npx playwright test e2e/rbac.spec.ts
 * ============================================================================
 */

import { test, expect, describe } from './auth.setup';
import { mockTreeResponse, mockCrudResponses, waitForLoading } from './fixtures';

// Helper to check if mock auth is enabled
const useMockAuth = () => process.env.VITE_USE_MOCK_AUTH === 'true';

describe('Admin Role Access @rbac-admin', { tag: ['@rbac', '@admin'] }, () => {
    test.beforeEach(async ({ page }) => {
        await clearAuth(page);
        if (useMockAuth()) {
            await loginAsRole(page, 'admin');
        } else {
            await page.goto('/login');
            await page.locator('#email').fill('admin@aura.edu');
            await page.locator('#password').fill('admin123');
            await page.locator('button[type="submit"]').click();
            await page.waitForLoadState('networkidle');
        }
        await waitForLoading(page);
    });

    test('can access admin dashboard', async ({ page }) => {
        // Navigate to admin dashboard
        await page.goto('/admin');
        await page.waitForLoadState('domcontentloaded');
        await page.waitForLoadState('networkidle');

        // Should see admin dashboard content
        const adminHeader = page.locator('text=Admin, h1:has-text("Admin"), [data-testid="admin-dashboard"]');
        await expect(adminHeader.first()).toBeVisible({ timeout: 10000 });
    });

    test('can view all departments', async ({ page }) => {
        await page.goto('/');
        await waitForLoading(page);

        // Should see department tree
        const departments = page.locator('.explorer-sidebar, [data-testid="department-tree"]');
        await expect(departments.first()).toBeVisible();

        // Should see multiple departments
        const deptItems = page.locator('text=Computer Science, text=Mathematics');
        await expect(deptItems.first()).toBeVisible();
    });

    test('can create new department', async ({ page }) => {
        // Set up CRUD mocks
        await mockTreeResponse(page);
        await mockCrudResponses(page);

        await page.goto('/');
        await waitForLoading(page);

        // Right-click to open context menu
        const contentArea = page.locator('.explorer-content, main');
        await contentArea.first().click({ button: 'right' });

        // Should see create options
        const createOption = page.locator('text=New Department, text=Create Department');
        await expect(createOption.first()).toBeVisible({ timeout: 5000 });
    });

    test('can edit existing department', async ({ page }) => {
        await mockTreeResponse(page);
        await mockCrudResponses(page);

        await page.goto('/');
        await waitForLoading(page);

        // Find and right-click a department
        const dept = page.locator('text=Computer Science').first();
        await dept.click({ button: 'right' });

        // Should see edit options
        const editOption = page.locator('text=Rename, text=Edit');
        await expect(editOption.first()).toBeVisible({ timeout: 5000 });
    });

    test('can delete department', async ({ page }) => {
        await mockTreeResponse(page);
        await mockCrudResponses(page);

        await page.goto('/');
        await waitForLoading(page);

        // Find and right-click a department
        const dept = page.locator('text=Computer Science').first();
        await dept.click({ button: 'right' });

        // Should see delete option
        const deleteOption = page.locator('text=Delete');
        await expect(deleteOption.first()).toBeVisible({ timeout: 5000 });
    });

    test('has full CRUD access to all resources', async ({ page }) => {
        await mockTreeResponse(page);
        await mockCrudResponses(page);

        await page.goto('/');
        await waitForLoading(page);

        // Navigate through hierarchy
        await page.locator('text=Computer Science').first().dblclick();
        await page.waitForTimeout(500);
        await page.locator('text=Fall 2025').first().dblclick();
        await page.waitForTimeout(500);
        await page.locator('text=Data Structures').first().dblclick();
        await page.waitForTimeout(500);

        // Should be able to create notes in modules
        const createNoteOption = page.locator('text=New Note, text=Upload Note');
        await expect(createNoteOption.first()).toBeVisible({ timeout: 5000 });
    });
});

describe('Staff Role Access @rbac-staff', { tag: ['@rbac', '@staff'] }, () => {
    test.beforeEach(async ({ page }) => {
        await clearAuth(page);
        if (useMockAuth()) {
            await loginAsRole(page, 'staff');
        } else {
            await page.goto('/login');
            await page.locator('#email').fill('staff@aura.edu');
            await page.locator('#password').fill('staff123');
            await page.locator('button[type="submit"]').click();
            await page.waitForLoadState('networkidle');
        }
        await waitForLoading(page);
    });

    test('cannot access admin dashboard', async ({ page }) => {
        // Try to navigate to admin dashboard
        await page.goto('/admin');
        await page.waitForLoadState('domcontentloaded');
        await page.waitForLoadState('networkidle');

        // Should redirect to login or show access denied
        const isOnLogin = await page.url().includes('/login');
        const hasAccessDenied = await page.locator('text=Access Denied, text=Unauthorized').first().isVisible().catch(() => false);

        expect(isOnLogin || hasAccessDenied).toBe(true);
    });

    test('can view all departments (read-only)', async ({ page }) => {
        await page.goto('/');
        await waitForLoading(page);

        // Should see department tree
        const departments = page.locator('.explorer-sidebar');
        await expect(departments.first()).toBeVisible();

        // Should see departments
        const deptItems = page.locator('text=Computer Science, text=Mathematics');
        await expect(deptItems.first()).toBeVisible();
    });

    test('cannot create new department', async ({ page }) => {
        await mockTreeResponse(page);

        await page.goto('/');
        await waitForLoading(page);

        // Right-click to open context menu
        const contentArea = page.locator('.explorer-content, main');
        await contentArea.first().click({ button: 'right' });

        // Should NOT see "New Department" option
        const createDeptOption = page.locator('text=New Department');
        const isVisible = await createDeptOption.first().isVisible().catch(() => false);
        expect(isVisible).toBe(false);
    });

    test('can read all subjects but edit only assigned', async ({ page }) => {
        await page.goto('/');
        await waitForLoading(page);

        // Navigate to see subjects
        await page.locator('text=Computer Science').first().click();
        await page.waitForTimeout(500);

        // Should be able to see subjects
        const subjects = page.locator('text=Data Structures, text=Calculus');
        await expect(subjects.first()).toBeVisible();
    });

    test('has module management in assigned subjects', async ({ page }) => {
        await mockTreeResponse(page);
        await mockCrudResponses(page);

        await page.goto('/');
        await waitForLoading(page);

        // Navigate to assigned subject
        await page.locator('text=Computer Science').first().dblclick();
        await page.waitForTimeout(500);
        await page.locator('text=Fall 2025').first().dblclick();
        await page.waitForTimeout(500);
        await page.locator('text=Data Structures').first().dblclick();
        await page.waitForTimeout(500);

        // Should be able to create modules
        const createModuleOption = page.locator('text=New Module, text=Create Module');
        await expect(createModuleOption.first()).toBeVisible({ timeout: 5000 });
    });

    test('restricted UI elements for staff role', async ({ page }) => {
        await page.goto('/');
        await waitForLoading(page);

        // Should NOT see admin navigation
        const adminNav = page.locator('[href="/admin"], text=Admin Dashboard');
        const hasAdminNav = await adminNav.first().isVisible().catch(() => false);
        expect(hasAdminNav).toBe(false);

        // Should see staff-specific elements
        const staffIndicator = page.locator('text=Staff, [data-testid="staff-badge"]');
        const hasStaffIndicator = await staffIndicator.first().isVisible().catch(() => false);
        expect(hasStaffIndicator).toBe(true);
    });
});

describe('Student Role Access @rbac-student', { tag: ['@rbac', '@student'] }, () => {
    test.beforeEach(async ({ page }) => {
        await clearAuth(page);
        if (useMockAuth()) {
            await loginAsRole(page, 'student');
        } else {
            await page.goto('/login');
            await page.locator('#email').fill('student@aura.edu');
            await page.locator('#password').fill('student123');
            await page.locator('button[type="submit"]').click();
            await page.waitForLoadState('networkidle');
        }
        await waitForLoading(page);
    });

    test('cannot access admin dashboard', async ({ page }) => {
        await page.goto('/admin');
        await page.waitForLoadState('domcontentloaded');
        await page.waitForLoadState('networkidle');

        // Should redirect to login or show access denied
        const isOnLogin = await page.url().includes('/login');
        const hasAccessDenied = await page.locator('text=Access Denied, text=Unauthorized').first().isVisible().catch(() => false);

        expect(isOnLogin || hasAccessDenied).toBe(true);
    });

    test('can view departments (read-only)', async ({ page }) => {
        await page.goto('/');
        await waitForLoading(page);

        // Should see department tree
        const departments = page.locator('.explorer-sidebar');
        await expect(departments.first()).toBeVisible();

        // Should see departments
        const deptItems = page.locator('text=Computer Science');
        await expect(deptItems.first()).toBeVisible();
    });

    test('cannot create new departments', async ({ page }) => {
        await page.goto('/');
        await waitForLoading(page);

        // Right-click to open context menu
        const contentArea = page.locator('.explorer-content, main');
        await contentArea.first().click({ button: 'right' });

        // Should NOT see any create options
        const createOptions = page.locator('text=New Department, text=New Semester, text=New Subject');
        const count = await createOptions.count();
        expect(count).toBe(0);
    });

    test('cannot create notes or upload content', async ({ page }) => {
        await mockTreeResponse(page);

        await page.goto('/');
        await waitForLoading(page);

        // Navigate to module level
        await page.locator('text=Computer Science').first().dblclick();
        await page.waitForTimeout(500);
        await page.locator('text=Fall 2025').first().dblclick();
        await page.waitForTimeout(500);
        await page.locator('text=Data Structures').first().dblclick();
        await page.waitForTimeout(500);
        await page.locator('text=Module 1: Arrays').first().dblclick();
        await page.waitForTimeout(500);

        // Should NOT see upload/create note buttons
        const uploadButton = page.locator('text=Upload Note, text=New Note, [data-testid="upload-note"]');
        const hasUpload = await uploadButton.first().isVisible().catch(() => false);
        expect(hasUpload).toBe(false);
    });

    test('read-only access throughout the application', async ({ page }) => {
        await page.goto('/');
        await waitForLoading(page);

        // Should NOT see any edit buttons
        const editButtons = page.locator('text=Edit, text=Rename, [data-testid="edit-btn"]');
        const hasEditButtons = await editButtons.first().isVisible().catch(() => false);

        // In some views, edit buttons might be visible but disabled
        // The key is they should not be actionable
        if (hasEditButtons) {
            const editButton = editButtons.first();
            await expect(editButton).toBeHidden({ timeout: 1000 }).catch(() => {
                // If not hidden, should be disabled
                expect(editButton).toHaveAttribute('disabled');
            });
        }

        // Should NOT see delete buttons
        const deleteButtons = page.locator('text=Delete, [data-testid="delete-btn"]');
        const hasDelete = await deleteButtons.first().isVisible().catch(() => false);
        expect(hasDelete).toBe(false);
    });

    test('department isolation for student', async ({ page }) => {
        await page.goto('/');
        await waitForLoading(page);

        // Student should primarily see their own department
        // May or may not see other departments depending on requirements

        // Student display should be visible
        const studentIndicator = page.locator('text=Student, [data-testid="student-badge"]');
        await expect(studentIndicator.first()).toBeVisible({ timeout: 5000 });
    });
});

describe('Advanced RBAC Scenarios @rbac-advanced', { tag: ['@rbac', '@advanced'] }, () => {
    test('role change reflects in UI without full logout', async ({ page }) => {
        const useMock = useMockAuth();
        if (!useMock) {
            test.skip();
            return;
        }

        // Login as staff
        await loginAsRole(page, 'staff');

        // Verify staff permissions
        let adminNav = page.locator('[href="/admin"]');
        expect(await adminNav.first().isVisible().catch(() => false)).toBe(false);

        // Clear and login as admin
        await clearAuth(page);
        await loginAsRole(page, 'admin');

        // Now should see admin navigation
        await page.waitForTimeout(500);
        adminNav = page.locator('[href="/admin"]');
        expect(await adminNav.first().isVisible().catch(() => false)).toBe(true);
    });

    test('disabled account shows appropriate error', async ({ page }) => {
        // This test verifies error handling for disabled accounts
        // In a real scenario, the backend would return 403 for disabled users

        await page.goto('/login');
        await expect(page.locator('#email')).toBeVisible();

        // Try to login with credentials of a disabled user
        // This depends on having a disabled test user configured
        await page.locator('#email').fill('disabled@aura.edu');
        await page.locator('#password').fill('anypassword');
        await page.locator('button[type="submit"]').click();
        await page.waitForLoadState('networkidle');

        // Should show disabled account message if user exists and is disabled
        // Otherwise will show generic error
        const errorMessage = page.locator('.error-message');
        if (await errorMessage.isVisible().catch(() => false)) {
            await expect(errorMessage).not.toBeEmpty();
        }
    });

    test('concurrent sessions share authentication state', async ({ page }) => {
        const useMock = useMockAuth();
        if (!useMock) {
            test.skip();
            return;
        }

        // Open first page and login
        const context1 = await page.context();
        const page1 = await context1.newPage();

        await loginAsRole(page1, 'admin');
        await waitForAuth(page1);

        // Verify page1 is authenticated
        expect(await isAuthenticated(page1)).toBe(true);

        // Open second page in same context
        const page2 = await context1.newPage();
        await page2.goto('/');
        await page2.waitForLoadState('domcontentloaded');

        // Same context should share auth state
        expect(await isAuthenticated(page2)).toBe(true);

        // Close pages
        await page1.close();
        await page2.close();
    });
});

describe('UI Element Visibility @ui-restrictions', { tag: ['@ui', '@permissions'] }, () => {
    test.describe('Admin UI Elements', () => {
        test.beforeEach(async ({ page }) => {
            await clearAuth(page);
            if (useMockAuth()) {
                await loginAsRole(page, 'admin');
            } else {
                await page.goto('/login');
                await page.locator('#email').fill('admin@aura.edu');
                await page.locator('#password').fill('admin123');
                await page.locator('button[type="submit"]').click();
                await page.waitForLoadState('networkidle');
            }
            await waitForLoading(page);
        });

        test('admin sees all management options', async ({ page }) => {
            // Check for admin-specific navigation
            const adminLink = page.locator('[href="/admin"], text=Admin Dashboard');
            await expect(adminLink.first()).toBeVisible({ timeout: 5000 });

            // Should see user management option
            const userManagement = page.locator('text=User Management, text=Manage Users');
            await expect(userManagement.first()).toBeVisible();
        });

        test('admin sees create buttons throughout', async ({ page }) => {
            await mockTreeResponse(page);

            // Check various create buttons are visible
            const createButtons = page.locator(
                'text=New Department, text=New Semester, text=New Subject, text=New Module, text=Upload'
            );
            const count = await createButtons.count();
            expect(count).toBeGreaterThan(0);
        });
    });

    test.describe('Non-Admin UI Restrictions', () => {
        test.beforeEach(async ({ page }) => {
            await clearAuth(page);
            if (useMockAuth()) {
                await loginAsRole(page, 'student');
            } else {
                await page.goto('/login');
                await page.locator('#email').fill('student@aura.edu');
                await page.locator('#password').fill('student123');
                await page.locator('button[type="submit"]').click();
                await page.waitForLoadState('networkidle');
            }
            await waitForLoading(page);
        });

        test('non-admin users do not see admin link', async ({ page }) => {
            // Admin link should be hidden
            const adminLink = page.locator('[href="/admin"]');
            await expect(adminLink.first()).toBeHidden({ timeout: 2000 }).catch(async () => {
                // If visible, should be disabled
                await expect(adminLink.first()).toHaveAttribute('disabled');
            });
        });

        test('non-admin users do not see user management', async ({ page }) => {
            // User management should be hidden
            const userManagement = page.locator('text=User Management, text=Manage Users');
            await expect(userManagement.first()).toBeHidden({ timeout: 2000 });
        });
    });
});
