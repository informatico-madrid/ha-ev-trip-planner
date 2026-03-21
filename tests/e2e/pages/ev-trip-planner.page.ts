/**
 * EV Trip Planner Dashboard Page Object
 * 
 * Provides methods to interact with the EV Trip Planner dashboard
 * in Home Assistant for E2E testing.
 */

import { Page, Locator } from '@playwright/test';

export class EVTripPlannerPage {
  readonly page: Page;
  
  // Navigation
  readonly sidebar: Locator;
  readonly evTripPlannerMenuItem: Locator;
  
  // Dashboard elements
  readonly dashboardTitle: Locator;
  readonly vehicleCards: Locator;
  readonly addVehicleButton: Locator;
  
  // Sensor values (dynamic selectors)
  readonly tripDistanceSensor: (entityId: string) => Locator;
  readonly energyUsedSensor: (entityId: string) => Locator;
  readonly chargingStatusSensor: (entityId: string) => Locator;
  
  // Trip management
  readonly createTripButton: Locator;
  readonly tripList: Locator;
  
  // Settings
  readonly settingsButton: Locator;
  readonly configurationButton: Locator;

  constructor(page: Page) {
    this.page = page;
    
    // Sidebar navigation
    this.sidebar = page.locator('home-assistant-sidebar, aside');
    this.evTripPlannerMenuItem = page.getByText(/ev trip planner|planificador de viajes ev/i);
    
    // Dashboard
    this.dashboardTitle = page.getByRole('heading', { name: /ev trip planner|planificador de viajes/i });
    this.vehicleCards = page.locator('[data-testid="vehicle-card"]');
    this.addVehicleButton = page.getByRole('button', { name: /add vehicle|añadir vehículo/i });
    
    // Dynamic sensor locators
    this.tripDistanceSensor = (entityId: string) => 
      page.locator(`[data-entity="${entityId}"], [data-testid="sensor.${entityId}"]`);
    this.energyUsedSensor = (entityId: string) => 
      page.locator(`[data-entity="sensor.${entityId}_energy_used"]`);
    this.chargingStatusSensor = (entityId: string) => 
      page.locator(`[data-entity="sensor.${entityId}_charging_status"]`);
    
    // Trip management
    this.createTripButton = page.getByRole('button', { name: /create trip|crear viaje/i });
    this.tripList = page.locator('[data-testid="trip-list"]');
    
    // Settings
    this.settingsButton = page.getByRole('button', { name: /settings|ajustes/i });
    this.configurationButton = page.getByRole('button', { name: /configure|configurar/i });
  }

  /**
   * Navigate to EV Trip Planner dashboard
   */
  async goto() {
    await this.page.goto('/lovelace/ev-trip-planner');
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Navigate via sidebar
   */
  async navigateViaSidebar() {
    await this.evTripPlannerMenuItem.click();
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Check if dashboard is loaded
   */
  async isLoaded(): Promise<boolean> {
    try {
      await this.dashboardTitle.waitFor({ timeout: 5000 });
      return true;
    } catch {
      return false;
    }
  }

  /**
   * Get all vehicle cards on dashboard
   */
  async getVehicleCount(): Promise<number> {
    return await this.vehicleCards.count();
  }

  /**
   * Click add vehicle button
   */
  async clickAddVehicle() {
    await this.addVehicleButton.click();
    // Wait for modal or form to appear
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Get sensor value by entity ID
   */
  async getSensorValue(entityId: string): Promise<string> {
    const sensor = this.page.locator(`[data-entity="sensor.${entityId}"]`);
    return await sensor.textContent() || '';
  }

  /**
   * Check if vehicle is charging
   */
  async isVehicleCharging(vehicleId: string): Promise<boolean> {
    const statusCard = this.page.locator(`[data-testid="charging-status-${vehicleId}"]`);
    const text = await statusCard.textContent() || '';
    return text.toLowerCase().includes('charging') || text.toLowerCase().includes('cargando');
  }

  /**
   * Create a new trip
   */
  async createTrip(destination: string, departureTime?: string) {
    await this.createTripButton.click();
    
    // Fill in trip form
    const destinationInput = this.page.getByLabel(/destination|destino/i);
    await destinationInput.fill(destination);
    
    if (departureTime) {
      const timeInput = this.page.getByLabel(/departure time|hora de salida/i);
      await timeInput.fill(departureTime);
    }
    
    const submitButton = this.page.getByRole('button', { name: /create|crear/i });
    await submitButton.click();
    
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Open settings
   */
  async openSettings() {
    await this.settingsButton.click();
    await this.page.waitForLoadState('networkidle');
  }

  /**
   * Wait for sensor update
   */
  async waitForSensorUpdate(entityId: string, timeout: number = 10000) {
    const sensor = this.page.locator(`[data-entity="sensor.${entityId}"]`);
    await sensor.waitFor({ state: 'visible', timeout });
  }
}
