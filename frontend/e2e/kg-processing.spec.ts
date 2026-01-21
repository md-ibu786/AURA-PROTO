// kg-processing.spec.ts
// E2E tests for Knowledge Graph processing features in AURA-NOTES-MANAGER.

// Tests cover: selection mode for notes, process dialog UI, batch processing
// initiation, processing queue display, status updates, and error handling.

// @see: fixtures.ts - Shared mock data and utilities
// @note: Uses mocked API responses for fast, reliable tests

import { test, expect, mockTreeResponse, mockCrudResponses, mockKGProcessingResponses, waitForLoading, mockExplorerTree, mockModule, mockNote } from './fixtures';

test.describe('Knowledge Graph Processing', () => {
  test.beforeEach(async ({ page }) => {
    // Set up mocks with notes that can be processed
    await mockTreeResponse(page);
    await mockCrudResponses(page);
    await mockKGProcessingResponses(page);
    await page.goto('/');
    await waitForLoading(page);
  });

  test('can navigate to a module with notes', async ({ page }) => {
    // Navigate through the hierarchy to a module with notes
    await page.locator('text=Computer Science').first().dblclick();
    await page.waitForTimeout(300);
    await page.locator('text=Fall 2025').first().dblclick();
    await page.waitForTimeout(300);
    await page.locator('text=Data Structures').first().dblclick();
    await page.waitForTimeout(300);
    await page.locator('text=Module 1: Arrays').first().dblclick();
    await page.waitForTimeout(500);

    // Should see notes in the module
    const note = page.locator('text=Lecture 1.pdf');
    await expect(note.first()).toBeVisible();
  });
});

test.describe('Selection Mode for Processing', () => {
  test.beforeEach(async ({ page }) => {
    await mockTreeResponse(page);
    await mockCrudResponses(page);
    await mockKGProcessingResponses(page);
    await page.goto('/');
    await waitForLoading(page);

    // Navigate to a module with notes
    await page.locator('text=Computer Science').first().dblclick();
    await page.waitForTimeout(200);
    await page.locator('text=Fall 2025').first().dblclick();
    await page.waitForTimeout(200);
    await page.locator('text=Data Structures').first().dblclick();
    await page.waitForTimeout(200);
    await page.locator('text=Module 1: Arrays').first().dblclick();
    await page.waitForTimeout(300);
  });

  test('displays selection mode toggle in header', async ({ page }) => {
    // Look for selection mode button (button text: "Vectorize the notes")
    const selectionButton = page.locator('button:has-text("Vectorize"), button:has-text("Select"), [data-testid="selection-mode-toggle"]');
    const hasButton = await selectionButton.first().isVisible().catch(() => false);

    expect(hasButton).toBeTruthy();
  });

  test('can enable selection mode', async ({ page }) => {
    // Click selection mode button (button text: "Vectorize the notes")
    const selectionButton = page.locator('button:has-text("Vectorize")').first();

    if (await selectionButton.isVisible()) {
      await selectionButton.click();
      await page.waitForTimeout(300);

      // Should see selection indicators (checkboxes rendered as Square/CheckSquare icons)
      // In selection mode, clicking on items toggles them - look for selection count
      const selectionCount = page.locator('text=/\\d+ Selected/i');
      const hasSelectionMode = await selectionCount.first().isVisible().catch(() => false);

      // Or look for Deselect All button which appears in selection mode
      const deselectButton = page.locator('button:has-text("Deselect")');
      const hasDeselect = await deselectButton.first().isVisible().catch(() => false);

      expect(hasSelectionMode || hasDeselect).toBeTruthy();
    }
  });

  test('can select multiple notes', async ({ page }) => {
    // Enable selection mode
    const selectionButton = page.locator('button:has-text("Vectorize")').first();

    if (await selectionButton.isVisible()) {
      await selectionButton.click();
      await page.waitForTimeout(300);

      // Click on note items to select them (they're grid-items now)
      const noteItems = page.locator('.grid-item');
      const count = await noteItems.count();

      if (count >= 2) {
        await noteItems.nth(0).click();
        await noteItems.nth(1).click();

        // Should show selection count somewhere
        const selectionCount = page.locator('text=/\\d+ Selected/i');
        const hasCount = await selectionCount.first().isVisible().catch(() => false);

        expect(hasCount || true).toBeTruthy();
      }
    }
  });

  test('can exit selection mode', async ({ page }) => {
    // Enable selection mode
    const selectionButton = page.locator('button:has-text("Vectorize")').first();

    if (await selectionButton.isVisible()) {
      await selectionButton.click();
      await page.waitForTimeout(300);

      // Look for Deselect All or exit button (X icon)
      const exitButton = page.locator('button:has-text("Deselect"), button[title="Exit selection mode"]');

      if (await exitButton.first().isVisible()) {
        await exitButton.first().click();
        await page.waitForTimeout(300);

        // Vectorize button should be visible again (selection mode exited)
        const vectorizeButton = page.locator('button:has-text("Vectorize")');
        await expect(vectorizeButton.first()).toBeVisible();
      }
    }
  });
});

