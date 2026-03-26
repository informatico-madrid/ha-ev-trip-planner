/**
 * E2E Test: EV Trip Planner Panel Card Loading
 *
 * Uses hass-taste-test to automatically:
 * - Install and start a Home Assistant instance
 * - Add custom components
 * - Create a dashboard with the card
 * - Return authenticated URLs
 *
 * Usage:
 *   npx jest tests/e2e/card-loading.test.ts
 */

import { HomeAssistant, PlaywrightBrowser } from 'hass-taste-test';

let hass: HomeAssistant;

beforeAll(async () => {
  // Create a Home Assistant instance with Playwright browser integration
  hass = await HomeAssistant.create(undefined, {
    browser: new PlaywrightBrowser('chromium'),
    customComponents: ['custom_components'],
  });
}, 120000);

afterAll(async () => {
  await hass?.close();
});

describe('EV Trip Planner Panel', () => {
  test('should load the panel card in a dashboard', async () => {
    // Add the custom card resource to Lovelace
    await hass.addResource(
      'custom_components/ev_trip_planner/dashboard/ev-trip-planner-simple.js',
      'module'
    );

    // Create a dashboard with the panel card
    const dashboard = await hass.Dashboard([
      {
        type: 'custom:ev-trip-planner-panel',
        entity: 'sensor.coche2_battery',
      },
    ]);

    // Get the authenticated URL for debugging
    const dashboardUrl = await dashboard.link();
    console.log('Dashboard URL:', dashboardUrl);

    // Take a screenshot of the loaded panel
    const screenshot = await dashboard.cards[0].screenshot();
    expect(screenshot).toBeDefined();

    // Get the HTML to verify structure
    const html = await dashboard.cards[0].html();
    expect(html).toBeDefined();
    expect(html.length).toBeGreaterThan(0);
  });

  test('should handle missing entity gracefully', async () => {
    await hass.addResource(
      'custom_components/ev_trip_planner/dashboard/ev-trip-planner-simple.js',
      'module'
    );

    // Create dashboard with a non-existent entity to test error handling
    const dashboard = await hass.Dashboard([
      {
        type: 'custom:ev-trip-planner-panel',
        entity: 'sensor.nonexistent_entity',
      },
    ]);

    // Should still render (even if with error state)
    const screenshot = await dashboard.cards[0].screenshot();
    expect(screenshot).toBeDefined();
  });
});
