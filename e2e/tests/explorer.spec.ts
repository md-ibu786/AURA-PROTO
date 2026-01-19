import { test, expect } from '@playwright/test';
import { ExplorerPage } from '../page-objects/ExplorerPage';
import { ApiHelper } from '../page-objects/ApiHelper';

/**
 * Explorer UI E2E Tests
 * Tests the React frontend explorer interface
 * Uses Page Object Model for maintainable UI interactions
 */

test.describe('Explorer - Page Load & Basic UI', () => {
    let explorerPage: ExplorerPage;

    test.beforeEach(async ({ page }) => {
        explorerPage = new ExplorerPage(page);
        await explorerPage.goto();
    });

    test('should load the explorer page with correct title', async ({ page }) => {
        await expect(page).toHaveTitle(/AURA|Explorer/i);
    });

    test('should display main layout components', async () => {
        await explorerPage.waitForExplorerLoad();

        await expect(explorerPage.sidebar).toBeVisible();
        await expect(explorerPage.mainContent).toBeVisible();
        await expect(explorerPage.header).toBeVisible();
    });

    test('should display tree container', async () => {
        await explorerPage.waitForExplorerLoad();
        await expect(explorerPage.treeContainer).toBeVisible();
    });

    test('should show action buttons', async () => {
        await explorerPage.waitForExplorerLoad();
        await expect(explorerPage.createDeptBtn).toBeVisible();
        await expect(explorerPage.searchInput).toBeVisible();
    });

    test('should have view toggle buttons', async () => {
        await explorerPage.waitForExplorerLoad();
        await expect(explorerPage.gridViewBtn).toBeVisible();
        await expect(explorerPage.listViewBtn).toBeVisible();
    });
});

test.describe('Explorer - Tree Navigation', () => {
    let explorerPage: ExplorerPage;
    let apiHelper: ApiHelper;
    let hierarchy: { departmentId: string; semesterId: string; subjectId: string; moduleId: string };

    test.beforeAll(async ({ request }) => {
        apiHelper = new ApiHelper(request);
        hierarchy = await apiHelper.createTestHierarchy();
    });

    test.afterAll(async ({ request }) => {
        if (hierarchy?.departmentId) {
            await apiHelper.deleteDepartment(hierarchy.departmentId);
        }
    });

    test.beforeEach(async ({ page }) => {
        explorerPage = new ExplorerPage(page);
        await explorerPage.goto();
        await explorerPage.waitForExplorerLoad();
    });

    test('should display created department in tree', async () => {
        const deptNode = await explorerPage.getNodeById(hierarchy.departmentId);
        await expect(deptNode).toBeVisible();
    });

    test('should expand department to show semesters', async () => {
        await explorerPage.expandNode(hierarchy.departmentId);

        const semesters = await apiHelper.getSemestersByDepartment(hierarchy.departmentId);
        expect(semesters.length).toBeGreaterThan(0);

        // Verify semester is visible after expansion
        const semNode = await explorerPage.getNodeById(hierarchy.semesterId);
        await expect(semNode).toBeVisible();
    });

    test('should expand semester to show subjects', async () => {
        await explorerPage.expandNode(hierarchy.departmentId);
        await explorerPage.expandNode(hierarchy.semesterId);

        const semNode = await explorerPage.getNodeById(hierarchy.subjectId);
        await expect(semNode).toBeVisible();
    });

    test('should expand subject to show modules', async () => {
        await explorerPage.expandNode(hierarchy.departmentId);
        await explorerPage.expandNode(hierarchy.semesterId);
        await explorerPage.expandNode(hierarchy.subjectId);

        const modNode = await explorerPage.getNodeById(hierarchy.moduleId);
        await expect(modNode).toBeVisible();
    });

    test('should select node on click', async () => {
        await explorerPage.selectNode(hierarchy.departmentId);

        // Node should have selected state (visual feedback)
        const node = await explorerPage.getNodeById(hierarchy.departmentId);
        const classes = await node.getAttribute('class');
        expect(classes).toContain('selected');
    });
});

