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
    console.log('EV Trip Planner Panel: connectedCallback');
    console.log('EV Trip Planner Panel: full URL:', window.location.href);
    console.log('EV Trip Planner Panel: pathname:', window.location.pathname);
    console.log('EV Trip Planner Panel: hash:', window.location.hash);
    console.log('EV Trip Planner Panel: _rendered:', this._rendered, '_pollStarted:', this._pollStarted);

    // CRITICAL: Exit immediately if already rendered - prevents multiple connectedCallback calls
    if (this._rendered) {
      console.log('EV Trip Planner Panel: Already rendered, exiting connectedCallback');
      // But still stop polling if it's running
      if (this._pollTimeout) {
        clearTimeout(this._pollTimeout);
        this._pollTimeout = null;
      }
      this._pollStarted = false;
      return;
    }

    // CRITICAL: Exit if polling already started to prevent multiple poll loops
    if (this._pollStarted) {
      console.log('EV Trip Planner Panel: Polling already started, exiting connectedCallback');
      // Clear any pending poll to stop it
      if (this._pollTimeout) {
        clearTimeout(this._pollTimeout);
        this._pollTimeout = null;
      }
      this._pollStarted = false;
      return;
    }

    // CRITICAL: Check if we already have hass and vehicleId - render immediately
    if (this._hass && this._vehicleId) {
      console.log('EV Trip Planner Panel: hass and vehicleId already available, rendering immediately');
      this._rendered = true;
      this._render();
      return;
    }

    // Check if hass is available but vehicle_id is not - render with error
    if (this._hass && !this._vehicleId) {
      console.log('EV Trip Planner Panel: hass available but no vehicle_id');
      // Try to extract vehicle_id from URL one more time
      const path = window.location.pathname;
      if (path.includes('ev-trip-planner-')) {
        const parts = path.split('ev-trip-planner-');
        if (parts.length > 1) {
          this._vehicleId = parts[1].split('/')[0];
          console.log('EV Trip Planner Panel: vehicle_id from URL:', this._vehicleId);
          if (this._vehicleId) {
            this._rendered = true;
            this._render();
            return;
          }
        }
      }
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

    // Start polling for hass if not available
    // But first check if we can render now
    if (this._hass && this._vehicleId) {
      console.log('EV Trip Planner Panel: hass available now, rendering');
      this._rendered = true;
      this._render();
      // Stop any pending polling
      if (this._pollTimeout) {
        clearTimeout(this._pollTimeout);
        this._pollTimeout = null;
      }
      this._pollStarted = false;
    }
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

    // Stop any pending polling since we now have hass
    if (this._pollTimeout) {
      clearTimeout(this._pollTimeout);
      this._pollTimeout = null;
    }
    // Mark polling as stopped
    this._pollStarted = false;

    // Only render if we haven't rendered yet - CRITICAL FIX
    if (!this._rendered) {
      this._rendered = true;
      this._render();
    } else if (this._hass) {
      // Only update if hass is available and already rendered
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
        // Set rendered flag BEFORE calling _render
        this._rendered = true;
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
   * Get list of trips for the vehicle via Home Assistant service call.
   *
   * Calls the ev_trip_planner.trip_list service to retrieve both
   * recurring and punctual trips for the current vehicle.
   *
   * @returns {Promise<Array>} Promise resolving to array of trip objects
   */
  async _getTripsList() {
    if (!this._hass || !this._hass.connection) {
      console.warn('EV Trip Planner Panel: Cannot get trips - no hass connection');
      return [];
    }

    if (!this._vehicleId) {
      console.warn('EV Trip Planner Panel: Cannot get trips - no vehicle_id');
      return [];
    }

    try {
      console.log('EV Trip Planner Panel: Fetching trips for vehicle:', this._vehicleId);

      const response = await this._hass.connection.callService('ev_trip_planner', 'trip_list', {
        vehicle_id: this._vehicleId,
      });

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
    if (!this._hass || !this._hass.connection) {
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
        this._updateTripsSection('<p class="no-trips">No hay viajes programados</p>');
        return;
      }

      // Render trips
      const tripsHtml = trips.map(trip => this._formatTripDisplay(trip)).join('');

      this._updateTripsSection(`
        <div class="trips-section">
          <h2>Viajes Programados (${trips.length})</h2>
          <div class="trips-list">
            ${tripsHtml}
          </div>
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
    if (!this._hass || !this._hass.connection) {
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
      await this._hass.connection.callService('ev_trip_planner', 'trip_create', serviceData);

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

    // Build action buttons based on trip type and status
    let actionButtons = `
          <button class="trip-action-btn edit-btn" onclick="window._tripPanel._handleEditClick(event)" title="Editar viaje">
            ✏️ Editar
          </button>
          <button class="trip-action-btn delete-btn" onclick="window._tripPanel._handleDeleteClick(event)" title="Eliminar viaje">
            🗑️ Eliminar
          </button>
    `;

    // Add pause/resume buttons for recurring trips
    if (isRecurring) {
      if (isActive) {
        actionButtons += `
          <button class="trip-action-btn pause-btn" onclick="window._tripPanel._handlePauseTrip(event, '${this._escapeHtml(tripIdForForm)}')" title="Pausar viaje">
            ⏸️ Pausar
          </button>
        `;
      } else {
        actionButtons += `
          <button class="trip-action-btn resume-btn" onclick="window._tripPanel._handleResumeTrip(event, '${this._escapeHtml(tripIdForForm)}')" title="Reanudar viaje">
            ▶️ Reanudar
          </button>
        `;
      }
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
          ${actionButtons}
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
   * Pause a recurring trip by ID.
   *
   * @param {string} tripId - The trip ID to pause
   * @returns {Promise<void>} Promise that resolves when trip is paused
   */
  async _pauseTrip(tripId) {
    if (!this._hass || !this._hass.connection) {
      throw new Error('No connection to Home Assistant');
    }

    if (!this._vehicleId) {
      throw new Error('No vehicle configured');
    }

    await this._hass.connection.callService('ev_trip_planner', 'pause_recurring_trip', {
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
    if (!this._hass || !this._hass.connection) {
      throw new Error('No connection to Home Assistant');
    }

    if (!this._vehicleId) {
      throw new Error('No vehicle configured');
    }

    await this._hass.connection.callService('ev_trip_planner', 'resume_recurring_trip', {
      vehicle_id: this._vehicleId,
      trip_id: tripId,
    });

    console.log('EV Trip Planner Panel: Trip resumed successfully:', tripId);
  }

  /**
   * Get a single trip by ID.
   *
   * @param {string} tripId - The trip ID to fetch
   * @returns {Promise<Object|null>} Promise resolving to trip data or null
   */
  async _getTripById(tripId) {
    if (!this._hass || !this._hass.connection) {
      console.warn('EV Trip Planner Panel: Cannot get trip - no hass connection');
      return null;
    }

    if (!this._vehicleId) {
      console.warn('EV Trip Planner Panel: Cannot get trip - no vehicle_id');
      return null;
    }

    try {
      console.log('EV Trip Planner Panel: Fetching trip by ID:', tripId);

      const response = await this._hass.connection.callService('ev_trip_planner', 'trip_list', {
        vehicle_id: this._vehicleId,
      });

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
    if (!this._hass || !this._hass.connection) {
      throw new Error('No connection to Home Assistant');
    }

    if (!this._vehicleId) {
      throw new Error('No vehicle configured');
    }

    await this._hass.connection.callService('ev_trip_planner', 'delete_trip', {
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
    if (!this._hass || !this._hass.connection) {
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
      await this._hass.connection.callService('ev_trip_planner', 'trip_update', serviceData);

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
   */
  _subscribeToStates() {
    if (!this._hass || !this._hass.connection) {
      console.warn('EV Trip Planner Panel: Cannot subscribe - no hass connection');
      return;
    }

    // Normalize vehicle_id to lowercase for matching (sensors are lowercase)
    const lowerVehicleId = this._vehicleId.toLowerCase();

    // Define all patterns to match vehicle sensors
    const patterns = [
      `sensor.${lowerVehicleId}_`,
      `sensor.ev_trip_planner_${lowerVehicleId}_`
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
   * Includes: sensor.*, binary_sensor.*, and all vehicle-specific sensors
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

    // Define all patterns to capture vehicle sensors
    // Include all entity types: sensor, binary_sensor, input_number, input_boolean
    // Pattern 1: sensor.{vehicle_id}_{sensor_name} - direct vehicle sensors
    // Pattern 2: binary_sensor.{vehicle_id}_{sensor_name} - binary sensors (charging, etc.)
    // Pattern 3: input_number.{vehicle_id}_{sensor_name} - numeric inputs
    // Pattern 4: input_boolean.{vehicle_id}_{sensor_name} - boolean inputs
    // Pattern 5: sensor.ev_trip_planner_{vehicle_id}_{sensor_name} - EV Trip Planner sensors
    // Pattern 6: binary_sensor.ev_trip_planner_{vehicle_id}_{sensor_name} - EV Trip Planner binary sensors
    const patterns = [
      `sensor.${lowerVehicleId}_`,
      `binary_sensor.${lowerVehicleId}_`,
      `input_number.${lowerVehicleId}_`,
      `input_boolean.${lowerVehicleId}_`,
      `sensor.ev_trip_planner_${lowerVehicleId}_`,
      `binary_sensor.ev_trip_planner_${lowerVehicleId}_`,
    ];

    console.log('EV Trip Planner Panel: Searching for ALL vehicle sensors');
    console.log('EV Trip Planner Panel: Patterns:', patterns);
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

    console.log('EV Trip Planner Panel: Found', Object.keys(result).length, 'sensors');

    // Log any missing sensor patterns for debugging
    const expectedPatterns = [
      `sensor.${lowerVehicleId}_soc`,
      `sensor.${lowerVehicleId}_range`,
      `sensor.${lowerVehicleId}_charging`,
      `sensor.${lowerVehicleId}_consumption`,
    ];

    const missingPatterns = expectedPatterns.filter(pattern => {
      const found = Object.keys(result).some(entityId => entityId.includes(pattern.split('.').pop().split('_')[0]));
      return !found;
    });

    if (missingPatterns.length > 0) {
      console.log('EV Trip Planner Panel: Some expected patterns may be missing:', missingPatterns);
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
   */
  _entityIdToName(entityId) {
    // Remove prefix (sensor., binary_sensor., input_number., etc.) and underscores
    const name = entityId.replace(/^[\w_]+\./, '').replace(/_/g, ' ');
    return name
      .split(' ')
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
   * Returns "No disponible" for unavailable/unknown states
   * Formats numbers with appropriate decimal places based on value type
   */
  _formatSensorValue(entityId) {
    const states = this._hass?.states || {};
    const state = states[entityId];
    if (!state) {
      return 'No disponible';
    }

    const unit = this._getUnit(entityId);
    let value = state.state;

    // Handle unavailable/unknown states
    if (value === 'unavailable' || value === 'unknown' || value === 'N/A' || value === 'none' || value === '' || value === null) {
      return 'No disponible';
    }

    // Check if it's a boolean value (binary sensor)
    if (value === 'on' || value === 'off' || value === 'true' || value === 'false') {
      return this._formatBooleanValue(value);
    }

    // Try to parse as number and format appropriately
    const numericValue = parseFloat(value);
    if (!isNaN(numericValue)) {
      value = this._formatNumericValue(numericValue, unit);
      return unit && !unit.includes('%') ? `${value} ${unit}` : value;
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
   * Format numeric values with appropriate decimal places
   */
  _formatNumericValue(value, unit) {
    // Handle percentages
    if (unit === '%' || (value >= 0 && value <= 100)) {
      return value.toFixed(1) + '%';
    }

    // Handle small values (less than 1) - 2 decimal places
    if (value > 0 && value < 1) {
      return value.toFixed(2);
    }

    // Handle values between 1 and 1000 - 1 decimal place
    if (value >= 1 && value < 1000) {
      return value.toFixed(1);
    }

    // Handle large values - 0 decimal places
    return value.toFixed(0);
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
    // CRITICAL: Prevent re-rendering - if already rendered, just update
    if (this._rendered) {
      console.log('EV Trip Planner Panel: Already rendered, calling _update instead');
      this._update();
      return;
    }

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

    // CRITICAL: Stop polling immediately when rendering
    if (this._pollTimeout) {
      clearTimeout(this._pollTimeout);
      this._pollTimeout = null;
    }

    this._rendered = true;
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
              const isUnavailable = formattedValue === 'No disponible';
              const stateAttr = isUnavailable ? 'data-state="unavailable"' : '';
              return `
            <div class="sensor-item" ${stateAttr} data-entity-id="${s.entityId}">
              <div class="sensor-left">
                <span class="sensor-icon">${s.icon}</span>
                <span class="sensor-name" title="${entityIdDisplay}">${s.name}</span>
              </div>
              <div class="sensor-right">
                <span class="sensor-value">${formattedValue}</span>
              </div>
            </div>
              `;
            }).join('')}
          </div>
        </div>
      `;
      }).join('');

    // Fetch trips asynchronously and render them
    this._renderTripsSection().catch(error => {
      console.error('EV Trip Planner Panel: Error rendering trips section:', error);
    });

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
          <div class="trips-section">
            <div class="trips-header">
              <h2>Viajes Programados</h2>
              <button class="add-trip-btn" onclick="this.closest('.panel-container').querySelector('ev-trip-planner-panel')._showTripForm()">
                + Agregar Viaje
              </button>
            </div>
            <div id="trips-section">
              <h2>Loading trips...</h2>
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
      .status-section, .sensors-section, .trips-section {
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
      /* Sensor items list styling */
      .sensor-items-list {
        display: flex;
        flex-direction: column;
        gap: 8px;
      }
      .sensor-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 12px 16px;
        background-color: var(--panel-background, #fafafa);
        border-radius: 6px;
        border-left: 3px solid var(--panel-primary-color, #2196f3);
        transition: background-color 0.2s, transform 0.2s;
      }
      .sensor-item:hover {
        background-color: var(--panel-primary-light, #e3f2fd);
        transform: translateX(4px);
      }
      .sensor-item:active {
        transform: translateX(0);
      }
      .sensor-left {
        display: flex;
        align-items: center;
        gap: 12px;
        flex: 1;
        min-width: 0;
      }
      .sensor-icon {
        font-size: 18px;
        width: 24px;
        text-align: center;
      }
      .sensor-name {
        flex: 1;
        font-size: 14px;
        color: var(--panel-text-primary, #212121);
        font-weight: 500;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
      .sensor-right {
        flex-shrink: 0;
      }
      .sensor-value {
        font-size: 15px;
        font-weight: 600;
        color: var(--panel-primary-color, #1976d2);
        white-space: nowrap;
        min-width: 80px;
        text-align: right;
        padding: 4px 8px;
        background-color: rgba(33, 150, 243, 0.08);
        border-radius: 4px;
      }
      .sensor-item[data-state="unavailable"] .sensor-value,
      .sensor-item[data-state="unknown"] .sensor-value,
      .sensor-item[data-state="no disponible"] .sensor-value {
        color: var(--panel-text-secondary, #757575);
        font-style: italic;
      }
      .no-sensors {
        text-align: center;
        color: var(--panel-text-secondary, #757575);
        padding: 32px 20px;
        font-size: 14px;
        background-color: var(--panel-background, #fafafa);
        border-radius: 8px;
        border: 2px dashed var(--panel-divider, #e0e0e0);
      }
      /* Trips section styles */
      .trips-section {
        margin-bottom: 24px;
      }
      .trips-section h2 {
        font-size: 16px;
        margin-bottom: 12px;
        color: var(--secondary-text-color, #757575);
      }
      .trips-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
      }
      .add-trip-btn {
        background-color: var(--primary-color, #03a9f4);
        color: white;
        border: none;
        padding: 10px 20px;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        transition: background-color 0.2s, transform 0.2s;
      }
      .add-trip-btn:hover {
        background-color: #0288d1;
        transform: translateY(-1px);
      }
      .add-trip-btn:active {
        transform: translateY(0);
      }
      .trips-list {
        background: var(--card-background-color, white);
        border-radius: 8px;
        padding: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
      }
      .trip-card {
        background: var(--card-background-color, white);
        border-radius: 8px;
        padding: 16px;
        margin-bottom: 12px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.12);
        transition: transform 0.2s, box-shadow 0.2s;
      }
      .trip-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 3px 6px rgba(0,0,0,0.15);
      }
      .trip-card-inactive {
        opacity: 0.7;
      }
      .trip-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
      }
      .trip-type {
        font-size: 12px;
        font-weight: 600;
        color: var(--primary-color, #03a9f4);
        text-transform: uppercase;
      }
      .trip-status {
        font-size: 11px;
        font-weight: 600;
        padding: 4px 8px;
        border-radius: 4px;
      }
      .trip-status.status-active {
        background-color: rgba(76, 175, 80, 0.1);
        color: #2e7d32;
      }
      .trip-status.status-inactive {
        background-color: rgba(255, 152, 0, 0.1);
        color: #ef6c00;
      }
      .trip-info {
        margin-bottom: 8px;
      }
      .trip-time {
        font-size: 14px;
        font-weight: 500;
        color: var(--primary-text-color, #212121);
        margin-bottom: 4px;
      }
      .trip-details {
        display: flex;
        align-items: center;
        font-size: 13px;
        color: var(--secondary-text-color, #757575);
      }
      .trip-detail {
        font-weight: 500;
      }
      .trip-separator {
        margin: 0 8px;
        color: var(--divider-color, #e0e0e0);
      }
      .trip-description {
        font-size: 13px;
        color: var(--secondary-text-color, #757575);
        margin-top: 8px;
        padding-top: 8px;
        border-top: 1px solid var(--divider-color, #e0e0e0);
      }
      .trip-id {
        font-size: 11px;
        color: var(--secondary-text-color, #757575);
        text-align: right;
      }
      .trip-actions {
        display: flex;
        justify-content: flex-end;
        gap: 8px;
        margin-top: 12px;
        padding-top: 12px;
        border-top: 1px solid var(--divider-color, #e0e0e0);
      }
      .trip-action-btn {
        border: none;
        padding: 6px 12px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: 500;
        cursor: pointer;
        transition: background-color 0.2s, transform 0.1s;
      }
      .trip-action-btn:active {
        transform: scale(0.95);
      }
      .edit-btn {
        background-color: var(--primary-color, #03a9f4);
        color: white;
      }
      .edit-btn:hover {
        background-color: #0288d1;
      }
      .delete-btn {
        background-color: rgba(211, 47, 47, 0.1);
        color: #d32f2f;
      }
      .delete-btn:hover {
        background-color: rgba(211, 47, 47, 0.2);
      }
      .no-trips {
        text-align: center;
        color: var(--secondary-text-color, #757575);
        padding: 20px;
        font-style: italic;
      }
      .error-trips {
        text-align: center;
        color: #d32f2f;
        padding: 20px;
        background-color: rgba(211, 47, 47, 0.1);
        border-radius: 8px;
      }
      /* Trip creation form styles */
      .trip-form-overlay {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background-color: rgba(0, 0, 0, 0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 1000;
      }
      .trip-form-container {
        background: var(--card-background-color, white);
        border-radius: 12px;
        padding: 24px;
        max-width: 500px;
        width: 90%;
        max-height: 90vh;
        overflow-y: auto;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
      }
      .trip-form-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 20px;
        padding-bottom: 12px;
        border-bottom: 2px solid var(--divider-color, #e0e0e0);
      }
      .trip-form-header h3 {
        margin: 0;
        font-size: 18px;
        color: var(--primary-color, #03a9f4);
      }
      .close-form-btn {
        background: none;
        border: none;
        font-size: 24px;
        color: var(--secondary-text-color, #757575);
        cursor: pointer;
        padding: 4px 8px;
        border-radius: 4px;
        transition: background-color 0.2s;
      }
      .close-form-btn:hover {
        background-color: rgba(0,0,0,0.05);
        color: #d32f2f;
      }
      .form-group {
        margin-bottom: 16px;
      }
      .form-group label {
        display: block;
        font-size: 14px;
        font-weight: 500;
        color: var(--primary-text-color, #212121);
        margin-bottom: 8px;
      }
      .form-group input,
      .form-group select,
      .form-group textarea {
        width: 100%;
        padding: 10px 12px;
        border: 1px solid var(--divider-color, #e0e0e0);
        border-radius: 6px;
        font-size: 14px;
        font-family: inherit;
        box-sizing: border-box;
      }
      .form-group input:focus,
      .form-group select:focus,
      .form-group textarea:focus {
        outline: none;
        border-color: var(--primary-color, #03a9f4);
        box-shadow: 0 0 0 2px rgba(3, 169, 244, 0.2);
      }
      .form-group textarea {
        resize: vertical;
        min-height: 80px;
      }
      .form-row {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
      }
      .form-actions {
        display: flex;
        gap: 12px;
        margin-top: 20px;
        padding-top: 16px;
        border-top: 1px solid var(--divider-color, #e0e0e0);
      }
      .form-actions .btn {
        flex: 1;
        padding: 12px 20px;
        border: none;
        border-radius: 6px;
        font-size: 14px;
        font-weight: 500;
        cursor: pointer;
        transition: background-color 0.2s, transform 0.2s;
      }
      .form-actions .btn-primary {
        background-color: var(--primary-color, #03a9f4);
        color: white;
      }
      .form-actions .btn-primary:hover {
        background-color: #0288d1;
        transform: translateY(-1px);
      }
      .form-actions .btn-secondary {
        background-color: var(--divider-color, #e0e0e0);
        color: var(--primary-text-color, #212121);
      }
      .form-actions .btn-secondary:hover {
        background-color: #bdbdbd;
        transform: translateY(-1px);
      }
      .form-actions .btn:active {
        transform: translateY(0);
      }
      .form-error {
        background-color: rgba(211, 47, 47, 0.1);
        border: 1px solid #d32f2f;
        color: #d32f2f;
        padding: 12px;
        border-radius: 6px;
        font-size: 13px;
        margin-bottom: 16px;
      }
      @media (max-width: 600px) {
        .status-grid {
          grid-template-columns: repeat(2, 1fr);
        }
        .status-value {
          font-size: 16px;
        }
        .trip-details {
          flex-direction: column;
          align-items: flex-start;
        }
        .trip-separator {
          display: none;
        }
        .form-row {
          grid-template-columns: 1fr;
        }
        .form-actions {
          flex-direction: column;
        }
        .trip-form-container {
          width: 95%;
          padding: 16px;
        }
        .trip-form-header h3 {
          font-size: 16px;
        }
      }
    `;
  }
}

// Register the custom element
customElements.define('ev-trip-planner-panel', EVTripPlannerPanel);
