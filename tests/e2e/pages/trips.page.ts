/**
 * Trips Page Object - E2E Tests for EV Trip Planner
 *
 * Provides methods to interact with the trips panel in Home Assistant.
 * Uses web-first locators (getByRole, getByText, getByLabel) for Shadow DOM compatibility.
 */

import { Page, Locator } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

export class TripsPage {
  readonly page: Page;

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
    this.sidebar = page.locator('ha-sidebar, aside');
    this.evTripPlannerMenuItem = page.getByText(/ev trip planner|planificador de viajes ev/i);

    // Empty state - shown when no trips exist
    this.emptyState = page.getByText(/no hay viajes|there are no trips/i);

    // Add trip button
    this.addTripButton = page.getByRole('button', { name: /\+ Agregar Viaje|Add Trip/i });

    // Trip form overlay
    this.tripFormOverlay = page.getByRole('dialog', { name: /viaje|trip/i });

    // Trip type options
    this.recurrenteOption = page.getByRole('radio', { name: /recurrente|recurring/i });
    this.puntualOption = page.getByRole('radio', { name: /puntual|one-time|single/i });

    // Day selector for recurring trips
    this.daySelector = page.getByLabel(/día|day/i);

    // Time input
    this.timeInput = page.getByLabel(/hora|time/i);

    // Submit button in form
    this.submitButton = page.getByRole('button', { name: /guardar|save|crear|create/i });

    // Trip card locators (indexed by position - 1-based for user friendliness)
    this.tripCard = (index: number) =>
      page.locator('.trip-card').nth(index - 1);

    // Action buttons
    this.editButton = (index: number) =>
      this.tripCard(index).getByRole('button', { name: /editar|edit/i });
    this.deleteButton = (index: number) =>
      this.tripCard(index).getByRole('button', { name: /eliminar|delete/i });
    this.pauseButton = (index: number) =>
      this.tripCard(index).getByRole('button', { name: /pausar|pause/i });
    this.resumeButton = (index: number) =>
      this.tripCard(index).getByRole('button', { name: /reanudar|resume/i });
    this.completeButton = (index: number) =>
      this.tripCard(index).getByRole('button', { name: /completar|complete/i });
    this.cancelButton = (index: number) =>
      this.tripCard(index).getByRole('button', { name: /cancelar|cancel/i });

