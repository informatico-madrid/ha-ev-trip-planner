/**
 * Trips Page Object - E2E Tests for EV Trip Planner
 *
 * Provides methods to interact with the trips panel in Home Assistant.
 * Uses web-first locators (getByRole, getByText, getByLabel) for Shadow DOM compatibility.
 */

import { Page, Locator, expect } from '@playwright/test';

export class TripsPage {
  readonly page: Page;

  // ============================================================
  // CONSTANTS - Selector patterns and configuration
  // ============================================================

  // Panel element selector
  static readonly PANEL_SELECTOR = 'ev-trip-planner-panel';

  // CSS class for trip cards
  static readonly TRIP_CARD_CLASS = '.trip-card';

  // Sidebar selectors
  static readonly SIDEBAR_SELECTOR = 'ha-sidebar, aside';

  // Service configuration
  static readonly SERVICE_DOMAIN = 'ev_trip_planner';
  static readonly SERVICES = {
    CREATE: 'trip_create',
    UPDATE: 'trip_update',
    DELETE: 'delete_trip',
    PAUSE_RECURRING: 'pause_recurring_trip',
    RESUME_RECURRING: 'resume_recurring_trip',
    COMPLETE_PUNCTUAL: 'complete_punctual_trip',
    CANCEL_PUNCTUAL: 'cancel_punctual_trip',
  } as const;

  // Text patterns for UI elements (i18n-aware)
  static readonly TEXT_PATTERNS = {
    // Navigation
    EV_TRIP_PLANNER: /ev trip planner|planificador de viajes ev/i,

    // Empty state
    NO_TRIPS: /no hay viajes|there are no trips/i,

    // Buttons
    AGREGAR_VIAJE: /\+ Agregar Viaje|Add Trip/i,
    GUARDAR: /guardar|save|crear|create/i,
    EDITAR: /editar|edit/i,
    ELIMINAR: /eliminar|delete/i,
    PAUSAR: /pausar|pause/i,
    REANUDAR: /reanudar|resume/i,
    COMPLETAR: /completar|complete/i,
    CANCELAR: /cancelar|cancel/i,

    // Form elements
    VIAJE_TRIP: /viaje|trip/i,
    RECURRENTE: /recurrente|recurring/i,
    PUNTUAL: /puntual|one-time|single/i,
    DIA_DAY: /día|day/i,
    HORA_TIME: /hora|time/i,

    // Dialog
    CONFIRM_DIALOG: /confirm|confirmar|eliminar|delete/i,
    CANCEL_DIALOG: /cancelar|cancel|volver|back/i,
  } as const;

  // Default configuration
  static readonly DEFAULT_PANEL_URL = 'http://127.0.0.1:8123/ev-trip-planner-Coche2';
  static readonly DEFAULT_TIMEOUT_MS = 5000;
  static readonly DEFAULT_WAIT_MS = 100;

  // ============================================================
  // LOCATORS
  // ============================================================

  // Sidebar navigation
  readonly sidebar: Locator;
  readonly evTripPlannerMenuItem: Locator;

  // Panel URL (read from auth state)
  protected panelUrl: string | null = null;

  // Empty state
  readonly emptyState: Locator;

  // Add trip button
  readonly addTripButton: Locator;

  // Trip form overlay
  readonly tripFormOverlay: Locator;

  // Trip type radio buttons
  readonly recurrenteOption: Locator;
  readonly puntualOption: Locator;

  // Day selector (for recurring trips)
  readonly daySelector: Locator;

  // Time input
  readonly timeInput: Locator;

  // Submit button
  readonly submitButton: Locator;

  // Trip card locators (indexed by position)
  readonly tripCard: (index: number) => Locator;

  // Action buttons for trips
  readonly editButton: (index: number) => Locator;
  readonly deleteButton: (index: number) => Locator;
  readonly pauseButton: (index: number) => Locator;
  readonly resumeButton: (index: number) => Locator;
  readonly completeButton: (index: number) => Locator;
  readonly cancelButton: (index: number) => Locator;

  // Confirmation dialog
  readonly confirmDialog: Locator;
  readonly confirmDeleteBtn: Locator;
  readonly cancelDialogBtn: Locator;

