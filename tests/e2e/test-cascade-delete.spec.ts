/**
 * E2E Test: Cascade Delete - Verify trips removed when integration is deleted
 *
 * Validates US-3: Cascade delete of trips when vehicle integration is removed
 * Uses auth.setup.ts for authentication
 *
 * User Story:
 * As an EV owner, I want all trips to be automatically deleted when I remove a vehicle
 * So that no orphaned trip data remains in Home Assistant storage
 *
 * Acceptance Criteria (AC-3.x):
 * - AC-3.1: Given a vehicle with trips exists in HA, when the user deletes the vehicle
 *           integration, then all trips for that vehicle are removed from TripManager storage
 * - AC-3.4: HA storage contains zero orphaned trip records after vehicle deletion
 *
 * Test Flow:
 * 1. Navigate to panel and create trips
 * 2. Delete the vehicle integration via HA UI
 * 3. Re-add the vehicle integration via Config Flow
 * 4. Verify trips are NOT present (cascade delete worked)
 *
 * Usage:
 *   npx playwright test test-cascade-delete.spec.ts
 */

import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const VEHICLE_ID = 'Coche2';
const SERVER_INFO_PATH = path.join(process.cwd(), 'playwright/.auth/server-info.json');

function getBaseUrl(): string {
  if (fs.existsSync(SERVER_INFO_PATH)) {
    const info = JSON.parse(fs.readFileSync(SERVER_INFO_PATH, 'utf-8'));
    return new URL(info.link || info.baseUrl || process.env.HA_BASE_URL!).origin;
  }
  throw new Error('Server info not found - run auth.setup.ts first');
}

async function navigateToPanel(page: any): Promise<void> {
  const baseUrl = getBaseUrl();

  console.log('[Test Setup] Navigating to Home Assistant dashboard...');
  await page.goto(baseUrl);

  // Wait for sidebar to be visible
  const sidebar = page.locator('ha-sidebar');
  await expect(sidebar).toBeVisible({ timeout: 15000 });

  // Click on vehicle option in sidebar
  const vehicleOption = sidebar.getByText(VEHICLE_ID).first();
  await vehicleOption.waitFor({ state: 'visible', timeout: 10000 });
  await vehicleOption.click();

  // Wait for panel to become active
  await page.waitForTimeout(2000);

  console.log('[Test Setup] Panel navigation complete');
}

async function createTrip(page: any, tripData: {
  type: string;
  day?: string;
  time: string;
  distance: string;
  energy: string;
  description?: string;
}): Promise<void> {
  // Click "Agregar Viaje" button
  const addButton = page.getByRole('button', { name: /Agregar Viaje/i });
  await expect(addButton).toBeVisible({ timeout: 10000 });
  await addButton.click();
  console.log('[Test] Trip modal opened');

  // Fill form based on trip type
  const typeCombobox = page.getByRole('combobox', { name: 'Tipo de Viaje' });
  await expect(typeCombobox).toBeVisible();
  await typeCombobox.selectOption(tripData.type);
  console.log(`[Test] Selected trip type: ${tripData.type}`);

  // Fill day if provided
  if (tripData.day) {
    const dayCombobox = page.getByRole('combobox', { name: 'Día de la Semana' });
    await expect(dayCombobox).toBeVisible();
    await dayCombobox.selectOption(tripData.day);
    console.log(`[Test] Selected day: ${tripData.day}`);
  }

  // Fill time
  const timeInput = page.getByRole('textbox', { name: 'Hora' });
  await expect(timeInput).toBeVisible();
  await timeInput.fill(tripData.time);
  console.log(`[Test] Filled time: ${tripData.time}`);

  // Fill distance
  const distanceInput = page.getByRole('spinbutton', { name: 'Distancia (km)' });
  await expect(distanceInput).toBeVisible();
  await distanceInput.fill(tripData.distance);
  console.log(`[Test] Filled distance: ${tripData.distance} km`);

  // Fill energy
  const energyInput = page.getByRole('spinbutton', { name: 'Energía Estimada (kWh)' });
  await expect(energyInput).toBeVisible();
  await energyInput.fill(tripData.energy);
  console.log(`[Test] Filled energy: ${tripData.energy} kWh`);

  // Fill description if provided
  if (tripData.description) {
    const descriptionInput = page.getByRole('textbox', { name: 'Descripción (opcional)' });
    await expect(descriptionInput).toBeVisible();
    await descriptionInput.fill(tripData.description);
    console.log(`[Test] Filled description: ${tripData.description}`);
  }

  // Submit form
  const createButton = page.locator('.trip-form-overlay').getByRole('button', { name: 'Crear Viaje' });
  await expect(createButton).toBeVisible({ timeout: 10000 });
  await createButton.click();
  console.log('[Test] Create button clicked');

  // Handle dialog
  const dialog = await page.waitForEvent('dialog', { timeout: 10000 });
  await dialog.accept();
  console.log('[Test] Dialog accepted');

  // Wait for modal to close
  await page.waitForSelector('[role="dialog"]', { state: 'detached', timeout: 10000 });
  console.log('[Test] Modal closed');
}

