/**
 * EV Trip Planner Lit Web Component
 *
 * A Lit-based web component that renders the EV Trip Planner dashboard
 * as a native Home Assistant panel (not Lovelace).
 *
 * @version 3.0.14 - CRITICAL FIX: Added missing disconnectedCallback() to prevent blank screen on tab switching
 * @author EV Trip Planner Team
 */

// Debug mode - set to true to enable verbose logging
const DEBUG = false;

// VERSION=3.0.14 UNIQUE_LOG_ID=DISCONNECTED_CALLBACK_FIX_2026-04-18
if (DEBUG) console.log('EV Trip Planner Panel: VERSION=3.0.14 - CRITICAL: Added disconnectedCallback() lifecycle method');

// Cache busting removed - CSS version is now fixed

// Import Lit: prefer local bundle (offline-safe) then fall back to CDN
// The local bundle is served by HA at /ev-trip-planner/lit-bundle.js
// The CDN is used as fallback for production environments that allow outbound traffic
import { LitElement, html, css } from '/ev-trip-planner/lit-bundle.js';

class EVTripPlannerPanel extends LitElement {
  // Lit handles Shadow DOM automatically - no need for attachShadow

  // Reactive properties - Lit manages updates automatically
  static properties = {
    _hass: { type: Object },
    _vehicleId: { type: String },
    _config: { type: Object },
    _rendered: { type: Boolean, value: false },
    _trips: { type: Array, value: [] },
    _isLoading: { type: Boolean, value: true },
    _initAttempts: { type: Number, value: 0 },
    _maxInitAttempts: { type: Number, value: 10 },
    _pollTimeout: { type: Object },
    _pollStarted: { type: Boolean, value: false },
    // Form state
    _showForm: { type: Boolean, value: false },
    _editingTrip: { type: Object, value: null },
    _formType: { type: String, value: 'recurrente' }
  };

  static styles = css`
    /* Styles are centralized in panel.css */
    :host {
      display: block;
    }

    .panel-container {
      font-family: 'Segoe UI', Roboto, sans-serif;
      max-width: 1200px;
      margin: 0 auto;
    }

    .panel-header {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      padding: 20px;
      border-radius: 12px;
      margin-bottom: 20px;
      box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }

    .panel-header h1 {
      margin: 0;
      font-size: 24px;
    }

    .status-section, .sensors-section, .trips-section {
      margin-bottom: 20px;
    }

    .section-title {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 18px;
      font-weight: 600;
      color: #333;
      margin-bottom: 15px;
    }

    .section-icon {
      font-size: 20px;
    }

    .add-trip-btn {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: 8px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 600;
      transition: transform 0.2s, box-shadow 0.2s;
    }

    .add-trip-btn:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }

    .add-trip-btn:active {
      transform: translateY(0);
    }

    .trips-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 15px;
    }

    .no-trips {
      color: #666;
      font-style: italic;
      text-align: center;
      padding: 20px;
    }

    .trips-list {
      display: grid;
      gap: 15px;
    }

    .trip-card {
      background: white;
      border-radius: 12px;
      padding: 15px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      transition: transform 0.2s, box-shadow 0.2s;
    }

    .trip-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
    }

    .trip-card-inactive {
      opacity: 0.7;
    }

    .trip-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }

    .trip-type {
      font-size: 14px;
      font-weight: 600;
      color: #667eea;
    }

    .trip-status {
      padding: 4px 12px;
      border-radius: 20px;
      font-size: 12px;
      font-weight: 600;
    }

    .trip-status.status-active {
      background: #10b981;
      color: white;
    }

    .trip-status.status-inactive {
      background: #ef4444;
      color: white;
    }

    .trip-info {
      margin-bottom: 10px;
    }

    .trip-time {
      font-weight: 600;
      color: #333;
      margin-bottom: 5px;
    }

    .trip-details {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 14px;
      color: #666;
    }

    .trip-detail {
      background: #f3f4f6;
      padding: 4px 8px;
      border-radius: 4px;
    }

    .trip-description {
      font-size: 13px;
      color: #666;
      margin-top: 5px;
      font-style: italic;
    }

    .trip-actions {
      margin-top: 15px;
    }

    .action-group-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .trip-action-group-label {
      font-size: 12px;
      font-weight: 600;
      color: #666;
    }

    .action-buttons-container {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .trip-action-btn {
      background: white;
      border: 1px solid #ddd;
      padding: 6px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 13px;
      transition: all 0.2s;
    }

    .trip-action-btn:hover {
      background: #f3f4f6;
      border-color: #ccc;
    }

    .edit-btn { color: #667eea; }
    .delete-btn { color: #ef4444; }
    .pause-btn { color: #f59e0b; }
    .resume-btn { color: #10b981; }
    .complete-btn { color: #10b981; }
    .cancel-btn { color: #ef4444; }

    .trip-form-overlay {
      position: fixed;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      background: rgba(0, 0, 0, 0.5);
      display: flex;
      align-items: center;
      justify-content: center;
      z-index: 1000;
    }

    .trip-form-container {
      background: white;
      border-radius: 12px;
      padding: 25px;
      max-width: 500px;
      width: 90%;
      max-height: 90vh;
      overflow-y: auto;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
    }

    .trip-form-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 20px;
    }

    .trip-form-header h3 {
      margin: 0;
      font-size: 20px;
      color: #333;
    }

    .close-form-btn {
      background: none;
      border: none;
      font-size: 28px;
      cursor: pointer;
      color: #999;
      padding: 0;
      line-height: 1;
    }

    .close-form-btn:hover {
      color: #333;
    }

    .form-group {
      margin-bottom: 15px;
    }

    .form-group label {
      display: block;
      font-weight: 600;
      margin-bottom: 8px;
      color: #333;
    }

    .form-group select,
    .form-group input,
    .form-group textarea {
      width: 100%;
      padding: 10px;
      border: 1px solid #ddd;
      border-radius: 6px;
      font-size: 14px;
      box-sizing: border-box;
    }

    .form-group textarea {
      resize: vertical;
      min-height: 80px;
    }

    .form-actions {
      display: flex;
      gap: 10px;
      margin-top: 20px;
    }

    .btn {
      padding: 10px 20px;
      border: none;
      border-radius: 6px;
      cursor: pointer;
      font-size: 14px;
      font-weight: 600;
      transition: all 0.2s;
    }

    .btn-primary {
      background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
      color: white;
      flex: 1;
    }

    .btn-primary:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }

    .btn-primary:disabled {
      opacity: 0.5;
      cursor: not-allowed;
      transform: none;
    }

    .btn-secondary {
      background: #f3f4f6;
      color: #333;
    }

    .btn-secondary:hover {
      background: #e5e7eb;
    }

    /* Status cards */
    .status-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 15px;
    }

    .status-card {
      background: white;
      border-radius: 12px;
      padding: 15px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      display: flex;
      align-items: center;
      gap: 12px;
      transition: transform 0.2s, box-shadow 0.2s;
    }

    .status-card:hover {
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    .status-icon {
      font-size: 24px;
    }

    .status-label {
      font-weight: 600;
      color: #333;
      flex: 1;
    }

    .status-value {
      font-weight: 600;
      color: #667eea;
      font-size: 18px;
    }

    /* Sensor list */
    .sensor-list-grouped {
      display: grid;
      gap: 20px;
    }

    .sensor-group {
      background: white;
      border-radius: 12px;
      padding: 15px;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
    }

    .sensor-group-title {
      font-size: 16px;
      font-weight: 600;
      color: #333;
      margin-bottom: 15px;
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .sensor-items-list {
      display: grid;
      gap: 10px;
    }

    .sensor-item {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px;
      background: #f8f9fa;
      border-radius: 8px;
      transition: background 0.2s;
    }

    .sensor-item:hover {
      background: #e9ecef;
    }

    .sensor-left {
      display: flex;
      align-items: center;
      gap: 12px;
      flex: 1;
      min-width: 0;
    }

    .sensor-icon {
      font-size: 20px;
      flex-shrink: 0;
    }

    .sensor-name-container {
      flex: 1;
      min-width: 0;
    }

    .sensor-name {
      display: block;
      font-weight: 600;
      color: #333;
      margin-bottom: 2px;
    }

    .sensor-entity {
      font-size: 12px;
      color: #666;
      font-family: monospace;
    }

    .sensor-right {
      text-align: right;
      flex-shrink: 0;
      margin-left: 15px;
    }

    .sensor-value {
      font-weight: 600;
      color: #667eea;
      font-size: 16px;
    }

    .no-sensors {
      color: #666;
      text-align: center;
      padding: 20px;
    }

    .sensor-entity-id {
      font-size: 11px;
      color: #999;
      margin-top: 4px;
      font-family: monospace;
    }
  `;

