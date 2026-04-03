# Trip Creation - Research Findings

## Executive Summary

Investigación de patrones de form handling, service calls, y panel implementations en Home Assistant para implementar trip creation functionality. Se encontraron patrones establecidos en el código de EV Trip Planner que siguen las mejores prácticas de Lit web components y Home Assistant service framework.

## Research Topics

### 1. Form Handling Patterns

**Key Finding:** Home Assistant custom components use Lit web components with standardized form handling patterns.

#### Pattern 1: Event Prevention with FormData API

```javascript
async _handleTripCreate(e) {
  e.preventDefault();  // Prevent default form submission

  const form = e.target;
  const formData = new FormData(form);  // Extract form data

  const type = formData.get('type');
  const km = formData.get('km');
  const kwh = formData.get('kwh');
  const description = formData.get('description');
}
```

**Best Practices:**
- Always use `e.preventDefault()` to prevent page refresh
- Use `FormData` API for reliable data extraction
- Extract conditionally based on form type (recurrente vs puntual)

#### Pattern 2: Form Validation

```javascript
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

  // Type-specific validation
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
```

**Best Practices:**
- Validate required fields before service call
- Validate numeric fields for positive values
- Add type-specific validation rules
- Return structured error object for UI feedback

### 2. Service Call Patterns

#### Pattern 1: Standard Service Call

```javascript
try {
  await this._hass.callService('ev_trip_planner', 'trip_create', serviceData);
  this._closeForm();
  await this._loadTrips();
  alert('✅ Viaje creado exitosamente');
} catch (error) {
  console.error('EV Trip Planner Panel: Error creating trip:', error);
  alert('❌ Error al crear el viaje: ' + (error.message || 'Verifique los logs'));
} finally {
  submitBtn.textContent = originalText;
  submitBtn.disabled = false;
}
```

**Key Components:**
- Try/catch/finally for robust error handling
- Loading state management on submit button
- Form closure after success
- Trip list refresh after creation
- User feedback via alerts

#### Available Services

| Service | Method | Purpose |
|---------|--------|---------|
| `ev_trip_planner.trip_list` | `callService()` | List all trips |
| `ev_trip_planner.trip_create` | `callService()` | Create new trip |
| `ev_trip_planner.trip_update` | `callService()` | Update existing trip |
| `ev_trip_planner.delete_trip` | `callService()` | Delete trip |
| `ev_trip_planner.pause_recurring_trip` | `callService()` | Pause recurring trip |
| `ev_trip_planner.resume_recurring_trip` | `callService()` | Resume recurring trip |
| `ev_trip_planner.complete_punctual_trip` | `callService()` | Mark punctual trip as completed |
| `ev_trip_planner.cancel_punctual_trip` | `callService()` | Cancel punctual trip |

#### Pattern 2: Service Response Handling

```javascript
async _getTripsList() {
  if (!this._hass || !this._vehicleId) {
    return [];
  }

  try {
    const response = await this._hass.callService('ev_trip_planner', 'trip_list', {
      vehicle_id: this._vehicleId,
    });

    // HA service responses come directly, not wrapped in {result: {...}}
    let tripsData = response;

    if (response && response.context && !response.recurring_trips) {
      // It's an error response with only context
      return [];
    }

    if (tripsData && tripsData.recurring_trips !== undefined) {
      const recurringTrips = tripsData.recurring_trips || [];
      const punctualTrips = tripsData.punctual_trips || [];

      return [
        ...recurringTrips.map(t => ({...t, trip_type: 'recurrente'})),
        ...punctualTrips.map(t => ({...t, trip_type: 'puntual'})),
      ];
    }
  } catch (error) {
    console.error('Error fetching trips:', error);
    return [];
  }
}
```

**Key Insight:** HA service responses come directly, not wrapped in `{result: {...}}`

### 3. Error Handling and Notifications

#### Pattern 1: Dual Notification System

```javascript
// Show a success notification
const showSuccess = (message) => {
  if (window._huiNotification) {
    window._huiNotification(message, 'success');
  } else if (window.showToast) {
    window.showToast(message, 'success');
  } else {
    console.log(`✓ ${message}`);
  }
};

// Show an error notification
const showError = (message) => {
  if (window._huiNotification) {
    window._huiNotification(message, 'error');
  } else if (window.showToast) {
    window.showToast(message, 'error');
  } else {
    console.error(`✗ ${message}`);
  }
};
```