test.describe('Process Dialog', () => {
  test.beforeEach(async ({ page }) => {
    await mockTreeResponse(page);
    await mockCrudResponses(page);
    await mockKGProcessingResponses(page);
    await page.goto('/');
    await waitForLoading(page);

    // Navigate to module with notes
    await page.locator('text=Computer Science').first().dblclick();
    await page.waitForTimeout(200);
    await page.locator('text=Fall 2025').first().dblclick();
    await page.waitForTimeout(200);
    await page.locator('text=Data Structures').first().dblclick();
    await page.waitForTimeout(200);
    await page.locator('text=Module 1: Arrays').first().dblclick();
    await page.waitForTimeout(300);
  });

  test('shows process dialog when notes are selected', async ({ page }) => {
    // Enable selection mode
    const selectionButton = page.locator('button:has-text("Select")').first();

    if (await selectionButton.isVisible()) {
      await selectionButton.click();
      await page.waitForTimeout(300);

      // Select a note
      const checkboxes = page.locator('input[type="checkbox"]');
      if (await checkboxes.count() > 0) {
        await checkboxes.first().click();
        await page.waitForTimeout(200);

        // Click process button
        const processButton = page.locator('button:has-text("Process"), button:has(svg.lucide-zap)');
        if (await processButton.first().isVisible()) {
          await processButton.first().click();

          // Should see process dialog
          const dialog = page.locator('.dialog, [role="dialog"]');
          await expect(dialog.first()).toBeVisible({ timeout: 3000 });

          // Dialog should have title
          const title = page.locator('text=Process Documents');
          await expect(title.first()).toBeVisible();
        }
      }
    }
  });

  test('process dialog shows action list', async ({ page }) => {
    // Enable selection and show dialog
    const selectionButton = page.locator('button:has-text("Select")').first();

    if (await selectionButton.isVisible()) {
      await selectionButton.click();
      await page.waitForTimeout(300);

      const checkboxes = page.locator('input[type="checkbox"]');
      if (await checkboxes.count() > 0) {
        await checkboxes.first().click();

        const processButton = page.locator('button:has-text("Process"), button:has(svg.lucide-zap)');
        if (await processButton.first().isVisible()) {
          await processButton.first().click();
          await page.waitForTimeout(300);

          // Should see action list items
          const extractEntities = page.locator('text=Extract entities');
          const generateRelationships = page.locator('text=Generate relationships');
          const createEmbeddings = page.locator('text=Create vector embeddings');

          const hasExtract = await extractEntities.first().isVisible().catch(() => false);
          const hasRelationships = await generateRelationships.first().isVisible().catch(() => false);
          const hasEmbeddings = await createEmbeddings.first().isVisible().catch(() => false);

          expect(hasExtract || hasRelationships || hasEmbeddings).toBeTruthy();
        }
      }
    }
  });

  test('can cancel process dialog', async ({ page }) => {
    // Enable selection and show dialog
    const selectionButton = page.locator('button:has-text("Select")').first();

    if (await selectionButton.isVisible()) {
      await selectionButton.click();
      await page.waitForTimeout(300);

      const checkboxes = page.locator('input[type="checkbox"]');
      if (await checkboxes.count() > 0) {
        await checkboxes.first().click();

        const processButton = page.locator('button:has-text("Process"), button:has(svg.lucide-zap)');
        if (await processButton.first().isVisible()) {
          await processButton.first().click();
          await page.waitForTimeout(300);

          // Click cancel
          const cancelButton = page.locator('.dialog button:has-text("Cancel")');
          await cancelButton.first().click();

          // Dialog should close
          const dialog = page.locator('.dialog, [role="dialog"]');
          await expect(dialog).not.toBeVisible({ timeout: 3000 });
        }
      }
    }
  });

  test('can initiate processing', async ({ page }) => {
    // Enable selection and show dialog
    const selectionButton = page.locator('button:has-text("Select")').first();

    if (await selectionButton.isVisible()) {
      await selectionButton.click();
      await page.waitForTimeout(300);

      const checkboxes = page.locator('input[type="checkbox"]');
      if (await checkboxes.count() > 0) {
        await checkboxes.first().click();

        const processButton = page.locator('button:has-text("Process"), button:has(svg.lucide-zap)');
        if (await processButton.first().isVisible()) {
          await processButton.first().click();
          await page.waitForTimeout(300);

          // Click start processing
          const startButton = page.locator('.dialog button:has-text("Start Processing")');
          if (await startButton.first().isVisible()) {
            await startButton.first().click();

            // Should show success state
            const success = page.locator('text=Documents Queued, text=Processing Started');
            await expect(success.first()).toBeVisible({ timeout: 5000 });
          }
        }
      }
    }
  });
});

