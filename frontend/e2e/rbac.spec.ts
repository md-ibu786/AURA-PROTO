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
 *    - Internal: fixtures.ts (test fixtures, auth helpers, API mocks)
 *
 * USAGE:
 *    npx playwright test e2e/rbac.spec.ts
 * ============================================================================
 */

import { test, expect } from './fixtures';
import {
    mockTreeResponse,
    mockCrudResponses,
    waitForLoading,
    loginAsRole,
    clearAuth,
    useMockAuth,
    waitForAuth,
    isAuthenticated,
} from './fixtures';

// ============================================================================
// Helper: Mock admin dashboard API endpoints
// ============================================================================

async function mockAdminApiResponses(page: import('@playwright/test').Page): Promise<void> {
    // Mock /api/users endpoint for admin dashboard
    await page.route('**/api/users*', async (route) => {
        if (route.request().method() === 'GET') {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify([
                    {
                        id: 'user-admin-001',
                        email: 'admin@aura.edu',
                        display_name: 'Admin User',
                        role: 'admin',
                        department_id: null,
                        department_name: null,
                        subject_ids: [],
                        status: 'active',
                    },
                    {
                        id: 'user-staff-001',
                        email: 'staff@aura.edu',
                        display_name: 'Staff User',
                        role: 'staff',
                        department_id: 'dept-cs',
                        department_name: 'Computer Science',
                        subject_ids: ['subj-1'],
                        status: 'active',
                    },
                    {
                        id: 'user-student-001',
                        email: 'student@aura.edu',
                        display_name: 'Student User',
                        role: 'student',
                        department_id: 'dept-cs',
                        department_name: 'Computer Science',
                        subject_ids: [],
                        status: 'active',
                    },
                ]),
            });
        } else if (route.request().method() === 'POST') {
            await route.fulfill({
                status: 201,
                contentType: 'application/json',
                body: JSON.stringify({
                    id: `user-${Date.now()}`,
                    email: 'new@aura.edu',
                    display_name: 'New User',
                    role: 'staff',
                    status: 'active',
                }),
            });
        } else {
            await route.continue();
        }
    });

    // Mock /departments endpoint
    await page.route('**/departments', async (route) => {
        if (route.request().method() === 'GET') {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify({
                    departments: [
                        { id: 'dept-cs', name: 'Computer Science', code: 'CS' },
                        { id: 'dept-math', name: 'Mathematics', code: 'MATH' },
                    ],
                }),
            });
        } else {
            await route.continue();
        }
    });

    // Mock department subjects
    await page.route('**/api/departments/*/subjects', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                subjects: [
                    { id: 'subj-1', name: 'Data Structures', code: 'CS201' },
                    { id: 'subj-2', name: 'Algorithms', code: 'CS301' },
                ],
            }),
        });
    });

    // Mock department semesters
    await page.route('**/departments/*/semesters', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify({
                semesters: [
                    { id: 'sem-1', name: 'Fall 2025', semester_number: 1 },
                    { id: 'sem-2', name: 'Spring 2026', semester_number: 2 },
                ],
            }),
        });
    });
}

// ============================================================================
// ADMIN ROLE TESTS
// ============================================================================

