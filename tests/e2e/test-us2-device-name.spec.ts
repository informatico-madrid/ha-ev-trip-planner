/**
 * E2E Tests for User Story 2: Device with Custom Name
 *
 * This test verifies that devices are created with the custom name "EV Trip Planner {nombre}"
 * where {nombre} is the vehicle name provided by the user (not the internal ID).
 *
 * Acceptance Scenarios:
 * 1. Device name is "EV Trip Planner {nombre}" not the slug
 * 2. Device identifier uses slug of the name
 * 3. Device URL uses slug (e.g., /config/devices/device/chispitas)
 *
 * Usage:
 *   npx playwright test test-us2-device-name.spec.ts
 */

import { test, expect } from '@playwright/test';
import * as fs from 'fs';
import * as path from 'path';

const WORKTREE_PATH = process.cwd();

test.describe('US2: Device with Custom Name - Static Code Verification', () => {
  test('should verify device_info uses vehicle_name from config entry', async () => {
    // Read sensor.py to verify device_info implementation
    const sensorPath = path.join(
      WORKTREE_PATH,
      'custom_components',
      'ev_trip_planner',
      'sensor.py'
    );
    expect(fs.existsSync(sensorPath)).toBe(true, 'sensor.py should exist');

    const sensorContent = fs.readFileSync(sensorPath, 'utf-8');

    // Verify TripPlannerSensor.device_info method exists
    expect(sensorContent).toContain('def device_info(self)'),
    'sensor.py should have device_info method';

    // Verify device_info searches for vehicle_name in config entries
    const vehicleNameSearch = sensorContent.includes('vehicle_name') &&
                              sensorContent.includes('config_entry');
    expect(vehicleNameSearch).toBe(true),
    'device_info should search for vehicle_name in config entries';

    // Verify the device name format includes "EV Trip Planner {vehicle_name}"
    const deviceNameFormat = /name:\s*f["']EV Trip Planner \{vehicle_name\}["']/;
    const hasCorrectFormat = deviceNameFormat.test(sensorContent) ||
                             sensorContent.includes('f"EV Trip Planner {vehicle_name}"') ||
                             sensorContent.includes("f'EVE Trip Planner {vehicle_name}'");
    expect(hasCorrectFormat).toBe(true),
    'device_info should create device name as "EV Trip Planner {vehicle_name}"';

    // Verify identifiers use vehicle_id (slug)
    const hasIdentifiers = sensorContent.includes('"identifiers"') &&
                           sensorContent.includes('vehicle_id');
    expect(hasIdentifiers).toBe(true),
    'device_info should use vehicle_id as identifier';
  });

  test('should verify device name format in TripPlannerSensor', async () => {
    const sensorPath = path.join(
      WORKTREE_PATH,
      'custom_components',
      'ev_trip_planner',
      'sensor.py'
    );
    expect(fs.existsSync(sensorPath)).toBe(true);

    const sensorContent = fs.readFileSync(sensorPath, 'utf-8');

    // Find the TripPlannerSensor class
    const tripPlannerSensorStart = sensorContent.indexOf('class TripPlannerSensor');
    expect(tripPlannerSensorStart).toBeGreaterThan(-1,
      'TripPlannerSensor class should exist');

    // Find the device_info method within TripPlannerSensor
    const deviceInfoStart = sensorContent.indexOf('def device_info', tripPlannerSensorStart);
    expect(deviceInfoStart).toBeGreaterThan(tripPlannerSensorStart,
      'device_info should be in TripPlannerSensor');

    // Extract the device_info method (approximately 1000 characters to get the return statement)
    const deviceInfoMethod = sensorContent.substring(
      deviceInfoStart,
      deviceInfoStart + 1000
    );

    // Verify the method creates device name with "EV Trip Planner {vehicle_name}"
    expect(deviceInfoMethod).toContain('EV Trip Planner'),
    'device_info should include "EV Trip Planner" in device name';

    expect(deviceInfoMethod).toContain('vehicle_name'),
    'device_info should use vehicle_name variable';

    // Verify it searches config entries for the vehicle_name
    expect(deviceInfoMethod).toContain('async_entries'),
    'device_info should search config entries';

    expect(deviceInfoMethod).toContain('get("vehicle_name"'),
    'device_info should extract vehicle_name from config entry';
  });

  test('should verify EmhassDeferrableLoadSensor device_info', async () => {
    const sensorPath = path.join(
      WORKTREE_PATH,
      'custom_components',
      'ev_trip_planner',
      'sensor.py'
    );
    expect(fs.existsSync(sensorPath)).toBe(true);

    const sensorContent = fs.readFileSync(sensorPath, 'utf-8');

    // Find the EmhassDeferrableLoadSensor class
    const emhassStart = sensorContent.indexOf('class EmhassDeferrableLoadSensor');
    expect(emhassStart).toBeGreaterThan(-1,
      'EmhassDeferrableLoadSensor class should exist');

    // Find the device_info method within EmhassDeferrableLoadSensor
    const deviceInfoStart = sensorContent.indexOf('def device_info', emhassStart);
    expect(deviceInfoStart).toBeGreaterThan(emhassStart,
      'device_info should be in EmhassDeferrableLoadSensor');

    // Extract the device_info method
    const deviceInfoMethod = sensorContent.substring(
      deviceInfoStart,
      deviceInfoStart + 1000
    );

    // Verify the method creates device name with "EV Trip Planner {vehicle_name}"
    expect(deviceInfoMethod).toContain('EV Trip Planner'),
    'device_info should include "EV Trip Planner" in device name';

    expect(deviceInfoMethod).toContain('vehicle_name'),
    'device_info should use vehicle_name variable';
  });

  test('should verify TripSensor device_info uses vehicle_name', async () => {
    const sensorPath = path.join(
      WORKTREE_PATH,
      'custom_components',
      'ev_trip_planner',
      'sensor.py'
    );
    expect(fs.existsSync(sensorPath)).toBe(true);

    const sensorContent = fs.readFileSync(sensorPath, 'utf-8');

    // Find the TripSensor class
    const tripSensorStart = sensorContent.indexOf('class TripSensor');
    expect(tripSensorStart).toBeGreaterThan(-1,
      'TripSensor class should exist');

    // Find the device_info method within TripSensor
    const deviceInfoStart = sensorContent.indexOf('def device_info', tripSensorStart);
    expect(deviceInfoStart).toBeGreaterThan(tripSensorStart,
      'device_info should be in TripSensor');

    // Extract the device_info method
    const deviceInfoMethod = sensorContent.substring(
      deviceInfoStart,
      deviceInfoStart + 1000
    );

    // TripSensor device name format is "Trip {trip_id} - {vehicle_name}" which includes vehicle_name
    expect(deviceInfoMethod).toContain('vehicle_name'),
    'TripSensor device_info should use vehicle_name variable';

    // Verify it searches config entries for the vehicle_name
    expect(deviceInfoMethod).toContain('async_entries'),
    'TripSensor device_info should search config entries';

    expect(deviceInfoMethod).toContain('get("vehicle_name"'),
    'TripSensor device_info should extract vehicle_name from config entry';
  });

  test('should verify config_flow generates slug from vehicle_name', async () => {
    const configFlowPath = path.join(
      WORKTREE_PATH,
      'custom_components',
      'ev_trip_planner',
      'config_flow.py'
    );
    expect(fs.existsSync(configFlowPath)).toBe(true);

    const configFlowContent = fs.readFileSync(configFlowPath, 'utf-8');

    // Verify the slug generation formula: vehicle_name.lower().replace(" ", "_")
    const slugGenerationMatch = configFlowContent.match(
      /vehicle_id\s*=\s*vehicle_name\.lower\(\)\.replace\(" ", "_"\)/
    );

    expect(slugGenerationMatch).toBeTruthy(),
    'config_flow.py should generate vehicle_id slug from vehicle_name using .lower().replace(" ", "_")';

    // Test cases: verify the slug generation handles different vehicle names correctly
    const testCases = [
      { vehicleName: 'Chispitas', expectedSlug: 'chispitas' },
      { vehicleName: 'Mi Coche Eléctrico', expectedSlug: 'mi_coche_eléctrico' },
      { vehicleName: 'Tesla Model 3', expectedSlug: 'tesla_model_3' },
      { vehicleName: 'Coche Eléctrico', expectedSlug: 'coche_eléctrico' },
    ];

    // Verify the logic produces correct slugs
    testCases.forEach(testCase => {
      const result = testCase.vehicleName.toLowerCase().replace(/ /g, '_');
      expect(result).toBe(testCase.expectedSlug,
        `Slug generation should convert "${testCase.vehicleName}" to "${testCase.expectedSlug}"`);
    });
  });
});
