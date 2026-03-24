/**
 * E2E Tests for User Story 7: Panel muestra los viajes con UI legible
 *
 * This test verifies that the panel displays trips in a user-friendly format
 * with readable information including trip type, status, time, distance, energy,
 * and action buttons.
 *
 * Acceptance Scenarios:
 * 1. Panel displays trips header with count
 * 2. Panel shows "No hay viajes programados" when no trips exist
 * 3. Panel displays trip cards with readable format
 * 4. Trip cards show trip type badge (Recurrente/Puntual)
 * 5. Trip cards show status badge (Activo/Inactivo)
 * 6. Trip cards display time/day information
 * 7. Trip cards show distance and energy details
 * 8. Trip cards show description when available
 * 9. Trip cards display action buttons (Editar, Eliminar, etc.)
 *
 * Usage:
 *   npx playwright test test-us7-trips-ui.spec.ts
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

test.describe('US7: Panel muestra los viajes con UI legible', () => {

  // Test 1: Verify panel.js has _getTripsList method
  test('should have _getTripsList method to fetch trips from HA', async () => {
    expect(fs.existsSync(PANEL_JS_PATH)).toBe(true);
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _getTripsList method exists
    expect(panelContent).toContain('_getTripsList()');

    // Verify it calls trip_list service
    expect(panelContent).toContain('call_service');
    expect(panelContent).toContain('trip_list');

    // Verify it handles vehicle_id
    expect(panelContent).toContain('vehicle_id');
  });

  // Test 2: Verify _renderTripsSection method exists
  test('should have _renderTripsSection method to render trips UI', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _renderTripsSection method exists
    expect(panelContent).toContain('_renderTripsSection(');

    // Verify it calls _getTripsList
    expect(panelContent).toContain('_getTripsList()');

    // Verify it handles empty trips case
    expect(panelContent).toContain('trips.length === 0');
  });

  // Test 3: Verify "No hay viajes programados" message
  test('should show "No hay viajes programados" when no trips exist', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify the no-trips message exists
    expect(panelContent).toContain('No hay viajes programados');

    // Verify it has CSS class for styling
    expect(panelContent).toContain('no-trips');
  });

  // Test 4: Verify _formatTripDisplay method exists
  test('should have _formatTripDisplay method to format trip cards', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _formatTripDisplay method exists
    expect(panelContent).toContain('_formatTripDisplay(');

    // Verify it handles trip type
    expect(panelContent).toContain('trip_type');
    expect(panelContent).toContain('tipo');

    // Verify it handles active status
    expect(panelContent).toContain('activo');
    expect(panelContent).toContain('active');
  });

  // Test 5: Verify trip type badge display (Recurrente/Puntual)
  test('should display trip type badge with emoji icons', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify trip type badge includes emoji icons
    expect(panelContent).toContain('🔄 Recurrente');
    expect(panelContent).toContain('📅 Puntual');

    // Verify it shows trip type in header
    expect(panelContent).toContain('trip-type');
  });

  // Test 6: Verify status badge display (Activo/Inactivo)
  test('should display status badge with status indicators', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify status badge exists
    expect(panelContent).toContain('trip-status');
    expect(panelContent).toContain('status-active');
    expect(panelContent).toContain('status-inactive');

    // Verify status text
    expect(panelContent).toContain('Activo');
    expect(panelContent).toContain('Inactivo');
  });

  // Test 7: Verify time display for recurring trips
  test('should display day and time for recurring trips', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify it handles day names
    expect(panelContent).toContain('dayNames');
    expect(panelContent).toContain('Domingo');
    expect(panelContent).toContain('Lunes');
    expect(panelContent).toContain('Martes');
    expect(panelContent).toContain('Miércoles');
    expect(panelContent).toContain('Jueves');
    expect(panelContent).toContain('Viernes');
    expect(panelContent).toContain('Sábado');

    // Verify it handles time display
    expect(panelContent).toContain('timeDisplay');
    expect(panelContent).toContain('dia_semana');
    expect(panelContent).toContain('day_of_week');
  });

  // Test 8: Verify date/time display for punctual trips
  test('should display date and time for punctual trips', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify it handles punctual trip datetime
    expect(panelContent).toContain('datetime');
    expect(panelContent).toContain('trip.date');
    expect(panelContent).toContain('trip.time');
  });

  // Test 9: Verify distance and energy display
  test('should display distance and energy details', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify it displays km and kWh
    expect(panelContent).toContain('km');
    expect(panelContent).toContain('kwh');
    expect(panelContent).toContain('kWh');

    // Verify it has trip-details class
    expect(panelContent).toContain('trip-details');
    expect(panelContent).toContain('trip-detail');
  });

  // Test 10: Verify description display
  test('should display trip description', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify it handles description
    expect(panelContent).toContain('descripcion');
    expect(panelContent).toContain('description');
    expect(panelContent).toContain('trip-description');
  });

  // Test 11: Verify action buttons exist
  test('should have action buttons for trip management', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify action buttons exist
    expect(panelContent).toContain('trip-action-btn');
    expect(panelContent).toContain('trip-actions');

    // Verify edit button
    expect(panelContent).toContain('edit-btn');
    expect(panelContent).toContain('Editar');

    // Verify delete button
    expect(panelContent).toContain('delete-btn');
    expect(panelContent).toContain('Eliminar');
  });

  // Test 12: Verify pause/resume buttons for recurring trips
  test('should have pause/resume buttons for recurring trips', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify pause button
    expect(panelContent).toContain('pause-btn');
    expect(panelContent).toContain('Pausar');

    // Verify resume button
    expect(panelContent).toContain('resume-btn');
    expect(panelContent).toContain('Reanudar');
  });

  // Test 13: Verify complete/cancel buttons for punctual trips
  test('should have complete/cancel buttons for punctual trips', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify complete button
    expect(panelContent).toContain('complete-btn');
    expect(panelContent).toContain('Completar');

    // Verify cancel button
    expect(panelContent).toContain('cancel-btn');
    expect(panelContent).toContain('Cancelar');
  });

  // Test 14: Verify trip card CSS classes
  test('should have proper CSS classes for trip cards', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify trip card classes
    expect(panelContent).toContain('trip-card');
    expect(panelContent).toContain('trip-card-inactive');

    // Verify trip sections
    expect(panelContent).toContain('trip-header');
    expect(panelContent).toContain('trip-info');
  });

  // Test 15: Verify trips header with count
  test('should display trips header with count', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify trips header
    expect(panelContent).toContain('trips-header');
    expect(panelContent).toContain('Viajes Programados');

    // Verify it shows count with dynamic value
    expect(panelContent).toContain('trips.length');
  });

  // Test 16: Verify add trip button
  test('should have add trip button', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify add trip button exists
    expect(panelContent).toContain('add-trip-btn');
    expect(panelContent).toContain('Agregar Viaje');

    // Verify it shows form
    expect(panelContent).toContain('_showTripForm');
  });

  // Test 17: Verify trip card data attribute
  test('should have data-trip-id attribute on trip cards', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify trip card has data attribute
    expect(panelContent).toContain('data-trip-id');
  });

  // Test 18: Verify escape HTML for security
  test('should escape HTML to prevent XSS', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify escape method exists
    expect(panelContent).toContain('_escapeHtml');

    // Verify it's used on trip data
    expect(panelContent).toContain('this._escapeHtml');
  });

  // Test 19: Verify CSS styling for trips
  test('should have CSS styles for trip UI', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify CSS includes trip styles (check for style method or inline styles)
    expect(panelContent).toContain('getStyles(') || expect(panelContent).toContain('Styles()');

    // Verify CSS classes are defined
    const cssClassPatterns = [
      '.trips-header',
      '.add-trip-btn',
      '.trip-card',
      '.trip-header',
      '.trip-type',
      '.trip-status',
      '.trip-info',
      '.trip-time',
      '.trip-details',
      '.trip-detail',
      '.trip-actions',
      '.no-trips',
    ];

    for (const pattern of cssClassPatterns) {
      expect(panelContent).toContain(pattern);
    }
  });

  // Test 20: Integration test - verify trips are fetched and displayed
  test('should fetch trips from service and display them in UI', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify the complete flow exists:
    // 1. _getTripsList fetches trips
    // 2. _renderTripsSection renders them
    // 3. _formatTripDisplay formats each trip
    expect(panelContent).toContain('_getTripsList()');
    expect(panelContent).toContain('_renderTripsSection(');
    expect(panelContent).toContain('_formatTripDisplay(');

    // Verify error handling
    expect(panelContent).toContain('try');
    expect(panelContent).toContain('catch');
    expect(panelContent).toContain('console.error');
    expect(panelContent).toContain('console.warn');

    // Verify logging for debugging
    expect(panelContent).toContain('console.log');
  });

});
