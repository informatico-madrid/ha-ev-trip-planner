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
    this._pollTimeout = null;
    this._pollStarted = false; // Track if polling has already started
    console.log('EV Trip Planner Panel: Constructor called');
  }

  /**
   * Called when the panel is attached to the DOM
   */
  connectedCallback() {
    console.log('EV Trip Planner Panel: connectedCallback called');
    console.log('EV Trip Planner Panel: full URL:', window.location.href);
    console.log('EV Trip Planner Panel: pathname:', window.location.pathname);
    console.log('EV Trip Planner Panel: hash:', window.location.hash);
    console.log('EV Trip Planner Panel: _rendered:', this._rendered, '_pollStarted:', this._pollStarted);
    console.log('EV Trip Planner Panel: innerHTML.length:', this.innerHTML.length);
    console.log('EV Trip Planner Panel: innerHTML includes EV Trip Planner:', this.innerHTML.includes('EV Trip Planner'));

    // CRITICAL: Exit early if already fully rendered with content
    // This prevents re-rendering if the panel is already complete
    const hasContent = this.innerHTML.length > 0 && this.innerHTML.includes('EV Trip Planner');
    if (this._rendered && hasContent) {
      console.log('EV Trip Planner Panel: Already fully rendered with content, exiting connectedCallback');
      return;
    }

    // CRITICAL: Reset _rendered flag if innerHTML is empty (indicates failed render)
    // This handles race conditions where _rendered was set prematurely
    if (this._rendered && !hasContent) {
      console.log('EV Trip Planner Panel: _rendered=true but no content, resetting to false for re-render');
      this._rendered = false;
    }

    // CRITICAL: Exit if polling already started to prevent multiple poll loops
    if (this._pollStarted) {
      console.log('EV Trip Planner Panel: Polling already started, exiting connectedCallback');
      return;
    }

    // CRITICAL: Mark polling as started BEFORE doing anything else
    // This prevents multiple connectedCallback calls from starting separate polling loops
    this._pollStarted = true;
    console.log('EV Trip Planner Panel: Marked _pollStarted=true');

    // CRITICAL: Get vehicle_id from URL as early as possible - ALWAYS do this FIRST
    // URL format: /ev-trip-planner-{vehicle_id}
    const path = window.location.pathname;
    console.log('EV Trip Planner Panel: trying to extract from path:', path);

    // Method 1: Simple split approach (most reliable)
    if (path.includes('ev-trip-planner-')) {
      const parts = path.split('ev-trip-planner-');
      if (parts.length > 1) {
        const potentialId = parts[1].split('/')[0];
        if (potentialId) {
          this._vehicleId = potentialId;
          console.log('EV Trip Planner Panel: vehicle_id from split:', this._vehicleId);
        }
      }
    }

    // Method 2: regex (fallback)
    if (!this._vehicleId) {
      const match = path.match(/\/ev-trip-planner-(.+)/);
      if (match && match[1]) {
        this._vehicleId = match[1];
        console.log('EV Trip Planner Panel: vehicle_id from regex:', this._vehicleId);
      }
    }

    // Method 3: from hash (fallback)
    if (!this._vehicleId && window.location.hash) {
      const hashMatch = window.location.hash.match(/\/ev-trip-planner-(.+)/);
      if (hashMatch && hashMatch[1]) {
        this._vehicleId = hashMatch[1];
        console.log('EV Trip Planner Panel: vehicle_id from hash:', this._vehicleId);
      }
    }

    console.log('EV Trip Planner Panel: Final vehicle_id:', this._vehicleId);

    // CRITICAL: Check if we already have hass and vehicleId - render immediately
    if (this._hass && this._vehicleId) {
      console.log('EV Trip Planner Panel: hass and vehicleId already available, rendering immediately');
      // Only render if not already rendered with content
      if (!this._rendered || this.innerHTML.length === 0) {
        this._render();
      }
      return;
    }

    // If we have vehicle_id but not hass yet, start polling for hass
    if (this._vehicleId) {
      console.log('EV Trip Planner Panel: vehicle_id obtained, waiting for hass');
      this._startHassPolling();
      return;
    }

    // No vehicle_id found and no hass - start polling with error handling
    console.log('EV Trip Planner Panel: No vehicle_id found, starting polling with timeout');
    this._startHassPolling();
  }

  /**
   * Called when the panel is detached from the DOM
   */
  disconnectedCallback() {
    console.log('EV Trip Planner Panel: disconnectedCallback');
    // Clear polling timeout
    if (this._pollTimeout) {
      clearTimeout(this._pollTimeout);
      this._pollTimeout = null;
    }
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
    // Only reset attempts if we haven't rendered yet (to prevent infinite loop)
    if (!this._rendered) {
      this._initAttempts = 0;
    }

    // CRITICAL: Stop any pending polling since we now have hass
    // This prevents race conditions between polling and hass setter
    if (this._pollTimeout) {
      clearTimeout(this._pollTimeout);
      this._pollTimeout = null;
    }
    // Mark polling as stopped
    this._pollStarted = false;

    // Try to get vehicle_id from URL - multiple approaches
    // Only do this if we don't have vehicle_id yet (connectedCallback should have set it)
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

    // Only render if we have BOTH hass AND vehicleId AND not already rendered with content
    if (this._hass && this._vehicleId) {
      // Check if already rendered with actual content
      const alreadyFullyRendered = this._rendered &&
        this.innerHTML.length > 0 &&
        this.innerHTML.includes('EV Trip Planner');

      if (alreadyFullyRendered) {
        console.log('EV Trip Planner Panel: Already fully rendered, skipping in setter');
      } else {
        console.log('EV Trip Planner Panel: hass and vehicleId available in setter, rendering');
        this._render();
      }
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
    
    // Check if already fully rendered (including trips section)
    const alreadyFullyRendered = this._rendered &&
      this.innerHTML.length > 0 &&
      this.innerHTML.includes('EV Trip Planner') &&
      (this.innerHTML.includes('trips-section') || this.innerHTML.includes('trips-list') || this.innerHTML.includes('trips-header'));

    // If hass is already available and not fully rendered, render
    if (this._hass && !alreadyFullyRendered) {
      console.log('EV Trip Planner Panel: hass available in setConfig, rendering');
      this._render();
    } else if (!this._hass) {
      // If hass not available yet, try again after a short delay
      console.log('EV Trip Planner Panel: hass not available yet, will retry');
    }

    // Also try to render if we now have vehicle_id (since hass might have been set before config)
    if (this._vehicleId && this._hass && !alreadyFullyRendered) {
      console.log('EV Trip Planner Panel: vehicle_id now available after config, rendering');
      this._render();
    }
  }

  /**
   * Poll for hass property since it might be set after connectedCallback
   */
  _startHassPolling() {
    // CRITICAL: Exit immediately if already rendered - prevent multiple polling loops
    if (this._rendered) {
      console.log('EV Trip Planner Panel: Already rendered, skipping _startHassPolling');
      // Stop any existing polling
      if (this._pollTimeout) {
        clearTimeout(this._pollTimeout);
        this._pollTimeout = null;
      }
      this._pollStarted = false;
      return;
    }

    // CRITICAL: Exit if polling already started
    if (this._pollStarted) {
      console.log('EV Trip Planner Panel: Polling already started, skipping');
      return;
    }

    // CRITICAL: Mark polling as started BEFORE doing anything else
    this._pollStarted = true;

    // CRITICAL: Clear any existing poll timeout first
    if (this._pollTimeout) {
      clearTimeout(this._pollTimeout);
      this._pollTimeout = null;
    }

    const poll = () => {
      // CRITICAL: Exit immediately if already rendered
      if (this._rendered) {
        console.log('EV Trip Planner Panel: Panel already rendered, stopping polling');
        if (this._pollTimeout) {
          clearTimeout(this._pollTimeout);
          this._pollTimeout = null;
        }
        this._pollStarted = false;
        return;
      }

      // CRITICAL: Exit if polling has already been stopped
      if (!this._pollStarted) {
        console.log('EV Trip Planner Panel: Polling already stopped');
        return;
      }

      // Check if we have vehicle_id and hass - render and stop polling
      if (this._hass && this._vehicleId) {
        console.log('EV Trip Planner Panel: hass and vehicle_id available, rendering', {
          has_hass: !!this._hass,
          has_connection: !!this._hass?.connection,
          vehicle_id: this._vehicleId,
          is_rendered: this._rendered
        });
        // Stop polling FIRST
        this._pollStarted = false;
        if (this._pollTimeout) {
          clearTimeout(this._pollTimeout);
          this._pollTimeout = null;
        }
        // Call _render() - it will set _rendered = true AFTER content is written
        this._render();
        return;
      }

      // Check if already rendered by external code (hass setter) - stop polling
      if (this._rendered) {
        console.log('EV Trip Planner Panel: Panel already rendered externally, stopping polling');
        this._pollStarted = false;
        if (this._pollTimeout) {
          clearTimeout(this._pollTimeout);
          this._pollTimeout = null;
        }
        return;
      }

      // Increment attempts and continue polling
      this._initAttempts++;

      if (this._initAttempts < this._maxInitAttempts) {
        console.log(`EV Trip Planner Panel: waiting for hass... attempt ${this._initAttempts}/${this._maxInitAttempts}`);
        this._pollTimeout = setTimeout(poll, 500);
      } else {
        console.error('EV Trip Planner Panel: Max init attempts reached, hass not available');
        if (this._pollTimeout) {
          clearTimeout(this._pollTimeout);
          this._pollTimeout = null;
        }
        this._pollStarted = false;
        this.innerHTML = `
          <div style="padding: 20px; text-align: center; color: red;">
            <h3>Error: Home Assistant not initialized</h3>
            <p>Please refresh the page or check HA logs.</p>
            <p>Debug: init attempts = ${this._initAttempts}</p>
            <p>Has hass: ${!!this._hass}, Has vehicleId: ${!!this._vehicleId}</p>
          </div>
        `;
      }
    };

    // Reset attempts counter before starting poll
    this._initAttempts = 0;

    // Start polling after a short delay
    this._pollTimeout = setTimeout(poll, 100);
  }

  /**
   * Get list of trips for the vehicle via hass.connection.call_service.
   *
   * Calls the ev_trip_planner.trip_list service to retrieve both
   * recurring and punctual trips for the current vehicle.
   *
   * @returns {Promise<Array>} Promise resolving to array of trip objects
   */
  async _getTripsList() {
    if (!this._hass) {
      console.warn('EV Trip Planner Panel: Cannot get trips - no hass');
      return [];
    }

    if (!this._vehicleId) {
      console.warn('EV Trip Planner Panel: Cannot get trips - no vehicle_id');
      return [];
    }

    try {
      console.log('EV Trip Planner Panel: Fetching trips for vehicle:', this._vehicleId);

      // Use hass.services.call for service calls
      const response = await this._hass.callService('ev_trip_planner', 'trip_list', {
        vehicle_id: this._vehicleId,
      });
      // Response format: either direct result or wrapped in array/object

      console.log('EV Trip Planner Panel: Trip list response:', response);

      // In newer HA versions, callService returns the result directly
      // or as an array with [result]
      let tripsData = response;

      // Handle array response: [result]
      if (Array.isArray(response) && response.length > 0) {
        tripsData = response[0];
      }
      // Handle object with result property
      else if (response && response.result) {
        tripsData = response.result;
      }

      console.log('EV Trip Planner Panel: Trips data:', tripsData);

      if (tripsData && tripsData.recurring_trips) {
        // Combine recurring and punctual trips
        const allTrips = [
          ...tripsData.recurring_trips.map(t => ({...t, trip_type: 'recurrente'})),
          ...tripsData.punctual_trips.map(t => ({...t, trip_type: 'puntual'})),
        ];
        console.log('EV Trip Planner Panel: Retrieved', allTrips.length, 'trips');
        return allTrips;
      }

      console.warn('EV Trip Planner Panel: Unexpected response format:', tripsData);
      return [];
    } catch (error) {
      console.error('EV Trip Planner Panel: Error fetching trips:', error);
      return [];
    }
  }

  /**
   * Fetch and render trips section for the vehicle.
   *
   * Calls the trip_list service to get all trips (recurring and punctual)
   * and renders them in a user-friendly format.
   *
   * @returns {Promise<void>} Promise that resolves when trips are rendered
   */
  async _renderTripsSection() {
    if (!this._hass) {
      console.warn('EV Trip Planner Panel: Cannot render trips - no hass connection');
      this._updateTripsSection('<p>No connection to Home Assistant</p>');
      return;
    }

    if (!this._vehicleId) {
      console.warn('EV Trip Planner Panel: Cannot render trips - no vehicle_id');
      this._updateTripsSection('<p>No vehicle configured</p>');
      return;
    }

    try {
      console.log('EV Trip Planner Panel: Fetching trips for rendering...');
      const trips = await this._getTripsList();

      if (trips.length === 0) {
        this._updateTripsSection(`
          <div class="trips-header">
            <h2>Viajes Programados (0)</h2>
            <button class="add-trip-btn" onclick="window._tripPanel._showTripForm()">
              + Agregar Viaje
            </button>
          </div>
          <p class="no-trips">No hay viajes programados</p>
        `);
        return;
      }

      // Render trips
      const tripsHtml = trips.map(trip => this._formatTripDisplay(trip)).join('');

      this._updateTripsSection(`
        <div class="trips-header">
          <h2>Viajes Programados (${trips.length})</h2>
          <button class="add-trip-btn" onclick="window._tripPanel._showTripForm()">
            + Agregar Viaje
          </button>
        </div>
        <div class="trips-list">
          ${tripsHtml}
        </div>
      `);
    } catch (error) {
      console.error('EV Trip Planner Panel: Error fetching trips:', error);
      this._updateTripsSection('<p class="error-trips">Error cargando viajes. Verifique los logs.</p>');
    }
  }

  /**
   * Update the trips section with the given HTML content.
   *
   * @param {string} html - HTML content to render in the trips section
   */
  _updateTripsSection(html) {
    const tripsSection = document.getElementById('trips-section');
    if (tripsSection) {
      tripsSection.innerHTML = html;
    } else {
      console.warn('EV Trip Planner Panel: Trips section element not found');
    }
  }

  /**
   * Show the trip creation form overlay.
   */
  _showTripForm() {
    const formHtml = `
      <div class="trip-form-overlay" id="trip-form-overlay">
        <div class="trip-form-container">
          <div class="trip-form-header">
            <h3>🚗 Nuevo Viaje</h3>
            <button class="close-form-btn" onclick="document.getElementById('trip-form-overlay').remove()">×</button>
          </div>
          <form id="trip-creation-form" onsubmit="event.preventDefault();">
            <div class="form-group">
              <label for="trip-type">Tipo de Viaje</label>
              <select id="trip-type" name="type" required>
                <option value="recurrente">🔄 Recurrente (semanal)</option>
                <option value="puntual">📅 Puntual (una vez)</option>
              </select>
            </div>
            <div class="form-group" id="day-group">
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
            <div class="form-group">
              <label for="trip-time">Hora</label>
              <input type="time" id="trip-time" name="time" required>
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
              <button type="button" class="btn btn-secondary" onclick="document.getElementById('trip-form-overlay').remove()">Cancelar</button>
              <button type="submit" class="btn btn-primary">Crear Viaje</button>
            </div>
          </form>
        </div>
      </div>
    `;

    const container = document.querySelector('.panel-container');
    if (container) {
      container.insertAdjacentHTML('beforeend', formHtml);

      // Set default time to now
      const now = new Date();
      const hours = String(now.getHours()).padStart(2, '0');
      const minutes = String(now.getMinutes()).padStart(2, '0');
      document.getElementById('trip-time').value = `${hours}:${minutes}`;

      // Set form submit handler
      document.getElementById('trip-creation-form').onsubmit = () => this._handleTripCreate();
    }
  }

  /**
   * Handle trip creation form submission.
   *
   * Calls the ev_trip_planner.trip_create service with form data.
   *
   * @returns {Promise<void>} Promise that resolves when trip is created
   */
  async _handleTripCreate() {
    if (!this._hass) {
      alert('Error: No hay conexión con Home Assistant');
      return;
    }

    if (!this._vehicleId) {
      alert('Error: No hay vehículo configurado');
      return;
    }

    // Get form values
    const type = document.getElementById('trip-type').value;
    const day = document.getElementById('trip-day').value;
    const time = document.getElementById('trip-time').value;
    const km = document.getElementById('trip-km').value;
    const kwh = document.getElementById('trip-kwh').value;
    const description = document.getElementById('trip-description').value;

    // Build service data
    const serviceData = {
      vehicle_id: this._vehicleId,
      type: type,
      time: time,
      day_of_week: day,
    };

    if (km) {
      serviceData.km = parseFloat(km);
    }
    if (kwh) {
      serviceData.kwh = parseFloat(kwh);
    }
    if (description) {
      serviceData.description = description;
    }

    // Show loading
    const submitBtn = document.querySelector('.trip-form-container .btn-primary');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Creando...';
    submitBtn.disabled = true;

    try {
      // Call the trip_create service
      await this._hass.callService('ev_trip_planner', 'trip_create', serviceData);

      // Close form and refresh trips
      document.getElementById('trip-form-overlay').remove();
      await this._renderTripsSection();

      // Show success message
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
   * Format a trip object for display in a human-readable format.
   *
   * @param {Object} trip - Trip object from the API
   * @returns {string} HTML string for the trip display
   */
  _formatTripDisplay(trip) {
    const tripId = trip.id || 'N/A';
    const tripType = trip.tipo || trip.type || 'Desconocido';
    const isActive = trip.activo !== false || trip.active !== false; // Support both Spanish and English
    const isRecurring = trip.tipo === 'recurrente' || trip.type === 'recurrente' || trip.recurring === true;
    const isPunctual = trip.tipo === 'puntual' || trip.type === 'puntual' || trip.recurring === false;

    // Format day/time display - support both numeric day_of_week and Spanish dia_semana
    let timeDisplay = '';
    if (isRecurring) {
      const dayNames = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
      let dayName = '';
      let time = '00:00';

      // Support Spanish dia_semana (e.g., "lunes")
      if (trip.dia_semana) {
        const lowerDay = trip.dia_semana.toLowerCase();
        dayName = dayNames.find(d => d.toLowerCase() === lowerDay) ||
          trip.dia_semana;
        time = trip.hora || '00:00';
      }
      // Support numeric day_of_week (0-6)
      else if (trip.day_of_week !== undefined) {
        const dayIndex = parseInt(trip.day_of_week, 10);
        dayName = dayNames[dayIndex] || `Día ${dayIndex}`;
        time = trip.time || trip.hora || '00:00';
      }
      // Support Spanish numeric index
      else if (trip.day_of_week_index) {
        const dayIndex = parseInt(trip.day_of_week_index, 10);
        dayName = dayNames[dayIndex] || `Día ${dayIndex}`;
        time = trip.time || trip.hora || '00:00';
      }

      timeDisplay = dayName ? `${dayName} ${time}` : 'Sin hora programada';
    } else if (isPunctual) {
      // Punctual trips use datetime
      timeDisplay = trip.date || trip.datetime || trip.date || 'Sin fecha';
      if (trip.time) {
        timeDisplay += ` a las ${trip.time}`;
      }
    }

    // Calculate and display distance/energy
    const distance = trip.km ? `${trip.km} km` : 'N/A';
    const energy = trip.kwh ? `${trip.kwh} kWh` : 'N/A';

    // Description or default text
    const description = trip.descripcion || trip.description || '';
    const descriptionHtml = description ? `<div class="trip-description">${this._escapeHtml(description)}</div>` : '';

    // Status badge
    const statusBadge = isActive ? '<span class="trip-status status-active">Activo</span>' : '<span class="trip-status status-inactive">Inactivo</span>';

    // Trip ID for form handling
    const tripIdForForm = trip.id || trip.trip_id || trip.tripId || trip.trip_id || trip.id || trip.id || 'unknown';

    // Build action buttons grouped by category
    let actionButtons = `
          <!-- Universal Actions -->
          <div class="trip-action-group universal-actions">
            <button class="trip-action-btn edit-btn" onclick="window._tripPanel._handleEditClick(event)" title="Editar viaje">
              ✏️ Editar
            </button>
            <button class="trip-action-btn delete-btn" onclick="window._tripPanel._handleDeleteClick(event)" title="Eliminar viaje">
              🗑️ Eliminar
            </button>
          </div>
    `;

    // Add status action buttons based on trip type and status
    if (isRecurring) {
      actionButtons += `
          <!-- Recurring Trip Status Actions -->
          <div class="trip-action-group status-actions">
            ${isActive ? `
              <button class="trip-action-btn pause-btn" onclick="window._tripPanel._handlePauseTrip(event, '${this._escapeHtml(tripIdForForm)}')" title="Pausar viaje">
                ⏸️ Pausar
              </button>
            ` : `
              <button class="trip-action-btn resume-btn" onclick="window._tripPanel._handleResumeTrip(event, '${this._escapeHtml(tripIdForForm)}')" title="Reanudar viaje">
                ▶️ Reanudar
              </button>
            `}
          </div>
      `;
    }

    // Add complete/cancel buttons for punctual trips
    if (isPunctual && isActive) {
      actionButtons += `
          <!-- Punctual Trip Status Actions -->
          <div class="trip-action-group status-actions">
            <button class="trip-action-btn complete-btn" onclick="window._tripPanel._handleCompletePunctualTrip(event, '${this._escapeHtml(tripIdForForm)}')" title="Completar viaje">
              ✅ Completar
            </button>
            <button class="trip-action-btn cancel-btn" onclick="window._tripPanel._handleCancelPunctualTrip(event, '${this._escapeHtml(tripIdForForm)}')" title="Cancelar viaje">
              ❌ Cancelar
            </button>
          </div>
      `;
    }

    return `
      <div class="trip-card ${isActive ? '' : 'trip-card-inactive'}" data-trip-id="${this._escapeHtml(tripIdForForm)}">
        <div class="trip-header">
          <div class="trip-type">${isRecurring ? '🔄 Recurrente' : '📅 Puntual'}</div>
          ${statusBadge}
        </div>
        <div class="trip-info">
          <div class="trip-time">${timeDisplay || 'Sin hora programada'}</div>
          <div class="trip-details">
            <span class="trip-detail">${distance}</span>
            <span class="trip-separator">•</span>
            <span class="trip-detail">${energy}</span>
          </div>
          ${descriptionHtml}
        </div>
        <div class="trip-id">ID: ${this._escapeHtml(tripId)}</div>
        <div class="trip-actions">
          <div class="action-group-header">
            <span class="trip-action-group-label">Acciones</span>
            <div class="action-buttons-container">
              ${actionButtons}
            </div>
          </div>
        </div>
      </div>
    `;
  }

  /**
   * Escape HTML special characters to prevent XSS.
   *
   * @param {string} text - Text to escape
   * @returns {string} Escaped HTML string
   */
  _escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
  }

  /**
   * Handle edit button click on a trip card.
   *
   * Opens the edit form with the trip's current data pre-filled.
   *
   * @param {Event} event - Click event
   */
  _handleEditClick(event) {
    const tripCard = event.target.closest('.trip-card');
    const tripId = tripCard.dataset.tripId;

    if (!tripId) {
      console.error('EV Trip Planner Panel: No trip ID found on card');
      alert('Error: No se pudo identificar el viaje');
      return;
    }

    // Get trip data from the service
    this._getTripById(tripId).then(tripData => {
      if (tripData) {
        this._showEditForm(tripData);
      } else {
        alert('Error: No se pudo obtener la información del viaje');
      }
    }).catch(error => {
      console.error('EV Trip Planner Panel: Error getting trip:', error);
      alert('Error: No se pudo cargar la información del viaje');
    });
  }

  /**
   * Handle delete button click on a trip card.
   *
   * Shows a confirmation dialog and deletes the trip if confirmed.
   *
   * @param {Event} event - Click event
   */
  _handleDeleteClick(event) {
    const tripCard = event.target.closest('.trip-card');
    const tripId = tripCard.dataset.tripId;

    if (!tripId) {
      console.error('EV Trip Planner Panel: No trip ID found on card');
      alert('Error: No se pudo identificar el viaje');
      return;
    }

    // Show confirmation dialog
    if (!confirm('¿Estás seguro de que quieres eliminar este viaje?')) {
      return;
    }

    // Delete the trip
    this._deleteTrip(tripId).then(() => {
      // Remove the card from DOM
      tripCard.remove();
      // Refresh the trips list
      this._renderTripsSection().catch(error => {
        console.error('EV Trip Planner Panel: Error refreshing trips:', error);
      });
    }).catch(error => {
      console.error('EV Trip Planner Panel: Error deleting trip:', error);
      alert('Error: No se pudo eliminar el viaje');
    });
  }

  /**
   * Handle pause button click on a recurring trip card.
   *
   * Calls the pause_recurring_trip service to deactivate the trip.
   *
   * @param {Event} event - Click event
   * @param {string} tripId - The trip ID to pause
   */
  _handlePauseTrip(event, tripId) {
    if (!tripId) {
      console.error('EV Trip Planner Panel: No trip ID provided for pause');
      alert('Error: No se pudo identificar el viaje');
      return;
    }

    // Show confirmation dialog
    if (!confirm('¿Estás seguro de que quieres pausar este viaje recurrente?')) {
      return;
    }

    // Pause the trip
    this._pauseTrip(tripId).then(() => {
      // Update the card status
      const tripCard = event.target.closest('.trip-card');
      if (tripCard) {
        tripCard.classList.add('trip-card-inactive');
        // Update status badge
        const statusBadge = tripCard.querySelector('.trip-status');
        if (statusBadge) {
          statusBadge.textContent = 'Inactivo';
          statusBadge.classList.remove('status-active');
          statusBadge.classList.add('status-inactive');
        }
      }
      // Refresh the trips list to ensure consistency
      this._renderTripsSection().catch(error => {
        console.error('EV Trip Planner Panel: Error refreshing trips:', error);
      });
    }).catch(error => {
      console.error('EV Trip Planner Panel: Error pausing trip:', error);
      alert('Error: No se pudo pausar el viaje');
    });
  }

  /**
   * Handle resume button click on a recurring trip card.
   *
   * Calls the resume_recurring_trip service to reactivate the trip.
   *
   * @param {Event} event - Click event
   * @param {string} tripId - The trip ID to resume
   */
  _handleResumeTrip(event, tripId) {
    if (!tripId) {
      console.error('EV Trip Planner Panel: No trip ID provided for resume');
      alert('Error: No se pudo identificar el viaje');
      return;
    }

    // Resume the trip
    this._resumeTrip(tripId).then(() => {
      // Update the card status
      const tripCard = event.target.closest('.trip-card');
      if (tripCard) {
        tripCard.classList.remove('trip-card-inactive');
        // Update status badge
        const statusBadge = tripCard.querySelector('.trip-status');
        if (statusBadge) {
          statusBadge.textContent = 'Activo';
          statusBadge.classList.remove('status-inactive');
          statusBadge.classList.add('status-active');
        }
      }
      // Refresh the trips list to ensure consistency
      this._renderTripsSection().catch(error => {
        console.error('EV Trip Planner Panel: Error refreshing trips:', error);
      });
    }).catch(error => {
      console.error('EV Trip Planner Panel: Error resuming trip:', error);
      alert('Error: No se pudo reanudar el viaje');
    });
  }

  /**
   * Handle complete button click on a punctual trip card.
   *
   * Calls the complete_punctual_trip service to mark the trip as completed.
   *
   * @param {Event} event - Click event
   * @param {string} tripId - The trip ID to complete
   */
  _handleCompletePunctualTrip(event, tripId) {
    if (!tripId) {
      console.error('EV Trip Planner Panel: No trip ID provided for complete');
      alert('Error: No se pudo identificar el viaje');
      return;
    }

    // Show confirmation dialog
    if (!confirm('¿Estás seguro de que quieres completar este viaje?')) {
      return;
    }

    // Complete the trip
    this._completeTrip(tripId).then(() => {
      // Remove the card from DOM
      const tripCard = event.target.closest('.trip-card');
      if (tripCard) {
        tripCard.remove();
      }
      // Refresh the trips list
      this._renderTripsSection().catch(error => {
        console.error('EV Trip Planner Panel: Error refreshing trips:', error);
      });
    }).catch(error => {
      console.error('EV Trip Planner Panel: Error completing trip:', error);
      alert('Error: No se pudo completar el viaje');
    });
  }

  /**
   * Handle cancel button click on a punctual trip card.
   *
   * Calls the cancel_punctual_trip service to cancel the trip.
   *
   * @param {Event} event - Click event
   * @param {string} tripId - The trip ID to cancel
   */
  _handleCancelPunctualTrip(event, tripId) {
    if (!tripId) {
      console.error('EV Trip Planner Panel: No trip ID provided for cancel');
      alert('Error: No se pudo identificar el viaje');
      return;
    }

    // Show confirmation dialog
    if (!confirm('¿Estás seguro de que quieres cancelar este viaje?')) {
      return;
    }

    // Cancel the trip
    this._cancelTrip(tripId).then(() => {
      // Remove the card from DOM
      const tripCard = event.target.closest('.trip-card');
      if (tripCard) {
        tripCard.remove();
      }
      // Refresh the trips list
      this._renderTripsSection().catch(error => {
        console.error('EV Trip Planner Panel: Error refreshing trips:', error);
      });
    }).catch(error => {
      console.error('EV Trip Planner Panel: Error cancelling trip:', error);
      alert('Error: No se pudo cancelar el viaje');
    });
  }

  /**
   * Pause a recurring trip by ID.
   *
   * @param {string} tripId - The trip ID to pause
   * @returns {Promise<void>} Promise that resolves when trip is paused
   */
  async _pauseTrip(tripId) {
    if (!this._hass) {
      throw new Error('No connection to Home Assistant');
    }

    if (!this._vehicleId) {
      throw new Error('No vehicle configured');
    }

    await this._hass.callService('ev_trip_planner', 'pause_recurring_trip', {
      vehicle_id: this._vehicleId,
      trip_id: tripId,
    });

    console.log('EV Trip Planner Panel: Trip paused successfully:', tripId);
  }

  /**
   * Resume a recurring trip by ID.
   *
   * @param {string} tripId - The trip ID to resume
   * @returns {Promise<void>} Promise that resolves when trip is resumed
   */
  async _resumeTrip(tripId) {
    if (!this._hass) {
      throw new Error('No connection to Home Assistant');
    }

    if (!this._vehicleId) {
      throw new Error('No vehicle configured');
    }

    await this._hass.callService('ev_trip_planner', 'resume_recurring_trip', {
      vehicle_id: this._vehicleId,
      trip_id: tripId,
    });

    console.log('EV Trip Planner Panel: Trip resumed successfully:', tripId);
  }

  /**
   * Complete a punctual trip by ID.
   *
   * @param {string} tripId - The trip ID to complete
   * @returns {Promise<void>} Promise that resolves when trip is completed
   */
  async _completeTrip(tripId) {
    if (!this._hass) {
      throw new Error('No connection to Home Assistant');
    }

    if (!this._vehicleId) {
      throw new Error('No vehicle configured');
    }

    await this._hass.callService('ev_trip_planner', 'complete_punctual_trip', {
      vehicle_id: this._vehicleId,
      trip_id: tripId,
    });

    console.log('EV Trip Planner Panel: Trip completed successfully:', tripId);
  }

  /**
   * Cancel a punctual trip by ID.
   *
   * @param {string} tripId - The trip ID to cancel
   * @returns {Promise<void>} Promise that resolves when trip is cancelled
   */
  async _cancelTrip(tripId) {
    if (!this._hass) {
      throw new Error('No connection to Home Assistant');
    }

    if (!this._vehicleId) {
      throw new Error('No vehicle configured');
    }

    await this._hass.callService('ev_trip_planner', 'cancel_punctual_trip', {
      vehicle_id: this._vehicleId,
      trip_id: tripId,
    });

    console.log('EV Trip Planner Panel: Trip cancelled successfully:', tripId);
  }

  /**
   * Get a single trip by ID.
   *
   * @param {string} tripId - The trip ID to fetch
   * @returns {Promise<Object|null>} Promise resolving to trip data or null
   */
  async _getTripById(tripId) {
    if (!this._hass) {
      console.warn('EV Trip Planner Panel: Cannot get trip - no hass connection');
      return null;
    }

    if (!this._vehicleId) {
      console.warn('EV Trip Planner Panel: Cannot get trip - no vehicle_id');
      return null;
    }

    try {
      console.log('EV Trip Planner Panel: Fetching trip by ID:', tripId);

      // Use hass.services.call for service calls
      const response = await this._hass.callService('ev_trip_planner', 'trip_list', {
        vehicle_id: this._vehicleId,
        trip_id: tripId,
      });
      // Response format: either direct result or wrapped in array/object

      let tripsData = response;

      if (Array.isArray(response) && response.length > 0) {
        tripsData = response[0];
      } else if (response && response.result) {
        tripsData = response.result;
      }

      if (!tripsData || !tripsData.recurring_trips || !tripsData.punctual_trips) {
        console.warn('EV Trip Planner Panel: Unexpected response format');
        return null;
      }

      // Search in both recurring and punctual trips
      const allTrips = [
        ...tripsData.recurring_trips.map(t => ({...t, trip_type: 'recurrente'})),
        ...tripsData.punctual_trips.map(t => ({...t, trip_type: 'puntual'})),
      ];

      const trip = allTrips.find(t => t.id === tripId);
      console.log('EV Trip Planner Panel: Found trip:', trip);
      return trip || null;
    } catch (error) {
      console.error('EV Trip Planner Panel: Error fetching trip:', error);
      return null;
    }
  }

  /**
   * Delete a trip by ID.
   *
   * @param {string} tripId - The trip ID to delete
   * @returns {Promise<void>} Promise that resolves when trip is deleted
   */
  async _deleteTrip(tripId) {
    if (!this._hass) {
      throw new Error('No connection to Home Assistant');
    }

    if (!this._vehicleId) {
      throw new Error('No vehicle configured');
    }

    await this._hass.callService('ev_trip_planner', 'delete_trip', {
      vehicle_id: this._vehicleId,
      trip_id: tripId,
    });

    console.log('EV Trip Planner Panel: Trip deleted successfully:', tripId);
  }

  /**
   * Show the trip edit form overlay with pre-filled data.
   *
   * @param {Object} trip - Trip data to edit
   */
  _showEditForm(trip) {
    const formHtml = `
      <div class="trip-form-overlay" id="trip-form-overlay">
        <div class="trip-form-container">
          <div class="trip-form-header">
            <h3>✏️ Editar Viaje</h3>
            <button class="close-form-btn" onclick="document.getElementById('trip-form-overlay').remove()">×</button>
          </div>
          <form id="trip-edit-form" onsubmit="event.preventDefault;">
            <input type="hidden" id="edit-trip-id" value="${this._escapeHtml(trip.id || trip.trip_id)}">
            <div class="form-group">
              <label for="edit-trip-type">Tipo de Viaje</label>
              <select id="edit-trip-type" name="type" required>
                <option value="recurrente">🔄 Recurrente (semanal)</option>
                <option value="puntual">📅 Puntual (una vez)</option>
              </select>
            </div>
            <div class="form-group" id="edit-day-group">
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
            <div class="form-group">
              <label for="edit-trip-time">Hora</label>
              <input type="time" id="edit-trip-time" name="time" required>
            </div>
            <div class="form-group">
              <label for="edit-trip-km">Distancia (km)</label>
              <input type="number" id="edit-trip-km" name="km" step="0.1" min="0" placeholder="Ej: 25.5">
            </div>
            <div class="form-group">
              <label for="edit-trip-kwh">Energía Estimada (kWh)</label>
              <input type="number" id="edit-trip-kwh" name="kwh" step="0.1" min="0" placeholder="Ej: 5.2">
            </div>
            <div class="form-group">
              <label for="edit-trip-description">Descripción (opcional)</label>
              <textarea id="edit-trip-description" name="description" placeholder="Ej: Viaje al trabajo, compras, etc."></textarea>
            </div>
            <div class="form-actions">
              <button type="button" class="btn btn-secondary" onclick="document.getElementById('trip-form-overlay').remove()">Cancelar</button>
              <button type="submit" class="btn btn-primary">Guardar Cambios</button>
            </div>
          </form>
        </div>
      </div>
    `;

    const container = document.querySelector('.panel-container');
    if (container) {
      container.insertAdjacentHTML('beforeend', formHtml);

      // Pre-fill form with existing trip data
      const form = document.getElementById('trip-edit-form');
      const tripTypeSelect = document.getElementById('edit-trip-type');
      const tripDaySelect = document.getElementById('edit-trip-day');
      const tripTimeInput = document.getElementById('edit-trip-time');
      const tripKmInput = document.getElementById('edit-trip-km');
      const tripKwhInput = document.getElementById('edit-trip-kwh');
      const tripDescInput = document.getElementById('edit-trip-description');

      // Set trip type
      tripTypeSelect.value = trip.type === 'puntual' ? 'puntual' : 'recurrente';

      // Set trip day
      if (trip.day_of_week !== undefined) {
        tripDaySelect.value = trip.day_of_week;
      } else if (trip.dia_semana) {
        const dayNames = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
        const lowerDay = trip.dia_semana.toLowerCase();
        const dayIndex = dayNames.indexOf(lowerDay);
        if (dayIndex >= 0) {
          tripDaySelect.value = dayIndex;
        }
      }

      // Set trip time
      const time = trip.time || trip.hora || '00:00';
      tripTimeInput.value = time;

      // Set trip distance
      if (trip.km) {
        tripKmInput.value = trip.km;
      }

      // Set trip energy
      if (trip.kwh) {
        tripKwhInput.value = trip.kwh;
      }

      // Set trip description
      const description = trip.descripcion || trip.description || '';
      if (description) {
        tripDescInput.value = description;
      }

      // Set form submit handler
      form.onsubmit = () => this._handleTripUpdate();
    }
  }

  /**
   * Handle trip edit form submission.
   *
   * Calls the ev_trip_planner.trip_update service with form data.
   *
   * @returns {Promise<void>} Promise that resolves when trip is updated
   */
  async _handleTripUpdate() {
    if (!this._hass) {
      alert('Error: No hay conexión con Home Assistant');
      return;
    }

    if (!this._vehicleId) {
      alert('Error: No hay vehículo configurado');
      return;
    }

    // Get form values
    const tripId = document.getElementById('edit-trip-id').value;
    const type = document.getElementById('edit-trip-type').value;
    const day = document.getElementById('edit-trip-day').value;
    const time = document.getElementById('edit-trip-time').value;
    const km = document.getElementById('edit-trip-km').value;
    const kwh = document.getElementById('edit-trip-kwh').value;
    const description = document.getElementById('edit-trip-description').value;

    if (!tripId) {
      alert('Error: No se pudo identificar el viaje');
      return;
    }

    // Build service data
    const serviceData = {
      vehicle_id: this._vehicleId,
      trip_id: tripId,
      type: type,
      time: time,
      day_of_week: day,
    };

    if (km) {
      serviceData.km = parseFloat(km);
    }
    if (kwh) {
      serviceData.kwh = parseFloat(kwh);
    }
    if (description) {
      serviceData.description = description;
    }

    // Show loading
    const submitBtn = document.querySelector('.trip-form-container .btn-primary');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Guardando...';
    submitBtn.disabled = true;

    try {
      // Call the trip_update service
      await this._hass.callService('ev_trip_planner', 'trip_update', serviceData);

      // Close form and refresh trips
      document.getElementById('trip-form-overlay').remove();
      await this._renderTripsSection();

      // Show success message
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
   * Subscribe to Home Assistant state changes for ALL vehicle sensors
   * Listens to state changes for all sensor patterns associated with this vehicle
   * Ensures real-time updates for all vehicle-related entities
   */
  _subscribeToStates() {
    if (!this._hass) {
      console.warn('EV Trip Planner Panel: Cannot subscribe - no hass connection');
      return;
    }

    // Normalize vehicle_id to lowercase for matching (sensors are lowercase)
    const lowerVehicleId = this._vehicleId.toLowerCase();

    // Define ALL patterns to match vehicle sensors and entities
    // This ensures we capture state changes for all entity types associated with the vehicle
    const patterns = [
      // Standard entity types
      `sensor.${lowerVehicleId}_`,
      `binary_sensor.${lowerVehicleId}_`,
      `input_number.${lowerVehicleId}_`,
      `input_boolean.${lowerVehicleId}_`,
      `climate.${lowerVehicleId}_`,
      `cover.${lowerVehicleId}_`,
      `number.${lowerVehicleId}_`,
      `switch.${lowerVehicleId}_`,
      `light.${lowerVehicleId}_`,
      `fan.${lowerVehicleId}_`,
      `vacuum.${lowerVehicleId}_`,
      `lock.${lowerVehicleId}_`,
      `media_player.${lowerVehicleId}_`,
      `device_tracker.${lowerVehicleId}_`,
      `weather.${lowerVehicleId}_`,
      `alarm_control_panel.${lowerVehicleId}_`,
      // EV Trip Planner specific entity types
      `sensor.ev_trip_planner_${lowerVehicleId}_`,
      `binary_sensor.ev_trip_planner_${lowerVehicleId}_`,
      `input_number.ev_trip_planner_${lowerVehicleId}_`,
      `input_boolean.ev_trip_planner_${lowerVehicleId}_`,
      `climate.ev_trip_planner_${lowerVehicleId}_`,
      `cover.ev_trip_planner_${lowerVehicleId}_`,
      `number.ev_trip_planner_${lowerVehicleId}_`,
      `switch.ev_trip_planner_${lowerVehicleId}_`,
      `light.ev_trip_planner_${lowerVehicleId}_`,
      `fan.ev_trip_planner_${lowerVehicleId}_`,
    ];

    // Subscribe to all state changes for vehicle sensors
    this._unsubscribe = this._hass.connection.subscribeMessage(
      (message) => {
        if (message.type === 'event' && message.event?.event_type === 'state_changed') {
          const entityId = message.event.data?.entity_id;
          // Check if the entity matches any of our patterns
          const matchesPattern = patterns.some(pattern => entityId.startsWith(pattern));
          if (matchesPattern) {
            console.log('EV Trip Planner Panel: State changed for', entityId);
            // Trigger update to refresh the sensor display
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
    if (typeof this._unsubscribe === 'function') {
      this._unsubscribe();
      this._unsubscribe = null;
    }
  }

  /**
   * Get ALL vehicle sensor states - includes all vehicle-related sensors
   * Captures sensors from multiple patterns to ensure all vehicle data is shown
   * Includes: sensor.*, binary_sensor.*, input_number.*, input_boolean.*, climate.*, cover.*, number.*, switch.*
   * and all vehicle-specific sensor patterns for EV Trip Planner
   *
   * @returns {Object} Object with entity IDs as keys and state objects as values
   */
  _getVehicleStates() {
    if (!this._hass || !this._hass.states) {
      console.log('EV Trip Planner Panel: No hass.states available');
      return {};
    }

    const states = this._hass.states;
    const result = {};

    // Normalize vehicle_id to lowercase for matching (sensors are lowercase)
    const lowerVehicleId = this._vehicleId.toLowerCase();

    // Define all patterns to capture ALL vehicle sensors and entities
    // This ensures comprehensive coverage of all entity types associated with the vehicle
    const patterns = [
      // Standard Home Assistant entity types for vehicle sensors
      `sensor.${lowerVehicleId}`,
      `sensor.${lowerVehicleId}_`,
      `binary_sensor.${lowerVehicleId}`,
      `binary_sensor.${lowerVehicleId}_`,
      `input_number.${lowerVehicleId}`,
      `input_number.${lowerVehicleId}_`,
      `input_boolean.${lowerVehicleId}`,
      `input_boolean.${lowerVehicleId}_`,
      `climate.${lowerVehicleId}`,
      `climate.${lowerVehicleId}_`,
      `cover.${lowerVehicleId}`,
      `cover.${lowerVehicleId}_`,
      `number.${lowerVehicleId}`,
      `number.${lowerVehicleId}_`,
      `switch.${lowerVehicleId}`,
      `switch.${lowerVehicleId}_`,
      `light.${lowerVehicleId}`,
      `light.${lowerVehicleId}_`,
      `fan.${lowerVehicleId}`,
      `fan.${lowerVehicleId}_`,
      `vacuum.${lowerVehicleId}`,
      `vacuum.${lowerVehicleId}_`,
      `lock.${lowerVehicleId}`,
      `lock.${lowerVehicleId}_`,
      `media_player.${lowerVehicleId}`,
      `media_player.${lowerVehicleId}_`,
      `device_tracker.${lowerVehicleId}`,
      `device_tracker.${lowerVehicleId}_`,
      `weather.${lowerVehicleId}`,
      `weather.${lowerVehicleId}_`,
      `alarm_control_panel.${lowerVehicleId}`,
      `alarm_control_panel.${lowerVehicleId}_`,
      // EV Trip Planner specific entity types (with entry_id namespace)
      `sensor.ev_trip_planner_${lowerVehicleId}`,
      `sensor.ev_trip_planner_${lowerVehicleId}_`,
      `binary_sensor.ev_trip_planner_${lowerVehicleId}`,
      `binary_sensor.ev_trip_planner_${lowerVehicleId}_`,
      `input_number.ev_trip_planner_${lowerVehicleId}`,
      `input_number.ev_trip_planner_${lowerVehicleId}_`,
      `input_boolean.ev_trip_planner_${lowerVehicleId}`,
      `input_boolean.ev_trip_planner_${lowerVehicleId}_`,
      `climate.ev_trip_planner_${lowerVehicleId}`,
      `climate.ev_trip_planner_${lowerVehicleId}_`,
      `cover.ev_trip_planner_${lowerVehicleId}`,
      `cover.ev_trip_planner_${lowerVehicleId}_`,
      `number.ev_trip_planner_${lowerVehicleId}`,
      `number.ev_trip_planner_${lowerVehicleId}_`,
      `switch.ev_trip_planner_${lowerVehicleId}`,
      `switch.ev_trip_planner_${lowerVehicleId}_`,
      `light.ev_trip_planner_${lowerVehicleId}`,
      `light.ev_trip_planner_${lowerVehicleId}_`,
      `fan.ev_trip_planner_${lowerVehicleId}`,
      `fan.ev_trip_planner_${lowerVehicleId}_`,
      // Trip-specific sensors (each trip has its own sensor)
      `sensor.trip_`,
      // Additional patterns for sensor entity naming conventions
      `sensor.ev_trip_planner_`,
      `sensor.ev_trip_planner`,
    ];

    console.log('EV Trip Planner Panel: Searching for ALL vehicle sensors');
    console.log('EV Trip Planner Panel: Patterns count:', patterns.length);
    console.log('EV Trip Planner Panel: Total entities in hass.states:', states instanceof Map ? states.size : Object.keys(states).length);

    // hass.states is a Map in Home Assistant, use forEach to iterate
    if (states instanceof Map) {
      for (const [entityId, state] of states) {
        // Check if entity matches any of our patterns
        if (patterns.some(pattern => entityId.startsWith(pattern))) {
          result[entityId] = state;
        }
      }
    } else {
      // Fallback for plain object
      for (const [entityId, state] of Object.entries(states)) {
        if (patterns.some(pattern => entityId.startsWith(pattern))) {
          result[entityId] = state;
        }
      }
    }

    console.log('EV Trip Planner Panel: Found', Object.keys(result).length, 'sensors for vehicle:', lowerVehicleId);

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

    // Try multiple entity type patterns
    const entityTypes = ['sensor', 'binary_sensor', 'input_number', 'input_boolean'];
    let state = null;

    for (const etype of entityTypes) {
      const fullEntityId = `${etype}.${lowerVehicleId}_${entityId}`;
      if (hassStates instanceof Map) {
        state = hassStates.get(fullEntityId);
      } else {
        state = hassStates[fullEntityId];
      }
      if (state) {
        break;
      }
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
   * Handles multiple naming patterns for better readability
   */
  _entityIdToName(entityId) {
    // Remove prefix (sensor., binary_sensor., input_number., etc.)
    let name = entityId.replace(/^[\w_]+\./, '');

    // Handle vehicle-specific naming patterns
    // Remove vehicle_id prefix if present (e.g., "_chispitas_" or "_coche_")
    const vehiclePatterns = [
      '_soc_actual', '_battery_level', '_range', '_charging_status',
      '_charging', '_connection', '_presence', '_state',
      '_kwh_today', '_hours_today', '_next_trip', '_trips_list',
      '_recurring_trips_count', '_punctual_trips_count'
    ];

    for (const pattern of vehiclePatterns) {
      if (name.toLowerCase().includes(pattern)) {
        name = name.replace(/_chispitas_/gi, '_').replace(/_coche_/gi, '_');
        break;
      }
    }

    // Convert camelCase to spaces
    name = name.replace(/([A-Z])/g, ' $1');

    // Replace underscores with spaces
    name = name.replace(/_/g, ' ');

    // Clean up multiple spaces
    name = name.replace(/\s+/g, ' ');

    // Title case each word
    name = name
      .trim()
      .split(' ')
      .map(word => {
        // Handle abbreviations and special cases
        const abbreviations = ['soc', 'kwh', 'ev', 'ha', 'id', 'km', 'dc', 'ac'];
        const lowerWord = word.toLowerCase();
        if (abbreviations.includes(lowerWord)) {
          return lowerWord.toUpperCase();
        }
        // Title case normal words
        return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
      })
      .join(' ');

    return name;
  }

  /**
   * Get sensor unit of measurement
   */
  _getUnit(entityId) {
    const states = this._hass?.states || {};
    const state = states[entityId];
    if (state && state.attributes) {
      // Check for unit_of_measurement attribute first
      if (state.attributes.unit_of_measurement) {
        return state.attributes.unit_of_measurement;
      }

      // Check for state_class attributes that imply units
      const stateClass = state.attributes.state_class;
      const device_class = state.attributes.device_class;

      // Derive unit from device_class if no explicit unit
      if (device_class) {
        const unitMap = {
          'battery': '%',
          'co2': 'ppm',
          'current': 'A',
          'distance': this._deriveDistanceUnit(state),
          'duration': 's',
          'energy': 'kWh',
          'frequency': 'Hz',
          'gas': 'm³',
          'illumination': 'lx',
          'monetary': '€',
          'power': 'kW',
          'power_factor': '',
          'pressure': 'hPa',
          'reactive_energy': 'kVArh',
          'signal_strength': 'dBm',
          'sound_pressure': 'dB',
          'temperature': '°C',
          'timestamp': '',
          'volatile_organic_compounds': 'ppm',
          'voltag': 'V',
          'volume': 'L',
          'volume_flow_rate': 'L/min',
          'water': 'm³',
          'weight': 'kg',
          'wind_speed': 'm/s'
        };
        return unitMap[device_class] || '';
      }
    }
    return '';
  }

  /**
   * Derive distance unit from entity attributes
   */
  _deriveDistanceUnit(state) {
    const attributes = state.attributes;
    // Check for native_unit_of_measurement first (preferred)
    if (attributes.native_unit_of_measurement) {
      return attributes.native_unit_of_measurement;
    }
    // Default to km for vehicle-related sensors
    if (state.entity_id.includes('vehicle') || state.entity_id.includes('ev_trip_planner')) {
      return 'km';
    }
    return 'm';
  }

  /**
   * Format sensor value with unit - improved for readability
   * Returns undefined for unavailable/unknown states to filter them out
   * Formats numbers with appropriate decimal places based on value type
   * Only returns valid, non-N/A values - N/A values are filtered out
   */
  _formatSensorValue(entityId) {
    const states = this._hass?.states || {};
    const state = states[entityId];
    if (!state) {
      return null; // Return null to indicate this sensor should be filtered out
    }

    const unit = this._getUnit(entityId);
    let value = state.state;

    // Handle unavailable/unknown states - return null to filter them out
    if (value === 'unavailable' || value === 'unknown' || value === 'N/A' || value === 'none' || value === '' || value === null) {
      return null; // Filter out unavailable/unknown sensors
    }

    // Check if it's a boolean value (binary sensor)
    if (value === 'on' || value === 'off' || value === 'true' || value === 'false') {
      return this._formatBooleanValue(value);
    }

    // Try to parse as number and format appropriately
    const numericValue = parseFloat(value);
    if (!isNaN(numericValue)) {
      value = this._formatNumericValue(numericValue, unit);
      return unit ? `${value} ${unit}` : value;
    }

    // For text values, return as-is with unit if available
    return unit ? `${value} ${unit}` : value;
  }

  /**
   * Format boolean values for better readability
   */
  _formatBooleanValue(value) {
    if (value === 'on' || value === 'true') {
      return '✓ Activo';
    }
    if (value === 'off' || value === 'false') {
      return '✗ Inactivo';
    }
    return value;
  }

  /**
   * Format numeric values with appropriate decimal places based on context
   * Uses smart formatting rules for better readability
   */
  _formatNumericValue(value, unit) {
    // Handle percentages - always show 1 decimal
    if (unit === '%' || unit === 'percentage' || (value >= 0 && value <= 100)) {
      return value.toFixed(1) + '%';
    }

    // Handle energy-related values (kWh, MWh)
    if (unit && (unit.includes('kWh') || unit.includes('MWh') || unit.includes('Wh'))) {
      return value.toFixed(2) + ' ' + unit;
    }

    // Handle distance values (km, m, mi)
    if (unit && (unit.includes('km') || unit.includes('mi') || unit.includes('m'))) {
      if (value < 1) {
        return value.toFixed(2) + ' ' + unit;
      }
      return value.toFixed(1) + ' ' + unit;
    }

    // Handle power values (kW, W)
    if (unit && (unit.includes('kW') || unit.includes('W'))) {
      return value.toFixed(2) + ' ' + unit;
    }

    // Handle temperature values
    if (unit && (unit.includes('°C') || unit.includes('°F') || unit === '°')) {
      return value.toFixed(1) + (unit.includes('°C') ? '°C' : unit.includes('°F') ? '°F' : '°');
    }

    // Handle small values (< 1) - 3 decimal places for precision
    if (value > 0 && value < 1) {
      return value.toFixed(3);
    }

    // Handle values between 1 and 10 - 2 decimal places
    if (value >= 1 && value < 10) {
      return value.toFixed(2);
    }

    // Handle values between 10 and 100 - 1 decimal place
    if (value >= 10 && value < 100) {
      return value.toFixed(1);
    }

    // Handle values between 100 and 10000 - 1 decimal place
    if (value >= 100 && value < 10000) {
      return value.toFixed(1);
    }

    // Handle large values (>= 10000) - 0 decimal places
    if (value >= 10000) {
      return value.toFixed(0);
    }

    // Default: 1 decimal place for values between 1 and 100
    return value.toFixed(1);
  }

  /**
   * Get sensor icon based on entity type
   * Returns appropriate emoji icon based on sensor characteristics
   */
  _getSensorIcon(entityId) {
    const name = this._entityIdToName(entityId);
    const lowerName = name.toLowerCase();

    // Energy and power sensors
    if (lowerName.includes('soc') || lowerName.includes('batería') || lowerName.includes('battery') || lowerName.includes('soc')) {
      return '🔋';
    }
    if (lowerName.includes('range') || lowerName.includes('rango') || lowerName.includes('distance') || lowerName.includes('distancia')) {
      return '📍';
    }
    if (lowerName.includes('charging') || lowerName.includes('carga') || lowerName.includes('charge')) {
      return '⚡';
    }
    if (lowerName.includes('kwh') || lowerName.includes('energy') || lowerName.includes('consumo') || lowerName.includes('consumption')) {
      return '💡';
    }
    if (lowerName.includes('power') || lowerName.includes('potencia') || lowerName.includes('watt')) {
      return '💪';
    }
    if (lowerName.includes('hour') || lowerName.includes('hora') || lowerName.includes('duration') || lowerName.includes('duración')) {
      return '⏰';
    }
    if (lowerName.includes('trip') || lowerName.includes('viaje') || lowerName.includes('trip')) {
      return '🚗';
    }
    if (lowerName.includes('next') || lowerName.includes('siguiente') || lowerName.includes('proximo')) {
      return '🎯';
    }
    if (lowerName.includes('temperature') || lowerName.includes('temp') || lowerName.includes('temperatura')) {
      return '🌡️';
    }
    if (lowerName.includes('pressure') || lowerName.includes('presión') || lowerName.includes('pressure')) {
      return '🌡️';
    }
    if (lowerName.includes('speed') || lowerName.includes('velocidad') || lowerName.includes('speed')) {
      return '🚀';
    }
    if (lowerName.includes('light') || lowerName.includes('luz') || lowerName.includes('brightness')) {
      return '💡';
    }
    if (lowerName.includes('lock') || lowerName.includes('cerrado') || lowerName.includes('locked')) {
      return '🔒';
    }
    if (lowerName.includes('cover') || lowerName.includes('persiana') || lowerName.includes('shade')) {
      return '🪟';
    }
    if (lowerName.includes('fan') || lowerName.includes('ventilador') || lowerName.includes('fan')) {
      return '💨';
    }
    if (lowerName.includes('vacuum') || lowerName.includes('aspiradora') || lowerName.includes('robot')) {
      return '🤖';
    }
    if (lowerName.includes('plug') || lowerName.includes('enchufe') || lowerName.includes('connection')) {
      return '🔌';
    }
    if (lowerName.includes('presence') || lowerName.includes('presencia') || lowerName.includes('plug')) {
      return '👤';
    }
    if (lowerName.includes('status') || lowerName.includes('estado') || lowerName.includes('state')) {
      return '📊';
    }
    if (lowerName.includes('count') || lowerName.includes('conteo') || lowerName.includes('total')) {
      return '🔢';
    }
    if (lowerName.includes('switch') || lowerName.includes('interruptor') || lowerName.includes('switch')) {
      return '🔘';
    }
    if (lowerName.includes('door') || lowerName.includes('puerta') || lowerName.includes('door')) {
      return '🚪';
    }
    if (lowerName.includes('window') || lowerName.includes('ventana') || lowerName.includes('window')) {
      return '🪟';
    }
    if (lowerName.includes('motion') || lowerName.includes('movimiento') || lowerName.includes('motion')) {
      return '🏃';
    }
    if (lowerName.includes('water') || lowerName.includes('agua') || lowerName.includes('water')) {
      return '💧';
    }
    if (lowerName.includes('gas') || lowerName.includes('gas') || lowerName.includes('gas')) {
      return '🔥';
    }

    return '📊';
  }

  /**
   * Check if sensor is a status indicator
   * Status indicators are key vehicle metrics that should be prominently displayed
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
   * Group sensors by type - comprehensive categorization
   * Ensures ALL sensors are properly categorized and displayed
   */
  _groupSensors(sensors) {
    const groups = {
      status: [],      // SOC, range, charging status - key vehicle indicators
      battery: [],     // Battery-related sensors
      trips: [],       // Trip-related sensors
      energy: [],      // Energy/consumption sensors
      charging: [],    // Charging-specific sensors
      other: []        // All other sensors
    };

    for (const [entityId, state] of Object.entries(sensors)) {
      const name = this._entityIdToName(entityId);
      const lowerName = name.toLowerCase();
      const icon = this._getSensorIcon(entityId);

      // Categorize based on sensor name patterns
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

    // Log groups for debugging
    console.log('EV Trip Planner Panel: Grouped sensors:', {
      status: groups.status.length,
      battery: groups.battery.length,
      trips: groups.trips.length,
      energy: groups.energy.length,
      charging: groups.charging.length,
      other: groups.other.length,
      total: Object.values(groups).flat().length
    });

    return groups;
  }

  /**
   * Render the panel
   */
  _render() {
    console.log('EV Trip Planner Panel: _render() called, _rendered:', this._rendered, '_hass:', !!this._hass, '_vehicleId:', this._vehicleId);

    // CRITICAL: Reset _rendered flag if innerHTML is empty - indicates failed render
    // This handles race conditions where _rendered was set prematurely
    if (this._rendered && this.innerHTML.length === 0) {
      console.log('EV Trip Planner Panel: innerHTML is empty, resetting _rendered flag to allow re-render');
      this._rendered = false;
    }

    // CRITICAL: Prevent re-rendering only if content was actually written
    // Check if innerHTML contains expected panel content
    if (this._rendered) {
      // If innerHTML is empty or doesn't contain panel content, reset _rendered to allow re-render
      if (this.innerHTML.length === 0 || !this.innerHTML.includes('EV Trip Planner')) {
        console.log("EV Trip Planner Panel: _rendered=true but innerHTML is empty or missing panel content, resetting to allow re-render");
        this._rendered = false;
      } else {
        // Check if trips section is already rendered (not just initial render)
        const hasTripsSection = this.innerHTML.includes('trips-section') || this.innerHTML.includes('trips-list');
        if (hasTripsSection) {
          console.log("EV Trip Planner Panel: Already fully rendered with trips section, skipping");
          return;
        }
        // If trips section is missing but _rendered is true, this means trips haven't been rendered yet
        // In this case, we should NOT return early - let the render flow complete
        console.log("EV Trip Planner Panel: _rendered=true but trips section missing, continuing to render");
        this._rendered = false; // Reset to allow re-render
      }
    }

    if (!this._hass) {
      console.warn('EV Trip Planner Panel: Cannot render - no hass');
      this.innerHTML = `
        <div style="padding: 20px; text-align: center;">
          <p>Waiting for Home Assistant...</p>
        </div>
      `;
      this._rendered = true;
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
      this._rendered = true;
      return;
    }

    // CRITICAL: Stop polling immediately when rendering
    if (this._pollTimeout) {
      clearTimeout(this._pollTimeout);
      this._pollTimeout = null;
    }

    // Stop any pending polling immediately
    if (this._pollTimeout) {
      clearTimeout(this._pollTimeout);
      this._pollTimeout = null;
    }
    this._pollStarted = false;
    console.log('EV Trip Planner Panel: Rendering for vehicle', this._vehicleId);

    // Store panel reference globally for onclick handlers
    window._tripPanel = this;

    // Get vehicle states
    const states = this._getVehicleStates();
    const stateKeys = Object.keys(states);
    console.log('EV Trip Planner Panel: Found', stateKeys.length, 'sensors:', stateKeys);
    const groupedSensors = this._groupSensors(states);

    // Filter out sensors with unavailable/unknown values (N/A not allowed)
    const validStatusSensors = groupedSensors.status.filter(s => {
      const formattedValue = this._formatSensorValue(s.entityId);
      return formattedValue !== null;
    });

    // Build sensor list HTML with data attributes for update
    const statusCards = validStatusSensors.map(s => `
      <div class="status-card" data-entity="${this._escapeHtml(s.entityId)}">
        <span class="status-icon">${s.icon}</span>
        <span class="status-label">${s.name}</span>
        <span class="status-value">${this._formatSensorValue(s.entityId)}</span>
      </div>
    `).join('');

    // Filter out sensors with unavailable/unknown values (N/A not allowed)
    const filteredGroupedSensors = {};
    Object.entries(groupedSensors).forEach(([groupName, sensors]) => {
      const validSensors = sensors.filter(s => {
        const formattedValue = this._formatSensorValue(s.entityId);
        return formattedValue !== null; // Filter out unavailable/unknown sensors
      });
      filteredGroupedSensors[groupName] = validSensors;
    });

    const sensorListHtml = Object.entries(filteredGroupedSensors)
      .filter(([_, sensors]) => sensors.length > 0)
      .map(([groupName, sensors]) => {
        const groupNameMapping = {
          status: 'Estado del Vehículo',
          battery: 'Batería',
          trips: 'Viajes',
          energy: 'Energía y Consumo',
          charging: 'Carga',
          other: 'Otros Sensores'
        };
        return `
        <div class="sensor-group">
          <h3 class="sensor-group-title">${groupNameMapping[groupName] || this._getGroupName(groupName)}</h3>
          <div class="sensor-items-list">
            ${sensors.map(s => {
              const formattedValue = this._formatSensorValue(s.entityId);
              const entityIdDisplay = s.entityId.split('.').slice(1).join('.');
              // Use formatted value or show N/A for unavailable
              const valueDisplay = formattedValue || 'N/A';
              return `
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
            }).join('')}
          </div>
        </div>
      `;
      }).join('');

    // CRITICAL: Render the panel HTML first - this is the key line that writes to DOM
    const panelHtml = `
      <link rel="stylesheet" href="/ev-trip-planner/panel.css?v=${Date.now()}">
      <div class="panel-container">
        <header class="panel-header">
          <h1>🚗 EV Trip Planner - ${this._vehicleId}</h1>
        </header>
        <main class="panel-content">
          ${statusCards ? `
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
            ${Object.values(filteredGroupedSensors).some(s => s.length > 0) ? `
              <h2 class="section-title">
                <span class="section-icon">📡</span>
                <span class="section-title-text">Available Sensors (${Object.values(filteredGroupedSensors).reduce((sum, s) => sum + s.length, 0)})</span>
              </h2>
              <div class="sensor-list-grouped">
                ${sensorListHtml || '<p class="no-sensors">No valid sensors found</p>'}
              </div>
            ` : '<p class="no-sensors">No sensors found</p>'}
          </div>
          <div class="trips-section">
            <div class="trips-header">
              <h2 class="section-title">
                <span class="section-icon">📅</span>
                <span class="section-title-text">Viajes Programados</span>
              </h2>
              <button class="add-trip-btn" onclick="window._tripPanel._showTripForm()">
                + Agregar Viaje
              </button>
            </div>
            <div id="trips-section">
              <h2>Cargando viajes...</h2>
            </div>
          </div>
        </main>
      </div>
    `;

    // CRITICAL: Write HTML to DOM FIRST
    this.innerHTML = panelHtml;
    console.log('EV Trip Planner Panel: innerHTML written, length:', this.innerHTML.length);

    // Subscribe to state changes after render
    this._subscribeToStates();

    // CRITICAL: Do NOT set _rendered = true yet - wait for trips to be fully rendered
    // This prevents early exit from _render() before trips are loaded

    // Schedule trips rendering after a delay to ensure panel is fully rendered
    setTimeout(() => {
      // Only render trips if not already rendered
      if (!this._rendered) {
        this._renderTripsLater().catch(error => {
          console.error('EV Trip Planner Panel: Error rendering trips section:', error);
        });
      }
    }, 100);
  }

  /**
   * Render trips section - must be called AFTER panel is fully rendered
   * to prevent infinite recursion.
   * Sets _rendered = true AFTER trips are fully rendered.
   */
  async _renderTripsLater() {
    await this._renderTripsSection().catch(error => {
      console.error('EV Trip Planner Panel: Error rendering trips section:', error);
    });
    // CRITICAL: Set _rendered = true ONLY AFTER trips are fully rendered
    this._rendered = true;
    console.log('EV Trip Planner Panel: _rendered = true set after trips rendering complete');
  }

  /**
   * Update individual sensor values without triggering re-render.
   * This method is called by the state subscription when sensors change.
   */
  _update() {
    if (!this._rendered || !this._hass) {
      return;
    }

    // Update status section values only - do not replace innerHTML
    const states = this._getVehicleStates();
    const groupedSensors = this._groupSensors(states);

    // Update each status card value individually
    groupedSensors.status.forEach(s => {
      const card = document.querySelector(`.status-card[data-entity="${this._escapeHtml(s.entityId)}"]`);
      if (card) {
        const valueEl = card.querySelector('.status-value');
        if (valueEl) {
          valueEl.textContent = this._formatSensorValue(s.entityId);
        }
      }
    });

    // Update each sensor item value individually - do not replace innerHTML
    groupedSensors.status.forEach(s => {
      this._updateSensorItem(s.entityId, s.name, s.icon, this._formatSensorValue(s.entityId));
    });

    // Update other sensor groups
    Object.entries(groupedSensors)
      .filter(([_, sensors]) => sensors.length > 0)
      .forEach(([groupName, sensors]) => {
        const groupTitle = document.querySelector(`.sensor-group-title:contains("${this._getGroupName(groupName)}")`);
        if (groupTitle) {
          sensors.forEach(s => {
            this._updateSensorItem(s.entityId, s.name, s.icon, this._formatSensorValue(s.entityId));
          });
        }
      });
  }

  /**
   * Update a single sensor item by entity ID.
   * @param {string} entityId - The entity ID
   * @param {string} name - The sensor name
   * @param {string} icon - The sensor icon
   * @param {string} value - The sensor value
   */
  _updateSensorItem(entityId, name, icon, value) {
    const sensorItem = document.querySelector(`.sensor-item[data-entity-id="${this._escapeHtml(entityId)}"]`);
    if (sensorItem) {
      const valueEl = sensorItem.querySelector('.sensor-value');
      const nameEl = sensorItem.querySelector('.sensor-name');
      const iconEl = sensorItem.querySelector('.sensor-icon');

      if (valueEl) valueEl.textContent = value;
      if (nameEl) nameEl.textContent = name;
      if (iconEl) iconEl.textContent = icon;
    }
  }


  /**
   * Get group name for display
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
   * Get CSS styles
   */
  _getStyles() {
    // All styles are now centralized in panel.css for consistency
    // This method returns an empty string as styles are loaded from external CSS file
    return '';
  }
}

// Register the custom element
customElements.define('ev-trip-planner-panel', EVTripPlannerPanel);
