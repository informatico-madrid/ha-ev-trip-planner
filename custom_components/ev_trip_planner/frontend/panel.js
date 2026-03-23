/**
 * EV Trip Planner Native Panel Web Component
 *
 * A custom web component that renders the EV Trip Planner dashboard
 * as a native Home Assistant panel (not Lovelace).
 *
 * This component is loaded by panel_custom and receives hass and config
 * as properties from Home Assistant.
 *
 * @version 2.0.0
 * @author EV Trip Planner Team
 */

class EVTripPlannerPanel extends HTMLElement {
  constructor() {
    super();
    this._hass = null;
    this._vehicleId = null;
    this._config = null;
    this._unsubscribe = null;
    this._rendered = false;
    this._pollStarted = false;
    this._initAttempts = 0;
    this._maxInitAttempts = 10;
    console.log('EV Trip Planner Panel: Constructor called');
  }

  /**
   * Called when the panel is attached to the DOM
   */
  connectedCallback() {
    console.log('EV Trip Planner Panel: connectedCallback');

    // CRITICAL: Exit immediately if already rendered - prevents multiple connectedCallback calls
    if (this._rendered) {
      console.log('EV Trip Planner Panel: Already rendered, exiting connectedCallback');
      return;
    }

    // CRITICAL: Check if we already have hass and vehicleId - render immediately
    if (this._hass && this._vehicleId) {
      console.log('EV Trip Planner Panel: hass and vehicleId already available, rendering immediately');
      this._rendered = true;
      this._render();
      return;
    }

    // Try to get vehicle_id from URL path as early as possible
    // URL format: /ev-trip-planner-{vehicle_id}
    const path = window.location.pathname;
    console.log('EV Trip Planner Panel: trying to extract from path:', path);
    const match = path.match(/\/ev-trip-planner-(.+)/);
    if (match && match[1]) {
      this._vehicleId = match[1];
      console.log('EV Trip Planner Panel: vehicle_id from URL (early):', this._vehicleId);
    } else {
      console.log('EV Trip Planner Panel: no match found in path');
      // Try with hash (some HA versions use hash routing)
      const hashMatch = window.location.hash.match(/\/ev-trip-planner-(.+)/);
      if (hashMatch && hashMatch[1]) {
        this._vehicleId = hashMatch[1];
        console.log('EV Trip Planner Panel: vehicle_id from hash:', this._vehicleId);
      }
    }

    // CRITICAL: Check if we now have both hass and vehicleId after extracting from URL
    if (this._hass && this._vehicleId) {
      console.log('EV Trip Planner Panel: hass and vehicleId available after URL extraction, rendering immediately');
      this._rendered = true;
      this._render();
      return;
    }

    // Start polling for hass if not available
    this._startHassPolling();
  }

  /**
   * Called when the panel is detached from the DOM
   */
  disconnectedCallback() {
    console.log('EV Trip Planner Panel: disconnectedCallback');
    this._cleanup();
  }

  /**
   * Called by Home Assistant when hass is available
   * This is the main property that HA sets on custom elements
   */
  set hass(hass) {
    console.log('EV Trip Planner Panel: hass setter called', hass ? 'available' : 'null', 'attempts:', this._initAttempts);
    console.log('EV Trip Planner Panel: URL in hass setter:', window.location.href);

    // CRITICAL: Exit immediately if already rendered to prevent multiple renders
    if (this._rendered) {
      console.log('EV Trip Planner Panel: Already rendered, exiting hass setter');
      this._hass = hass;
      return;
    }

    this._hass = hass;
    this._initAttempts = 0; // Reset attempts on successful hass set

    // CRITICAL: Check if we're already rendered after setting hass (race condition)
    if (this._rendered) {
      console.log('EV Trip Planner Panel: Already rendered after hass set, exiting');
      return;
    }

    // Try to get vehicle_id from URL - multiple approaches
    if (!this._vehicleId) {
      const path = window.location.pathname;
      console.log('EV Trip Planner Panel: pathname:', path);
      
      // Method 1: Simple split approach
      if (path.includes('ev-trip-planner-')) {
        const parts = path.split('ev-trip-planner-');
        if (parts.length > 1) {
          this._vehicleId = parts[1].split('/')[0];
          console.log('EV Trip Planner Panel: vehicle_id from split:', this._vehicleId);
        }
      }
      
      // Method 2: regex (keep for backward compatibility)
      if (!this._vehicleId) {
        const match = path.match(/\/ev-trip-planner-(.+)/);
        if (match && match[1]) {
          this._vehicleId = match[1];
          console.log('EV Trip Planner Panel: vehicle_id from URL (in hass setter):', this._vehicleId);
        }
      }
      
      // Method 3: from hash
      if (!this._vehicleId && window.location.hash) {
        const hashMatch = window.location.hash.match(/\/ev-trip-planner-(.+)/);
        if (hashMatch && hashMatch[1]) {
          this._vehicleId = hashMatch[1];
          console.log('EV Trip Planner Panel: vehicle_id from hash:', this._vehicleId);
        }
      }
    }
    
    console.log('EV Trip Planner Panel: Final vehicle_id:', this._vehicleId);
    
    if (!this._rendered) {
      this._render();
    } else {
      this._update();
    }
  }

