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

    // Step 1: Integrations page — click "Add Integration"
    console.log('[AuthSetup] Step 1: Navigate to integrations...');
    await page.getByRole('link', { name: 'Integrations' }).click();
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

// Allow running as standalone script: npx ts-node tests/e2e/auth.setup.ts
if (require.main === module) {
  runAuthSetup()
    .then(() => { console.log('[AuthSetup] Done'); process.exit(0); })
    .catch(err => { console.error('[AuthSetup] Error:', err); process.exit(1); });
}