async function deleteIntegration(page: any, vehicleName: string): Promise<void> {
  const baseUrl = getBaseUrl();

  console.log('[Test] Navigating to integrations page...');
  await page.goto(`${baseUrl}/config/integrations`, {
    waitUntil: 'domcontentloaded',
    timeout: 30000,
  });

  // Wait for page to load
  await page.waitForLoadState('domcontentloaded');
  await page.waitForTimeout(2000);

  // Find the integration by vehicle name
  console.log(`[Test] Looking for integration: ${vehicleName}`);
  const integrationElement = page.locator(`text="${vehicleName}"`).first();
  await integrationElement.waitFor({ state: 'visible', timeout: 10000 });

  // Click on the integration to open its details
  await integrationElement.click();
  await page.waitForTimeout(2000);

  // Look for delete button - HA shows a delete option when viewing an integration
  // Try to find the delete button in the integration details
  const deleteButton = page.getByRole('button', { name: /Delete|Eliminar/i }).or(
    page.locator('ha-icon-button').filter({ has: page.locator('ha-svg-icon') }).last()
  );

  // If we can't find a direct delete button, try clicking the overflow menu or similar
  const moreOptionsBtn = page.locator('button[aria-label*="delete" i], button[aria-label*="remove" i], button[aria-label*="eliminar" i]').first();
  const hasMoreOptions = await moreOptionsBtn.isVisible({ timeout: 2000 }).catch(() => false);

  if (hasMoreOptions) {
    console.log('[Test] Found delete button via aria-label');
    await moreOptionsBtn.click();
    await page.waitForTimeout(1000);
  } else {
    // Alternative: look for three-dot menu or similar
    const overflowBtn = page.locator('ha-button-menu').or(page.locator('button[aria-label*="more"]'));
    const hasOverflow = await overflowBtn.isVisible({ timeout: 2000 }).catch(() => false);

    if (hasOverflow) {
      await overflowBtn.click();
      await page.waitForTimeout(1000);
      // Look for delete in the menu
      const menuDelete = page.getByRole('menuitem', { name: /Delete|Eliminar/i });
      if (await menuDelete.isVisible({ timeout: 2000 }).catch(() => false)) {
        await menuDelete.click();
      }
    }
  }

  // Wait for confirmation dialog
  await page.waitForTimeout(1000);

  // Check if there's a confirmation dialog to accept
  const confirmDialog = page.locator('[role="alertdialog"], [role="dialog"]').filter({ hasText: /delete|eliminar|confirm/i });
  if (await confirmDialog.isVisible({ timeout: 2000 }).catch(() => false)) {
    console.log('[Test] Found confirmation dialog, accepting...');
    const confirmButton = page.getByRole('button', { name: /Delete|Confirm|Eliminar|Confirmar/i });
    await confirmButton.click();
    await page.waitForTimeout(2000);
  }

  // Also try to handle any dialog that might appear
  try {
    const dialog = await page.waitForEvent('dialog', { timeout: 3000 });
    await dialog.accept();
    console.log('[Test] Dialog accepted');
  } catch {
    console.log('[Test] No dialog appeared or already handled');
  }

  // Wait for integration to be removed
  await page.waitForTimeout(3000);

  // Verify integration is no longer visible in the list
  const integrationStillVisible = await integrationElement.isVisible({ timeout: 5000 }).catch(() => false);
  if (!integrationStillVisible) {
    console.log('[Test] Integration successfully deleted');
  } else {
    console.log('[Test] Warning: Integration might still be visible');
  }
}

