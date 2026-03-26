/**
 * E2E Tests: Config Flow Validation
 *
 * Tests for validation, error handling, and edge cases in EV Trip Planner Config Flow
 *
 * Usage:
 *   npx playwright test tests/e2e/test-config-flow-validation.spec.ts
 *   npx playwright test --headed
 */

import { test, expect, Page } from '@playwright/test';

/**
 * Helper function to access hass instance from global setup
 */
function getHassInstance(): { link: string; configDir: string } {
  const serverInfoPath = '/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/playwright/.auth/server-info.json';
  const fs = require('fs');
  const path = require('path');
  const serverInfo = JSON.parse(fs.readFileSync(serverInfoPath, 'utf8'));
  return {
    link: serverInfo.link,
    configDir: serverInfo.configDir,
  };
}

test.describe('EV Trip Planner Config Flow Validation', () => {
  let hassUrl: string;

  test.beforeAll(async () => {
    // Initialize hass-taste-test to get ephemeral HA URL
    const hass = getHassInstance();
    hassUrl = hass.link;
    console.log('[ConfigFlow Validation] Ephemeral HA URL:', hassUrl);
  });

  /**
   * Test 2: Navigate to integrations page and verify EV Trip Planner appears in add integration list
   */
  test('should navigate to integrations and find EV Trip Planner', async ({ page }) => {
    console.log('[Nav] Navigating to integrations dashboard...');

    // Extract base URL from hassUrl (without query params which are for auth)
    const url = new URL(hassUrl);
    const baseUrl = `${url.protocol}//${url.host}`;

    // Navigate to integrations dashboard
    await page.goto(`${baseUrl}/config/integrations/dashboard`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });

    // Verify we're on the integrations page
    await expect(page.getByRole('heading', { name: 'Integrations' })).toBeVisible({
      timeout: 10000,
    });

    // Click "Add integration" button
    console.log('[Nav] Clicking Add integration...');
    await page.click('text="Add integration"');

    // Search for EV Trip Planner
    console.log('[Nav] Searching for EV Trip Planner...');
    await page.fill('input[placeholder="Search"]', 'EV Trip Planner');

    // Verify EV Trip Planner appears in search results
    const evTripPlannerLink = page.getByRole('button', { name: /EV Trip Planner/i });
    await expect(evTripPlannerLink).toBeVisible({ timeout: 10000 });

    console.log('[Test] EV Trip Planner found in integrations list!');
  });

  /**
   * Test 3: Validate empty vehicle name
   */
  test('should show validation error for empty vehicle name', async ({ page }) => {
    console.log('[Validation] Testing empty vehicle name...');

    const url = new URL(hassUrl);
    const baseUrl = `${url.protocol}//${url.host}`;

    // Navigate to integrations and add EV Trip Planner
    await page.goto(`${baseUrl}/config/integrations/dashboard`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });
    await page.click('text="Add integration"');
    await page.fill('input[placeholder="Search"]', 'EV Trip Planner');
    await page.click('text="EV Trip Planner"');

    // Wait for dialog
    const dialogHeading = page.getByRole('heading', { name: 'EV Trip Planner' });
    await dialogHeading.waitFor({ state: 'visible', timeout: 15000 });

    // Try to submit without filling vehicle name
    await page.getByRole('button', { name: 'Submit' }).click();

    // Wait for validation error
    await expect(
      page.getByText(/vehicle name is required|vehicle_name.*required/i)
    ).toBeVisible({ timeout: 5000 });

    console.log('[Test] Validation error shown for empty vehicle name!');
  });

  /**
   * Test 4: Validate vehicle name too long (>100 characters)
   */
  test('should show validation error for vehicle name exceeding 100 characters', async ({
    page,
  }) => {
    console.log('[Validation] Testing vehicle name too long...');

    const url = new URL(hassUrl);
    const baseUrl = `${url.protocol}//${url.host}`;

    // Navigate to integrations and add EV Trip Planner
    await page.goto(`${baseUrl}/config/integrations/dashboard`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });
    await page.click('text="Add integration"');
    await page.fill('input[placeholder="Search"]', 'EV Trip Planner');
    await page.click('text="EV Trip Planner"');

    // Wait for dialog
    const dialogHeading = page.getByRole('heading', { name: 'EV Trip Planner' });
    await dialogHeading.waitFor({ state: 'visible', timeout: 15000 });

    // Fill vehicle name with >100 characters
    const tooLongName = 'A'.repeat(101) + ' Test Vehicle';
    await page.getByRole('textbox', { name: 'vehicle_name*' }).fill(tooLongName);

    // Try to submit
    await page.getByRole('button', { name: 'Submit' }).click();

    // Wait for validation error about length
    await expect(
      page.getByText(/must be less than 100 characters|exceeds maximum/i)
    ).toBeVisible({ timeout: 5000 });

    console.log('[Test] Validation error shown for vehicle name too long!');
  });

  /**
   * Test 5: Validate vehicle name with valid value
   */
  test('should accept valid vehicle name', async ({ page }) => {
    console.log('[Validation] Testing valid vehicle name...');

    const url = new URL(hassUrl);
    const baseUrl = `${url.protocol}//${url.host}`;

    // Navigate to integrations and add EV Trip Planner
    await page.goto(`${baseUrl}/config/integrations/dashboard`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });
    await page.click('text="Add integration"');
    await page.fill('input[placeholder="Search"]', 'EV Trip Planner');
    await page.click('text="EV Trip Planner"');

    // Wait for dialog
    const dialogHeading = page.getByRole('heading', { name: 'EV Trip Planner' });
    await dialogHeading.waitFor({ state: 'visible', timeout: 15000 });

    // Fill valid vehicle name
    const validName = 'Mi Vehiculo Validado';
    await page.getByRole('textbox', { name: 'vehicle_name*' }).fill(validName);
    await page.getByRole('button', { name: 'Submit' }).click();

    // Verify transition to next step (sensors)
    await expect(
      page.getByRole('textbox', { name: /battery capacity|kwh/i })
    ).toBeVisible({ timeout: 10000 });

    console.log('[Test] Valid vehicle name accepted!');
  });

  /**
   * Test 6: Skip optional steps (EMHASS)
   */
  test('should allow skipping optional EMHASS configuration', async ({ page }) => {
    console.log('[Validation] Testing optional step skip...');

    const url = new URL(hassUrl);
    const baseUrl = `${url.protocol}//${url.host}`;

    // Navigate to integrations and add EV Trip Planner
    await page.goto(`${baseUrl}/config/integrations/dashboard`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });
    await page.click('text="Add integration"');
    await page.fill('input[placeholder="Search"]', 'EV Trip Planner');
    await page.click('text="EV Trip Planner"');

    // Wait for dialog
    const dialogHeading = page.getByRole('heading', { name: 'EV Trip Planner' });
    await dialogHeading.waitFor({ state: 'visible', timeout: 15000 });

    // Fill vehicle name
    await page.getByRole('textbox', { name: 'vehicle_name*' }).fill('Test Vehicle');
    await page.getByRole('button', { name: 'Submit' }).click();

    // Fill sensor values
    await page.getByRole('textbox', { name: 'battery_capacity_kwh*' }).fill('75.0');
    await page.getByRole('textbox', { name: 'charging_power_kw*' }).fill('11.0');
    await page.getByRole('textbox', { name: 'kwh_per_km*' }).fill('0.17');
    await page.getByRole('spinbutton', { name: 'safety_margin_percent*' }).fill('15');
    await page.getByRole('button', { name: 'Submit' }).click();

    // EMHASS step should be optional - just click Submit to skip
    console.log('[Validation] Skipping optional EMHASS configuration...');
    await page.getByRole('button', { name: 'Submit' }).click();

    // Should proceed to presence step
    await expect(
      page.getByRole('heading', { name: 'EV Trip Planner' })
    ).toBeVisible({ timeout: 10000 });

    console.log('[Test] Optional EMHASS step skipped successfully!');
  });

  /**
   * Test 7: Handle special characters in vehicle name
   */
  test('should handle special characters in vehicle name', async ({ page }) => {
    console.log('[Validation] Testing special characters...');

    const url = new URL(hassUrl);
    const baseUrl = `${url.protocol}//${url.host}`;

    // Navigate to integrations and add EV Trip Planner
    await page.goto(`${baseUrl}/config/integrations/dashboard`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });
    await page.click('text="Add integration"');
    await page.fill('input[placeholder="Search"]', 'EV Trip Planner');
    await page.click('text="EV Trip Planner"');

    // Wait for dialog
    const dialogHeading = page.getByRole('heading', { name: 'EV Trip Planner' });
    await dialogHeading.waitFor({ state: 'visible', timeout: 15000 });

    // Fill vehicle name with special characters
    const specialName = 'Mi Tesla Model 3 - ¡Verão! 🚗 (2024)';
    await page.getByRole('textbox', { name: 'vehicle_name*' }).fill(specialName);
    await page.getByRole('button', { name: 'Submit' }).click();

    // Verify transition to next step
    await expect(
      page.getByRole('textbox', { name: /battery capacity|kwh/i })
    ).toBeVisible({ timeout: 10000 });

    console.log('[Test] Special characters in vehicle name handled successfully!');
  });

  /**
   * Test 8: Complete full config flow and verify vehicle appears in sidebar
   */
  test('should complete full config flow and verify vehicle in sidebar', async ({
    page,
  }) => {
    console.log('[Validation] Testing complete config flow...');

    const url = new URL(hassUrl);
    const baseUrl = `${url.protocol}//${url.host}`;

    // Navigate to integrations and add EV Trip Planner
    await page.goto(`${baseUrl}/config/integrations/dashboard`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });
    await page.click('text="Add integration"');
    await page.fill('input[placeholder="Search"]', 'EV Trip Planner');
    await page.click('text="EV Trip Planner"');

    // Wait for dialog
    const dialogHeading = page.getByRole('heading', { name: 'EV Trip Planner' });
    await dialogHeading.waitFor({ state: 'visible', timeout: 15000 });

    // Step 1: Fill vehicle name
    console.log('[Validation] Filling vehicle name...');
    await page.getByRole('textbox', { name: 'vehicle_name*' }).fill('Test Vehicle');
    await page.getByRole('button', { name: 'Submit' }).click();

    // Step 2: Fill sensor values
    console.log('[Validation] Filling sensor values...');
    await page.getByRole('textbox', { name: 'battery_capacity_kwh*' }).fill('75.0');
    await page.getByRole('textbox', { name: 'charging_power_kw*' }).fill('11.0');
    await page.getByRole('textbox', { name: 'kwh_per_km*' }).fill('0.17');
    await page.getByRole('spinbutton', { name: 'safety_margin_percent*' }).fill('15');
    await page.getByRole('button', { name: 'Submit' }).click();

    // Step 3: Skip optional EMHASS
    console.log('[Validation] Skipping EMHASS...');
    await page.getByRole('button', { name: 'Submit' }).click();

    // Step 4: Select presence sensors
    console.log('[Validation] Selecting presence sensors...');
    await page.getByRole('combobox', { name: /charging sensor/i }).click();
    await page.getByRole('option', { name: /coche1 cargando/i }).click();

    await page.getByRole('combobox', { name: /home sensor/i }).click();
    await page.getByRole('option', { name: /coche1 en casa/i }).click();

    await page.getByRole('combobox', { name: /plugged sensor/i }).click();
    await page.getByRole('option', { name: /coche1 enchufado/i }).click();

    await page.getByRole('button', { name: /Submit|Next/i }).click();

    // Verify success message
    console.log('[Validation] Waiting for success message...');
    await expect(
      page.locator('div:has-text("Successfully configured")')
    ).toBeVisible({ timeout: 10000 });

    // Navigate to dashboard
    console.log('[Nav] Navigating to dashboard...');
    await page.goto('/dashboard');

    // Click on EV Trip Planner panel in sidebar
    console.log('[Nav] Looking for EV Trip Planner panel in sidebar...');
    const sidebarLink = page.getByRole('link', {
      name: /EV Trip Planner|Test Vehicle/i,
    });
    await expect(sidebarLink).toBeVisible({ timeout: 10000 });
    await sidebarLink.click();

    // Verify panel loaded with vehicle name
    console.log('[Validation] Verifying panel loaded...');
    await expect(
      page.getByRole('heading', { name: /Test Vehicle/i })
    ).toBeVisible({ timeout: 10000 });

    console.log('[Test] Complete config flow and sidebar verification passed!');
  });
});
