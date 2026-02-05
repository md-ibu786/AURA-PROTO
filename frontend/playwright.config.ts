// playwright.config.ts
// Playwright E2E test configuration for AURA-NOTES-MANAGER frontend.

// Configures test directory, browser projects (Chromium, Firefox, WebKit),
// timeouts, and webServer settings. Uses fullyParallel: false per project
// convention for DB consistency during sequential tests.

// @see: e2e/ - Test specification files
// @note: Use 127.0.0.1 not localhost to avoid IPv6 issues

import process from 'process';
import { defineConfig, devices } from '@playwright/test';

// Default to mock auth for E2E tests unless explicitly set
if (!process.env.VITE_USE_MOCK_AUTH) {
    process.env.VITE_USE_MOCK_AUTH = 'true';
}

/**
 * Playwright E2E test configuration for AURA-NOTES-MANAGER frontend.
 * @see https://playwright.dev/docs/test-configuration
 */
export default defineConfig({
  testDir: './e2e',

  /* Sequential execution for DB consistency (project convention) */
  fullyParallel: false,

  /* Fail the build on CI if you accidentally left test.only in the source code */
  forbidOnly: !!process.env.CI,

  /* Retry on CI only */
  retries: process.env.CI ? 2 : 0,

  /* Sequential workers on CI */
  workers: process.env.CI ? 1 : undefined,

  /* Reporter to use */
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['list'],
  ],

  /* Shared settings for all the projects below */
  use: {
    /* Base URL for the frontend */
    baseURL: 'http://127.0.0.1:5173',

    /* Collect trace when retrying the failed test */
    trace: 'on-first-retry',

    /* Screenshot on failure */
    screenshot: 'only-on-failure',

    /* Video recording */
    video: 'retain-on-failure',

    /* Ignore HTTPS errors for local development */
    ignoreHTTPSErrors: true,
  },

  /* Configure projects for major browsers */
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    /* Auth setup project - runs before other tests */
    {
      name: 'auth-setup',
      testMatch: /auth\.setup\.ts/,
    },
  ],

  /* Run your local dev server before starting the tests */
  webServer: {
    command: 'npm run dev',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
    env: {
      VITE_USE_MOCK_AUTH: 'true',
    },
  },

  /* Global timeout for each test */
  timeout: 30 * 1000,

  /* Expect timeout */
  expect: {
    timeout: 5 * 1000,
  },

  /* Hook configuration */
  globalSetup: undefined,

  /* Shard configuration */
  shard: undefined,

  /* Maximum number of test failures before stopping */
  maxFailures: process.env.CI ? 10 : undefined,
});
