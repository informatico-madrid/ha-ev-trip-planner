/**
 * E2E Test: Trip List View and Empty State
 *
 * User Stories:
 * - As a user, I want to see the EV Trip Planner panel in the sidebar
 * - As a user, I want to see "No hay viajes programados" when no trips exist
 * - As a user, I want to see the panel header with vehicle information
 * - As a user, I want to see the "+ Agregar Viaje" button to add new trips
 * - As a user, I want to see trip type badges (Recurrente/Puntual) on trip cards
 * - As a user, I want to see trip details (km, kWh, time) on each trip card
 */
import { test, expect, type Page } from '@playwright/test';
import { navigateToPanel, createTestTrip, deleteTestTrip } from './trips-helpers';

test.describe('Trip List View', () => {
  test.beforeEach(async ({ page }: { page: Page }) => {
    await navigateToPanel(page);
  });

  test('should display the panel with correct header', async ({ page }: { page: Page }) => {
    // Verify the panel header contains the EV Trip Planner title
    await expect(page.getByText('EV Trip Planner')).toBeVisible();
  });

  test('should display "+ Agregar Viaje" button', async ({ page }: { page: Page }) => {
    // Verify the add trip button is always visible
    await expect(page.getByRole('button', { name: '+ Agregar Viaje' })).toBeVisible();
  });

  test('should display Viajes Programados section', async ({ page }: { page: Page }) => {
    // Verify the trips section header is visible
    await expect(page.getByText('Viajes Programados')).toBeVisible();
  });

  test('should display trip details on card after creation', async ({ page }: { page: Page }) => {
    // Create a trip and verify its details are displayed correctly
    const tripId = await createTestTrip(
      page,
      'puntual',
      '2026-05-01T10:00',
      100,
      30,
      'Detail View Test',
    );

    // Verify the trip card shows all expected information
    const tripCard = page.locator('.trip-card', { hasText: 'Detail View Test' }).last();
    await expect(tripCard).toBeVisible();

    // Verify trip type badge
    await expect(tripCard.getByText('Puntual')).toBeVisible();

    // Verify trip status
    await expect(tripCard.getByText('Activo')).toBeVisible();

    // Verify distance display (contains "100")
    await expect(tripCard.getByText('100')).toBeVisible();

    // Verify energy display (contains "30")
    await expect(tripCard.getByText('30')).toBeVisible();

    // Verify description
    await expect(tripCard.getByText('Detail View Test')).toBeVisible();

    // Verify action buttons are present
    await expect(tripCard.getByText('Editar')).toBeVisible();
    await expect(tripCard.getByText('Eliminar')).toBeVisible();

    // Clean up
    await deleteTestTrip(page, '2026-05-01T10:00-Detail View Test');
  });

  test('should display recurrente trip with day and time', async ({ page }: { page: Page }) => {
    // Create a recurrente trip and verify time display format
    const tripId = await createTestTrip(
      page,
      'recurrente',
      '2026-05-02T07:00',
      20,
      5,
      'Recurrente View Test',
      { day: '1', time: '07:00' },
    );

    const tripCard = page.locator('.trip-card', { hasText: 'Recurrente View Test' }).last();
    await expect(tripCard).toBeVisible();

    // Verify trip type badge shows "Recurrente"
    await expect(tripCard.getByText('Recurrente')).toBeVisible();

    // Verify recurring trip shows pause button (not complete/cancel)
    await expect(tripCard.getByText('Pausar')).toBeVisible();

    // Clean up
    await deleteTestTrip(page, '2026-05-02T07:00-Recurrente View Test');
  });

  test('should display puntual trip with complete and cancel buttons', async ({ page }: { page: Page }) => {
    // Create a puntual trip and verify it has the correct action buttons
    const tripId = await createTestTrip(
      page,
      'puntual',
      '2026-05-03T15:00',
      45,
      12,
      'Puntual Actions Test',
    );

    const tripCard = page.locator('.trip-card', { hasText: 'Puntual Actions Test' }).last();
    await expect(tripCard).toBeVisible();

    // Verify puntual trip has Complete and Cancel buttons
    await expect(tripCard.getByText('Completar')).toBeVisible();
    await expect(tripCard.locator('.cancel-btn')).toBeVisible();

    // Verify puntual trip does NOT have Pause button
    await expect(tripCard.getByText('Pausar')).toBeHidden();

    // Clean up
    await deleteTestTrip(page, '2026-05-03T15:00-Puntual Actions Test');
  });
});
