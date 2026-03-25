/**
 * Playwright E2E Configuration for Home Assistant
 *
 * This configuration is designed for testing the Home Assistant UI
 * including the EV Trip Planner integration dashboard.
 *
 * Usage:
 *   npx playwright test              # Run all tests
 *   npx playwright test --headed     # Run with browser visible
 *   npx playwright test --debug      # Run in debug mode
 */

import { defineConfig, devices } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

// Load environment variables from worktree .env (without external deps)
const envPath = path.resolve(__dirname, '../../.env');
if (fs.existsSync(envPath)) {
  const lines = fs.readFileSync(envPath, 'utf8').split(/\r?\n/);
  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line || line.startsWith('#')) {
      continue;
    }

    const separator = line.indexOf('=');
    if (separator < 1) {
      continue;
    }

    const key = line.slice(0, separator).trim();
    let value = line.slice(separator + 1).trim();
    value = value.replace(/^['\"]|['\"]$/g, '');

    if (key && process.env[key] === undefined) {
      process.env[key] = value;
    }
  }
}

// Ensure E2E credentials are always available (mock-safe defaults)
process.env.HA_URL = process.env.HA_URL || 'http://192.168.1.100:18123';
process.env.HA_USER = process.env.HA_USER || process.env.HA_USERNAME || 'tests';
process.env.HA_USERNAME = process.env.HA_USERNAME || process.env.HA_USER;
process.env.HA_PASSWORD = process.env.HA_PASSWORD || 'tests';

// Get HA URL from environment or use default
const haUrl = process.env.HA_URL || 'http://192.168.1.100:18123';
const haToken = process.env.HA_TOKEN || '';

export default defineConfig({
  testDir: './',
  timeout: 60000,
  expect: {
    timeout: 10000,
  },
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [
    ['html', { outputFolder: 'playwright-report' }],
    ['junit', { outputFile: 'playwright-results.xml' }],
    ['list'],
  ],
  use: {
    baseURL: haUrl,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15000,
  },
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
    {
      name: 'mobile-chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'mobile-safari',
      use: { ...devices['iPhone 12'] },
    },
  ],
  webServer: {
    command: 'cd /home/malka/ha-ev-trip-planner/test-ha && docker-compose up -d',
    url: haUrl,
    timeout: 120 * 1000,
    reuseExistingServer: true,
  },
});