  constructor() {
    super();
    console.log('EV Trip Planner Panel: Lit constructor called');
    console.log('EV Trip Planner Panel: VERSION=3.0.12 TIMESTAMP=' + new Date().toISOString());
  }

  /**
   * Connected callback - called when element is added to DOM
   */
  connectedCallback() {
    super.connectedCallback();

    // Detect if this is a reconnection (component already had vehicle_id)
    // Use != null (loose equality) to catch both null AND undefined
    const isReconnection = this._vehicleId != null;

    if (DEBUG) {
      console.log('EV Trip Planner Panel: connectedCallback called',
        isReconnection ? '(reconexión)' : '(primera vez)');
      console.log('EV Trip Planner Panel: full URL:', window.location.href);
      console.log('EV Trip Planner Panel: pathname:', window.location.pathname);
      console.log('EV Trip Planner Panel: hash:', window.location.hash);
    }

    // If reconnection, reset state to ensure clean reload
    if (isReconnection) {
      if (DEBUG) console.log('EV Trip Planner Panel: Resetting state for reconnection');
      this._rendered = false;
      this._pollStarted = false;
      this._isLoading = true;
    }

    // Get vehicle_id from URL
    this._extractVehicleId();

    // Start hass polling if needed
    if (this._hass && this._vehicleId) {
      this._loadTrips();
    } else {
      this._startHassPolling();
    }
  }

  /**
   * Disconnected callback - called when element is removed from DOM
   * CRITICAL: This prevents memory leaks and ensures clean reconnection
   * Following Lit lifecycle best practices - this method was MISSING
   */
  disconnectedCallback() {
    super.disconnectedCallback();

    if (DEBUG) console.log('EV Trip Planner Panel: disconnectedCallback called - cleaning up');

    // Clear polling timeout to prevent memory leaks
    if (this._pollTimeout) {
      if (DEBUG) console.log('EV Trip Planner Panel: Clearing poll timeout');
      clearTimeout(this._pollTimeout);
      this._pollTimeout = null;
    }

    // Reset state flags to ensure clean reconnection
    this._rendered = false;
    this._pollStarted = false;

    // Note: We DON'T reset _trips or _vehicleId as they may be useful on reconnection
    // The render() method will handle showing appropriate loading state
  }

  /**
   * Extract vehicle_id from URL
   */
  _extractVehicleId() {
    let path = window.location.pathname;

    // Normalize path - remove /panel prefix if present
    if (path.startsWith('/panel/')) {
      path = path.substring(7);
    }

    // Method 1: Simple split approach
    if (path.includes('ev-trip-planner-')) {
      const parts = path.split('ev-trip-planner-');
      if (parts.length > 1) {
        this._vehicleId = parts[1].split('/')[0];
        console.log('EV Trip Planner Panel: ✓ vehicle_id from split:', this._vehicleId);
        return;
      }
    }

    // Method 2: regex fallback
    const match = path.match(/\/ev-trip-planner-(.+)/);
    if (match && match[1]) {
      this._vehicleId = match[1];
      console.log('EV Trip Planner Panel: ✓ vehicle_id from regex:', this._vehicleId);
    }

    // Method 3: from hash
    if (!this._vehicleId && window.location.hash) {
      const hashMatch = window.location.hash.match(/\/ev-trip-planner-(.+)/);
      if (hashMatch && hashMatch[1]) {
        this._vehicleId = hashMatch[1];
        console.log('EV Trip Planner Panel: ✓ vehicle_id from hash:', this._vehicleId);
      }
    }

    console.log('EV Trip Planner Panel: === FINAL vehicle_id:', this._vehicleId, '===');
  }

  /**
   * Poll for hass property
   */
  _startHassPolling() {
    if (this._rendered) {
      if (this._pollTimeout) {
        clearTimeout(this._pollTimeout);
        this._pollTimeout = null;
      }
      this._pollStarted = false;
      return;
    }

    if (this._pollStarted) {
      if (DEBUG) console.log('EV Trip Planner Panel: Polling already started, skipping');
      return;
    }

    this._pollStarted = true;
    this._initAttempts = 0;

    const poll = () => {
      if (this._rendered) {
        if (DEBUG) console.log('EV Trip Planner Panel: Panel already rendered, stopping polling');
        if (this._pollTimeout) {
          clearTimeout(this._pollTimeout);
          this._pollTimeout = null;
        }
        this._pollStarted = false;
        return;
      }

      if (!this._pollStarted) {
        return;
      }

      if (this._hass && this._vehicleId) {
        if (DEBUG) console.log('EV Trip Planner Panel: hass and vehicle_id available, rendering');
        this._pollStarted = false;
        if (this._pollTimeout) {
          clearTimeout(this._pollTimeout);
          this._pollTimeout = null;
        }
        this._loadTrips();
        return;
      }

      this._initAttempts++;

      if (this._initAttempts < this._maxInitAttempts) {
        if (DEBUG) console.log(`EV Trip Planner Panel: waiting for hass... attempt ${this._initAttempts}/${this._maxInitAttempts}`);
        this._pollTimeout = setTimeout(poll, 500);
      } else {
        console.error('EV Trip Planner Panel: Max init attempts reached, hass not available');
        if (this._pollTimeout) {
          clearTimeout(this._pollTimeout);
          this._pollTimeout = null;
        }
        this._pollStarted = false;
      }
    };

    this._pollTimeout = setTimeout(poll, 100);
  }

  /**
   * Hass setter - called by Home Assistant
   */
  set hass(hass) {
    this._hass = hass;
    if (DEBUG) console.log('EV Trip Planner Panel: hass setter called', hass ? 'available' : 'null');

    if (this._hass && this._vehicleId) {
      const now = Date.now();
      if (!this._lastLoadTrips || (now - this._lastLoadTrips) > 5000) {
        this._lastLoadTrips = now;
        this._loadTrips();
      }
    }
  }