  /**
   * Getter for hass - allows checking current value
   */
  get hass() {
    return this._hass;
  }

  /**
   * Called by Home Assistant when config is set
   */
  setConfig(config) {
    console.log('EV Trip Planner Panel: setConfig called', config);
    this._config = config;

    // Get vehicle_id from config
    if (config && config.vehicle_id) {
      this._vehicleId = config.vehicle_id;
      console.log('EV Trip Planner Panel: vehicle_id from config:', this._vehicleId);
    } else {
      // Try to get vehicle_id from URL path as fallback
      // URL format: /ev-trip-planner-{vehicle_id}
      const path = window.location.pathname;
      const match = path.match(/\/ev-trip-planner-(.+)/);
      if (match && match[1]) {
        this._vehicleId = match[1];
        console.log('EV Trip Planner Panel: vehicle_id from URL:', this._vehicleId);
      }
    }

    // If hass is already available and not rendered yet, render
    if (this._hass && !this._rendered) {
      this._render();
    } else if (!this._hass) {
      // If hass not available yet, try again after a short delay
      console.log('EV Trip Planner Panel: hass not available yet, will retry');
    }

    // Also try to render if we now have vehicle_id (since hass might have been set before config)
    if (this._vehicleId && this._hass && !this._rendered) {
      console.log('EV Trip Planner Panel: vehicle_id now available after config, rendering');
      this._render();
    }
  }

  /**
   * Poll for hass property since it might be set after connectedCallback
   */
  _startHassPolling() {
    // CRITICAL: Exit immediately if already rendered - no need to poll
    if (this._rendered) {
      console.log('EV Trip Planner Panel: Already rendered, no polling needed');
      return;
    }

    // CRITICAL: Check if polling is already running - prevent multiple poll loops
    if (this._pollStarted) {
      console.log('EV Trip Planner Panel: Polling already running, skipping');
      return;
    }

    // Mark polling as started to prevent multiple poll loops
    this._pollStarted = true;

    const poll = () => {
      // CRITICAL: Exit immediately if already rendered - no need to continue polling
      if (this._rendered) {
        console.log('EV Trip Planner Panel: Already rendered during polling, stopping');
        this._pollStarted = false;
        if (this._pollTimeout) {
          clearTimeout(this._pollTimeout);
          this._pollTimeout = null;
        }
        return;
      }

      // CRITICAL: Check again if polling was stopped by another call
      if (!this._pollStarted) {
        console.log('EV Trip Planner Panel: Polling stopped, exiting');
        return;
      }

      this._initAttempts++;

      // Debug: log the hass state
      console.log('EV Trip Planner Panel: Poll check - _hass:', !!this._hass, 'hass getter:', !!this.hass, '_rendered:', this._rendered);

      // Check if hass is now available - stop polling immediately
      if (this._hass || this.hass) {
        console.log('EV Trip Planner Panel: hass found via polling, stopping');
        // CRITICAL: Stop polling FIRST before any rendering
        this._pollStarted = false;
        if (this._pollTimeout) {
          clearTimeout(this._pollTimeout);
          this._pollTimeout = null;
        }
        // Only render if not already rendered
        if (!this._rendered) {
          this._rendered = true;
          this._render();
        }
        return;
      }

      if (this._initAttempts < this._maxInitAttempts) {
        console.log(`EV Trip Planner Panel: waiting for hass... attempt ${this._initAttempts}/${this._maxInitAttempts}`);
        setTimeout(poll, 500);
      } else {
        console.error('EV Trip Planner Panel: Max init attempts reached, hass not available');
        // Show error message in the panel
        this.innerHTML = `
          <div style="padding: 20px; text-align: center; color: red;">
            <h3>Error: Home Assistant not initialized</h3>
            <p>Please refresh the page or check HA logs.</p>
            <p>Debug: init attempts = ${this._initAttempts}</p>
          </div>
        `;
      }
    };

    // Start polling after a short delay
    this._pollTimeout = setTimeout(poll, 100);
  }