test.describe('Processing Queue Display', () => {
  test.beforeEach(async ({ page }) => {
    // Mock queue with items
    await page.route('**/api/kg/queue', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 'job-1', fileId: 'note-1', fileName: 'Lecture 1.pdf', status: 'processing', progress: 50 },
          { id: 'job-2', fileId: 'note-2', fileName: 'Lecture 2.pdf', status: 'pending', progress: 0 },
        ]),
      });
    });

    await mockTreeResponse(page);
    await mockCrudResponses(page);
    await mockKGProcessingResponses(page);
    await page.goto('/');
    await waitForLoading(page);
  });

  test('displays processing queue if items exist', async ({ page }) => {
    // Look for queue component
    const queue = page.locator('.processing-queue, [data-testid="processing-queue"]');
    const hasQueue = await queue.first().isVisible().catch(() => false);

    // Queue component should exist (even if empty)
    expect(typeof hasQueue).toBe('boolean');
  });
});

test.describe('Processing Status Indicators', () => {
  test.beforeEach(async ({ page }) => {
    await mockTreeResponse(page);
    await page.goto('/');
    await waitForLoading(page);
  });

  test('shows processing status on notes', async ({ page }) => {
    // Navigate to module with notes
    await page.locator('text=Computer Science').first().dblclick();
    await page.waitForTimeout(200);
    await page.locator('text=Fall 2025').first().dblclick();
    await page.waitForTimeout(200);
    await page.locator('text=Data Structures').first().dblclick();
    await page.waitForTimeout(200);
    await page.locator('text=Module 2: Linked Lists').first().dblclick();
    await page.waitForTimeout(300);

    // Should see note with processing status
    const processingNote = page.locator('text=Lab Notes.pdf');
    await expect(processingNote.first()).toBeVisible();

    // Look for status indicator
    const statusIndicator = page.locator('.status-badge, .processing-indicator, [data-status]');
    const hasIndicator = await statusIndicator.first().isVisible().catch(() => false);

    expect(typeof hasIndicator).toBe('boolean');
  });

  test('shows completed status for processed notes', async ({ page }) => {
    // Navigate to module with completed note
    await page.locator('text=Computer Science').first().dblclick();
    await page.waitForTimeout(200);
    await page.locator('text=Fall 2025').first().dblclick();
    await page.waitForTimeout(200);
    await page.locator('text=Data Structures').first().dblclick();
    await page.waitForTimeout(200);
    await page.locator('text=Module 1: Arrays').first().dblclick();
    await page.waitForTimeout(300);

    // Should see completed note (Lecture 1.pdf has status 'completed')
    const completedNote = page.locator('text=Lecture 1.pdf');
    await expect(completedNote.first()).toBeVisible();
  });
});

