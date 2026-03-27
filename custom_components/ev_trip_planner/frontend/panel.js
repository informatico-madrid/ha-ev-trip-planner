class EVTripPlannerPanel extends HTMLElement {
  constructor() {
    super();
    this._hass = null;
    this._vehicleId = null;
    this._tripList = null;
    this._showForm = false;
    this._formType = 'recurrente';
    this._editingTrip = null;
  }

  connectedCallback() {
    this._initialize();
  }

  async _initialize() {
    this._extractVehicleId();
    await this._waitForHass();
    this._loadTrips();
  }

  _extractVehicleId() {
    const urlPath = window.location.pathname;
    const match = urlPath.match(/ev-trip-planner-(.+)/);
    this._vehicleId = match ? match[1] : null;
  }

  async _waitForHass() {
    return new Promise(resolve => {
      const checkHass = () => {
        const hass = document.querySelector('home-assistant')?.hass;
        if (hass) {
          this._hass = hass;
          resolve();
        } else {
          setTimeout(checkHass, 100);
        }
      };
      checkHass();
    });
  }

  async _loadTrips() {
    if (!this._hass || !this._vehicleId) return;

    try {
      const response = await this._callTripService('trip_list', {
        vehicle_id: this._vehicleId,
      });

      let tripsData = response;
      if (tripsData && tripsData.recurring_trips !== undefined) {
        const allTrips = [
          ...tripsData.recurring_trips.map(t => ({...t, trip_type: 'recurrente'})),
          ...tripsData.punctual_trips.map(t => ({...t, trip_type: 'puntual'})),
        ];
        this._tripList = allTrips;
      } else {
        this._tripList = [];
      }
    } catch (error) {
      console.error('Error loading trips:', error);
      this._tripList = [];
    }

    this._render();
  }

  _render() {
    if (!this.shadowRoot) return;

    const shadowRoot = this.attachShadow({ mode: 'open' });
    const style = document.createElement('style');

    style.textContent = `
      :host { display: block; padding: 16px; font-family: Arial, sans-serif; }
      .add-trip-btn {
        background: #2196F3;
        color: white;
        padding: 8px 16px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
      }
      .add-trip-btn:hover { background: #1976D2; }
      .trip-form-overlay {
        position: fixed;
        top: 0; left: 0; right: 0; bottom: 0;
        background: rgba(0,0,0,0.5);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
      }
      .trip-form {
        background: white;
        padding: 24px;
        border-radius: 8px;
        min-width: 400px;
        max-width: 500px;
      }
      .form-group { margin-bottom: 16px; }
      .form-group label { display: block; margin-bottom: 4px; font-weight: bold; }
      .form-group select, .form-group input {
        width: 100%;
        padding: 8px;
        border: 1px solid #ccc;
        border-radius: 4px;
        box-sizing: border-box;
      }
      .btn-primary {
        background: #2196F3;
        color: white;
        padding: 10px 20px;
        border: none;
        border-radius: 4px;
        cursor: pointer;
      }
      .btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
      .trip-card {
        border: 1px solid #ddd;
        padding: 12px;
        margin-bottom: 8px;
        border-radius: 4px;
      }
      .trip-card button {
        margin-right: 8px;
        padding: 4px 8px;
        cursor: pointer;
      }
      .success { color: #4CAF50; }
      .error { color: #f44336; }
    `;

    // Build HTML content
    let htmlContent = `
      ${style}
      <button class="add-trip-btn" @click="${this._openForm}">Add Trip</button>
    `;

    // Trip list with event delegation
    htmlContent += this._renderTripList();

    // Form overlay
    htmlContent += this._renderForm();

    shadowRoot.innerHTML = htmlContent;

    // Add event delegation for trip list
    shadowRoot.addEventListener('click', (e) => {
      if (e.target.classList.contains('delete-btn')) {
        const tripId = e.target.getAttribute('data-trip-id');
        if (tripId) {
          e.stopPropagation();
          this._handleDeleteTrip(tripId);
        }
      } else if (e.target.classList.contains('edit-btn')) {
        const tripId = e.target.getAttribute('data-trip-id');
        if (tripId) {
          e.stopPropagation();
          this._handleTripEdit(tripId);
        }
      }
    });
  }

  _renderTripList() {
    if (!this._tripList || this._tripList.length === 0) {
      return '<div>No trips found</div>';
    }

    const tripCards = this._tripList.map(trip => `
      <div class="trip-card" data-trip-id="${trip.id}">
        <strong>${trip.type}</strong> - ${trip.km} km
        <button class="edit-btn" data-trip-id="${trip.id}">Edit</button>
        <button class="delete-btn" data-trip-id="${trip.id}">Delete</button>
      </div>
    `).join('');

    return `<div class="trip-list">${tripCards}</div>`;
  }

  _renderForm() {
    if (!this._showForm) return '';

    const isEdit = !!this._editingTrip;
    const formType = this._formType;
    const trip = this._editingTrip;

    return `
      <div class="trip-form-overlay" @click="${this._handleOverlayClick}">
        <div class="trip-form" @click="${e => e.stopPropagation()}">
          <h2>${isEdit ? 'Edit Trip' : 'Add Trip'}</h2>
          <form @submit="${this._editingTrip ? this._handleTripUpdate : this._handleTripCreate}">
            <div class="form-group">
              <label for="trip-type">Type:</label>
              <select id="trip-type" name="type" @change="${this._handleTypeChange}">
                <option value="recurrente">Recurrente</option>
                <option value="puntual">Puntual</option>
              </select>
            </div>

            <div class="form-group" id="day-time-group">
              <label for="trip-day">Day:</label>
              <select id="trip-day" name="day">
                <option value="1">Monday</option>
                <option value="2">Tuesday</option>
                <option value="3">Wednesday</option>
                <option value="4">Thursday</option>
                <option value="5">Friday</option>
                <option value="6">Saturday</option>
                <option value="7">Sunday</option>
              </select>

              <label for="trip-time">Time:</label>
              <input type="time" id="trip-time" name="time" value="09:00">
            </div>

            <div class="form-group" id="datetime-group" style="display: none;">
              <label for="trip-datetime">Date & Time:</label>
              <input type="datetime-local" id="trip-datetime" name="datetime">
            </div>

            <div class="form-group">
              <label for="trip-km">Distance (km):</label>
              <input type="number" id="trip-km" name="km" step="0.1" required>
            </div>

            <div class="form-group">
              <label for="trip-kwh">Energy (kWh):</label>
              <input type="number" id="trip-kwh" name="kwh" step="0.1" required>
            </div>

            <div class="form-group">
              <label for="trip-description">Description:</label>
              <input type="text" id="trip-description" name="description">
            </div>

            ${isEdit ? `<input type="hidden" name="edit-trip-id" value="${trip.id}">` : ''}

            <button type="submit" class="btn-primary">
              ${isEdit ? 'Update' : 'Create'}
            </button>
            <button type="button" @click="${this._closeForm}" style="margin-left: 8px;">Cancel</button>
          </form>
        </div>
      </div>
    `;
  }

  _handleTypeChange(e) {
    const type = e.target.value;
    const dayTimeGroup = document.getElementById('day-time-group');
    const datetimeGroup = document.getElementById('datetime-group');

    if (type === 'recurrente') {
      dayTimeGroup.style.display = 'block';
      datetimeGroup.style.display = 'none';
    } else {
      dayTimeGroup.style.display = 'none';
      datetimeGroup.style.display = 'block';
    }
  }

  _openForm() {
    this._formType = 'recurrente';
    this._editingTrip = null;
    this._showForm = true;
    this._render();
  }

  _closeForm() {
    this._showForm = false;
    this._editingTrip = null;
    this._render();
  }

  _handleOverlayClick(e) {
    if (e.target.classList.contains('trip-form-overlay')) {
      this._closeForm();
    }
  }

  /**
   * Handle trip creation form submission
   * @param {Event} e - Form submit event
   * @memberof EVTripPlannerPanel
   */
  async _handleTripCreate(e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);

    // Extract form data
    const km = formData.get('km');
    const kwh = formData.get('kwh');

    // Validate required fields
    if (!km || parseFloat(km) <= 0) {
      this._showAlert('❌ La distancia (km) debe ser un número positivo', false);
      return;
    }

    if (!kwh || parseFloat(kwh) <= 0) {
      this._showAlert('❌ El consumo de energía (kWh) debe ser un número positivo', false);
      return;
    }

    if (!this._hass || !this._vehicleId) {
      this._showAlert('Error: No hay conexión con Home Assistant', false);
      return;
    }

    // Continue with service call
    const type = formData.get('type');

    // Build service data
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

    serviceData.km = parseFloat(km);
    serviceData.kwh = parseFloat(kwh);
    serviceData.description = formData.get('description') || '';

    // Set loading state
    const submitBtn = form.querySelector('.btn-primary');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Creando...';
    submitBtn.disabled = true;

    try {
      await this._callTripService('trip_create', serviceData);
      this._closeForm();
      await this._loadTrips();
      this._showAlert('✅ Viaje creado exitosamente', true);
    } catch (error) {
      console.error('EV Trip Planner Panel: Error creating trip:', error);
      this._showAlert(`❌ Error al crear el viaje: ${error.message}`, false);
    } finally {
      form.reset();
      submitBtn.textContent = originalText;
      submitBtn.disabled = false;
    }
  }

  /**
   * Handle trip update form submission
   * @param {Event} e - Form submit event
   * @memberof EVTripPlannerPanel
   */
  async _handleTripUpdate(e) {
    e.preventDefault();

    const form = e.target;
    const formData = new FormData(form);

    const tripId = formData.get('edit-trip-id');
    if (!tripId) {
      this._showAlert('❌ Error: No se pudo identificar el viaje', false);
      return;
    }

    const km = formData.get('km');
    const kwh = formData.get('kwh');

    // Validate
    if (!km || parseFloat(km) <= 0) {
      this._showAlert('❌ La distancia (km) debe ser un número positivo', false);
      return;
    }

    if (!kwh || parseFloat(kwh) <= 0) {
      this._showAlert('❌ El consumo de energía (kWh) debe ser un número positivo', false);
      return;
    }

    if (!this._hass || !this._vehicleId) {
      this._showAlert('Error: No hay conexión con Home Assistant', false);
      return;
    }

    const type = formData.get('type');

    // Build service data
    const serviceData = {
      vehicle_id: this._vehicleId,
      trip_id: tripId,
      type: type,
    };

    if (type === 'puntual') {
      serviceData.datetime = formData.get('datetime');
    } else {
      serviceData.dia_semana = formData.get('day');
      serviceData.hora = formData.get('time');
    }

    serviceData.km = parseFloat(km);
    serviceData.kwh = parseFloat(kwh);
    serviceData.description = formData.get('description') || '';

    // Set loading state
    const submitBtn = form.querySelector('.btn-primary');
    const originalText = submitBtn.textContent;
    submitBtn.textContent = 'Guardando...';
    submitBtn.disabled = true;

    try {
      await this._callTripService('trip_update', serviceData);
      this._closeForm();
      await this._loadTrips();
      this._showAlert('✅ Viaje actualizado exitosamente', true);
    } catch (error) {
      console.error('Error updating trip:', error);
      this._showAlert(`❌ Error al actualizar el viaje: ${error.message}`, false);
    } finally {
      form.reset();
      submitBtn.textContent = originalText;
      submitBtn.disabled = false;
    }
  }

  /**
   * Handle trip edit by fetching trip data and displaying in form
   * @param {string} tripId - The trip ID to edit
   * @memberof EVTripPlannerPanel
   */
  async _handleTripEdit(tripId) {
    const trip = await this._getTripById(tripId);
    if (!trip) {
      this._showAlert('❌ Error: Viaje no encontrado', false);
      return;
    }

    this._showEditForm(trip);
  }

  /**
   * Show edit form with pre-filled trip data
   * @param {Object} trip - Trip data object
   * @memberof EVTripPlannerPanel
   */
  _showEditForm(trip) {
    this._editingTrip = trip;
    this._showForm = true;
    this._formType = trip.type === 'puntual' ? 'puntual' : 'recurrente';
    this._render();

    // Wait for DOM update and pre-fill form
    setTimeout(() => {
      const form = this.shadowRoot.querySelector('form');
      if (form) {
        form.querySelector('#trip-type').value = trip.type === 'puntual' ? 'puntual' : 'recurrente';
        form.querySelector('#trip-day').value = trip.dia_semana || '1';
        form.querySelector('#trip-time').value = trip.hora || '09:00';
        form.querySelector('#trip-km').value = trip.km || '';
        form.querySelector('#trip-kwh').value = trip.kwh || '';
        form.querySelector('#trip-description').value = trip.description || '';

        // Show/hide datetime group based on type
        this._handleTypeChange({
          target: { value: this._formType }
        });
      }
    }, 0);
  }

  /**
   * Call EV Trip Planner service with centralized error handling
   * @param {string} serviceName - Name of the service to call
   * @param {Object} serviceData - Service data payload
   * @returns {Promise<Object>} Service call result
   * @memberof EVTripPlannerPanel
   */
  async _callTripService(serviceName, serviceData) {
    try {
      const result = await this._hass.callService('ev_trip_planner', serviceName, serviceData);
      return result;
    } catch (error) {
      console.error(`Service call failed for ${serviceName}:`, error);
      throw error;
    }
  }

  /**
   * Fetch trip data by ID from the service
   * @param {string} tripId - The trip ID to fetch
   * @returns {Promise<Object|null>} Trip data or null if not found
   * @memberof EVTripPlannerPanel
   */
  async _getTripById(tripId) {
    if (!this._hass || !this._vehicleId) return null;

    try {
      const response = await this._callTripService('trip_list', {
        vehicle_id: this._vehicleId,
        trip_id: tripId,
      });

      let tripsData = response;
      if (tripsData && tripsData.recurring_trips !== undefined) {
        const allTrips = [
          ...tripsData.recurring_trips.map(t => ({...t, trip_type: 'recurrente'})),
          ...tripsData.punctual_trips.map(t => ({...t, trip_type: 'puntual'})),
        ];
        return allTrips.find(t => t.id === tripId) || null;
      }
      return null;
    } catch (error) {
      console.error('Error fetching trip:', error);
      return null;
    }
  }

  /**
   * Handle trip deletion with confirmation dialog
   * @param {string} tripId - The trip ID to delete
   * @memberof EVTripPlannerPanel
   */
  async _handleDeleteTrip(tripId) {
    if (!confirm('¿Estás seguro de que quieres eliminar este viaje?')) {
      return;
    }

    const deleteBtn = document.querySelector(`[data-trip-id="${tripId}"].delete-btn`);
    const originalText = deleteBtn?.textContent;
    if (deleteBtn) {
      deleteBtn.textContent = 'Eliminando...';
      deleteBtn.disabled = true;
    }

    try {
      await this._callTripService('delete_trip', {
        vehicle_id: this._vehicleId,
        trip_id: tripId,
      });

      await this._loadTrips();
      this._showAlert('✅ Viaje eliminado exitosamente', true);
    } catch (error) {
      console.error('Error deleting trip:', error);
      this._showAlert(`❌ Error: ${error.message}`, false);
    } finally {
      if (deleteBtn) {
        deleteBtn.textContent = originalText;
        deleteBtn.disabled = false;
      }
    }
  }

  /**
   * Show toast notification alert
   * @param {string} message - Alert message to display
   * @param {boolean} isSuccess - Whether this is a success message
   * @memberof EVTripPlannerPanel
   */
  _showAlert(message, isSuccess) {
    const alertDiv = document.createElement('div');
    alertDiv.textContent = message;
    alertDiv.className = isSuccess ? 'success' : 'error';
    alertDiv.style.cssText = 'position: fixed; top: 20px; right: 20px; padding: 12px 24px; border-radius: 4px; z-index: 9999;';
    document.body.appendChild(alertDiv);

    setTimeout(() => {
      alertDiv.remove();
    }, 5000);
  }
}

customElements.define('ev-trip-planner-panel', EVTripPlannerPanel);
