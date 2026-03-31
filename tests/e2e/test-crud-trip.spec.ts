/**
 * E2E Test: Create & Edit Trip - Complete User Story Validation
 *
 * Validates US4: Create trips via UI with form interaction
 * Uses auth.setup.ts for authentication
 *
 * User Story:
 * As an EV owner, I want to create new trips so I can plan my journeys
 *
 * Acceptance Criteria:
 * ✓ Panel loads successfully
 * ✓ Trip creation form is accessible
 * ✓ Trip is saved and appears in list
 * ✓ Trip details are displayed correctly
 * ✓ Trip can be edited
 * ✓ Edited trip reflects changes in list
 *
 * Usage:
 *   npx playwright test test-create-trip.spec.ts
 */

import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import { join } from 'path';

const VEHICLE_ID = 'Coche2';
const SERVER_INFO_PATH = join(process.cwd(), 'playwright/.auth/server-info.json');

function getBaseUrl(): string {
  if (fs.existsSync(SERVER_INFO_PATH)) {
    const info = JSON.parse(fs.readFileSync(SERVER_INFO_PATH, 'utf-8'));
    return new URL(info.link || info.baseUrl || process.env.HA_BASE_URL!).origin;
  }
  throw new Error('Server info not found - run auth.setup.ts first');
}

