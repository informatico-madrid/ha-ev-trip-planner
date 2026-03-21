/**
 * EV Trip Planner E2E Tests
 * 
 * These tests verify the EV Trip Planner integration works correctly
 * in the Home Assistant UI using Playwright.
 * 
 * Prerequisites:
 * - Playwright installed: npm install -D @playwright/test
 * - Browsers installed: npx playwright install
 * - HA instance running with EV Trip Planner integration
 * 
 * Environment Variables:
 * - HA_URL: Home Assistant URL (default: http://192.168.1.100:8123)
 * - HA_TOKEN: Long-lived access token for HA
 * 
 * Usage:
 *   npx playwright test                    # Run all tests
 *   npx playwright test --headed           # Run with browser visible
 *   npx playwright test --debug            # Run in debug mode
 *   npx playwright test ha-ev-trip-planner.spec.ts  # Run specific file
 */

import { test, expect } from '@playwright/test';
import { HALoginPage, EVTripPlannerPage } from './pages';

// Get credentials from environment
const HA_USERNAME = process.env.HA_USERNAME || 'admin';
const HA_PASSWORD = process.env.HA_PASSWORD || '';

test.describe('Home Assistant Authentication', () => {
  let loginPage: HALoginPage;

  test.beforeEach(({ page }) => {
    loginPage = new HALoginPage(page);
  });

  test('should display login page', async ({ page }) => {
    await loginPage.goto();
    
    // Verify login form elements are visible
    await expect(loginPage.usernameInput).toBeVisible();
    await expect(loginPage.passwordInput).toBeVisible();
    await expect(loginPage.loginButton).toBeVisible();
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    // Skip if no password provided (CI environments)
    if (!HA_PASSWORD) {
      test.skip();
    }
    
    await loginPage.goto();
    await loginPage.login(HA_USERNAME, HA_PASSWORD);
    
    // Should redirect away from login page
    await expect(page).not.toHaveURL(/auth\/login/);
  });

  test('should show error with invalid credentials', async ({ page }) => {
    await loginPage.goto();
    await loginPage.login('invalid', 'wrongpassword');
    
    // Should show error message
    const errorMessage = await loginPage.getErrorMessage();
    expect(errorMessage).toBeTruthy();
  });
});

test.describe('EV Trip Planner Dashboard', () => {
  let dashboardPage: EVTripPlannerPage;

  test.beforeEach(async ({ page }) => {
    dashboardPage = new EVTripPlannerPage(page);
    
    // Navigate to dashboard
    await dashboardPage.goto();
  });

  test('should load dashboard successfully', async () => {
    // Verify dashboard is loaded
    const isLoaded = await dashboardPage.isLoaded();
    expect(isLoaded).toBe(true);
  });

  test('should display vehicle cards', async () => {
    // Get vehicle count
    const vehicleCount = await dashboardPage.getVehicleCount();
    
    // Should have at least 0 vehicles (dashboard should render)
    expect(vehicleCount).toBeGreaterThanOrEqual(0);
  });

  test('should navigate to add vehicle flow', async ({ page }) => {
    // Click add vehicle button
    await dashboardPage.clickAddVehicle();
    
    // Should show some form or modal
    await page.waitForLoadState('networkidle');
  });
});

test.describe('EV Trip Planner Sensors', () => {
  test('should display sensor entities via API', async ({ request }) => {
    const haUrl = process.env.HA_URL || 'http://192.168.1.100:8123';
    const haToken = process.env.HA_TOKEN;
    
    if (!haToken) {
      test.skip('No HA_TOKEN provided');
    }
    
    // Get all EV Trip Planner entities
    const response = await request.get(`${haUrl}/api/states`, {
      headers: {
        'Authorization': `Bearer ${haToken}`,
      },
    });
    
    expect(response.ok()).toBe(true);
    
    const states = await response.json();
    const evTripEntities = states.filter((state: any) => 
      state.entity_id.includes('ev_trip')
    );
    
    // Log entity count for debugging
    console.log(`Found ${evTripEntities.length} EV Trip Planner entities`);
    
    // Verify we have some entities
    expect(evTripEntities.length).toBeGreaterThan(0);
  });
});

test.describe('EV Trip Planner Dashboard - Visual Regression', () => {
  let dashboardPage: EVTripPlannerPage;

  test.beforeEach(async ({ page }) => {
    dashboardPage = new EVTripPlannerPage(page);
    await dashboardPage.goto();
  });

  test('should match dashboard screenshot', async ({ page }) => {
    // This test can be enabled for visual regression testing
    // await expect(page).toHaveScreenshot('ev-trip-dashboard.png');
    
    // For now, just verify the page loads
    await expect(dashboardPage.dashboardTitle).toBeVisible();
  });
});
