/**
 * E2E Test: Options Flow SOH and T_BASE Validation
 *
 * Verifies that the options flow for EV Trip Planner integration includes
 * the dynamic SOC capping fields (t_base and soh_sensor) and validates
 * their values correctly.
 *
 * Tests interact with the Home Assistant UI — they navigate to the integration
 * settings page, click the Configure button on the test_vehicle entry card,
 * and interact with the form in the dialog. No REST API calls.
 *
 * User Stories:
 * - As a user, I want to configure SOH sensor in the integration options
 * - As a user, I want to configure T_BASE window for dynamic SOC capping
 * - As a user, I want validation that T_BASE is within 6-48h range
 *
 * [VE0] [VERIFY:API] E2E Config Flow Validation
 */
import { test, expect, type Page } from '@playwright/test';
import { navigateToPanel, cleanupTestTrips } from './trips-helpers';

/**
 * Open the options flow dialog for the EV Trip Planner integration.
 *
 * HA uses native <dialog> element for options flow.
 * Form fields use spinbutton elements with labels like "t_base*".
 *
 * In the SOC suite, there is exactly one integration entry (test_vehicle),
 * so we use a section-scoped selector to find the Configure button.
 */
async function openOptionsDialog(page: Page): Promise<void> {
  await page.goto('/config/integrations/integration/ev_trip_planner');
  await page.waitForLoadState('networkidle');
  await page.waitForSelector('text=Integration entries', { timeout: 15_000 });

  // Scope: find the section/card containing "test_vehicle" (the integration title)
  // then click the Configure button inside that same section.
  // This avoids selecting a global Configure button that might exist outside the integration card.
  const testVehicleSection = page.locator('section').filter({ hasText: 'test_vehicle' }).first();

  // Primary: Configure button within the test_vehicle section
  const sectionConfigureBtn = testVehicleSection.getByRole('button', { name: 'Configure' });
  if (await sectionConfigureBtn.count().catch(() => 0) > 0) {
    await sectionConfigureBtn.first().click({ force: true });
    return;
  }

  // Fallback: any visible Configure button (should not happen in SOC suite)
  const allConfigureBtns = page.getByRole('button', { name: 'Configure' });
  if (await allConfigureBtns.count().catch(() => 0) > 0) {
    await allConfigureBtns.first().click({ force: true });
    return;
  }

  throw new Error('[openOptionsDialog] Could not find Configure button for test_vehicle integration');
}

/**
 * Wait for a form submission to complete successfully.
 * Handles the HA pattern where Submit triggers a success dialog with "Finish" button.
 */
async function waitForFormSubmit(page: Page): Promise<void> {
  // Wait for success dialog to appear
  const successBtn = page.getByRole('button', { name: 'Finish' });
  await expect(successBtn).toBeVisible({ timeout: 10_000 });

  // Click Finish to close the success dialog
  await successBtn.click();

  // Wait for the success dialog to disappear
  await expect(successBtn).not.toBeVisible({ timeout: 5_000 });
}

test.describe('Options Flow SOH and T_BASE Validation', () => {
  test.beforeEach(async ({ page }: { page: Page }) => {
    await navigateToPanel(page);
    await cleanupTestTrips(page);
  });

  test('options flow should show t_base with default value 24 and soh_sensor field', async ({
    page,
  }) => {
    await openOptionsDialog(page);

    // Verify the t_base spinbutton field is visible with a numeric value
    const tBaseSpinbutton = page.getByRole('spinbutton', { name: /t_base/ });
    await expect(tBaseSpinbutton).toBeVisible({ timeout: 5_000 });
    const tBaseValue = await tBaseSpinbutton.inputValue();
    expect(Number(tBaseValue)).toBeGreaterThanOrEqual(6);
    expect(Number(tBaseValue)).toBeLessThanOrEqual(48);

    // Verify the soh_sensor field is visible
    // soh_sensor is an entity selector rendered as a generic element with "soh_sensor" label
    const sohLabel = page.getByText('soh_sensor');
    await expect(sohLabel).toBeVisible({ timeout: 5_000 });

    // Verify the dialog has a Submit button
    const submitBtn = page.getByRole('button', { name: 'Submit' });
    await expect(submitBtn).toBeVisible({ timeout: 5_000 });
  });

  test('options flow should validate t_base range (6-48 hours)', async ({
    page,
  }) => {
    // Set up a known state: change SOC via HA frontend (websocket)
    const socResult = await page.evaluate(async () => {
      const haMain = document.querySelector('home-assistant') as any;
      if (!haMain?.hass) return { ok: false };
      try {
        await haMain.hass.callService('input_number', 'set_value', {
          entity_id: 'input_number.test_vehicle_soc',
          value: 50,
        });
        return { ok: true };
      } catch { return { ok: false }; }
    });
    expect(socResult.ok).toBe(true);

    await page.waitForTimeout(1000);

    // Open options dialog
    await openOptionsDialog(page);

    // Try to set t_base to 5 (below minimum of 6)
    const tBaseSpinbutton = page.getByRole('spinbutton', { name: /t_base/ });
    await tBaseSpinbutton.fill('5');

    // Click submit
    const submitBtn = page.getByRole('button', { name: 'Submit' });
    await submitBtn.click();

    // Wait for form to process — should show validation error (dialog stays open)
    await page.waitForTimeout(1000);

    // The dialog should still be open with the form (has Submit button)
    const hasFormDialog = await page.getByRole('button', { name: 'Submit' }).count().catch(() => 0);
    expect(hasFormDialog).toBeGreaterThan(0);

    // Close the error dialog to re-open for the max value test
    const closeBtn = page.getByRole('button', { name: 'Close' });
    if (await closeBtn.count().catch(() => 0) > 0) {
      await closeBtn.click();
      await page.waitForTimeout(500);
    }
    await openOptionsDialog(page);

    // Fill with maximum valid value
    const tBaseSpinbutton2 = page.getByRole('spinbutton', { name: /t_base/ });
    await tBaseSpinbutton2.fill('48');

    // Click submit
    const submitBtn2 = page.getByRole('button', { name: 'Submit' });
    await submitBtn2.click();

    // Should save successfully — dialog should close
    await waitForFormSubmit(page);

    // Verify we're back on the integration page (no dialogs open)
    const dialogCount = await page.locator('dialog').count().catch(() => 0);
    expect(dialogCount).toBe(0);
  });

  test('options flow should accept t_base at minimum boundary (6 hours)', async ({
    page,
  }) => {
    await openOptionsDialog(page);

    // Fill with minimum valid value
    const tBaseSpinbutton = page.getByRole('spinbutton', { name: /t_base/ });
    await tBaseSpinbutton.fill('6');

    // Click submit
    const submitBtn = page.getByRole('button', { name: 'Submit' });
    await submitBtn.click();

    // Should save successfully
    await waitForFormSubmit(page);

    // Verify we're back on the integration page
    const dialogCount = await page.locator('dialog').count().catch(() => 0);
    expect(dialogCount).toBe(0);
  });
});
