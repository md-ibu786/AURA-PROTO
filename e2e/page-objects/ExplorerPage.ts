import { Page, Locator, expect } from '@playwright/test';

/**
 * Explorer Page Object
 * Encapsulates interactions with the main explorer interface
 * Includes methods for navigation, CRUD operations, and UI interactions
 */
export class ExplorerPage {
    readonly page: Page;

    // Layout elements
    readonly sidebar: Locator;
    readonly mainContent: Locator;
    readonly header: Locator;
    readonly breadcrumbs: Locator;

    // Tree elements
    readonly treeContainer: Locator;
    readonly treeNodes: Locator;
    readonly expandButtons: Locator;

    // View controls
    readonly gridViewBtn: Locator;
    readonly listViewBtn: Locator;
    readonly searchInput: Locator;

    // Action buttons
    readonly createDeptBtn: Locator;
    readonly createSemBtn: Locator;
    readonly createSubjBtn: Locator;
    readonly createModBtn: Locator;
    readonly uploadBtn: Locator;

    // Context menu
    readonly contextMenu: Locator;

    // Upload dialog
    readonly uploadDialog: Locator;
    readonly uploadOptions: Locator;

    // Modals and dialogs
    readonly modalOverlay: Locator;
    readonly dialogClose: Locator;

    constructor(page: Page) {
        this.page = page;

        // Layout
        this.sidebar = page.locator('[data-testid="sidebar"], .sidebar, .explorer-sidebar');
        this.mainContent = page.locator('[data-testid="content"], .main-content, .explorer-content');
        this.header = page.locator('[data-testid="header"], header, .header');
        this.breadcrumbs = page.locator('[data-testid="breadcrumbs"], .breadcrumbs');

        // Tree
        this.treeContainer = page.locator('[data-testid="explorer-tree"], .tree-view, [class*="tree"]');
        this.treeNodes = page.locator('[data-testid^="node-"], .tree-node, [role="treeitem"]');
        this.expandButtons = page.locator('[data-testid^="expand-"], .expand-btn, .tree-expand');

        // View controls
        this.gridViewBtn = page.locator('[data-testid="view-grid"], .view-grid-btn, [aria-label="Grid view"]');
        this.listViewBtn = page.locator('[data-testid="view-list"], .view-list-btn, [aria-label="List view"]');
        this.searchInput = page.locator('[data-testid="search"], .search-input, input[placeholder*="Search"]');

        // Action buttons
        this.createDeptBtn = page.locator('[data-testid="create-department"], .create-department-btn');
        this.createSemBtn = page.locator('[data-testid="create-semester"], .create-semester-btn');
        this.createSubjBtn = page.locator('[data-testid="create-subject"], .create-subject-btn');
        this.createModBtn = page.locator('[data-testid="create-module"], .create-module-btn');
        this.uploadBtn = page.locator('[data-testid="upload"], .upload-btn, button:has-text("Upload")');

        // Context menu
        this.contextMenu = page.locator('[data-testid="context-menu"], .context-menu, .dropdown-menu');

        // Upload dialog
        this.uploadDialog = page.locator('[data-testid="upload-dialog"], .upload-dialog, .dialog');
        this.uploadOptions = page.locator('.upload-option-card');

        // Modals
        this.modalOverlay = page.locator('.dialog-overlay, .modal-overlay, [role="dialog"]');
        this.dialogClose = page.locator('.dialog-close, .close-btn, [aria-label="Close"]');
    }

    // ========== Navigation ==========

    async goto(): Promise<void> {
        await this.page.goto('/');
        await this.page.waitForLoadState('networkidle');
    }

    async refresh(): Promise<void> {
        await this.page.reload();
        await this.page.waitForLoadState('networkidle');
    }

    async waitForExplorerLoad(): Promise<void> {
        await this.treeContainer.waitFor({ state: 'visible', timeout: 15000 });
        await this.page.waitForTimeout(500); // Extra time for async tree loading
    }

    // ========== Tree Operations ==========

    async getTreeNodes(): Promise<Locator> {
        return this.treeNodes;
    }

    async getVisibleNodeCount(): Promise<number> {
        await this.page.waitForTimeout(300); // Allow for rendering
        return await this.treeNodes.count();
    }

    async getNodeByLabel(label: string, exact: boolean = false): Promise<Locator> {
        return this.page.getByText(label, { exact });
    }

    async getNodeById(nodeId: string): Promise<Locator> {
        return this.page.locator(`[data-testid="node-${nodeId}"], [data-node-id="${nodeId}"]`);
    }

    async expandNode(nodeId: string): Promise<void> {
        const expandBtn = this.page.locator(`[data-testid="expand-${nodeId}"], [data-node-id="${nodeId}"] .expand-btn`);
        if (await expandBtn.isVisible()) {
            await expandBtn.click();
            await this.page.waitForTimeout(300);
        }
    }

