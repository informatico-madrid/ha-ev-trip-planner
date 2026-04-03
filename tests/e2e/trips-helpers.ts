import { type Page } from '@playwright/test';

/**
 * Navigates to the EV Trip Planner panel via sidebar navigation.
 * Uses the SPA entry point pattern: goto('/') -> waitForURL('/home') -> sidebar click -> waitForURL
 * @param page - Playwright Page object
 * @returns The page object for chaining
 */
export async function navigateToPanel(page: Page): Promise<Page> {
  await page.goto('/');
  await page.waitForURL('/home');
  await page.getByRole('link', { name: 'EV Trip Planner' }).click();
  await page.waitForURL(/\/ev_trip_planner\//);
  return page;
}

/**
 * Trip type enum for createTestTrip
 */
export type TripType = 'puntual' | 'recurrente';

/**
 * Creates a test trip in the EV Trip Planner panel.
 * @param page - Playwright Page object
 * @param tripType - Trip type: 'puntual' or 'recurrente'
 * @param datetime - DateTime string in ISO format (e.g., '2026-04-15T08:30')
 * @param km - Distance in kilometers
 * @param kwh - Energy consumption in kWh
 * @param description - Trip description
 * @returns The trip identifier for cleanup purposes
 */
export async function createTestTrip(
  page: Page,
  tripType: TripType,
  datetime: string,
  km: number,
  kwh: number,
  description: string,
): Promise<string> {
  // Click "+ Agregar Viaje" button
  await page.getByRole('button', { name: '+ Agregar Viaje' }).click();

  // Select trip type via combobox
  await page.getByRole('combobox').selectOption(tripType);

  // Fill form fields using web-first locators
  await page.getByLabel(/datetime/i).fill(datetime);
  await page.getByLabel(/km/i).fill(String(km));
  await page.getByLabel(/kwh/i).fill(String(kwh));
  await page.getByLabel(/descripci/i).fill(description);

  // Submit via "Crear Viaje" button
  await page.getByRole('button', { name: 'Crear Viaje' }).click();

  // Wait for the trip to appear in the list and return its identifier
  // The identifier is typically derived from the datetime or description for cleanup
  const tripIdentifier = `${datetime}-${description}`;

  // Wait for the trip card to appear
  await page.waitForSelector(`text=${description}`);

  return tripIdentifier;
}
