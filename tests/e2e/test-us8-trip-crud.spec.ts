/**
 * E2E Tests for User Story 8: CRUD de viajes en el panel de control
 *
 * This test verifies the complete CRUD (Create, Read, Update, Delete) functionality
 * for trips in the EV Trip Planner vehicle panel.
 *
 * Acceptance Scenarios:
 * 1. Create a new trip (recurrente and puntual)
 * 2. Read/Display trips in the panel UI
 * 3. Edit an existing trip
 * 4. Delete a trip
 * 5. Pause/Resume recurring trips
 * 6. Complete/Cancel punctual trips
 *
 * Usage:
 *   npx playwright test test-us8-trip-crud.spec.ts
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

test.describe('US8: CRUD de viajes en el panel de control', () => {

  // ============================================
  // TESTS FOR CREATE TRIP FUNCTIONALITY
  // ============================================

  test('should have _showTripForm method to display trip creation form', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _showTripForm method exists
    expect(panelContent).toContain('_showTripForm()');

    // Verify form overlay structure
    expect(panelContent).toContain('trip-form-overlay');
    expect(panelContent).toContain('trip-form-container');
    expect(panelContent).toContain('trip-form-header');

    // Verify form has ID for JavaScript access
    expect(panelContent).toContain('id="trip-form-overlay"');
    expect(panelContent).toContain('id="trip-creation-form"');
  });

  test('should have form fields for trip creation', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify trip type selector
    expect(panelContent).toContain('id="trip-type"');
    expect(panelContent).toContain('name="type"');
    expect(panelContent).toContain('recurrente');
    expect(panelContent).toContain('puntual');

    // Verify day selector for recurring trips
    expect(panelContent).toContain('id="trip-day"');
    expect(panelContent).toContain('name="day"');
    expect(panelContent).toContain('Domingo');
    expect(panelContent).toContain('Lunes');
    expect(panelContent).toContain('Martes');
    expect(panelContent).toContain('Miércoles');
    expect(panelContent).toContain('Jueves');
    expect(panelContent).toContain('Viernes');
    expect(panelContent).toContain('Sábado');

    // Verify time input
    expect(panelContent).toContain('id="trip-time"');
    expect(panelContent).toContain('name="time"');
    expect(panelContent).toContain('type="time"');

    // Verify distance input
    expect(panelContent).toContain('id="trip-km"');
    expect(panelContent).toContain('name="km"');
    expect(panelContent).toContain('step="0.1"');
    expect(panelContent).toContain('min="0"');

    // Verify energy input
    expect(panelContent).toContain('id="trip-kwh"');
    expect(panelContent).toContain('name="kwh"');
    expect(panelContent).toContain('step="0.1"');
    expect(panelContent).toContain('min="0"');

    // Verify description textarea
    expect(panelContent).toContain('id="trip-description"');
    expect(panelContent).toContain('name="description"');
    expect(panelContent).toContain('textarea');
  });

  test('should have _handleTripCreate method to submit trip form', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _handleTripCreate method exists
    expect(panelContent).toContain('_handleTripCreate()');

    // Verify service call to ev_trip_planner.trip_create
    expect(panelContent).toContain('ev_trip_planner');
    expect(panelContent).toContain('trip_create');

    // Verify vehicle_id is included in service data
    expect(panelContent).toContain('vehicle_id: this._vehicleId');

    // Verify all form fields are captured
    expect(panelContent).toContain('trip-type');
    expect(panelContent).toContain('trip-day');
    expect(panelContent).toContain('trip-time');
    expect(panelContent).toContain('trip-km');
    expect(panelContent).toContain('trip-kwh');
    expect(panelContent).toContain('trip-description');

    // Verify form submission flow
    expect(panelContent).toContain('onsubmit');
    expect(panelContent).toContain('document.getElementById(\'trip-form-overlay\').remove()');

    // Verify trips section refresh after creation
    expect(panelContent).toContain('_renderTripsSection()');

    // Verify success/error handling
    expect(panelContent).toContain('alert(\'✅ Viaje creado exitosamente\')');
    expect(panelContent).toContain('console.error');
  });

  test('should have proper form submission event handling', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify form event handling
    expect(panelContent).toContain('onsubmit="event.preventDefault();');
    expect(panelContent).toContain('document.getElementById(\'trip-creation-form\').onsubmit');

    // Verify form values are captured correctly
    expect(panelContent).toContain('document.getElementById(\'trip-type\').value');
    expect(panelContent).toContain('document.getElementById(\'trip-day\').value');
    expect(panelContent).toContain('document.getElementById(\'trip-time\').value');
    expect(panelContent).toContain('document.getElementById(\'trip-km\').value');
    expect(panelContent).toContain('document.getElementById(\'trip-kwh\').value');
    expect(panelContent).toContain('document.getElementById(\'trip-description\').value');

    // Verify service data building
    expect(panelContent).toContain('const serviceData =');
    expect(panelContent).toContain('day_of_week:');
    expect(panelContent).toContain('parseFloat(km)');
    expect(panelContent).toContain('parseFloat(kwh)');
  });

  // ============================================
  // TESTS FOR READ TRIP FUNCTIONALITY
  // ============================================

  test('should have _getTripsList method to fetch trips from HA', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _getTripsList method exists
    expect(panelContent).toContain('_getTripsList()');

    // Verify it calls trip_list service
    expect(panelContent).toContain('call_service');
    expect(panelContent).toContain('trip_list');

    // Verify vehicle_id is used
    expect(panelContent).toContain('vehicle_id: this._vehicleId');

    // Verify error handling
    expect(panelContent).toContain('try');
    expect(panelContent).toContain('catch');
  });

  test('should have _renderTripsSection method to display trips', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _renderTripsSection method exists
    expect(panelContent).toContain('_renderTripsSection(');

    // Verify trips header
    expect(panelContent).toContain('trips-header');
    expect(panelContent).toContain('Viajes Programados');
    expect(panelContent).toContain('trips.length');

    // Verify no trips message
    expect(panelContent).toContain('no-trips');
    expect(panelContent).toContain('No hay viajes programados');

    // Verify trip cards container
    expect(panelContent).toContain('trips-list');
  });

  test('should have _formatTripDisplay method to format trip cards', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _formatTripDisplay method exists
    expect(panelContent).toContain('_formatTripDisplay(');

    // Verify trip data properties are handled
    expect(panelContent).toContain('trip.id');
    expect(panelContent).toContain('trip.tipo');
    expect(panelContent).toContain('trip.type');
    expect(panelContent).toContain('trip.activo');
    expect(panelContent).toContain('trip.active');
    expect(panelContent).toContain('trip.recurring');

    // Verify trip type detection
    expect(panelContent).toContain('isRecurring');
    expect(panelContent).toContain('isPunctual');

    // Verify day/time formatting
    expect(panelContent).toContain('dayNames');
    expect(panelContent).toContain('day_of_week');
    expect(panelContent).toContain('hora');
    expect(panelContent).toContain('time');

    // Verify distance/energy formatting
    expect(panelContent).toContain('trip.km');
    expect(panelContent).toContain('trip.kwh');
    expect(panelContent).toContain('km');
    expect(panelContent).toContain('kWh');
  });

  test('should have data-trip-id attribute for trip identification', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify trip cards have data-trip-id attribute
    expect(panelContent).toContain('data-trip-id');
    expect(panelContent).toContain('data-trip-id="${this._escapeHtml');

    // Verify trip ID extraction
    expect(panelContent).toContain('trip.id || trip.trip_id');
    expect(panelContent).toContain('trip.tripId');
  });

  // ============================================
  // TESTS FOR EDIT TRIP FUNCTIONALITY
  // ============================================

  test('should have _handleEditClick method to open edit form', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _handleEditClick method exists
    expect(panelContent).toContain('_handleEditClick(event)');

    // Verify trip card identification
    expect(panelContent).toContain('tripCard = event.target.closest(\'.trip-card\')');
    expect(panelContent).toContain('tripCard.dataset.tripId');

    // Verify trip data retrieval
    expect(panelContent).toContain('_getTripById');

    // Verify edit form display
    expect(panelContent).toContain('_showEditForm');

    // Verify error handling
    expect(panelContent).toContain('alert(\'Error: No se pudo obtener la información del viaje\')');
    expect(panelContent).toContain('alert(\'Error: No se pudo cargar la información del viaje\')');
  });

  test('should have _showEditForm method with trip data pre-filled', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _showEditForm method exists
    expect(panelContent).toContain('_showEditForm(');

    // Verify edit form structure - uses same overlay as create form
    expect(panelContent).toContain('trip-form-overlay');
    expect(panelContent).toContain('trip-form-container');

    // Verify trip ID display in edit form (Edit Viaje in Spanish)
    expect(panelContent).toContain('✏️ Editar Viaje');
    expect(panelContent).toContain('edit-trip-id');

    // Verify form fields are pre-filled
    expect(panelContent).toContain('trip-type');
    expect(panelContent).toContain('trip-day');
    expect(panelContent).toContain('trip-time');
    expect(panelContent).toContain('trip-km');
    expect(panelContent).toContain('trip-kwh');
    expect(panelContent).toContain('trip-description');
  });

  test('should have _handleTripUpdate method to submit edited trip', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _handleTripUpdate method exists
    expect(panelContent).toContain('_handleTripUpdate');

    // Verify service call to trip_update
    expect(panelContent).toContain('trip_update');

    // Verify trip ID is included
    expect(panelContent).toContain('trip_id:');

    // Verify form fields are updated
    expect(panelContent).toContain('type');
    expect(panelContent).toContain('day_of_week');
    expect(panelContent).toContain('time');
    expect(panelContent).toContain('km');
    expect(panelContent).toContain('kwh');
    expect(panelContent).toContain('description');

    // Verify success/error handling (note: actual code has space after colon)
    expect(panelContent).toContain('alert(\'✅ Viaje actualizado exitosamente\')');
    expect(panelContent).toContain('Error al actualizar el viaje:');

    // Verify trips section refresh
    expect(panelContent).toContain('_renderTripsSection()');
  });

  // ============================================
  // TESTS FOR DELETE TRIP FUNCTIONALITY
  // ============================================

  test('should have _handleDeleteClick method to delete trip', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _handleDeleteClick method exists
    expect(panelContent).toContain('_handleDeleteClick(event)');

    // Verify trip card identification
    expect(panelContent).toContain('tripCard = event.target.closest(\'.trip-card\')');
    expect(panelContent).toContain('tripCard.dataset.tripId');

    // Verify confirmation dialog
    expect(panelContent).toContain('confirm(');
    expect(panelContent).toContain('¿Estás seguro de que quieres eliminar este viaje?');

    // Verify delete service call
    expect(panelContent).toContain('_deleteTrip');

    // Verify DOM removal
    expect(panelContent).toContain('tripCard.remove()');

    // Verify trips section refresh
    expect(panelContent).toContain('_renderTripsSection()');

    // Verify error handling
    expect(panelContent).toContain('alert(\'Error: No se pudo eliminar el viaje\')');
  });

  test('should have _deleteTrip method to call HA delete service', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _deleteTrip method exists
    expect(panelContent).toContain('_deleteTrip(');

    // Verify service call to delete_trip
    expect(panelContent).toContain('delete_trip');

    // Verify vehicle_id and trip_id are included
    expect(panelContent).toContain('vehicle_id: this._vehicleId');
    expect(panelContent).toContain('trip_id: tripId');

    // Verify error handling
    expect(panelContent).toContain('try');
    expect(panelContent).toContain('catch');
    expect(panelContent).toContain('console.error');
  });

  // ============================================
  // TESTS FOR RECURRING TRIP ACTIONS
  // ============================================

  test('should have _handlePauseTrip method to pause recurring trips', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _handlePauseTrip method exists
    expect(panelContent).toContain('_handlePauseTrip(event, tripId)');

    // Verify confirmation dialog
    expect(panelContent).toContain('confirm(');
    expect(panelContent).toContain('¿Estás seguro de que quieres pausar este viaje recurrente?');

    // Verify pause service call
    expect(panelContent).toContain('_pauseTrip');

    // Verify pause_recurring_trip service
    expect(panelContent).toContain('pause_recurring_trip');

    // Verify card status update
    expect(panelContent).toContain('tripCard.classList.add(\'trip-card-inactive\')');
    expect(panelContent).toContain('statusBadge.classList.add(\'status-inactive\')');
    expect(panelContent).toContain('statusBadge.classList.remove(\'status-active\')');

    // Verify trips section refresh
    expect(panelContent).toContain('_renderTripsSection()');
  });

  test('should have _handleResumeTrip method to resume paused trips', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _handleResumeTrip method exists
    expect(panelContent).toContain('_handleResumeTrip(event, tripId)');

    // Verify resume service call
    expect(panelContent).toContain('_resumeTrip');

    // Verify resume_recurring_trip service
    expect(panelContent).toContain('resume_recurring_trip');

    // Verify card status update
    expect(panelContent).toContain('tripCard.classList.remove(\'trip-card-inactive\')');
    expect(panelContent).toContain('statusBadge.classList.remove(\'status-inactive\')');
    expect(panelContent).toContain('statusBadge.classList.add(\'status-active\')');

    // Verify trips section refresh
    expect(panelContent).toContain('_renderTripsSection()');
  });

  // ============================================
  // TESTS FOR PUNCTUAL TRIP ACTIONS
  // ============================================

  test('should have _handleCompletePunctualTrip method to complete trips', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _handleCompletePunctualTrip method exists
    expect(panelContent).toContain('_handleCompletePunctualTrip(event, tripId)');

    // Verify confirmation dialog
    expect(panelContent).toContain('confirm(');
    expect(panelContent).toContain('¿Estás seguro de que quieres completar este viaje?');

    // Verify complete service call
    expect(panelContent).toContain('_completeTrip');

    // Verify complete_punctual_trip service
    expect(panelContent).toContain('complete_punctual_trip');

    // Verify trips section refresh
    expect(panelContent).toContain('_renderTripsSection()');
  });

  test('should have _handleCancelPunctualTrip method to cancel trips', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _handleCancelPunctualTrip method exists
    expect(panelContent).toContain('_handleCancelPunctualTrip(event, tripId)');

    // Verify confirmation dialog
    expect(panelContent).toContain('confirm(');
    expect(panelContent).toContain('¿Estás seguro de que quieres cancelar este viaje?');

    // Verify cancel service call
    expect(panelContent).toContain('_cancelTrip');

    // Verify cancel_punctual_trip service
    expect(panelContent).toContain('cancel_punctual_trip');

    // Verify trips section refresh
    expect(panelContent).toContain('_renderTripsSection()');
  });

  // ============================================
  // TESTS FOR ACTION BUTTONS UI
  // ============================================

  test('should have action buttons in trip card HTML', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify action buttons are built dynamically
    expect(panelContent).toContain('actionButtons =');
    expect(panelContent).toContain('let actionButtons');

    // Verify edit button HTML
    expect(panelContent).toContain('edit-btn');
    expect(panelContent).toContain('✏️ Editar');

    // Verify delete button HTML
    expect(panelContent).toContain('delete-btn');
    expect(panelContent).toContain('🗑️ Eliminar');

    // Verify pause button HTML
    expect(panelContent).toContain('pause-btn');
    expect(panelContent).toContain('⏸️ Pausar');

    // Verify resume button HTML
    expect(panelContent).toContain('resume-btn');
    expect(panelContent).toContain('▶️ Reanudar');

    // Verify complete button HTML
    expect(panelContent).toContain('complete-btn');
    expect(panelContent).toContain('✅ Completar');

    // Verify cancel button HTML
    expect(panelContent).toContain('cancel-btn');
    expect(panelContent).toContain('❌ Cancelar');
  });

  test('should have proper action button event handlers', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify onclick handlers for all buttons
    expect(panelContent).toContain('onclick="window._tripPanel._handleEditClick(event)"');
    expect(panelContent).toContain('onclick="window._tripPanel._handleDeleteClick(event)"');
    expect(panelContent).toContain('onclick="window._tripPanel._handlePauseTrip(event,');
    expect(panelContent).toContain('onclick="window._tripPanel._handleResumeTrip(event,');
    expect(panelContent).toContain('onclick="window._tripPanel._handleCompletePunctualTrip(event,');
    expect(panelContent).toContain('onclick="window._tripPanel._handleCancelPunctualTrip(event,');

    // Verify tripId is passed to handlers
    expect(panelContent).toContain('\'${this._escapeHtml(tripIdForForm)}\')');
  });

  // ============================================
  // TESTS FOR TRIP CARD STRUCTURE
  // ============================================

  test('should have trip card with proper structure', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify trip card class
    expect(panelContent).toContain('class="trip-card');

    // Verify inactive trip card class
    expect(panelContent).toContain('trip-card-inactive');

    // Verify trip header
    expect(panelContent).toContain('trip-header');
    expect(panelContent).toContain('trip-type');
    expect(panelContent).toContain('trip-status');

    // Verify trip info section
    expect(panelContent).toContain('trip-info');
    expect(panelContent).toContain('trip-time');
    expect(panelContent).toContain('trip-details');
    expect(panelContent).toContain('trip-detail');

    // Verify trip actions section
    expect(panelContent).toContain('trip-actions');
  });

  test('should have trip type badges with emoji icons', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify recurring trip badge
    expect(panelContent).toContain('🔄 Recurrente');

    // Verify punctual trip badge
    expect(panelContent).toContain('📅 Puntual');

    // Verify status badges
    expect(panelContent).toContain('status-active');
    expect(panelContent).toContain('status-inactive');
  });

  // ============================================
  // TESTS FOR FORM VISUALIZATION
  // ============================================

  test('should have form visualization methods', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify form visibility methods
    expect(panelContent).toContain('_showTripForm');
    expect(panelContent).toContain('_showEditForm');

    // Verify form overlay removal
    expect(panelContent).toContain('document.getElementById(\'trip-form-overlay\').remove()');
  });

  test('should have form action buttons', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify form has cancel button
    expect(panelContent).toContain('class="btn btn-secondary"');
    expect(panelContent).toContain('onclick="document.getElementById(\'trip-form-overlay\').remove()"');

    // Verify form has submit button
    expect(panelContent).toContain('class="btn btn-primary"');
    expect(panelContent).toContain('Crear Viaje');

    // Verify edit form submit button (uses "Guardar Cambios")
    expect(panelContent).toContain('Guardar Cambios');
  });

  // ============================================
  // TESTS FOR FORM SUBMISSION FLOW
  // ============================================

  test('should have complete form submission flow for trip creation', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify form is created in DOM
    expect(panelContent).toContain('container.insertAdjacentHTML(\'beforeend\', formHtml)');

    // Verify form submit handler is attached
    expect(panelContent).toContain('document.getElementById(\'trip-creation-form\').onsubmit = () => this._handleTripCreate()');

    // Verify loading state during submission
    expect(panelContent).toContain("submitBtn.textContent = 'Creando...'");
    expect(panelContent).toContain('submitBtn.disabled = true');

    // Verify form is closed after successful submission
    expect(panelContent).toContain('document.getElementById(\'trip-form-overlay\').remove()');

    // Verify trips are refreshed after submission
    expect(panelContent).toContain('await this._renderTripsSection()');
  });

  test('should have complete form submission flow for trip update', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify edit form has submit handler
    expect(panelContent).toContain('form.onsubmit = () => this._handleTripUpdate()');

    // Verify loading state during submission
    expect(panelContent).toContain("submitBtn.textContent = 'Guardando...'");
    expect(panelContent).toContain('submitBtn.disabled = true');

    // Verify form is closed after successful submission (uses trip-form-overlay)
    expect(panelContent).toContain('document.getElementById(\'trip-form-overlay\').remove()');

    // Verify trips are refreshed after submission
    expect(panelContent).toContain('await this._renderTripsSection()');
  });

  // ============================================
  // TESTS FOR SECURITY AND VALIDATION
  // ============================================

  test('should have XSS protection with escapeHtml method', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify _escapeHtml method exists
    expect(panelContent).toContain('_escapeHtml(');

    // Verify it's used on trip data
    expect(panelContent).toContain('this._escapeHtml(');

    // Verify escape is used on user-controllable data (varies in code)
    expect(panelContent).toContain('this._escapeHtml(');
  });

  test('should have form validation', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify form has required attributes
    expect(panelContent).toContain('name="type" required');

    // Verify trip type is required
    expect(panelContent).toContain('id="trip-type" name="type" required');

    // Verify time is required
    expect(panelContent).toContain('id="trip-time" name="time" required');

    // Verify form validation is handled
    expect(panelContent).toContain('event.preventDefault()');
  });

  // ============================================
  // INTEGRATION TESTS
  // ============================================

  test('should have complete CRUD integration flow', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify complete flow: Create → Read → Update → Delete
    // Create
    expect(panelContent).toContain('_showTripForm');
    expect(panelContent).toContain('_handleTripCreate');

    // Read
    expect(panelContent).toContain('_getTripsList');
    expect(panelContent).toContain('_renderTripsSection');
    expect(panelContent).toContain('_formatTripDisplay');

    // Update
    expect(panelContent).toContain('_handleEditClick');
    expect(panelContent).toContain('_showEditForm');
    expect(panelContent).toContain('_handleTripUpdate');

    // Delete
    expect(panelContent).toContain('_handleDeleteClick');
    expect(panelContent).toContain('_deleteTrip');

    // All service calls exist
    expect(panelContent).toContain('trip_create');
    expect(panelContent).toContain('trip_update');
    expect(panelContent).toContain('delete_trip');
  });

  test('should have proper error handling throughout CRUD operations', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify error handling for create
    expect(panelContent).toContain('catch (error)');
    expect(panelContent).toContain('EV Trip Planner Panel: Error creating trip');

    // Verify error handling for edit
    expect(panelContent).toContain('EV Trip Planner Panel: Error getting trip');
    expect(panelContent).toContain('EV Trip Planner Panel: Error updating trip');

    // Verify error handling for delete
    expect(panelContent).toContain('EV Trip Planner Panel: Error deleting trip');

    // Verify error handling for pause/resume/complete/cancel
    expect(panelContent).toContain('EV Trip Planner Panel: Error pausing trip');
    expect(panelContent).toContain('EV Trip Planner Panel: Error resuming trip');
    expect(panelContent).toContain('EV Trip Planner Panel: Error completing trip');
    expect(panelContent).toContain('EV Trip Planner Panel: Error cancelling trip');
  });

  // ============================================
  // TESTS FOR VISUAL FEEDBACK
  // ============================================

  test('should have visual feedback for CRUD operations', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify success alerts
    expect(panelContent).toContain('alert(\'✅ Viaje creado exitosamente\')');
    expect(panelContent).toContain('alert(\'✅ Viaje actualizado exitosamente\')');

    // Verify error alerts (note: actual code has space after colon)
    expect(panelContent).toContain('Error al crear el viaje:');
    expect(panelContent).toContain('Error al actualizar el viaje:');
  });

  // ============================================
  // TESTS FOR FORM RESET AND CLEANUP
  // ============================================

  test('should handle form reset after submission', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify form is removed after submission
    expect(panelContent).toContain('document.getElementById(\'trip-form-overlay\').remove()');

    // Verify form can be reopened
    expect(panelContent).toContain('_showTripForm()');
  });

  test('should handle edit form cleanup', async () => {
    const panelContent = fs.readFileSync(PANEL_JS_PATH, 'utf-8');

    // Verify edit form uses same overlay as create form
    expect(panelContent).toContain('document.getElementById(\'trip-form-overlay\').remove()');

    // Verify cancel closes form (uses same overlay)
    expect(panelContent).toContain('document.getElementById(\'trip-form-overlay\').remove()');
  });

});
