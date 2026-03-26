/**
 * Test Base Class for EV Trip Planner E2E Tests
 *
 * Uses hass-taste-test for ephemeral HA container with pre-authenticated URLs
 * NO manual login - hass.link() provides authenticated access automatically
 */

/// <reference types="playwright/types/test" />
import { test as baseTest, expect, Page } from '@playwright/test';
import { HomeAssistant, PlaywrightBrowser } from 'hass-taste-test';

// Declare customElements for browser context
declare const customElements: CustomElementRegistry;

// Global hass-taste-test instance shared across tests
let hassInstance: HomeAssistant | null = null;
let hassUrl: string = '';

/**
 * Get or create the hass-taste-test instance
 * This is called once before all tests
 */
export async function getHassInstance(): Promise<HomeAssistant> {
  if (!hassInstance) {
    // Configuration for the ephemeral HA instance
    // Include our custom component path
    const evTripPlannerPath = '/mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/custom_components/ev_trip_planner';

    hassInstance = await HomeAssistant.create(`
input_boolean:
  coche1_cargando:
    name: "Coche1 Cargando"
  coche1_en_casa:
    name: "Coche1 En Casa"
  coche1_enchufado:
    name: "Coche1 Enchufado"
`, {
      python: 'python3',
      browser: new PlaywrightBrowser('chromium'),
      customComponents: [evTripPlannerPath],
    });

    // Get the authenticated URL
    hassUrl = hassInstance.link;
    console.log('[HassTasteTest] Ephemeral HA URL:', hassUrl);
  }
  return hassInstance;
}

/**
 * Get the base URL for the ephemeral HA instance
 */
export function getHassUrl(): string {
  if (!hassUrl) {
    throw new Error('Hass instance not initialized. Call getHassInstance() first.');
  }
  return hassUrl;
}

export const test = baseTest.extend<{
  tripPanel: TripPanel;
  hassUrl: string;
}>({
  tripPanel: async ({ page }, use) => {
    const tripPanel = new TripPanel(page);
    await use(tripPanel);
  },
  hassUrl: async ({}, use) => {
    await use(hassUrl);
  },
});

export class TripPanel {
  protected page: Page;
  protected vehicleId: string;
  protected consoleErrors: string[] = [];

  constructor(page: Page, vehicleId: string = 'Coche2') {
    this.page = page;
    this.vehicleId = vehicleId;
    this.consoleErrors = [];
  }

  /**
   * Set up console error listener to catch JavaScript errors
   */
  async setupConsoleErrorHandler(): Promise<void> {
    this.consoleErrors = [];
    this.page.on('console', msg => {
      if (msg.type() === 'error') {
        const errorText = msg.text();
        // Skip harmless errors
        if (!errorText.includes('Failed to load resource') &&
            !errorText.includes('404') &&
            !errorText.includes('CORS')) {
          this.consoleErrors.push(`[${msg.type()}] ${errorText}`);
          console.warn(`Console Error: ${errorText}`);
        }
      }
    });

    this.page.on('pageerror', error => {
      this.consoleErrors.push(`[PAGE_ERROR] ${error.message}`);
      console.warn(`Page Error: ${error.message}`);
    });
  }

  /**
   * Check for JavaScript errors
   */
  async assertNoJsErrors(): Promise<void> {
    if (this.consoleErrors.length > 0) {
      console.error('JavaScript errors detected:');
      this.consoleErrors.forEach(err => console.error(`  - ${err}`));
      throw new Error(`JavaScript errors detected: ${this.consoleErrors.length} errors found`);
    }
  }

  /**
   * Navigate directly to panel using hass-taste-test authenticated URL
   * NO MANUAL LOGIN - dashboard.link() provides pre-authenticated access
   */
  async navigateToPanel(): Promise<void> {
    // Wait for the web component to be defined
    await this.page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Wait for the panel to be in the DOM
    await this.page.waitForSelector('ev-trip-planner-panel', { timeout: 30000 });

    // Wait for the panel to be visible and rendered with content
    await this.page.locator('ev-trip-planner-panel').waitFor({ state: 'visible', timeout: 30000 });

    // Verify panel content is rendered
    await this.page.locator('ev-trip-planner-panel >> .add-trip-btn').waitFor({ state: 'visible', timeout: 30000 });
  }