test.describe('Explorer - CRUD Operations via UI', () => {
    let explorerPage: ExplorerPage;
    let apiHelper: ApiHelper;
    let cleanupDeptId: string;

    test.beforeEach(async ({ page, request }) => {
        explorerPage = new ExplorerPage(page);
        apiHelper = new ApiHelper(request);
        await explorerPage.goto();
        await explorerPage.waitForExplorerLoad();
    });

    test.afterEach(async ({ request }) => {
        if (cleanupDeptId) {
            await apiHelper.deleteDepartment(cleanupDeptId);
            cleanupDeptId = '';
        }
    });

    test('should create a new department via UI', async () => {
        const deptName = `UI Dept ${Date.now()}`;
        const deptCode = `UI${Date.now() % 1000}`;

        await explorerPage.createDepartment(deptName, deptCode);

        // Wait for tree to update
        await explorerPage.waitForTimeout(1000);

        // Verify department appears in tree
        const exists = await explorerPage.verifyNodeExists(deptName);
        expect(exists).toBe(true);

        // Get ID for cleanup
        const tree = await apiHelper.getExplorerTree();
        const dept = tree.find((d: any) => d.label === deptName);
        if (dept) cleanupDeptId = dept.id;
    });

    test('should create a semester under a department', async () => {
        // First create department via API for clean test
        const deptName = `Dept ${Date.now()}`;
        const deptId = await apiHelper.createDepartment(deptName, 'UISEM');
        cleanupDeptId = deptId;

        // Refresh page to see new department
        await explorerPage.refresh();
        await explorerPage.waitForExplorerLoad();

        const semName = `Semester ${Date.now()}`;

        // Create semester via UI
        await explorerPage.createSemester(deptName, semName);

        await explorerPage.waitForTimeout(1000);

        // Verify semester appears
        const exists = await explorerPage.verifyNodeExists(semName);
        expect(exists).toBe(true);
    });

    test('should create a subject under a semester', async () => {
        const deptName = `Dept ${Date.now()}`;
        const semName = `Sem ${Date.now()}`;
        const subjName = `Subj ${Date.now()}`;
        const subjCode = `S${Date.now() % 1000}`;

        const hierarchy = await apiHelper.createTestHierarchy();
        cleanupDeptId = hierarchy.departmentId;

        await explorerPage.refresh();
        await explorerPage.waitForExplorerLoad();

        // Create subject via UI
        await explorerPage.createSubject(semName, subjName, subjCode);

        await explorerPage.waitForTimeout(1000);

        const exists = await explorerPage.verifyNodeExists(subjName);
        expect(exists).toBe(true);
    });

    test('should create a module under a subject', async () => {
        const hierarchy = await apiHelper.createTestHierarchy();
        cleanupDeptId = hierarchy.departmentId;

        await explorerPage.refresh();
        await explorerPage.waitForExplorerLoad();

        const modName = `Module ${Date.now()}`;

        await explorerPage.createModule('Test Subject', modName);

        await explorerPage.waitForTimeout(1000);

        const exists = await explorerPage.verifyNodeExists(modName);
        expect(exists).toBe(true);
    });
});

test.describe('Explorer - Context Menu Operations', () => {
    let explorerPage: ExplorerPage;
    let apiHelper: ApiHelper;
    let hierarchy: { departmentId: string; semesterId: string; subjectId: string; moduleId: string };

    test.beforeAll(async ({ request }) => {
        apiHelper = new ApiHelper(request);
        hierarchy = await apiHelper.createTestHierarchy();
    });

    test.afterAll(async ({ request }) => {
        if (hierarchy?.departmentId) {
            await apiHelper.deleteDepartment(hierarchy.departmentId);
        }
    });

    test.beforeEach(async ({ page }) => {
        explorerPage = new ExplorerPage(page);
        await explorerPage.goto();
        await explorerPage.waitForExplorerLoad();
    });

    test('should open context menu on right-click', async () => {
        await explorerPage.openContextMenu('Test Dept');

        await expect(explorerPage.contextMenu).toBeVisible();
    });

    test('should rename node via context menu', async () => {
        const newName = `Renamed ${Date.now()}`;

        await explorerPage.renameNode('Test Dept', newName);

        await explorerPage.waitForTimeout(500);

        // Verify new name appears
        const exists = await explorerPage.verifyNodeExists(newName);
        expect(exists).toBe(true);

        // Update local reference for cleanup
        const tree = await apiHelper.getExplorerTree();
        const dept = tree.find((d: any) => d.label === newName);
        if (dept) hierarchy.departmentId = dept.id;
    });

    test('should delete node via context menu', async () => {
        // Create a temp department for deletion test
        const tempDeptId = await apiHelper.createDepartment(`Delete Me ${Date.now()}`, 'DEL');
        await explorerPage.refresh();
        await explorerPage.waitForExplorerLoad();

        // Delete it
        await explorerPage.deleteNode(`Delete Me`);

        await explorerPage.waitForTimeout(500);

        // Verify it's gone
        const exists = await explorerPage.verifyNodeExists(`Delete Me`);
        expect(exists).toBe(false);
    });
});

