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
    this._initAttempts = 0;
    this._maxInitAttempts = 10;
    console.log('EV Trip Planner Panel: Constructor called');
  }

  /**
   * Called when the panel is attached to the DOM
   */
  connectedCallback() {
    console.log('EV Trip Planner Panel: connectedCallback');
    console.log('EV Trip Planner Panel: full URL:', window.location.href);
    console.log('EV Trip Planner Panel: pathname:', window.location.pathname);
    console.log('EV Trip Planner Panel: hash:', window.location.hash);
    
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
    this._hass = hass;
    this._initAttempts = 0; // Reset attempts on successful hass set
    
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
    
    // If hass is already available, render
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
    const poll = () => {
      this._initAttempts++;
      
      // Check if hass is now available as a property
      if (this._hass && !this._rendered) {
        console.log('EV Trip Planner Panel: hass found via polling, rendering');
        this._render();
        return;
      }
      
      // Also try reading directly from element properties (HA sets these)
      if (this.hass && !this._rendered) {
        console.log('EV Trip Planner Panel: hass found via getter, rendering');
        this._hass = this.hass;
        this._render();
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
    setTimeout(poll, 100);
  }

  /**
   * Subscribe to Home Assistant state changes
   */
  _subscribeToStates() {
    if (!this._hass || !this._hass.connection) {
      console.warn('EV Trip Planner Panel: Cannot subscribe - no hass connection');
      return;
    }

    // Subscribe to all state changes
    this._unsubscribe = this._hass.connection.subscribeMessage(
      (message) => {
        if (message.type === 'event' && message.event?.event_type === 'state_changed') {
          const entityId = message.event.data?.entity_id;
          if (entityId && entityId.startsWith(`sensor.${this._vehicleId}`)) {
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
   * Get all vehicle sensor states
   *
   * This method retrieves ALL sensors associated with the vehicle, including:
   * - EV Trip Planner sensors (sensor.ev_trip_planner_{entry_id}_{sensor_name})
   * - Trip sensors (sensor.trip_{trip_id})
   * - Any other sensors registered to the vehicle's device
   *
   * @returns {Object} Dictionary of entity IDs to state objects
   */
  _getVehicleStates() {
    if (!this._hass || !this._hass.states) {
      return {};
    }

    const states = this._hass.states;
    const result = {};

    // Collect all vehicle-related sensors
    for (const [entityId, state] of Object.entries(states)) {
      // Skip if no state available
      if (!state) {
        continue;
      }

      // Include EV Trip Planner sensors (all domains under ev_trip_planner)
      if (entityId.startsWith('sensor.ev_trip_planner_')) {
        result[entityId] = state;
        continue;
      }

      // Include trip sensors (sensor.trip_{trip_id})
      if (entityId.startsWith('sensor.trip_')) {
        result[entityId] = state;
        continue;
      }

      // Include any other sensors that might be registered to this vehicle
      // Check if the entity has device_info pointing to our vehicle
      if (state.attributes && state.attributes.device_id) {
        // Get the device and check if it belongs to our vehicle
        // The device identifier pattern is (DOMAIN, vehicle_id)
        // We look for entities that have our vehicle_id in their attributes or name
        const deviceId = state.attributes.device_id;
        if (deviceId && deviceId.includes(this._vehicleId)) {
          result[entityId] = state;
        }
      }
    }

    return result;
  }

  /**
   * Convert entity ID to a human-readable name
   * @param {string} entityId - The entity ID (e.g., sensor.ev_trip_planner_morgan_soc)
   * @returns {string} Human-readable name (e.g., "State of Charge")
   */
  _entityIdToName(entityId) {
    // Remove prefix and split by underscores
    const name = entityId
      .replace('sensor.ev_trip_planner_', '')
      .replace('sensor.trip_', '')
      .replace('sensor.', '')
      .split('_')
      .map((word, index) => {
        // Capitalize first letter of each word
        if (word.length === 0) return '';
        return word.charAt(0).toUpperCase() + word.slice(1);
      })
      .join(' ');

    return name || entityId;
  }

  /**
   * Get the unit of measurement for an entity
   * @param {string} entityId - The entity ID
   * @param {Object} state - The state object
   * @returns {string} Unit of measurement or empty string
   */
  _getUnit(entityId, state) {
    if (state.attributes && state.attributes.unit_of_measurement) {
      return state.attributes.unit_of_measurement;
    }
    return '';
  }

  /**
   * Format a sensor value for display
   * @param {string} entityId - The entity ID
   * @param {Object} state - The state object
   * @returns {string} Formatted value for display
   */
  _formatSensorValue(entityId, state) {
    const stateValue = state.state;

    // Handle unavailable or unknown states
    if (stateValue === 'unavailable' || stateValue === 'unknown' || stateValue === 'none') {
      return '<span style="color: var(--secondary-text-color, #757575);">No disponible</span>';
    }

    // Try to get display value from attributes first
    if (state.attributes && state.attributes.device_class === 'battery') {
      return `${stateValue}%`;
    }

    if (state.attributes && state.attributes.device_class === 'distance') {
      return `${stateValue} km`;
    }

    if (state.attributes && state.attributes.device_class === 'energy') {
      return `${stateValue} kWh`;
    }

    if (state.attributes && state.attributes.device_class === 'power') {
      return `${stateValue} kW`;
    }

    if (state.attributes && state.attributes.device_class === 'current') {
      return `${stateValue} A`;
    }

    if (state.attributes && state.attributes.device_class === 'voltage') {
      return `${stateValue} V`;
    }

    // Format numeric values
    const numericValue = parseFloat(stateValue);
    if (!isNaN(numericValue)) {
      // Format with appropriate precision
      if (numericValue >= 1000) {
        return `${Math.round(numericValue)}`;
      } else if (numericValue >= 100) {
        return `${Math.round(numericValue)}`;
      } else if (numericValue >= 10) {
        return numericValue.toFixed(1);
      } else {
        return numericValue.toFixed(2);
      }
    }

    // Return string value as-is
    return stateValue;
  }

  /**
   * Get the icon for a sensor based on its entity ID
   * @param {string} entityId - The entity ID
   * @returns {string} Emoji icon
   */
  _getSensorIcon(entityId) {
    const name = entityId.toLowerCase();

    if (name.includes('soc') || name.includes('battery')) {
      return '🔋';
    }
    if (name.includes('range')) {
      return '📍';
    }
    if (name.includes('charging')) {
      return '⚡';
    }
    if (name.includes('charge')) {
      return '🔌';
    }
    if (name.includes('trip') || name.includes('destination')) {
      return '🚗';
    }
    if (name.includes('consumption') || name.includes('energy')) {
      return '💡';
    }
    if (name.includes('distance') || name.includes('range')) {
      return '📏';
    }
    if (name.includes('speed')) {
      return '🚀';
    }
    if (name.includes('temperature')) {
      return '🌡️';
    }
    if (name.includes('power')) {
      return '⚡';
    }
    if (name.includes('voltage')) {
      return '🔋';
    }
    if (name.includes('current')) {
      return 'A';
    }

    // Default icon for unknown sensors
    return '📊';
  }

  /**
   * Check if a sensor should be displayed in the status section
   * @param {string} entityId - The entity ID
   * @returns {boolean} True if sensor should be shown in status section
   */
  _isStatusSensor(entityId) {
    const name = entityId.toLowerCase();
    const statusSensors = [
      'soc',
      'state_of_charge',
      'battery_level',
      'range',
      'charging',
      'is_charging',
      'trip_distance',
      'total_distance',
    ];
    return statusSensors.some((sensor) => name.includes(sensor));
  }

  /**
   * Group sensors by category for better organization
   * @param {Object} states - Dictionary of entity IDs to states
   * @returns {Object} Organized groups of sensors
   */
  _groupSensors(states) {
    const groups = {
      status: [],
      battery: [],
      trip: [],
      energy: [],
      other: [],
    };

    for (const [entityId, state] of Object.entries(states)) {
      if (!state) continue;

      const name = entityId.toLowerCase();

      // Check if it should be in status section
      if (this._isStatusSensor(entityId)) {
        groups.status.push({ entityId, state });
        continue;
      }

      // Group by category
      if (name.includes('battery') || name.includes('soc') || name.includes('charge')) {
        groups.battery.push({ entityId, state });
      } else if (
        name.includes('trip') ||
        name.includes('destination') ||
        name.includes('range')
      ) {
        groups.trip.push({ entityId, state });
      } else if (
        name.includes('consumption') ||
        name.includes('energy') ||
        name.includes('power') ||
        name.includes('kwh')
      ) {
        groups.energy.push({ entityId, state });
      } else {
        groups.other.push({ entityId, state });
      }
    }

    return groups;
  }

  /**
   * Get a specific sensor value
   */
  _getSensorValue(entityId, attribute = null) {
    // Try to get from hass states directly with the correct prefix
    const hassStates = this._hass?.states || {};
    
    // Try full entity ID first: sensor.ev_trip_planner_{vehicle_id}_{entityId}
    let fullEntityId = entityId.startsWith('sensor.') ? entityId : `sensor.ev_trip_planner_${this._vehicleId}_${entityId}`;
    let state = hassStates[fullEntityId];
    
    if (!state) {
      // Try alternative: sensor.{vehicle_id}_{entityId}
      fullEntityId = `sensor.${this._vehicleId}_${entityId}`;
      state = hassStates[fullEntityId];
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
   * Render the panel
   */
  _render() {
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

    // Group sensors by category
    const groups = this._groupSensors(states);

    // Build status cards dynamically
    const statusCards = groups.status.map(({ entityId, state }) => {
      const name = this._entityIdToName(entityId);
      const formattedValue = this._formatSensorValue(entityId, state);
      const icon = this._getSensorIcon(entityId);
      return `
        <div class="status-card">
          <span class="status-label">${icon} ${name}</span>
          <span class="status-value">${formattedValue}</span>
        </div>
      `;
    }).join('');

    // Build sensor list for each group
    const buildSensorList = (group, title) => {
      if (group.length === 0) return '';
      return `
        <div class="sensor-group">
          <h3>📊 ${title} (${group.length})</h3>
          ${group.map(({ entityId, state }) => `
            <div class="sensor-item">
              <div class="sensor-info">
                <span class="sensor-name">${this._getSensorIcon(entityId)} ${this._entityIdToName(entityId)}</span>
                ${state.attributes && state.attributes.unit_of_measurement ? `<span class="sensor-unit">(${state.attributes.unit_of_measurement})</span>` : ''}
              </div>
              <div class="sensor-value">${this._formatSensorValue(entityId, state)}</div>
            </div>
          `).join('')}
        </div>
      `;
    };

    const batterySection = buildSensorList(groups.battery, 'Batería');
    const tripSection = buildSensorList(groups.trip, 'Viajes');
    const energySection = buildSensorList(groups.energy, 'Energía');
    const otherSection = buildSensorList(groups.other, 'Otros');

    // Combine all sections
    const allSensorsSections = [batterySection, tripSection, energySection, otherSection].filter(s => s !== '').join('');

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
            <h2>Estado del Vehículo</h2>
            <div class="status-grid">
              ${statusCards}
            </div>
          </div>
          ` : ''}
          <div class="sensors-section">
            <h2>Sensores Disponibles (${stateKeys.length})</h2>
            ${stateKeys.length > 0 ? allSensorsSections : '<p class="no-sensors">No hay sensores disponibles</p>'}
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
      .no-sensors {
        text-align: center;
        color: var(--secondary-text-color, #757575);
        padding: 20px;
      }
      .status-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 12px;
      }
      .status-card {
        background: var(--card-background-color, white);
        border-radius: 8px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
      }
      .status-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 3px 6px rgba(0,0,0,0.16);
      }
      .status-label {
        display: block;
        font-size: 12px;
        color: var(--secondary-text-color, #757575);
        margin-bottom: 8px;
      }
      .status-value {
        display: block;
        font-size: 24px;
        font-weight: bold;
        color: var(--primary-color, #03a9f4);
      }
      .sensor-list {
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
      .sensor-group h3 {
        font-size: 14px;
        margin: 0 0 8px 0;
        color: var(--primary-color, #03a9f4);
        padding-bottom: 8px;
        border-bottom: 2px solid var(--divider-color, #e0e0e0);
      }
      .sensor-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 10px 8px;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
        transition: background-color 0.2s ease;
      }
      .sensor-item:hover {
        background-color: var(--secondary-background-color, #f5f5f5);
      }
      .sensor-item:last-child {
        border-bottom: none;
      }
      .sensor-info {
        display: flex;
        align-items: center;
        gap: 8px;
        flex: 1;
        min-width: 0;
      }
      .sensor-name {
        font-size: 14px;
        color: var(--primary-text-color, #212121);
        font-weight: 500;
        flex: 1;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .sensor-unit {
        font-size: 12px;
        color: var(--secondary-text-color, #757575);
        margin-left: 8px;
        flex-shrink: 0;
      }
      .sensor-value {
        font-size: 14px;
        font-weight: 600;
        color: var(--primary-color, #03a9f4);
        padding: 4px 8px;
        background-color: var(--primary-background-color, #f5f5f5);
        border-radius: 4px;
        min-width: 80px;
        text-align: right;
      }
      /* Responsive adjustments */
      @media (max-width: 600px) {
        .status-grid {
          grid-template-columns: 1fr;
        }
        .status-card {
          padding: 12px;
        }
        .status-value {
          font-size: 20px;
        }
        .sensor-item {
          flex-direction: column;
          align-items: flex-start;
          gap: 8px;
        }
        .sensor-value {
          width: 100%;
          text-align: left;
        }
      }
    `;
  }
}

// Register the custom element
customElements.define('ev-trip-planner-panel', EVTripPlannerPanel);
