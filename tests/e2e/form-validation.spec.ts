/**
 * E2E Test: Form Validation
 *
 * User Stories:
 * - As a user, I want to see the correct form fields for each trip type
 * - As a user, when I select "recurrente", I should see day and time fields
 * - As a user, when I select "puntual", I should see datetime field
 * - As a user, I want the form to close when I click "Cancelar"
 * - As a user, I want to switch between trip types and see the form update
 */
import { test, expect, type Page } from '@playwright/test';
import { navigateToPanel } from './trips-helpers';

test.describe('Form Validation', () => {
  test.beforeEach(async ({ page }: { page: Page }) => {
    await navigateToPanel(page);
  });

  test('should show recurrente form fields by default', async ({ page }: { page: Page }) => {
    // Open the trip creation form
    await page.getByRole('button', { name: '+ Agregar Viaje' }).click();

    // Default trip type should be "recurrente"
    const tripTypeSelect = page.locator('#trip-type');
    await expect(tripTypeSelect).toHaveValue('recurrente');

    // For recurrente: day selector and time input should be visible
    await expect(page.locator('#trip-day')).toBeVisible();
    await expect(page.locator('#trip-time')).toBeVisible();

    // For recurrente: datetime input should be hidden
    await expect(page.locator('#trip-datetime')).toBeHidden();

    // Common fields should be visible
    await expect(page.locator('#trip-km')).toBeVisible();
    await expect(page.locator('#trip-kwh')).toBeVisible();
    await expect(page.locator('#trip-description')).toBeVisible();

    // Buttons should be visible
    await expect(page.getByRole('button', { name: 'Crear Viaje' })).toBeVisible();
  });

  test('should show puntual form fields when switching to puntual', async ({ page }: { page: Page }) => {
    // Open the trip creation form
    await page.getByRole('button', { name: '+ Agregar Viaje' }).click();

    // Switch to puntual trip type
    await page.locator('#trip-type').selectOption('puntual');

    // For puntual: datetime input should be visible
    await expect(page.locator('#trip-datetime')).toBeVisible();

    // For puntual: day selector and time input should be hidden
    await expect(page.locator('#trip-day')).toBeHidden();
    await expect(page.locator('#trip-time')).toBeHidden();

    // Common fields should still be visible
    await expect(page.locator('#trip-km')).toBeVisible();
    await expect(page.locator('#trip-kwh')).toBeVisible();
    await expect(page.locator('#trip-description')).toBeVisible();
  });

  test('should switch form fields when changing trip type', async ({ page }: { page: Page }) => {
    // Open the trip creation form (defaults to recurrente)
    await page.getByRole('button', { name: '+ Agregar Viaje' }).click();

    // Verify initial state (recurrente)
    await expect(page.locator('#trip-day')).toBeVisible();
    await expect(page.locator('#trip-datetime')).toBeHidden();

    // Switch to puntual
    await page.locator('#trip-type').selectOption('puntual');
    await expect(page.locator('#trip-datetime')).toBeVisible();
    await expect(page.locator('#trip-day')).toBeHidden();

    // Switch back to recurrente
    await page.locator('#trip-type').selectOption('recurrente');
    await expect(page.locator('#trip-day')).toBeVisible();
    await expect(page.locator('#trip-datetime')).toBeHidden();
  });

  test('should close form when clicking Cancelar button', async ({ page }: { page: Page }) => {
    // Open the trip creation form
    await page.getByRole('button', { name: '+ Agregar Viaje' }).click();

    // Verify form is open (km field visible)
    await expect(page.locator('#trip-km')).toBeVisible();

    // Click "Cancelar" button (the form action button, not the trip action)
    await page.locator('.form-actions').getByText('Cancelar').click();

    // Verify form is closed (km field no longer visible)
    await expect(page.locator('#trip-km')).toBeHidden();
  });

  test('should have correct day options in day selector', async ({ page }: { page: Page }) => {
    // Open the form
    await page.getByRole('button', { name: '+ Agregar Viaje' }).click();

    // Verify day selector has all 7 days
    const daySelect = page.locator('#trip-day');

    // Check Domingo (0) through Sábado (6) exist as options
    const options = daySelect.locator('option');
    await expect(options).toHaveCount(7);

    // Verify first option is Domingo (value 0)
    await expect(options.first()).toHaveText('Domingo');

    // Verify Monday option exists
    await expect(daySelect.locator('option[value="1"]')).toHaveText('Lunes');
  });

  test('should have correct trip type options', async ({ page }: { page: Page }) => {
    // Open the form
    await page.getByRole('button', { name: '+ Agregar Viaje' }).click();

    // Verify trip type has two options
    const typeSelect = page.locator('#trip-type');
    const options = typeSelect.locator('option');
    await expect(options).toHaveCount(2);

    // Verify options contain expected text
    await expect(options.nth(0)).toContainText('Recurrente');
    await expect(options.nth(1)).toContainText('Puntual');
  });
});