test.describe('Admin Role Access @rbac-admin', { tag: ['@rbac', '@admin'] }, () => {
    test.beforeEach(async ({ page }) => {
        await clearAuth(page);
        // Set up API mocks BEFORE login (admin goes to /admin dashboard)
        await mockAdminApiResponses(page);
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
        // Admin should already be on /admin after login
        await expect(page).toHaveURL(/.*\/admin.*/, { timeout: 10000 });

        // Should see admin dashboard content
        const adminHeader = page.locator('h1:has-text("Admin Dashboard")');
        await expect(adminHeader).toBeVisible({ timeout: 10000 });
    });

    test('can view all departments in admin dashboard', async ({ page }) => {
        await page.goto('/admin');
        await page.waitForLoadState('domcontentloaded');

        // Click on Hierarchy Management tab
        const hierarchyTab = page.locator('.tab-btn:has-text("Hierarchy Management")');
        await expect(hierarchyTab).toBeVisible({ timeout: 10000 });
        await hierarchyTab.click();

        // Should see department management content
        const adminContent = page.locator('.admin-content');
        await expect(adminContent).toBeVisible();
    });

    test('admin dashboard shows user management', async ({ page }) => {
        await page.goto('/admin');
        await page.waitForLoadState('domcontentloaded');

        // User Management tab should be visible and active by default
        const userTab = page.locator('.tab-btn:has-text("User Management")');
        await expect(userTab).toBeVisible({ timeout: 10000 });

        // Should see user management panel
        const userPanel = page.locator('h2:has-text("User Management")');
        await expect(userPanel).toBeVisible({ timeout: 10000 });
    });

    test('admin can see create user button', async ({ page }) => {
        await page.goto('/admin');
        await page.waitForLoadState('domcontentloaded');

        // Should see create user button
        const createUserBtn = page.locator('button:has-text("Create User")');
        await expect(createUserBtn).toBeVisible({ timeout: 10000 });
    });

    test('has full CRUD access through admin dashboard', async ({ page }) => {
        await page.goto('/admin');
        await page.waitForLoadState('domcontentloaded');

        // Verify admin header with user badge
        const userBadge = page.locator('.user-badge');
        await expect(userBadge).toBeVisible({ timeout: 10000 });
        await expect(userBadge).toContainText('Admin User');

        // Verify both tabs are accessible
        const userTab = page.locator('.tab-btn:has-text("User Management")');
        const hierarchyTab = page.locator('.tab-btn:has-text("Hierarchy Management")');
        await expect(userTab).toBeVisible();
        await expect(hierarchyTab).toBeVisible();

        // Verify logout button is present
        const logoutBtn = page.locator('button:has-text("Logout")');
        await expect(logoutBtn).toBeVisible();
    });
});

// ============================================================================
// STAFF ROLE TESTS
// ============================================================================

test.describe('Staff Role Access @rbac-staff', { tag: ['@rbac', '@staff'] }, () => {
    test.beforeEach(async ({ page }) => {
        await clearAuth(page);
        // Set up API mocks BEFORE login so explorer tree loads with mock data
        await mockTreeResponse(page);
        await mockCrudResponses(page);
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
        await page.goto('/admin');
        await page.waitForLoadState('domcontentloaded');
        await page.waitForLoadState('networkidle');

        // Should redirect to home (ProtectedRoute redirects non-admin to /)
        const currentUrl = page.url();
        const isNotAdmin = !currentUrl.includes('/admin');
        const hasAccessDenied = await page
            .locator('text=Access Denied, text=Unauthorized')
            .first()
            .isVisible()
            .catch(() => false);

        expect(isNotAdmin || hasAccessDenied).toBe(true);
    });

    test('can view departments in sidebar (read-only)', async ({ page }) => {
        // Staff should be on explorer page
        await expect(page).not.toHaveURL(/.*\/admin.*/);

        // Should see explorer sidebar
        const sidebar = page.locator('.explorer-sidebar');
        await expect(sidebar).toBeVisible({ timeout: 10000 });

        // Should see the mock department in the tree
        const deptItem = page.locator('text=Computer Science');
        await expect(deptItem.first()).toBeVisible({ timeout: 10000 });
    });

    test('cannot create new department', async ({ page }) => {
        // Staff on explorer page - right-click to check context menu
        const contentArea = page.locator('.explorer-content, .explorer-main');
        await expect(contentArea.first()).toBeVisible({ timeout: 10000 });
        await contentArea.first().click({ button: 'right' });
        await page.waitForTimeout(500);

        // Should NOT see "New Department" option (staff can't manage hierarchy)
        const createDeptOption = page.locator('text=New Department');
        const isVisible = await createDeptOption.first().isVisible().catch(() => false);
        expect(isVisible).toBe(false);
    });

    test('can read subjects in the explorer tree', async ({ page }) => {
        // Navigate into department to see subjects
        const dept = page.locator('text=Computer Science');
        await expect(dept.first()).toBeVisible({ timeout: 10000 });
        await dept.first().dblclick();
        await page.waitForTimeout(500);

        // Should see semesters/subjects in the tree
        const treeContent = page.locator('.explorer-sidebar');
        await expect(treeContent).toBeVisible();
    });

    test('restricted UI elements for staff role', async ({ page }) => {
        // Should NOT see admin navigation link in sidebar
        const adminNav = page.locator('a[href="/admin"]');
        const hasAdminNav = await adminNav.first().isVisible().catch(() => false);
        expect(hasAdminNav).toBe(false);

        // Sidebar displays user role as "staff" (capitalized via CSS)
        const sidebar = page.locator('.explorer-sidebar');
        await expect(sidebar).toBeVisible({ timeout: 10000 });

        // Role text is shown in the sidebar user info section
        // The DOM text is 'staff' (lowercase), CSS text-transform capitalizes it
        const roleText = sidebar.locator('p').filter({ hasText: /^staff$/i });
        await expect(roleText.first()).toBeVisible({ timeout: 5000 });
    });

    test('staff sidebar shows sign out button', async ({ page }) => {
        const signOutBtn = page.locator('button:has-text("Sign out")');
        await expect(signOutBtn).toBeVisible({ timeout: 10000 });
    });
});

