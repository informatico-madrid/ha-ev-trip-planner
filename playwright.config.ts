import { defineConfig } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
  testDir: './tests/e2e',
  // CI_SINGLE_TEST: temporarily run only trip-list-view for fast CI debugging.
  // TODO: Remove testMatch once CI is green to restore all tests.
  testMatch: process.env.CI ? 'trip-list-view.spec.ts' : undefined,
  timeout: 60000,
  retries: 1,
  workers: 1,
  reporter: [
    ['list'],
    ['html', { open: 'never' }],
  ],
  globalSetup: './auth.setup.ts',
  globalTeardown: './globalTeardown.ts',
  use: {
    baseURL: 'http://localhost:8123',
    // In CI, don't use storageState - let trusted_networks auth handle each
    // test context via navigateToPanel(). Locally, use the saved auth state.
    storageState: process.env.CI ? undefined : 'playwright/.auth/user.json',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
});