**Best Practices:**
- Fallback to console logging if UI notifications unavailable
- Use emoji icons for visual feedback
- Include error details in console for debugging

#### Pattern 2: Service Call with Retry

```javascript
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
```

### 4. Panel Implementation Patterns

#### Lit Web Component Structure

```javascript
import { LitElement, html, css } from 'https://esm.sh/lit@2.8.0?bundle';

class EVTripPlannerPanel extends LitElement {
  static properties = {
    _hass: { type: Object },
    _vehicleId: { type: String },
    _config: { type: Object },
    _rendered: { type: Boolean, value: false },
    _trips: { type: Array, value: [] },
    _isLoading: { type: Boolean, value: true },
    // Form state
    _showForm: { type: Boolean, value: false },
    _editingTrip: { type: Object, value: null },
    _formType: { type: String, value: 'recurrente' }
  };
}
```

#### Data Synchronization Patterns

**Pattern 1: Hass Polling**

```javascript
_startHassPolling() {
  const poll = () => {
    if (this._hass && this._vehicleId) {
      console.log('hass and vehicle_id available, rendering');
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
      console.log(`waiting for hass... attempt ${this._initAttempts}/${this._maxInitAttempts}`);
      this._pollTimeout = setTimeout(poll, 500);
    } else {
      console.error('Max init attempts reached, hass not available');
      this._pollStarted = false;
    }
  };

  this._pollTimeout = setTimeout(poll, 100);
}
```

**Pattern 2: State Subscription**

```javascript
_subscribeToStates() {
  if (!this._hass || !this._hass.connection) {
    return;
  }

  // Subscribe to all state changes
  this._unsubscribe = this._hass.connection.subscribeMessage(
    (message) => {
      if (message.type === 'event' && message.event?.event_type === 'state_changed') {
        const entityId = message.event.data?.entity_id;
        if (entityId && entityId.startsWith(`sensor.${this._vehicleId}`)) {
          console.log('State changed for', entityId);
          this._update();
        }
      }
    },
    { type: 'subscribe_events', event_type: 'state_changed' }
  );
}
```

**Pattern 3: Resource Cleanup**

```javascript
_cleanup() {
  if (this._unsubscribe) {
    this._unsubscribe();
    this._unsubscribe = null;
  }
}
```

#### URL Parameter Extraction

```javascript
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
      return;
    }
  }

  // Method 2: regex fallback
  const match = path.match(/\/ev-trip-planner-(.+)/);
  if (match && match[1]) {
    this._vehicleId = match[1];
  }

  // Method 3: from hash
  if (!this._vehicleId && window.location.hash) {
    const hashMatch = window.location.hash.match(/\/ev-trip-planner-(.+)/);
    if (hashMatch && hashMatch[1]) {
      this._vehicleId = hashMatch[1];
    }
  }
}
```

**Best Practices:**
- Multiple fallback methods for robustness
- Normalize paths before extraction
- Check both path and hash

## Key Recommendations

### 1. Form Handling Implementation

```javascript
async _handleTripCreate(e) {
  e.preventDefault();

  // Validate required fields first
  const form = e.target;
  const formData = new FormData(form);
  const km = formData.get('km');
  const kwh = formData.get('kwh');

  if (!km || parseFloat(km) <= 0) {
    this._showAlert('❌ La distancia (km) debe ser un número positivo', false);
    return;
  }

  if (!kwh || parseFloat(kwh) <= 0) {
    this._showAlert('❌ El consumo de energía (kWh) debe ser un número positivo', false);
    return;
  }

  // Build service data
  const serviceData = {
    vehicle_id: this._vehicleId,
    type: formData.get('type'),
  };

  // Type-specific fields
  if (type === 'puntual') {
    serviceData.datetime = formData.get('datetime');
  } else {
    serviceData.dia_semana = formData.get('day');
    serviceData.hora = formData.get('time');
  }

  // Common fields
  serviceData.km = parseFloat(km);
  serviceData.kwh = parseFloat(kwh);
  serviceData.description = formData.get('description') || '';

  // Loading state
  const submitBtn = form.querySelector('.btn-primary');
  const originalText = submitBtn.textContent;
  submitBtn.textContent = 'Creando...';
  submitBtn.disabled = true;

  try {
    await this._hass.callService('ev_trip_planner', 'trip_create', serviceData);
    this._closeForm();
    await this._loadTrips();
    this._showAlert('✅ Viaje creado exitosamente', true);
  } catch (error) {
    console.error('EV Trip Planner Panel: Error creating trip:', error);
    this._showAlert(`❌ Error: ${error.message}`, false);
  } finally {
    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
  }
}
```

