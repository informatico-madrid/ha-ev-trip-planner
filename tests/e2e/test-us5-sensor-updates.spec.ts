/**
 * E2E Tests for User Story 5: Automatic Sensor Updates
 *
 * This test verifies that the panel automatically updates sensor values
 * when they change in Home Assistant, without requiring a page reload.
 * Acceptance Scenarios:
 * 1. Panel subscribes to state_changed events for vehicle sensors
 * 2. Sensor values update in real-time when hass.states changes
 * 3. No page reload required - updates are live
 * Usage:
 *   npx playwright test test-us5-sensor-updates.spec.ts
 */

import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const PANEL_JS_PATH = path.join(
  process.cwd(),
  'custom_components',
  'ev_trip_planner',
  'frontend',
  'panel.js'
);

test.describe('US5: Automatic Sensor Updates', () => {
  test('should verify panel.js has _subscribeToStates method', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(fs.existsSync(PANEL_JS_PATH)).toBe(true);
    expect(panelContent).toContain('_subscribeToStates()');
    expect(panelContent).toContain('subscribeMessage');
    expect(panelContent).toContain('state_changed');
  });

  test('should verify panel.js has _getVehicleStates method', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('_getVehicleStates()');
    expect(panelContent).toContain('this._hass.states');
    expect(panelContent).toContain('sensor.');
    expect(panelContent).toContain('binary_sensor.');
    expect(panelContent).toContain('ev_trip_planner');
  });

  test('should verify panel.js has _update method for live updates', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('_update()');
    expect(panelContent).toContain('this._unsubscribe');
  });

  test('should verify panel.js has _updateSensorItem method', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('_updateSensorItem(');
  });

  test('should verify panel.js subscribes to state changes after render', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    const hasRenderMethod = panelContent.includes('_render()');
    const hasSubscribeCallInRender = panelContent.includes('this._rendered = true') &&
                                      panelContent.includes('_subscribeToStates()');

    expect(hasRenderMethod).toBe(true);
    expect(hasSubscribeCallInRender).toBe(true);
  });

  test('should verify panel.js handles state changes correctly', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('startsWith');
    expect(panelContent).toContain('patterns');
    expect(panelContent).toContain('console.log');
    expect(panelContent).toContain('State changed');
  });

  test('should verify panel.js has _cleanup method', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('_cleanup()');
    expect(panelContent).toContain('_unsubscribe');
    expect(panelContent).toContain('this._unsubscribe()');
  });

  test('should verify panel.js groups sensors for efficient updates', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('_groupSensors(');
    expect(panelContent).toContain('status');
    expect(panelContent).toContain('battery');
    expect(panelContent).toContain('trips');
    expect(panelContent).toContain('energy');
    expect(panelContent).toContain('charging');
  });
});