async function reAddIntegration(page: any, vehicleName: string): Promise<void> {
  const baseUrl = getBaseUrl();

  console.log('[Test] Navigating to integrations page to re-add...');
  await page.goto(`${baseUrl}/config/integrations/dashboard`, {
    waitUntil: 'domcontentloaded',
    timeout: 30000,
  });

  // Wait for sidebar to be visible
  await expect(page.locator('ha-sidebar, [role="navigation"]')).toBeVisible({ timeout: 15000 });

  // Click "Add integration"
  console.log('[Test] Clicking Add integration...');
  await page.getByRole('button', { name: /Add integration/i }).click();

  // Search for EV Trip Planner
  console.log('[Test] Searching for EV Trip Planner...');
  const searchBox = page.getByRole('textbox', { name: /Search for a brand name/i });
  await searchBox.waitFor({ state: 'visible', timeout: 10000 });
  await searchBox.fill('EV Trip Planner');

  // Wait for search results and use .first() - search results only show matching items
  await expect(page.getByText('EV Trip Planner').first()).toBeVisible({ timeout: 5000 });
  await page.locator('text="EV Trip Planner"').first().click();

  // Wait for dialog
  console.log('[Test] Waiting for dialog...');
  const dialogHeading = page.getByText('EV Trip Planner');
  await dialogHeading.waitFor({ state: 'visible', timeout: 15000 });

  // CI may have slower rendering
  await page.waitForTimeout(3000);

  // Fill vehicle name
  const vehicleNameField = page.locator('input[name="vehicle_name"]');
  await vehicleNameField.waitFor({ state: 'visible', timeout: 30000 });
  await vehicleNameField.click();
  await vehicleNameField.type(vehicleName, { delay: 50 });

  // Submit
  await page.getByRole('button', { name: 'Submit' }).click();
  await page.waitForTimeout(2000);

  // Fill sensors
  const numericInputs = page.locator('input[type="number"]');
  const count = await numericInputs.count();
  if (count >= 4) {
    await numericInputs.nth(0).click();
    await numericInputs.nth(0).type('75.0', { delay: 30 });
    await numericInputs.nth(1).click();
    await numericInputs.nth(1).type('11.0', { delay: 30 });
    await numericInputs.nth(2).click();
    await numericInputs.nth(2).type('0.17', { delay: 30 });
    await numericInputs.nth(3).click();
    await numericInputs.nth(3).type('15', { delay: 30 });
  }

  await page.getByRole('button', { name: 'Submit' }).click();
  await page.waitForTimeout(2000);

  // Skip EMHASS step
  await page.getByRole('button', { name: 'Submit' }).click();
  await page.waitForTimeout(2000);

  // Presence step - same robust handling as auth.setup.ts
  console.log('[Test] Submitting presence step...');

  // Check if there's a validation error BEFORE trying to submit
  const validationError = page.locator('text="Not all required fields are filled in"');
  const hasValidationError = await validationError
    .isVisible({ timeout: 2000 })
    .catch(() => false);

  if (hasValidationError) {
    console.log('[Test] Validation error detected before presence submit, clicking Submit...');
    await page.getByRole('button', { name: /Submit|Next/i }).click();
  }

  const presenceSubmit = page.getByRole('button', { name: /Submit|Next/i });
  await presenceSubmit.waitFor({ state: 'visible', timeout: 10000 });
  await presenceSubmit.click();

  // The presence form might need to be submitted twice
  await page.waitForTimeout(1000);
  const presenceFormRedisplayed = await page.getByRole('button', { name: /Submit|Next/i }).isVisible().catch(() => false);
  if (presenceFormRedisplayed) {
    console.log('[Test] Presence form redisplayed - submitting again...');
    await page.getByRole('button', { name: /Submit|Next/i }).click();
    await page.waitForTimeout(1000);
  }

  // Skip notifications step if visible
  await page.waitForTimeout(2000);
  const notifSubmit = page.getByRole('button', { name: /Submit|Next/i });
  const notifVisible = await notifSubmit.isVisible({ timeout: 3000 }).catch(() => false);
  if (notifVisible) {
    console.log('[Test] Submitting notifications form...');
    await notifSubmit.click();
    await page.waitForTimeout(1000);

    // Check if form redisplayed
    const notifRedisplayed = await page.getByRole('button', { name: /Submit|Next/i }).isVisible().catch(() => false);
    if (notifRedisplayed) {
      console.log('[Test] Notifications form redisplayed - submitting again...');
      await page.getByRole('button', { name: /Submit|Next/i }).click();
      await page.waitForTimeout(1000);
    }
  }

  console.log('[Test] Re-added integration');
}

