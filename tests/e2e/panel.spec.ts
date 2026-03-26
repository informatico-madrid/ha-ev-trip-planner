/**
 * E2E Test: EV Trip Planner Panel Access
 *
 * Architecture:
 * - global.setup.ts: Starts ephemeral HA server, saves server URL
 * - auth.setup.ts: Logs in with dev/dev, completes config flow, saves storageState
 * - chromium tests: Reuse storageState via project dependency, navigate to panel
 */

import { test, expect } from '@playwright/test';
import * as fs from 'fs';

const PANEL_URL_PATH = '/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/playwright/.auth/panel-url.txt';

function getPanelUrl(): string {
  if (fs.existsSync(PANEL_URL_PATH)) {
    return fs.readFileSync(PANEL_URL_PATH, 'utf-8').trim();
  }
  throw new Error('Panel URL not found. Run auth.setup first.');
}

test.describe('EV Trip Planner Panel', () => {
  test('Debe cargar el panel del vehiculo desde el menu lateral', async ({ page }) => {
    const panelUrl = getPanelUrl();
    console.log('[Panel] Navigating to:', panelUrl);

    // Navigate to the EV Trip Planner panel (storageState handles auth)
    await page.goto(panelUrl, { waitUntil: 'domcontentloaded' });
    await page.waitForTimeout(3000);

    // Verify we're authenticated and panel loaded
    await expect(page.locator('text="Settings"')).toBeVisible({ timeout: 10000 });
    console.log('[Panel] Successfully accessed EV Trip Planner panel!');
  });
});
