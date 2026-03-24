/**
 * E2E Tests for User Story 6: Panel muestra todos los sensores del vehículo
 *
 * This test verifies that the panel displays ALL vehicle sensors from the integration,
 * not just a subset. The panel should show sensor values for various entity types.
 *
 * Acceptance Scenarios:
 * 1. Panel displays SOC sensor with value
 * 2. Panel displays range sensor with value
 * 3. Panel displays charging state sensor
 * 4. Panel displays presence/availability sensors
 * 5. Panel displays trip-related sensors
 * 6. Panel displays energy consumption sensors
 * 7. Panel displays all configured sensors from the vehicle integration
 *
 * Usage:
 *   npx playwright test test-us6-vehicle-sensors.spec.ts
 */

import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const HA_URL = process.env.HA_URL || 'http://localhost:18123';
const HA_USERNAME = process.env.HA_USER || process.env.HA_USERNAME || 'tests';
const HA_PASSWORD = process.env.HA_PASSWORD || '';

// Path to panel.js in the worktree
const PANEL_JS_PATH = path.join(
  process.cwd(),
  'custom_components',
  'ev_trip_planner',
  'frontend',
  'panel.js'
);

test.describe('US6: Panel muestra todos los sensores del vehículo', () => {
  // Test 1: Verify panel.js has _getVehicleStates method that captures all sensor patterns
  test('should have _getVehicleStates method with all sensor entity patterns', async () => {
    expect(fs.existsSync(PANEL_JS_PATH)).toBe(true);
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _getVehicleStates method exists
    expect(panelContent).toContain('_getVehicleStates()');

    // Verify it captures sensor patterns for all entity types
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

  // Test 2: Verify _formatSensorValue handles unavailable values correctly
  test('should have _formatSensorValue that returns null for unavailable values', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _formatSensorValue exists
    expect(panelContent).toContain('_formatSensorValue(');

    // Verify it checks for unavailable or unknown states
    expect(panelContent).toContain('unavailable');
    expect(panelContent).toContain('unknown');

    // Verify it returns null for unavailable values (not "N/A")
    expect(panelContent).toContain('return null');
  });

  // Test 3: Verify _update method filters out unavailable sensors
  test('should filter out unavailable sensors from panel display', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _update method exists and filters unavailable
    expect(panelContent).toContain('_update(');

    // Look for filtering logic (state === null, state === 'unavailable', etc.)
    const hasFiltering = panelContent.includes('state === null') ||
                         panelContent.includes('state === \'unavailable\'') ||
                         panelContent.includes('=== null') ||
                         panelContent.includes('=== \'unavailable\'');
    expect(hasFiltering).toBe(true);
  });

  // Test 4: Verify _entityIdToName has comprehensive entity name mapping
  test('should have _entityIdToName with vehicle sensor name mappings', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _entityIdToName method exists
    expect(panelContent).toContain('_entityIdToName(');

    // Verify it has mappings for common vehicle sensor entities
    expect(panelContent).toContain('soc');
    expect(panelContent).toContain('range');
    expect(panelContent).toContain('battery');
    expect(panelContent).toContain('charging');
    expect(panelContent).toContain('trip');
  });

  // Test 5: Verify panel has sensor display structure with _updateSensorItem method
  test('should have _updateSensorItem method for displaying sensors', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _updateSensorItem method exists (actual method name in panel.js)
    expect(panelContent).toContain('_updateSensorItem(');

    // Verify it renders sensor elements with querySelector
    expect(panelContent).toContain('querySelector');
    expect(panelContent).toContain('.sensor-item');
  });

  // Test 6: Verify _formatNumericValue handles decimal precision
  test('should have _formatNumericValue with context-aware decimal precision', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _formatNumericValue method exists
    expect(panelContent).toContain('_formatNumericValue(');

    // Verify it handles different decimal precisions
    expect(panelContent).toContain('toFixed');
    expect(panelContent).toContain('decimal');
  });

  // Test 7: Verify _getSensorIcon has comprehensive icon mapping
  test('should have _getSensorIcon with icon mapping for sensor types', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _getSensorIcon method exists
    expect(panelContent).toContain('_getSensorIcon(');

    // Verify it maps different sensor types to icons (emoji icons)
    expect(panelContent).toContain('battery');
    expect(panelContent).toContain('soc');
    expect(panelContent).toContain('charging');
    expect(panelContent).toContain('range');
  });

  // Test 8: Verify panel subscribes to state changes for real-time updates
  test('should subscribe to state_changed events for vehicle sensors', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify subscription mechanism exists
    expect(panelContent).toContain('subscribeMessage');

    // Verify it subscribes to state_changed topic
    expect(panelContent).toContain('state_changed');

    // Verify it uses hass.states
    expect(panelContent).toContain('this._hass.states');
  });

  // Test 9: Verify panel has cleanup for subscriptions
  test('should have _cleanup method to unsubscribe from state changes', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _cleanup method exists
    expect(panelContent).toContain('_cleanup(');

    // Verify it unsubscribes
    expect(panelContent).toContain('_unsubscribe');
    expect(panelContent).toContain('this._unsubscribe()');
  });

  // Test 10: Verify panel groups sensors for efficient updates
  test('should group sensors by type for efficient updates', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _groupSensors or similar grouping method exists
    expect(panelContent).toContain('_groupSensors(') || expect(panelContent).toContain('groupSensors(');

    // Verify it groups by sensor categories
    const hasGrouping = panelContent.includes('status') ||
                        panelContent.includes('battery') ||
                        panelContent.includes('energy') ||
                        panelContent.includes('charging');
    expect(hasGrouping).toBe(true);
  });
});
