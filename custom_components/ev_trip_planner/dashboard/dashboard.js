/**
 * EV Trip Planner Dashboard JavaScript Handlers
 *
 * Handles CRUD operations for trips through the Home Assistant Lovelace dashboard.
 * Provides service call handlers for creating, updating, and deleting trips.
 *
 * @version 1.0.0
 * @author EV Trip Planner Team
 */

/**
 * EVTripPlannerDashboard - Main controller for dashboard CRUD operations
 *
 * @namespace EVTripPlannerDashboard
 */
const EVTripPlannerDashboard = (() => {
  'use strict';

  /**
   * Get the Home Assistant API instance
   *
   * @returns {Object} HA API instance
   */
  const getHass = () => {
    if (window.hass) {
      return window.hass;
    }
    if (window.hassConnection) {
      return window.hassConnection.hass;
    }
    throw new Error('Home Assistant not initialized');
  };

  /**
   * Call a Home Assistant service with the given parameters
   *
   * @param {string} domain - Service domain (e.g., 'ev_trip_planner')
   * @param {string} service - Service name (e.g., 'add_recurring_trip')
   * @param {Object} serviceData - Service data parameters
   * @returns {Promise<Object>} Service call result
   */
  const callService = async (domain, service, serviceData) => {
    const hass = getHass();
    try {
      const result = await hass.callService(domain, service, serviceData);
      return result;
    } catch (error) {
      console.error(`Service call failed for ${domain}.${service}:`, error);
      throw error;
    }
  };

  /**
   * Show a success notification
   *
   * @param {string} message - Success message to display
   */
  const showSuccess = (message) => {
    if (window._huiNotification) {
      window._huiNotification(message, 'success');
    } else if (window.showToast) {
      window.showToast(message, 'success');
    } else {
      console.log(`✓ ${message}`);
    }
  };

  /**
   * Show an error notification
   *
   * @param {string} message - Error message to display
   */
  const showError = (message) => {
    if (window._huiNotification) {
      window._huiNotification(message, 'error');
    } else if (window.showToast) {
      window.showToast(message, 'error');
    } else {
      console.error(`✗ ${message}`);
    }
  };

  /**
   * Navigate to a different Lovelace view
   *
   * @param {string} path - Navigation path (e.g., '/lovelace/dashboard')
   */
  const navigate = (path) => {
    if (window.location) {
      window.location.href = path;
    } else if (window.history && window.history.pushState) {
      window.history.pushState(null, '', path);
      if (window.dispatchEvent) {
        window.dispatchEvent(new Event('locationchange'));
      }
    }
  };

  /**
   * Refresh the current view
   */
  const refreshView = () => {
    if (window.location) {
      window.location.reload();
    } else if (window.hassConnection) {
      window.hassConnection.connection.sendMessage({
        type: 'config/lovelace/drawer',
      });
    }
  };

  /**
   * Add a recurring trip through the dashboard
   *
   * @param {Object} tripData - Trip configuration data
   * @param {string} tripData.vehicle_id - Vehicle identifier
   * @param {string} tripData.dia_semana - Day of the week
   * @param {string} tripData.hora - Trip time
   * @param {number} tripData.km - Distance in kilometers
   * @param {number} tripData.kwh - Energy required in kWh
   * @param {string} tripData.descripcion - Trip description (optional)
   * @returns {Promise<Object>} Service call result
   */
  const addRecurringTrip = async (tripData) => {
    const {
      vehicle_id,
      dia_semana,
      hora,
      km,
      kwh,
      descripcion = '',
    } = tripData;

    try {
      const result = await callService(
        'ev_trip_planner',
        'add_recurring_trip',
        {
          vehicle_id,
          dia_semana,
          hora,
          km: parseFloat(km),
          kwh: parseFloat(kwh),
          descripcion,
        }
      );

      showSuccess(`Viaje recurrente agregado exitosamente (${dia_semana})`);
      return result;
    } catch (error) {
      showError(`Error al agregar viaje recurrente: ${error.message}`);
      throw error;
    }
  };

  /**
   * Add a punctual trip through the dashboard
   *
   * @param {Object} tripData - Trip configuration data
   * @param {string} tripData.vehicle_id - Vehicle identifier
   * @param {string} tripData.datetime - Trip date and time
   * @param {number} tripData.km - Distance in kilometers
   * @param {number} tripData.kwh - Energy required in kWh
   * @param {string} tripData.descripcion - Trip description (optional)
   * @returns {Promise<Object>} Service call result
   */
  const addPunctualTrip = async (tripData) => {
    const {
      vehicle_id,
      datetime,
      km,
      kwh,
      descripcion = '',
    } = tripData;

    try {
      const result = await callService(
        'ev_trip_planner',
        'add_punctual_trip',
        {
          vehicle_id,
          datetime,
          km: parseFloat(km),
          kwh: parseFloat(kwh),
          descripcion,
        }
      );

      showSuccess(`Viaje puntual agregado exitosamente (${datetime})`);
      return result;
    } catch (error) {
      showError(`Error al agregar viaje puntual: ${error.message}`);
      throw error;
    }
  };

  /**
   * Update an existing trip through the dashboard
   *
   * @param {Object} tripData - Trip update data
   * @param {string} tripData.vehicle_id - Vehicle identifier
   * @param {string} tripData.trip_id - Trip identifier
   * @param {string} tripData.tipo - Trip type ('recurrente' or 'puntual')
   * @param {Object} tripData.config - Trip configuration based on type
   * @returns {Promise<Object>} Service call result
   */
  const updateTrip = async (tripData) => {
    const {
      vehicle_id,
      trip_id,
      tipo,
      config,
    } = tripData;

    try {
      const result = await callService(
        'ev_trip_planner',
        'update_trip',
        {
          vehicle_id,
          trip_id,
          tipo,
          ...config,
        }
      );

      showSuccess('Viaje actualizado exitosamente');
      return result;
    } catch (error) {
      showError(`Error al actualizar viaje: ${error.message}`);
      throw error;
    }
  };

  /**
   * Delete a trip through the dashboard
   *
   * @param {Object} tripData - Trip deletion data
   * @param {string} tripData.vehicle_id - Vehicle identifier
   * @param {string} tripData.trip_type - Trip type ('recurring' or 'punctual')
   * @param {string} tripData.trip_id - Trip identifier (optional)
   * @returns {Promise<Object>} Service call result
   */
  const deleteTrip = async (tripData) => {
    const {
      vehicle_id,
      trip_type,
      trip_id = null,
    } = tripData;

    try {
      const result = await callService(
        'ev_trip_planner',
        'delete_trip',
        {
          vehicle_id,
          trip_type,
          trip_id,
        }
      );

      showSuccess('Viaje eliminado exitosamente');
      return result;
    } catch (error) {
      showError(`Error al eliminar viaje: ${error.message}`);
      throw error;
    }
  };

  /**
   * Get list of trips for a vehicle
   *
   * @param {string} vehicle_id - Vehicle identifier
   * @returns {Promise<Object>} Trips list data
   */
  const getTrips = async (vehicle_id) => {
    try {
      const result = await callService(
        'ev_trip_planner',
        'get_trips',
        { vehicle_id }
      );
      return result;
    } catch (error) {
      showError(`Error al obtener lista de viajes: ${error.message}`);
      throw error;
    }
  };

  /**
   * Validate trip data before submission
   *
   * @param {Object} tripData - Trip data to validate
   * @returns {Object} Validation result with isValid flag and errors
   */
  const validateTripData = (tripData) => {
    const errors = [];

    if (!tripData.vehicle_id) {
      errors.push('Vehicle ID is required');
    }

    if (!tripData.km || tripData.km <= 0) {
      errors.push('Distance (km) must be greater than 0');
    }

    if (!tripData.kwh || tripData.kwh <= 0) {
      errors.push('Energy (kWh) must be greater than 0');
    }

    if (tripData.tipo === 'recurrente' && !tripData.dia_semana) {
      errors.push('Day of week is required for recurring trips');
    }

    if (tripData.tipo === 'puntual' && !tripData.datetime) {
      errors.push('Date and time is required for punctual trips');
    }

    return {
      isValid: errors.length === 0,
      errors,
    };
  };

  /**
   * Parse service data from HTML form elements
   *
   * @param {HTMLFormElement} form - Form element
   * @param {string} vehicle_id - Vehicle identifier
   * @param {string} tripType - Trip type ('recurrente' or 'puntual')
   * @returns {Object} Parsed service data
   */
  const parseFormServiceData = (form, vehicle_id, tripType) => {
    const formData = new FormData(form);
    const serviceData = { vehicle_id };

    if (tripType === 'recurrente') {
      serviceData.dia_semana = formData.get('dia_semana');
      serviceData.hora = formData.get('hora');
      serviceData.km = formData.get('km');
      serviceData.kwh = formData.get('kwh');
      serviceData.descripcion = formData.get('descripcion') || '';
    } else if (tripType === 'puntual') {
      serviceData.datetime = formData.get('datetime');
      serviceData.km = formData.get('km');
      serviceData.kwh = formData.get('kwh');
      serviceData.descripcion = formData.get('descripcion') || '';
    }

    return serviceData;
  };

  /**
   * Handle form submission for trip creation
   *
   * @param {Event} event - Form submit event
   * @param {string} tripType - Trip type ('recurrente' or 'puntual')
   */
  const handleFormSubmit = async (event, tripType) => {
    event.preventDefault();

    const form = event.target;
    const vehicle_id = form.dataset.vehicleId;

    const serviceData = parseFormServiceData(form, vehicle_id, tripType);

    const validation = validateTripData(serviceData);
    if (!validation.isValid) {
      showError(`Validación fallida: ${validation.errors.join(', ')}`);
      return;
    }

    try {
      if (tripType === 'recurrente') {
        await addRecurringTrip(serviceData);
      } else {
        await addPunctualTrip(serviceData);
      }

      form.reset();
      refreshView();
    } catch (error) {
      console.error('Form submission failed:', error);
    }
  };

  /**
   * Initialize dashboard event handlers
   */
  const init = () => {
    // Attach event listeners to trip creation forms
    const forms = document.querySelectorAll('[data-trip-form]');
    forms.forEach((form) => {
      form.addEventListener('submit', (event) => {
        const tripType = form.dataset.tripType;
        handleFormSubmit(event, tripType);
      });
    });

    // Attach event listeners to trip update forms
    const updateForms = document.querySelectorAll('[data-update-form]');
    updateForms.forEach((form) => {
      form.addEventListener('submit', async (event) => {
        event.preventDefault();

        const vehicleId = form.dataset.vehicleId;
        const tripId = form.dataset.tripId;
        const tipo = form.dataset.tipo;

        const serviceData = parseFormServiceData(form, vehicleId, tipo);
        serviceData.trip_id = tripId;
        serviceData.tipo = tipo;

        try {
          await updateTrip(serviceData);
          form.reset();
          refreshView();
        } catch (error) {
          console.error('Update failed:', error);
        }
      });
    });

    // Attach event listeners to delete confirmation forms
    const deleteForms = document.querySelectorAll('[data-delete-form]');
    deleteForms.forEach((form) => {
      form.addEventListener('submit', async (event) => {
        event.preventDefault();

        const vehicleId = form.dataset.vehicleId;
        const tripType = form.dataset.tripType;

        if (!confirm('¿Está seguro que desea eliminar este viaje?')) {
          return;
        }

        try {
          await deleteTrip({
            vehicle_id: vehicleId,
            trip_type: tripType,
          });
          refreshView();
        } catch (error) {
          console.error('Delete failed:', error);
        }
      });
    });
  };

  /**
   * Cleanup event handlers
   */
  const destroy = () => {
    // Remove all event listeners
    const allForms = document.querySelectorAll('[data-trip-form], [data-update-form], [data-delete-form]');
    allForms.forEach((form) => {
      form.removeEventListener('submit', () => {});
    });
  };

  // Initialize on DOM ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Public API
  return {
    addRecurringTrip,
    addPunctualTrip,
    updateTrip,
    deleteTrip,
    getTrips,
    validateTripData,
    parseFormServiceData,
    handleFormSubmit,
    init,
    destroy,
    callService,
    showSuccess,
    showError,
    navigate,
    refreshView,
  };
})();

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = EVTripPlannerDashboard;
}

// Make available globally
if (typeof window !== 'undefined') {
  window.EVTripPlannerDashboard = EVTripPlannerDashboard;
}
