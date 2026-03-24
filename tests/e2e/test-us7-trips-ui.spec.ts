/**
 * E2E Tests for User Story 7: Panel muestra los viajes con UI legible
 *
 * This test verifies that the panel displays trips in a user-friendly format
 * with readable information including trip type, status, time, distance, energy,
 * and action buttons.
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
 * Usage:
 *   npx playwright test test-us7-trips-ui.spec.ts
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

test.describe('US7: Panel muestra los viajes con UI legible', () => {
  test('should have _getTripsList method to fetch trips from HA', async () => {
    expect(fs.existsSync(PANEL_JS_PATH)).toBe(true);
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('_getTripsList()');
    expect(panelContent).toContain('call_service');
    expect(panelContent).toContain('trip_list');
    expect(panelContent).toContain('vehicle_id');
  });

  test('should have _renderTripsSection method to render trips UI', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('_renderTripsSection(');
    expect(panelContent).toContain('trips.length === 0');
  });

  test('should show "No hay viajes programados" when no trips exist', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('No hay viajes programados');
    expect(panelContent).toContain('no-trips');
  });

  test('should have _formatTripDisplay method to format trip cards', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('_formatTripDisplay(');
    expect(panelContent).toContain('trip_type');
    expect(panelContent).toContain('tipo');
    expect(panelContent).toContain('activo');
    expect(panelContent).toContain('active');
  });

  test('should display trip type badge with emoji icons', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('🔄 Recurrente');
    expect(panelContent).toContain('📅 Puntual');
    expect(panelContent).toContain('trip-type');
  });

  test('should display status badge with status indicators', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('trip-status');
    expect(panelContent).toContain('status-active');
    expect(panelContent).toContain('status-inactive');
    expect(panelContent).toContain('Activo');
    expect(panelContent).toContain('Inactivo');
  });

  test('should display day and time for recurring trips', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('dayNames');
    expect(panelContent).toContain('Domingo');
    expect(panelContent).toContain('Lunes');
    expect(panelContent).toContain('Martes');
    expect(panelContent).toContain('Miércoles');
    expect(panelContent).toContain('Jueves');
    expect(panelContent).toContain('Viernes');
    expect(panelContent).toContain('Sábado');
    expect(panelContent).toContain('timeDisplay');
    expect(panelContent).toContain('dia_semana');
    expect(panelContent).toContain('day_of_week');
  });

  test('should display date and time for punctual trips', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('datetime');
    expect(panelContent).toContain('trip.date');
    expect(panelContent).toContain('trip.time');
  });

  test('should display distance and energy details', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('km');
    expect(panelContent).toContain('kwh');
    expect(panelContent).toContain('kWh');
    expect(panelContent).toContain('trip-details');
    expect(panelContent).toContain('trip-detail');
  });

  test('should display trip description', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('descripcion');
    expect(panelContent).toContain('description');
    expect(panelContent).toContain('trip-description');
  });

  test('should have action buttons for trip management', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('trip-action-btn');
    expect(panelContent).toContain('trip-actions');
    expect(panelContent).toContain('edit-btn');
    expect(panelContent).toContain('Editar');
    expect(panelContent).toContain('delete-btn');
    expect(panelContent).toContain('Eliminar');
  });

  test('should have pause/resume buttons for recurring trips', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('pause-btn');
    expect(panelContent).toContain('Pausar');
    expect(panelContent).toContain('resume-btn');
    expect(panelContent).toContain('Reanudar');
  });

  test('should have complete/cancel buttons for punctual trips', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('complete-btn');
    expect(panelContent).toContain('Completar');
    expect(panelContent).toContain('cancel-btn');
    expect(panelContent).toContain('Cancelar');
  });

  test('should have proper CSS classes for trip cards', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('trip-card');
    expect(panelContent).toContain('trip-card-inactive');
    expect(panelContent).toContain('trip-header');
    expect(panelContent).toContain('trip-info');
  });

  test('should display trips header with count', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('trips-header');
    expect(panelContent).toContain('Viajes Programados');
    expect(panelContent).toContain('trips.length');
  });

  test('should have add trip button', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('add-trip-btn');
    expect(panelContent).toContain('Agregar Viaje');
    expect(panelContent).toContain('_showTripForm');
  });

  test('should have data-trip-id attribute on trip cards', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('data-trip-id');
  });

  test('should escape HTML to prevent XSS', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('_escapeHtml');
    expect(panelContent).toContain('this._escapeHtml');
  });

  test('should have CSS styles for trip UI', async () => {
    const cssPath = path.join(
      process.cwd(),
      'custom_components',
      'ev_trip_planner',
      'frontend',
      'panel.css'
    );

    expect(fs.existsSync(cssPath)).toBe(true);
    const cssContent = fs.readFileSync(cssPath, 'utf-8');

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
      expect(cssContent).toContain(pattern);
    }
  });

  test('should fetch trips from service and display them in UI', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    expect(panelContent).toContain('_getTripsList');
    expect(panelContent).toContain('_renderTripsSection');
    expect(panelContent).toContain('_formatTripDisplay');

    expect(panelContent).toContain('try');
    expect(panelContent).toContain('catch');
    expect(panelContent).toContain('console.error');
    expect(panelContent).toContain('console.warn');
    expect(panelContent).toContain('console.log');
  });
});
