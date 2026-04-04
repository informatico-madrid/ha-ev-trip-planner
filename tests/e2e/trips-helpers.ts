import { type Page } from '@playwright/test';

/** Panel URL for the test vehicle (matches panel registration: PANEL_URL_PREFIX-vehicle_id) */
const PANEL_URL = '/ev-trip-planner-test_vehicle';

/**
 * Navigates to the EV Trip Planner panel using direct URL navigation.
 * Auth state is pre-loaded from storageState (playwright/.auth/user.json), so
 * direct navigation to any HA panel URL works without re-authenticating.
 * Waits for the panel's "+ Agregar Viaje" button to confirm the component rendered.
 * @param page - Playwright Page object
 * @returns The page object for chaining
 */
export async function navigateToPanel(page: Page): Promise<Page> {
  await page.goto(PANEL_URL);
  await page.waitForURL(/\/ev-trip-planner-/, { timeout: 30_000 });
  // In CI, the panel may take longer to render the button. Use 60s timeout.
  await page.getByRole('button', { name: '+ Agregar Viaje' }).waitFor({ state: 'visible', timeout: 60_000 });
  return page;
}

/**
 * Trip type enum for createTestTrip
 */
export type TripType = 'puntual' | 'recurrente';

/**
 * Trip data interface for createTestTrip parameters and return values.
 */
export interface TripData {
  tripType: TripType;
  datetime: string;
  km: number;
  kwh: number;
  description: string;
  day?: string;
  time?: string;
}

/**
 * Creates a test trip in the EV Trip Planner panel.
 *
 * For puntual trips, uses the datetime-local input.
 * For recurrente trips, uses the day selector and time input.
 *
 * @param page - Playwright Page object
 * @param tripType - Trip type: 'puntual' or 'recurrente'
 * @param datetime - DateTime string in ISO format (e.g., '2026-04-15T08:30') for puntual trips
 * @param km - Distance in kilometers
 * @param kwh - Energy consumption in kWh
 * @param description - Trip description
 * @param options - Optional: { day: '1' (Lunes), time: '08:00' } for recurrente trips
 * @returns The trip identifier for cleanup purposes
 */
export async function createTestTrip(
  page: Page,
  tripType: TripType,
  datetime: string,
  km: number,
  kwh: number,
  description: string,
  options?: { day?: string; time?: string },
): Promise<string> {
  // Click "+ Agregar Viaje" button
  await page.getByRole('button', { name: '+ Agregar Viaje' }).click();

  // Select trip type - the first combobox is the trip type selector
  const tripTypeSelect = page.locator('#trip-type');
  await tripTypeSelect.selectOption(tripType);

  if (tripType === 'recurrente') {
    // For recurrente trips, fill day selector and time input
    if (options?.day) {
      await page.locator('#trip-day').selectOption(options.day);
    }
    const timeValue = options?.time || datetime.split('T')[1] || '08:00';
    await page.locator('#trip-time').fill(timeValue);
  } else {
    // For puntual trips, fill datetime-local input
    await page.locator('#trip-datetime').fill(datetime);
  }

  // Fill common fields
  await page.locator('#trip-km').fill(String(km));
  await page.locator('#trip-kwh').fill(String(kwh));
  await page.locator('#trip-description').fill(description);

  // Handle the success alert dialog that appears after creation
  const alertPromise = page.waitForEvent('dialog').then(async dialog => {
    await dialog.accept();
  });

  // Submit via "Crear Viaje" button
  await page.getByRole('button', { name: 'Crear Viaje' }).click();

  // Wait for the success alert
  await alertPromise;

  // Wait for the trip card to appear in the list
  await page.getByText(description).first().waitFor({ state: 'visible', timeout: 10_000 });

  // Return trip identifier for cleanup
  return `${datetime}-${description}`;
}

/**
 * Deletes a test trip from the EV Trip Planner panel by its description.
 * Finds the trip card by description text, clicks delete, handles both
 * the confirmation dialog and the success alert.
 * @param page - Playwright Page object
 * @param tripId - The trip identifier returned by createTestTrip (datetime-description format)
 */