  constructor(page: Page) {
    this.page = page;

    // Sidebar navigation
    this.sidebar = page.locator(TripsPage.SIDEBAR_SELECTOR);
    this.evTripPlannerMenuItem = page.getByText(TripsPage.TEXT_PATTERNS.EV_TRIP_PLANNER);

    // Empty state - shown when no trips exist
    this.emptyState = page.getByText(TripsPage.TEXT_PATTERNS.NO_TRIPS);

    // Add trip button
    this.addTripButton = page.getByRole('button', { name: TripsPage.TEXT_PATTERNS.AGREGAR_VIAJE });

    // Trip form overlay
    this.tripFormOverlay = page.getByRole('dialog', { name: TripsPage.TEXT_PATTERNS.VIAJE_TRIP });

    // Trip type options
    this.recurrenteOption = page.getByRole('radio', { name: TripsPage.TEXT_PATTERNS.RECURRENTE });
    this.puntualOption = page.getByRole('radio', { name: TripsPage.TEXT_PATTERNS.PUNTUAL });

    // Day selector for recurring trips
    this.daySelector = page.getByLabel(TripsPage.TEXT_PATTERNS.DIA_DAY);

    // Time input
    this.timeInput = page.getByLabel(TripsPage.TEXT_PATTERNS.HORA_TIME);

    // Submit button in form
    this.submitButton = page.getByRole('button', { name: TripsPage.TEXT_PATTERNS.GUARDAR });

    // Trip card locators (indexed by position - 1-based for user friendliness)
    this.tripCard = (index: number) =>
      page.locator(TripsPage.TRIP_CARD_CLASS).nth(index - 1);

    // Action buttons
    this.editButton = (index: number) =>
      this.tripCard(index).getByRole('button', { name: TripsPage.TEXT_PATTERNS.EDITAR });
    this.deleteButton = (index: number) =>
      this.tripCard(index).getByRole('button', { name: TripsPage.TEXT_PATTERNS.ELIMINAR });
    this.pauseButton = (index: number) =>
      this.tripCard(index).getByRole('button', { name: TripsPage.TEXT_PATTERNS.PAUSAR });
    this.resumeButton = (index: number) =>
      this.tripCard(index).getByRole('button', { name: TripsPage.TEXT_PATTERNS.REANUDAR });
    this.completeButton = (index: number) =>
      this.tripCard(index).getByRole('button', { name: TripsPage.TEXT_PATTERNS.COMPLETAR });
    this.cancelButton = (index: number) =>
      this.tripCard(index).getByRole('button', { name: TripsPage.TEXT_PATTERNS.CANCELAR });

    // Confirmation dialog
    this.confirmDialog = page.getByRole('dialog', { name: TripsPage.TEXT_PATTERNS.CONFIRM_DIALOG });
    this.confirmDeleteBtn = page.getByRole('button', { name: TripsPage.TEXT_PATTERNS.ELIMINAR });
    this.cancelDialogBtn = page.getByRole('button', { name: TripsPage.TEXT_PATTERNS.CANCEL_DIALOG });
  }

