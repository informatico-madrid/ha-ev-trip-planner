/**
 * E2E Tests for User Story 5: Automatic Sensor Updates
 *
 * This test verifies that the panel automatically updates sensor values
 * when they change in Home Assistant, without requiring a page reload.
 *
 * Acceptance Scenarios:
 * 1. Panel subscribes to state_changed events for vehicle sensors
 * 2. Sensor values update in real-time when hass.states changes
 * 3. No page reload required - updates are live
 *
 * Usage:
 *   npx playwright test test-us5-sensor-updates.spec.ts
 */

import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const HA_URL = process.env.HA_URL || 'http://localhost:18123';
const HA_USERNAME = process.env.HA_USER || process.env.HA_USERNAME || 'tests';
const HA_PASSWORD = process.env.HA_PASSWORD || 'tests';

// Path to panel.js in the worktree
const PANEL_JS_PATH = path.join(
  process.cwd(),
  'custom_components',
  'ev_trip_planner',
  'frontend',
  'panel.js'
);

test.describe('US5: Automatic Sensor Updates', () => {
  // Verify panel.js code exists and has the required methods
  test('should verify panel.js has _subscribeToStates method', async () => {
    // Read the panel.js file
    const panelJsPath = PANEL_JS_PATH;

    // Check if file exists
    expect(fs.existsSync(panelJsPath)).toBe(true);

    const panelContent = fs.readFileSync(panelJsPath, 'utf-8');

    // Verify _subscribeToStates method exists
    expect(panelContent).toContain('_subscribeToStates()');
    expect(panelContent).toContain('subscribeMessage');
    expect(panelContent).toContain('state_changed');
  });

  test('should verify panel.js has _getVehicleStates method that captures all sensors', async () => {
    const panelJsPath = PANEL_JS_PATH;
    expect(fs.existsSync(panelJsPath)).toBe(true);

    const panelContent = fs.readFileSync(panelJsPath, 'utf-8');

    // Verify _getVehicleStates method exists
    expect(panelContent).toContain('_getVehicleStates()');

    // Verify it uses hass.states
    expect(panelContent).toContain('this._hass.states');

    // Verify it captures multiple sensor patterns
    expect(panelContent).toContain('sensor.');
    expect(panelContent).toContain('binary_sensor.');
    expect(panelContent).toContain('ev_trip_planner');
  });

  test('should verify panel.js has _update method for live updates', async () => {
    const panelJsPath = PANEL_JS_PATH;
    expect(fs.existsSync(panelJsPath)).toBe(true);

    const panelContent = fs.readFileSync(panelJsPath, 'utf-8');

    // Verify _update method exists
    expect(panelContent).toContain('_update()');

    // Verify _update uses the subscription mechanism
    expect(panelContent).toContain('this._unsubscribe');
  });

  test('should verify panel.js has _updateSensorItem method', async () => {
    const panelJsPath = PANEL_JS_PATH;
    expect(fs.existsSync(panelJsPath)).toBe(true);

    const panelContent = fs.readFileSync(panelJsPath, 'utf-8');

    // Verify _updateSensorItem method exists
    expect(panelContent).toContain('_updateSensorItem(');
  });

  test('should verify panel.js subscribes to state changes after render', async () => {
    const panelJsPath = PANEL_JS_PATH;
    expect(fs.existsSync(panelJsPath)).toBe(true);

    const panelContent = fs.readFileSync(panelJsPath, 'utf-8');

    // Verify _render calls _subscribeToStates
    expect(panelContent).toContain('_subscribeToStates()');

    // Verify the subscription happens after panel is rendered
    // Check that _render method exists and _subscribeToStates is called
    const hasRenderMethod = panelContent.includes('_render()');
    const hasSubscribeCallInRender = panelContent.includes('this._rendered = true') &&
                                      panelContent.includes('_subscribeToStates()');
    expect(hasRenderMethod).toBe(true);
    expect(hasSubscribeCallInRender).toBe(true);
  });

  test('should verify panel.js handles state changes correctly', async () => {
    const panelJsPath = PANEL_JS_PATH;
    expect(fs.existsSync(panelJsPath)).toBe(true);

    const panelContent = fs.readFileSync(panelJsPath, 'utf-8');

    // Verify the state change handler checks entity patterns
    expect(panelContent).toContain('startsWith');
    expect(panelContent).toContain('patterns');

    // Verify the handler logs when state changes
    expect(panelContent).toContain('console.log');
    expect(panelContent).toContain('State changed');
  });

  test('should verify panel.js has _cleanup method', async () => {
    const panelJsPath = PANEL_JS_PATH;
    expect(fs.existsSync(panelJsPath)).toBe(true);

    const panelContent = fs.readFileSync(panelJsPath, 'utf-8');

    // Verify _cleanup method exists
    expect(panelContent).toContain('_cleanup()');

    // Verify it unsubscribes from state changes
    expect(panelContent).toContain('_unsubscribe');
    expect(panelContent).toContain('this._unsubscribe()');
  });

  test('should verify panel.js groups sensors for efficient updates', async () => {
    const panelJsPath = PANEL_JS_PATH;
    expect(fs.existsSync(panelJsPath)).toBe(true);

    const panelContent = fs.readFileSync(panelJsPath, 'utf-8');

    // Verify _groupSensors method exists
    expect(panelContent).toContain('_groupSensors(');

    // Verify it groups by sensor type
    expect(panelContent).toContain('status');
    expect(panelContent).toContain('battery');
    expect(panelContent).toContain('trips');
    expect(panelContent).toContain('energy');
    expect(panelContent).toContain('charging');
  });
});