test.describe('EV Trip Planner - Cascade Delete User Story', () => {
  test('should remove all trips when integration is deleted', async ({ page }) => {
    // Step 1: Navigate to panel and create trips
    console.log('\n=== Step 1: Create trips ===');
    await navigateToPanel(page);

    // Create first trip (recurring)
    await createTrip(page, {
      type: 'recurrente',
      day: '1',
      time: '08:00',
      distance: '25',
      energy: '4.25',
      description: 'Morning commute test trip',
    });
    console.log('[Test] Created recurring trip 1');

    // Create second trip (punctual)
    await createTrip(page, {
      type: 'puntual',
      time: '14:00',
      distance: '50',
      energy: '8.5',
      description: 'Afternoon errand test trip',
    });
    console.log('[Test] Created punctual trip 2');

    // Verify trips exist
    const tripCards = page.locator('.trip-card');
    const tripCountBeforeDelete = await tripCards.count();
    console.log(`[Test] Trips before delete: ${tripCountBeforeDelete}`);
    expect(tripCountBeforeDelete).toBeGreaterThanOrEqual(2);
    console.log('[Test] Verified: Trips created successfully');

    // Step 2: Delete the integration
    console.log('\n=== Step 2: Delete integration ===');
    await deleteIntegration(page, VEHICLE_ID);
    console.log('[Test] Integration deleted');

    // Step 3: Re-add the integration
    console.log('\n=== Step 3: Re-add integration ===');
    await reAddIntegration(page, VEHICLE_ID);
    console.log('[Test] Integration re-added');

    // Step 4: Navigate to panel and verify trips are GONE
    console.log('\n=== Step 4: Verify trips removed ===');
    await navigateToPanel(page);

    // Check trip count - should be ZERO or show empty state
    const tripCardsAfter = page.locator('.trip-card');
    const tripCountAfterDelete = await tripCardsAfter.count();
    console.log(`[Test] Trips after delete: ${tripCountAfterDelete}`);

    // The key assertion: trips should be completely removed (cascade delete worked)
    expect(tripCountAfterDelete).toBe(0);
    console.log('[Test] SUCCESS: All trips were removed after integration deletion');

    // Also verify empty state is shown
    const emptyState = page.locator('text=/no trips|no hay|vacio/i').or(
      page.locator('.empty-state, .no-trips')
    );
    const hasEmptyState = await emptyState.isVisible({ timeout: 2000 }).catch(() => false);
    console.log(`[Test] Empty state visible: ${hasEmptyState}`);
  });

  test('should show empty trip list for fresh integration', async ({ page }) => {
    // This test verifies that a fresh integration has no trips
    console.log('\n=== Verify fresh integration has empty trips ===');

    // Navigate to settings and delete the integration if it exists
    const baseUrl = getBaseUrl();
    await page.goto(`${baseUrl}/config/integrations`, {
      waitUntil: 'domcontentloaded',
      timeout: 30000,
    });
    await page.waitForTimeout(2000);

    // Check if integration exists and delete it
    const integrationElement = page.locator(`text="${VEHICLE_ID}"`).first();
    const exists = await integrationElement.isVisible({ timeout: 3000 }).catch(() => false);

    if (exists) {
      console.log('[Test] Integration exists, deleting first...');
      await deleteIntegration(page, VEHICLE_ID);
      await page.waitForTimeout(2000);
    }

    // Re-add integration
    await reAddIntegration(page, VEHICLE_ID);
    await page.waitForTimeout(2000);

    // Navigate to panel
    await navigateToPanel(page);

    // Should show empty state
    const tripCards = page.locator('.trip-card');
    const tripCount = await tripCards.count();
    console.log(`[Test] Fresh integration trip count: ${tripCount}`);

    // A fresh integration should have no trips
    expect(tripCount).toBe(0);
    console.log('[Test] SUCCESS: Fresh integration has no trips');
  });
});