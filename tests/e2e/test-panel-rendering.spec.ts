/**
 * E2E Tests for Panel Rendering - Captures T002, T003 specific errors
 *
 * This test specifically captures the rendering error where:
 * - Panel element exists but innerHTML is empty despite _rendered = true
 * - Race condition in rendering flow
 *
 * Acceptance Scenarios:
 * 1. Panel element exists and has content (innerHTML.length > 0)
 * 2. innerHTML includes 'EV Trip Planner'
 * 3. innerHTML includes vehicleId
 *
 * Usage:
 *   npx playwright test test-panel-rendering.spec.ts
 */

import { test, expect } from '@playwright/test';

const HA_URL = process.env.HA_URL || 'http://192.168.1.100:18123';
const HA_USERNAME = process.env.HA_USER || 'admin';
const HA_PASSWORD = process.env.HA_PASSWORD || '';

test.describe('Panel Rendering - T002/T003 Specific Error Capture', () => {
  test('should capture T002 error: panel element exists but innerHTML is empty', async ({ page }) => {
    // Skip if no password provided
    if (!HA_PASSWORD) {
      test.skip('No HA_PASSWORD provided');
    }

    // Login to Home Assistant
    await page.goto(`${HA_URL}/auth/login`);
    await page.locator('input[type="text"]').fill(HA_USERNAME);
    await page.locator('input[type="password"]').fill(HA_PASSWORD);
    await page.locator('paper-button:not([disabled])').click();
    await page.waitForURL(`${HA_URL}/dashboard`);

    // Navigate to vehicle panel with cache buster
    const vehicleId = 'cochesprueba';
    await page.goto(`${HA_URL}/ev-trip-planner-${vehicleId}?v=${Date.now()}`);
    await page.waitForLoadState('networkidle');

    // Wait for panel to be fully loaded
    await page.waitForSelector('ev-trip-planner-panel', { timeout: 10000 });

    // CRITICAL: Capture the exact error from T002/T003
    const panel = page.locator('ev-trip-planner-panel').first();

    // Get innerHTML length
    const innerHTMLLength = await page.evaluate(() => {
      const panel = document.querySelector('ev-trip-planner-panel');
      return panel ? panel.innerHTML.length : 0;
    });

    // Get _rendered status
    const renderedStatus = await page.evaluate(() => {
      const panel = document.querySelector('ev-trip-planner-panel');
      return panel ? (panel as any)._rendered : null;
    });

    // Get _vehicleId status
    const vehicleIdStatus = await page.evaluate(() => {
      const panel = document.querySelector('ev-trip-planner-panel');
      return panel ? (panel as any)._vehicleId : null;
    });

    // Get _hass status
    const hassStatus = await page.evaluate(() => {
      const panel = document.querySelector('ev-trip-planner-panel');
      return panel ? (panel as any)._hass : null;
    });

    // Get innerHTML content
    const innerHTMLContent = await page.evaluate(() => {
      const panel = document.querySelector('ev-trip-planner-panel');
      return panel ? panel.innerHTML : '';
    });

    // Log all status for debugging
    console.log('Panel Rendering Status:', {
      innerHTMLLength,
      renderedStatus,
      vehicleIdStatus,
      hassStatus,
      hasEVTripPlanner: innerHTMLContent.includes('EV Trip Planner'),
      hasVehicleId: innerHTMLContent.includes(vehicleId)
    });

    // T002/T003 Error Detection: innerHTML is empty despite _rendered = true
    if (innerHTMLLength === 0 && renderedStatus === true) {
      console.error('T002/T003 ERROR DETECTED: Panel element exists but innerHTML is empty despite _rendered = true');
      console.error('Evidence: innerHTML.length =', innerHTMLLength);
      console.error('Evidence: _rendered =', renderedStatus);
      console.error('Evidence: _vehicleId =', vehicleIdStatus);
      console.error('Evidence: _hass =', hassStatus ? 'available' : 'null');
    }

    // Verify panel has content (this is the acceptance criterion)
    expect(innerHTMLLength).toBeGreaterThan(0, 'Panel should have content, not empty innerHTML');

    // Verify innerHTML includes expected content
    expect(innerHTMLContent).toContain('EV Trip Planner', 'Panel should include EV Trip Planner header');
    expect(innerHTMLContent).toContain(vehicleId, 'Panel should include vehicleId');
  });

  test('should verify panel rendering flow completes correctly', async ({ page }) => {
    if (!HA_PASSWORD) {
      test.skip('No HA_PASSWORD provided');
    }

    // Login
    await page.goto(`${HA_URL}/auth/login`);
    await page.locator('input[type="text"]').fill(HA_USERNAME);
    await page.locator('input[type="password"]').fill(HA_PASSWORD);
    await page.locator('paper-button:not([disabled])').click();
    await page.waitForURL(`${HA_URL}/dashboard`);

    // Navigate with cache buster
    const vehicleId = 'cochesprueba';
    await page.goto(`${HA_URL}/ev-trip-planner-${vehicleId}?v=${Date.now()}`);
    await page.waitForLoadState('networkidle');

    // Wait for panel
    await page.waitForSelector('ev-trip-planner-panel', { timeout: 10000 });

    // CRITICAL: Verify the specific conditions from T002/T003
    const result = await page.evaluate((vehicleId) => {
      const panel = document.querySelector('ev-trip-planner-panel') as any;

      // Check all conditions
      const hasPanelElement = !!panel;
      const innerHTMLLength = panel ? panel.innerHTML.length : 0;
      const rendered = panel ? panel._rendered : null;
      const vehicleIdMatch = panel ? panel._vehicleId : null;
      const hassAvailable = !!panel?._hass;

      return {
        hasPanelElement,
        innerHTMLLength,
        rendered,
        vehicleIdMatch,
        hassAvailable,
        innerHTMLIncludesEVTripPlanner: panel ? panel.innerHTML.includes('EV Trip Planner') : false,
        innerHTMLIncludesVehicleId: panel ? panel.innerHTML.includes(vehicleId) : false,
        // T002/T003 Error: innerHTML is empty despite _rendered = true
        hasT002Error: rendered === true && innerHTMLLength === 0,
        // Rendering completed successfully
        renderingComplete: rendered === true && innerHTMLLength > 0 && panel.innerHTML.includes('EV Trip Planner')
      };
    }, vehicleId);

    console.log('Rendering Flow Verification:', result);

    // Verify panel element exists
    expect(result.hasPanelElement).toBe(true);

    // Verify no T002/T003 error
    expect(result.hasT002Error).toBe(false, 'Panel should not have T002/T003 error (empty innerHTML with _rendered=true)');

    // Verify rendering completed successfully
    expect(result.renderingComplete).toBe(true, 'Panel rendering should complete with content');

    // Verify innerHTML has content
    expect(result.innerHTMLLength).toBeGreaterThan(0);

    // Verify innerHTML includes expected content
    expect(result.innerHTMLIncludesEVTripPlanner).toBe(true);
    expect(result.innerHTMLIncludesVehicleId).toBe(true);
  });

  test('should capture console JavaScript logs for debugging', async ({ page }) => {
    if (!HA_PASSWORD) {
      test.skip('No HA_PASSWORD provided');
    }

    // Collect console messages
    const consoleMessages: Array<{ type: string; text: string }> = [];

    page.on('console', message => {
      consoleMessages.push({
        type: message.type(),
        text: message.text()
      });
    });

    // Login
    await page.goto(`${HA_URL}/auth/login`);
    await page.locator('input[type="text"]').fill(HA_USERNAME);
    await page.locator('input[type="password"]').fill(HA_PASSWORD);
    await page.locator('paper-button:not([disabled])').click();
    await page.waitForURL(`${HA_URL}/dashboard`);

    // Navigate to panel
    const vehicleId = 'cochesprueba';
    await page.goto(`${HA_URL}/ev-trip-planner-${vehicleId}?v=${Date.now()}`);
    await page.waitForLoadState('networkidle');

    // Wait for panel
    await page.waitForSelector('ev-trip-planner-panel', { timeout: 10000 });

    // Filter for EV Trip Planner related logs
    const evTripPlannerLogs = consoleMessages.filter(msg =>
      msg.text.toLowerCase().includes('ev trip planner') ||
      msg.text.toLowerCase().includes('vehicle_id') ||
      msg.text.toLowerCase().includes('render') ||
      msg.text.toLowerCase().includes('panel')
    );

    console.log('EV Trip Planner Console Logs:', evTripPlannerLogs);

    // Check for critical errors
    const errors = consoleMessages.filter(msg =>
      msg.type() === 'error' &&
      (msg.text.toLowerCase().includes('vehicle_id') ||
       msg.text.toLowerCase().includes('cannot render'))
    );

    expect(errors).toHaveLength(0, 'No critical JavaScript errors related to vehicle_id or rendering');
  });
});
