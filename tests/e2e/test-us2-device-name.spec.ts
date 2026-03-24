/**
 * E2E Tests for User Story 2: Device with Custom Name
 *
 * This test verifies that devices are created with the custom name "EV Trip Planner {nombre}"
 * where {nombre} is the vehicle name provided by the user (not the internal ID).
 *
 * Acceptance Scenarios:
 * 1. Device name is "EV Trip Planner {nombre}" not the slug
 * 2. Device identifier uses slug of the name
 * 3. Device URL uses slug (e.g., /config/devices/device/chispitas)
 *
 * Usage:
 *   npx playwright test test-us2-device-name.spec.ts
 */

import { test, expect } from '@playwright/test';

const HA_URL = process.env.HA_URL || 'http://localhost:18123';
const HA_USERNAME = process.env.HA_USERNAME || 'admin';
const HA_PASSWORD = process.env.HA_PASSWORD || '';

test.describe('US2: Device with Custom Name', () => {
  test('should verify device name follows "EV Trip Planner {nombre}" pattern', async ({
    page,
  }) => {
    // Skip if no password provided
    if (!HA_PASSWORD) {
      test.skip('No HA_PASSWORD provided');
    }

    // Login to Home Assistant
    await page.goto(`${HA_URL}/auth/login`);
    await page.fill('#username', HA_USERNAME);
    await page.fill('#password', HA_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL(`${HA_URL}/dashboard`);

    // Navigate to integrations page
    await page.goto(`${HA_URL}/config/integrations`);
    await page.waitForLoadState('networkidle');

    // Find EV Trip Planner integration
    const evIntegrationLink = page.getByRole('link', {
      name: /Planificador de Viajes EV/i,
    });
    await expect(evIntegrationLink).toBeVisible();

    // Click on the integration
    await evIntegrationLink.click();
    await page.waitForLoadState('networkidle');

    // Verify the device name is "EV Trip Planner {nombre}" format
    // The device name should appear in the integration page
    const deviceNameText = await page
      .locator('[class*="device"] [class*="name"], [class*="integration-item"]')
      .textContent();

    // Check that the device name contains "EV Trip Planner" followed by a meaningful name
    // (not a long hex ID like 0d8f6f83...)
    const hasEvTripPlannerPrefix = deviceNameText?.includes('EV Trip Planner');
    expect(hasEvTripPlannerPrefix).toBe(true);

    // Verify it doesn't contain a long hex ID after "EV Trip Planner "
    const hasLongHexId = /\bEV Trip Planner [0-9A-F]{20,}/.test(deviceNameText || '');
    expect(hasLongHexId).toBe(false);

    // The device name should be "EV Trip Planner {nombre}" where {nombre} is the vehicle name
    // Examples: "EV Trip Planner Coche2", "EV Trip Planner Chispitas"
    const deviceNameMatch = deviceNameText?.match(/EV Trip Planner ([^,]+)/);
    if (deviceNameMatch) {
      const vehicleName = deviceNameMatch[1].trim();
      // Vehicle name should be a reasonable length (not too short, not too long)
      expect(vehicleName.length).toBeGreaterThan(0);
      expect(vehicleName.length).toBeLessThan(50);
      // Vehicle name should not contain hex characters only
      expect(/^[0-9a-f]+$/.test(vehicleName)).toBe(false);
    }
  });

  test('should verify device info in integration page', async ({ page }) => {
    if (!HA_PASSWORD) {
      test.skip('No HA_PASSWORD provided');
    }

    // Login
    await page.goto(`${HA_URL}/auth/login`);
    await page.fill('#username', HA_USERNAME);
    await page.fill('#password', HA_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL(`${HA_URL}/dashboard`);

    // Navigate to integrations
    await page.goto(`${HA_URL}/config/integrations`);
    await page.waitForLoadState('networkidle');

    // Click on EV Trip Planner integration
    const evIntegrationLink = page.getByRole('link', {
      name: /Planificador de Viajes EV/i,
    });
    await evIntegrationLink.click();
    await page.waitForLoadState('networkidle');

    // Verify device count is shown
    const deviceCountLink = page.getByRole('link', { name: /1 dispositivo/i });
    await expect(deviceCountLink).toBeVisible();

    // Click on device link
    await deviceCountLink.click();
    await page.waitForLoadState('networkidle');

    // Get device name from the page
    const deviceHeading = await page
      .getByRole('heading', { level: 1 })
      .first()
      .textContent();

    // Device name should follow pattern "EV Trip Planner {nombre}"
    const hasCorrectPattern = deviceHeading?.includes('EV Trip Planner');
    expect(hasCorrectPattern).toBe(true);

    // Should not have long hex ID
    const hasHexId = /\bEV Trip Planner [0-9a-f]{20,}/.test(deviceHeading || '');
    expect(hasHexId).toBe(false);
  });
});