  /**
   * Setup dialog handler for confirmation dialogs
   */
  async setupDialogHandler(accept: boolean = true): Promise<void> {
    this.page.on('dialog', async (dialog) => {
      console.log(`Dialog message: ${dialog.message()}`);
      if (accept) {
        await dialog.accept();
      } else {
        await dialog.dismiss();
      }
    });
  }

  /**
   * Verify panel header by penetrating Shadow DOM
   */
  async verifyPanelHeader(expectedText: string): Promise<void> {
    await this.page.locator('ev-trip-planner-panel').waitFor({ state: 'visible', timeout: 30000 });

    const headerElement = this.page.locator('ev-trip-planner-panel >> .panel-header');
    await expect(headerElement).toBeVisible({ timeout: 10000 });

    const headerText = await headerElement.textContent();
    if (!headerText) {
      throw new Error('Panel header text is empty');
    }

    expect(headerText).toContain(expectedText);
  }

  /**
   * Verify trips section by penetrating Shadow DOM
   */
  async verifyTripsSectionVisible(): Promise<void> {
    await this.page.locator('ev-trip-planner-panel').waitFor({ state: 'visible', timeout: 30000 });

    const tripsSection = this.page.locator('ev-trip-planner-panel >> .trips-section');
    await expect(tripsSection).toBeVisible({ timeout: 10000 });
  }

  /**
   * Verify sensors section by penetrating Shadow DOM
   */
  async verifySensorsSectionVisible(): Promise<void> {
    await this.page.locator('ev-trip-planner-panel').waitFor({ state: 'visible', timeout: 30000 });

    const sensorsSection = this.page.locator('ev-trip-planner-panel >> .sensors-section');
    await expect(sensorsSection).toBeVisible({ timeout: 10000 });
  }

  /**
   * Get trip count by penetrating Shadow DOM
   */
  async getTripCount(): Promise<number> {
    const count = await this.page.evaluate(() => {
      const panel = document.querySelector('ev-trip-planner-panel') as any;
      if (!panel || !panel.shadowRoot) {
        return 0;
      }
      const trips = panel.shadowRoot.querySelectorAll('.trip-card');
      return trips.length;
    });
    return count;
  }

  async openAddTripForm(): Promise<void> {
    const addTripButton = this.page.locator('ev-trip-planner-panel').locator('.add-trip-btn');
    await addTripButton.click();
    const formOverlay = this.page.locator('ev-trip-planner-panel').locator('.trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });
  }

  async fillTripForm(data: {
    type: 'recurrente' | 'puntual';
    day?: string;
    time: string;
    km?: string;
    kwh?: string;
    description?: string;
  }): Promise<void> {
    await this.page.locator('ev-trip-planner-panel').locator('#trip-type').selectOption(data.type);
    if (data.day !== undefined) {
      await this.page.locator('ev-trip-planner-panel').locator('#trip-day').selectOption(data.day);
    }
    await this.page.locator('ev-trip-planner-panel').locator('#trip-time').fill(data.time);
    if (data.km !== undefined) {
      await this.page.locator('ev-trip-planner-panel').locator('#trip-km').fill(data.km);
    }
    if (data.kwh !== undefined) {
      await this.page.locator('ev-trip-planner-panel').locator('#trip-kwh').fill(data.kwh);
    }
    if (data.description !== undefined) {
      await this.page.locator('ev-trip-planner-panel').locator('#trip-description').fill(data.description);
    }
  }

  async submitTripForm(): Promise<void> {
    await this.page.locator('ev-trip-planner-panel').locator('.btn-primary').click();
  }

  async waitForFormToClose(timeout: number = 5000): Promise<void> {
    const formOverlay = this.page.locator('ev-trip-planner-panel').locator('.trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout });
  }

  logProgress(message: string): void {
    console.log(`[TripPanel] ${message}`);
  }
}