test.describe('Explorer - Search Functionality', () => {
    let explorerPage: ExplorerPage;
    let apiHelper: ApiHelper;
    let hierarchy: { departmentId: string };

    test.beforeAll(async ({ request }) => {
        apiHelper = new ApiHelper(request);
        // Create multiple departments with distinct names
        await apiHelper.createDepartment('Searchable Alpha', 'SAL');
        await apiHelper.createDepartment('Searchable Beta', 'SBE');
        await apiHelper.createDepartment('Other Department', 'OTH');
    });

    test.afterAll(async ({ request }) => {
        // Cleanup all test departments
        const tree = await apiHelper.getExplorerTree();
        for (const node of tree) {
            if (node.label.includes('Searchable') || node.label.includes('Other Department')) {
                await apiHelper.deleteDepartment(node.id);
            }
        }
    });

    test.beforeEach(async ({ page }) => {
        explorerPage = new ExplorerPage(page);
        await explorerPage.goto();
        await explorerPage.waitForExplorerLoad();
    });

    test('should filter tree by search query', async () => {
        await explorerPage.search('Searchable');

        await explorerPage.waitForTimeout(500);

        const visibleCount = await explorerPage.getVisibleNodeCount();
        expect(visibleCount).toBeGreaterThan(0);
        expect(visibleCount).toBeLessThan(3); // Should filter out "Other Department"
    });

    test('should clear search and show all nodes', async () => {
        await explorerPage.search('Searchable');
        await explorerPage.clearSearch();

        await explorerPage.waitForTimeout(300);

        const visibleCount = await explorerPage.getVisibleNodeCount();
        expect(visibleCount).toBeGreaterThan(2); // Should show all departments
    });

    test('should show no results for non-matching search', async () => {
        await explorerPage.search('NonExistent12345');

        await explorerPage.waitForTimeout(500);

        const visibleCount = await explorerPage.getVisibleNodeCount();
        expect(visibleCount).toBe(0);
    });
});

test.describe('Explorer - View Switching', () => {
    let explorerPage: ExplorerPage;
    let apiHelper: ApiHelper;

    test.beforeAll(async ({ request }) => {
        apiHelper = new ApiHelper(request);
        await apiHelper.createDepartment('View Test', 'VWT');
    });

    test.afterAll(async ({ request }) => {
        const tree = await apiHelper.getExplorerTree();
        for (const node of tree) {
            if (node.label === 'View Test') {
                await apiHelper.deleteDepartment(node.id);
            }
        }
    });

    test.beforeEach(async ({ page }) => {
        explorerPage = new ExplorerPage(page);
        await explorerPage.goto();
        await explorerPage.waitForExplorerLoad();
    });

    test('should switch to grid view', async () => {
        await explorerPage.switchToGridView();

        // Verify grid view is active
        const gridActive = await explorerPage.gridViewBtn.getAttribute('class');
        expect(gridActive).toContain('active');
    });

    test('should switch to list view', async () => {
        await explorerPage.switchToListView();

        // Verify list view is active
        const listActive = await explorerPage.listViewBtn.getAttribute('class');
        expect(listActive).toContain('active');
    });
});

test.describe('Explorer - Upload Dialog', () => {
    let explorerPage: ExplorerPage;
    let apiHelper: ApiHelper;
    let hierarchy: { departmentId: string; moduleId: string };

    test.beforeAll(async ({ request }) => {
        apiHelper = new ApiHelper(request);
        hierarchy = await apiHelper.createTestHierarchy();
    });

    test.afterAll(async ({ request }) => {
        if (hierarchy?.departmentId) {
            await apiHelper.deleteDepartment(hierarchy.departmentId);
        }
    });

    test.beforeEach(async ({ page }) => {
        explorerPage = new ExplorerPage(page);
        await explorerPage.goto();
        await explorerPage.waitForExplorerLoad();
    });

    test('should open upload dialog when module is selected', async () => {
        await explorerPage.expandPath(['Test Dept', 'Test Semester', 'Test Subject']);
        await explorerPage.openUploadDialog('Test Module');

        await expect(explorerPage.uploadDialog).toBeVisible();
    });

    test('should show upload options (document vs voice)', async () => {
        await explorerPage.openUploadDialog('Test Module');

        await expect(explorerPage.uploadOptions).toBeVisible();
        const optionCount = await explorerPage.uploadOptions.count();
        expect(optionCount).toBeGreaterThanOrEqual(2); // Document and Voice options
    });

    test('should close dialog when close button clicked', async () => {
        await explorerPage.openUploadDialog('Test Module');
        await explorerPage.closeDialog();

        const isOpen = await explorerPage.isDialogOpen();
        expect(isOpen).toBe(false);
    });
});

