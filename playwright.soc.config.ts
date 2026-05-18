import { defineConfig } from '@playwright/test';

/**
 * Playwright config for the SOC test suite.
 *
 * Uses a separate auth setup and storage state so it has independent
 * credentials from the main test suite. This prevents state bleed
 * between suites that test different sensor configurations.
 */
export default defineConfig({
  testDir: './tests/e2e-dynamic-soc',
  timeout: 60000,
  retries: 1,
  workers: 1,
  reporter: [
    ['list'],
    ['html', { open: 'never' }],
  ],
  globalSetup: './auth.setup.soc.ts',
  use: {
    baseURL: 'http://localhost:8123',
    storageState: 'playwright/.auth/user-soc.json',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
});