  /**
   * Render the panel using Lit template literals
   */
  render() {
    if (!this._hass || !this._vehicleId) {
      return html`
        <div style="padding: 20px; text-align: center;">
          <p>Loading EV Trip Planner...</p>
        </div>
      `;
    }

    // Get vehicle states
    const states = this._getVehicleStates();
    const groupedSensors = this._groupSensors(states);

    // Filter out unavailable/unknown sensors
    const validStatusSensors = groupedSensors.status.filter(s => {
      const formattedValue = this._formatSensorValue(s.entityId);
      return formattedValue !== null;
    });

    // Filter other sensor groups
    const filteredGroupedSensors = {};
    Object.entries(groupedSensors).forEach(([groupName, sensors]) => {
      const validSensors = sensors.filter(s => {
        const formattedValue = this._formatSensorValue(s.entityId);
        return formattedValue !== null;
      });
      filteredGroupedSensors[groupName] = validSensors;
    });

    const statusCards = validStatusSensors.map(s => html`
      <div class="status-card" data-entity="${this._escapeHtml(s.entityId)}">
        <span class="status-icon">${s.icon}</span>
        <span class="status-label">${s.name}</span>
        <span class="status-value">${this._formatSensorValue(s.entityId)}</span>
      </div>
    `);

    const sensorListHtml = Object.entries(filteredGroupedSensors)
      .filter(([_, sensors]) => sensors.length > 0)
      .map(([groupName, sensors]) => html`
        <div class="sensor-group">
          <h3 class="sensor-group-title">${this._getGroupName(groupName)}</h3>
          <div class="sensor-items-list">
            ${sensors.map(s => {
              const formattedValue = this._formatSensorValue(s.entityId);
              const entityIdDisplay = s.entityId.split('.').slice(1).join('.');
              const valueDisplay = formattedValue || 'N/A';
              return html`
                <div class="sensor-item" data-entity-id="${s.entityId}" data-value="${this._escapeHtml(valueDisplay)}">
                  <div class="sensor-left">
                    <span class="sensor-icon" title="${this._escapeHtml(entityIdDisplay)}">${s.icon}</span>
                    <div class="sensor-name-container">
                      <span class="sensor-name">${s.name}</span>
                      <span class="sensor-entity" title="${this._escapeHtml(entityIdDisplay)}">${this._escapeHtml(entityIdDisplay)}</span>
                    </div>
                  </div>
                  <div class="sensor-right">
                    <span class="sensor-value">${this._escapeHtml(valueDisplay)}</span>
                  </div>
                </div>
              `;
            })}
          </div>
        </div>
      `);

    const hasValidSensors = Object.values(filteredGroupedSensors).some(s => s.length > 0);

    return html`
      <link rel="stylesheet" href="/ev-trip-planner/panel.css">
      <div class="panel-container">
        <header class="panel-header">
          <h1>🚗 EV Trip Planner - ${this._vehicleId}</h1>
        </header>

        <main class="panel-content">
          ${statusCards ? html`
            <div class="status-section">
              <h2 class="section-title">
                <span class="section-icon">📊</span>
                <span class="section-title-text">Vehicle Status</span>
              </h2>
              <div class="status-grid">
                ${statusCards}
              </div>
            </div>
          ` : ''}

          <div class="sensors-section">
            ${hasValidSensors ? html`
              <h2 class="section-title">
                <span class="section-icon">📡</span>
                <span class="section-title-text">Available Sensors (${Object.values(filteredGroupedSensors).reduce((sum, s) => sum + s.length, 0)})</span>
              </h2>
              <div class="sensor-list-grouped">
                ${sensorListHtml || html`<p class="no-sensors">No valid sensors found</p>`}
              </div>
            ` : html`<p class="no-sensors">No sensors found</p>`}
          </div>

          ${this._renderEmhassConfig()}

          <div class="trips-section">
            <div class="trips-header">
              <h2 class="section-title">
                <span class="section-icon">📅</span>
                <span class="section-title-text">Viajes Programados</span>
              </h2>
              <button class="add-trip-btn" @click=${() => this._showTripForm()}>
                + Agregar Viaje
              </button>
            </div>
            ${this._isLoading ? html`<h2>Cargando viajes...</h2>` : html`
              ${(this._trips?.length || 0) === 0 ? html`<p class="no-trips">No hay viajes programados</p>` : html`
                <div class="trips-list">
                  ${this._trips.map(trip => this._formatTripDisplay(trip))}
                </div>
              `}
            `}
          </div>
        </main>

        ${this._showForm ? html`
          ${this._editingTrip ? this._renderEditForm() : this._renderCreateForm()}
        ` : ''}
      </div>
    `;
  }

  /**
   * Get list of trips for the vehicle
   */
  async _getTripsList() {
    if (!this._hass || !this._vehicleId) {
      console.warn('EV Trip Planner Panel: Cannot get trips - no hass or vehicle_id');
      return [];
    }

    // VERSION=3.0.5 UNIQUE_LOG_ID=VTP-2026-03-28-RESPONSE-EXTRACTION-FIX
    if (DEBUG) {
      console.log('EV Trip Planner Panel: === _getTripsList START ===');
      console.log('EV Trip Planner Panel: _hass:', this._hass ? 'available' : 'null');
      console.log('EV Trip Planner Panel: _vehicleId:', this._vehicleId);
    }

    try {
      if (DEBUG) console.log('EV Trip Planner Panel: Fetching trips for vehicle:', this._vehicleId);
      // Source: /mnt/bunker_data/ha-ev-trip-planner/ha-frontend-source/src/types.ts
      // callService<T = any>(
      //   domain: string,
      //   service: string,
      //   serviceData?: Record<string, any>,
      //   target?: HassServiceTarget,
      //   notifyOnError?: boolean,
      //   returnResponse?: boolean  // ← 6th parameter, boolean (not object!)
      // ): Promise<ServiceCallResponse<T>>;
      const response = await this._hass.callService(
        'ev_trip_planner',
        'trip_list',
        { vehicle_id: this._vehicleId },  // serviceData (3rd param)
        undefined,  // target (4th param)
        undefined,  // notifyOnError (5th param)
        true  // returnResponse (6th param, boolean)
      );

      if (DEBUG) console.log('EV Trip Planner Panel: Trip list response:', JSON.stringify(response, null, 2));

      // Guard: Handle null/undefined response
      if (!response) {
        console.warn('EV Trip Planner Panel: Service returned null/undefined response');
        return [];
      }

      // Home Assistant services with SupportsResponse.ONLY wrap response in {response: {...}}
      // Extract actual data from the response wrapper
      let tripsData = response;

      // Try response.response first (SupportsResponse.ONLY)
      if (response && response.response) {
        tripsData = response.response;
        if (DEBUG) console.log('EV Trip Planner Panel: Extracted from response.response:', JSON.stringify(tripsData, null, 2));
      }
      // Fallback to response.result for other service types
      else if (response && response.result) {
        tripsData = response.result;
        if (DEBUG) console.log('EV Trip Planner Panel: Extracted from result:', JSON.stringify(tripsData, null, 2));
      }

      // Now check if the extracted data is valid
      // If tripsData has context but no recurring_trips, it's an error
      if (tripsData && tripsData.context && !tripsData.recurring_trips) {
        // This is an error response with just context
        console.warn('EV Trip Planner Panel: Service returned context-only response:', tripsData);
        return [];
      }

      // Debug: Check what we have
      if (DEBUG) {
        console.log('EV Trip Planner Panel: tripsData keys:', tripsData ? Object.keys(tripsData) : 'null');
        console.log('EV Trip Planner Panel: tripsData.recurring_trips:', tripsData?.recurring_trips);
        console.log('EV Trip Planner Panel: tripsData.punctual_trips:', tripsData?.punctual_trips);
      }

      if (tripsData && tripsData.recurring_trips !== undefined) {
        const recurringTrips = tripsData.recurring_trips || [];
        const punctualTrips = tripsData.punctual_trips || [];
        if (DEBUG) console.log('EV Trip Planner Panel: retrieved', recurringTrips.length, 'recurring and', punctualTrips.length, 'punctual trips');

        const trips = [
          ...recurringTrips.map(t => ({...t, trip_type: 'recurrente'})),
          ...punctualTrips.map(t => ({...t, trip_type: 'puntual'})),
        ];

        if (DEBUG) console.log('EV Trip Planner Panel: === _getTripsList END - trips:', trips);
        return trips;
      }

      console.warn('EV Trip Planner Panel: Unexpected response format:', tripsData);
      return [];
    } catch (error) {
      console.error('EV Trip Planner Panel: Error fetching trips:', error);
      return [];
    }
  }

