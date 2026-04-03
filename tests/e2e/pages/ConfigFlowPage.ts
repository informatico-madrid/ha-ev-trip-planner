import { Page, Locator } from '@playwright/test';

export class ConfigFlowPage {
  readonly page: Page;

  // Integrations page
  readonly addIntegrationBtn: Locator;
  readonly searchInput: Locator;

  // Config Flow form
  readonly vehicleNameInput: Locator;
  readonly submitBtn: Locator;

  constructor(page: Page) {
    this.page = page;
    this.addIntegrationBtn = page.getByRole('button', { name: 'Add Integration' });
    this.searchInput = page.getByPlaceholder('Search...');
    this.vehicleNameInput = page.locator('input[name="vehicle_name"]');
    this.submitBtn = page.getByRole('button', { name: 'Submit' });
  }

  async navigateToIntegrations() {
    await this.page.goto('/config/integrations');
  }

  async addIntegration(name: string) {
    await this.addIntegrationBtn.click();
    await this.searchInput.fill(name);
    await this.page.getByRole('option', { name }).click();
    await this.vehicleNameInput.waitFor({ state: 'visible' });
  }

  async fillVehicleName(name: string) {
    await this.vehicleNameInput.fill(name);
  }

  async submit() {
    await this.submitBtn.click();
    await this.page.waitForTimeout(500);  // Allow transition to next step
  }

  async waitForIntegrationComplete() {
    // Config Flow returns to integrations page on success
    await this.page.waitForURL(/\/config\/integrations/, { timeout: 15000 });
  }

  async waitForPanelInSidebar() {
    await this.page.waitForSelector('a:has-text("EV Trip Planner")', { timeout: 10000 });
  }
}