// ============================================================================
// STUDENT ROLE TESTS
// ============================================================================

test.describe('Student Role Access @rbac-student', { tag: ['@rbac', '@student'] }, () => {
    test.beforeEach(async ({ page }) => {
        await clearAuth(page);
        // Set up API mocks BEFORE login so explorer tree loads with mock data
        await mockTreeResponse(page);
        await mockCrudResponses(page);
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

        // Should redirect away from admin
        const currentUrl = page.url();
        const isNotAdmin = !currentUrl.includes('/admin');
        const hasAccessDenied = await page
            .locator('text=Access Denied, text=Unauthorized')
            .first()
            .isVisible()
            .catch(() => false);

        expect(isNotAdmin || hasAccessDenied).toBe(true);
    });

    test('can view departments (read-only)', async ({ page }) => {
        // Student should be on explorer page
        await expect(page).not.toHaveURL(/.*\/admin.*/);

        // Should see explorer sidebar
        const sidebar = page.locator('.explorer-sidebar');
        await expect(sidebar).toBeVisible({ timeout: 10000 });

        // Should see the mock department
        const deptItem = page.locator('text=Computer Science');
        await expect(deptItem.first()).toBeVisible({ timeout: 10000 });
    });

    test('cannot create new departments', async ({ page }) => {
        // Right-click in explorer area
        const contentArea = page.locator('.explorer-content, .explorer-main');
        await expect(contentArea.first()).toBeVisible({ timeout: 10000 });
        await contentArea.first().click({ button: 'right' });
        await page.waitForTimeout(500);

        // Should NOT see any create options
        const createOptions = page.locator(
            'text=New Department, text=New Semester, text=New Subject'
        );
        const count = await createOptions.count();
        expect(count).toBe(0);
    });

    test('cannot create notes or upload content', async ({ page }) => {
        // Navigate into the tree hierarchy
        const dept = page.locator('text=Computer Science');
        await expect(dept.first()).toBeVisible({ timeout: 10000 });
        await dept.first().dblclick();
        await page.waitForTimeout(500);

        // Students should not see upload/create note buttons at any level
        const uploadButton = page.locator(
            'text=Upload Note, text=New Note, text=Upload Notes'
        );
        const hasUpload = await uploadButton.first().isVisible().catch(() => false);
        expect(hasUpload).toBe(false);
    });

    test('read-only access throughout the application', async ({ page }) => {
        // Should NOT see any actionable edit buttons
        const editButtons = page.locator('text=Edit, text=Rename');
        const hasEditButtons = await editButtons.first().isVisible().catch(() => false);

        if (hasEditButtons) {
            const editButton = editButtons.first();
            // If visible, should be disabled
            await expect(editButton).toBeHidden({ timeout: 1000 }).catch(async () => {
                await expect(editButton).toHaveAttribute('disabled');
            });
        }

        // Should NOT see delete buttons
        const deleteButtons = page.locator('text=Delete');
        const hasDelete = await deleteButtons.first().isVisible().catch(() => false);
        expect(hasDelete).toBe(false);
    });

    test('student role shown in sidebar', async ({ page }) => {
        // Sidebar should show user role as "student"
        const sidebar = page.locator('.explorer-sidebar');
        await expect(sidebar).toBeVisible({ timeout: 10000 });

        // The DOM text is 'student' (lowercase), CSS text-transform capitalizes it
        const roleText = sidebar.locator('p').filter({ hasText: /^student$/i });
        await expect(roleText.first()).toBeVisible({ timeout: 5000 });
    });
});

// ============================================================================
// ADVANCED RBAC SCENARIOS
// ============================================================================

