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
}