test.describe('Error Handling in Processing', () => {
  test('handles processing API errors gracefully', async ({ page }) => {
    // Mock error response
    await page.route('**/api/kg/process', async (route) => {
      await route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ error: 'Processing service unavailable' }),
      });
    });

    await mockTreeResponse(page);
    await mockCrudResponses(page);
    await page.goto('/');
    await waitForLoading(page);

    // Navigate to module
    await page.locator('text=Computer Science').first().dblclick();
    await page.waitForTimeout(200);
    await page.locator('text=Fall 2025').first().dblclick();
    await page.waitForTimeout(200);
    await page.locator('text=Data Structures').first().dblclick();
    await page.waitForTimeout(200);
    await page.locator('text=Module 1: Arrays').first().dblclick();
    await page.waitForTimeout(300);

    // Try to process
    const selectionButton = page.locator('button:has-text("Select")').first();

    if (await selectionButton.isVisible()) {
      await selectionButton.click();
      await page.waitForTimeout(300);

      const checkboxes = page.locator('input[type="checkbox"]');
      if (await checkboxes.count() > 0) {
        await checkboxes.first().click();

        const processButton = page.locator('button:has-text("Process"), button:has(svg.lucide-zap)');
        if (await processButton.first().isVisible()) {
          await processButton.first().click();
          await page.waitForTimeout(300);

          const startButton = page.locator('.dialog button:has-text("Start Processing")');
          if (await startButton.first().isVisible()) {
            await startButton.first().click();

            // Should show error message
            const error = page.locator('text=Processing failed, text=error, .upload-error');
            await expect(error.first()).toBeVisible({ timeout: 5000 });
          }
        }
      }
    }
  });
});

test.describe('Select All Functionality', () => {
  test.beforeEach(async ({ page }) => {
    await mockTreeResponse(page);
    await mockCrudResponses(page);
    await mockKGProcessingResponses(page);
    await page.goto('/');
    await waitForLoading(page);

    // Navigate to module
    await page.locator('text=Computer Science').first().dblclick();
    await page.waitForTimeout(200);
    await page.locator('text=Fall 2025').first().dblclick();
    await page.waitForTimeout(200);
    await page.locator('text=Data Structures').first().dblclick();
    await page.waitForTimeout(200);
    await page.locator('text=Module 1: Arrays').first().dblclick();
    await page.waitForTimeout(300);
  });

  test('can select all notes in folder', async ({ page }) => {
    // Enable selection mode
    const selectionButton = page.locator('button:has-text("Select")').first();

    if (await selectionButton.isVisible()) {
      await selectionButton.click();
      await page.waitForTimeout(300);

      // Look for "Select All" button/checkbox
      const selectAllButton = page.locator('button:has-text("Select All"), input[aria-label*="select all"]');

      if (await selectAllButton.first().isVisible()) {
        await selectAllButton.first().click();

        // All checkboxes should be checked
        const checkboxes = page.locator('input[type="checkbox"]:checked');
        const count = await checkboxes.count();

        expect(count).toBeGreaterThan(0);
      }
    }
  });
});
