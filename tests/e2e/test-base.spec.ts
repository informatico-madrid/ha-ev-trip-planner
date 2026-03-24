/**
 * Test Base Class for EV Trip Planner E2E Tests
 *
 * Enhanced to validate Shadow DOM content and JavaScript errors
 */

import { test as baseTest, expect, Page } from '@playwright/test';

export const test = baseTest.extend<{
  tripPanel: TripPanel;
}>({
  tripPanel: async ({ page }, use) => {
    const tripPanel = new TripPanel(page);
    await use(tripPanel);
  },
});

export { expect };

export class TripPanel {
  protected page: Page;
  protected vehicleId: string;
  protected haUrl: string;
  protected consoleErrors: string[] = [];

  constructor(page: Page, vehicleId: string = 'Coche2', haUrl: string = 'http://192.168.1.100:18123') {
    this.page = page;
    this.vehicleId = vehicleId;
    this.haUrl = haUrl;
    this.consoleErrors = [];
  }

  get haUrlValue(): string {
    return this.haUrl;
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

  async login(username: string = 'tests', password: string = 'tests'): Promise<void> {
    await this.setupConsoleErrorHandler();
    await this.page.goto(this.haUrl, { waitUntil: 'networkidle' });

    // Fill login form using HA's native input elements
    await this.page.fill('input[name="username"]', username);
    await this.page.fill('input[name="password"]', password);

    // Click the brand-colored login button
    await this.page.click('ha-button[variant="brand"]');

    // Wait for home navigation (HA redirects to /home/overview after login)
    await this.page.waitForURL(`${this.haUrl}/home*`, { waitUntil: 'networkidle', timeout: 30000 });
  }

  async navigateToPanel(): Promise<void> {
    // Navigate to the panel using the correct URL format
    const panelUrl = `${this.haUrl}/panel/ev-trip-planner-${this.vehicleId}`;
    await this.page.goto(panelUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });

    // Wait for the web component to be defined
    await this.page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Wait for the panel to be in the DOM
    await this.page.waitForSelector('ev-trip-planner-panel', { timeout: 30000 });

    // Wait for the panel to be visible and rendered with content
    // Playwright's locator API automatically penetrates Shadow DOM
    await this.page.locator('ev-trip-planner-panel').waitFor({ state: 'visible', timeout: 30000 });

    // Verify panel content is rendered by looking for a specific element
    // The add-trip-btn is inside the panel's shadow DOM and indicates successful rendering
    await this.page.locator('ev-trip-planner-panel >> .add-trip-btn').waitFor({ state: 'visible', timeout: 30000 });
  }

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
   * The header is rendered inside the ev-trip-planner-panel shadow root
   */
  async verifyPanelHeader(expectedText: string): Promise<void> {
    // Wait for panel to be fully rendered
    await this.page.locator('ev-trip-planner-panel').waitFor({ state: 'visible', timeout: 30000 });

    // Use Playwright locator to penetrate Shadow DOM and get header text
    // The panel-header class is inside the shadow root
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
    // Wait for panel to be fully rendered
    await this.page.locator('ev-trip-planner-panel').waitFor({ state: 'visible', timeout: 30000 });

    // Use Playwright locator to penetrate Shadow DOM
    const tripsSection = this.page.locator('ev-trip-planner-panel >> .trips-section');
    await expect(tripsSection).toBeVisible({ timeout: 10000 });
  }

  /**
   * Verify sensors section by penetrating Shadow DOM
   */
  async verifySensorsSectionVisible(): Promise<void> {
    // Wait for panel to be fully rendered
    await this.page.locator('ev-trip-planner-panel').waitFor({ state: 'visible', timeout: 30000 });

    // Use Playwright locator to penetrate Shadow DOM
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

  /**
   * Wait for trips section to be populated by penetrating Shadow DOM
   */
  async waitForTripsSection(timeout: number = 10000): Promise<void> {
    await this.page.waitForFunction(
      () => {
        const panel = (window as any)._tripPanel;
        return panel !== undefined && panel.innerHTML.includes('trips-section');
      },
      { timeout }
    );
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
    await this.page.locator('ev-trip-planner-panel').selectOption('#trip-type', data.type);
    if (data.day !== undefined) {
      await this.page.locator('ev-trip-planner-panel').selectOption('#trip-day', data.day);
    }
    await this.page.locator('ev-trip-planner-panel').fill('#trip-time', data.time);
    if (data.km !== undefined) {
      await this.page.locator('ev-trip-planner-panel').fill('#trip-km', data.km);
    }
    if (data.kwh !== undefined) {
      await this.page.locator('ev-trip-planner-panel').fill('#trip-kwh', data.kwh);
    }
    if (data.description !== undefined) {
      await this.page.locator('ev-trip-planner-panel').fill('#trip-description', data.description);
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

export { Page, expect };