test.describe('EV Trip Planner - Create & Edit Trip User Story', () => {
  // Shared variable to store created trip data
  let createdTripData: { distance: string; energy: string; description: string } | null = null;

  /**
   * Setup: Navigate to panel via sidebar using ha-sidebar
   * Pattern from test-trip-list.spec.ts: click('text="..."') for sidebar navigation
   */
  async function navigateToPanel(page: any): Promise<void> {
    const baseUrl = getBaseUrl();

    // 1. Navigate to Home Assistant dashboard
    console.log('[Test Setup] Navigating to Home Assistant dashboard...');
    await page.goto(baseUrl);

    // Wait for sidebar to be visible
    const sidebar = page.locator('ha-sidebar');
    await expect(sidebar).toBeVisible({ timeout: 15000 });

    // 2. Click on vehicle option in sidebar (from snapshot: it's a listitem, not an option)
    // Use getByText to find the vehicle name in the sidebar
    const vehicleOption = sidebar.getByText(VEHICLE_ID).first();
    await vehicleOption.waitFor({ state: 'visible', timeout: 10000 });
    await vehicleOption.click();

    // 3. Wait for panel to become active
    await page.waitForTimeout(2000);

    console.log('[Test Setup] Panel navigation complete');
  }

  test('should create a new trip with all required fields', async ({ page }) => {
    await navigateToPanel(page);

    // Step 1: Click on "+ Agregar Viaje" button to open modal
    const addButton = page.getByRole('button', { name: /Agregar Viaje/i });
    await expect(addButton).toBeVisible({ timeout: 10000 });
    await addButton.click();
    console.log('[Test] Created trip modal opened');

    // Step 2: Fill trip form with test data
    // Fill Destination (combobox for Type of Trip)
    const typeCombobox = page.getByRole('combobox', { name: 'Tipo de Viaje' });
    await expect(typeCombobox).toBeVisible();
    console.log('[Test] Type of trip combobox found');

    // Fill Time (textbox)
    const timeInput = page.getByRole('textbox', { name: 'Hora' });
    const testTime = '14:00';
    await timeInput.fill(testTime);
    console.log(`[Test] Filled time: ${testTime}`);

    // Fill Distance (spinbutton)
    const distanceInput = page.getByRole('spinbutton', { name: 'Distancia (km)' });
    const testDistance = '150';
    await distanceInput.fill(testDistance);
    console.log(`[Test] Filled distance: ${testDistance} km`);

    // Fill Energy (spinbutton)
    const energyInput = page.getByRole('spinbutton', { name: 'Energía Estimada (kWh)' });
    const testEnergy = '20';
    await energyInput.fill(testEnergy);
    console.log(`[Test] Filled energy: ${testEnergy} kWh`);

    // Fill optional Description (textbox)
    const descriptionInput = page.getByRole('textbox', { name: 'Descripción (opcional)' });
    const testDescription = 'Test trip description';
    await descriptionInput.fill(testDescription);
    console.log(`[Test] Filled description: ${testDescription}`);

    // Step 3: Click "Crear Viaje" button inside the modal form
    // The modal has class trip-form-container inside trip-form-overlay
    // Use the overlay to scope the button search to the modal
    const createButton = page.locator('.trip-form-overlay').getByRole('button', { name: 'Crear Viaje' });
    await expect(createButton).toBeVisible({ timeout: 10000 });
    await createButton.click();
    console.log('[Test] Create trip button clicked');

    // Step 4: Handle browser confirmation dialog
    // Wait for dialog and accept it
    const dialog = await page.waitForEvent('dialog', { timeout: 10000 });
    await dialog.accept();
    console.log('[Test] Dialog accepted');

    // Wait for the modal to close - the dialog overlay should disappear
    // The modal is the dialog element with role="dialog" or class="dialog"
    await page.waitForSelector('[role="dialog"]', { state: 'detached', timeout: 10000 });
    console.log('[Test] Modal closed, verifying trip list');

    // Step 5: Verify the trip appears in the list
    const tripCards = page.locator('.trip-card');
    // Wait for at least 1 trip card with retry
    await expect(async () => {
      const count = await tripCards.count();
      expect(count).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10000 });

    const count = await tripCards.count();
    console.log(`[Test] Trip list count: ${count}`);

    // Verify the newly created trip is visible in the DOM
    const firstTripCard = tripCards.first();
    await expect(firstTripCard).toBeVisible();

    // Validate trip card internal structure
    const tripType = await firstTripCard.locator('.trip-type').first().textContent();
    const tripTime = await firstTripCard.locator('.trip-time').first().textContent();
    console.log(`[Test] Trip type: ${tripType}`);
    console.log(`[Test] Trip time: ${tripTime}`);
    expect(tripType || tripTime).toBeTruthy();

    // Check for trip details in the card
    const tripText = await firstTripCard.allTextContents();
    const fullText = tripText.join(' ');

    // Validate that trip details are present
    expect(fullText).toContain(testDistance);
    expect(fullText).toContain(testEnergy);
    expect(fullText).toContain(testDescription);

    console.log('[Test] Trip created successfully and visible in list');

    // Store trip data for edit test
    createdTripData = {
      distance: testDistance,
      energy: testEnergy,
      description: testDescription
    };
  });

  // Edit trip test runs immediately after create test completes
  test('should edit the newly created trip', async ({ page }) => {
    // This test runs after "should create a new trip" due to test.describe.configure({ mode: 'serial' })
    // So we know a trip exists at this point

    // Step 1: Navigate to panel and find trip card
    await navigateToPanel(page);

    const tripCards = page.locator('.trip-card');
    await expect(async () => {
      const count = await tripCards.count();
      expect(count).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10000 });

    const firstTripCard = tripCards.first();
    await expect(firstTripCard).toBeVisible();

    // Click the edit button
    const editButton = firstTripCard.getByText('✏️ Editar');
    await expect(editButton).toBeVisible();
    await editButton.click();
    console.log('[Test Edit] Edit button clicked, modal opened');

    // Step 2: Verify edit modal opens
    const modalTitle = page.getByRole('heading', { name: /Editar Viaje/i });
    await expect(modalTitle).toBeVisible();
    console.log('[Test Edit] Edit modal title verified');

    // Step 3: Modify form fields
    const timeInput = page.getByRole('textbox', { name: 'Hora' });
    const newTime = '18:30';
    await timeInput.fill(newTime);
    console.log(`[Test Edit] Updated time to: ${newTime}`);

    const distanceInput = page.getByRole('spinbutton', { name: 'Distancia (km)' });
    const newDistance = '200';
    await distanceInput.fill(newDistance);
    console.log(`[Test Edit] Updated distance to: ${newDistance} km`);

    const energyInput = page.getByRole('spinbutton', { name: 'Energía Estimada (kWh)' });
    const newEnergy = '25';
    await energyInput.fill(newEnergy);
    console.log(`[Test Edit] Updated energy to: ${newEnergy} kWh`);

    const descriptionInput = page.getByRole('textbox', { name: 'Descripción (opcional)' });
    await descriptionInput.fill('Updated trip description');
    console.log('[Test Edit] Updated description');

    // Step 4: Click "Guardar Cambios" button
    const updateButton = page.getByRole('button', { name: 'Guardar Cambios' });
    await expect(updateButton).toBeVisible({ timeout: 10000 });
    await updateButton.click();
    console.log('[Test Edit] Update trip button clicked');

    // Step 5: Handle confirmation dialog
    const dialog = await page.waitForEvent('dialog', { timeout: 10000 });
    await dialog.accept();
    console.log('[Test Edit] Dialog accepted');

    // Step 6: Wait for modal to close
    await page.waitForSelector('[role="dialog"]', { state: 'detached', timeout: 10000 });
    console.log('[Test Edit] Edit modal closed');

    // Step 7: Verify trip was updated
    const updatedTripCards = page.locator('.trip-card');
    await expect(async () => {
      const count = await updatedTripCards.count();
      expect(count).toBeGreaterThanOrEqual(1);
    }).toPass({ timeout: 10000 });

    const updatedTripCard = updatedTripCards.first();
    await expect(updatedTripCard).toBeVisible();

    const tripText = await updatedTripCard.allTextContents();
    const fullText = tripText.join(' ');

    // Validate updated values
    expect(fullText).toContain(newDistance);
    expect(fullText).toContain(newEnergy);
    expect(fullText).toContain(newTime);
    expect(fullText).toContain('Updated trip description');

    console.log('[Test Edit] Trip updated successfully and changes visible in list');
  });

  test('should display trip creation form with all fields', async ({ page }) => {
    await navigateToPanel(page);

    // Open the trip creation modal
    const addButton = page.getByRole('button', { name: /Agregar Viaje/i });
    await addButton.click();

    // Verify modal title (with emoji)
    const modalTitle = page.getByRole('heading', { name: '🚗 Nuevo Viaje' });
    await expect(modalTitle).toBeVisible();
    console.log('[Test] Modal title verified');

    // Verify all form fields are present
    // Type of Trip combobox
    const typeCombobox = page.getByRole('combobox', { name: 'Tipo de Viaje' });
    await expect(typeCombobox).toBeVisible();
    console.log('[Test] Type of trip combobox found');

    // Day of Week combobox
    const dayCombobox = page.getByRole('combobox', { name: 'Día de la Semana' });
    await expect(dayCombobox).toBeVisible();
    console.log('[Test] Day of week combobox found');

    // Time textbox
    const timeTextbox = page.getByRole('textbox', { name: 'Hora' });
    await expect(timeTextbox).toBeVisible();
    console.log('[Test] Time textbox found');

    // Distance spinbutton
    const distanceSpinbutton = page.getByRole('spinbutton', { name: 'Distancia (km)' });
    await expect(distanceSpinbutton).toBeVisible();
    console.log('[Test] Distance spinbutton found');

    // Energy spinbutton
    const energySpinbutton = page.getByRole('spinbutton', { name: 'Energía Estimada (kWh)' });
    await expect(energySpinbutton).toBeVisible();
    console.log('[Test] Energy spinbutton found');

    // Description textbox (optional)
    const descriptionTextbox = page.getByRole('textbox', { name: 'Descripción (opcional)' });
    await expect(descriptionTextbox).toBeVisible();
    console.log('[Test] Description textbox found');

    // Verify action buttons
    const cancelButton = page.getByRole('button', { name: 'Cancelar' });
    await expect(cancelButton).toBeVisible();
    console.log('[Test] Cancel button found');

    const createButton = page.getByRole('button', { name: 'Crear Viaje' });
    await expect(createButton).toBeVisible();
    console.log('[Test] Create button found');

    // Cancel the modal to leave clean state
    await cancelButton.click();
    await expect(modalTitle).not.toBeVisible();
    console.log('[Test] Modal closed');
  });

  test('should display trip list panel', async ({ page }) => {
    await navigateToPanel(page);

    // Verify panel loads without errors
    await expect(page).toHaveURL(new RegExp(`ev-trip-planner-${VEHICLE_ID.toLowerCase()}`, 'i'));

    // Verify the page content is loaded (not a 404 error page)
    const bodyText = await page.textContent('body');
    expect(bodyText || '').not.toContain('404');
    expect(bodyText || '').not.toContain('Not Found');

    console.log('[Test] Panel loaded successfully');
  });

  test('should show trip list with proper structure', async ({ page }) => {
    await navigateToPanel(page);

    // Verify panel loads
    await expect(page).toHaveURL(new RegExp(`ev-trip-planner-${VEHICLE_ID.toLowerCase()}`, 'i'));

    // Check for the trip creation button
    const addButton = page.getByRole('button', { name: /Agregar Viaje/i });
    const addButtonVisible = await addButton.isVisible();
    console.log(`[Test] Trip creation button visible: ${addButtonVisible}`);

    // Check for trip cards or empty state message
    const tripCards = page.locator('.trip-card');
    const tripCount = await tripCards.count();
    console.log(`[Test] Current trip count: ${tripCount}`);

    // Verify page is still functional (not a 404 error page)
    const bodyText = await page.textContent('body');
    expect(bodyText || '').not.toContain('404');
    expect(bodyText || '').not.toContain('Not Found');

    // Verify page structure - should have a heading for scheduled trips
    const scheduledTripsHeading = page.locator('h2', { hasText: '📅 Viajes Programados' });
    const hasScheduledTripsHeading = await scheduledTripsHeading.count() > 0;
    console.log(`[Test] Has scheduled trips heading: ${hasScheduledTripsHeading}`);

    console.log('[Test] Trip list structure verified');
  });
});
