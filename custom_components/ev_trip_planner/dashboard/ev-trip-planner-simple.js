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
   * Extracts vehicle_id from URL BEFORE waiting for hass
   */
  connectedCallback() {
    console.log('=== EV Trip Planner Panel: connectedCallback START ===');
    console.log('EV Trip Planner Panel: full URL:', window.location.href);
    console.log('EV Trip Planner Panel: pathname:', window.location.pathname);
    console.log('EV Trip Planner Panel: hash:', window.location.hash);
    console.log('EV Trip Planner Panel: initial vehicle_id:', this._vehicleId);
    console.log('EV Trip Planner Panel: initial hass:', this._hass ? 'available' : 'null');

    // CRITICAL: Get vehicle_id from URL BEFORE waiting for hass
    // This ensures vehicle_id is available even if hass/config timing is off
    const extracted = this._extractVehicleIdFromUrl();

    console.log('EV Trip Planner Panel: extracted vehicle_id:', this._vehicleId);
    console.log('EV Trip Planner Panel: _extractVehicleIdFromUrl returned:', extracted);
    console.log('=== EV Trip Planner Panel: connectedCallback END ===');

    // Start polling for hass after vehicle_id is extracted
    this._startHassPolling();
  }

  /**
   * Extract vehicle_id from the URL path or hash
   * This is called in connectedCallback to get vehicle_id BEFORE waiting for hass
   * @returns {boolean} true if vehicle_id was extracted successfully
   */
  _extractVehicleIdFromUrl() {
    // URL format: /ev-trip-planner-{vehicle_id}
    const path = window.location.pathname;
    const hash = window.location.hash;
    const href = window.location.href;

    console.log('=== EV Trip Planner Panel: _extractVehicleIdFromUrl START ===');
    console.log('EV Trip Planner Panel: URL details:');
    console.log('  - pathname:', path);
    console.log('  - hash:', hash);
    console.log('  - href:', href);
    console.log('EV Trip Planner Panel: current vehicle_id:', this._vehicleId);

    let extracted = false;

    // Method 1: Regex match on pathname
    console.log('EV Trip Planner Panel: Attempt 1 - Regex match on pathname');
    const match = path.match(/\/ev-trip-planner-(.+)/);
    if (match && match[1]) {
      this._vehicleId = match[1];
      console.log('EV Trip Planner Panel: ✓ vehicle_id from pathname regex:', this._vehicleId);
      extracted = true;
    } else {
      console.log('EV Trip Planner Panel: ✗ Regex match failed on pathname');
    }

    // Method 2: Hash routing (fallback)
    if (!extracted && hash) {
      console.log('EV Trip Planner Panel: Attempt 2 - Hash routing');
      const hashMatch = hash.match(/\/ev-trip-planner-(.+)/);
      if (hashMatch && hashMatch[1]) {
        this._vehicleId = hashMatch[1];
        console.log('EV Trip Planner Panel: ✓ vehicle_id from hash:', this._vehicleId);
        extracted = true;
      } else {
        console.log('EV Trip Planner Panel: ✗ No vehicle_id in hash');
      }
    }

    // Method 3: Simple split (last resort)
    if (!extracted && path.includes('ev-trip-planner-')) {
      console.log('EV Trip Planner Panel: Attempt 3 - Simple split fallback');
      const parts = path.split('ev-trip-planner-');
      if (parts.length > 1) {
        this._vehicleId = parts[1].split('/')[0];
        console.log('EV Trip Planner Panel: ✓ vehicle_id from split:', this._vehicleId);
        extracted = true;
      } else {
        console.log('EV Trip Planner Panel: ✗ Split did not produce parts');
      }
    }

    if (!extracted) {
      console.log('EV Trip Planner Panel: ✗ No vehicle_id found in URL');
      console.log('EV Trip Planner Panel: Available URL parts:');
      console.log('  - pathname includes "ev-trip-planner-":', path.includes('ev-trip-planner-'));
      console.log('  - hash:', hash || '(empty)');
    }

    console.log('EV Trip Planner Panel: Final vehicle_id after extraction:', this._vehicleId);
    console.log('EV Trip Planner Panel: _extractVehicleIdFromUrl returning:', extracted);
    console.log('=== EV Trip Planner Panel: _extractVehicleIdFromUrl END ===');

    return extracted;
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
    console.log('=== EV Trip Planner Panel: hass setter START ===');
    console.log('EV Trip Planner Panel: hass setter called:', hass ? 'available' : 'null', 'attempts:', this._initAttempts);
    console.log('EV Trip Planner Panel: URL in hass setter:', window.location.href);
    console.log('EV Trip Planner Panel: pathname in hass setter:', window.location.pathname);
    console.log('EV Trip Planner Panel: vehicle_id before hass set:', this._vehicleId);

    this._hass = hass;
    this._initAttempts = 0; // Reset attempts on successful hass set

    // Try to get vehicle_id from URL - multiple approaches
    if (!this._vehicleId) {
      console.log('EV Trip Planner Panel: No vehicle_id yet, attempting extraction in hass setter');
      const path = window.location.pathname;
      console.log('EV Trip Planner Panel: pathname:', path);

      // Method 1: Simple split approach
      console.log('EV Trip Planner Panel: Attempting Method 1 - Simple split');
      if (path.includes('ev-trip-planner-')) {
        const parts = path.split('ev-trip-planner-');
        if (parts.length > 1) {
          this._vehicleId = parts[1].split('/')[0];
          console.log('EV Trip Planner Panel: ✓ vehicle_id from split:', this._vehicleId);
        } else {
          console.log('EV Trip Planner Panel: ✗ Split did not produce parts');
        }
      } else {
        console.log('EV Trip Planner Panel: ✗ pathname does not include "ev-trip-planner-"');
      }

      // Method 2: regex (keep for backward compatibility)
      if (!this._vehicleId) {
        console.log('EV Trip Planner Panel: Attempting Method 2 - Regex');
        const match = path.match(/\/ev-trip-planner-(.+)/);
        if (match && match[1]) {
          this._vehicleId = match[1];
          console.log('EV Trip Planner Panel: ✓ vehicle_id from regex:', this._vehicleId);
        } else {
          console.log('EV Trip Planner Panel: ✗ Regex did not match');
        }
      }

      // Method 3: from hash
      if (!this._vehicleId && window.location.hash) {
        console.log('EV Trip Planner Panel: Attempting Method 3 - Hash');
        const hashMatch = window.location.hash.match(/\/ev-trip-planner-(.+)/);
        if (hashMatch && hashMatch[1]) {
          this._vehicleId = hashMatch[1];
          console.log('EV Trip Planner Panel: ✓ vehicle_id from hash:', this._vehicleId);
        } else {
          console.log('EV Trip Planner Panel: ✗ Hash did not match');
        }
      }
    }

    console.log('EV Trip Planner Panel: Final vehicle_id after hass setter:', this._vehicleId);
    console.log('=== EV Trip Planner Panel: hass setter END ===');

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
    console.log('=== EV Trip Planner Panel: _startHassPolling START ===');
    console.log('EV Trip Planner Panel: Initial state for polling:');
    console.log('  - hass:', this._hass ? 'available' : 'null');
    console.log('  - vehicle_id:', this._vehicleId);
    console.log('  - initAttempts:', this._initAttempts);
    console.log('=== EV Trip Planner Panel: _startHassPolling END ===');

    const poll = () => {
      this._initAttempts++;

      console.log('=== EV Trip Planner Panel: Poll attempt #' + this._initAttempts + ' START ===');
      console.log('EV Trip Planner Panel: Poll state:');
      console.log('  - hass:', this._hass ? 'available' : 'null');
      console.log('  - vehicle_id:', this._vehicleId);

      // Check if vehicle_id is available - critical for rendering
      if (!this._vehicleId) {
        console.warn('EV Trip Planner Panel: ⚠️ vehicle_id still not available, retrying extraction');
        console.log('EV Trip Planner Panel: Extracting vehicle_id from URL...');
        this._extractVehicleIdFromUrl();
        console.log('EV Trip Planner Panel: vehicle_id after extraction:', this._vehicleId);
      }

      // Check if hass is now available as a property
      if (this._hass && !this._rendered && this._vehicleId) {
        console.log('✓ EV Trip Planner Panel: hass found via polling with vehicle_id:', this._vehicleId);
        console.log('=== EV Trip Planner Panel: Poll attempt #' + this._initAttempts + ' END - SUCCESS ===');
        this._render();
        return;
      }

      // Also try reading directly from element properties (HA sets these)
      if (this.hass && !this._rendered && this._vehicleId) {
        console.log('✓ EV Trip Planner Panel: hass found via getter with vehicle_id:', this._vehicleId);
        this._hass = this.hass;
        this._render();
        return;
      }

      if (this._initAttempts < this._maxInitAttempts) {
        console.log(`EV Trip Planner Panel: waiting for hass... attempt ${this._initAttempts}/${this._maxInitAttempts}`);
        console.log('=== EV Trip Planner Panel: Poll attempt #' + this._initAttempts + ' END - PENDING ===');
        setTimeout(poll, 500);
      } else {
        console.error('✗ EV Trip Planner Panel: Max init attempts reached, hass not available');
        console.error('Final state:');
        console.error('  - initAttempts:', this._initAttempts);
        console.error('  - vehicle_id:', this._vehicleId || 'not found');
        console.error('  - hass:', this._hass ? 'available' : 'null');
        // Show error message in the panel
        this.innerHTML = `
          <div style="padding: 20px; text-align: center; color: red;">
            <h3>Error: Home Assistant not initialized</h3>
            <p>Please refresh the page or check HA logs.</p>
            <p>Debug: init attempts = ${this._initAttempts}, vehicle_id = ${this._vehicleId || 'not found'}</p>
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
   * Get vehicle sensor states
   * @returns {Object} Object containing vehicle sensor states
   */
  _getVehicleStates() {
    console.log('=== EV Trip Planner Panel: _getVehicleStates START ===');

    if (!this._hass) {
      console.warn('EV Trip Planner Panel: hass not available in _getVehicleStates');
      console.log('=== EV Trip Planner Panel: _getVehicleStates END (no hass) ===');
      return {};
    }

    if (!this._hass.states) {
      console.warn('EV Trip Planner Panel: hass.states not available in _getVehicleStates');
      console.log('=== EV Trip Planner Panel: _getVehicleStates END (no states) ===');
      return {};
    }

    const states = this._hass.states;
    // Use the correct prefix for EV Trip Planner sensors: sensor.ev_trip_planner_{vehicle_id}_{sensor_name}
    const prefix = `sensor.ev_trip_planner_${this._vehicleId}`;
    const result = {};

    console.log('EV Trip Planner Panel: Searching for sensors with prefix:', prefix);
    console.log('EV Trip Planner Panel: Total entities in hass.states:', Object.keys(states).length);

    for (const [entityId, state] of Object.entries(states)) {
      if (entityId.startsWith(prefix)) {
        result[entityId] = state;
        console.log('EV Trip Planner Panel: Found sensor:', entityId, 'state:', state.state);
      }
    }

    console.log('EV Trip Planner Panel: Found', Object.keys(result).length, 'sensors');
    console.log('=== EV Trip Planner Panel: _getVehicleStates END ===');

    return result;
  }

  /**
   * Get a specific sensor value
   * @param {string} entityId - The sensor entity ID (without prefix)
   * @param {string|null} attribute - Optional attribute to retrieve
   * @returns {string} The sensor value or 'N/A' if not found
   */
  _getSensorValue(entityId, attribute = null) {
    // Try to get from hass states directly with the correct prefix
    const hassStates = this._hass?.states || {};

    console.log('EV Trip Planner Panel: Getting sensor value for:', entityId);
    console.log('EV Trip Planner Panel: Total entities in hass.states:', Object.keys(hassStates).length);

    // Try full entity ID first: sensor.ev_trip_planner_{vehicle_id}_{entityId}
    let fullEntityId = entityId.startsWith('sensor.') ? entityId : `sensor.ev_trip_planner_${this._vehicleId}_${entityId}`;
    let state = hassStates[fullEntityId];

    console.log('EV Trip Planner Panel: Trying entity:', fullEntityId);

    if (!state) {
      // Try alternative: sensor.{vehicle_id}_{entityId}
      console.log('EV Trip Planner Panel: First attempt failed, trying alternative...');
      fullEntityId = `sensor.${this._vehicleId}_${entityId}`;
      state = hassStates[fullEntityId];
      console.log('EV Trip Planner Panel: Trying alternative entity:', fullEntityId);
    }

    if (!state) {
      console.log('EV Trip Planner Panel: Sensor not found:', entityId);
      return 'N/A';
    }

    let value;
    if (attribute && state.attributes) {
      value = state.attributes[attribute];
      console.log('EV Trip Planner Panel: Retrieved attribute:', attribute, 'value:', value);
    } else {
      value = state.state;
      console.log('EV Trip Planner Panel: Retrieved state value:', value);
    }

    return value;
  }

  /**
   * Render the panel
   */
  _render() {
    console.log('=== EV Trip Planner Panel: _render START ===');
    console.log('EV Trip Planner Panel: _render called with:');
    console.log('  - hass:', this._hass ? 'available' : 'null');
    console.log('  - vehicle_id:', this._vehicleId);
    console.log('  - _rendered:', this._rendered);

    if (!this._hass) {
      console.warn('✗ EV Trip Planner Panel: Cannot render - no hass');
      this.innerHTML = `
        <div style="padding: 20px; text-align: center;">
          <p>Waiting for Home Assistant...</p>
        </div>
      `;
      console.log('=== EV Trip Planner Panel: _render END (early exit - no hass) ===');
      return;
    }

    // Try to get vehicle_id from URL as last resort (comprehensive fallback)
    if (!this._vehicleId) {
      console.warn('⚠️ EV Trip Planner Panel: vehicle_id missing, attempting extraction in _render');
      console.log('EV Trip Planner Panel: Current URL:', window.location.href);
      console.log('EV Trip Planner Panel: Current pathname:', window.location.pathname);
      console.log('EV Trip Planner Panel: Current hash:', window.location.hash);
      this._extractVehicleIdFromUrl();
      if (this._vehicleId) {
        console.log('✓ EV Trip Planner Panel: vehicle_id extracted in _render:', this._vehicleId);
      } else {
        console.error('✗ EV Trip Planner Panel: Failed to extract vehicle_id in _render');
      }
    }

    if (!this._vehicleId) {
      console.error('✗ EV Trip Planner Panel: Cannot render - no vehicle_id');
      this.innerHTML = `
        <div style="padding: 20px; text-align: center; color: red;">
          <h3>Error: No vehicle configured</h3>
          <p>Debug information:</p>
          <ul>
            <li>URL: ${window.location.href}</li>
            <li>pathname: ${window.location.pathname}</li>
            <li>hash: ${window.location.hash}</li>
          </ul>
          <p>Please navigate to the correct panel URL: /ev-trip-planner-{vehicle_id}</p>
        </div>
      `;
      console.log('=== EV Trip Planner Panel: _render END (early exit - no vehicle_id) ===');
      return;
    }

    this._rendered = true;
    console.log('✓ EV Trip Planner Panel: Rendering panel for vehicle:', this._vehicleId);

    // Get vehicle states
    const states = this._getVehicleStates();
    const stateKeys = Object.keys(states);

    this.innerHTML = `
      <style>
        ${this._getStyles()}
      </style>
      <div class="panel-container">
        <header class="panel-header">
          <h1>🚗 EV Trip Planner - ${this._vehicleId}</h1>
        </header>
        <main class="panel-content">
          <div class="status-section">
            <h2>Vehicle Status</h2>
            <div class="status-grid">
              <div class="status-card">
                <span class="status-label">SOC</span>
                <span class="status-value">${this._getSensorValue('soc')}%</span>
              </div>
              <div class="status-card">
                <span class="status-label">Range</span>
                <span class="status-value">${this._getSensorValue('range')} km</span>
              </div>
              <div class="status-card">
                <span class="status-label">Charging</span>
                <span class="status-value">${this._getSensorValue('charging')}</span>
              </div>
            </div>
          </div>
          <div class="sensors-section">
            <h2>Available Sensors (${stateKeys.length})</h2>
            <div class="sensor-list">
              ${stateKeys.length > 0 ? stateKeys.map(key => `
                <div class="sensor-item">
                  <span class="sensor-name">${key}</span>
                  <span class="sensor-value">${states[key].state}</span>
                </div>
              `).join('') : '<p>No sensors found</p>'}
            </div>
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
      }
      .status-label {
        display: block;
        font-size: 12px;
        color: var(--secondary-text-color, #757575);
        margin-bottom: 4px;
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
      .sensor-item {
        display: flex;
        justify-content: space-between;
        padding: 8px;
        border-bottom: 1px solid var(--divider-color, #e0e0e0);
      }
      .sensor-item:last-child {
        border-bottom: none;
      }
      .sensor-name {
        font-size: 14px;
        color: var(--primary-text-color, #212121);
      }
      .sensor-value {
        font-size: 14px;
        font-weight: 500;
        color: var(--primary-color, #03a9f4);
      }
    `;
  }
}

// Register the custom element
customElements.define('ev-trip-planner-panel', EVTripPlannerPanel);