  /**
   * Navigate to trips panel via sidebar.
   * Clicks the EV Trip Planner menu item in the Home Assistant sidebar.
   *
   * @returns Promise that resolves when navigation is complete
   */
  async navigateViaSidebar(): Promise<void> {
    await this.evTripPlannerMenuItem.click();
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Get the panel URL for direct navigation.
   * Reads from cached value, environment variable HA_PANEL_URL, or falls back to DEFAULT_PANEL_URL.
   *
   * @returns Promise resolving to the panel URL string
   */
  async getPanelUrl(): Promise<string> {
    if (this.panelUrl) {
      return this.panelUrl;
    }

    // Try environment variable first
    const envUrl = process.env.HA_PANEL_URL;
    if (envUrl) {
      this.panelUrl = envUrl;
      return this.panelUrl;
    }

    // Fallback to default - this should be overridden by test setup
    // The test should call setPanelUrl before navigation if using direct navigation
    this.panelUrl = TripsPage.DEFAULT_PANEL_URL;
    return this.panelUrl;
  }

  /**
   * Set panel URL explicitly.
   * Recommended approach when using direct navigation instead of sidebar.
   *
   * @param url - The full URL to the EV Trip Planner panel
   */
  setPanelUrl(url: string): void {
    this.panelUrl = url;
  }

  /**
   * Navigate directly to trips panel using stored URL.
   * Use this for direct navigation instead of navigateViaSidebar().
   *
   * @returns Promise that resolves when navigation is complete
   */
  async navigateDirect(): Promise<void> {
    const url = await this.getPanelUrl();
    await this.page.goto(url, { waitUntil: 'domcontentloaded' });
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Click the add trip button to open the trip form modal.
   *
   * @returns Promise that resolves when form is visible
   */
  async clickAddTripButton(): Promise<void> {
    await this.addTripButton.click();
    await this.tripFormOverlay.waitFor({ state: 'visible', timeout: 5000 });
  }

  /**
   * Select Recurrente (recurring) trip type in the form.
   *
   * @returns Promise that resolves when selection is complete
   */
  async selectRecurrente(): Promise<void> {
    await this.recurrenteOption.click();
  }

  /**
   * Select Puntual (one-time) trip type in the form.
   *
   * @returns Promise that resolves when selection is complete
   */
  async selectPuntual(): Promise<void> {
    await this.puntualOption.click();
  }

  /**
   * Enter time in the form time input field.
   *
   * @param time - Time string in HH:MM format (e.g., "08:30")
   * @returns Promise that resolves when time is entered
   */
  async enterTime(time: string): Promise<void> {
    await this.timeInput.fill(time);
  }

  /**
   * Open the edit form for a specific trip by index.
   *
   * @param index - 1-based index of the trip card (1 = first trip)
   * @returns Promise that resolves when edit form is visible
   */
  async openEditFormForTrip(index: number): Promise<void> {
    await this.editButton(index).click();
    await this.tripFormOverlay.waitFor({ state: 'visible', timeout: 5000 });
  }

  /**
   * Open the delete confirmation dialog for a specific trip by index.
   *
   * @param index - 1-based index of the trip card (1 = first trip)
   * @returns Promise that resolves when delete dialog is visible
   */
  async openDeleteDialogForTrip(index: number): Promise<void> {
    await this.deleteButton(index).click();
    await this.confirmDialog.waitFor({ state: 'visible', timeout: 5000 });
  }

  /**
   * Confirm the delete action by clicking the confirm button.
   *
   * @returns Promise that resolves when dialog is dismissed
   */
  async confirmDelete(): Promise<void> {
    await this.confirmDeleteBtn.click();
    await this.confirmDialog.waitFor({ state: 'hidden', timeout: 5000 });
  }

  /**
   * Cancel the delete action by clicking the cancel button.
   *
   * @returns Promise that resolves when dialog is dismissed
   */
  async cancelDelete(): Promise<void> {
    await this.cancelDialogBtn.click();
    await this.confirmDialog.waitFor({ state: 'hidden', timeout: 5000 });
  }

  /**
   * Check if the empty state message is visible (shown when no trips exist).
   *
   * @returns Promise resolving to true if empty state is visible, false otherwise
   */
  async isEmptyStateVisible(): Promise<boolean> {
    try {
      return await this.emptyState.isVisible({ timeout: 3000 });
    } catch {
      return false;
    }
  }

  /**
   * Get the current number of trips displayed in the panel.
   * Uses Shadow DOM traversal to count .trip-card elements.
   *
   * @returns Promise resolving to the trip count
   */
  async getTripCount(): Promise<number> {
    return await this.page.evaluate(() => {
      const panel = document.querySelector(TripsPage.PANEL_SELECTOR);
      if (!panel || !panel.shadowRoot) {
        return 0;
      }
      return panel.shadowRoot.querySelectorAll(TripsPage.TRIP_CARD_CLASS).length;
    });
  }

  /**
   * Wait for the trip count to reach the expected value.
   * Polls every 100ms until timeout is reached.
   *
   * @param expected - Expected trip count
   * @param timeout - Maximum wait time in milliseconds (default: 5000)
   * @returns Promise that resolves when count matches expected
   * @throws Error if count doesn't match within timeout
   */
  async waitForTripCount(expected: number, timeout: number = 5000): Promise<void> {
    const startTime = Date.now();
    while (Date.now() - startTime < timeout) {
      const count = await this.getTripCount();
      if (count === expected) {
        return;
      }
      await this.page.waitForTimeout(100);
    }
    throw new Error(`Expected ${expected} trips but found ${await this.getTripCount()}`);
  }

  /**
   * Check if a trip is in paused state.
   *
   * @param tripIndex - 1-based index of the trip card
   * @returns Promise resolving to true if trip is paused, false otherwise
   */
  async isTripPaused(tripIndex: number): Promise<boolean> {
    return await this.page.evaluate((index) => {
      const panel = document.querySelector(TripsPage.PANEL_SELECTOR);
      if (!panel || !panel.shadowRoot) {
        return false;
      }
      const cards = panel.shadowRoot.querySelectorAll(TripsPage.TRIP_CARD_CLASS);
      if (index < 0 || index >= cards.length) {
        return false;
      }
      const card = cards[index];
      return card.classList.contains('paused') ||
             card.getAttribute('data-state') === 'paused' ||
             card.textContent?.toLowerCase().includes('pausado') === true;
    }, tripIndex - 1); // 1-based to 0-based
  }

  /**
   * Check if a trip is in active state (not paused).
   *
   * @param tripIndex - 1-based index of the trip card
   * @returns Promise resolving to true if trip is active, false if paused
   */
  async isTripActive(tripIndex: number): Promise<boolean> {
    const isPaused = await this.isTripPaused(tripIndex);
    return !isPaused;
  }

  /**
   * Set up automatic dialog handling.
   * Call this in test beforeEach to auto-accept all dialogs.
   *
   * @param action - Dialog action to take ('accept' | 'dismiss'), defaults to 'accept'
   */
  setupDialogHandler(action: 'accept' | 'dismiss' = 'accept'): void {
    this.page.on('dialog', async dialog => {
      if (action === 'accept') {
        await dialog.accept();
      } else {
        await dialog.dismiss();
      }
    });
  }

  // ============================================================
  // ASSERTION HELPERS
  // ============================================================

  /**
   * Assert that empty state is visible.
   * Uses Playwright's expect for auto-retrying assertions.
   *
   * @returns Promise that resolves when assertion passes
   */
  async assertEmptyState(): Promise<void> {
    await expect(this.emptyState).toBeVisible();
  }

  /**
   * Assert that a specific number of trips are displayed.
   * Uses Playwright's expect for auto-retrying assertions.
   *
   * @param expected - Expected trip count
   * @returns Promise that resolves when assertion passes
   */
  async assertTripCount(expected: number): Promise<void> {
    const actual = await this.getTripCount();
    expect(actual).toBe(expected);
  }

  /**
   * Assert that a trip at given index is in active state.
   *
   * @param tripIndex - 1-based index of the trip card
   * @returns Promise that resolves when assertion passes
   */
  async assertTripActive(tripIndex: number): Promise<void> {
    const isActive = await this.isTripActive(tripIndex);
    expect(isActive).toBe(true);
  }

  /**
   * Assert that a trip at given index is in paused state.
   *
   * @param tripIndex - 1-based index of the trip card
   * @returns Promise that resolves when assertion passes
   */
  async assertTripPaused(tripIndex: number): Promise<void> {
    const isPaused = await this.isTripPaused(tripIndex);
    expect(isPaused).toBe(true);
  }

  /**
   * Call trip_create service via Home Assistant API.
   * Used for test setup to create trips directly without UI.
   *
   * @param data - Trip creation data
   * @param data.vehicle_id - The vehicle identifier
   * @param data.trip_type - Either 'recurrente' (recurring) or 'puntual' (one-time)
   * @param data.day - Day of week for recurring trips (e.g., 'Lunes')
   * @param data.time - Time in HH:MM format (e.g., '08:30')
   * @returns Promise that resolves when service call completes
   * @throws Error if panel or hass is not available
   */
  async callTripCreateService(data: {
    vehicle_id: string;
    trip_type: 'recurrente' | 'puntual';
    day?: string;
    time: string;
  }): Promise<void> {
    await this.page.evaluate(async (serviceData) => {
      const panel = document.querySelector(TripsPage.PANEL_SELECTOR) as any;
      if (!panel || !panel.hass) {
        throw new Error('Cannot call service: panel or hass not available');
      }
      await panel.hass.callService(TripsPage.SERVICE_DOMAIN, TripsPage.SERVICES.CREATE, serviceData);
    }, data);
  }

  /**
   * Call trip_update service via Home Assistant API.
   * Used to modify an existing trip's properties.
   *
   * @param tripId - The unique identifier of the trip to update
   * @param data - Fields to update
   * @param data.time - New time in HH:MM format (optional)
   * @param data.day - New day for recurring trips (optional)
   * @param data.enabled - Enable/disable the trip (optional)
   * @returns Promise that resolves when service call completes
   * @throws Error if panel or hass is not available
   */
  async callTripUpdateService(tripId: string, data: {
    time?: string;
    day?: string;
    enabled?: boolean;
  }): Promise<void> {
    await this.page.evaluate(async ({ id, updateData }) => {
      const panel = document.querySelector(TripsPage.PANEL_SELECTOR) as any;
      if (!panel || !panel.hass) {
        throw new Error('Cannot call service: panel or hass not available');
      }
      await panel.hass.callService(TripsPage.SERVICE_DOMAIN, TripsPage.SERVICES.UPDATE, {
        trip_id: id,
        ...updateData,
      });
    }, { id: tripId, updateData: data });
  }

  /**
   * Call delete_trip service via Home Assistant API.
   * Permanently removes a trip.
   *
   * @param tripId - The unique identifier of the trip to delete
   * @returns Promise that resolves when service call completes
   * @throws Error if panel or hass is not available
   */
  async callDeleteTripService(tripId: string): Promise<void> {
    await this.page.evaluate(async (id) => {
      const panel = document.querySelector(TripsPage.PANEL_SELECTOR) as any;
      if (!panel || !panel.hass) {
        throw new Error('Cannot call service: panel or hass not available');
      }
      await panel.hass.callService(TripsPage.SERVICE_DOMAIN, TripsPage.SERVICES.DELETE, { trip_id: id });
    }, tripId);
  }

  /**
   * Call pause_recurring_trip service via Home Assistant API.
   * Pauses a recurring trip (shows Reanudar button instead of Pausar).
   *
   * @param tripId - The unique identifier of the recurring trip to pause
   * @returns Promise that resolves when service call completes
   * @throws Error if panel or hass is not available
   */
  async callPauseRecurringTripService(tripId: string): Promise<void> {
    await this.page.evaluate(async (id) => {
      const panel = document.querySelector(TripsPage.PANEL_SELECTOR) as any;
      if (!panel || !panel.hass) {
        throw new Error('Cannot call service: panel or hass not available');
      }
      await panel.hass.callService(TripsPage.SERVICE_DOMAIN, TripsPage.SERVICES.PAUSE_RECURRING, { trip_id: id });
    }, tripId);
  }

  /**
   * Call resume_recurring_trip service via Home Assistant API.
   * Resumes a paused recurring trip (shows Pausar button again).
   *
   * @param tripId - The unique identifier of the paused recurring trip to resume
   * @returns Promise that resolves when service call completes
   * @throws Error if panel or hass is not available
   */
  async callResumeRecurringTripService(tripId: string): Promise<void> {
    await this.page.evaluate(async (id) => {
      const panel = document.querySelector(TripsPage.PANEL_SELECTOR) as any;
      if (!panel || !panel.hass) {
        throw new Error('Cannot call service: panel or hass not available');
      }
      await panel.hass.callService(TripsPage.SERVICE_DOMAIN, TripsPage.SERVICES.RESUME_RECURRING, { trip_id: id });
    }, tripId);
  }

  /**
   * Call complete_punctual_trip service via Home Assistant API.
   * Marks a punctual trip as completed and removes it from the active list.
   *
   * @param tripId - The unique identifier of the punctual trip to complete
   * @returns Promise that resolves when service call completes
   * @throws Error if panel or hass is not available
   */
  async callCompletePunctualTripService(tripId: string): Promise<void> {
    await this.page.evaluate(async (id) => {
      const panel = document.querySelector(TripsPage.PANEL_SELECTOR) as any;
      if (!panel || !panel.hass) {
        throw new Error('Cannot call service: panel or hass not available');
      }
      await panel.hass.callService(TripsPage.SERVICE_DOMAIN, TripsPage.SERVICES.COMPLETE_PUNCTUAL, { trip_id: id });
    }, tripId);
  }

  /**
   * Call cancel_punctual_trip service via Home Assistant API.
   * Cancels a punctual trip and removes it from the active list.
   *
   * @param tripId - The unique identifier of the punctual trip to cancel
   * @returns Promise that resolves when service call completes
   * @throws Error if panel or hass is not available
   */
  async callCancelPunctualTripService(tripId: string): Promise<void> {
    await this.page.evaluate(async (id) => {
      const panel = document.querySelector(TripsPage.PANEL_SELECTOR) as any;
      if (!panel || !panel.hass) {
        throw new Error('Cannot call service: panel or hass not available');
      }
      await panel.hass.callService(TripsPage.SERVICE_DOMAIN, TripsPage.SERVICES.CANCEL_PUNCTUAL, { trip_id: id });
    }, tripId);
  }
}
