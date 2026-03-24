/**
 * Test Base Class for EV Trip Planner E2E Tests
 *
 * This base class provides common setup, helper methods, and utilities
 * for all E2E tests in the EV Trip Planner project.
 *
 * Usage:
 *   import { TripPanelTestBase, test } from './test-base.spec';
 *
 *   test.describe('My Tests', () => {
 *     const test = new TripPanelTestBase();
 *
 *     test('should do something', async ({ page }) => {
 *       await test.setup(page);
 *       // ... test logic
 *     });
 *   });
 */

import { Page, TestInfo } from '@playwright/test';

export class TripPanelTestBase {
  protected page: Page | null = null;
  protected testInfo: TestInfo | null = null;
  protected vehicleId: string = 'chispitas';
  protected haUrl: string = 'http://192.168.1.100:8123';

  /**
   * Configure the test with custom settings
   */
  configure(options: {
    vehicleId?: string;
    haUrl?: string;
    timeout?: number;
  }) {
    if (options.vehicleId) {
      this.vehicleId = options.vehicleId;
    }
    if (options.haUrl) {
      this.haUrl = options.haUrl;
    }
  }

  /**
   * Setup test before each test case
   */
  async setup(page: Page, testInfo?: TestInfo, timeout = 30000) {
    this.page = page;
    this.testInfo = testInfo || null;

    // Navigate to panel URL
    await page.goto(`${this.haUrl}/ev-trip-planner-${this.vehicleId}`);

    // Wait for panel to load
    await this.waitForPanel(timeout);

    // Set up dialog handler for confirmation dialogs
    this.setupDialogHandler();
  }

  /**
   * Wait for panel to be ready
   */
  async waitForPanel(timeout = 30000) {
    await this.page!.waitForFunction(
      (url) => {
        try {
          const panel = (window as any)._tripPanel;
          return panel !== undefined && panel._vehicleId !== undefined;
        } catch (e) {
          return false;
        }
      },
      this.haUrl,
      { timeout }
    );
  }

  /**
   * Set up dialog handler for confirmation dialogs
   */
  setupDialogHandler(accept: boolean = true) {
    this.page!.on('dialog', async (dialog) => {
      console.log(`Dialog message: ${dialog.message()}`);
      if (accept) {
        await dialog.accept();
      } else {
        await dialog.dismiss();
      }
    });
  }

  /**
   * Get panel URL
   */
  getPanelUrl(suffix: string = ''): string {
    return `${this.haUrl}${suffix}`;
  }

  /**
   * Navigate to panel URL
   */
  async navigateToPanel(suffix: string = '') {
    await this.page!.goto(this.getPanelUrl(suffix));
  }

  /**
   * Verify panel header contains expected text
   */
  async verifyPanelHeader(expectedText: string) {
    const header = this.page!.locator('.panel-header');
    await expect(header).toBeVisible();
    await expect(header).toContainText(expectedText);
  }

  /**
   * Verify trips section is visible
   */
  async verifyTripsSectionVisible() {
    const tripsSection = this.page!.locator('.trips-section');
    await expect(tripsSection).toBeVisible();
  }

  /**
   * Verify sensors section is visible
   */
  async verifySensorsSectionVisible() {
    const sensorsSection = this.page!.locator('.sensors-section');
    await expect(sensorsSection).toBeVisible();
  }

  /**
   * Click add trip button and wait for form
   */
  async openAddTripForm() {
    const addTripButton = this.page!.locator('.add-trip-btn');
    await addTripButton.click();

    const formOverlay = this.page!.locator('.trip-form-overlay');
    await expect(formOverlay).toBeVisible({ timeout: 10000 });
  }

  /**
   * Fill trip creation/edit form
   */
  async fillTripForm(data: {
    type: 'recurrente' | 'puntual';
    day?: string;
    time: string;
    km?: string;
    kwh?: string;
    description?: string;
  }) {
    // Select trip type
    await this.page!.selectOption('#trip-type', data.type);

    // Set day if provided
    if (data.day !== undefined) {
      await this.page!.selectOption('#trip-day', data.day);
    }

    // Set time
    await this.page!.fill('#trip-time', data.time);

    // Set optional km
    if (data.km !== undefined) {
      await this.page!.fill('#trip-km', data.km);
    }

    // Set optional kwh
    if (data.kwh !== undefined) {
      await this.page!.fill('#trip-kwh', data.kwh);
    }

    // Set optional description
    if (data.description !== undefined) {
      await this.page!.fill('#trip-description', data.description);
    }
  }

  /**
   * Submit trip form
   */
  async submitTripForm() {
    await this.page!.locator('.btn-primary').click();
  }

  /**
   * Wait for form to close
   */
  async waitForFormToClose(timeout = 5000) {
    const formOverlay = this.page!.locator('.trip-form-overlay');
    await expect(formOverlay).toBeHidden({ timeout });
  }

  /**
   * Get trip count
   */
  async getTripCount(): Promise<number> {
    return await this.page!.locator('.trip-card').count();
  }

  /**
   * Wait for trips section to be populated
   */
  async waitForTripsSection(timeout = 10000) {
    await this.page!.waitForSelector('.trips-list', { timeout });
  }

  /**
   * Log test progress
   */
  logProgress(message: string) {
    console.log(`[TripPanelTest] ${message}`);
  }

  /**
   * Cleanup after test
   */
  async cleanup() {
    this.page = null;
    this.testInfo = null;
  }
}

// Export test and expect from Playwright
export { test, expect } from '@playwright/test';