  /**
   * Render EMHASS configuration section with Jinja2 template
   */
  _renderEmhassConfig() {
    // Search for EMHASS sensor scoped to current vehicle by vehicle_id attribute
    // FR-2.1: Multi-vehicle safety - filter EMHASS sensors by vehicle_id attribute, not just prefix
    let emhassSensorEntityId = null;
    const states = this._hass && this._hass.states ? this._hass.states : {};
    
    if (states instanceof Map) {
      for (const [entityId, state] of states) {
        if (entityId.includes('emhass_perfil_diferible_')) {
          const vehicleId = state.attributes?.vehicle_id;
          if (vehicleId === this._vehicleId) {
            emhassSensorEntityId = entityId;
            break;
          }
        }
      }
    } else {
      for (const [entityId, state] of Object.entries(states)) {
        if (entityId.includes('emhass_perfil_diferible_')) {
          const vehicleId = state.attributes?.vehicle_id;
          if (vehicleId === this._vehicleId) {
            emhassSensorEntityId = entityId;
            break;
          }
        }
      }
    }

    // Get EMHASS sensor state
    const emhassState = emhassSensorEntityId ? this._hass.states[emhassSensorEntityId] : null;
    const emhassAvailable = emhassState && emhassState.state !== 'unavailable' && emhassState.state !== 'unknown';

    // Jinja2 template for all 6 EMHASS parameters
    // Note: Use state_attr() instead of states().attributes - Home Assistant
    const jinja2Template = `
{# EMHASS Configuration for ${this._vehicleId} #}
{# Generated from EV Trip Planner EMHASS Aggregated Sensor #}

number_of_deferrable_loads: {{ state_attr('${emhassSensorEntityId}', 'number_of_deferrable_loads') | default(0) }}
def_total_hours: {{ state_attr('${emhassSensorEntityId}', 'def_total_hours_array') | default([], true) }}
P_deferrable_nom: {{ state_attr('${emhassSensorEntityId}', 'p_deferrable_nom_array') | default([], true) }}
def_start_timestep: {{ state_attr('${emhassSensorEntityId}', 'def_start_timestep_array') | default([], true) }}
def_end_timestep: {{ state_attr('${emhassSensorEntityId}', 'def_end_timestep_array') | default([], true) }}
P_deferrable: {{ state_attr('${emhassSensorEntityId}', 'p_deferrable_matrix') | default([], true) }}`;

    return html`
      <div class="emhass-config-section">
        <div class="emhass-header">
          <h2 class="section-title">
            <span class="section-icon">⚡</span>
            <span class="section-title-text">EMHASS Configuration</span>
          </h2>
          ${emhassAvailable ? html`
            <span class="emhass-status emhass-status-available">● Sensor Available</span>
          ` : html`
            <span class="emhass-status emhass-status-unavailable">● Sensor Unavailable</span>
          `}
        </div>

        <div class="emhass-info">
          <p class="emhass-description">
            Use this Jinja2 template in your EMHASS optimization configuration.
            The template references the <strong>EMHASS Aggregated Sensor</strong> which contains
            all 6 EMHASS parameters from your active trips.
          </p>
        </div>

        <div class="emhass-template-container">
          <pre class="emhass-template"><code>${this._escapeHtml(jinja2Template)}</code></pre>
          <button
            class="copy-button"
            @click=${async () => {
              try {
                await navigator.clipboard.writeText(jinja2Template);
                this._showCopyConfirmation();
              } catch (err) {
                console.error('Failed to copy template:', err);
              }
            }}
            ?disabled=${!emhassAvailable}
          >
            📋 Copy Template
          </button>
        </div>

        ${this._copyConfirmationVisible ? html`
          <div class="copy-confirmation">
            ✓ Template copied to clipboard!
          </div>
        ` : ''}

        <div class="emhass-parameters">
          <h3>EMHASS Parameters Reference</h3>
          <table class="emhass-table">
            <thead>
              <tr>
                <th>Parameter</th>
                <th>Description</th>
                <th>Jinja2 Reference</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td><code>number_of_deferrable_loads</code></td>
                <td>Number of active trips with EMHASS data</td>
                <td><code>emhass.attributes.number_of_deferrable_loads</code></td>
              </tr>
              <tr>
                <td><code>def_total_hours_array</code></td>
                <td>Total hours for each deferrable load</td>
                <td><code>emhass.attributes.def_total_hours_array</code></td>
              </tr>
              <tr>
                <td><code>p_deferrable_nom_array</code></td>
                <td>Nominal power for each deferrable load (W)</td>
                <td><code>emhass.attributes.p_deferrable_nom_array</code></td>
              </tr>
              <tr>
                <td><code>def_start_timestep_array</code></td>
                <td>Start timestep for each deferrable load</td>
                <td><code>emhass.attributes.def_start_timestep_array</code></td>
              </tr>
              <tr>
                <td><code>def_end_timestep_array</code></td>
                <td>End timestep for each deferrable load</td>
                <td><code>emhass.attributes.def_end_timestep_array</code></td>
              </tr>
              <tr>
                <td><code>p_deferrable_matrix</code></td>
                <td>Power profile matrix (Watts per timestep)</td>
                <td><code>emhass.attributes.p_deferrable_matrix</code></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  /**
   * Show copy confirmation for EMHASS template
   */
  _showCopyConfirmation() {
    this._copyConfirmationVisible = true;
    setTimeout(() => {
      this._copyConfirmationVisible = false;
      this.requestUpdate();
    }, 2000);
    this.requestUpdate();
  }

  /**
   * Load trips from API
   */
  async _loadTrips() {
    if (DEBUG) console.log('EV Trip Planner Panel: === _loadTrips START ===');

    if (!this._hass || !this._vehicleId) {
      console.warn('EV Trip Planner Panel: Cannot load trips - no hass or vehicle_id');
      return;
    }

    try {
      const trips = await this._getTripsList() || [];  // Guard: default to empty array if null
      if (DEBUG) console.log('EV Trip Planner Panel: Trips retrieved:', trips.length);

      // Update trips array
      this._trips = trips;
      this._isLoading = false;
      this._rendered = true;  // Stop polling once successfully loaded

      // Force re-render
      this.requestUpdate();

      if (DEBUG) console.log('EV Trip Planner Panel: === _loadTrips END - trips:', this._trips.length);
    } catch (error) {
      console.error('EV Trip Planner Panel: Error fetching trips:', error);
      this._isLoading = false;
      this._rendered = true;  // Stop polling even on error to prevent infinite loop
      this.requestUpdate();
    }
  }

  /**
   * Format trip for display
   */
  _formatTripDisplay(trip) {
    const tripId = trip.id || 'N/A';
    const isActive = trip.activo !== false || trip.active !== false;
    const isRecurring = trip.tipo === 'recurrente' || trip.type === 'recurrente' || trip.recurring === true;
    const isPunctual = trip.tipo === 'puntual' || trip.type === 'puntual' || trip.recurring === false;

    let timeDisplay = '';
    if (isRecurring) {
      const dayNames = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
      let dayName = '';
      let time = '00:00';

      if (trip.dia_semana) {
        const lowerDay = trip.dia_semana.toLowerCase();
        dayName = dayNames.find(d => d.toLowerCase() === lowerDay) || trip.dia_semana;
        time = trip.hora || '00:00';
      } else if (trip.day_of_week !== undefined) {
        const dayIndex = parseInt(trip.day_of_week, 10);
        dayName = dayNames[dayIndex] || `Día ${dayIndex}`;
        time = trip.time || trip.hora || '00:00';
      }

      timeDisplay = dayName ? `${dayName} ${time}` : 'Sin hora programada';
    } else if (isPunctual) {
      timeDisplay = trip.date || trip.datetime || trip.date || 'Sin fecha';
      if (trip.time) {
        timeDisplay += ` a las ${trip.time}`;
      }
    }

    const distance = trip.km ? `${trip.km} km` : 'N/A';
    const energy = trip.kwh ? `${trip.kwh} kWh` : 'N/A';
    const description = trip.descripcion || trip.description || '';
    const descriptionHtml = description ? html`<div class="trip-description">${this._escapeHtml(description)}</div>` : '';

    const statusBadge = isActive ? html`<span class="trip-status status-active">Activo</span>` : html`<span class="trip-status status-inactive">Inactivo</span>`;

    const tripIdForForm = trip.id || trip.trip_id || trip.tripId || 'unknown';

    let actionButtons = html`
      <div class="trip-action-group universal-actions">
        <button class="trip-action-btn edit-btn" @click=${() => this._handleEditClick(tripIdForForm)}>
          ✏️ Editar
        </button>
        <button class="trip-action-btn delete-btn" @click=${() => this._handleDeleteClick(tripIdForForm)}>
          🗑️ Eliminar
        </button>
      </div>
    `;

    if (isRecurring) {
      actionButtons = html`
        ${actionButtons}
        <div class="trip-action-group status-actions">
          ${isActive ? html`
            <button class="trip-action-btn pause-btn" @click=${() => this._handlePauseTrip(tripIdForForm)}>
              ⏸️ Pausar
            </button>
          ` : html`
            <button class="trip-action-btn resume-btn" @click=${() => this._handleResumeTrip(tripIdForForm)}>
              ▶️ Reanudar
            </button>
          `}
        </div>
      `;
    } else if (isPunctual) {
      actionButtons = html`
        ${actionButtons}
        <div class="trip-action-group punctual-actions">
          <button class="trip-action-btn complete-btn" @click=${() => this._handleCompletePunctualTrip(tripIdForForm)}>
            ✓ Completar
          </button>
          <button class="trip-action-btn cancel-btn" @click=${() => this._handleCancelPunctualTrip(tripIdForForm)}>
            ❌ Cancelar
          </button>
        </div>
      `;
    }

    return html`
      <div class="trip-card ${isActive ? '' : 'trip-card-inactive'}" data-trip-id="${tripIdForForm}">
        <div class="trip-header">
          <div>
            <span class="trip-type">${isRecurring ? '🔄 Recurrente' : '📅 Puntual'}</span>
            ${statusBadge}
          </div>
        </div>
        <div class="trip-info">
          <div class="trip-time">⏰ ${timeDisplay}</div>
          <div class="trip-details">
            <span class="trip-detail">📏 ${distance}</span>
            <span class="trip-detail">⚡ ${energy}</span>
          </div>
          ${descriptionHtml}
        </div>
        <div class="trip-actions">
          ${actionButtons}
        </div>
      </div>
    `;
  }

  /**
   * Get vehicle states
   */
  _getVehicleStates() {
    if (!this._hass || !this._hass.states) {
      console.log('EV Trip Planner Panel: No hass.states available');
      return {};
    }

    const states = this._hass.states;
    const result = {};
    const lowerVehicleId = this._vehicleId.toLowerCase();

    const patterns = [
      `sensor.${lowerVehicleId}`, `sensor.${lowerVehicleId}_`,
      `binary_sensor.${lowerVehicleId}`, `binary_sensor.${lowerVehicleId}_`,
      `input_number.${lowerVehicleId}`, `input_number.${lowerVehicleId}_`,
      `input_boolean.${lowerVehicleId}`, `input_boolean.${lowerVehicleId}_`,
      `climate.${lowerVehicleId}`, `climate.${lowerVehicleId}_`,
      `cover.${lowerVehicleId}`, `cover.${lowerVehicleId}_`,
      `number.${lowerVehicleId}`, `number.${lowerVehicleId}_`,
      `switch.${lowerVehicleId}`, `switch.${lowerVehicleId}_`,
      `light.${lowerVehicleId}`, `light.${lowerVehicleId}_`,
      `fan.${lowerVehicleId}`, `fan.${lowerVehicleId}_`,
      `vacuum.${lowerVehicleId}`, `vacuum.${lowerVehicleId}_`,
      `lock.${lowerVehicleId}`, `lock.${lowerVehicleId}_`,
      `media_player.${lowerVehicleId}`, `media_player.${lowerVehicleId}_`,
      `device_tracker.${lowerVehicleId}`, `device_tracker.${lowerVehicleId}_`,
      `weather.${lowerVehicleId}`, `weather.${lowerVehicleId}_`,
      `alarm_control_panel.${lowerVehicleId}`, `alarm_control_panel.${lowerVehicleId}_`,
      `sensor.ev_trip_planner_${lowerVehicleId}`, `sensor.ev_trip_planner_${lowerVehicleId}_`,
      `binary_sensor.ev_trip_planner_${lowerVehicleId}`, `binary_sensor.ev_trip_planner_${lowerVehicleId}_`,
      `input_number.ev_trip_planner_${lowerVehicleId}`, `input_number.ev_trip_planner_${lowerVehicleId}_`,
      `input_boolean.ev_trip_planner_${lowerVehicleId}`, `input_boolean.ev_trip_planner_${lowerVehicleId}_`,
      `climate.ev_trip_planner_${lowerVehicleId}`, `climate.ev_trip_planner_${lowerVehicleId}_`,
      `cover.ev_trip_planner_${lowerVehicleId}`, `cover.ev_trip_planner_${lowerVehicleId}_`,
      `number.ev_trip_planner_${lowerVehicleId}`, `number.ev_trip_planner_${lowerVehicleId}_`,
      `switch.ev_trip_planner_${lowerVehicleId}`, `switch.ev_trip_planner_${lowerVehicleId}_`,
      `light.ev_trip_planner_${lowerVehicleId}`, `light.ev_trip_planner_${lowerVehicleId}_`,
      `fan.ev_trip_planner_${lowerVehicleId}`, `fan.ev_trip_planner_${lowerVehicleId}_`,
      'sensor.trip_',
      'sensor.ev_trip_planner_',
      // FR-2.1: Filter EMHASS sensors by entry_id attribute (not pattern matching)
      'sensor.emhass_perfil_diferible_',
    ];

    if (states instanceof Map) {
      for (const [entityId, state] of states) {
        if (patterns.some(pattern => entityId.includes(pattern))) {
          // FR-2.1: For EMHASS sensors, verify vehicle_id attribute matches current vehicle
          // Compare vehicle_id (the vehicle name slug) with this._vehicleId from URL
          if (entityId.includes('emhass_perfil_diferible_')) {
            const vehicleId = state.attributes?.vehicle_id;
            if (vehicleId === this._vehicleId) {
              result[entityId] = state;
            }
          } else {
            result[entityId] = state;
          }
        }
      }
    } else {
      for (const [entityId, state] of Object.entries(states)) {
        if (patterns.some(pattern => entityId.includes(pattern))) {
          // FR-2.1: For EMHASS sensors, verify vehicle_id attribute matches current vehicle
          // Compare vehicle_id (the vehicle name slug) with this._vehicleId from URL
          if (entityId.includes('emhass_perfil_diferible_')) {
            const vehicleId = state.attributes?.vehicle_id;
            if (vehicleId === this._vehicleId) {
              result[entityId] = state;
            }
          } else {
            result[entityId] = state;
          }
        }
      }
    }

    return result;
  }

  /**
   * Group sensors by type
   */
  _groupSensors(sensors) {
    const groups = {
      status: [],
      battery: [],
      trips: [],
      energy: [],
      charging: [],
      other: []
    };

    for (const [entityId, state] of Object.entries(sensors)) {
      const name = this._entityIdToName(entityId);
      const lowerName = name.toLowerCase();
      const icon = this._getSensorIcon(entityId);

      if (this._isStatusSensor(entityId)) {
        groups.status.push({ entityId, state, name, icon });
      } else if (lowerName.includes('soc') || lowerName.includes('battery') || lowerName.includes('capacidad')) {
        groups.battery.push({ entityId, state, name, icon });
      } else if (lowerName.includes('trip') || lowerName.includes('viaje') || lowerName.includes('recurring') || lowerName.includes('puntual')) {
        groups.trips.push({ entityId, state, name, icon });
      } else if (lowerName.includes('kwh') || lowerName.includes('energy') || lowerName.includes('consumption') || lowerName.includes('consumo')) {
        groups.energy.push({ entityId, state, name, icon });
      } else if (lowerName.includes('charging') || lowerName.includes('carga') || lowerName.includes('charge_status') || lowerName.includes('plugged') || lowerName.includes('home')) {
        groups.charging.push({ entityId, state, name, icon });
      } else {
        groups.other.push({ entityId, state, name, icon });
      }
    }

    return groups;
  }

  /**
   * Check if sensor is a status indicator
   */
  _isStatusSensor(entityId) {
    const name = this._entityIdToName(entityId);
    const lowerName = name.toLowerCase();
    return (
      lowerName.includes('soc') ||
      lowerName.includes('battery_level') ||
      lowerName.includes('range') ||
      lowerName.includes('charging_status') ||
      lowerName.includes('charging') ||
      lowerName.includes('plugged') ||
      lowerName.includes('state') ||
      lowerName.includes('status')
    );
  }

  /**
   * Get sensor icon
   */
  _getSensorIcon(entityId) {
    const name = this._entityIdToName(entityId);
    const lowerName = name.toLowerCase();

    if (lowerName.includes('soc') || lowerName.includes('battery')) return '🔋';
    if (lowerName.includes('range') || lowerName.includes('distance')) return '📍';
    if (lowerName.includes('charging') || lowerName.includes('carga')) return '⚡';
    if (lowerName.includes('kwh') || lowerName.includes('energy')) return '💡';
    if (lowerName.includes('trip') || lowerName.includes('viaje')) return '🚗';
    if (lowerName.includes('temperature') || lowerName.includes('temp')) return '🌡️';
    if (lowerName.includes('pressure')) return '🌡️';
    if (lowerName.includes('speed')) return '🚀';
    if (lowerName.includes('light')) return '💡';
    if (lowerName.includes('lock')) return '🔒';
    if (lowerName.includes('cover') || lowerName.includes('persiana')) return '🪟';
    if (lowerName.includes('fan')) return '💨';
    if (lowerName.includes('presence')) return '👤';
    if (lowerName.includes('status') || lowerName.includes('estado')) return '📊';

    return '📊';
  }

  /**
   * Entity ID to name
   */
  _entityIdToName(entityId) {
    let name = entityId.replace(/^[\w_]+\./, '');
    name = name.replace(/_chispitas_/gi, '_').replace(/_coche_/gi, '_');
    name = name.replace(/([A-Z])/g, ' $1');
    name = name.replace(/_/g, ' ');
    name = name.replace(/\s+/g, ' ');

    return name
      .trim()
      .split(' ')
      .map(word => {
        const abbreviations = ['soc', 'kwh', 'ev', 'ha', 'id', 'km', 'dc', 'ac'];
        const lowerWord = word.toLowerCase();
        if (abbreviations.includes(lowerWord)) {
          return lowerWord.toUpperCase();
        }
        return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
      })
      .join(' ');
  }

  /**
   * Get group name
   */
  _getGroupName(groupName) {
    const names = {
      status: '📊 Estado del Vehículo',
      battery: '🔋 Batería',
      trips: '🚗 Viajes',
      energy: '⚡ Energía y Consumo',
      charging: '🔌 Carga',
      other: '📋 Otros Sensores'
    };
    return names[groupName] || groupName;
  }

  /**
   * Format sensor value
   */
  _formatSensorValue(entityId) {
    const states = this._hass?.states || {};
    const state = states[entityId];
    if (!state) return null;

    const value = state.state;

    if (value === 'unavailable' || value === 'unknown' || value === 'N/A' || value === 'none' || value === '' || value === null) {
      return 'N/A';
    }

    if (value === 'on' || value === 'off' || value === 'true' || value === 'false') {
      return value === 'on' || value === 'true' ? '✓ Activo' : '✗ Inactivo';
    }

    const numericValue = parseFloat(value);
    if (!isNaN(numericValue)) {
      return numericValue.toFixed(1);
    }

    return value;
  }

  /**
   * Escape HTML
   */
  _escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Show trip form
   */
  _showTripForm() {
    this._showForm = true;
    this._formType = 'recurrente';
    this._editingTrip = null;
  }

  /**
   * Close form
   */
  _closeForm() {
    this._showForm = false;
    this._editingTrip = null;
    this._formType = 'recurrente';
  }

  /**
   * Handle trip type change
   */
  _handleTripTypeChange(e) {
    if (e && e.target) {
      this._formType = e.target.value;
    }
  }

  /**
   * Render create form with dynamic field visibility based on trip type
   */
  _renderCreateForm() {
    const now = new Date();
    const hours = String(now.getHours()).padStart(2, '0');
    const minutes = String(now.getMinutes()).padStart(2, '0');
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const isPunctual = this._formType === 'puntual';

    return html`
      <div class="trip-form-overlay">
        <div class="trip-form-container">
          <div class="trip-form-header">
            <h3>🚗 Nuevo Viaje</h3>
            <button class="close-form-btn" @click=${this._closeForm}>×</button>
          </div>
          <form @submit=${this._handleTripCreate}>
            <div class="form-group">
              <label for="trip-type">Tipo de Viaje</label>
              <select id="trip-type" name="type" required @change=${this._handleTripTypeChange}>
                <option value="recurrente">🔄 Recurrente (semanal)</option>
                <option value="puntual">📅 Puntual (una vez)</option>
              </select>
            </div>
            <div class="form-group" style="display: ${isPunctual ? 'none' : 'block'}">
              <label for="trip-day">Día de la Semana</label>
              <select id="trip-day" name="day">
                <option value="0">Domingo</option>
                <option value="1">Lunes</option>
                <option value="2">Martes</option>
                <option value="3">Miércoles</option>
                <option value="4">Jueves</option>
                <option value="5">Viernes</option>
                <option value="6">Sábado</option>
              </select>
            </div>
            <div class="form-group" style="display: ${isPunctual ? 'block' : 'none'}">
              <label for="trip-datetime">Fecha y Hora</label>
              <input type="datetime-local" id="trip-datetime" name="datetime" value="${year}-${month}-${day}T${hours}:${minutes}">
            </div>
            <div class="form-group" style="display: ${isPunctual ? 'none' : 'block'}">
              <label for="trip-time">Hora</label>
              <input type="time" id="trip-time" name="time" required value="${hours}:${minutes}">
            </div>
            <div class="form-group">
              <label for="trip-km">Distancia (km)</label>
              <input type="number" id="trip-km" name="km" step="0.1" min="0" placeholder="Ej: 25.5">
            </div>
            <div class="form-group">
              <label for="trip-kwh">Energía Estimada (kWh)</label>
              <input type="number" id="trip-kwh" name="kwh" step="0.1" min="0" placeholder="Ej: 5.2">
            </div>
            <div class="form-group">
              <label for="trip-description">Descripción (opcional)</label>
              <textarea id="trip-description" name="description" placeholder="Ej: Viaje al trabajo, compras, etc."></textarea>
            </div>
            <div class="form-actions">
              <button type="button" class="btn btn-secondary" @click=${this._closeForm}>Cancelar</button>
              <button type="submit" class="btn btn-primary">Crear Viaje</button>
            </div>
          </form>
        </div>
      </div>
    `;
  }

  /**
   * Handle trip creation form submission
   */
  async _handleTripCreate(e) {
    e.preventDefault();
    if (DEBUG) console.log('EV Trip Planner Panel: Creating trip...');

    if (!this._hass || !this._vehicleId) {
      alert('Error: No hay conexión con Home Assistant');
      return;
    }

    const form = e.target;
    const formData = new FormData(form);

    const type = formData.get('type');
    const km = formData.get('km');
    const kwh = formData.get('kwh');
    const description = formData.get('description');

    const serviceData = {
      vehicle_id: this._vehicleId,
      type: type,
    };

    if (type === 'puntual') {
      const datetime = formData.get('datetime');
      if (datetime) {
        serviceData.datetime = datetime;
      }
    } else {
      const day = formData.get('day');
      const time = formData.get('time');
      serviceData.dia_semana = day;
      serviceData.hora = time;
    }

    if (km) serviceData.km = parseFloat(km);
    if (kwh) serviceData.kwh = parseFloat(kwh);
    if (description) serviceData.description = description;

    if (DEBUG) console.log('EV Trip Planner Panel: Service data:', serviceData);

    const submitBtn = form.querySelector('.btn-primary');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Creando...';
    submitBtn.disabled = true;

    try {
      // Use correct callService signature: (domain, service, serviceData, target, notifyOnError, returnResponse)
      // Note: Some HA versions require return_response=true for services that may return data
      const result = await this._hass.callService('ev_trip_planner', 'trip_create', serviceData);
      console.log('EV Trip Planner Panel: trip_create result:', result);
      this._closeForm();

      // Load trips and force update
      await this._loadTrips();

      // Force immediate DOM update
      this.requestUpdate();

      console.log('EV Trip Planner Panel: Current trips after create:', this._trips);
      alert('✅ Viaje creado exitosamente');
    } catch (error) {
      console.error('EV Trip Planner Panel: Error creating trip:', error);
      alert('❌ Error al crear el viaje: ' + (error.message || 'Verifique los logs'));
    } finally {
      submitBtn.textContent = originalText;
      submitBtn.disabled = false;
    }
  }

  /**
   * Get trip by ID using trip_get service
   */
  async _getTripById(tripId) {
    if (!this._hass || !this._vehicleId) return null;

    try {
      // Use correct callService signature: (domain, service, serviceData, target, notifyOnError, returnResponse)
      if (DEBUG) {
        console.log('EV Trip Planner Panel: _getTripById called with tripId:', tripId);
        console.log('EV Trip Planner Panel: _hass:', this._hass ? 'available' : 'null');
        console.log('EV Trip Planner Panel: _vehicleId:', this._vehicleId);
      }

      const response = await this._hass.callService(
        'ev_trip_planner',
        'trip_get',
        {
          vehicle_id: this._vehicleId,
          trip_id: tripId,
        },
        undefined,  // target
        undefined,  // notifyOnError
        true  // returnResponse (6th param, boolean)
      );

      if (DEBUG) {
        console.log('EV Trip Planner Panel: trip_get response:', JSON.stringify(response, null, 2));
        console.log('EV Trip Planner Panel: response keys:', Object.keys(response || {}));
      }

      // Handle response structure: {context: {...}, response: {vehicle_id, trip, found}}
      const responseData = response?.response || response;
      if (DEBUG) console.log('EV Trip Planner Panel: responseData:', JSON.stringify(responseData, null, 2));

      // Response structure: { vehicle_id, trip, found }
      if (responseData && responseData.found && responseData.trip) {
        const trip = responseData.trip;
        // Add trip_type based on trip structure
        trip.trip_type = trip.tipo === 'recurrente' ? 'recurrente' : 'puntual';
        if (DEBUG) console.log('EV Trip Planner Panel: Returning trip:', trip);
        return trip;
      }

      console.error('EV Trip Planner Panel: Trip not found or invalid response:', responseData);
      return null;
    } catch (error) {
      console.error('EV Trip Planner Panel: Error fetching trip:', error);
      return null;
    }
  }

  /**
   * Handle edit click
   */
  async _handleEditClick(tripId) {
    const tripData = await this._getTripById(tripId);
    if (tripData) {
      this._showEditForm(tripData);
    } else {
      alert('Error: No se pudo obtener la información del viaje');
    }
  }

  /**
   * Show edit form
   */
  _showEditForm(trip) {
    this._editingTrip = trip;
    this._showForm = true;
    // Determine trip type for form visibility
    const isPunctual = trip.tipo === 'puntual' || trip.type === 'puntual' || trip.recurring === false;
    this._formType = isPunctual ? 'puntual' : 'recurrente';
  }

  /**
   * Render edit form with dynamic field visibility
   */
  _renderEditForm() {
    const trip = this._editingTrip;
    const dayNames = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
    let dayValue = '1';

    if (trip.day_of_week !== undefined) {
      dayValue = trip.day_of_week;
    } else if (trip.dia_semana) {
      const lowerDay = trip.dia_semana.toLowerCase();
      dayValue = dayNames.indexOf(lowerDay);
      if (dayValue === -1) dayValue = '1';
    }

    const isPunctual = this._formType === 'puntual';

    return html`
      <div class="trip-form-overlay">
        <div class="trip-form-container">
          <div class="trip-form-header">
            <h3>✏️ Editar Viaje</h3>
            <button class="close-form-btn" @click=${this._closeForm}>×</button>
          </div>
          <form @submit=${this._handleTripUpdate}>
            <input type="hidden" name="edit-trip-id" value="${this._escapeHtml(trip.id || trip.trip_id)}">
            <div class="form-group">
              <label for="edit-trip-type">Tipo de Viaje</label>
              <select id="edit-trip-type" name="type" required @change=${this._handleTripTypeChange}>
                <option value="recurrente">🔄 Recurrente (semanal)</option>
                <option value="puntual">📅 Puntual (una vez)</option>
              </select>
            </div>
            <div class="form-group" style="display: ${isPunctual ? 'none' : 'block'}">
              <label for="edit-trip-day">Día de la Semana</label>
              <select id="edit-trip-day" name="day">
                <option value="0">Domingo</option>
                <option value="1">Lunes</option>
                <option value="2">Martes</option>
                <option value="3">Miércoles</option>
                <option value="4">Jueves</option>
                <option value="5">Viernes</option>
                <option value="6">Sábado</option>
              </select>
            </div>
            <div class="form-group" style="display: ${isPunctual ? 'block' : 'none'}">
              <label for="edit-trip-datetime">Fecha y Hora</label>
              <input type="datetime-local" id="edit-trip-datetime" name="datetime" value="${trip.date || trip.datetime || ''}">
            </div>
            <div class="form-group" style="display: ${isPunctual ? 'none' : 'block'}">
              <label for="edit-trip-time">Hora</label>
              <input type="time" id="edit-trip-time" name="time" required value="${trip.time || trip.hora || '00:00'}">
            </div>
            <div class="form-group">
              <label for="edit-trip-km">Distancia (km)</label>
              <input type="number" id="edit-trip-km" name="km" step="0.1" min="0" placeholder="Ej: 25.5" value="${trip.km || ''}">
            </div>
            <div class="form-group">
              <label for="edit-trip-kwh">Energía Estimada (kWh)</label>
              <input type="number" id="edit-trip-kwh" name="kwh" step="0.1" min="0" placeholder="Ej: 5.2" value="${trip.kwh || ''}">
            </div>
            <div class="form-group">
              <label for="edit-trip-description">Descripción (opcional)</label>
              <textarea id="edit-trip-description" name="description" placeholder="Ej: Viaje al trabajo, compras, etc.">${trip.descripcion || trip.description || ''}</textarea>
            </div>
            <div class="form-actions">
              <button type="button" class="btn btn-secondary" @click=${this._closeForm}>Cancelar</button>
              <button type="submit" class="btn btn-primary">Guardar Cambios</button>
            </div>
          </form>
        </div>
      </div>
    `;
  }

  /**
   * Handle trip update
   */
  async _handleTripUpdate(e) {
    e.preventDefault();

    if (!this._hass || !this._vehicleId) {
      alert('Error: No hay conexión con Home Assistant');
      return;
    }

    const form = e.target;
    const formData = new FormData(form);

    const tripId = formData.get('edit-trip-id');
    const type = formData.get('type');
    const day = formData.get('day');
    const time = formData.get('time');
    const datetime = formData.get('datetime');
    const km = formData.get('km');
    const kwh = formData.get('kwh');
    const description = formData.get('description');

    if (!tripId) {
      alert('Error: No se pudo identificar el viaje');
      return;
    }

    const serviceData = {
      vehicle_id: this._vehicleId,
      trip_id: tripId,
      type: type,
    };

    // Always include these fields if provided (regardless of trip type)
    if (datetime) serviceData.datetime = datetime;
    if (day) serviceData.dia_semana = day;
    if (time) serviceData.hora = time;
    if (km) serviceData.km = parseFloat(km);
    if (kwh) serviceData.kwh = parseFloat(kwh);
    if (description) serviceData.description = description;

    const submitBtn = form.querySelector('.btn-primary');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Guardando...';
    submitBtn.disabled = true;

    try {
      // Use correct callService signature: (domain, service, serviceData, target, notifyOnError, returnResponse)
      await this._hass.callService('ev_trip_planner', 'trip_update', serviceData);
      this._closeForm();
      await this._loadTrips();
      alert('✅ Viaje actualizado exitosamente');
    } catch (error) {
      console.error('EV Trip Planner Panel: Error updating trip:', error);
      alert('❌ Error al actualizar el viaje: ' + (error.message || 'Verifique los logs'));
    } finally {
      submitBtn.textContent = originalText;
      submitBtn.disabled = false;
    }
  }

  /**
   * Handle delete click
   */
  async _handleDeleteClick(tripId) {
    if (!confirm('¿Estás seguro de que quieres eliminar este viaje?')) {
      return;
    }

    try {
      await this._deleteTrip(tripId);
      // Remove trip from list
      this._trips = this._trips.filter(t => t.id !== tripId);
      this.requestUpdate();
      alert('✅ Viaje eliminado');
    } catch (error) {
      console.error('EV Trip Planner Panel: Error deleting trip:', error);
      alert('Error: No se pudo eliminar el viaje');
    }
  }

  /**
   * Delete trip
   */
  async _deleteTrip(tripId) {
    if (!this._hass || !this._vehicleId) {
      throw new Error('No connection to Home Assistant');
    }

    // Use correct callService signature: (domain, service, serviceData, target, notifyOnError, returnResponse)
    await this._hass.callService('ev_trip_planner', 'delete_trip', {
      vehicle_id: this._vehicleId,
      trip_id: tripId,
    });

    console.log('EV Trip Planner Panel: Trip deleted successfully:', tripId);
  }

  /**
   * Handle pause trip
   */
  async _handlePauseTrip(tripId) {
    if (!confirm('¿Estás seguro de que quieres pausar este viaje recurrente?')) {
      return;
    }

    try {
      await this._pauseTrip(tripId);
      // Update trip state to trigger re-render
      const tripIndex = this._trips.findIndex(t => t.id === tripId);
      if (tripIndex !== -1) {
        this._trips[tripIndex].activo = false;
        this.requestUpdate();
      }
      alert('✅ Viaje pausado');
    } catch (error) {
      console.error('EV Trip Planner Panel: Error pausing trip:', error);
      alert('Error: No se pudo pausar el viaje');
    }
  }

  /**
   * Pause trip
   */
  async _pauseTrip(tripId) {
    if (!this._hass || !this._vehicleId) {
      throw new Error('No connection to Home Assistant');
    }

    // Use correct callService signature: (domain, service, serviceData, target, notifyOnError, returnResponse)
    await this._hass.callService('ev_trip_planner', 'pause_recurring_trip', {
      vehicle_id: this._vehicleId,
      trip_id: tripId,
    });

    console.log('EV Trip Planner Panel: Trip paused successfully:', tripId);
  }

  /**
   * Handle resume trip
   */
  async _handleResumeTrip(tripId) {
    try {
      await this._resumeTrip(tripId);
      // Update trip state to trigger re-render
      const tripIndex = this._trips.findIndex(t => t.id === tripId);
      if (tripIndex !== -1) {
        this._trips[tripIndex].activo = true;
        this.requestUpdate();
      }
      alert('✅ Viaje reanudado');
    } catch (error) {
      console.error('EV Trip Planner Panel: Error resuming trip:', error);
      alert('Error: No se pudo reanudar el viaje');
    }
  }

  /**
   * Resume trip
   */
  async _resumeTrip(tripId) {
    if (!this._hass || !this._vehicleId) {
      throw new Error('No connection to Home Assistant');
    }

    // Use correct callService signature: (domain, service, serviceData, target, notifyOnError, returnResponse)
    await this._hass.callService('ev_trip_planner', 'resume_recurring_trip', {
      vehicle_id: this._vehicleId,
      trip_id: tripId,
    });

    console.log('EV Trip Planner Panel: Trip resumed successfully:', tripId);
  }

  /**
   * Handle complete punctual trip
   */
  async _handleCompletePunctualTrip(tripId) {
    if (!confirm('¿Estás seguro de que quieres completar este viaje?')) {
      return;
    }

    try {
      await this._completeTrip(tripId);
      // Remove trip from list
      this._trips = this._trips.filter(t => t.id !== tripId);
      this.requestUpdate();
      alert('✅ Viaje completado');
    } catch (error) {
      console.error('EV Trip Planner Panel: Error completing trip:', error);
      alert('Error: No se pudo completar el viaje');
    }
  }

  /**
   * Complete trip
   */
  async _completeTrip(tripId) {
    if (!this._hass || !this._vehicleId) {
      throw new Error('No connection to Home Assistant');
    }

    // Use correct callService signature: (domain, service, serviceData, target, notifyOnError, returnResponse)
    await this._hass.callService('ev_trip_planner', 'complete_punctual_trip', {
      vehicle_id: this._vehicleId,
      trip_id: tripId,
    });

    console.log('EV Trip Planner Panel: Trip completed successfully:', tripId);
  }

  /**
   * Handle cancel punctual trip
   */
  async _handleCancelPunctualTrip(tripId) {
    if (!confirm('¿Estás seguro de que quieres cancelar este viaje?')) {
      return;
    }

    try {
      await this._cancelTrip(tripId);
      // Remove trip from list
      this._trips = this._trips.filter(t => t.id !== tripId);
      this.requestUpdate();
      alert('✅ Viaje cancelado');
    } catch (error) {
      console.error('EV Trip Planner Panel: Error cancelling trip:', error);
      alert('Error: No se pudo cancelar el viaje');
    }
  }

  /**
   * Cancel trip
   */
  async _cancelTrip(tripId) {
    if (!this._hass || !this._vehicleId) {
      throw new Error('No connection to Home Assistant');
    }

    // Use correct callService signature: (domain, service, serviceData, target, notifyOnError, returnResponse)
    await this._hass.callService('ev_trip_planner', 'cancel_punctual_trip', {
      vehicle_id: this._vehicleId,
      trip_id: tripId,
    });

    console.log('EV Trip Planner Panel: Trip cancelled successfully:', tripId);
  }
}

// Register the custom element
customElements.define('ev-trip-planner-panel', EVTripPlannerPanel);
