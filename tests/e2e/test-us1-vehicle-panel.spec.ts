/**
 * E2E Tests for User Story 1: Corregir error "Cannot render - no vehicle_id"
 *
 * This test verifies that the EV Trip Planner vehicle panel renders correctly
 * without the "Cannot render - no vehicle_id" error.
 *
 * Acceptance Scenarios:
 * 1. Vehicle panel renders correctly without error message
 * 2. Panel shows vehicle name in header
 * 3. No console errors related to vehicle_id
 *
 * Usage:
 *   npx playwright test test-us1.spec.ts
 */

import { test, expect } from '@playwright/test';

const HA_URL = process.env.HA_URL || 'http://localhost:18123';
const HA_USERNAME = process.env.HA_USERNAME || 'admin';
const HA_PASSWORD = process.env.HA_PASSWORD || '';

test.describe('US1: Vehicle Panel Renders Without vehicle_id Error', () => {
  test('should navigate to vehicle panel and verify no vehicle_id error', async ({ page }) => {
    // Skip if no password provided
    if (!HA_PASSWORD) {
      test.skip('No HA_PASSWORD provided');
    }

    // Login to Home Assistant
    await page.goto(`${HA_URL}/auth/login`);
    await page.fill('#username', HA_USERNAME);
    await page.fill('#password', HA_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL(`${HA_URL}/dashboard`);

    // Navigate to the vehicle panel (replace COCHESPRUEBA with actual vehicle_id)
    // Using a generic vehicle panel URL pattern
    await page.goto(`${HA_URL}/ev-trip-planner-cochesprueba?v=${Date.now()}`);

    // Wait for panel to load
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);

    // Check that the page does NOT contain the error message
    const errorText = await page.textContent('body');
    expect(errorText).not.toContain('Cannot render - no vehicle_id');

    // Check that there are no JavaScript errors related to vehicle_id
    const consoleMessages = await page.evaluate(() => {
      const messages: string[] = [];
      // Check for vehicle_id related errors
      const errorElements = document.querySelectorAll('[class*="error"], [class*="error-"]');
      errorElements.forEach(el => {
        if (el.textContent?.toLowerCase().includes('vehicle_id')) {
          messages.push(el.textContent);
        }
      });
      return messages;
    });

    // Should not have vehicle_id related errors
    const vehicleIdErrors = consoleMessages.filter(msg =>
      msg.toLowerCase().includes('vehicle_id') ||
      msg.toLowerCase().includes('no vehicle')
    );

    expect(vehicleIdErrors).toHaveLength(0);
  });

  test('should display vehicle panel header with vehicle name', async ({ page }) => {
    if (!HA_PASSWORD) {
      test.skip('No HA_PASSWORD provided');
    }

    // Login
    await page.goto(`${HA_URL}/auth/login`);
    await page.fill('#username', HA_USERNAME);
    await page.fill('#password', HA_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL(`${HA_URL}/dashboard`);

    // Navigate to vehicle panel
    await page.goto(`${HA_URL}/ev-trip-planner-cochesprueba?v=${Date.now()}`);
    await page.waitForLoadState('networkidle');

    // Check for panel header with EV Trip Planner
    const headerText = await page.textContent('h1, .panel-header h1');
    expect(headerText).toContain('EV Trip Planner');
  });

  test('should not show error div in panel', async ({ page }) => {
    if (!HA_PASSWORD) {
      test.skip('No HA_PASSWORD provided');
    }

    // Login
    await page.goto(`${HA_URL}/auth/login`);
    await page.fill('#username', HA_USERNAME);
    await page.fill('#password', HA_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL(`${HA_URL}/dashboard`);

    // Navigate to vehicle panel
    await page.goto(`${HA_URL}/ev-trip-planner-cochesprueba?v=${Date.now()}`);
    await page.waitForLoadState('networkidle');

    // Check for error elements that should not exist
    const errorElements = await page.locator('div:has-text("Cannot render")').count();
    expect(errorElements).toBe(0);
  });

  test('should have panel container element', async ({ page }) => {
    if (!HA_PASSWORD) {
      test.skip('No HA_PASSWORD provided');
    }

    // Login
    await page.goto(`${HA_URL}/auth/login`);
    await page.fill('#username', HA_USERNAME);
    await page.fill('#password', HA_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL(`${HA_URL}/dashboard`);

    // Navigate to vehicle panel
    await page.goto(`${HA_URL}/ev-trip-planner-cochesprueba?v=${Date.now()}`);
    await page.waitForLoadState('networkidle');

    // Check that panel container exists
    const panelContainer = await page.locator('.panel-container').count();
    expect(panelContainer).toBeGreaterThan(0);
  });
});

test.describe('US1: Panel JavaScript Console Validation', () => {
  test('should have no critical JavaScript errors in console', async ({ page }) => {
    if (!HA_PASSWORD) {
      test.skip('No HA_PASSWORD provided');
    }

    // Collect console errors before navigation
    const consoleErrors: string[] = [];

    page.on('console', message => {
      if (message.type() === 'error') {
        consoleErrors.push(message.text());
      }
    });

    // Login
    await page.goto(`${HA_URL}/auth/login`);
    await page.fill('#username', HA_USERNAME);
    await page.fill('#password', HA_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL(`${HA_URL}/dashboard`);

    // Navigate to vehicle panel
    await page.goto(`${HA_URL}/ev-trip-planner-cochesprueba?v=${Date.now()}`);
    await page.waitForLoadState('networkidle');

    // Check for vehicle_id related errors
    const vehicleIdErrors = consoleErrors.filter(msg =>
      msg.toLowerCase().includes('vehicle_id') ||
      msg.toLowerCase().includes('cannot render')
    );

    expect(vehicleIdErrors).toHaveLength(0, 'No vehicle_id related console errors');
  });

  test('should load panel script without errors', async ({ page }) => {
    if (!HA_PASSWORD) {
      test.skip('No HA_PASSWORD provided');
    }

    // Collect network requests
    const failedRequests: string[] = [];

    page.on('response', response => {
      if (response.status() >= 400) {
        failedRequests.push(`${response.url()} - ${response.status()}`);
      }
    });

    // Login
    await page.goto(`${HA_URL}/auth/login`);
    await page.fill('#username', HA_USERNAME);
    await page.fill('#password', HA_PASSWORD);
    await page.click('button[type="submit"]');
    await page.waitForURL(`${HA_URL}/dashboard`);

    // Navigate to vehicle panel
    await page.goto(`${HA_URL}/ev-trip-planner-cochesprueba?v=${Date.now()}`);
    await page.waitForLoadState('networkidle');

    // Check for panel.js failures
    const panelJsFailures = failedRequests.filter(req => req.includes('panel.js'));
    expect(panelJsFailures).toHaveLength(0);
  });
});
