/**
 * Auth Setup Script
 *
 * Runs the Config Flow UI end-to-end to authenticate and save storageState.
 * This script is invoked by global.setup.ts AFTER the ephemeral HA server starts.
 *
 * Uses Playwright programmatically (not as a test) to:
 * 1. Launch a browser
 * 2. Navigate to HA
 * 3. Run Config Flow for EV Trip Planner
 * 4. Save storageState to playwright/.auth/user.json
 */

import { chromium } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const rootDir = process.cwd();
const authDir = path.join(rootDir, 'playwright', '.auth');
const serverInfoPath = path.join(authDir, 'server-info.json');
const authFile = path.join(authDir, 'user.json');

export async function runAuthSetup(): Promise<void> {
  // Read server info
  if (!fs.existsSync(serverInfoPath)) {
    throw new Error(`server-info.json not found at ${serverInfoPath}. global.setup.ts must run first.`);
  }
  const serverInfo = JSON.parse(fs.readFileSync(serverInfoPath, 'utf-8'));

  console.log('[AuthSetup] Starting Config Flow authentication...');

  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext();
  const page = await context.newPage();

  try {
    await page.goto(serverInfo.link);

    // Wait for the URL to leave the auth callback and show the main UI
    console.log('[AuthSetup] Waiting for auth callback to complete...');
    await page.waitForURL((url) => !url.toString().includes('auth_callback'), { timeout: 30000 });

    // Wait for the sidebar to be visible
    console.log('[AuthSetup] Waiting for sidebar to load...');
    await page.waitForSelector('home-assistant-main', { state: 'visible', timeout: 30000 });

    // Wait a bit for the page to stabilize
    await page.waitForLoadState('networkidle');

    // Debug: Check current URL
    const currentUrl = page.url();
    console.log('[AuthSetup] Current URL after callback:', currentUrl);

    // Take a snapshot of the page to understand what's there
    const snapshot = await page.evaluate(() => {
      const body = document.body ? document.body.innerHTML.substring(0, 2000) : 'no body';
      const haMain = document.querySelector('home-assistant-main');
      const haSidebar = document.querySelector('ha-sidebar');
      return {
        url: window.location.href,
        bodyLength: document.body ? document.body.innerHTML.length : 0,
        hasHaMain: !!haMain,
        hasHaSidebar: !!haSidebar,
        haSidebarHTML: haSidebar ? haSidebar.innerHTML.substring(0, 500) : 'none',
        allLinks: Array.from(document.querySelectorAll('a')).slice(0, 10).map(a => ({
          text: a.textContent?.trim().substring(0, 50),
          href: a.getAttribute('href')
        }))
      };
    });
    console.log('[AuthSetup] Page snapshot:', JSON.stringify(snapshot, null, 2));

    // Step 1: Navigate directly to integrations page
    console.log('[AuthSetup] Step 1: Navigate to integrations...');
    await page.goto(serverInfo.link + '/config/integrations');
    await page.waitForURL(/\/config\/integrations/, { timeout: 30000 });
    await page.waitForURL(/\/config\/integrations/);
    await page.getByRole('button', { name: 'Add Integration' }).click();

    // Step 2: Search and select "EV Trip Planner"
    console.log('[AuthSetup] Step 2: Select EV Trip Planner...');
    await page.getByPlaceholder('Search...').fill('EV Trip Planner');
    await page.getByRole('option', { name: 'EV Trip Planner' }).click();

    // Step 3: Config Flow step 1 — vehicle_name
    console.log('[AuthSetup] Step 3: Fill vehicle name...');
    await page.waitForSelector('input[name="vehicle_name"]', { timeout: 10000 });
    await page.getByLabel(/vehicle name/i).fill('TestVehicle');

    // Submit step 1 → step 2 (sensors — all defaults, submit immediately)
    await page.getByRole('button', { name: 'Submit' }).click();
    await page.waitForTimeout(500);

    // Step 4: Config Flow step 2 (sensors) — submit with defaults
    console.log('[AuthSetup] Step 4: Sensors (defaults)...');
    await page.getByRole('button', { name: 'Submit' }).click();
    await page.waitForTimeout(500);

    // Step 5: Config Flow step 3 (EMHASS) — submit with defaults
    console.log('[AuthSetup] Step 5: EMHASS (defaults)...');
    await page.getByRole('button', { name: 'Submit' }).click();
    await page.waitForTimeout(500);

    // Step 6: Config Flow step 4 (presence) — charging_sensor auto-selected
    console.log('[AuthSetup] Step 6: Presence (defaults)...');
    await page.getByRole('button', { name: 'Submit' }).click();
    await page.waitForTimeout(500);

    // Step 7: Config Flow step 5 (notifications) — submit
    console.log('[AuthSetup] Step 7: Notifications (submit)...');
    await page.getByRole('button', { name: 'Submit' }).click();
    await page.waitForURL(/\/config\/integrations/, { timeout: 15000 });

    // Verify panel appears in sidebar
    console.log('[AuthSetup] Verifying EV Trip Planner in sidebar...');
    await page.waitForSelector('a:has-text("EV Trip Planner")', { timeout: 10000 });

    // Save storage state
    console.log('[AuthSetup] Saving storageState to:', authFile);
    await context.storageState({ path: authFile });

    console.log('[AuthSetup] Config Flow completed successfully!');
  } finally {
    await browser.close();
  }
}

// Note: This module is invoked from global.setup.ts via runAuthSetup()
// The standalone script capability was removed to avoid ESM/CJS conflicts
