/**
 * E2E Test: Delete Trip - Complete User Story Validation
 *
 * Validates the complete user story for deleting trips via UI.
 * This test creates its own data in beforeEach to be fully isolated and deterministic.
 *
 * User Story:
 * As an EV owner, I want to delete trips so I can remove journeys I no longer need
 *
 * Architecture:
 * - Uses sidebar navigation pattern (ha-sidebar) - NEVER hardcode URLs
 * - Creates trip data in beforeEach via UI interaction
 * - Tests are deterministic - no conditional skipping
 */

import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import { join } from 'path';

const SERVER_INFO_PATH = join(process.cwd(), 'playwright/.auth/server-info.json');

function getBaseUrl(): string {
  if (fs.existsSync(SERVER_INFO_PATH)) {
    const info = JSON.parse(fs.readFileSync(SERVER_INFO_PATH, 'utf-8'));
    return new URL(info.link || info.baseUrl || process.env.HA_BASE_URL!).origin;
  }
  throw new Error('Server info not found - run auth.setup.ts first');
}

test.describe('EV Trip Planner - Delete Trip', () => {

  test.beforeEach(async ({ page }) => {
    const baseUrl = getBaseUrl();

    // 1. NAVEGACIÓN ESTRICTA POR MENÚ LATERAL (ha-sidebar)
    console.log('[Test Setup] Navigating to Home Assistant dashboard via sidebar...');
    await page.goto(baseUrl);

    // Wait for sidebar to be visible
    const sidebar = page.locator('ha-sidebar');
    await expect(sidebar).toBeVisible({ timeout: 15000 });

    // Click on EV Trip Planner panel in sidebar
    const sidebarLink = sidebar.getByRole('link', { name: /EV Trip Planner|Mi Coche|Coche/i, exact: false }).first();
    await sidebarLink.waitFor({ state: 'visible', timeout: 10000 });
    await sidebarLink.click();

    // Wait for panel to load
    const panel = page.locator('ev-trip-planner-panel, ha-panel-ev_trip_planner').first();
    await expect(panel).toBeVisible({ timeout: 15000 });

    // 2. AISLAMIENTO DEL TEST: CREAR EL VIAJE DE PRUEBA VÍA UI
    console.log('[Test Setup] Creating test trip via UI...');

    // Click on "Add Trip" or "Crear Viaje" button
    const addButton = panel.getByRole('button', { name: /Add|Crear|Añadir|New/i }).first();
    await expect(addButton).toBeVisible({ timeout: 10000 });
    await addButton.click();

    // Fill trip destination
    const destinationInput = panel.getByRole('textbox', { name: /Destination|Destino|Destination/i }).first();
    await destinationInput.fill('Test Location');

    // Fill trip time
    const timeInput = panel.getByRole('textbox', { name: /Time|Hora|Time/i }).first();
    await timeInput.fill('10:00');

    // Fill distance
    const distanceInput = panel.getByRole('textbox', { name: /Distance|Distancia|Distance/i }).first();
    await distanceInput.fill('50');

    // Save the trip
    const saveButton = panel.getByRole('button', { name: /Save|Guardar|Save/i }).first();
    await expect(saveButton).toBeVisible({ timeout: 10000 });
    await saveButton.click();

    // 3. Esperar a que el viaje aparezca en la pantalla para confirmar que se creó
    const tripCards = panel.locator('.trip-card');
    await expect(tripCards.first()).toBeVisible({ timeout: 10000 });
    console.log('[Test Setup] Test trip created successfully');
  });

  test('Debe mostrar el dialogo de confirmacion y borrar el viaje exitosamente', async ({ page }) => {
    const baseUrl = getBaseUrl();
    const panel = page.locator('ev-trip-planner-panel, ha-panel-ev_trip_planner').first();
    const tripCards = panel.locator('.trip-card');

    // Get initial count - should be at least 1 (the trip we just created)
    const initialCount = await tripCards.count();
    expect(initialCount).toBeGreaterThan(0);

    // Click on the first trip card
    const targetCard = tripCards.first();
    await expect(targetCard).toBeVisible();
    await targetCard.click();

    console.log('[Test] Clicked trip card, looking for delete button...');

    // Find and click delete button on the trip card
    const deleteButton = targetCard.locator('button[aria-label*="delete"], button:has-text("Delete"), button:has-text("Eliminar"), button[aria-label*="borrar"]');
    await expect(deleteButton).toBeVisible({ timeout: 5000 });
    await deleteButton.click();

    // Wait for confirmation dialog
    console.log('[Test] Waiting for delete confirmation dialog...');
    const dialog = page.locator('ha-dialog, .delete-dialog').filter({ hasText: /Confirm|Delete|Are you sure|Estás seguro/i });
    await expect(dialog).toBeVisible({ timeout: 10000 });

    // Click confirm button
    const confirmButton = dialog.getByRole('button', { name: /Confirm|Aceptar|Confirmar|Delete/i }).first();
    await expect(confirmButton).toBeVisible();
    await confirmButton.click();

    // Wait for dialog to close
    await expect(dialog).toBeHidden({ timeout: 10000 });

    // Verify the trip count decreased by 1
    const finalCount = await tripCards.count();
    expect(finalCount).toBe(initialCount - 1);

    console.log('[Test] Trip deleted successfully');
  });

  test('Debe cancelar el borrado cuando se presiona cancelar', async ({ page }) => {
    const baseUrl = getBaseUrl();
    const panel = page.locator('ev-trip-planner-panel, ha-panel-ev_trip_planner').first();
    const tripCards = panel.locator('.trip-card');

    // Get initial count
    const initialCount = await tripCards.count();
    expect(initialCount).toBeGreaterThan(0);

    // Click on the first trip card
    const targetCard = tripCards.first();
    await targetCard.click();

    // Find and click delete button
    const deleteButton = targetCard.locator('button[aria-label*="delete"], button:has-text("Delete"), button:has-text("Eliminar"), button[aria-label*="borrar"]');
    await expect(deleteButton).toBeVisible({ timeout: 5000 });
    await deleteButton.click();

    // Wait for confirmation dialog
    const dialog = page.locator('ha-dialog, .delete-dialog').filter({ hasText: /Confirm|Delete|Are you sure|Estás seguro/i });
    await expect(dialog).toBeVisible({ timeout: 10000 });

    // Click cancel button
    const cancelButton = dialog.getByRole('button', { name: /Cancel|Cancelar|Cancel/i }).first();
    await expect(cancelButton).toBeVisible();
    await cancelButton.click();

    // Wait for dialog to close
    await expect(dialog).toBeHidden({ timeout: 10000 });

    // Verify trip count did NOT change
    const finalCount = await tripCards.count();
    expect(finalCount).toBe(initialCount);

    console.log('[Test] Delete cancelled successfully');
  });

});
