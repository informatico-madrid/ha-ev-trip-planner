/**
 * E2E Test: Single Panel for Vehicle "Chispitas" - US-1 Validation
 *
 * Validates US-1: Prevent Duplicate Vehicle Panels
 * Uses auth.setup.ts for authentication
 *
 * User Story:
 * As a vehicle owner, I want only one panel to be created when I add a vehicle
 * So that I do not see duplicate entries in my Home Assistant sidebar
 *
 * Acceptance Criteria (US-1):
 * - AC-1.1: Given a user adds a vehicle named "Chispitas", when the integration is set up,
 *           then exactly ONE panel is created (not two panels with URLs differing only in case)
 * - AC-1.2: Panel URL uses normalized (lowercased) vehicle_id
 * - AC-1.3: No two panels exist with URLs differing only in case
 *
 * Usage:
 *   npx playwright test test-single-panel-chispitas.spec.ts
 */

import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const VEHICLE_NAME = 'Chispitas';
const EXPECTED_VEHICLE_ID = 'chispitas';  // normalized lowercase
const EXPECTED_URL_PATTERN = `/ev-trip-planner-${EXPECTED_VEHICLE_ID}`;
const SERVER_INFO_PATH = path.join(process.cwd(), 'playwright/.auth/server-info.json');

function getBaseUrl(): string {
  if (fs.existsSync(SERVER_INFO_PATH)) {
    const info = JSON.parse(fs.readFileSync(SERVER_INFO_PATH, 'utf-8'));
    return new URL(info.link || info.baseUrl || process.env.HA_BASE_URL!).origin;
  }
  throw new Error('Server info not found - run auth.setup.ts first');
}