export async function deleteTestTrip(page: Page, tripId: string): Promise<void> {
  // Extract description from tripId (format: "YYYY-MM-DDTHH:MM-description")
  const parts = tripId.split('-');
  // datetime part is like "2026-04-15T08:30", so after split:
  // ["2026", "04", "15T08:30", "Description Words"]
  // Find the first part that doesn't look like a date/time component
  const datetimePart = parts.slice(0, 3).join('-'); // "2026-04-15T08:30"
  const description = tripId.substring(datetimePart.length + 1); // Everything after datetime-

  // Find the trip card by description text
  const tripCard = page.getByText(description).last();
  await tripCard.waitFor({ state: 'visible', timeout: 5_000 });

  // Set up handlers for both confirm and alert dialogs
  let dialogCount = 0;
  const dialogHandler = async (dialog: import('@playwright/test').Dialog) => {
    dialogCount++;
    await dialog.accept();
  };
  page.on('dialog', dialogHandler);

  // Click the delete button on the trip card
  // The delete button has class "delete-btn" and text "🗑️ Eliminar"
  const deleteBtn = tripCard.locator('..').locator('.delete-btn').first();
  if (await deleteBtn.isVisible().catch(() => false)) {
    await deleteBtn.click();
  } else {
    // Fallback: try finding the button by text within the trip card's parent
    await tripCard.locator('xpath=ancestor::div[contains(@class, "trip-card")]')
      .getByText('Eliminar').click();
  }

  // Wait briefly for dialogs to be handled
  await page.waitForTimeout(1_000);

  // Remove dialog handler to avoid interference with other tests
  page.removeListener('dialog', dialogHandler);
}

/**
 * Handles a native confirm() dialog by accepting or dismissing it.
 * Must be called BEFORE the action that triggers the dialog.
 * @param page - Playwright Page object
 * @param accept - Whether to accept (true) or dismiss (false) the dialog
 * @returns Promise that resolves with the dialog message text
 */
export function setupDialogHandler(
  page: Page,
  accept: boolean = true,
): Promise<string> {
  return new Promise<string>((resolve) => {
    page.once('dialog', async (dialog) => {
      const message = dialog.message();
      if (accept) {
        await dialog.accept();
      } else {
        await dialog.dismiss();
      }
      resolve(message);
    });
  });
}

/**
 * Handles a native alert() dialog by accepting it.
 * Must be called BEFORE the action that triggers the alert.
 * @param page - Playwright Page object
 * @returns Promise that resolves with the alert message text
 */
export function setupAlertHandler(page: Page): Promise<string> {
  return new Promise<string>((resolve) => {
    page.once('dialog', async (dialog) => {
      const message = dialog.message();
      await dialog.accept();
      resolve(message);
    });
  });
}

/**
 * Cleans up ALL visible trip cards from the panel by deleting them.
 * This is used in beforeEach to ensure a clean state before each test.
 * WARNING: Do NOT call this before tests that expect existing trips to be present.
 * @param page - Playwright Page object
 */
export async function cleanupTestTrips(page: Page): Promise<void> {
  // Wait for trip cards to be loaded
  await page.waitForSelector('.trip-card', { timeout: 5_000 }).catch(() => {
    // No trips exist, nothing to clean
    return;
  });

  // Check if any trip cards are visible
  const tripCards = page.locator('.trip-card');
  const count = await tripCards.count();

  if (count === 0) {
    return; // Nothing to clean
  }

  // Delete each trip card
  for (let i = 0; i < count; i++) {
    const cards = page.locator('.trip-card');
    const currentCount = await cards.count();
    if (currentCount === 0) break;

    const tripCard = cards.first();
    const isVisible = await tripCard.isVisible().catch(() => false);
    if (!isVisible) break;

    // Set up dialog handler for confirm dialog
    page.once('dialog', async (dialog) => {
      await dialog.accept();
    });

    // Try to click delete button
    const deleteBtn = tripCard.locator('.delete-btn').first();
    const deleteBtnVisible = await deleteBtn.isVisible().catch(() => false);
    if (deleteBtnVisible) {
      await deleteBtn.click();
      // Wait for deletion to process
      await page.waitForTimeout(500);
    } else {
      // Fallback: find delete by text in parent
      const parent = tripCard.locator('..');
      const deleteInParent = parent.getByText('Eliminar').first();
      const deleteVisible = await deleteInParent.isVisible().catch(() => false);
      if (deleteVisible) {
        await deleteInParent.click();
        await page.waitForTimeout(500);
      }
    }
  }
}
