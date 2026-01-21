// fixtures.ts
// Shared Playwright test fixtures and utilities for AURA-NOTES-MANAGER E2E tests.

// Provides mock data helpers (mockExplorerTree, mockNote, mockModule),
// API route interception helpers, and common wait utilities for consistent
// test data across all E2E specifications.

// @see: playwright.config.ts - Test configuration
// @note: All mock data follows FileSystemNode interface from src/types

import { test as base, expect, Page, Route } from '@playwright/test';

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

  // Mock delete operations
  await page.route('**/api/explorer/departments/*', async (route: Route) => {
    if (route.request().method() === 'DELETE') {
      await route.fulfill({ status: 204 });
    } else {
      await route.continue();
    }
  });

  await page.route('**/api/explorer/semesters/*', async (route: Route) => {
    if (route.request().method() === 'DELETE') {
      await route.fulfill({ status: 204 });
    } else {
      await route.continue();
    }
  });

  await page.route('**/api/explorer/subjects/*', async (route: Route) => {
    if (route.request().method() === 'DELETE') {
      await route.fulfill({ status: 204 });
    } else {
      await route.continue();
    }
  });

  await page.route('**/api/explorer/modules/*', async (route: Route) => {
    if (route.request().method() === 'DELETE') {
      await route.fulfill({ status: 204 });
    } else {
      await route.continue();
    }
  });

  await page.route('**/api/explorer/notes/*', async (route: Route) => {
    if (route.request().method() === 'DELETE') {
      await route.fulfill({ status: 204 });
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

/**
 * Extended test fixture with pre-configured mocks.
 */
export const test = base.extend<{
  explorerPage: Page;
}>({
  explorerPage: async ({ page }, use) => {
    // Set up default mocks
    await mockTreeResponse(page);
    await mockCrudResponses(page);
    
    // Navigate to the app
    await page.goto('/');
    await waitForLoading(page);
    
    await use(page);
  },
});

export { expect };
