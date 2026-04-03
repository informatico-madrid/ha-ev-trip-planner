import { Page, Locator, expect } from '@playwright/test';

export class EVTripPlannerPage {
  readonly page: Page;

  // Shadow DOM selectors via pierce combinator `>>`
  readonly sidebarLink: Locator;
  readonly addTripBtn: Locator;
  readonly tripsList: Locator;
  readonly tripFormOverlay: Locator;

  // Form fields (inside .trip-form-container via pierce)
  readonly tripTypeSelect: Locator;
  readonly tripDaySelect: Locator;
  readonly tripTimeInput: Locator;
  readonly tripKmInput: Locator;
  readonly tripKwhInput: Locator;
  readonly tripDescriptionInput: Locator;
  readonly tripSubmitBtn: Locator;

  constructor(page: Page) {
    this.page = page;

    // Sidebar navigation (light DOM)
    this.sidebarLink = page.locator('a:has-text("EV Trip Planner")');

    // Shadow DOM — pierce combinator `>>` traverses into shadow roots
    this.addTripBtn       = page.locator('ev-trip-planner-panel >> .add-trip-btn');
    this.tripsList        = page.locator('ev-trip-planner-panel >> .trips-list');
    this.tripFormOverlay  = page.locator('ev-trip-planner-panel >> .trip-form-overlay');

    // Form fields inside .trip-form-container
    this.tripTypeSelect       = page.locator('ev-trip-planner-panel >> #trip-type');
    this.tripDaySelect        = page.locator('ev-trip-planner-panel >> #trip-day');
    this.tripTimeInput        = page.locator('ev-trip-planner-panel >> #trip-time');
    this.tripKmInput          = page.locator('ev-trip-planner-panel >> #trip-km');
    this.tripKwhInput         = page.locator('ev-trip-planner-panel >> #trip-kwh');
    this.tripDescriptionInput = page.locator('ev-trip-planner-panel >> #trip-description');
    this.tripSubmitBtn        = page.locator('ev-trip-planner-panel >> .trip-form-container .btn-primary');
  }

  async openFromSidebar() {
    await this.sidebarLink.click();
    await this.page.waitForURL(/\/ev-trip-planner-/);
    await this.addTripBtn.waitFor({ state: 'visible', timeout: 15000 });
  }

  async openAddTripForm() {
    await this.addTripBtn.click();
    await this.tripFormOverlay.waitFor({ state: 'visible', timeout: 5000 });
  }

  async createRecurringTrip(opts: {
    day?: number;       // 0=Sun … 6=Sat; default 1 (Lunes)
    time?: string;      // HH:MM; default "12:00"
    km?: number;
    kwh?: number;
    description?: string;
  }) {
    const {
      day = 1,
      time = '12:00',
      km,
      kwh,
      description,
    } = opts;

    await this.tripTypeSelect.waitFor({ state: 'visible' });
    await this.tripTypeSelect.selectOption('recurrente');
    await this.tripDaySelect.selectOption(String(day));
    await this.tripTimeInput.fill(time);
    if (km !== undefined) await this.tripKmInput.fill(String(km));
    if (kwh !== undefined) await this.tripKwhInput.fill(String(kwh));
    if (description) await this.tripDescriptionInput.fill(description);

    await this.tripSubmitBtn.click();
    // Form closes and trip card appears
    await this.tripFormOverlay.waitFor({ state: 'hidden', timeout: 5000 });
  }

  async tripCardLocator(tripId: string): Promise<Locator> {
    return this.page.locator(`ev-trip-planner-panel >> .trip-card[data-trip-id="${tripId}"]`);
  }

  async expectTripVisible(tripId: string) {
    const card = await this.tripCardLocator(tripId);
    await expect(card).toBeVisible({ timeout: 10000 });
  }

  async deleteTrip(tripId: string) {
    const card = await this.tripCardLocator(tripId);
    const deleteBtn = card.locator('.delete-btn');
    this.page.on('dialog', dialog => dialog.accept());  // Confirm dialog
    await deleteBtn.click();
    await card.waitFor({ state: 'detached', timeout: 5000 });
  }
}