### 2. Edit Mode Implementation

```javascript
async _handleTripUpdate(e) {
  e.preventDefault();

  const form = e.target;
  const formData = new FormData(form);

  const tripId = formData.get('edit-trip-id');
  if (!tripId) {
    this._showAlert('❌ Error: No se pudo identificar el viaje', false);
    return;
  }

  // Build service data
  const serviceData = {
    trip_id: tripId,
    vehicle_id: this._vehicleId,
    type: formData.get('type'),
  };

  // Type-specific fields
  if (type === 'puntual') {
    serviceData.datetime = formData.get('datetime');
  } else {
    serviceData.dia_semana = formData.get('day');
    serviceData.hora = formData.get('time');
  }

  serviceData.km = parseFloat(formData.get('km'));
  serviceData.kwh = parseFloat(formData.get('kwh'));
  serviceData.description = formData.get('description') || '';

  try {
    await this._hass.callService('ev_trip_planner', 'trip_update', serviceData);
    this._closeForm();
    await this._loadTrips();
    this._showAlert('✅ Viaje actualizado exitosamente', true);
  } catch (error) {
    console.error('Error updating trip:', error);
    this._showAlert(`❌ Error: ${error.message}`, false);
  } finally {
    submitBtn.textContent = originalText;
    submitBtn.disabled = false;
  }
}
```

### 3. Delete with Confirmation

```javascript
async _handleDeleteTrip(e) {
  const tripId = e.target.dataset.tripId;

  if (!confirm('¿Estás seguro de que quieres eliminar este viaje?')) {
    return;
  }

  try {
    await this._hass.callService('ev_trip_planner', 'delete_trip', {
      vehicle_id: this._vehicleId,
      trip_id: tripId,
    });

    await this._loadTrips();
    this._showAlert('✅ Viaje eliminado exitosamente', true);
  } catch (error) {
    console.error('Error deleting trip:', error);
    this._showAlert(`❌ Error: ${error.message}`, false);
  }
}
```

## Feasibility: High | Risk: Low | Effort: M

### Feasibility Justification

- **Well-established patterns:** All patterns found in existing codebase
- **Service layer exists:** Backend services already implemented
- **Frontend framework:** Lit web components fully supported
- **Error handling:** Standard try/catch/finally pattern works reliably

### Risk Assessment

**Low Risk Factors:**
- Patterns are already proven in current codebase
- No new dependencies required
- HA service framework is stable
- Error handling is straightforward

**Potential Risks:**
- Service call failures (handled with try/catch)
- Form validation edge cases (handled with explicit validation)
- URL parameter extraction (handled with multiple fallbacks)

### Effort Estimation

**Small (S):** Core implementation
- Form handling: 2-3 hours
- Service calls: 1-2 hours
- Error handling: 1 hour

**Medium (M):** Complete with tests
- Unit tests: 2-3 hours
- Documentation: 1-2 hours

**Total:** M (Medium) - 10-15 hours for complete implementation

## Related Specs

| Spec Name | Relationship | Reason |
|-----------|--------------|--------|
| trip-creation | Primary | This spec |
| trip-management | Extension | Edit/delete functionality |
| ev-trip-planner-panel | Integration | Panel implementation |

## Files Reference

| File | Purpose |
|------|---------|
| `custom_components/ev_trip_planner/frontend/panel.js` | Lit web component with form handling |
| `custom_components/ev_trip_planner/dashboard/dashboard.js` | Service wrapper functions |
| `custom_components/ev_trip_planner/dashboard/dashboard-create.yaml` | Create trip dashboard template |
| `custom_components/ev_trip_planner/dashboard/dashboard-edit.yaml` | Edit trip dashboard template |
| `custom_components/ev_trip_planner/dashboard/dashboard-list.yaml` | List trips dashboard template |
