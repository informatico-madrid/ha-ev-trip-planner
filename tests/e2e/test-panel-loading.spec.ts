/**
 * E2E Test: Panel Loading
 *
 * Uses hass-taste-test for ephemeral HA with pre-authenticated URLs
 * The panel is loaded directly as a module (not via Lovelace)
 *
 * NO manual login - hass.link() provides authenticated access automatically
 */

import { test, expect, Page } from '@playwright/test';
import { getHassInstance } from './test-helpers';

const VEHICLE_ID = 'Coche2';

test.describe('EV Trip Planner Panel Loading', () => {
  let hassUrl: string;

  test.beforeAll(async () => {
    // Initialize hass-taste-test
    const hass = await getHassInstance();
    hassUrl = hass.link;
    console.log('[Test] Ephemeral HA URL:', hassUrl);
  });

  /**
   * Navigate to panel by directly loading the module and creating the element
   * This bypasses the Lovelace/Dashboard approach which doesn't work for standalone panels
   */
  async function loadPanelDirectly(page: Page): Promise<void> {
    // Navigate to the hass-taste-test URL first (authenticated)
    const baseUrl = hassUrl;
    console.log('[Test] Navigating to base URL:', baseUrl);
    await page.goto(baseUrl, {
      waitUntil: 'networkidle',
      timeout: 60000
    });

    // Inject the panel.js module which will register the custom element
    // The panel.js is served at /local/panel.js via the www directory copy
    await page.addScriptTag({
      url: `${baseUrl}/local/panel.js`,
      type: 'module'
    });

    // Wait for the custom element to be defined
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Create the custom element and append to body
    await page.evaluate(() => {
      const panel = document.createElement('ev-trip-planner-panel');
      panel.setAttribute('vehicle-id', 'Coche2');
      document.body.appendChild(panel);
    });

    // Wait for the panel to be visible
    await page.waitForSelector('ev-trip-planner-panel', { state: 'visible', timeout: 15000 });
  }

  test('should load panel directly as custom element', async ({ page }) => {
    await loadPanelDirectly(page);

    // Verify the custom element is present and visible
    const panel = page.locator('ev-trip-planner-panel');
    await expect(panel).toBeVisible({ timeout: 15000 });
  });

  test('should display vehicle name in panel header', async ({ page }) => {
    await loadPanelDirectly(page);

    // Verify panel header is visible by penetrating Shadow DOM
    const header = page.locator('ev-trip-planner-panel >> .panel-header');
    await expect(header).toBeVisible({ timeout: 10000 });
    const headerText = await header.textContent();
    expect(headerText).toContain(VEHICLE_ID);
  });

  test('should show sensors section after panel loads', async ({ page }) => {
    await loadPanelDirectly(page);

    // Verify sensors section is visible
    const sensorsSection = page.locator('ev-trip-planner-panel >> .sensors-section');
    await expect(sensorsSection).toBeVisible({ timeout: 15000 });
  });

  test('should show trips section after panel loads', async ({ page }) => {
    await loadPanelDirectly(page);

    // Verify trips section is visible
    const tripsSection = page.locator('ev-trip-planner-panel >> .trips-section');
    await expect(tripsSection).toBeVisible({ timeout: 15000 });
  });
});
