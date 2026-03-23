/**
 * ============================================================================
 * FILE: settings.spec.ts
 * LOCATION: frontend/e2e/settings.spec.ts
 * ============================================================================
 *
 * PURPOSE:
 *    Playwright E2E tests for the AURA-NOTES-MANAGER settings page.
 *    Validates that all 5 use case model rows are visible and that the
 *    gatekeeper and relationship extraction model pickers are functional.
 *
 * ROLE IN PROJECT:
 *    Part of the Phase 17 cross-app frontend validation suite.
 *    Ensures settings page works correctly with mocked API data.
 *
 * KEY COMPONENTS:
 *    - Test 1: Verifies all 5 use case labels are displayed
 *    - Test 2: Verifies gatekeeper model picker opens, allows selection, and calls mutation
 *    - Test 3: Verifies relationship extraction model picker opens, allows selection, and calls mutation
 *
 * DEPENDENCIES:
 *    - External: @playwright/test
 *    - Internal: ./fixtures (loginAsRole, mock utilities)
 *
 * USAGE:
 *    npx playwright test e2e/settings.spec.ts
 * ============================================================================
 */

import { test, expect, loginAsRole } from './fixtures';

// ---------------------------------------------------------------------------
// Mock data
// ---------------------------------------------------------------------------

const mockDefaults = {
    chat: { provider: 'vertex_ai', model: 'gemini-2.5-flash-lite' },
    embeddings: { provider: 'vertex_ai', model: 'text-embedding-004' },
    entity_extraction: { provider: 'vertex_ai', model: 'gemini-2.5-flash-lite' },
    gatekeeper: { provider: 'vertex_ai', model: 'gemini-2.5-flash-lite' },
    relationship_extraction: {
        provider: 'vertex_ai',
        model: 'gemini-2.5-flash-lite',
    },
};

const mockModels = [
    {
        name: 'gemini-2.5-flash-lite',
        provider: 'vertex_ai',
        display_name: 'Gemini 2.5 Flash Lite',
        model_type: 'generation',
    },
    {
        name: 'text-embedding-004',
        provider: 'vertex_ai',
        display_name: 'Text Embedding 004',
        model_type: 'embedding',
    },
    {
        name: 'anthropic/claude-sonnet-4',
        provider: 'openrouter',
        display_name: 'Claude Sonnet 4',
        model_type: 'generation',
    },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Sets up API route mocks for settings endpoints.
 */
async function mockSettingsRoutes(page: import('@playwright/test').Page) {
    await page.route('**/api/v1/settings/defaults', async (route) => {
        if (route.request().method() === 'GET') {
            await route.fulfill({
                status: 200,
                contentType: 'application/json',
                body: JSON.stringify(mockDefaults),
            });
            return;
        }
        await route.continue();
    });

    await page.route('**/api/v1/settings/models', async (route) => {
        await route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: JSON.stringify(mockModels),
        });
    });
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

test.describe('Settings Page', () => {
    test.beforeEach(async ({ page }) => {
        await mockSettingsRoutes(page);
        await loginAsRole(page, 'admin');
        await page.goto('/settings');
        await page.waitForLoadState('networkidle');
    });

    test('displays all 5 use case rows', async ({ page }) => {
        await expect(
            page.getByRole('heading', { name: 'Chat Model' })
        ).toBeVisible();
        await expect(
            page.getByRole('heading', { name: 'Embeddings Model' })
        ).toBeVisible();
        await expect(
            page.getByRole('heading', { name: 'Entity Extraction Model' })
        ).toBeVisible();
        await expect(
            page.getByRole('heading', { name: 'Gatekeeper Model' })
        ).toBeVisible();
        await expect(
            page.getByRole('heading', { name: 'Relationship Extraction Model' })
        ).toBeVisible();
    });

    test('gatekeeper model picker is functional', async ({ page }) => {
        // Track PUT calls to the gatekeeper defaults endpoint
        const mutationPromise = page.waitForRequest(
            (req) =>
                req.method() === 'PUT' &&
                req.url().includes('/api/v1/settings/defaults/gatekeeper')
        );

        // Find the Gatekeeper Model section and its picker trigger
        const gatekeeperHeading = page.getByRole('heading', {
            name: 'Gatekeeper Model',
        });
        await expect(gatekeeperHeading).toBeVisible();

        // The picker trigger button sits inside the same section container
        const section = gatekeeperHeading.locator('xpath=ancestor::div[contains(@class,"flex flex-col space-y-2")]');
        const pickerTrigger = section.locator('button').first();
        await pickerTrigger.click();

        // Dropdown panel should open — look for a model option
        const modelOption = page.locator('button', {
            hasText: 'Claude Sonnet 4',
        });
        await expect(modelOption).toBeVisible({ timeout: 5000 });

        // Select a different model
        await modelOption.click();

        // Verify the PUT mutation was called
        await mutationPromise;
    });

    test('relationship extraction model picker is functional', async ({
        page,
    }) => {
        // Track PUT calls to the relationship_extraction defaults endpoint
        const mutationPromise = page.waitForRequest(
            (req) =>
                req.method() === 'PUT' &&
                req.url().includes(
                    '/api/v1/settings/defaults/relationship_extraction'
                )
        );

        // Find the Relationship Extraction Model section
        const sectionHeading = page.getByRole('heading', {
            name: 'Relationship Extraction Model',
        });
        await expect(sectionHeading).toBeVisible();

        const section = sectionHeading.locator(
            'xpath=ancestor::div[contains(@class,"flex flex-col space-y-2")]'
        );
        const pickerTrigger = section.locator('button').first();
        await pickerTrigger.click();

        // Dropdown panel should open — look for a model option
        const modelOption = page.locator('button', {
            hasText: 'Claude Sonnet 4',
        });
        await expect(modelOption).toBeVisible({ timeout: 5000 });

        // Select a model
        await modelOption.click();

        // Verify the PUT mutation was called
        await mutationPromise;
    });
});
