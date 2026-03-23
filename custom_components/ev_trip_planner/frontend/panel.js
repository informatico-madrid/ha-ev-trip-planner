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
   * Get vehicle sensor states
   */
  _getVehicleStates() {
    if (!this._hass || !this._hass.states) {
      return {};
    }
    const states = this._hass.states;
    // Use the correct prefix for EV Trip Planner sensors: sensor.ev_trip_planner_{vehicle_id}_{sensor_name}
    const prefix = `sensor.ev_trip_planner_${this._vehicleId}`;
    const result = {};
    
    for (const [entityId, state] of Object.entries(states)) {
      if (entityId.startsWith(prefix)) {
        result[entityId] = state;
      }
    }
    
    return result;
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