test.describe('EV Trip Planner - Single Panel for Vehicle "Chispitas" (US-1)', () => {
  /**
   * Navigate to the integrations dashboard to add a new vehicle
   */
  async function navigateToIntegrations(page: any): Promise<void> {
    const baseUrl = getBaseUrl();
    console.log('[Test Setup] Navigating to integrations dashboard...');
    await page.goto(`${baseUrl}/config/integrations/dashboard`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });

    // Verify sidebar is visible (authentication check)
    const sidebarVisible = await page
      .locator('ha-sidebar, [role="navigation"]')
      .isVisible({ timeout: 10000 })
      .catch(() => false);

    if (!sidebarVisible) {
      throw new Error('Not authenticated - sidebar not visible');
    }
    console.log('[Test Setup] Sidebar visible, authenticated');
  }

  /**
   * Add a new vehicle via the HA Config Flow
   */
  async function addVehicleViaConfigFlow(page: any, vehicleName: string): Promise<void> {
    console.log(`[Config Flow] Starting to add vehicle: ${vehicleName}`);

    // Navigate to integrations
    await navigateToIntegrations(page);

    // Click "Add integration"
    console.log('[Config Flow] Clicking Add integration...');
    await page.getByRole('button', { name: /Add integration/i }).click();

    // Wait for the integration selection dialog
    await page.waitForTimeout(1000);

    // Search for EV Trip Planner
    console.log('[Config Flow] Searching for EV Trip Planner...');
    const searchBox = page.getByRole('textbox', { name: /Search for a brand name/i });
    await searchBox.waitFor({ state: 'visible', timeout: 10000 });
    await searchBox.fill('EV Trip Planner');
    await expect(page.getByText('EV Trip Planner')).toBeVisible({ timeout: 5000 });

    // Select EV Trip Planner
    console.log('[Config Flow] Selecting EV Trip Planner...');
    await page.getByText('EV Trip Planner').click();

    // Wait for the config dialog to appear
    console.log('[Config Flow] Waiting for config dialog...');
    await page.waitForTimeout(2000);

    // Step 1: Enter vehicle name
    console.log('[Config Flow Step 1] Entering vehicle name...');
    const vehicleNameField = page.locator('input[name="vehicle_name"]');
    await vehicleNameField.waitFor({ state: 'visible', timeout: 30000 });
    await vehicleNameField.click();
    await vehicleNameField.type(vehicleName, { delay: 50 });
    await page.getByRole('button', { name: 'Submit' }).click();

    // Wait for step 2 form
    await page.waitForTimeout(2000);

    // Step 2: Fill sensors (numeric fields)
    console.log('[Config Flow Step 2] Filling sensor values...');
    const numericInputs = page.locator('input[type="number"]');
    const count = await numericInputs.count();
    console.log(`[Config Flow Step 2] Found ${count} numeric inputs`);

    if (count >= 4) {
      await numericInputs.nth(0).click();
      await numericInputs.nth(0).type('75.0', { delay: 30 });
      await numericInputs.nth(1).click();
      await numericInputs.nth(1).type('11.0', { delay: 30 });
      await numericInputs.nth(2).click();
      await numericInputs.nth(2).type('0.17', { delay: 30 });
      await numericInputs.nth(3).click();
      await numericInputs.nth(3).type('15', { delay: 30 });
    }
    await page.getByRole('button', { name: 'Submit' }).click();

    // Step 3: EMHASS (optional)
    console.log('[Config Flow Step 3] Skipping EMHASS (optional)...');
    await page.getByRole('button', { name: 'Submit' }).click();

    // Wait for step 4 (presence sensors)
    await page.waitForTimeout(2000);

    // Step 4: Presence sensors - submit with auto-selection
    console.log('[Config Flow Step 4] Submitting presence sensors...');
    const presenceSubmitButton = page.getByRole('button', { name: /Submit|Next/i });
    await presenceSubmitButton.waitFor({ state: 'visible', timeout: 10000 });
    await presenceSubmitButton.click();

    // Wait for notifications form
    await page.waitForTimeout(2000);

    // Step 5: Notifications - submit if visible
    const notificationsSubmitButton = page.getByRole('button', { name: /Submit|Next/i });
    const notificationsVisible = await notificationsSubmitButton.isVisible({ timeout: 3000 }).catch(() => false);
    if (notificationsVisible) {
      console.log('[Config Flow Step 5] Submitting notifications...');
      await notificationsSubmitButton.click();
      await page.waitForTimeout(1000);
    }

    console.log(`[Config Flow] Vehicle "${vehicleName}" added successfully`);
  }

  /**
   * Get all EV Trip Planner sidebar items and count them
   */
  async function getEvTripPlannerSidebarItems(page: any): Promise<number> {
    const sidebar = page.locator('ha-sidebar');
    await sidebar.waitFor({ state: 'visible', timeout: 10000 });

    // Find all items containing "ev-trip-planner" or "Chispitas" in the sidebar
    const sidebarText = await sidebar.textContent();
    console.log('[Sidebar Analysis] Sidebar content:', sidebarText?.substring(0, 500));

    // Look for items with "Chispitas" or the panel URL pattern
    const evTripPlannerItems = page.locator('ha-sidebar >> text=/Chispitas|ev-trip-planner/i');
    const count = await evTripPlannerItems.count();
    console.log(`[Sidebar Analysis] Found ${count} EV Trip Planner related items`);

    return count;
  }

  test('should add vehicle "Chispitas" and verify single panel in sidebar', async ({ page }) => {
    // Step 1: Add vehicle "Chispitas" via config flow
    console.log('[Test] Starting: Add vehicle "Chispitas" via config flow');
    await addVehicleViaConfigFlow(page, VEHICLE_NAME);

    // Step 2: Navigate to the dashboard
    console.log('[Test] Navigating to dashboard...');
    const baseUrl = getBaseUrl();
    await page.goto(`${baseUrl}/dashboard`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });
    await page.waitForTimeout(2000);

    // Step 3: Verify exactly ONE panel appears in sidebar for Chispitas
    console.log('[Test] Checking sidebar for EV Trip Planner panels...');
    const sidebar = page.locator('ha-sidebar');
    await expect(sidebar).toBeVisible({ timeout: 10000 });

    // Look for sidebar items containing "Chispitas"
    const chispitasItems = sidebar.getByText(/Chispitas/i);
    const itemCount = await chispitasItems.count();
    console.log(`[Test] Found ${itemCount} sidebar items with "Chispitas"`);

    // There should be EXACTLY ONE panel for Chispitas
    expect(itemCount).toBe(1);
    console.log('[Test] PASS: Exactly one panel found for "Chispitas"');

    // Step 4: Click on the Chispitas panel and verify URL
    console.log('[Test] Clicking on Chispitas panel in sidebar...');
    await chispitasItems.first().click();

    // Wait for navigation
    await page.waitForTimeout(2000);

    // Step 5: Verify URL is lowercase /ev-trip-planner-chispitas
    const currentUrl = page.url();
    console.log(`[Test] Current URL after click: ${currentUrl}`);

    // The URL should contain the normalized (lowercase) vehicle_id
    expect(currentUrl).toContain(EXPECTED_URL_PATTERN);
    console.log(`[Test] PASS: URL contains expected pattern "${EXPECTED_URL_PATTERN}"`);

    // Also verify it's NOT the uppercase variant
    expect(currentUrl).not.toContain('/ev-trip-planner-Chispitas');
    console.log('[Test] PASS: URL does not contain uppercase variant');

    console.log('[Test] All US-1 acceptance criteria verified successfully');
  });

  test('should have normalized URL when navigating directly to Chispitas panel', async ({ page }) => {
    // Step 1: Navigate directly to the expected URL
    const baseUrl = getBaseUrl();
    const panelUrl = `${baseUrl}${EXPECTED_URL_PATTERN}`;
    console.log(`[Test] Navigating directly to: ${panelUrl}`);

    await page.goto(panelUrl, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });

    await page.waitForTimeout(2000);

    // Step 2: Verify the URL is still the normalized lowercase version
    const currentUrl = page.url();
    console.log(`[Test] Current URL: ${currentUrl}`);

    expect(currentUrl).toBe(panelUrl);
    console.log('[Test] PASS: Direct navigation to normalized URL works');

    // Step 3: Verify panel content is loaded (not 404)
    const bodyText = await page.textContent('body');
    expect(bodyText || '').not.toContain('404');
    expect(bodyText || '').not.toContain('Not Found');
    console.log('[Test] PASS: Panel loaded without 404 error');

    console.log('[Test] Direct URL navigation test passed');
  });

  test('should NOT have duplicate panels with different case variations', async ({ page }) => {
    // Navigate to dashboard
    const baseUrl = getBaseUrl();
    await page.goto(`${baseUrl}/dashboard`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });
    await page.waitForTimeout(2000);

    // Check sidebar for any case variations of the panel
    const sidebar = page.locator('ha-sidebar');
    await expect(sidebar).toBeVisible({ timeout: 10000 });

    // Count items with "chispitas" (lowercase)
    const lowercaseItems = sidebar.getByText(/chispitas/i);
    const lowercaseCount = await lowercaseItems.count();

    // Count items with "Chispitas" (mixed case)
    const mixedcaseItems = sidebar.getByText(/Chispitas/i);
    const mixedcaseCount = await mixedcaseItems.count();

    console.log(`[Test] Lowercase "chispitas" items: ${lowercaseCount}`);
    console.log(`[Test] Mixed case "Chispitas" items: ${mixedcaseCount}`);

    // There should be only ONE panel total (matching the normalized vehicle name)
    expect(mixedcaseCount).toBe(1);
    console.log('[Test] PASS: Only one panel exists (no duplicates with different case)');

    // Verify there is no lowercase-only "chispitas" panel (which would be a different URL)
    // The sidebar should show "Chispitas" not "chispitas"
    const sidebarContent = await sidebar.textContent();
    const hasLowercaseOnly = sidebarContent?.includes('ev-trip-planner-chispitas') &&
                             !sidebarContent?.includes('Chispitas');
    expect(hasLowercaseOnly).toBe(false);
    console.log('[Test] PASS: No lowercase-only URL variant in sidebar');
  });
});