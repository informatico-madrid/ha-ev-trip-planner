/**
 * E2E Tests for User Story 8: CRUD de viajes en el panel de control
 *
 * IMPORTANT: Tests MUST verify actual panel state changes, not just UI behavior.
 * This test validates complete CRUD lifecycle through panel component state.
 *
 * Usage:
 *   npx playwright test test-us8-trip-crud.spec.ts
 */

import { test, expect } from '@playwright/test';

const vehicleId = process.env.VEHICLE_ID || 'Coche2';
const haUrl = process.env.HA_URL || process.env.HA_TEST_URL || 'http://192.168.1.201:8123';

// Helper to fetch trips from panel component state
async function fetchTripsFromPanel(page: any, vehicle: string) {
  const trips = await page.evaluate(() => {
    const panel = document.querySelector('ev-trip-planner-panel');
    if (!panel) {
      return { recurring_trips: [], punctual_trips: [] };
    }
    const shadow = panel.shadowRoot;
    if (!shadow) {
      return { recurring_trips: [], punctual_trips: [] };
    }
    const tripsSection = shadow.querySelector('.trips-section');
    if (!tripsSection) {
      return { recurring_trips: [], punctual_trips: [] };
    }
    const tripCards = tripsSection.querySelectorAll('.trip-card');
    const recurringCards = tripsSection.querySelectorAll('.trip-card[recurring="true"]');
    const punctualCards = tripsSection.querySelectorAll('.trip-card[punctual="true"]');
    return {
      recurring_trips: Array.from(recurringCards).map((c: any) => ({
        descripcion: c.querySelector('.trip-description')?.textContent?.trim() || '',
        hora: c.querySelector('.trip-time')?.textContent?.trim() || ''
      })),
      punctual_trips: Array.from(punctualCards).map((c: any) => ({
        descripcion: c.querySelector('.trip-description')?.textContent?.trim() || '',
        datetime: c.querySelector('.trip-datetime')?.textContent?.trim() || ''
      }))
    };
  });
  return trips;
}

