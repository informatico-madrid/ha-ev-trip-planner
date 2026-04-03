import { defineConfig, devices } from '@playwright/test';
import * as path from 'path';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false,           // One browser at a time; hass-taste-test ports conflict
  forbidOnly: !!process.env.CI,   // Fail on only() in CI
  retries: 0,                     // No retries; tests are fast and isolated
  workers: 1,                     // Single worker; ephemeral HA is not parallel-safe
  reporter: [['html', { open: 'never' }]],

  use: {
    baseURL: 'http://localhost:8123',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  globalSetup: path.join(__dirname, 'tests', 'global.setup.ts'),
  globalTeardown: path.join(__dirname, 'tests', 'global.teardown.ts'),

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
