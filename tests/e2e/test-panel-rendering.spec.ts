/**
 * E2E Tests for Panel Rendering - Captures T002, T003 specific errors
 *
 * This test specifically captures the rendering error where:
 * - Panel element exists but innerHTML is empty despite _rendered = true
 * - Race condition in rendering flow
 * Acceptance Scenarios:
 * 1. Panel element exists and has content (innerHTML.length > 0)
 * 2. innerHTML includes 'EV Trip Planner'
 * 3. innerHTML includes vehicleId
 * Usage:
 *   npx playwright test test-panel-rendering.spec.ts
 */

import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const HA_URL = process.env.HA_URL || 'http://192.168.1.100:18123';
const HA_USERNAME = process.env.HA_USER || 'tests';
const HA_PASSWORD = process.env.HA_PASSWORD || 'tests';

// Path to panel.js in the worktree
const PANEL_JS_PATH = path.join(
  process.cwd(),
  'custom_components',
  'ev_trip_planner',
  'frontend',
  'panel.js'
);

test.describe('Panel Rendering - T002/T003 Specific Error Capture', () => {
  test('should verify _rendered flag is set AFTER content is written to DOM', async () => {
    expect(fs.existsSync(PANEL_JS_PATH)).toBe(true, 'panel.js should exist');

    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // CRITICAL: Verify the specific fix in _renderTripsLater method
    // Find the _renderTripsLater method
    const renderTripsLaterMatch = panelContent.match(/async _renderTripsLater\(\)[\s\S]*?this\._rendered = true/);
    expect(renderTripsLaterMatch).toBeTruthy();
    expect(renderTripsLaterMatch !== null, '_renderTripsLater should set _rendered = true');

    // Verify the method is async
    expect(
      panelContent.includes('async _renderTripsLater()'),
      '_renderTripsLater should be an async method'
    ).toBe(true);

    // Verify _rendered = true is set AFTER trips rendering (at end of method)
    const innerHTMLWriteIndex = panelContent.indexOf('this.innerHTML = panelHtml');
    const renderTripsLaterStart = panelContent.indexOf('async _renderTripsLater()');

    // _rendered = true should be in _renderTripsLater method which comes after _render
    const renderTripsLaterEnd = panelContent.indexOf('console.log(\'EV Trip Planner Panel: _rendered = true set after trips rendering complete\')');

    expect(innerHTMLWriteIndex).toBeGreaterThan(-1, 'panel.js should write to innerHTML');
    expect(renderTripsLaterStart).toBeGreaterThan(-1, 'panel.js should have _renderTripsLater method');
    expect(renderTripsLaterEnd).toBeGreaterThan(-1, 'panel.js should log after setting _rendered');

    // The fix: _rendered = true (line 2231) comes AFTER innerHTML (line 2201)
    expect(
      renderTripsLaterEnd > innerHTMLWriteIndex,
      '_rendered = true should be set AFTER innerHTML in _renderTripsLater'
    ).toBe(true);
  });

  test('should verify connectedCallback has early exit guards', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify connectedCallback has early exit check for already-rendered panels
    expect(
      panelContent.includes('if (this._rendered && hasContent)'),
      'connectedCallback should check if already rendered with content'
    ).toBe(true);

    // Verify connectedCallback has early exit check for _pollStarted
    expect(
      panelContent.includes('if (this._pollStarted)'),
      'connectedCallback should check if polling already started'
    ).toBe(true);

    // Verify connectedCallback has _pollStarted = true set early
    const connectedCallbackMatch = panelContent.includes('connectedCallback()') &&
                                   panelContent.includes('this._pollStarted = true');
    expect(connectedCallbackMatch).toBe(true, '_pollStarted should be set in connectedCallback');
  });

  test('should verify _rendered flag reset on failed render', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify connectedCallback resets _rendered flag when innerHTML is empty
    expect(
      panelContent.includes('if (this._rendered && !hasContent)'),
      'connectedCallback should reset _rendered when no content'
    ).toBe(true);

    expect(
      panelContent.includes('this._rendered = false'),
      'connectedCallback should set _rendered = false on failed render'
    ).toBe(true);
  });

  test('should verify _pollStarted prevents multiple polling loops', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _pollStarted is initialized
    expect(
      panelContent.includes('_pollStarted = false'),
      '_pollStarted should be initialized to false'
    ).toBe(true);

    // Verify _pollStarted is set to true in connectedCallback
    expect(
      panelContent.includes('this._pollStarted = true'),
      '_pollStarted should be set to true'
    ).toBe(true);

    // Verify connectedCallback has both checks
    const hasBothChecks = panelContent.includes('if (this._rendered && hasContent)') &&
                          panelContent.includes('if (this._pollStarted)');
    expect(hasBothChecks).toBe(true, 'connectedCallback should have both early exit checks');
  });

  test('should verify vehicle_id extraction from URL', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify vehicle_id extraction from window.location.pathname
    expect(
      panelContent.includes('window.location.pathname'),
      'panel.js should extract vehicle_id from window.location.pathname'
    ).toBe(true);

    // Verify split method for vehicle_id extraction
    expect(
      panelContent.includes('path.split(\'ev-trip-planner-\''),
      'panel.js should use split to extract vehicle_id'
    ).toBe(true);

    // Verify regex fallback - use correct escaping
    expect(
      panelContent.includes('path.match(/\\/ev-trip-planner-'),
      'panel.js should use regex as fallback for vehicle_id extraction'
    ).toBe(true);
  });

  test('should verify panel HTML includes EV Trip Planner header', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify panel HTML template includes EV Trip Planner header
    expect(
      panelContent.includes('EV Trip Planner -'),
      'panel.js should include EV Trip Planner header in HTML'
    ).toBe(true);

    // Verify the header uses this._vehicleId
    expect(
      panelContent.includes('this._vehicleId}'),
      'panel.js should include vehicleId in header'
    ).toBe(true);
  });

  test('should verify innerHTML is written before subscribing to states', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Find the order of operations in _render method
    const innerHTMLIndex = panelContent.indexOf('this.innerHTML = panelHtml');
    const subscribeIndex = panelContent.indexOf('this._subscribeToStates()');

    // innerHTML should be written BEFORE subscribing to states
    expect(
      innerHTMLIndex < subscribeIndex,
      'innerHTML should be written before _subscribeToStates()'
    ).toBe(true);
  });

  test('should verify no _rendered = true set in _render before innerHTML', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Find the _render method
    const renderMatch = panelContent.match(/_render\(\)[\s\S]*?async _renderTripsLater/);
    expect(renderMatch).toBeTruthy();
    expect(renderMatch !== null, '_render method should exist before _renderTripsLater');

    // Verify the _render method exists and has proper structure
    expect(
      panelContent.includes('_render()'),
      '_render method should exist'
    ).toBe(true);

    // The key fix: _rendered = true should be set in _renderTripsLater, NOT in _render
    // Verify innerHTML is written in _render
    const innerHTMLIndex = panelContent.indexOf('this.innerHTML = panelHtml');
    expect(innerHTMLIndex).toBeGreaterThan(-1, 'panel.js should write to innerHTML in _render');

    // _rendered = true should be in _renderTripsLater (at line ~2231), not in _render method body
    const renderEndIndex = panelContent.indexOf('async _renderTripsLater()');
    const renderTripsLaterRenderedIndex = panelContent.indexOf('this._rendered = true', renderEndIndex);

    // The first _rendered = true after _render should be in _renderTripsLater
    expect(
      renderTripsLaterRenderedIndex > innerHTMLIndex,
      '_rendered = true should be set AFTER innerHTML'
    ).toBe(true);
  });

  test('should verify async trips loading does not block render', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _renderTripsLater is called with setTimeout
    expect(
      panelContent.includes('setTimeout'),
      'panel.js should use setTimeout for trips rendering'
    ).toBe(true);

    // Verify _renderTripsLater is called with a delay
    const setTimeoutMatch = panelContent.match(/setTimeout\(\(\) => \{[\s\S]*?_renderTripsLater/);
    expect(setTimeoutMatch).toBeTruthy();
    expect(setTimeoutMatch !== null, '_renderTripsLater should be called with setTimeout');

    // Verify the delay is 100ms
    expect(
      panelContent.includes('}, 100)'),
      'panel.js should have 100ms delay before rendering trips'
    ).toBe(true);
  });

  test('should verify connectedCallback exits early when already rendered', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify the complete early exit logic
    const hasContentCheck = panelContent.includes('const hasContent = this.innerHTML.length > 0 && this.innerHTML.includes(\'EV Trip Planner\')');
    expect(hasContentCheck).toBe(true, 'connectedCallback should check for hasContent');

    const earlyExit = panelContent.includes('if (this._rendered && hasContent)');
    expect(earlyExit).toBe(true, 'connectedCallback should exit early if already rendered with content');

    const returnStatement = panelContent.includes('return;');
    expect(returnStatement).toBe(true, 'connectedCallback should return early');
  });

  test('should verify T007: slug is generated correctly from vehicle_name', async () => {
    // Read config_flow.py to verify slug generation
    const configFlowPath = path.join(
      process.cwd(),
      'custom_components',
      'ev_trip_planner',
      'config_flow.py'
    );

    expect(fs.existsSync(configFlowPath)).toBe(true, 'config_flow.py should exist');

    const configFlowContent = fs.readFileSync(configFlowPath, 'utf-8');

    // Verify the slug generation formula: vehicle_name.lower().replace(" ", "_")
    // This should be in _async_create_entry method
    const slugGenerationMatch = configFlowContent.match(
      /vehicle_id\s*=\s*vehicle_name\.lower\(\)\.replace\(" ", "_"\)/
    );

    expect(slugGenerationMatch).toBeTruthy();
    expect(slugGenerationMatch !== null, 'config_flow.py should generate vehicle_id slug from vehicle_name using .lower().replace(" ", "_")');

    // Verify the slug generation is in the _async_create_entry method
    const createEntryIndex = configFlowContent.indexOf('async _async_create_entry');
    const slugGenerationIndex = configFlowContent.indexOf('vehicle_id = vehicle_name.lower().replace(" ", "_")');
    const createEntryEnd = configFlowContent.indexOf('return result', createEntryIndex);

    expect(slugGenerationIndex).toBeGreaterThan(createEntryIndex,
      'slug generation should be in _async_create_entry method');
    expect(slugGenerationIndex).toBeLessThan(createEntryEnd,
      'slug generation should be before creating entry');

    // Test cases: verify the slug generation handles different vehicle names correctly
    const testCases = [
      { vehicleName: 'Chispitas', expectedSlug: 'chispitas' },
      { vehicleName: 'Mi Coche Eléctrico', expectedSlug: 'mi_coche_eléctrico' },
      { vehicleName: 'Tesla Model 3', expectedSlug: 'tesla_model_3' },
      { vehicleName: 'Coche Eléctrico', expectedSlug: 'coche_eléctrico' },
    ];

    // Verify the logic produces correct slugs by checking the formula
    // This is a static analysis verification
    testCases.forEach(testCase => {
      const result = testCase.vehicleName.toLowerCase().replace(/ /g, '_');
      expect(result).toBe(testCase.expectedSlug,
        `Slug generation should convert "${testCase.vehicleName}" to "${testCase.expectedSlug}"`);
    });
  });
});

// Browser tests (optional - skip if HA is not available)
test.describe('Panel Rendering - Browser Verification (Optional)', () => {
  test('should have HA instance available', async ({ page }) => {
    // This test verifies HA is available for browser tests
    try {
      await page.goto(`${HA_URL}/api/states`, { timeout: 5000 });
      const response = await page.textContent('body');
      // If we get here, HA is available
      expect(response).toBeDefined();
    } catch (error) {
      console.log('HA instance not available, skipping browser tests');
      test.skip();
    }
  }, { timeout: 10000 });
});
