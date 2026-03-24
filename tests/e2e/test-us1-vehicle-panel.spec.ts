/**
 * E2E Tests for User Story 1: Corregir error "Cannot render - no vehicle_id"
 *
 * This test verifies that the EV Trip Planner vehicle panel renders correctly
 * without the "Cannot render - no vehicle_id" error.
 * Acceptance Scenarios:
 * 1. Vehicle panel renders correctly without error message
 * 2. Panel shows vehicle name in header
 * 3. No console errors related to vehicle_id
 * Usage:
 *   npx playwright test test-us1-vehicle-panel.spec.ts
 */

import { test, expect } from '@playwright/test';
import { TripPanel } from './test-base.spec';

test.describe('US1: Vehicle Panel Renders Without vehicle_id Error', () => {
  test('should navigate to vehicle panel and verify no vehicle_id error', async ({ page }) => {
    const tripPanel = new TripPanel(page, 'Coche2');

    await tripPanel.login();

    const panelUrl = `${tripPanel.haUrlValue}/ev-trip-planner-Coche2`;
    await page.goto(panelUrl, { waitUntil: 'domcontentloaded', timeout: 60000 });

    // Wait for the web component to be defined
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Check that the page does NOT contain the error message
    const bodyText = await page.textContent('body');
    expect(bodyText).not.toContain('Cannot render - no vehicle_id');
  });

  test('should display vehicle panel header with vehicle name', async ({ page }) => {
    const tripPanel = new TripPanel(page, 'Coche2');

    await tripPanel.login();
    await tripPanel.navigateToPanel();

    await tripPanel.verifyPanelHeader('Coche2');
  });

  test('should not show error div in panel', async ({ page }) => {
    const tripPanel = new TripPanel(page, 'Coche2');

    await tripPanel.login();
    await tripPanel.navigateToPanel();

    // Check for error elements that should not exist
    const errorElements = await page.locator('ev-trip-planner-panel >> .error').count();
    expect(errorElements).toBe(0);
  });

  test('should have panel container element', async ({ page }) => {
    const tripPanel = new TripPanel(page, 'Coche2');

    await tripPanel.login();
    await tripPanel.navigateToPanel();

    // Check that panel header exists
    const panelHeader = await page.locator('ev-trip-planner-panel >> .panel-header').count();
    expect(panelHeader).toBeGreaterThan(0);
  });
});

test.describe('US1: Panel JavaScript Console Validation', () => {
  test('should have no critical JavaScript errors in console', async ({ page }) => {
    const tripPanel = new TripPanel(page, 'Coche2');

    await tripPanel.login();
    await tripPanel.navigateToPanel();

    // Check for JavaScript errors
    await tripPanel.assertNoJsErrors();
  });

  test('should load panel script without errors', async ({ page }) => {
    const tripPanel = new TripPanel(page, 'Coche2');
    const consoleErrors: string[] = [];
    const failedRequests: string[] = [];

    page.on('console', message => {
      if (message.type() === 'error') {
        const text = message.text();
        // Skip harmless errors
        if (!text.includes('Failed to load resource') &&
            !text.includes('404') &&
            !text.includes('CORS')) {
          consoleErrors.push(text);
        }
      }
    });

    page.on('response', response => {
      if (response.status() >= 400) {
        failedRequests.push(`${response.url()} - ${response.status()}`);
      }
    });

    await tripPanel.login();
    await page.goto(`${tripPanel.haUrlValue}/ev-trip-planner-Coche2`, { waitUntil: 'domcontentloaded' });
    await page.waitForFunction(
      () => customElements.get('ev-trip-planner-panel') !== undefined,
      { timeout: 30000 }
    );

    // Check for panel.js failures
    const panelJsFailures = failedRequests.filter(req => req.includes('panel.js'));
    expect(panelJsFailures).toHaveLength(0);

    // Check for console errors
    expect(consoleErrors).toHaveLength(0);
  });
});
