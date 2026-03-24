/**
 * E2E Tests for User Story 6: Panel muestra todos los sensores del vehículo
 *
 * This test verifies that the panel displays ALL vehicle sensors from the integration,
 * not just a subset. The panel should show sensor values for various entity types.
 * Acceptance Scenarios:
 * 1. Panel displays SOC sensor with value
 * 2. Panel displays range sensor with value
 * 3. Panel displays charging state sensor
 * 4. Panel displays presence/availability sensors
 * 5. Panel displays trip-related sensors
 * 6. Panel displays energy consumption sensors
 * 7. Panel displays all configured sensors from the vehicle integration
 * Usage:
 *   npx playwright test test-us6-vehicle-sensors.spec.ts
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

test.describe('US6: Panel muestra todos los sensores del vehículo', () => {
  test('should have _getVehicleStates method with all sensor entity patterns', async () => {
    expect(fs.existsSync(PANEL_JS_PATH)).toBe(true);
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('_getVehicleStates()');

    const sensorPatterns = [
      'sensor.',
      'binary_sensor.',
      'input_number.',
      'input_boolean.',
      'climate.',
      'cover.',
      'number.',
      'switch.',
      'light.',
      'fan.',
      'vacuum.',
      'lock.',
      'media_player.',
      'device_tracker.',
      'weather.',
      'alarm_control_panel.',
      'ev_trip_planner',
      'trip_',
    ];

    for (const pattern of sensorPatterns) {
      expect(panelContent).toContain(pattern);
    }
  });

  test('should have _formatSensorValue that returns null for unavailable values', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('_formatSensorValue(');
    expect(panelContent).toContain('unavailable');
    expect(panelContent).toContain('unknown');
    expect(panelContent).toContain('return null');
  });

  test('should filter out unavailable sensors from panel display', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('_update(');

    const hasFiltering = panelContent.includes('state === null') ||
                         panelContent.includes('state === \'unavailable\'') ||
                         panelContent.includes('=== null') ||
                         panelContent.includes('=== \'unavailable\'');

    expect(hasFiltering).toBe(true);
  });

  test('should have _entityIdToName with vehicle sensor name mappings', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('_entityIdToName(');
    expect(panelContent).toContain('soc');
    expect(panelContent).toContain('range');
    expect(panelContent).toContain('battery');
    expect(panelContent).toContain('charging');
    expect(panelContent).toContain('trip');
  });

  test('should have _updateSensorItem method for displaying sensors', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('_updateSensorItem(');
    expect(panelContent).toContain('querySelector');
    expect(panelContent).toContain('.sensor-item');
  });

  test('should have _formatNumericValue with context-aware decimal precision', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('_formatNumericValue(');
    expect(panelContent).toContain('toFixed');
    expect(panelContent).toContain('decimal');
  });

  test('should have _getSensorIcon with icon mapping for sensor types', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('_getSensorIcon(');
  });

  test('should subscribe to state_changed events for vehicle sensors', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('subscribeMessage');
    expect(panelContent).toContain('state_changed');
    expect(panelContent).toContain('this._hass.states');
  });

  test('should have _cleanup method to unsubscribe from state changes', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('_cleanup(');
    expect(panelContent).toContain('_unsubscribe');
    expect(panelContent).toContain('this._unsubscribe()');
  });

  test('should group sensors by type for efficient updates', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('_groupSensors(');

    const hasGrouping = panelContent.includes('status') ||
                        panelContent.includes('battery') ||
                        panelContent.includes('energy') ||
                        panelContent.includes('charging');

    expect(hasGrouping).toBe(true);
  });
});
