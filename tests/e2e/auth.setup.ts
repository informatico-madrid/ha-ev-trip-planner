import { test as setup, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const authFile = path.join(__dirname, '..', '..', 'playwright', '.auth', 'user.json');

// Read server info from global.setup.ts output
function getServerInfo() {
  const serverInfoPath = path.join(__dirname, '..', '..', 'playwright', '.auth', 'server-info.json');
  if (!fs.existsSync(serverInfoPath)) {
    throw new Error(`server-info.json not found at ${serverInfoPath}. Run global.setup first.`);
  }
  return JSON.parse(fs.readFileSync(serverInfoPath, 'utf-8'));
}

setup('authenticate via Config Flow', async ({ page }) => {
  const { link } = getServerInfo();
  await page.goto(link);

  // Step 1: Integrations page — click "Add Integration"
  await page.getByRole('link', { name: 'Integrations' }).click();
  await page.waitForURL(/\/config\/integrations/);
  await page.getByRole('button', { name: 'Add Integration' }).click();

  // Step 2: Search and select "EV Trip Planner"
  await page.getByPlaceholder('Search...').fill('EV Trip Planner');
  await page.getByRole('option', { name: 'EV Trip Planner' }).click();

  // Step 3: Config Flow step 1 — vehicle_name
  await page.waitForSelector('input[name="vehicle_name"]', { timeout: 10000 });
  await page.getByLabel(/vehicle name/i).fill('TestVehicle');

  // Submit step 1 → step 2 (sensors — all defaults, submit immediately)
  await page.getByRole('button', { name: 'Submit' }).click();
  await page.waitForTimeout(500);

  // Step 4: Config Flow step 2 (sensors) — submit with defaults
  await page.getByRole('button', { name: 'Submit' }).click();
  await page.waitForTimeout(500);

  // Step 5: Config Flow step 3 (EMHASS) — submit with defaults
  await page.getByRole('button', { name: 'Submit' }).click();
  await page.waitForTimeout(500);

  // Step 6: Config Flow step 4 (presence) — charging_sensor auto-selected, submit
  await page.getByRole('button', { name: 'Submit' }).click();
  await page.waitForTimeout(500);

  // Step 7: Config Flow step 5 (notifications) — skip/submit
  await page.getByRole('button', { name: 'Submit' }).click();
  await page.waitForURL(/\/config\/integrations/);  // Confirms success

  // Verify panel appears in sidebar
  await page.waitForSelector('a:has-text("EV Trip Planner")', { timeout: 10000 });

  // Save storage state
  await page.context().storageState({ path: authFile });
  console.log('[auth.setup] storageState saved to', authFile);
});