    async collapseNode(nodeId: string): Promise<void> {
        const collapseBtn = this.page.locator(`[data-testid="collapse-${nodeId}"], [data-node-id="${nodeId}"] .collapse-btn`);
        if (await collapseBtn.isVisible()) {
            await collapseBtn.click();
            await this.page.waitForTimeout(300);
        }
    }

    async selectNode(nodeId: string): Promise<void> {
        const node = await this.getNodeById(nodeId);
        await node.click();
        await this.page.waitForTimeout(200);
    }

    async selectNodeByLabel(label: string): Promise<void> {
        const node = await this.getNodeByLabel(label);
        await node.click();
        await this.page.waitForTimeout(200);
    }

    async expandPath(labels: string[]): Promise<void> {
        for (const label of labels) {
            const node = await this.getNodeByLabel(label);
            const nodeId = await node.getAttribute('data-node-id');
            if (nodeId) {
                await this.expandNode(nodeId);
            }
        }
    }

    // ========== CRUD Operations ==========

    async createDepartment(name: string, code: string): Promise<void> {
        await this.createDeptBtn.click();
        await this.page.waitForSelector('[data-testid="department-name-input"], input[name="name"]', { state: 'visible' });

        await this.page.fill('[data-testid="department-name-input"], input[name="name"]', name);
        await this.page.fill('[data-testid="department-code-input"], input[name="code"]', code);
        await this.page.click('[data-testid="department-save"], button:has-text("Save")');

        await this.page.waitForTimeout(500);
    }

    async createSemester(parentLabel: string, name: string): Promise<void> {
        await this.expandPath([parentLabel]);
        const parent = await this.getNodeByLabel(parentLabel);
        const parentId = await parent.getAttribute('data-node-id');

        await this.selectNode(parentId!);
        await this.createSemBtn.click();

        await this.page.waitForSelector('[data-testid="semester-name-input"], input[name="name"]', { state: 'visible' });
        await this.page.fill('[data-testid="semester-name-input"], input[name="name"]', name);
        await this.page.click('[data-testid="semester-save"], button:has-text("Save")');

        await this.page.waitForTimeout(500);
    }

    async createSubject(parentLabel: string, name: string, code: string): Promise<void> {
        await this.expandPath([parentLabel]);
        const parent = await this.getNodeByLabel(parentLabel);
        const parentId = await parent.getAttribute('data-node-id');

        await this.selectNode(parentId!);
        await this.createSubjBtn.click();

        await this.page.waitForSelector('[data-testid="subject-name-input"], input[name="name"]', { state: 'visible' });
        await this.page.fill('[data-testid="subject-name-input"], input[name="name"]', name);
        await this.page.fill('[data-testid="subject-code-input"], input[name="code"]', code);
        await this.page.click('[data-testid="subject-save"], button:has-text("Save")');

        await this.page.waitForTimeout(500);
    }

    async createModule(parentLabel: string, name: string): Promise<void> {
        await this.expandPath([parentLabel]);
        const parent = await this.getNodeByLabel(parentLabel);
        const parentId = await parent.getAttribute('data-node-id');

        await this.selectNode(parentId!);
        await this.createModBtn.click();

        await this.page.waitForSelector('[data-testid="module-name-input"], input[name="name"]', { state: 'visible' });
        await this.page.fill('[data-testid="module-name-input"], input[name="name"]', name);
        await this.page.click('[data-testid="module-save"], button:has-text("Save")');

        await this.page.waitForTimeout(500);
    }

    // ========== Context Menu ==========

    async openContextMenu(nodeLabel: string): Promise<void> {
        const node = await this.getNodeByLabel(nodeLabel);
        await node.click({ button: 'right' });
        await this.contextMenu.waitFor({ state: 'visible', timeout: 5000 });
    }

    async contextMenuAction(action: string): Promise<void> {
        const actionBtn = this.contextMenu.locator(`text=${action}`);
        await actionBtn.click();
        await this.page.waitForTimeout(300);
    }

    async renameNode(nodeLabel: string, newName: string): Promise<void> {
        await this.openContextMenu(nodeLabel);
        await this.contextMenuAction('Rename');

        const input = this.page.locator('input[type="text"]');
        await input.fill(newName);
        await this.page.keyboard.press('Enter');
        await this.page.waitForTimeout(500);
    }

    async deleteNode(nodeLabel: string): Promise<void> {
        await this.openContextMenu(nodeLabel);
        await this.contextMenuAction('Delete');

        // Confirm if dialog appears
        const confirmBtn = this.page.locator('button:has-text("Delete"), button:has-text("Confirm")');
        if (await confirmBtn.isVisible()) {
            await confirmBtn.click();
        }

        await this.page.waitForTimeout(500);
    }

    // ========== Upload Operations ==========

    async openUploadDialog(nodeLabel: string): Promise<void> {
        await this.selectNodeByLabel(nodeLabel);
        await this.uploadBtn.click();
        await this.uploadDialog.waitFor({ state: 'visible', timeout: 5000 });
    }

    async selectUploadMode(mode: 'document' | 'voice'): Promise<void> {
        const modeBtn = this.uploadOptions.locator(mode === 'document' ? 'text=Document' : 'text=Voice, text=AI');
        await modeBtn.click();
        await this.page.waitForTimeout(300);
    }