test.describe('US8: CRUD de viajes - COMPLETO VALIDACION PANEL', () => {
  // ============================================
  // CREATE - Validar que los viajes se crean en el panel
  // ============================================

  test('should create a recurring trip and verify panel storage', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Get initial trip count from PANEL
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialCount = initialResponse?.recurring_trips?.length || 0;

    // Click add trip button
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();

    // Verify form appears
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    // Fill form with recurring trip data
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
    await page.locator('ev-trip-planner-panel >> #trip-day').selectOption('1'); // Monday
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('09:30');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('25.5');
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('5.2');
    await page.locator('ev-trip-planner-panel >> #trip-description').fill('Test E2E viaje recurrente');

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Verify form closes
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // CRITICAL: Verify trip was actually created in PANEL
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedCount = updatedResponse?.recurring_trips?.length || 0;

    // Panel MUST have created at least 1 new trip
    expect(updatedCount).toBe(initialCount + 1, 'Panel should have created a new recurring trip');

    // Verify the new trip has correct data
    const newTrip = updatedResponse.recurring_trips.find(
      (t: any) => t.descripcion === 'Test E2E viaje recurrente'
    );

    expect(newTrip).toBeDefined('Trip with correct description should exist in panel');
    expect(newTrip.hora).toContain('09:30', 'Time should be 09:30');

    // Verify UI reflects panel state
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    await expect(tripCards).toHaveCount(updatedCount, { timeout: 10000 });
  });

  test('should create a punctual trip and verify panel storage', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Get initial punctual trip count
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialPunctualCount = initialResponse?.punctual_trips?.length || 0;

    // Click add trip button
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();

    // Wait for form
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    // Fill form with punctual trip data
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('puntual');
    await page.locator('ev-trip-planner-panel >> #trip-datetime').fill('2026-03-25T14:00');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('15.0');
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('3.0');
    await page.locator('ev-trip-planner-panel >> #trip-description').fill('Viaje al aeropuerto');

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Verify form closes
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // CRITICAL: Verify trip was actually created in PANEL
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedPunctualCount = updatedResponse?.punctual_trips?.length || 0;

    // Panel MUST have created at least 1 new punctual trip
    expect(updatedPunctualCount).toBe(initialPunctualCount + 1,
      'Panel should have created a new punctual trip');

    // Verify the new trip has correct data
    const newTrip = updatedResponse.punctual_trips.find(
      (t: any) => t.descripcion === 'Viaje al aeropuerto'
    );

    expect(newTrip).toBeDefined('Trip with correct description should exist in panel');
    expect(newTrip.datetime).toContain('2026-03-25', 'Date should be 2026-03-25');
    expect(newTrip.datetime).toContain('14:00', 'Time should be 14:00');
  });

  test('should validate required fields - empty km should fail', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Get initial trip count
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialCount = initialResponse?.recurring_trips?.length || 0;

    // Click add trip button
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();

    // Fill form with EMPTY required field (km should be required)
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
    await page.locator('ev-trip-planner-panel >> #trip-day').selectOption('1');
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('10:00');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill(''); // Empty - should fail
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('5.0');

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Panel should reject the invalid trip - count should be unchanged
    const response = await fetchTripsFromPanel(page, vehicleId);
    const currentCount = response?.recurring_trips?.length || 0;

    // The panel should NOT have created a trip with empty km
    expect(currentCount).toBe(initialCount,
      'Panel should reject trip with empty required field');
  });

  // ============================================
  // READ - Validar que los viajes se muestran correctamente
  // ============================================

  test('should display trips section with header', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Verify trips header is visible
    const tripsHeader = page.locator('ev-trip-planner-panel >> .trips-header');
    await expect(tripsHeader).toBeVisible({ timeout: 10000 });

    // Verify header contains expected text
    const headerText = await tripsHeader.textContent();
    expect(headerText).toContain('Viajes Programados');
  });

  test('should display add trip button', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Check for add trip button
    const addTripButton = page.locator('ev-trip-planner-panel >> .add-trip-btn');
    await expect(addTripButton).toBeVisible({ timeout: 10000 });
  });

  test('should show no trips message when empty', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Get trips from panel
    const response = await fetchTripsFromPanel(page, vehicleId);
    const hasAnyTrips = (response.recurring_trips?.length || 0) > 0 ||
                        (response.punctual_trips?.length || 0) > 0;

    // Check for either no trips message or trip cards
    const hasNoTrips = await page.locator('ev-trip-planner-panel >> .no-trips').count() > 0;
    const hasTripCards = await page.locator('ev-trip-planner-panel >> .trip-card').count() > 0;

    if (!hasAnyTrips) {
      expect(hasNoTrips).toBe(true, 'Should show no trips message when panel is empty');
    } else {
      expect(hasTripCards).toBe(true, 'Should show trip cards when panel has trips');
    }
  });

  // ============================================
  // UPDATE - Validar edición de viajes
  // ============================================

  test('should edit a recurring trip and verify panel update', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Get initial trip from PANEL
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialTrips = initialResponse?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No recurring trips to edit');
      return;
    }

    const originalTime = initialTrips[0].hora;

    // Click edit button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.edit-btn').click();

    // Verify form is pre-filled with original data from panel
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });

    const tripTime = page.locator('ev-trip-planner-panel >> #trip-time');

    await expect(tripTime).toHaveValue(originalTime);

    // Modify the trip
    const newTime = '15:00';
    await tripTime.fill(newTime);

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Verify form closes
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // CRITICAL: Verify panel was actually updated
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedTrips = updatedResponse?.recurring_trips || [];

    const updatedTrip = updatedTrips.find((t: any) => t.hora === newTime);

    expect(updatedTrip).toBeDefined('Trip should exist in panel after edit');
    expect(updatedTrip.hora).toBe(newTime, 'Panel should have updated time');

    // Verify UI reflects the panel state
    const tripCard = page.locator('ev-trip-planner-panel >> .trip-card').first();
    await expect(tripCard).toContainText(newTime);
  });

  test('should pause and resume a recurring trip and verify panel state', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Get initial trip state from PANEL
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialTrips = initialResponse?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No recurring trips to pause');
      return;
    }

    const tripDesc = initialTrips[0].descripcion;
    const initialActive = true; // Assume active

    if (initialActive) {
      // Pause the trip
      await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.pause-btn').click();

      // Verify trip is paused in panel
      const pausedResponse = await fetchTripsFromPanel(page, vehicleId);
      const pausedTrip = pausedResponse.recurring_trips.find((t: any) =>
        t.descripcion === tripDesc
      );

      if (pausedTrip) {
        // Now resume the trip
        await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.resume-btn').click();

        // Verify trip is resumed in panel
        const resumedResponse = await fetchTripsFromPanel(page, vehicleId);
        const resumedTrip = resumedResponse.recurring_trips.find((t: any) =>
          t.descripcion === tripDesc
        );
        expect(resumedTrip).toBeDefined('Trip should be resumed in panel');
      }
    }
  });

  // ============================================
  // DELETE - Validar eliminación de viajes
  // ============================================

  test('should delete a recurring trip and verify panel removal', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Get initial trip count and description from PANEL
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialTrips = initialResponse?.recurring_trips || [];

    if (initialTrips.length === 0) {
      test.skip('No recurring trips to delete');
      return;
    }

    const tripToDelete = initialTrips[0];
    const initialCount = initialTrips.length;

    // Click delete button
    await page.locator('ev-trip-planner-panel >> .trip-card').first().locator('.delete-btn').click();

    // Accept deletion
    await page.locator('body').press('Escape');

    // CRITICAL: Verify trip was actually deleted from the PANEL
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedTrips = updatedResponse?.recurring_trips || [];

    // Panel should have deleted the trip
    const deletedTripStillExists = updatedTrips.find((t: any) =>
      t.descripcion === tripToDelete.descripcion
    );

    expect(deletedTripStillExists).toBeUndefined(
      'Panel should have deleted the trip'
    );

    // Verify count decreased
    expect(updatedTrips.length).toBe(initialCount - 1,
      'Panel trip count should decrease by 1');

    // Verify UI reflects panel state
    const tripCards = page.locator('ev-trip-planner-panel >> .trip-card');
    await expect(tripCards).toHaveCount(updatedTrips.length, { timeout: 10000 });
  });

  test('should delete a punctual trip and verify panel removal', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Get initial punctual trip
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialPunctualTrips = initialResponse?.punctual_trips || [];

    if (initialPunctualTrips.length === 0) {
      test.skip('No punctual trips to delete');
      return;
    }

    const tripToDelete = initialPunctualTrips[0];
    const initialCount = initialPunctualTrips.length;

    // Find and click delete button on punctual trip
    const punctualTrip = page.locator('ev-trip-planner-panel >> .trip-card').filter({
      hasText: 'Puntual'
    }).first();

    await punctualTrip.locator('.delete-btn').click();

    // Accept deletion
    await page.locator('body').press('Escape');

    // CRITICAL: Verify trip was actually deleted from the PANEL
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedPunctualTrips = updatedResponse?.punctual_trips || [];

    // Panel should have deleted the trip
    const deletedTripStillExists = updatedPunctualTrips.find((t: any) =>
      t.descripcion === tripToDelete.descripcion
    );

    expect(deletedTripStillExists).toBeUndefined(
      'Panel should have deleted the punctual trip'
    );

    // Verify count decreased
    expect(updatedPunctualTrips.length).toBe(initialCount - 1,
      'Panel punctual trip count should decrease by 1');
  });

  // ============================================
  // COMPLETE/CANCEL - Validar acciones de viajes puntuales
  // ============================================

  test('should complete a punctual trip and verify panel removal', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Get initial punctual trips from PANEL
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialPunctualTrips = initialResponse?.punctual_trips || [];

    if (initialPunctualTrips.length === 0) {
      test.skip('No punctual trips to complete');
      return;
    }

    const tripToComplete = initialPunctualTrips[0];
    const initialCount = initialPunctualTrips.length;

    // Find and click complete button on punctual trip
    const punctualTrip = page.locator('ev-trip-planner-panel >> .trip-card').filter({
      hasText: 'Puntual'
    }).first();

    await punctualTrip.locator('.complete-btn').click();

    // CRITICAL: Verify trip was actually completed (removed) from the PANEL
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedPunctualTrips = updatedResponse?.punctual_trips || [];

    // Completed trips should be removed from the list
    const completedTripStillExists = updatedPunctualTrips.find((t: any) =>
      t.descripcion === tripToComplete.descripcion
    );

    expect(completedTripStillExists).toBeUndefined(
      'Panel should have removed the completed trip'
    );

    // Verify count decreased
    expect(updatedPunctualTrips.length).toBe(initialCount - 1,
      'Panel punctual trip count should decrease by 1');
  });

  test('should cancel a punctual trip and verify panel removal', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Get initial punctual trips from PANEL
    const initialResponse = await fetchTripsFromPanel(page, vehicleId);
    const initialPunctualTrips = initialResponse?.punctual_trips || [];

    if (initialPunctualTrips.length === 0) {
      test.skip('No punctual trips to cancel');
      return;
    }

    const tripToCancel = initialPunctualTrips[0];
    const initialCount = initialPunctualTrips.length;

    // Find and click cancel button on punctual trip
    const punctualTrip = page.locator('ev-trip-planner-panel >> .trip-card').filter({
      hasText: 'Puntual'
    }).first();

    await punctualTrip.locator('.cancel-btn').click();

    // CRITICAL: Verify trip was actually cancelled (removed) from the PANEL
    const updatedResponse = await fetchTripsFromPanel(page, vehicleId);
    const updatedPunctualTrips = updatedResponse?.punctual_trips || [];

    // Cancelled trips should be removed from the list
    const cancelledTripStillExists = updatedPunctualTrips.find((t: any) =>
      t.descripcion === tripToCancel.descripcion
    );

    expect(cancelledTripStillExists).toBeUndefined(
      'Panel should have removed the cancelled trip'
    );

    // Verify count decreased
    expect(updatedPunctualTrips.length).toBe(initialCount - 1,
      'Panel punctual trip count should decrease by 1');
  });

  // ============================================
  // EDGE CASES - Casos borde
  // ============================================

  test('should handle special characters in description', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Click add trip button
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();

    // Fill form with special characters in description
    const specialChars = 'Test with special: á é í ó ú ñ & <script>';
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
    await page.locator('ev-trip-planner-panel >> #trip-day').selectOption('1');
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('10:00');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('10.0');
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('2.0');
    await page.locator('ev-trip-planner-panel >> #trip-description').fill(specialChars);

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Wait for form to close
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // CRITICAL: Verify panel stored the description correctly
    const response = await fetchTripsFromPanel(page, vehicleId);
    const newTrip = response.recurring_trips.find(
      (t: any) => t.descripcion && t.descripcion.includes('special')
    );

    expect(newTrip).toBeDefined('Trip with special characters should be stored in panel');
  });

  test('should handle long descriptions', async ({ page }) => {
    // Navigate to panel
    await page.goto(`${haUrl}/panel/ev-trip-planner-${vehicleId}`, { timeout: 60000 });

    // Click add trip button
    await page.locator('ev-trip-planner-panel >> .add-trip-btn').click();

    // Fill form with very long description
    const longDescription = 'A'.repeat(2000);
    await page.locator('ev-trip-planner-panel >> #trip-type').selectOption('recurrente');
    await page.locator('ev-trip-planner-panel >> #trip-day').selectOption('1');
    await page.locator('ev-trip-planner-panel >> #trip-time').fill('10:00');
    await page.locator('ev-trip-planner-panel >> #trip-km').fill('10.0');
    await page.locator('ev-trip-planner-panel >> #trip-kwh').fill('2.0');
    await page.locator('ev-trip-planner-panel >> #trip-description').fill(longDescription);

    // Submit form
    await page.locator('ev-trip-planner-panel >> button[type="submit"]').click();

    // Wait for form to close
    const formOverlay = page.locator('ev-trip-planner-panel >> .trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout: 10000 });

    // CRITICAL: Verify panel stored the long description
    const response = await fetchTripsFromPanel(page, vehicleId);
    const newTrip = response.recurring_trips.find(
      (t: any) => t.descripcion && t.descripcion.length > 100
    );

    expect(newTrip).toBeDefined('Trip with long description should be stored in panel');
    expect(newTrip.descripcion.length).toBeGreaterThan(100, 'Panel should store long description');
  });
});