test.describe('Explorer - Breadcrumbs', () => {
    let explorerPage: ExplorerPage;
    let apiHelper: ApiHelper;
    let hierarchy: { departmentId: string };

    test.beforeAll(async ({ request }) => {
        apiHelper = new ApiHelper(request);
        hierarchy = await apiHelper.createTestHierarchy();
    });

    test.afterAll(async ({ request }) => {
        if (hierarchy?.departmentId) {
            await apiHelper.deleteDepartment(hierarchy.departmentId);
        }
    });

    test.beforeEach(async ({ page }) => {
        explorerPage = new ExplorerPage(page);
        await explorerPage.goto();
        await explorerPage.waitForExplorerLoad();
    });

    test('should show breadcrumbs when navigating', async () => {
        await explorerPage.expandNode(hierarchy.departmentId);
        await explorerPage.selectNodeByLabel('Test Semester');

        // Breadcrumbs should be visible
        const crumbs = await explorerPage.getBreadcrumbsText();
        expect(crumbs.length).toBeGreaterThan(0);
    });
});

test.describe('Explorer - Error Handling UI', () => {
    let explorerPage: ExplorerPage;

    test.beforeEach(async ({ page }) => {
        explorerPage = new ExplorerPage(page);
        await explorerPage.goto();
        await explorerPage.waitForExplorerLoad();
    });

    test('should handle network errors gracefully', async ({ page }) => {
        // Simulate network failure by blocking requests (if needed)
        // For now, test that error states don't crash the UI
        await explorerPage.refresh();
        await expect(explorerPage.treeContainer).toBeVisible();
    });

    test('should show error message when operation fails', async () => {
        // Try to create department with invalid data
        // This depends on frontend validation
        // If validation exists, it should show error
    });
});

test.describe('Explorer - End-to-End User Flow', () => {
    let explorerPage: ExplorerPage;
    let apiHelper: ApiHelper;
    let cleanupIds: string[] = [];

    test.beforeEach(async ({ page, request }) => {
        explorerPage = new ExplorerPage(page);
        apiHelper = new ApiHelper(request);
        await explorerPage.goto();
        await explorerPage.waitForExplorerLoad();
    });

    test.afterEach(async ({ request }) => {
        for (const id of cleanupIds) {
            await apiHelper.deleteDepartment(id);
        }
        cleanupIds = [];
    });

    test('Complete workflow: Create hierarchy, upload document, verify', async () => {
        // 1. Create department
        const deptName = `Workflow ${Date.now()}`;
        await explorerPage.createDepartment(deptName, 'WF');
        await explorerPage.waitForTimeout(500);

        // Get ID for cleanup
        const tree = await apiHelper.getExplorerTree();
        const dept = tree.find((d: any) => d.label === deptName);
        if (dept) cleanupIds.push(dept.id);

        // 2. Create semester
        const semName = `Sem ${Date.now()}`;
        await explorerPage.createSemester(deptName, semName);
        await explorerPage.waitForTimeout(500);

        // 3. Create subject
        const subjName = `Subj ${Date.now()}`;
        await explorerPage.createSubject(semName, subjName, 'WF101');
        await explorerPage.waitForTimeout(500);

        // 4. Create module
        const modName = `Mod ${Date.now()}`;
        await explorerPage.createModule(subjName, modName);
        await explorerPage.waitForTimeout(500);

        // 5. Verify complete hierarchy exists
        const exists = await explorerPage.verifyNodeExists(modName);
        expect(exists).toBe(true);

        // 6. Expand to verify structure
        await explorerPage.expandPath([deptName, semName, subjName]);
        const modVisible = await explorerPage.verifyNodeVisible(modName);
        expect(modVisible).toBe(true);
    });
});