  /**
   * Subscribe to Home Assistant state changes
   */
  _subscribeToStates() {
    if (!this._hass || !this._hass.connection) {
      console.warn('EV Trip Planner Panel: Cannot subscribe - no hass connection');
      return;
    }

    // Normalize vehicle_id to lowercase for matching (sensors are lowercase)
    const lowerVehicleId = this._vehicleId.toLowerCase();

    // Subscribe to all state changes for vehicle sensors
    this._unsubscribe = this._hass.connection.subscribeMessage(
      (message) => {
        if (message.type === 'event' && message.event?.event_type === 'state_changed') {
          const entityId = message.event.data?.entity_id;
          if (entityId && (entityId.startsWith(`sensor.${lowerVehicleId}_`) || entityId.startsWith(`sensor.ev_trip_planner_${lowerVehicleId}`))) {
            console.log('EV Trip Planner Panel: State changed for', entityId);
            this._update();
          }
        }
      },
      { type: 'subscribe_events', event_type: 'state_changed' }
    );
  }

  /**
   * Clean up subscriptions
   */
  _cleanup() {
    if (this._unsubscribe) {
      this._unsubscribe();
      this._unsubscribe = null;
    }
  }

  /**
   * Get vehicle sensor states
   */
  _getVehicleStates() {
    if (!this._hass || !this._hass.states) {
      return {};
    }
    const states = this._hass.states;
    const result = {};

    // Normalize vehicle_id to lowercase for matching (sensors are lowercase)
    const lowerVehicleId = this._vehicleId.toLowerCase();

    // Pattern: sensor.{vehicle_id}_{sensor_name} (direct vehicle sensors)
    const prefix = `sensor.${lowerVehicleId}_`;

    // hass.states is a Map in Home Assistant, use forEach to iterate
    if (states instanceof Map) {
      for (const [entityId, state] of states) {
        if (entityId.startsWith(prefix)) {
          result[entityId] = state;
        }
      }
    } else {
      // Fallback for plain object
      for (const [entityId, state] of Object.entries(states)) {
        if (entityId.startsWith(prefix)) {
          result[entityId] = state;
        }
      }
    }

    return result;
  }

  /**
   * Get a specific sensor value
   */
  _getSensorValue(entityId, attribute = null) {
    // Try to get from hass states directly with the correct prefix
    const hassStates = this._hass?.states || new Map();

    // Normalize vehicle_id to lowercase for matching
    const lowerVehicleId = this._vehicleId.toLowerCase();

    // Try alternative: sensor.{vehicle_id}_{entityId}
    const fullEntityId = `sensor.${lowerVehicleId}_${entityId}`;
    let state = hassStates.get(fullEntityId);

    // If hassStates is a Map, use .get() method
    if (hassStates instanceof Map && !state) {
      state = hassStates.get(fullEntityId);
    }

    if (!state) {
      return 'N/A';
    }

    if (attribute && state.attributes) {
      return state.attributes[attribute];
    }

    return state.state;
  }

