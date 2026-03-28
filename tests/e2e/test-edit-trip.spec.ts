/**
 * E2E Test: Edit Trip - Complete User Story Validation
 *
 * Validates the complete user story for editing trips via UI.
 * This test creates its own data in beforeEach to be fully isolated and deterministic.
 *
 * User Story:
 * As an EV owner, I want to edit my trips so I can update my journey plans
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

test.describe('EV Trip Planner - Edit Trip', () => {

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
    await destinationInput.fill('Original Location');

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

  test('should pre-fill form when editing existing trip', async ({ page }) => {
    const panel = page.locator('ev-trip-planner-panel, ha-panel-ev_trip_planner').first();
    const tripCards = panel.locator('.trip-card');

    // Get initial count - should be at least 1 (the trip we just created)
    const initialCount = await tripCards.count();
    expect(initialCount).toBeGreaterThan(0);

    // Click on the first trip card to edit
    const targetCard = tripCards.first();
    await expect(targetCard).toBeVisible();
    await targetCard.click();

    // Look for edit button
    const editButton = targetCard.locator('button[aria-label*="edit"], button:has-text("Edit"), button:has-text("Editar"), button[aria-label*="editar"]');
    await expect(editButton).toBeVisible({ timeout: 5000 });
    await editButton.click();

    // Wait for edit form to appear
    const editForm = panel.locator('.trip-form-overlay, .edit-form, ha-dialog:has-text(/Edit|Editar/i)').first();
    await expect(editForm).toBeVisible({ timeout: 10000 });

    // Verify form fields are populated with original values
    const destinationInput = editForm.getByRole('textbox', { name: /Destination|Destino/i }).first();
    const destinationValue = await destinationInput.inputValue();
    expect(destinationValue).toContain('Original Location');

    console.log('[Test] Edit form pre-filled correctly');
  });

  test('should update trip when form is submitted', async ({ page }) => {
    const panel = page.locator('ev-trip-planner-panel, ha-panel-ev_trip_planner').first();
    const tripCards = panel.locator('.trip-card');

    // Get initial count
    const initialCount = await tripCards.count();
    expect(initialCount).toBeGreaterThan(0);

    // Click on the first trip card
    const targetCard = tripCards.first();
    await targetCard.click();

    // Find and click edit button
    const editButton = targetCard.locator('button[aria-label*="edit"], button:has-text("Edit"), button:has-text("Editar")');
    await expect(editButton).toBeVisible({ timeout: 5000 });
    await editButton.click();

    // Wait for edit form to appear
    const editForm = panel.locator('.trip-form-overlay, .edit-form, ha-dialog:has-text(/Edit|Editar/i)').first();
    await expect(editForm).toBeVisible({ timeout: 10000 });

    // Update the trip destination
    const destinationInput = editForm.getByRole('textbox', { name: /Destination|Destino/i }).first();
    await destinationInput.fill('Updated Location');

    // Submit the form
    const saveButton = editForm.getByRole('button', { name: /Save|Guardar|Save/i }).first();
    await expect(saveButton).toBeVisible();
    await saveButton.click();

    // Wait for form to close
    await expect(editForm).toBeHidden({ timeout: 10000 });

    // Verify the trip was updated - check that the new destination appears
    const updatedTripCard = tripCards.first();
    const destinationText = await updatedTripCard.locator('.trip-destination, .trip-title, [class*="destination"], [class*="title"]').textContent();
    expect(destinationText || '').toContain('Updated Location');

    console.log('[Test] Trip updated successfully');
  });

  test('should cancel edit when cancel button is clicked', async ({ page }) => {
    const panel = page.locator('ev-trip-planner-panel, ha-panel-ev_trip_planner').first();
    const tripCards = panel.locator('.trip-card');

    // Get initial count
    const initialCount = await tripCards.count();
    expect(initialCount).toBeGreaterThan(0);

    // Click on the first trip card
    const targetCard = tripCards.first();
    await targetCard.click();

    // Find and click edit button
    const editButton = targetCard.locator('button[aria-label*="edit"], button:has-text("Edit"), button:has-text("Editar")');
    await expect(editButton).toBeVisible({ timeout: 5000 });
    await editButton.click();

    // Wait for edit form to appear
    const editForm = panel.locator('.trip-form-overlay, .edit-form, ha-dialog:has-text(/Edit|Editar/i)').first();
    await expect(editForm).toBeVisible({ timeout: 10000 });

    // Update the trip destination
    const destinationInput = editForm.getByRole('textbox', { name: /Destination|Destino/i }).first();
    await destinationInput.fill('Temp Update');

    // Click cancel button
    const cancelButton = editForm.getByRole('button', { name: /Cancel|Cancelar|Cancel/i }).first();
    await expect(cancelButton).toBeVisible();
    await cancelButton.click();

    // Wait for form to close
    await expect(editForm).toBeHidden({ timeout: 10000 });

    // Verify trip count did NOT change
    const finalCount = await tripCards.count();
    expect(finalCount).toBe(initialCount);

    // Verify the original destination is still there (not updated)
    const originalTripCard = tripCards.first();
    const destinationText = await originalTripCard.locator('.trip-destination, .trip-title, [class*="destination"], [class*="title"]').textContent();
    expect(destinationText || '').toContain('Original Location');

    console.log('[Test] Edit cancelled successfully');
  });

});
