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

// Get HA URL from environment or use default
const haUrl = process.env.HA_URL || 'http://192.168.1.100:8123';
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
    command: '',
    url: haUrl,
