/**
 * Playwright E2E Configuration for Home Assistant
 *
 * Usage:
 *   npx playwright test              # Run all tests
 *   npx playwright test --headed     # Run with browser visible
 *   npx playwright test --debug      # Run in debug mode
 *
 * Environment Variables:
 *   HA_URL - Home Assistant URL (default: http://localhost:8123 for local testing)
 *   HA_USER - Home Assistant username (default: tests)
 *   HA_PASSWORD - Home Assistant password (default: tests)
 *
 * Note: When using hass-taste-test, the URL is generated dynamically and passed
 * directly to page.goto() in tests, so HA_URL is only needed for fallback.
 */

import { defineConfig, devices } from '@playwright/test';

const HA_URL = process.env.HA_URL || 'http://localhost:8123';
const HA_USER = process.env.HA_USER || 'tests';
const HA_PASSWORD = process.env.HA_PASSWORD || 'tests';

export default defineConfig({
  testDir: '.',
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
    baseURL: HA_URL,
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 15000,
    navigationTimeout: 30000,
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
});
