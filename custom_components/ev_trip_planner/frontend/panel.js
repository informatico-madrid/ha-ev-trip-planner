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
    this._pollTimeout = null;
    this._pollStarted = false; // Track if polling has already started
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

    // Stop any pending polling since we now have hass
    if (this._pollTimeout) {
      clearTimeout(this._pollTimeout);
      this._pollTimeout = null;
    }
    // Mark polling as stopped
    this._pollStarted = false;

    // Only render if we haven't rendered yet - CRITICAL FIX
    // NOTE: _rendered is set inside _render() AFTER content is rendered, not here
    if (!this._rendered) {
      this._render();
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

    // Start polling after a short delay
    this._pollTimeout = setTimeout(poll, 100);
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

      // Use hass.connection.call_service for direct service call
      const response = await this._hass.connection.callService('ev_trip_planner', 'trip_list', {
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
      await this._hass.services.call('ev_trip_planner', 'trip_create', serviceData);

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

    await this._hass.services.call('ev_trip_planner', 'pause_recurring_trip', {
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

    await this._hass.services.call('ev_trip_planner', 'resume_recurring_trip', {
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

    await this._hass.services.call('ev_trip_planner', 'complete_punctual_trip', {
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

    await this._hass.services.call('ev_trip_planner', 'cancel_punctual_trip', {
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

      // Use the correct HA API for calling services
      const response = await this._hass.services.call('ev_trip_planner', 'trip_list', {
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

    await this._hass.services.call('ev_trip_planner', 'delete_trip', {
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
      await this._hass.services.call('ev_trip_planner', 'trip_update', serviceData);

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

    // Subscribe to all state changes for vehicle sensors
    this._unsubscribe = this._hass.connection.subscribeMessage(
      (message) => {
        if (message.type === 'event' && message.event?.event_type === 'state_changed') {
          const entityId = message.event.data?.entity_id;
          if (entityId && (entityId.startsWith(`sensor.${lowerVehicleId}_`) || entityId.startsWith(`sensor.ev_trip_planner_${lowerVehicleId}`))) {
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
            <h2>Available Sensors (${stateKeys.length})</h2>
            ${stateKeys.length > 0 ? `
              <div class="sensor-list-grouped">
                ${sensorListHtml || '<p class="no-sensors">No sensors found</p>'}
              </div>
            ` : '<p class="no-sensors">No sensors found</p>'}
          </div>
        </main>
      </div>
    `

    // Set rendered AFTER innerHTML is set (not before)
    this._rendered = true;

    // Subscribe to state changes after render
    this._subscribeToStates();

    // CRITICAL: DO NOT render trips from _render() to prevent infinite loop
    // Trip rendering must be done separately after render completes
    // Call window._tripPanel._renderTripsLater() to render trips after render

    // Schedule trips rendering after a delay to ensure panel is fully rendered
    setTimeout(() => {
      if (this._rendered) {
        this._renderTripsLater().catch(error => {
          console.error('EV Trip Planner Panel: Error rendering trips section:', error);
        });
      }
    }, 100);
  }

  /**
   * Render trips section - must be called AFTER panel is fully rendered
   * to prevent infinite recursion.
   */
  async _renderTripsLater() {
    await this._renderTripsSection().catch(error => {
      console.error('EV Trip Planner Panel: Error rendering trips section:', error);
    });
  }

  /**
   * Update individual sensor values without triggering re-render.
   * This method is called by the state subscription when sensors change.
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