  /**
   * Convert entity ID to human-readable name
   */
  _entityIdToName(entityId) {
    // Remove prefix and underscores
    const name = entityId.replace(`sensor.${this._vehicleId}_`, '');
    return name
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  /**
   * Get sensor unit of measurement
   */
  _getUnit(entityId) {
    const states = this._hass?.states || {};
    const state = states[entityId];
    if (state && state.attributes) {
      return state.attributes.unit_of_measurement || '';
    }
    return '';
  }

  /**
   * Format sensor value with unit
   */
  _formatSensorValue(entityId) {
    const states = this._hass?.states || {};
    const state = states[entityId];
    if (!state) {
      return 'No disponible';
    }

    const unit = this._getUnit(entityId);
    const value = state.state;

    if (value === 'unavailable' || value === 'unknown') {
      return 'No disponible';
    }

    return unit ? `${value} ${unit}` : value;
  }

  /**
   * Get sensor icon based on entity type
   */
  _getSensorIcon(entityId) {
    const name = this._entityIdToName(entityId);
    const lowerName = name.toLowerCase();

    if (lowerName.includes('soc') || lowerName.includes('batería') || lowerName.includes('battery')) {
      return '🔋';
    }
    if (lowerName.includes('range') || lowerName.includes('rango') || lowerName.includes('distance')) {
      return '📍';
    }
    if (lowerName.includes('charging') || lowerName.includes('carga')) {
      return '⚡';
    }
    if (lowerName.includes('kwh') || lowerName.includes('energy')) {
      return '💡';
    }
    if (lowerName.includes('hour') || lowerName.includes('hora')) {
      return '⏰';
    }
    if (lowerName.includes('trip') || lowerName.includes('viaje')) {
      return '🚗';
    }
    if (lowerName.includes('next')) {
      return '🎯';
    }

    return '📊';
  }

  /**
   * Check if sensor is a status indicator
   */
  _isStatusSensor(entityId) {
    const name = this._entityIdToName(entityId);
    const lowerName = name.toLowerCase();
    return (
      lowerName.includes('soc') ||
      lowerName.includes('range') ||
      lowerName.includes('charging') ||
      lowerName.includes('status')
    );
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
      other: []
    };

    for (const [entityId, state] of Object.entries(sensors)) {
      const name = this._entityIdToName(entityId);
      const lowerName = name.toLowerCase();

      if (this._isStatusSensor(entityId)) {
        groups.status.push({ entityId, state, name, icon: this._getSensorIcon(entityId) });
      } else if (lowerName.includes('soc') || lowerName.includes('battery')) {
        groups.battery.push({ entityId, state, name, icon: this._getSensorIcon(entityId) });
      } else if (lowerName.includes('trip') || lowerName.includes('viaje')) {
        groups.trips.push({ entityId, state, name, icon: this._getSensorIcon(entityId) });
      } else if (lowerName.includes('kwh') || lowerName.includes('energy')) {
        groups.energy.push({ entityId, state, name, icon: this._getSensorIcon(entityId) });
      } else {
        groups.other.push({ entityId, state, name, icon: this._getSensorIcon(entityId) });
      }
    }

    return groups;
  }

  /**
   * Render the panel
   */
  _render() {
    // CRITICAL: Exit immediately if already rendered to prevent re-rendering
    if (this._rendered) {
      console.log('EV Trip Planner Panel: Already rendered, skipping _render');
      return;
    }

    // CRITICAL: Exit immediately if hass is not available
    if (!this._hass) {
      console.warn('EV Trip Planner Panel: Cannot render - no hass');
      this.innerHTML = `
        <div style="padding: 20px; text-align: center;">
          <p>Waiting for Home Assistant...</p>
        </div>
      `;
      return;
    }

    // Try to get vehicle_id from URL as last resort
    if (!this._vehicleId) {
      console.warn('EV Trip Planner Panel: Trying to get vehicle_id from URL in _render');
      const path = window.location.pathname;
      console.log('EV Trip Planner Panel: URL in _render:', path);

      // Simple split approach
      if (path.includes('ev-trip-planner-')) {
        const parts = path.split('ev-trip-planner-');
        if (parts.length > 1) {
          this._vehicleId = parts[1].split('/')[0];
          console.log('EV Trip Planner Panel: vehicle_id from split in _render:', this._vehicleId);
        }
      }
    }

    if (!this._vehicleId) {
      console.warn('EV Trip Planner Panel: Cannot render - no vehicle_id');
      this.innerHTML = `
        <div style="padding: 20px; text-align: center;">
          <p>No vehicle configured</p>
        </div>
      `;
      return;
    }

    this._rendered = true;
    console.log('EV Trip Planner Panel: Rendering for vehicle', this._vehicleId);

    // Get vehicle states
    const states = this._getVehicleStates();
    const stateKeys = Object.keys(states);
    const groupedSensors = this._groupSensors(states);

    // Build sensor list HTML
    const statusCards = groupedSensors.status.map(s => `
      <div class="status-card">
        <span class="status-icon">${s.icon}</span>
        <span class="status-label">${s.name}</span>
        <span class="status-value">${this._formatSensorValue(s.entityId)}</span>
      </div>
    `).join('');

    const sensorListHtml = Object.entries(groupedSensors)
      .filter(([_, sensors]) => sensors.length > 0)
      .map(([groupName, sensors]) => `
        <div class="sensor-group">
          <h3 class="sensor-group-title">${this._getGroupName(groupName)}</h3>
          ${sensors.map(s => `
            <div class="sensor-item">
              <span class="sensor-icon">${s.icon}</span>
              <span class="sensor-name">${s.name}</span>
              <span class="sensor-value">${this._formatSensorValue(s.entityId)}</span>
            </div>
          `).join('')}
        </div>
      `).join('');

    this.innerHTML = `
      <style>
        ${this._getStyles()}
      </style>
      <div class="panel-container">
        <header class="panel-header">
          <h1>🚗 EV Trip Planner - ${this._vehicleId}</h1>
        </header>
        <main class="panel-content">
          ${statusCards ? `
          <div class="status-section">
            <h2>Vehicle Status</h2>
            <div class="status-grid">
              ${statusCards}
            </div>
          </div>
          ` : ''}
          <div class="sensors-section">
            <h2>Available Sensors (${stateKeys.length})</h2>
            ${stateKeys.length > 0 ? `
              <div class="sensor-list-grouped">
                ${sensorListHtml || '<p class="no-sensors">No sensors found</p>'}
              </div>
            ` : '<p class="no-sensors">No sensors found</p>'}
          </div>
        </main>
      </div>
    `;

    // Subscribe to state changes after render
    this._subscribeToStates();
  }