    // Confirmation dialog
    this.confirmDialog = page.getByRole('dialog', { name: /confirm|confirmar|eliminar|delete/i });
    this.confirmDeleteBtn = page.getByRole('button', { name: /eliminar|delete|confirm|confirmar/i });
    this.cancelDialogBtn = page.getByRole('button', { name: /cancelar|cancel|volver|back/i });
  }

  /**
   * Navigate to trips panel via sidebar
   */
  async navigateViaSidebar(): Promise<void> {
    await this.evTripPlannerMenuItem.click();
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Get panel URL from stored auth state
   */
  async getPanelUrl(): Promise<string> {
    if (this.panelUrl) {
      return this.panelUrl;
    }

    const authDir = path.join(__dirname, '..', '..', '..', 'playwright', '.auth');
    const panelUrlPath = path.join(authDir, 'panel-url.txt');

    try {
      this.panelUrl = fs.readFileSync(panelUrlPath, 'utf-8').trim();
      return this.panelUrl;
    } catch {
      // Fallback to default URL pattern
      this.panelUrl = 'http://127.0.0.1:8477/ev-trip-planner-Coche2';
      return this.panelUrl;
    }
  }

  /**
   * Navigate directly to trips panel
   */
  async navigateDirect(): Promise<void> {
    const url = await this.getPanelUrl();
    await this.page.goto(url, { waitUntil: 'domcontentloaded' });
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Click the add trip button to open the form
   */
  async clickAddTripButton(): Promise<void> {
    await this.addTripButton.click();
    await this.tripFormOverlay.waitFor({ state: 'visible', timeout: 5000 });
  }

  /**
   * Select Recurrente (recurring) trip type
   */
  async selectRecurrente(): Promise<void> {
    await this.recurrenteOption.click();
  }

  /**
   * Select Puntual (one-time) trip type
   */
  async selectPuntual(): Promise<void> {
    await this.puntualOption.click();
  }

  /**
   * Enter time in the form
   */
  async enterTime(time: string): Promise<void> {
    await this.timeInput.fill(time);
  }

  /**
   * Open edit form for a specific trip
   */
  async openEditFormForTrip(index: number): Promise<void> {
    await this.editButton(index).click();
    await this.tripFormOverlay.waitFor({ state: 'visible', timeout: 5000 });
  }

  /**
   * Open delete confirmation dialog for a specific trip
   */
  async openDeleteDialogForTrip(index: number): Promise<void> {
    await this.deleteButton(index).click();
    await this.confirmDialog.waitFor({ state: 'visible', timeout: 5000 });
  }

  /**
   * Confirm the delete action
   */
  async confirmDelete(): Promise<void> {
    await this.confirmDeleteBtn.click();
    await this.confirmDialog.waitFor({ state: 'hidden', timeout: 5000 });
  }

  /**
   * Cancel the delete action
   */
  async cancelDelete(): Promise<void> {
    await this.cancelDialogBtn.click();
    await this.confirmDialog.waitFor({ state: 'hidden', timeout: 5000 });
  }

  /**
   * Check if empty state is visible (no trips message)
   */
  async isEmptyStateVisible(): Promise<boolean> {
    try {
      return await this.emptyState.isVisible({ timeout: 3000 });
    } catch {
      return false;
    }
  }

  /**
   * Get the number of trips in the list
   * Uses Shadow DOM traversal via evaluate
   */
  async getTripCount(): Promise<number> {
    return await this.page.evaluate(() => {
      const panel = document.querySelector('ev-trip-planner-panel');
      if (!panel || !panel.shadowRoot) {
        return 0;
      }
      return panel.shadowRoot.querySelectorAll('.trip-card').length;
    });
  }

  /**
   * Wait for trip count to reach expected value
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
   * Check if a trip is paused
   */
  async isTripPaused(tripIndex: number): Promise<boolean> {
    return await this.page.evaluate((index) => {
      const panel = document.querySelector('ev-trip-planner-panel');
      if (!panel || !panel.shadowRoot) {
        return false;
      }
      const cards = panel.shadowRoot.querySelectorAll('.trip-card');
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
   * Check if a trip is active
   */
  async isTripActive(tripIndex: number): Promise<boolean> {
    const isPaused = await this.isTripPaused(tripIndex);
    return !isPaused;
  }

  /**
   * Call trip_create service via Home Assistant API
   */
  async callTripCreateService(data: {
    vehicle_id: string;
    trip_type: 'recurrente' | 'puntual';
    day?: string;
    time: string;
  }): Promise<void> {
    await this.page.evaluate(async (serviceData) => {
      const panel = document.querySelector('ev-trip-planner-panel') as any;
      if (!panel || !panel.hass) {
        throw new Error('Cannot call service: panel or hass not available');
      }
      await panel.hass.callService('ev_trip_planner', 'trip_create', serviceData);
    }, data);
  }

  /**
   * Call trip_update service via Home Assistant API
   */
  async callTripUpdateService(tripId: string, data: {
    time?: string;
    day?: string;
    enabled?: boolean;
  }): Promise<void> {
    await this.page.evaluate(async ({ id, updateData }) => {
      const panel = document.querySelector('ev-trip-planner-panel') as any;
      if (!panel || !panel.hass) {
        throw new Error('Cannot call service: panel or hass not available');
      }
      await panel.hass.callService('ev_trip_planner', 'trip_update', {
        trip_id: id,
        ...updateData,
      });
    }, { id: tripId, updateData: data });
  }

  /**
   * Call delete_trip service via Home Assistant API
   */
  async callDeleteTripService(tripId: string): Promise<void> {
    await this.page.evaluate(async (id) => {
      const panel = document.querySelector('ev-trip-planner-panel') as any;
      if (!panel || !panel.hass) {
        throw new Error('Cannot call service: panel or hass not available');
      }
      await panel.hass.callService('ev_trip_planner', 'delete_trip', { trip_id: id });
    }, tripId);
  }

  /**
   * Call pause_recurring_trip service via Home Assistant API
   */
  async callPauseRecurringTripService(tripId: string): Promise<void> {
    await this.page.evaluate(async (id) => {
      const panel = document.querySelector('ev-trip-planner-panel') as any;
      if (!panel || !panel.hass) {
        throw new Error('Cannot call service: panel or hass not available');
      }
      await panel.hass.callService('ev_trip_planner', 'pause_recurring_trip', { trip_id: id });
    }, tripId);
  }

  /**
   * Call resume_recurring_trip service via Home Assistant API
   */
  async callResumeRecurringTripService(tripId: string): Promise<void> {
    await this.page.evaluate(async (id) => {
      const panel = document.querySelector('ev-trip-planner-panel') as any;
      if (!panel || !panel.hass) {
        throw new Error('Cannot call service: panel or hass not available');
      }
      await panel.hass.callService('ev_trip_planner', 'resume_recurring_trip', { trip_id: id });
    }, tripId);
  }

  /**
   * Call complete_punctual_trip service via Home Assistant API
   */
  async callCompletePunctualTripService(tripId: string): Promise<void> {
    await this.page.evaluate(async (id) => {
      const panel = document.querySelector('ev-trip-planner-panel') as any;
      if (!panel || !panel.hass) {
        throw new Error('Cannot call service: panel or hass not available');
      }
      await panel.hass.callService('ev_trip_planner', 'complete_punctual_trip', { trip_id: id });
    }, tripId);
  }

  /**
   * Call cancel_punctual_trip service via Home Assistant API
   */
  async callCancelPunctualTripService(tripId: string): Promise<void> {
    await this.page.evaluate(async (id) => {
      const panel = document.querySelector('ev-trip-planner-panel') as any;
      if (!panel || !panel.hass) {
        throw new Error('Cannot call service: panel or hass not available');
      }
      await panel.hass.callService('ev_trip_planner', 'cancel_punctual_trip', { trip_id: id });
    }, tripId);
  }
}