    async uploadDocumentFile(filePath: string, title?: string): Promise<void> {
        // Handle file input
        const fileInput = this.page.locator('input[type="file"]');
        await fileInput.setInputFiles(filePath);

        if (title) {
            const titleInput = this.page.locator('input[placeholder*="Title"], input[name="title"]');
            await titleInput.fill(title);
        }

        const uploadBtn = this.page.locator('button:has-text("Upload"), button:has-text("Generate")');
        await uploadBtn.click();

        // Wait for upload to complete
        await this.page.waitForTimeout(1000);
    }

    async uploadVoiceFile(filePath: string, topic: string): Promise<void> {
        const fileInput = this.page.locator('input[type="file"]');
        await fileInput.setInputFiles(filePath);

        const topicInput = this.page.locator('input[placeholder*="Topic"], input[name="topic"]');
        await topicInput.fill(topic);

        const generateBtn = this.page.locator('button:has-text("Generate Notes")');
        await generateBtn.click();

        // Wait for processing to start
        await this.page.waitForSelector('.processing-status, .progress-bar', { state: 'visible' });
    }

    async waitForProcessingComplete(timeout: number = 120000): Promise<boolean> {
        const startTime = Date.now();
        while (Date.now() - startTime < timeout) {
            const statusText = await this.page.locator('.processing-label, .processing-message').textContent();
            if (statusText?.includes('Complete') || statusText?.includes('complete')) {
                return true;
            }
            if (statusText?.includes('Error') || statusText?.includes('error')) {
                return false;
            }
            await this.page.waitForTimeout(2000);
        }
        return false;
    }

    // ========== View Switching ==========

    async switchToGridView(): Promise<void> {
        await this.gridViewBtn.click();
        await this.page.waitForTimeout(300);
    }

    async switchToListView(): Promise<void> {
        await this.listViewBtn.click();
        await this.page.waitForTimeout(300);
    }

    // ========== Search ==========

    async search(query: string): Promise<void> {
        await this.searchInput.fill(query);
        await this.page.waitForTimeout(500); // Allow filtering
    }

    async clearSearch(): Promise<void> {
        await this.searchInput.clear();
        await this.page.waitForTimeout(300);
    }

    async getSearchResults(): Promise<number> {
        return await this.treeNodes.count();
    }

    // ========== Breadcrumbs ==========

    async getBreadcrumbsText(): Promise<string> {
        return await this.breadcrumbs.textContent() || '';
    }

    async clickBreadcrumb(index: number): Promise<void> {
        const crumbs = this.breadcrumbs.locator('a, button, [data-testid^="crumb-"]');
        await crumbs.nth(index).click();
        await this.page.waitForTimeout(300);
    }

    // ========== Validation ==========

    async verifyNodeExists(label: string): Promise<boolean> {
        const node = await this.getNodeByLabel(label);
        return await node.count() > 0;
    }

    async verifyNodeVisible(label: string): Promise<boolean> {
        const node = await this.getNodeByLabel(label);
        try {
            await node.waitFor({ state: 'visible', timeout: 5000 });
            return true;
        } catch {
            return false;
        }
    }

    async verifyNodeCount(expected: number): Promise<void> {
        const count = await this.getVisibleNodeCount();
        expect(count).toBe(expected);
    }

    // ========== Dialog Management ==========

    async closeDialog(): Promise<void> {
        if (await this.dialogClose.isVisible()) {
            await this.dialogClose.click();
            await this.page.waitForTimeout(300);
        } else if (await this.modalOverlay.isVisible()) {
            await this.modalOverlay.click({ position: { x: 0, y: 0 } });
            await this.page.waitForTimeout(300);
        }
    }

    async isDialogOpen(): Promise<boolean> {
        return await this.uploadDialog.isVisible() || await this.modalOverlay.isVisible();
    }

    // ========== Error Handling ==========

    async getErrorMessage(): Promise<string | null> {
        const errorEl = this.page.locator('.error-message, .upload-error, [role="alert"]');
        if (await errorEl.isVisible()) {
            return await errorEl.textContent();
        }
        return null;
    }

    async hasError(): Promise<boolean> {
        const error = await this.getErrorMessage();
        return error !== null && error.length > 0;
    }

    // ========== Utility Methods ==========

    async waitForNetworkIdle(): Promise<void> {
        await this.page.waitForLoadState('networkidle');
    }

    async waitForTimeout(ms: number): Promise<void> {
        await this.page.waitForTimeout(ms);
    }

    async takeScreenshot(name: string): Promise<void> {
        await this.page.screenshot({ path: `test-results/screenshots/${name}.png`, fullPage: true });
    }

    async scrollToBottom(): Promise<void> {
        await this.page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        await this.page.waitForTimeout(300);
    }

    async scrollToTop(): Promise<void> {
        await this.page.evaluate(() => window.scrollTo(0, 0));
        await this.page.waitForTimeout(300);
    }
}
