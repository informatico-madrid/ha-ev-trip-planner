/**
 * Playwright E2E Configuration for Home Assistant
 *
 * Projects:
 *   - auth: Authenticates and saves storageState to file
 *   - chromium: Main tests - uses storageState from auth project
 */

import { defineConfig, devices } from '@playwright/test';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const rootDir = join(__dirname, '..', '..');

export default defineConfig({
  testDir: __dirname,
  timeout: 60000,
  expect: {
    timeout: 10000,
  },
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: 0,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['junit', { outputFile: 'playwright-results.xml' }],
    ['list'],
  ],

  globalSetup: join(rootDir, 'tests', 'global.setup.ts'),
  globalTeardown: join(rootDir, 'tests', 'global.teardown.ts'),

  use: {
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15000,
    navigationTimeout: 30000,
  },

  projects: [
    // Step 1: Authentication setup - saves storage state
    {
      name: 'auth',
      testMatch: 'auth.setup.ts',
      use: {
        ...devices['Desktop Chrome'],
      },
    },

    // Step 2: Main E2E tests - uses saved auth state from auth project
    {
      name: 'chromium',
      testMatch: ['**/*.spec.ts'],
      use: {
        ...devices['Desktop Chrome'],
      },
      dependencies: ['auth'],
    },
  ],
});