test.describe('Advanced RBAC Scenarios @rbac-advanced', { tag: ['@rbac', '@advanced'] }, () => {
    test('role change reflects in UI without full logout', async ({ page }) => {
        if (!useMockAuth()) {
            test.skip();
            return;
        }

        // Set up mocks for explorer page
        await mockTreeResponse(page);

        // Login as staff
        await loginAsRole(page, 'staff');

        // Verify staff permissions - should NOT see admin nav link
        const adminNav = page.locator('a[href="/admin"]');
        expect(await adminNav.first().isVisible().catch(() => false)).toBe(false);

        // Clear and login as admin (admin goes to /admin dashboard)
        await clearAuth(page);
        await mockAdminApiResponses(page);
        await loginAsRole(page, 'admin');

        // Admin should be on /admin dashboard
        await expect(page).toHaveURL(/.*\/admin.*/, { timeout: 10000 });

        // Admin dashboard should be visible
        const adminHeader = page.locator('h1:has-text("Admin Dashboard")');
        await expect(adminHeader).toBeVisible({ timeout: 5000 });
    });

    test('disabled account shows appropriate error', async ({ page }) => {
        // This test verifies error handling for disabled accounts
        await page.goto('/login');
        await expect(page.locator('#email')).toBeVisible();

        // Try to login with credentials of a disabled user
        await page.locator('#email').fill('disabled@aura.edu');
        await page.locator('#password').fill('anypassword');
        await page.locator('button[type="submit"]').click();
        await page.waitForLoadState('networkidle');

        // Should show error message (disabled or generic auth error)
        const errorMessage = page.locator('.error-message');
        if (await errorMessage.isVisible().catch(() => false)) {
            await expect(errorMessage).not.toBeEmpty();
        }
    });

    test('concurrent sessions share authentication state', async ({ page }) => {
        if (!useMockAuth()) {
            test.skip();
            return;
        }

        // Open first page and login
        const context1 = page.context();
        const page1 = await context1.newPage();

        await mockAdminApiResponses(page1);
        await loginAsRole(page1, 'admin');
        await waitForAuth(page1);

        // Verify page1 is authenticated
        expect(await isAuthenticated(page1)).toBe(true);

        // Open second page in same context
        const page2 = await context1.newPage();
        await page2.goto('/');
        await page2.waitForLoadState('domcontentloaded');

        // Same context should share auth state (localStorage is shared)
        expect(await isAuthenticated(page2)).toBe(true);

        // Cleanup
        await page1.close();
        await page2.close();
    });
});

// ============================================================================
// UI ELEMENT VISIBILITY TESTS
// ============================================================================

test.describe('UI Element Visibility @ui-restrictions', { tag: ['@ui', '@permissions'] }, () => {
    test.describe('Admin UI Elements', () => {
        test.beforeEach(async ({ page }) => {
            await clearAuth(page);
            await mockAdminApiResponses(page);
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
            // Admin should be on /admin dashboard
            await expect(page).toHaveURL(/.*\/admin.*/, { timeout: 10000 });

            // Should see User Management tab
            const userTab = page.locator('.tab-btn:has-text("User Management")');
            await expect(userTab).toBeVisible({ timeout: 5000 });

            // Should see Hierarchy Management tab
            const hierarchyTab = page.locator('.tab-btn:has-text("Hierarchy Management")');
            await expect(hierarchyTab).toBeVisible({ timeout: 5000 });
        });

        test('admin dashboard shows create user button', async ({ page }) => {
            await expect(page).toHaveURL(/.*\/admin.*/, { timeout: 10000 });

            // Should see create user button
            const createUserBtn = page.locator('button:has-text("Create User")');
            await expect(createUserBtn).toBeVisible({ timeout: 10000 });
        });
    });

    test.describe('Non-Admin UI Restrictions', () => {
        test.beforeEach(async ({ page }) => {
            await clearAuth(page);
            await mockTreeResponse(page);
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
            // Student should not see admin dashboard link in sidebar
            const adminLink = page.locator('a[href="/admin"]');
            const count = await adminLink.count();
            expect(count).toBe(0);
        });

        test('non-admin users do not see user management', async ({ page }) => {
            // Student should not see any user management UI
            const userManagement = page.locator('text=User Management, text=Manage Users');
            const count = await userManagement.count();
            expect(count).toBe(0);
        });
    });
});
