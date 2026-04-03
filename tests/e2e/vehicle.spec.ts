import { test, expect } from '@playwright/test';
import * as path from 'path';
import { ConfigFlowPage } from './pages/ConfigFlowPage';
import { EVTripPlannerPage } from './pages/EVTripPlannerPage';

const authFile = path.join(__dirname, '..', '..', 'playwright', '.auth', 'user.json');

test.describe('Vehicle Creation and Panel', () => {
  let configFlow: ConfigFlowPage;
  let panel: EVTripPlannerPage;
  let vehicleName: string;
  let vehicleId: string;

  test.beforeEach(async ({ page }) => {
    // Load auth state from auth.setup.ts
    await page.context().storageState({ path: authFile });

    configFlow = new ConfigFlowPage(page);
    panel = new EVTripPlannerPage(page);

    vehicleName = `TestVehicle${Date.now()}`;
    vehicleId = vehicleName.toLowerCase().replace(/\s+/g, '_');
  });

  test.afterEach(async ({ page }) => {
    // Remove integration via Config Flow "Delete" option
    await page.goto('/config/integrations');
    const integrationRow = page.locator(' hass-integration-card', { hasText: vehicleName });
    const row = integrationRow.first();
    if (await row.isVisible()) {
      await row.getByRole('button', { name: 'Delete' }).click();
      await page.getByRole('button', { name: 'Delete' }).click();  // Confirm
      await page.waitForTimeout(1000);
    }
  });

  test('US-1 + US-2: install EV Trip Planner and open panel', async ({ page }) => {
    // Navigate to HA
    await page.goto('/config/integrations');

    // Run Config Flow
    await configFlow.addIntegration('EV Trip Planner');
    await configFlow.fillVehicleName(vehicleName);
    await configFlow.submit();  // Step 1 → Step 2
    await configFlow.submit();  // Step 2 (sensors) → Step 3
    await configFlow.submit();  // Step 3 (EMHASS) → Step 4
    await configFlow.submit();  // Step 4 (presence) → Step 5
    await configFlow.submit();  // Step 5 (notifications) → complete

    // Verify panel appears in sidebar
    await configFlow.waitForPanelInSidebar();

    // Open panel
    await panel.openFromSidebar();
    await expect(panel.addTripBtn).toBeVisible();

    // Panel URL contains vehicle_id
    await expect(page).toHaveURL(/\/ev-trip-planner-/);
  });
});