  /**
   * Update the panel (re-render specific parts)
   */
  _update() {
    if (!this._rendered || !this._hass) {
      return;
    }

    // For now, just re-render the entire panel
    // In production, you'd update specific DOM elements
    this._render();
  }

  /**
   * Get group name for display
   */
  _getGroupName(groupName) {
    const names = {
      status: '📊 Status Indicators',
      battery: '🔋 Battery & Range',
      trips: '🚗 Trips & Journeys',
      energy: '⚡ Energy Consumption',
      other: '📋 Other Sensors'
    };
    return names[groupName] || groupName;
  }

  /**
   * Get CSS styles
   */
  _getStyles() {
    return `
      :host {
        display: block;
        height: 100%;
        background-color: var(--primary-background-color, #fafafa);
        color: var(--primary-text-color, #212121);
        font-family: var(--primary-font-family, Roboto, sans-serif);
      }
      .panel-container {
        height: 100%;
        display: flex;
        flex-direction: column;
      }
      .panel-header {
        background-color: var(--primary-color, #03a9f4);
        color: white;
        padding: 16px;
      }
      .panel-header h1 {
        margin: 0;
        font-size: 20px;
      }
      .panel-content {
        flex: 1;
        padding: 16px;
        overflow-y: auto;
      }
      .status-section, .sensors-section {
        margin-bottom: 24px;
      }
      h2 {
        font-size: 16px;
        margin-bottom: 12px;
        color: var(--secondary-text-color, #757575);
      }
      .status-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
      }
      .status-card {
        background: var(--card-background-color, white);
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        cursor: pointer;
        transition: transform 0.2s, box-shadow 0.2s;
      }
      .status-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 3px 6px rgba(0,0,0,0.15);
      }
      .status-icon {
        font-size: 24px;
        display: block;
        margin-bottom: 8px;
      }
      .status-label {
        display: block;
        font-size: 12px;
        color: var(--secondary-text-color, #757575);
        margin-bottom: 4px;
        text-transform: capitalize;
      }
      .status-value {
        display: block;
        font-size: 20px;
        font-weight: 600;
        color: var(--primary-color, #03a9f4);
      }
      .sensor-list-grouped {
        background: var(--card-background-color, white);
        border-radius: 8px;
        padding: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
      }
      .sensor-group {
        margin-bottom: 16px;
      }
      .sensor-group:last-child {
        margin-bottom: 0;
      }
      .sensor-group-title {
        font-size: 14px;
        font-weight: 600;
        color: var(--primary-color, #03a9f4);
        margin-bottom: 8px;
        padding-bottom: 4px;
        border-bottom: 2px solid var(--primary-color, #03a9f4);
      }
      .sensor-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 8px;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
        transition: background-color 0.2s;
      }
      .sensor-item:hover {
        background-color: rgba(3, 169, 244, 0.05);
      }
      .sensor-item:last-child {
        border-bottom: none;
      }
      .sensor-icon {
        font-size: 16px;
        margin-right: 8px;
        width: 24px;
        text-align: center;
      }
      .sensor-name {
        flex: 1;
        font-size: 14px;
        color: var(--primary-text-color, #212121);
        font-weight: 500;
        text-transform: capitalize;
        margin-right: 8px;
      }
      .sensor-value {
        font-size: 14px;
        font-weight: 600;
        color: var(--primary-color, #03a9f4);
        white-space: nowrap;
      }
      .no-sensors {
        text-align: center;
        color: var(--secondary-text-color, #757575);
        padding: 20px;
      }
      @media (max-width: 600px) {
        .status-grid {
          grid-template-columns: repeat(2, 1fr);
        }
        .status-value {
          font-size: 16px;
        }
      }
    `;
  }
}

// Register the custom element
customElements.define('ev-trip-planner-panel', EVTripPlannerPanel);
