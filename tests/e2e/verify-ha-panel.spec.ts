/**
 * Verification Test: Check HA Panel Registration
 *
 * This test verifies that the EV Trip Planner panel is registered in HA
 * and accessible at the expected URL.
 *
 * Usage:
 *   npx playwright test tests/e2e/verify-ha-panel.spec.ts
 *
 * Requires:
 *   HA_URL=http://192.168.1.201:18124
 *   HA_USER=tests
 *   HA_PASSWORD=tests
 */

import { test, expect } from '@playwright/test';

const VEHICLE_ID = 'Coche2';
const HA_USER = process.env.HA_USER || 'tests';
const HA_PASSWORD = process.env.HA_PASSWORD || 'tests';

test.describe('HA Panel Registration Verification', () => {
  test('should verify HA instance is accessible', async ({ page }) => {
    await page.goto('/', {
      waitUntil: 'networkidle',
      timeout: 30000
    });

    // Check if we got a response (should see HA login page)
    const title = await page.title();
    expect(title).toBeTruthy();
  });

  test('should login and check for panel', async ({ page }) => {
    // Login
    await page.goto('/', { waitUntil: 'networkidle', timeout: 30000 });
    await page.fill('input[name="username"]', HA_USER);
    await page.fill('input[name="password"]', HA_PASSWORD);
    await page.click('ha-button[variant="brand"]');
    await page.waitForURL('/home/**', { waitUntil: 'networkidle', timeout: 30000 });

    // Try to navigate to the panel
    await page.goto(`/panel/ev-trip-planner-${VEHICLE_ID}`, {
      waitUntil: 'domcontentloaded',
      timeout: 60000
    });

    // Check if the page loaded (may have errors if panel not registered)
    const url = page.url();
    console.log('Current URL:', url);

    // Check for common error indicators
    const hasError = await page.locator('ha-panel-lovelace-dashboard').count() > 0;
    const hasNotFound = await page.locator('[part="title"] >> text:has("404")').count() > 0;

    console.log('Has Lovelace error:', hasError);
    console.log('Has 404 error:', hasNotFound);

    // If panel is not registered, HA will show a 404 or redirect to Lovelace
    expect(hasNotFound || hasError).toBe(false);
  });
});
