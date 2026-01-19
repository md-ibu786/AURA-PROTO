import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for AURA-PROTO E2E tests
 *
 * Run tests: npx playwright test
 * View report: npx playwright show-report
 * Run specific: npx playwright test tests/api.spec.ts
 */
export default defineConfig({
    testDir: './tests',
    fullyParallel: false, // Run tests sequentially for database consistency
    forbidOnly: !!process.env.CI,
    retries: process.env.CI ? 2 : 0,
    workers: process.env.CI ? 1 : 1,
    reporter: [
        ['html', { outputFolder: '../test-results/html-report', open: 'never' }],
        ['list'],
        ['json', { outputFile: '../test-results/results.json' }]
    ],
    timeout: 60000, // 60 seconds per test
    expect: {
        timeout: 15000, // 15 seconds for assertions
    },

    use: {
        baseURL: 'http://127.0.0.1:5173',
        trace: 'on-first-retry',
        screenshot: 'only-on-failure',
        video: 'retain-on-failure',
        // Slow down actions for better visibility during debugging
        actionTimeout: 10000,
        navigationTimeout: 30000,
    },

    projects: [
        {
            name: 'chromium',
            use: {
                ...devices['Desktop Chrome'],
                viewport: { width: 1920, height: 1080 },
            },
        },
        {
            name: 'firefox',
            use: {
                ...devices['Desktop Firefox'],
                viewport: { width: 1920, height: 1080 },
            },
        },
        {
            name: 'webkit',
            use: {
                ...devices['Desktop Safari'],
                viewport: { width: 1920, height: 1080 },
            },
        },
    ],

    // Start backend and frontend before running tests
    // Only start servers if SKIP_WEBSERVER is not set
    webServer: process.env.SKIP_WEBSERVER ? [] : [
        {
            command: 'cd ../api && python -m uvicorn main:app --port 8001 --log-level warning',
            url: 'http://127.0.0.1:8001/health',
            reuseExistingServer: true,
            timeout: 120 * 1000,
            stderr: 'pipe',
        },
        {
            command: 'cd ../frontend && npm run dev',
            url: 'http://127.0.0.1:5173',
            reuseExistingServer: true,
            timeout: 120 * 1000,
            stderr: 'pipe',
        },
    ],
});
