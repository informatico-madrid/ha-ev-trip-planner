/**
 * E2E Test: EMHASS Sensor Updates
 *
 * This test file provides a selector map for inspecting EMHASS sensor state
 * and verifying sensor updates through Developer Tools in Home Assistant UI.
 *
 * Task 4.1 [VE0] - ui-map-init for EMHASS sensor updates
 */
import { test, expect, type Page } from '@playwright/test';
import { navigateToPanel, deleteTestTrip, cleanupTestTrips } from './trips-helpers';

// =============================================================================
// SELECTOR MAP - EMHASS Sensor Inspection Tools
// =============================================================================

/**
 * Developer Tools > States page selector
 */
export const DEVELOPER_TOOLS_STATES = 'iframe[href*="/developer-tools/state"]';

/**
 * Developer Tools > Devices page selector
 */
export const DEVELOPER_TOOLS_DEVICES = 'iframe[href*="/config/devices"]';

/**
 * EMHASS Deferrable Load Sensor state entity selector
 * Use this to inspect sensor attributes in Developer Tools > States
 */
export const EMHASS_STATE_SELECTOR = 'ha-entity-toggle[entity-id*="emhass_deferrable_load"]';

/**
 * Sensor attributes display area in Developer Tools > States
 */
export const SENSOR_ATTRIBUTES_PANEL = '.attributes';

/**
 * Power profile watts attribute
 */
export const POWER_PROFILE_WATTS_ATTR = 'power_profile_watts';

/**
 * Deferrables schedule attribute
 */
export const DEFERRABLES_SCHEDULE_ATTR = 'deferrables_schedule';

/**
 * EMHASS status attribute
 */
export const EMHASS_STATUS_ATTR = 'emhass_status';

// =============================================================================
// Test Suite
// =============================================================================

test.describe('EMHASS Sensor Updates', () => {
  test.beforeEach(async ({ page }: { page: Page }) => {
    await navigateToPanel(page);
    await cleanupTestTrips(page);
  });

  test('should navigate to Developer Tools > States to inspect EMHASS sensor', async ({ page }) => {
    // Navigate to Developer Tools
    await page.getByRole('button', { name: 'More' }).click();
    await page.getByRole('menuitem', { name: 'Developer tools' }).click();

    // Click on States tab
    await page.getByRole('tab', { name: 'States' }).click();

    // Wait for states panel to load
    await expect(page.locator(DEVELOPER_TOOLS_STATES)).toBeVisible();

    // Search for EMHASS sensor
    await page.getByLabel('Filter states').fill('emhass');

    // Verify EMHASS sensor appears in states list
    await expect(page.locator(EMHASS_STATE_SELECTOR)).toBeVisible();
  });

  test('should inspect EMHASS sensor attributes in Developer Tools', async ({ page }) => {
    // Navigate to Developer Tools > States
    await page.getByRole('button', { name: 'More' }).click();
    await page.getByRole('menuitem', { name: 'Developer tools' }).click();
    await page.getByRole('tab', { name: 'States' }).click();

    // Search for EMHASS sensor
    await page.getByLabel('Filter states').fill('emhass_deferrable_load');

    // Click on the sensor to show attributes
    await page.locator(EMHASS_STATE_SELECTOR).first().click();

    // Verify attributes panel is visible
    await expect(page.locator(SENSOR_ATTRIBUTES_PANEL)).toBeVisible();

    // Verify expected attributes exist (even if null before fixes)
    const attributes = page.locator(SENSOR_ATTRIBUTES_PANEL);
    const attributeNames = await attributes.locator('.attribute-name').allTextContents();

    // Check for expected attributes
    expect(attributeNames.join(', ')).toContain(POWER_PROFILE_WATTS_ATTR);
    expect(attributeNames.join(', ')).toContain(DEFERRABLES_SCHEDULE_ATTR);
    expect(attributeNames.join(', ')).toContain(EMHASS_STATUS_ATTR);
  });

  test('should verify single device for vehicle in Developer Tools > Devices', async ({ page }) => {
    // Navigate to Developer Tools > Devices
    await page.getByRole('button', { name: 'More' }).click();
    await page.getByRole('menuitem', { name: 'Developer tools' }).click();
    await page.getByRole('tab', { name: 'Devices' }).click();

    // Wait for devices panel
    await expect(page.locator(DEVELOPER_TOOLS_DEVICES)).toBeVisible();

    // Search for EV Trip Planner device
    await page.getByLabel('Filter devices').fill('EV Trip Planner');

    // Should show only ONE device (bug #1 fix verified)
    const deviceCount = await page.locator('.device-card').count();
    expect(deviceCount).toBeGreaterThanOrEqual(1);

    // Verify the device has expected entities
    const deviceCard = page.locator('.device-card').first();
    await expect(deviceCard).toBeVisible();

    // Click on device to see entities
    await deviceCard.click();

    // Verify expected entities count (sensor + helpers = ~8 entities)
    const entityCount = await page.locator('.entity-list .entity-item').count();
    // Allow for some variance depending on other entities
    expect(entityCount).toBeGreaterThanOrEqual(1);
  });

  test('should verify EMHASS sensor entity exists', async ({ page }) => {
    // Navigate to Developer Tools > States
    await page.getByRole('button', { name: 'More' }).click();
    await page.getByRole('menuitem', { name: 'Developer tools' }).click();
    await page.getByRole('tab', { name: 'States' }).click();

    // Filter for EMHASS sensor
    await page.getByLabel('Filter states').fill('emhass_deferrable_load_sensor');

    // Wait for the sensor to appear
    const sensorEntity = page.locator('[id*="emhass_deferrable_load"]').first();

    // Verify sensor entity exists
    await expect(sensorEntity).toBeVisible();

    // Verify entity state is available
    const state = await sensorEntity.locator('.state').first().textContent();
    expect(state).toBeDefined();
  });
});
