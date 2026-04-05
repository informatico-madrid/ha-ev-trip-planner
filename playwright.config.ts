import { defineConfig } from '@playwright/test';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

export default defineConfig({
  testDir: './tests/e2e',
  timeout: 120000,
  retries: 1,
  workers: 1,
  reporter: [
    ['list'],
    ['html', { open: 'never' }],
  ],
  globalSetup: './auth.setup.ts',
  globalTeardown: './globalTeardown.ts',
  // webServer manages HA lifecycle - Playwright waits for it automatically
  webServer: {
    command: 'hass -c /tmp/ha-e2e-config --log-no-color',
    url: 'http://localhost:8123/api/',
    reuseExistingServer: !process.env.CI,
    timeout: 180_000, // 3 min for HA startup in CI
    stdout: 'pipe',
    stderr: 'pipe',
  },
  use: {
    baseURL: 'http://localhost:8123',
    storageState: 'playwright/.auth/user.json',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
});