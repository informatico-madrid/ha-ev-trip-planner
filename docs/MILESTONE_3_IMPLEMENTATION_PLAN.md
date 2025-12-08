# 🚀 Milestone 3: Implementation Plan - Step by Step

**Document Version**: 1.0  
**Date**: 2025-12-08  
**Status**: Ready for Implementation  
**Target**: v0.3.0-dev

---

## 📋 Executive Summary

This document provides a **detailed, step-by-step implementation plan** for Milestone 3: EMHASS Integration & Smart Charging Control. The plan is divided into **5 phases (3A-3E)**, each with **clear entry/exit criteria**, **deployment checkpoints**, and **rollback strategies**.

**Key Principle**: **Deploy incrementally, validate at each phase, and only proceed when confident.** This minimizes risk to your production Home Assistant environment.

---

## 🎯 Phase 3A: Configuration & Planning Setup

**Duration**: 1 week  
**Risk Level**: 🟢 LOW  
**Goal**: Extend configuration system to support EMHASS integration parameters

### Step 3A.1: Add Configuration Constants

**Action**: Extend `const.py` with new configuration keys

**Files to Modify**:
- `custom_components/ev_trip_planner/const.py`

**Add these constants**:
```python
# EMHASS Integration
CONF_MAX_DEFERRABLE_LOADS = "max_deferrable_loads"
CONF_PLANNING_HORIZON = "planning_horizon_days"
CONF_PLANNING_SENSOR = "planning_sensor_entity"

# Presence Detection
CONF_HOME_SENSOR = "home_sensor"
CONF_PLUGGED_SENSOR = "plugged_sensor"
CONF_HOME_COORDINATES = "home_coordinates"
CONF_VEHICLE_COORDINATES_SENSOR = "vehicle_coordinates_sensor"

# Notifications
CONF_NOTIFICATION_SERVICE = "notification_service"
CONF_NOTIFICATION_DEVICES = "notification_devices"

# Defaults
DEFAULT_PLANNING_HORIZON = 7
DEFAULT_MAX_DEFERRABLE_LOADS = 50
DEFAULT_NOTIFICATION_SERVICE = "persistent_notification.create"
```

**CRITICAL CHANGE**: Removed `CONF_EMHASS_INDEX` (was per-vehicle, now dynamic per-trip)

**Validation**:
- [ ] Constants added without errors
- [ ] No existing constants modified (backward compatibility)
- [ ] Run `pytest tests/test_const.py` (create if doesn't exist)

**Deployment Checkpoint**: ✅ PASS → Continue to 3A.2
**Rollback**: Simply revert `const.py` changes

---

### Step 3A.2: Extend Config Flow - Step 4 (EMHASS Configuration)

**Action**: Add new config flow step for EMHASS setup

**Files to Modify**:
- `custom_components/ev_trip_planner/config_flow.py`

**Implementation Details**:

1. **Add new step method**:
```python
async def async_step_emhass(self, user_input=None):
    """Configure EMHASS integration parameters."""
    errors = {}
    
    if user_input is not None:
        # Store and continue to next step
        self.context["vehicle_data"].update(user_input)
        return await self.async_step_presence()
    
    schema = vol.Schema({
        vol.Optional(CONF_PLANNING_HORIZON, default=DEFAULT_PLANNING_HORIZON):
            vol.All(vol.Coerce(int), vol.Range(min=1, max=30)),
        vol.Optional(CONF_PLANNING_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_MAX_DEFERRABLE_LOADS, default=DEFAULT_MAX_DEFERRABLE_LOADS):
            vol.All(vol.Coerce(int), vol.Range(min=10, max=100)),
    })
    
    return self.async_show_form(
        step_id="emhass",
        data_schema=schema,
        errors=errors,
        description_placeholders={
            "horizon_help": "Days to plan ahead (must be ≤ EMHASS planning horizon)",
            "max_loads_help": "Maximum number of simultaneous trips (affects EMHASS config)",
            "config_snippet": """
# Add to your EMHASS configuration.yaml:
# (Create as many entries as your max_deferrable_loads setting)
emhass:
  deferrable_loads:
    - def_total_hours: "{{ state_attr('sensor.emhass_deferrable_load_config_0', 'def_total_hours') | default(0) }}"
      P_deferrable_nom: "{{ state_attr('sensor.emhass_deferrable_load_config_0', 'P_deferrable_nom') | default(0) }}"
      # ... repeat for indices 1-49 as needed
            """,
        }
    )
```

**CRITICAL CHANGE**: Removed `CONF_EMHASS_INDEX` validation (no longer needed per-vehicle)

**User Experience**:
- Form shows current vehicle name
- Explains dynamic index assignment (one index per trip, not per vehicle)
- Shows configuration snippet to copy into EMHASS config
- Asks for maximum number of deferrable loads (affects how many EMHASS config entries needed)

**Validation**:
- [ ] Config flow step appears after "consumption" step
- [ ] Form validates planning horizon (1-30 days)
- [ ] Form validates max deferrable loads (10-100)
- [ ] Configuration snippet is displayed correctly
- [ ] Data is stored in config entry
- [ ] Run `pytest tests/test_config_flow.py -k "test_step_emhass"`

**Deployment Checkpoint**: ✅ PASS → Continue to 3A.3
**Rollback**: Revert config_flow.py changes, delete new config entries

---

### Step 3A.3: Extend Config Flow - Step 5 (Presence Detection)

**Action**: Add optional presence detection configuration

**Files to Modify**:
- `custom_components/ev_trip_planner/config_flow.py`

**Implementation Details**:

```python
async def async_step_presence(self, user_input=None):
    """Configure presence detection (optional)."""
    if user_input is not None:
        self.context["vehicle_data"].update(user_input)
        # Create config entry
        return self.async_create_entry(
            title=self.context["vehicle_data"][CONF_VEHICLE_NAME],
            data=self.context["vehicle_data"]
        )
    
    schema = vol.Schema({
        vol.Optional(CONF_HOME_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="binary_sensor")
        ),
        vol.Optional(CONF_PLUGGED_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="binary_sensor")
        ),
        vol.Optional(CONF_HOME_COORDINATES): str,
        vol.Optional(CONF_VEHICLE_COORDINATES_SENSOR): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="sensor")
        ),
        vol.Optional(CONF_NOTIFICATION_SERVICE,
                    default=DEFAULT_NOTIFICATION_SERVICE): str,
    })
    
    return self.async_show_form(
        step_id="presence",
        data_schema=schema,
        description_placeholders={
            "presence_help": "Optional: Configure to prevent charging when vehicle not home/plugged",
            "sensor_help": "Select binary_sensors that indicate home/plugged status",
            "coordinates_help": "Or use coordinates: provide home coordinates and vehicle location sensor",
        }
    )
```

**User Experience**:
- Optional step (can skip)
- Explains benefits: safety, notifications, efficiency
- Shows examples of typical sensors
- Allows configuration of notification service
- NEW: Supports coordinate-based detection as alternative to sensors

**Validation**:
- [ ] Step appears after EMHASS step
- [ ] Can be skipped (creates entry without presence config)
- [ ] Entity selectors filter for binary_sensor domain
- [ ] Coordinate fields optional but validated if provided
- [ ] Data is stored correctly in config entry
- [ ] Run `pytest tests/test_config_flow.py -k "test_step_presence"`

**Deployment Checkpoint**: ✅ PASS → Continue to 3A.4
**Rollback**: Revert config_flow.py changes

---

### Step 3A.4: Add Status Sensors

**Action**: Create new sensors to monitor EMHASS integration status

**Files to Modify**:
- `custom_components/ev_trip_planner/sensor.py`

**Add three new sensor classes**:

1. **EMHASS Active Trips Count Sensor**:
```python
class EMHASSActiveTripsSensor(_BaseTripSensor):
    """Sensor to monitor number of active trips with EMHASS indices."""
    
    def __init__(self, vehicle_id, coordinator, trip_manager):
        super().__init__(vehicle_id, coordinator)
        self._trip_manager = trip_manager
        self._attr_name = f"{vehicle_id} active trips"
        self._attr_unique_id = f"{vehicle_id}_active_trips"
        self._attr_icon = "mdi:car-electric"
    
    @property
    def native_value(self):
        """Return number of active trips."""
        recurring = self._trip_manager.async_get_recurring_trips()
        punctual = self._trip_manager.async_get_punctual_trips()
        active_punctual = [t for t in punctual if t.get("estado") == "pending"]
        return len(recurring) + len(active_punctual)
    
    @property
    def extra_state_attributes(self):
        """Return trip details."""
        recurring = self._trip_manager.async_get_recurring_trips()
        punctual = self._trip_manager.async_get_punctual_trips()
        active_punctual = [t for t in punctual if t.get("estado") == "pending"]
        
        all_trips = recurring + active_punctual
        
        return {
            "trip_count": len(all_trips),
            "total_kwh": sum(float(t.get("kwh", 0)) for t in all_trips),
            "trips": [{"id": t["id"], "desc": t.get("descripcion", "")} for t in all_trips]
        }
```

2. **Presence Status Sensor**:
```python
class PresenceStatusSensor(_BaseTripSensor):
    """Sensor to monitor vehicle presence status."""
    
    def __init__(self, vehicle_id, coordinator, home_sensor, plugged_sensor):
        super().__init__(vehicle_id, coordinator)
        self._home_sensor = home_sensor
        self._plugged_sensor = plugged_sensor
        self._attr_name = f"{vehicle_id} presence status"
        self._attr_unique_id = f"{vehicle_id}_presence_status"
        self._attr_icon = "mdi:home-map-marker"
    
    @property
    def native_value(self):
        """Return presence status: At Home, Away, or Unknown."""
        if not self._home_sensor:
            return "Unknown"
        
        state = self.hass.states.get(self._home_sensor)
        if state is None:
            return "Unknown"
        
        return "At Home" if state.state == "on" else "Away"
    
    @property
    def extra_state_attributes(self):
        """Return presence details."""
        attrs = {}
        if self._home_sensor:
            attrs["home_sensor"] = self._home_sensor
        if self._plugged_sensor:
            attrs["plugged_sensor"] = self._plugged_sensor
            plugged_state = self.hass.states.get(self._plugged_sensor)
            attrs["is_plugged"] = plugged_state.state if plugged_state else "unknown"
        
        return attrs
```

3. **Charging Readiness Sensor**:
```python
class ChargingReadinessSensor(_BaseTripSensor):
    """Sensor to indicate if vehicle is ready for scheduled charging."""
    
    def __init__(self, vehicle_id, coordinator, home_sensor, plugged_sensor):
        super().__init__(vehicle_id, coordinator)
        self._home_sensor = home_sensor
        self._plugged_sensor = plugged_sensor
        self._attr_name = f"{vehicle_id} charging readiness"
        self._attr_unique_id = f"{vehicle_id}_charging_readiness"
        self._attr_icon = "mdi:battery-charging"
    
    @property
    def native_value(self):
        """Return readiness status: Ready, Not Home, Not Plugged, or Unknown."""
        if not self._home_sensor:
            return "Unknown"
        
        home_state = self.hass.states.get(self._home_sensor)
        if not home_state or home_state.state != "on":
            return "Not Home"
        
        if self._plugged_sensor:
            plugged_state = self.hass.states.get(self._plugged_sensor)
            if not plugged_state or plugged_state.state != "on":
                return "Not Plugged"
        
        return "Ready"
```

**Update `async_setup_entry`** to create these sensors:
```python
# In async_setup_entry function
home_sensor = entry.data.get(CONF_HOME_SENSOR)
plugged_sensor = entry.data.get(CONF_PLUGGED_SENSOR)

# Add new sensors
sensors.extend([
    EMHASSActiveTripsSensor(vehicle_id, coordinator, trip_manager),
    PresenceStatusSensor(vehicle_id, coordinator, home_sensor, plugged_sensor),
    ChargingReadinessSensor(vehicle_id, coordinator, home_sensor, plugged_sensor),
])
```

**CRITICAL CHANGE**:
- Removed `EMHASSConfigStatusSensor` (no longer needed per-vehicle index)
- Added `EMHASSActiveTripsSensor` (shows dynamic trip count)
- Sensors now work with dynamic index assignment

**Validation**:
- [ ] Three new sensors appear in HA after config
- [ ] Active trips sensor shows correct count
- [ ] Presence status reflects actual sensor states
- [ ] Charging readiness shows "Ready" only when both conditions met
- [ ] Run `pytest tests/test_sensors.py -k "test_emhass_active_trips"`

**Deployment Checkpoint**: ✅ PASS → Continue to 3A.5
**Rollback**: Revert sensor.py changes, delete new sensors

---

### Step 3A.5: Create Unit Tests

**Action**: Add comprehensive tests for new functionality

**Files to Create**:
- `tests/test_config_flow_milestone3.py`
- `tests/test_sensors_milestone3.py`

**Test Cases for Config Flow**:
```python
# tests/test_config_flow_milestone3.py

async def test_step_emhass_valid_config(hass):
    """Test EMHASS step with valid configuration."""
    # Setup
    # Execute: Submit planning horizon and max deferrable loads
    # Verify: Flow continues to presence step
    # Verify: Data stored correctly

async def test_step_emhass_invalid_horizon(hass):
    """Test EMHASS step rejects invalid planning horizon."""
    # Execute: Submit horizon > 30 days
    # Verify: Error shown

async def test_step_presence_optional(hass):
    """Test presence step can be skipped."""
    # Setup
    # Execute: Skip presence step
    # Verify: Entry created without presence sensors

async def test_step_presence_with_sensors(hass):
    """Test presence step with sensor selection."""
    # Setup: Create mock binary_sensors
    # Execute: Select sensors
    # Verify: Sensors stored in config entry

async def test_step_presence_with_coordinates(hass):
    """Test presence step with coordinate configuration."""
    # Execute: Provide home coordinates and vehicle sensor
    # Verify: Coordinate data stored correctly
```

**Test Cases for Sensors**:
```python
# tests/test_sensors_milestone3.py

async def test_active_trips_sensor(hass):
    """Test active trips sensor shows correct count."""
    # Create test trips
    # Verify sensor state matches trip count
    # Verify attributes contain trip details

async def test_active_trips_sensor_zero(hass):
    """Test active trips sensor with no trips."""
    # No trips created
    # Verify sensor state is 0

async def test_presence_status_at_home(hass):
    """Test presence status when vehicle at home."""
    # Create binary_sensor.test with state "on"
    # Verify sensor state is "At Home"

async def test_presence_status_away(hass):
    """Test presence status when vehicle away."""
    # Create binary_sensor.test with state "off"
    # Verify sensor state is "Away"

async def test_charging_readiness_ready(hass):
    """Test charging readiness when at home and plugged."""
    # Both sensors "on"
    # Verify state is "Ready"

async def test_charging_readiness_not_home(hass):
    """Test charging readiness when not home."""
    # Home sensor "off"
    # Verify state is "Not Home"
```

**CRITICAL CHANGE**:
- Removed tests for `EMHASSConfigStatusSensor` (no longer exists)
- Added tests for `EMHASSActiveTripsSensor`
- Added tests for coordinate-based presence detection

**Validation**:
- [ ] All tests pass: `pytest tests/test_config_flow_milestone3.py -v`
- [ ] All tests pass: `pytest tests/test_sensors_milestone3.py -v`
- [ ] Coverage remains >80%

**Deployment Checkpoint**: ✅ PASS → **PHASE 3A COMPLETE**
**Rollback**: Revert all changes from 3A.1-3A.5

---

## 🎯 Phase 3B: EMHASS Adapter & Deferrable Loads

**Duration**: 1 week  
**Risk Level**: 🟡 MEDIUM  
**Goal**: Create adapter to publish trips as EMHASS-compatible deferrable loads

### Step 3B.1: Create EMHASSAdapter Class

**Action**: Create new module for EMHASS integration

**Files to Create**:
- `custom_components/ev_trip_planner/emhass_adapter.py`

**Implementation**:
```python
"""EMHASS Adapter for EV Trip Planner."""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import (
    CONF_MAX_DEFERRABLE_LOADS,
    CONF_CHARGING_POWER,
    CONF_VEHICLE_NAME,
)

_LOGGER = logging.getLogger(__name__)


class EMHASSAdapter:
    """Adapter to publish trips as EMHASS deferrable loads."""
    
    def __init__(self, hass: HomeAssistant, vehicle_config: Dict[str, Any]):
        """Initialize adapter."""
        self.hass = hass
        self.vehicle_id = vehicle_config[CONF_VEHICLE_NAME]
        self.max_deferrable_loads = vehicle_config.get(CONF_MAX_DEFERRABLE_LOADS, 50)
        self.charging_power = vehicle_config.get(CONF_CHARGING_POWER, 7.4)
        
        # Storage for trip_id → emhass_index mapping
        self._store = Store(hass, version=1, key=f"ev_trip_planner_{self.vehicle_id}_emhass_indices")
        self._index_map: Dict[str, int] = {}  # trip_id → emhass_index
        self._available_indices: List[int] = list(range(self.max_deferrable_loads))
        
        _LOGGER.debug(
            "Created EMHASSAdapter for %s with %d available indices",
            self.vehicle_id,
            len(self._available_indices)
        )
    
    async def async_load(self):
        """Load index mapping from storage."""
        data = await self._store.async_load()
        if data:
            self._index_map = data.get("index_map", {})
            # Rebuild available indices
            used_indices = set(self._index_map.values())
            self._available_indices = [i for i in range(self.max_deferrable_loads) if i not in used_indices]
            _LOGGER.info(
                "Loaded %d trip-index mappings for %s, %d indices still available",
                len(self._index_map),
                self.vehicle_id,
                len(self._available_indices)
            )
    
    async def async_save(self):
        """Save index mapping to storage."""
        await self._store.async_save({
            "index_map": self._index_map,
            "vehicle_id": self.vehicle_id,
        })
    
    async def async_assign_index_to_trip(self, trip_id: str) -> Optional[int]:
        """
        Assign an available EMHASS index to a trip.
        
        Returns:
            Assigned index or None if no indices available
        """
        if trip_id in self._index_map:
            # Trip already has an index, reuse it
            return self._index_map[trip_id]
        
        if not self._available_indices:
            _LOGGER.error(
                "No available EMHASS indices for vehicle %s. "
                "Max deferrable loads: %d, currently used: %d",
                self.vehicle_id,
                self.max_deferrable_loads,
                len(self._index_map)
            )
            return None
        
        # Assign the smallest available index
        assigned_index = min(self._available_indices)
        self._available_indices.remove(assigned_index)
        self._index_map[trip_id] = assigned_index
        
        await self.async_save()
        
        _LOGGER.info(
            "Assigned EMHASS index %d to trip %s for vehicle %s. "
            "%d indices remaining available",
            assigned_index,
            trip_id,
            self.vehicle_id,
            len(self._available_indices)
        )
        
        return assigned_index
    
    async def async_release_trip_index(self, trip_id: str) -> bool:
        """
        Release an EMHASS index when trip is deleted/completed.
        
        Returns:
            True if index was released, False if trip not found
        """
        if trip_id not in self._index_map:
            _LOGGER.warning(
                "Attempted to release index for unknown trip %s",
                trip_id
            )
            return False
        
        released_index = self._index_map.pop(trip_id)
        self._available_indices.append(released_index)
        self._available_indices.sort()
        
        await self.async_save()
        
        _LOGGER.info(
            "Released EMHASS index %d from trip %s for vehicle %s. "
            "Index now available for reuse",
            released_index,
            trip_id,
            self.vehicle_id
        )
        
        return True
    
    def _get_config_sensor_id(self, emhass_index: int) -> str:
        """Get entity ID for EMHASS config sensor."""
        return f"sensor.emhass_deferrable_load_config_{emhass_index}"
    
    async def async_publish_deferrable_load(self, trip: Dict[str, Any]) -> bool:
        """
        Publish a trip as deferrable load configuration.
        
        Args:
            trip: Trip dictionary with kwh, deadline, etc.
            
        Returns:
            True if successful, False otherwise
        """
        try:
            trip_id = trip.get("id")
            if not trip_id:
                _LOGGER.error("Trip missing ID")
                return False
            
            # Assign index to trip
            emhass_index = await self.async_assign_index_to_trip(trip_id)
            if emhass_index is None:
                return False
            
            # Calculate parameters
            kwh = float(trip.get("kwh", 0))
            deadline = trip.get("datetime")
            
            if not deadline:
                _LOGGER.error("Trip missing deadline: %s", trip_id)
                await self.async_release_trip_index(trip_id)
                return False
            
            # Calculate hours available
            now = datetime.now()
            if isinstance(deadline, str):
                deadline_dt = datetime.fromisoformat(deadline)
            else:
                deadline_dt = deadline
            
            hours_available = (deadline_dt - now).total_seconds() / 3600
            
            if hours_available <= 0:
                _LOGGER.warning("Trip deadline in past: %s", trip_id)
                await self.async_release_trip_index(trip_id)
                return False
            
            # Calculate EMHASS parameters
            total_hours = kwh / self.charging_power
            power_watts = self.charging_power * 1000  # Convert to Watts
            end_timestep = min(int(hours_available), 168)  # Max 7 days
            
            # Create attributes
            attributes = {
                "def_total_hours": round(total_hours, 2),
                "P_deferrable_nom": round(power_watts, 0),
                "def_start_timestep": 0,
                "def_end_timestep": end_timestep,
                "trip_id": trip_id,
                "vehicle_id": self.vehicle_id,
                "trip_description": trip.get("descripcion", ""),
                "status": "pending",
                "kwh_needed": kwh,
                "deadline": deadline_dt.isoformat(),
                "emhass_index": emhass_index,
            }
            
            # Set state
            config_sensor_id = self._get_config_sensor_id(emhass_index)
            self.hass.states.async_set(
                entity_id=config_sensor_id,
                state="active",
                attributes=attributes
            )
            
            _LOGGER.info(
                "Published deferrable load for trip %s (index %d): %s hours, %s W",
                trip_id,
                emhass_index,
                round(total_hours, 2),
                round(power_watts, 0)
            )
            
            return True
            
        except Exception as err:
            _LOGGER.error("Error publishing deferrable load: %s", err)
            # Release index on error
            if 'trip_id' in locals() and trip_id in self._index_map:
                await self.async_release_trip_index(trip_id)
            return False
    
    async def async_remove_deferrable_load(self, trip_id: str) -> bool:
        """Remove a trip from deferrable load configuration."""
        try:
            if trip_id not in self._index_map:
                _LOGGER.warning(
                    "Attempted to remove unknown trip %s",
                    trip_id
                )
                return False
            
            emhass_index = self._index_map[trip_id]
            config_sensor_id = self._get_config_sensor_id(emhass_index)
            
            # Clear the configuration
            self.hass.states.async_set(
                entity_id=config_sensor_id,
                state="idle",
                attributes={}
            )
            
            # Release the index
            await self.async_release_trip_index(trip_id)
            
            _LOGGER.info(
                "Removed deferrable load for trip %s (index %d)",
                trip_id,
                emhass_index
            )
            
            return True
            
        except Exception as err:
            _LOGGER.error("Error removing deferrable load: %s", err)
            return False
    
    async def async_update_deferrable_load(self, trip: Dict[str, Any]) -> bool:
        """Update existing deferrable load with new parameters."""
        return await self.async_publish_deferrable_load(trip)
    
    async def async_publish_all_deferrable_loads(self, trips: List[Dict[str, Any]]) -> bool:
        """
        Publish multiple trips, each with its own index.
        
        Returns:
            True if all trips published successfully, False otherwise
        """
        success_count = 0
        
        for trip in trips:
            if await self.async_publish_deferrable_load(trip):
                success_count += 1
        
        _LOGGER.info(
            "Published %d/%d deferrable loads for vehicle %s",
            success_count,
            len(trips),
            self.vehicle_id
        )
        
        return success_count == len(trips)
    
    def get_assigned_index(self, trip_id: str) -> Optional[int]:
        """Get the EMHASS index assigned to a trip."""
        return self._index_map.get(trip_id)
    
    def get_all_assigned_indices(self) -> Dict[str, int]:
        """Get all trip-index mappings."""
        return self._index_map.copy()
```

**CRITICAL CHANGES**:
- **Removed**: `CONF_EMHASS_INDEX` from constructor (no longer per-vehicle)
- **Added**: Dynamic index assignment with `async_assign_index_to_trip()`
- **Added**: Index persistence using Home Assistant `Store`
- **Added**: Index pool management (`_available_indices`)
- **Added**: Methods to release and reuse indices
- **Added**: Support for multiple trips per vehicle (each gets unique index)
- **Modified**: `async_publish_deferrable_load()` now assigns index per trip
- **Added**: `async_publish_all_deferrable_loads()` for batch operations
- **Added**: Helper methods to query index assignments

**Validation**:
- [ ] Module imports without errors
- [ ] Class can be instantiated with mock config
- [ ] Index assignment works correctly
- [ ] Index persistence works across restarts
- [ ] Run `pytest tests/test_emhass_adapter.py -k "test_dynamic_index_assignment"`

**Deployment Checkpoint**: ✅ PASS → Continue to 3B.2
**Rollback**: Delete `emhass_adapter.py`

**Validation**:
- [ ] Module imports without errors
- [ ] Class can be instantiated with mock config
- [ ] Run `pytest tests/test_emhass_adapter.py -k "test_class_instantiation"`

**Deployment Checkpoint**: ✅ PASS → Continue to 3B.2  
**Rollback**: Delete `emhass_adapter.py`

---

### Step 3B.2: Integrate with TripManager

**Action**: Connect adapter to trip lifecycle events

**Files to Modify**:
- `custom_components/ev_trip_planner/__init__.py`
- `custom_components/ev_trip_planner/trip_manager.py`

**In `__init__.py`**, create adapter instance:
```python
# In async_setup_entry
from .emhass_adapter import EMHASSAdapter

# After creating trip_manager
emhass_adapter = EMHASSAdapter(hass, entry.data)
await emhass_adapter.async_load()  # Load existing index mappings
hass.data[DOMAIN][entry.entry_id]["emhass_adapter"] = emhass_adapter
```

**In `trip_manager.py`**, add dispatcher signal after trip changes:
```python
# After _async_save_trips in each method
async_dispatcher_send(
    self.hass,
    f"{SIGNAL_TRIPS_UPDATED}_{self.vehicle_id}",
    {"action": "added", "trip_id": trip_id}  # or "updated", "deleted"
)
```

**Create coordinator listener** in `__init__.py`:
```python
# In async_setup_entry
def handle_trip_update(event):
    """Handle trip update events."""
    action = event.get("action")
    trip_id = event.get("trip_id")
    
    if action == "added":
        # Get trip and publish
        async def publish():
            trip = await trip_manager.async_get_trip(trip_id)
            if trip:
                await emhass_adapter.async_publish_deferrable_load(trip)
        hass.async_create_task(publish())
    
    elif action == "deleted":
        # Remove deferrable load and release index
        async def remove():
            await emhass_adapter.async_remove_deferrable_load(trip_id)
        hass.async_create_task(remove())
    
    elif action == "updated":
        # Update existing deferrable load
        async def update():
            trip = await trip_manager.async_get_trip(trip_id)
            if trip:
                await emhass_adapter.async_update_deferrable_load(trip)
        hass.async_create_task(update())

# Listen for signals
hass.data[DOMAIN][entry.entry_id]["unsub_signal"] = async_dispatcher_connect(
    hass,
    f"{SIGNAL_TRIPS_UPDATED}_{vehicle_id}",
    handle_trip_update
)
```

**CRITICAL CHANGES**:
- Added `await emhass_adapter.async_load()` to restore index mappings on startup
- Added handler for "deleted" action to release indices
- Added handler for "updated" action to update existing loads
- Ensures indices are properly managed throughout trip lifecycle

**Validation**:
- [ ] Adapter instance created on setup
- [ ] Index mappings loaded on startup
- [ ] Signal sent after adding trip
- [ ] Signal sent after updating trip
- [ ] Signal sent after deleting trip
- [ ] Indices released when trips deleted
- [ ] Run `pytest tests/test_integration.py -k "test_trip_change_triggers_adapter"`

**Deployment Checkpoint**: ✅ PASS → Continue to 3B.3
**Rollback**: Revert `__init__.py` and `trip_manager.py` changes

---

### Step 3B.3: Handle Multiple Trips Per Vehicle

**Action**: Support multiple trips by assigning each trip its own EMHASS index

**Files to Modify**:
- `custom_components/ev_trip_planner/emhass_adapter.py` (no changes needed, already supports multiple trips)
- `custom_components/ev_trip_planner/__init__.py` (update listener)

**Update coordinator listener** to publish all trips individually:
```python
# In handle_trip_update
async def publish_all_trips():
    """Publish all active trips, each with its own EMHASS index."""
    # Get all active trips
    recurring = await trip_manager.async_get_recurring_trips()
    punctual = await trip_manager.async_get_punctual_trips()
    active_punctual = [t for t in punctual if t.get("estado") == "pending"]
    
    all_trips = recurring + active_punctual
    
    # Publish all trips (each gets its own index)
    await emhass_adapter.async_publish_all_deferrable_loads(all_trips)

hass.async_create_task(publish_all_trips())
```

**CRITICAL CHANGES**:
- **ELIMINADO**: Lógica de combinación de viajes (suma de kWh, deadline más temprano)
- **RAZÓN**: Con asignación dinámica de índices, cada viaje obtiene su propio índice EMHASS
- **VENTAJA**: EMHASS puede optimizar cada viaje individualmente para máxima eficiencia
- **NUEVO ENFOQUE**: Usar `async_publish_all_deferrable_loads()` que itera y publica cada viaje con índice único

**Flujo de Datos**:
```
Trip Manager → EMHASSAdapter →
  - Trip 1 (lunes trabajo) → Índice 0 → sensor.emhass_deferrable_load_config_0
  - Trip 2 (miércoles compras) → Índice 1 → sensor.emhass_deferrable_load_config_1
  - Trip 3 (viernes cine) → Índice 2 → sensor.emhass_deferrable_load_config_2
  ↓
EMHASS → Genera schedule para cada índice →
  - sensor.emhass_deferrable0_schedule
  - sensor.emhass_deferrable1_schedule
  - sensor.emhass_deferrable2_schedule
```

**Validation**:
- [ ] Each trip gets its own EMHASS index
- [ ] Multiple config sensors created (one per trip)
- [ ] EMHASS generates separate schedules for each index
- [ ] Run `pytest tests/test_emhass_adapter.py -k "test_multiple_trips_dynamic_indices"`

**Deployment Checkpoint**: ✅ PASS → Continue to 3B.4
**Rollback**: Revert listener changes

---

### Step 3B.4: Add Unit Tests for Adapter

**Action**: Create comprehensive tests for EMHASSAdapter

**Files to Create**:
- `tests/test_emhass_adapter.py`

**Test Cases**:
```python
# tests/test_emhass_adapter.py

async def test_adapter_instantiation(hass):
    """Test adapter can be created with valid config."""
    config = {
        CONF_VEHICLE_NAME: "test_vehicle",
        CONF_MAX_DEFERRABLE_LOADS: 50,
        CONF_CHARGING_POWER: 7.4,
    }
    adapter = EMHASSAdapter(hass, config)
    assert adapter.vehicle_id == "test_vehicle"
    assert adapter.max_deferrable_loads == 50
    assert len(adapter._available_indices) == 50  # All indices available initially

async def test_load_index_mappings(hass):
    """Test loading existing index mappings from storage."""
    # Setup: Pre-populate storage with existing mappings
    # Execute: Call async_load()
    # Verify: Index map restored, available indices calculated correctly

async def test_assign_index_to_trip(hass):
    """Test dynamic index assignment."""
    # Setup adapter
    await adapter.async_load()
    
    # Assign first index
    index1 = await adapter.async_assign_index_to_trip("trip_001")
    assert index1 == 0
    assert len(adapter._available_indices) == 49
    
    # Assign second index
    index2 = await adapter.async_assign_index_to_trip("trip_002")
    assert index2 == 1
    assert len(adapter._available_indices) == 48
    
    # Reassign same trip (should return same index)
    index1_again = await adapter.async_assign_index_to_trip("trip_001")
    assert index1_again == index1
    assert len(adapter._available_indices) == 48  # No change

async def test_assign_index_no_available(hass):
    """Test behavior when no indices available."""
    # Setup: Use up all indices
    for i in range(50):
        await adapter.async_assign_index_to_trip(f"trip_{i:03d}")
    
    # Try to assign one more
    index = await adapter.async_assign_index_to_trip("trip_051")
    assert index is None
    assert "No available EMHASS indices" in caplog.text

async def test_release_trip_index(hass):
    """Test releasing an index when trip deleted."""
    # Setup: Assign index to trip
    index = await adapter.async_assign_index_to_trip("trip_001")
    assert index == 0
    assert len(adapter._available_indices) == 49
    
    # Release index
    result = await adapter.async_release_trip_index("trip_001")
    assert result is True
    assert len(adapter._available_indices) == 50
    assert 0 in adapter._available_indices

async def test_publish_single_trip(hass):
    """Test publishing a single trip with dynamic index."""
    # Setup adapter
    await adapter.async_load()
    
    # Create test trip
    trip = {
        "id": "trip_001",
        "kwh": 3.6,
        "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
        "descripcion": "Work commute",
    }
    
    # Publish
    result = await adapter.async_publish_deferrable_load(trip)
    
    # Verify
    assert result is True
    index = adapter.get_assigned_index("trip_001")
    assert index is not None
    assert index >= 0
    
    # Verify sensor created
    sensor_id = f"sensor.emhass_deferrable_load_config_{index}"
    state = hass.states.get(sensor_id)
    assert state is not None
    assert state.state == "active"
    assert state.attributes["trip_id"] == "trip_001"
    assert state.attributes["kwh_needed"] == 3.6

async def test_publish_multiple_trips_dynamic_indices(hass):
    """Test publishing multiple trips, each gets unique index."""
    # Setup
    await adapter.async_load()
    
    # Create multiple trips
    trips = [
        {
            "id": f"trip_{i:03d}",
            "kwh": 3.0 + i,
            "datetime": (datetime.now() + timedelta(hours=8+i)).isoformat(),
            "descripcion": f"Trip {i}",
        }
        for i in range(5)
    ]
    
    # Publish all
    result = await adapter.async_publish_all_deferrable_loads(trips)
    assert result is True
    
    # Verify each trip has unique index
    assigned_indices = []
    for trip in trips:
        index = adapter.get_assigned_index(trip["id"])
        assert index is not None
        assert index not in assigned_indices  # Unique
        assigned_indices.append(index)
        
        # Verify sensor created
        sensor_id = f"sensor.emhass_deferrable_load_config_{index}"
        state = hass.states.get(sensor_id)
        assert state is not None

async def test_publish_trip_past_deadline(hass):
    """Test publishing trip with deadline in past."""
    # Create trip with deadline < now
    trip = {
        "id": "trip_old",
        "kwh": 3.6,
        "datetime": (datetime.now() - timedelta(hours=1)).isoformat(),
    }
    
    # Publish
    result = await adapter.async_publish_deferrable_load(trip)
    
    # Verify
    assert result is False
    assert "deadline in past" in caplog.text
    # Index should be released
    assert adapter.get_assigned_index("trip_old") is None

async def test_remove_deferrable_load(hass):
    """Test removing deferrable load and releasing index."""
    # Setup: Publish trip
    trip = {
        "id": "trip_001",
        "kwh": 3.6,
        "datetime": (datetime.now() + timedelta(hours=8)).isoformat(),
    }
    await adapter.async_publish_deferrable_load(trip)
    index = adapter.get_assigned_index("trip_001")
    assert index is not None
    
    # Remove
    result = await adapter.async_remove_deferrable_load("trip_001")
    assert result is True
    
    # Verify index released
    assert adapter.get_assigned_index("trip_001") is None
    assert index in adapter._available_indices
    
    # Verify sensor cleared
    sensor_id = f"sensor.emhass_deferrable_load_config_{index}"
    state = hass.states.get(sensor_id)
    assert state.state == "idle"
    assert state.attributes == {}

async def test_index_persistence(hass):
    """Test that index mappings persist across restarts."""
    # Setup: Assign some indices
    await adapter.async_assign_index_to_trip("trip_001")
    await adapter.async_assign_index_to_trip("trip_002")
    
    # Save
    await adapter.async_save()
    
    # Create new adapter instance (simulating restart)
    adapter2 = EMHASSAdapter(hass, config)
    await adapter2.async_load()
    
    # Verify mappings restored
    assert adapter2.get_assigned_index("trip_001") == 0
    assert adapter2.get_assigned_index("trip_002") == 1
    assert len(adapter2._available_indices) == 48  # 50 - 2 used
```

**CRITICAL CHANGES**:
- **Removed**: `CONF_EMHASS_INDEX` from test config (no longer per-vehicle)
- **Added**: Tests for `async_load()` and `async_save()` (persistence)
- **Added**: Tests for dynamic index assignment (`async_assign_index_to_trip`)
- **Added**: Tests for index release (`async_release_trip_index`)
- **Added**: Tests for multiple trips with unique indices
- **Added**: Test for index exhaustion scenario
- **Added**: Test for index persistence across restarts
- **Modified**: `test_publish_single_trip` to verify dynamic index assignment
- **Modified**: `test_publish_multiple_trips` to verify unique indices per trip

**Validation**:
- [ ] All tests pass
- [ ] Coverage >90% for adapter module
- [ ] Mock hass.states to avoid needing real HA
- [ ] Tests cover edge cases (no indices available, past deadlines)

**Deployment Checkpoint**: ✅ PASS → **PHASE 3B COMPLETE**
**Rollback**: Revert all 3B changes

---

## 🎯 Phase 3C: Vehicle Control Interface

**Duration**: 1 week  
**Risk Level**: 🟢 LOW  
**Goal**: Abstract vehicle control mechanisms (switch, service, script)

### Step 3C.1: Create Control Strategy Classes

**Action**: Create new module for vehicle control abstraction

**Files to Create**:
- `custom_components/ev_trip_planner/vehicle_controller.py`

**Implementation**:
```python
"""Vehicle Control Strategies for EV Trip Planner."""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class VehicleControlStrategy(ABC):
    """Abstract base class for vehicle control strategies."""
    
    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        """Initialize strategy."""
        self.hass = hass
        self.config = config
    
    @abstractmethod
    async def async_activate(self) -> bool:
        """Activate vehicle charging."""
        pass
    
    @abstractmethod
    async def async_deactivate(self) -> bool:
        """Deactivate vehicle charging."""
        pass
    
    @abstractmethod
    async def async_get_status(self) -> bool:
        """Get current charging status."""
        pass


class SwitchStrategy(VehicleControlStrategy):
    """Control via switch entity."""
    
    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        super().__init__(hass, config)
        self.switch_entity_id = config["entity_id"]
    
    async def async_activate(self) -> bool:
        """Turn on switch."""
        try:
            await self.hass.services.async_call(
                "switch", "turn_on", {"entity_id": self.switch_entity_id}
            )
            _LOGGER.info("Activated charging via switch: %s", self.switch_entity_id)
            return True
        except Exception as err:
            _LOGGER.error("Error activating switch: %s", err)
            return False
    
    async def async_deactivate(self) -> bool:
        """Turn off switch."""
        try:
            await self.hass.services.async_call(
                "switch", "turn_off", {"entity_id": self.switch_entity_id}
            )
            _LOGGER.info("Deactivated charging via switch: %s", self.switch_entity_id)
            return True
        except Exception as err:
            _LOGGER.error("Error deactivating switch: %s", err)
            return False
    
    async def async_get_status(self) -> bool:
        """Get switch state."""
        state = self.hass.states.get(self.switch_entity_id)
        return state and state.state == "on"


class ServiceStrategy(VehicleControlStrategy):
    """Control via custom service call."""
    
    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        super().__init__(hass, config)
        self.service_on = config["service_on"]
        self.service_off = config["service_off"]
        self.data_on = config.get("data_on", {})
        self.data_off = config.get("data_off", {})
    
    async def async_activate(self) -> bool:
        """Call service to start charging."""
        try:
            domain, service = self.service_on.split(".", 1)
            await self.hass.services.async_call(
                domain, service, self.data_on
            )
            _LOGGER.info("Activated charging via service: %s", self.service_on)
            return True
        except Exception as err:
            _LOGGER.error("Error calling service %s: %s", self.service_on, err)
            return False
    
    async def async_deactivate(self) -> bool:
        """Call service to stop charging."""
        try:
            domain, service = self.service_off.split(".", 1)
            await self.hass.services.async_call(
                domain, service, self.data_off
            )
            _LOGGER.info("Deactivated charging via service: %s", self.service_off)
            return True
        except Exception as err:
            _LOGGER.error("Error calling service %s: %s", self.service_off, err)
            return False
    
    async def async_get_status(self) -> bool:
        """Get status via service or sensor."""
        # This would need a sensor or additional config
        # For now, return unknown
        return False


class ScriptStrategy(VehicleControlStrategy):
    """Control via script execution."""
    
    def __init__(self, hass: HomeAssistant, config: Dict[str, Any]):
        super().__init__(hass, config)
        self.script_on = config["script_on"]
        self.script_off = config["script_off"]
    
    async def async_activate(self) -> bool:
        """Execute start charging script."""
        try:
            await self.hass.services.async_call(
                "script", self.script_on.replace("script.", "")
            )
            _LOGGER.info("Activated charging via script: %s", self.script_on)
            return True
        except Exception as err:
            _LOGGER.error("Error executing script %s: %s", self.script_on, err)
            return False
    
    async def async_deactivate(self) -> bool:
        """Execute stop charging script."""
        try:
            await self.hass.services.async_call(
                "script", self.script_off.replace("script.", "")
            )
            _LOGGER.info("Deactivated charging via script: %s", self.script_off)
            return True
        except Exception as err:
            _LOGGER.error("Error executing script %s: %s", self.script_off, err)
            return False
    
    async def async_get_status(self) -> bool:
        """Get status - scripts typically don't return status."""
        return False


class ExternalStrategy(VehicleControlStrategy):
    """No direct control - external system manages charging."""
    
    async def async_activate(self) -> bool:
        """No-op."""
        _LOGGER.info("External strategy: no action taken")
        return True
    
    async def async_deactivate(self) -> bool:
        """No-op."""
        _LOGGER.info("External strategy: no action taken")
        return True
    
    async def async_get_status(self) -> bool:
        """Unknown status."""
        return False


def create_control_strategy(hass: HomeAssistant, config: Dict[str, Any]) -> VehicleControlStrategy:
    """Factory function to create appropriate control strategy."""
    control_type = config.get("control_type", "none")
    
    if control_type == "switch":
        return SwitchStrategy(hass, {"entity_id": config["charge_control_entity"]})
    elif control_type == "service":
        return ServiceStrategy(hass, {
            "service_on": config["charge_service_on"],
            "service_off": config["charge_service_off"],
            "data_on": config.get("charge_service_data_on", {}),
            "data_off": config.get("charge_service_data_off", {}),
        })
    elif control_type == "script":
        return ScriptStrategy(hass, {
            "script_on": config["charge_script_on"],
            "script_off": config["charge_script_off"],
        })
    else:
        return ExternalStrategy(hass, {})
```

**Validation**:
- [ ] Module imports without errors
- [ ] Each strategy class can be instantiated
- [ ] Factory function returns correct strategy type
- [ ] Run `pytest tests/test_vehicle_controller.py -k "test_factory"`

**Deployment Checkpoint**: ✅ PASS → Continue to 3C.2  
**Rollback**: Delete `vehicle_controller.py`

---

### Step 3C.2: Integrate with Config Flow

**Action**: Add control configuration to config flow

**Files to Modify**:
- `custom_components/ev_trip_planner/config_flow.py`

**Add new step after presence step**:
```python
async def async_step_control(self, user_input=None):
    """Configure vehicle control mechanism."""
    errors = {}
    
    if user_input is not None:
        # Validate control entities/services exist
        if user_input["control_type"] == "switch":
            if not self.hass.states.get(user_input["charge_control_entity"]):
                errors["base"] = "switch_entity_not_found"
        
        elif user_input["control_type"] == "service":
            # Validate service format
            try:
                domain, service = user_input["charge_service_on"].split(".", 1)
                if not self.hass.services.has_service(domain, service):
                    errors["base"] = "service_not_found"
            except ValueError:
                errors["base"] = "invalid_service_format"
        
        if not errors:
            self.context["vehicle_data"].update(user_input)
            return await self.async_step_presence()
    
    schema = vol.Schema({
        vol.Required("control_type", default="none"): selector.SelectSelector(
            selector.SelectSelectorConfig(
                options=[
                    selector.SelectOptionDict(value="none", label="No direct control (notifications only)"),
                    selector.SelectOptionDict(value="switch", label="Switch entity"),
                    selector.SelectOptionDict(value="service", label="HA Service call"),
                    selector.SelectOptionDict(value="script", label="Script"),
                ],
                mode=selector.SelectSelectorMode.DROPDOWN,
            )
        ),
    })
    
    # Conditionally add fields based on selection
    control_type = self.context.get("control_type", "none")
    
    return self.async_show_form(
        step_id="control",
        data_schema=schema,
        errors=errors,
        description_placeholders={
            "control_help": "How should the module control charging?",
        }
    )
```

**Validation**:
- [ ] Control step appears in config flow
- [ ] Validates switch entity exists
- [ ] Validates service format and existence
- [ ] Stores configuration correctly
- [ ] Run `pytest tests/test_config_flow.py -k "test_step_control"`

**Deployment Checkpoint**: ✅ PASS → Continue to 3C.3  
**Rollback**: Revert config_flow.py changes

---

### Step 3C.3: Create Controller Instances

**Action**: Instantiate control strategies in setup

**Files to Modify**:
- `custom_components/ev_trip_planner/__init__.py`

**In `async_setup_entry`**:
```python
# Create control strategy
from .vehicle_controller import create_control_strategy

control_strategy = create_control_strategy(hass, entry.data)
hass.data[DOMAIN][entry.entry_id]["control_strategy"] = control_strategy

# Test control during setup (optional but recommended)
async def test_control():
    try:
        # Try to get status (non-invasive)
        status = await control_strategy.async_get_status()
        _LOGGER.info("Control strategy test successful, status: %s", status)
    except Exception as err:
        _LOGGER.warning("Control strategy test failed: %s", err)

hass.async_create_task(test_control())
```

**Validation**:
- [ ] Control strategy created without errors
- [ ] Strategy type matches config
- [ ] Test call executes without crashing
- [ ] Run `pytest tests/test_integration.py -k "test_control_strategy_setup"`

**Deployment Checkpoint**: ✅ PASS → **PHASE 3C COMPLETE**  
**Rollback**: Revert `__init__.py` changes

---

## 🎯 Phase 3D: Schedule Monitor & Presence Detection

**Duration**: 1 week  
**Risk Level**: 🔴 HIGH  
**Goal**: Monitor EMHASS schedules and execute control with safety checks

### Step 3D.1: Create ScheduleMonitor Class

**Action**: Create core monitoring component

**Files to Create**:
- `custom_components/ev_trip_planner/schedule_monitor.py`

**Implementation**:
```python
"""Schedule Monitor for EV Trip Planner."""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Set

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.event import async_track_state_change_event

from .const import CONF_VEHICLE_NAME

_LOGGER = logging.getLogger(__name__)


class ScheduleMonitor:
    """Monitors EMHASS schedules and executes vehicle control."""
    
    def __init__(self, hass: HomeAssistant):
        """Initialize monitor."""
        self.hass = hass
        self._vehicle_monitors: Dict[str, "VehicleScheduleMonitor"] = {}
        self._unsub_handlers: List[callable] = []
    
    async def async_setup(self, vehicle_configs: Dict[str, Dict[str, any]]):
        """Set up monitoring for all vehicles."""
        for entry_id, config in vehicle_configs.items():
            vehicle_id = config[CONF_VEHICLE_NAME]
            
            # Create vehicle monitor
            vehicle_monitor = VehicleScheduleMonitor(
                hass=self.hass,
                vehicle_id=vehicle_id,
                control_strategy=config["control_strategy"],
                presence_monitor=config.get("presence_monitor"),
                notification_service=config.get(CONF_NOTIFICATION_SERVICE),
                emhass_adapter=config.get("emhass_adapter"),  # NEW: Pass adapter
            )
            
            await vehicle_monitor.async_start()
            self._vehicle_monitors[vehicle_id] = vehicle_monitor
        
        _LOGGER.info("ScheduleMonitor setup complete for %d vehicles",
                    len(self._vehicle_monitors))
    
    async def async_stop(self):
        """Stop all monitoring."""
        for monitor in self._vehicle_monitors.values():
            await monitor.async_stop()
        
        self._vehicle_monitors.clear()
        _LOGGER.info("ScheduleMonitor stopped")


class VehicleScheduleMonitor:
    """Monitors schedules for a single vehicle."""
    
    def __init__(self, hass: HomeAssistant, vehicle_id: str,
                 control_strategy, presence_monitor, notification_service: str,
                 emhass_adapter):
        """Initialize vehicle monitor."""
        self.hass = hass
        self.vehicle_id = vehicle_id
        self.control_strategy = control_strategy
        self.presence_monitor = presence_monitor
        self.notification_service = notification_service
        self.emhass_adapter = emhass_adapter  # NEW: For index lookup
        
        self._unsub_handlers: Dict[int, callable] = {}  # index -> unsub function
        self._last_actions: Dict[int, str] = {}  # index -> last action
        
        _LOGGER.debug("Created VehicleScheduleMonitor for %s", vehicle_id)
    
    async def async_start(self):
        """Start monitoring all schedules for this vehicle."""
        if not self.emhass_adapter:
            _LOGGER.warning(
                "No EMHASS adapter for vehicle %s, cannot start monitoring",
                self.vehicle_id
            )
            return
        
        # Get all assigned indices for this vehicle
        assigned_indices = self.emhass_adapter.get_all_assigned_indices()
        
        if not assigned_indices:
            _LOGGER.info(
                "No active trips for vehicle %s, monitoring will start when trips added",
                self.vehicle_id
            )
            return
        
        # Subscribe to schedule for each index
        for trip_id, emhass_index in assigned_indices.items():
            await self._async_monitor_schedule(emhass_index)
        
        _LOGGER.info(
            "Started monitoring %d schedules for vehicle %s",
            len(assigned_indices),
            self.vehicle_id
        )
    
    async def async_stop(self):
        """Stop monitoring all schedules."""
        for unsub in self._unsub_handlers.values():
            if unsub:
                unsub()
        self._unsub_handlers.clear()
        self._last_actions.clear()
    
    async def _async_monitor_schedule(self, emhass_index: int):
        """Start monitoring a specific schedule."""
        schedule_entity_id = f"sensor.emhass_deferrable{emhass_index}_schedule"
        
        # Check if schedule entity exists
        if not self.hass.states.get(schedule_entity_id):
            _LOGGER.warning(
                "Schedule entity %s not found for vehicle %s. "
                "Ensure EMHASS is configured correctly.",
                schedule_entity_id,
                self.vehicle_id
            )
            return
        
        # Subscribe to state changes
        @callback
        def schedule_changed(event):
            """Handle schedule change."""
            self.hass.async_create_task(
                self._async_handle_schedule_change(emhass_index)
            )
        
        unsub = async_track_state_change_event(
            self.hass,
            [schedule_entity_id],
            schedule_changed
        )
        
        self._unsub_handlers[emhass_index] = unsub
        
        _LOGGER.debug(
            "Monitoring schedule for %s: %s",
            self.vehicle_id,
            schedule_entity_id
        )
        
        # Initial check
        await self._async_handle_schedule_change(emhass_index)
    
    async def _async_handle_schedule_change(self, emhass_index: int):
        """Process schedule change and execute control."""
        try:
            schedule_entity_id = f"sensor.emhass_deferrable{emhass_index}_schedule"
            
            # Get current schedule
            schedule_state = self.hass.states.get(schedule_entity_id)
            if not schedule_state:
                _LOGGER.warning("Schedule entity disappeared: %s", schedule_entity_id)
                return
            
            # Parse schedule
            should_charge = self._parse_schedule(schedule_state.state)
            
            if should_charge:
                await self._async_start_charging(emhass_index)
            else:
                await self._async_stop_charging(emhass_index)
                
        except Exception as err:
            _LOGGER.error("Error handling schedule change for index %d: %s", emhass_index, err)
    
    def _parse_schedule(self, schedule_state: str) -> bool:
        """
        Parse EMHASS schedule to determine if should charge now.
        
        Expected format: "02:00-03:00, 05:00-06:00" or JSON
        """
        if not schedule_state or schedule_state in ["unknown", "unavailable"]:
            return False
        
        # For now, simple check - expand based on actual EMHASS format
        # TODO: Implement proper schedule parsing
        return "on" in schedule_state.lower() or "true" in schedule_state.lower()
    
    async def _async_start_charging(self, emhass_index: int):
        """Start charging with safety checks."""
        if self._last_actions.get(emhass_index) == "start":
            # Already started, avoid duplicate
            return
        
        _LOGGER.info(
            "Schedule indicates charging should start for %s (index %d)",
            self.vehicle_id,
            emhass_index
        )
        
        # CRITICAL: Check presence first
        if self.presence_monitor:
            is_at_home = await self.presence_monitor.async_check_home_status()
            if not is_at_home:
                _LOGGER.info(
                    "Vehicle %s not at home, ignoring start charging request (index %d)",
                    self.vehicle_id,
                    emhass_index
                )
                await self._async_notify(
                    f"⚠️ Charging skipped: {self.vehicle_id} not at home",
                    f"Schedule requested charging but vehicle is not at home"
                )
                return
            
            is_plugged = await self.presence_monitor.async_check_plugged_status()
            if not is_plugged:
                _LOGGER.info(
                    "Vehicle %s not plugged, ignoring start charging request (index %d)",
                    self.vehicle_id,
                    emhass_index
                )
                await self._async_notify(
                    f"🔌 Connect vehicle: {self.vehicle_id}",
                    f"Schedule requested charging but vehicle is not plugged in"
                )
                return
        
        # Execute control
        success = await self.control_strategy.async_activate()
        
        if success:
            self._last_actions[emhass_index] = "start"
            _LOGGER.info(
                "Started charging for vehicle %s (index %d)",
                self.vehicle_id,
                emhass_index
            )
        else:
            _LOGGER.error(
                "Failed to start charging for vehicle %s (index %d)",
                self.vehicle_id,
                emhass_index
            )
            await self._async_notify(
                f"❌ Charging failed: {self.vehicle_id}",
                f"Failed to start charging. Check logs for errors."
            )
    
    async def _async_stop_charging(self, emhass_index: int):
        """Stop charging."""
        if self._last_actions.get(emhass_index) == "stop":
            # Already stopped
            return
        
        _LOGGER.info(
            "Schedule indicates charging should stop for %s (index %d)",
            self.vehicle_id,
            emhass_index
        )
        
        success = await self.control_strategy.async_deactivate()
        
        if success:
            self._last_actions[emhass_index] = "stop"
            _LOGGER.info(
                "Stopped charging for vehicle %s (index %d)",
                self.vehicle_id,
                emhass_index
            )
        else:
            _LOGGER.error(
                "Failed to stop charging for vehicle %s (index %d)",
                self.vehicle_id,
                emhass_index
            )
    
    async def _async_notify(self, title: str, message: str):
        """Send notification."""
        try:
            domain, service = self.notification_service.split(".", 1)
            await self.hass.services.async_call(
                domain,
                service,
                {
                    "title": title,
                    "message": message,
                    "notification_id": f"ev_trip_planner_{self.vehicle_id}",
                }
            )
        except Exception as err:
            _LOGGER.error("Error sending notification: %s", err)
    
    async def async_add_trip_monitor(self, trip_id: str, emhass_index: int):
        """Start monitoring a new trip's schedule."""
        if emhass_index in self._unsub_handlers:
            _LOGGER.debug(
                "Already monitoring index %d for vehicle %s",
                emhass_index,
                self.vehicle_id
            )
            return
        
        await self._async_monitor_schedule(emhass_index)
    
    async def async_remove_trip_monitor(self, emhass_index: int):
        """Stop monitoring a trip's schedule."""
        if emhass_index not in self._unsub_handlers:
            return
        
        unsub = self._unsub_handlers.pop(emhass_index)
        if unsub:
            unsub()
        
        self._last_actions.pop(emhass_index, None)
        
        _LOGGER.info(
            "Stopped monitoring schedule for %s (index %d)",
            self.vehicle_id,
            emhass_index
        )
```

**CRITICAL CHANGES**:
- **Removed**: `emhass_index` from constructor (no longer per-vehicle)
- **Removed**: `self.schedule_entity_id` (now dynamic per index)
- **Added**: `self.emhass_adapter` to query dynamic indices
- **Added**: `self._unsub_handlers` as dict (index -> unsub function)
- **Added**: `self._last_actions` as dict (index -> last action)
- **Modified**: `async_start()` now monitors all assigned indices
- **Added**: `async_add_trip_monitor()` to start monitoring new trips
- **Added**: `async_remove_trip_monitor()` to stop monitoring deleted trips
- **Modified**: All methods now accept `emhass_index` parameter

**Validation**:
- [ ] Module imports without errors
- [ ] Can instantiate ScheduleMonitor
- [ ] Can instantiate VehicleScheduleMonitor
- [ ] `async_start()` monitors all existing trips
- [ ] `async_add_trip_monitor()` adds monitoring for new trips
- [ ] `async_remove_trip_monitor()` removes monitoring for deleted trips
- [ ] Run `pytest tests/test_schedule_monitor.py -k "test_dynamic_index_monitoring"`

**Deployment Checkpoint**: ✅ PASS → Continue to 3D.2
**Rollback**: Delete `schedule_monitor.py`

---

### Step 3D.2: Create PresenceMonitor Class

**Action**: Create presence detection component

**Files to Create**:
- `custom_components/ev_trip_planner/presence_monitor.py`

**Implementation**:
```python
"""Presence Monitor for EV Trip Planner."""

import logging
import math
from typing import Optional, Tuple, Dict, Any

from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)


class PresenceMonitor:
    """Monitors if vehicle is at home and plugged in."""
    
    def __init__(self, hass: HomeAssistant, vehicle_id: str, config: Dict[str, Any]):
        """Initialize presence monitor."""
        self.hass = hass
        self.vehicle_id = vehicle_id
        
        # Sensor-based detection
        self.home_sensor = config.get(CONF_HOME_SENSOR)
        self.plugged_sensor = config.get(CONF_PLUGGED_SENSOR)
        
        # Coordinate-based detection
        self.home_coords = config.get(CONF_HOME_COORDINATES)
        self.vehicle_coords_sensor = config.get(CONF_VEHICLE_COORDINATES_SENSOR)
        
        _LOGGER.debug(
            "Created PresenceMonitor for %s: home_sensor=%s, coords=%s",
            vehicle_id,
            bool(self.home_sensor),
            bool(self.home_coords)
        )
    
    async def async_check_home_status(self) -> bool:
        """
        Check if vehicle is at home.
        
        Priority:
        1. If home sensor configured → use that
        2. If coordinates configured → calculate distance
        3. Otherwise → assume True (blind mode)
        """
        # Method 1: Sensor
        if self.home_sensor:
            state = self.hass.states.get(self.home_sensor)
            if state:
                return state.state == "on"
            _LOGGER.warning("Home sensor not found: %s", self.home_sensor)
        
        # Method 2: Coordinates
        if self.home_coords and self.vehicle_coords_sensor:
            vehicle_state = self.hass.states.get(self.vehicle_coords_sensor)
            if vehicle_state and vehicle_state.state:
                try:
                    vehicle_coords = self._parse_coordinates(vehicle_state.state)
                    if vehicle_coords:
                        distance_km = self._calculate_distance(
                            self.home_coords,
                            vehicle_coords
                        )
                        # Consider "at home" if within 500m
                        return distance_km < 0.5
                except Exception as err:
                    _LOGGER.warning(
                        "Error calculating distance for %s: %s",
                        self.vehicle_id,
                        err
                    )
        
        # Method 3: Blind mode
        _LOGGER.debug(
            "No presence detection for %s, assuming at home",
            self.vehicle_id
        )
        return True
    
    async def async_check_plugged_status(self) -> bool:
        """Check if vehicle is plugged in."""
        if not self.plugged_sensor:
            # Assume plugged if no sensor
            return True
        
        state = self.hass.states.get(self.plugged_sensor)
        if not state:
            _LOGGER.warning("Plugged sensor not found: %s", self.plugged_sensor)
            return True
        
        return state.state == "on"
    
    async def async_check_charging_readiness(self) -> Tuple[bool, Optional[str]]:
        """
        Check if vehicle is ready for charging.
        
        Returns:
            Tuple of (ready: bool, reason: str|None)
        """
        # Check home
        at_home = await self.async_check_home_status()
        if not at_home:
            return False, "Vehicle not at home"
        
        # Check plugged
        is_plugged = await self.async_check_plugged_status()
        if not is_plugged:
            return False, "Vehicle not plugged in"
        
        return True, None
    
    def _parse_coordinates(self, state_value: str) -> Optional[Tuple[float, float]]:
        """Parse coordinates from string."""
        try:
            if state_value.startswith("[") and state_value.endswith("]"):
                state_value = state_value[1:-1]
            lat, lon = map(float, state_value.split(","))
            return (lat, lon)
        except:
            _LOGGER.warning("Failed to parse coordinates: %s", state_value)
            return None
    
    def _calculate_distance(self, coords1: Tuple[float, float],
                           coords2: Tuple[float, float]) -> float:
        """Calculate distance between two points using Haversine formula."""
        lat1, lon1 = coords1
        lat2, lon2 = coords2
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        
        # Differences
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        # Haversine formula
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Earth radius in km
        r = 6371
        
        return c * r
```

**CRITICAL CHANGES**:
- **Added**: `Dict, Any` to typing imports (consistency with other modules)
- **No functional changes**: PresenceMonitor works independently of EMHASS index assignment
- **Note**: This module doesn't need changes for dynamic index assignment

**Validation**:
- [ ] Module imports without errors
- [ ] Can instantiate PresenceMonitor
- [ ] Sensor-based detection works
- [ ] Coordinate-based detection works
- [ ] Blind mode works when no config
- [ ] Run `pytest tests/test_presence_monitor.py -k "test_presence_detection"`

**Deployment Checkpoint**: ✅ PASS → Continue to 3D.3
**Rollback**: Delete `presence_monitor.py`

---

### Step 3D.3: Integrate All Components

**Action**: Wire everything together in `__init__.py`

**Files to Modify**:
- `custom_components/ev_trip_planner/__init__.py`

**Update `async_setup_entry`**:
```python
# In async_setup_entry

# Create EMHASS adapter (NEW - must be before control strategy)
from .emhass_adapter import EMHASSAdapter

emhass_adapter = EMHASSAdapter(hass, entry.data)
await emhass_adapter.async_load()  # Restore index mappings
hass.data[DOMAIN][entry.entry_id]["emhass_adapter"] = emhass_adapter

# Create control strategy
from .vehicle_controller import create_control_strategy

control_strategy = create_control_strategy(hass, entry.data)
hass.data[DOMAIN][entry.entry_id]["control_strategy"] = control_strategy

# Create presence monitor (if configured)
presence_monitor = None
if entry.data.get(CONF_HOME_SENSOR) or entry.data.get(CONF_HOME_COORDINATES):
    from .presence_monitor import PresenceMonitor
    
    presence_monitor = PresenceMonitor(hass, vehicle_id, entry.data)
    hass.data[DOMAIN][entry.entry_id]["presence_monitor"] = presence_monitor

# Create schedule monitor
# (Will be started after all vehicles are set up)
```

**Update `async_setup`** (domain-level):
```python
# At end of async_setup (after all entries loaded)
async def async_setup(hass: HomeAssistant, config: Dict[str, Any]) -> bool:
    """Set up domain."""
    hass.data.setdefault(DOMAIN, {})
    
    # Create schedule monitor (but don't start yet)
    from .schedule_monitor import ScheduleMonitor
    
    schedule_monitor = ScheduleMonitor(hass)
    hass.data[DOMAIN]["schedule_monitor"] = schedule_monitor
    
    return True
```

**Start monitoring after all entries loaded**:
```python
# In async_setup_entry, at the end
async def async_start_monitoring(hass: HomeAssistant, entry: ConfigEntry):
    """Start schedule monitoring when all entries are ready."""
    # Wait for all entries to be set up
    await hass.async_block_till_done()
    
    # Get schedule monitor
    schedule_monitor = hass.data[DOMAIN].get("schedule_monitor")
    if not schedule_monitor:
        return
    
    # Collect all vehicle configs
    vehicle_configs = {}
    for entry_id, data in hass.data[DOMAIN].items():
        if entry_id in ["managers", "coordinators", "schedule_monitor"]:
            continue
        if isinstance(data, dict) and "config" in data:
            # Add emhass_adapter to config for ScheduleMonitor
            data["emhass_adapter"] = data.get("emhass_adapter")
            vehicle_configs[entry_id] = data
    
    # Start monitoring
    await schedule_monitor.async_setup(vehicle_configs)

# Call this at end of last entry's setup
hass.async_create_task(async_start_monitoring(hass, entry))
```

**CRITICAL CHANGES**:
- **Added**: EMHASSAdapter instantiation and loading of index mappings
- **Added**: Adapter passed to vehicle config for ScheduleMonitor
- **Modified**: Filter logic for collecting vehicle configs (more robust)
- **Note**: ScheduleMonitor now receives adapter to query dynamic indices

**Validation**:
- [ ] No errors during setup
- [ ] EMHASSAdapter created and loads mappings
- [ ] Schedule monitor created
- [ ] Presence monitors created (if configured)
- [ ] Control strategies created
- [ ] Run `pytest tests/test_integration.py -k "test_full_setup"`

**Deployment Checkpoint**: ✅ PASS → Continue to 3D.4
**Rollback**: Revert `__init__.py` changes

---

### Step 3D.4: Add Integration Tests

**Action**: Create comprehensive E2E tests

**Files to Create**:
- `tests/test_integration.py`

**Test Scenarios**:

```python
# tests/test_integration.py

async def test_full_flow_single_trip_dynamic_index(hass):
    """
    Test complete flow: Add trip → Dynamic index assignment → EMHASS schedule → Control activation.
    
    Steps:
    1. Setup vehicle with EMHASS adapter (no fixed index)
    2. Add recurring trip
    3. Verify deferrable load sensor created with dynamic index
    4. Verify index assigned (0 for first trip)
    5. Simulate EMHASS schedule change to "on"
    6. Verify control strategy activate() called
    7. Verify presence checks performed
    """
    # Implementation

async def test_multiple_trips_different_indices(hass):
    """
    Test multiple trips for same vehicle get different indices.
    
    Steps:
    1. Setup vehicle with EMHASS adapter
    2. Add first trip (Monday work)
    3. Verify index 0 assigned
    4. Add second trip (Wednesday shopping)
    5. Verify index 1 assigned (different from first)
    6. Add third trip (Friday cinema)
    7. Verify index 2 assigned
    8. Verify all three config sensors exist
    9. Verify indices are unique per trip
    """
    # Implementation

async def test_presence_prevents_charging(hass):
    """
    Test that charging doesn't activate when vehicle not home.
    
    Steps:
    1. Setup vehicle with home_sensor
    2. Add trip and get dynamic index
    3. Set home_sensor to "off"
    4. Simulate EMHASS schedule "on"
    5. Verify control strategy NOT called
    6. Verify notification sent
    """
    # Implementation

async def test_trip_deletion_releases_index(hass):
    """
    Test that deleting a trip releases its EMHASS index.
    
    Steps:
    1. Setup vehicle and add trip (gets index 0)
    2. Verify index 0 assigned
    3. Delete the trip
    4. Verify index 0 released and available
    5. Add new trip
    6. Verify new trip gets index 0 (reused)
    """
    # Implementation

async def test_index_persistence_across_restart(hass):
    """
    Test that index assignments persist across restarts.
    
    Steps:
    1. Setup vehicle and add 3 trips (indices 0, 1, 2)
    2. Save adapter state
    3. Create new adapter instance (simulating restart)
    4. Load state
    5. Verify all 3 indices still assigned to correct trips
    6. Verify no indices available (all 3 used)
    """
    # Implementation

async def test_emhass_failure_fallback(hass):
    """
    Test behavior when EMHASS schedule entity unavailable.
    
    Steps:
    1. Setup vehicle and add trip
    2. Remove schedule entity
    3. Verify graceful handling (no crashes)
    4. Verify logging
    5. Verify trip still has index assigned (not released on error)
    """
    # Implementation

async def test_index_exhaustion_handling(hass):
    """
    Test behavior when no EMHASS indices available.
    
    Steps:
    1. Setup vehicle with max_deferrable_loads = 2
    2. Add 2 trips (uses indices 0 and 1)
    3. Try to add third trip
    4. Verify third trip rejected with appropriate error
    5. Verify logging indicates no available indices
    6. Delete one trip
    7. Verify index released
    8. Add new trip successfully
    """
    # Implementation
```

**CRITICAL CHANGES**:
- **Removed**: Tests with fixed EMHASS indices per vehicle
- **Added**: `test_multiple_trips_different_indices` to verify dynamic assignment
- **Added**: `test_trip_deletion_releases_index` to verify index reuse
- **Added**: `test_index_persistence_across_restart` to verify state restoration
- **Added**: `test_index_exhaustion_handling` to test edge case
- **Modified**: All tests to work with dynamic index assignment
- **Note**: Tests now verify the complete lifecycle: assign → use → release → reuse

**Validation**:
- [ ] All integration tests pass
- [ ] Tests cover happy path and error cases
- [ ] Tests verify dynamic index assignment
- [ ] Tests verify index persistence
- [ ] Tests verify index reuse
- [ ] Tests can run in isolation (mock external dependencies)
- [ ] Run `pytest tests/test_integration.py -v`

**Deployment Checkpoint**: ✅ PASS → **PHASE 3D COMPLETE**
**Rollback**: Revert all 3D changes

---

## 🎯 Phase 3E: Integration Testing & Migration

**Duration**: 1 week  
**Risk Level**: 🟡 MEDIUM  
**Goal**: Validate complete system and provide migration path

### Step 3E.1: Manual Testing in Production

**Action**: Deploy to your Home Assistant and monitor

**Deployment Steps**:

1. **Backup Everything**:
   ```bash
   # Backup HA config
   cp -r /home/malka/homeassistant /home/malka/homeassistant.backup.$(date +%Y%m%d)
   
   # Backup EV Trip Planner
   cd /home/malka/ha-ev-trip-planner
   git stash  # or commit current changes
   ```

2. **Deploy Phase 3A-3D Code**:
   ```bash
   # Copy new files
   cp -r custom_components/ev_trip_planner/* /home/malka/homeassistant/custom_components/ev_trip_planner/
   
   # Restart HA
   docker restart homeassistant
   ```

3. **Configure Test Vehicle**:
   - Go to HA → Settings → Devices & Services
   - Add EV Trip Planner integration
   - Configure with max_deferrable_loads = 10 (for testing)
   - Configure presence sensors (optional)
   - Configure control strategy (use "none" for safe testing)

4. **Add Test Trip**:
   ```yaml
   service: ev_trip_planner.add_recurring_trip
   data:
     vehicle_id: "chispitas"
     dia_semana: "lunes"
     hora: "09:00"
     km: 24
     kwh: 3.6
     descripcion: "Test Work Trip"
   ```

5. **Verify**:
   - [ ] Sensor `sensor.chispitas_active_trips` exists
   - [ ] Sensor shows count = 1
   - [ ] Sensor `sensor.emhass_deferrable_load_config_0` exists (dynamic index 0)
   - [ ] Sensor has correct attributes (def_total_hours, P_deferrable_nom, etc.)
   - [ ] Sensor attributes include `trip_id` and `emhass_index: 0`
   - [ ] No errors in HA logs

6. **Add Multiple Trips**:
   ```yaml
   # Second trip
   service: ev_trip_planner.add_recurring_trip
   data:
     vehicle_id: "chispitas"
     dia_semana: "miercoles"
     hora: "14:00"
     km: 15
     kwh: 2.5
     descripcion: "Shopping"
   
   # Third trip
   service: ev_trip_planner.add_recurring_trip
   data:
     vehicle_id: "chispitas"
     dia_semana: "viernes"
     hora: "20:00"
     km: 30
     kwh: 4.5
     descripcion: "Cinema"
   ```

7. **Verify Multiple Trips**:
   - [ ] Sensor `sensor.chispitas_active_trips` shows count = 3
   - [ ] Three config sensors exist: `sensor.emhass_deferrable_load_config_0`, `_1`, `_2`
   - [ ] Each sensor has unique `trip_id` attribute
   - [ ] Each sensor has unique `emhass_index` (0, 1, 2)
   - [ ] No errors in logs

8. **Test Index Persistence**:
   - Restart Home Assistant
   - Verify all 3 trips still have same indices after restart
   - Verify `sensor.chispitas_active_trips` still shows count = 3

9. **Test Trip Deletion**:
   - Delete one trip
   - Verify sensor count decreases to 2
   - Verify corresponding config sensor cleared (state = "idle")
   - Add new trip
   - Verify new trip gets index of deleted trip (reuse)

10. **Monitor for 24 Hours**:
    - Check logs every few hours
    - Verify no errors
    - Verify sensors update when trips change
    - Verify indices are properly managed

**Success Criteria**:
- [ ] No errors in logs for 24h
- [ ] Dynamic index assignment works correctly
- [ ] Multiple trips get unique indices
- [ ] Indices persist across restarts
- [ ] Indices are released and reused when trips deleted
- [ ] All config sensors created with correct attributes

**Deployment Checkpoint**: ✅ PASS → Continue to 3E.2
**Rollback**: Restore from backup

---

### Step 3E.2: Create Migration Service

**Action**: Add service to import from existing sliders

**Files to Modify**:
- `custom_components/ev_trip_planner/services.yaml`
- `custom_components/ev_trip_planner/trip_manager.py`

**Add to `services.yaml`**:
```yaml
import_from_sliders:
  name: Import from Sliders
  description: Convert existing slider-based configuration to trips
  fields:
    vehicle_id:
      description: Vehicle identifier
      example: chispitas
    preview:
      description: Preview mode (show what would be created without creating)
      example: true
    clear_existing:
      description: Clear existing trips before import
      example: false
```

**Add to `trip_manager.py`**:
```python
async def async_import_from_sliders(self, preview: bool = True, 
                                   clear_existing: bool = False) -> Dict[str, Any]:
    """
    Import configuration from input_number sliders.
    
    Expected slider format: input_number.{vehicle}_carga_necesaria_{dia}
    """
    result = {
        "preview": preview,
        "trips_created": 0,
        "trips_skipped": 0,
        "errors": [],
        "details": [],
    }
    
    try:
        # Find slider entities
        slider_pattern = f"input_number.{self.vehicle_id}_carga_necesaria_"
        slider_entities = [
            entity_id for entity_id in self.hass.states.async_entity_ids("input_number")
            if entity_id.startswith(slider_pattern)
        ]
        
        if not slider_entities:
            result["errors"].append("No slider entities found")
            return result
        
        # Parse each slider
        trips_to_create = []
        for entity_id in slider_entities:
            # Extract day from entity_id
            # input_number.chispitas_carga_necesaria_lunes → "lunes"
            day = entity_id.split("_")[-1]
            
            state = self.hass.states.get(entity_id)
            if not state:
                result["errors"].append(f"Slider not found: {entity_id}")
                continue
            
            try:
                kwh = float(state.state)
                if kwh <= 0:
                    result["details"].append(f"Skipping {day}: kWh is 0")
                    result["trips_skipped"] += 1
                    continue
                
                # Default time (can be made configurable)
                default_time = "09:00"
                
                trips_to_create.append({
                    "dia_semana": day,
                    "hora": default_time,
                    "km": kwh * 6.67,  # Rough estimate: 15 kWh/100km
                    "kwh": kwh,
                    "descripcion": f"Imported: {day}",
                })
                
            except ValueError:
                result["errors"].append(f"Invalid kWh value in {entity_id}: {state.state}")
                continue
        
        result["trips_to_create"] = len(trips_to_create)
        
        if preview:
            result["details"].extend([
                f"Would create: {trip['dia_semana']} at {trip['hora']} - {trip['kwh']} kWh"
                for trip in trips_to_create
            ])
            return result
        
        # Clear existing if requested
        if clear_existing:
            existing = await self.async_get_recurring_trips()
            for trip in existing:
                await self.async_delete_trip(trip["id"])
            result["details"].append(f"Cleared {len(existing)} existing trips")
        
        # Create trips
        for trip_data in trips_to_create:
            try:
                await self.async_add_recurring_trip(**trip_data)
                result["trips_created"] += 1
                result["details"].append(
                    f"Created: {trip_data['dia_semana']} at {trip_data['hora']}"
                )
            except Exception as err:
                result["errors"].append(
                    f"Failed to create trip for {trip_data['dia_semana']}: {err}"
                )
        
        return result
        
    except Exception as err:
        result["errors"].append(f"Unexpected error: {err}")
        return result
```

**Add service handler in `__init__.py`**:
```python
# In register_services
async def handle_import_from_sliders(call: ServiceCall):
    data = call.data
    mgr = _get_manager(data["vehicle_id"])
    await _ensure_setup(mgr)
    
    result = await mgr.async_import_from_sliders(
        preview=bool(data.get("preview", True)),
        clear_existing=bool(data.get("clear_existing", False))
    )
    
    # Return result as response
    return result

hass.services.async_register(
    DOMAIN,
    "import_from_sliders",
    handle_import_from_sliders,
    schema=vol.Schema({
        vol.Required("vehicle_id"): str,
        vol.Optional("preview", default=True): bool,
        vol.Optional("clear_existing", default=False): bool,
    }),
    supports_response=True,  # Return result to caller
)
```

**Validation**:
- [ ] Service appears in HA Developer Tools
- [ ] Preview mode shows what would be created
- [ ] Actual import creates trips correctly
- [ ] Run `pytest tests/test_migration.py -k "test_import_from_sliders"`

**Deployment Checkpoint**: ✅ PASS → Continue to 3E.3  
**Rollback**: Remove service registration

---

### Step 3E.3: Final Validation Checklist

**Action**: Complete final validation before declaring Milestone 3 complete

**Pre-Deployment Checklist**:
- [ ] All unit tests pass (`pytest tests/ -v`)
- [ ] Code coverage >80% (`pytest --cov=custom_components/ev_trip_planner tests/`)
- [ ] No linting errors (`flake8 custom_components/ev_trip_planner/`)
- [ ] Type hints added to all new functions
- [ ] Docstrings added to all new classes/functions

**Production Validation Checklist**:
- [ ] 24h manual test completed without errors
- [ ] EMHASS integration working (schedules generated)
- [ ] Control actions execute correctly (test with "none" strategy first)
- [ ] Presence detection prevents charging when away (if configured)
- [ ] Notifications sent correctly (if configured)
- [ ] Migration service works (test in preview mode)
- [ ] No errors in HA logs
- [ ] Latency measured: trip change → control action < 60s

**Documentation Checklist**:
- [ ] README.md updated with Milestone 3 features
- [ ] Configuration examples added for OVMS and Renault
- [ ] EMHASS setup guide added
- [ ] Troubleshooting section expanded
- [ ] Migration guide from sliders to trips added

**User Experience Checklist**:
- [ ] Config flow intuitive and error-free
- [ ] Error messages clear and actionable
- [ ] Sensors have friendly names and icons
- [ ] Attributes provide useful information
- [ ] No breaking changes for existing users

**Deployment Checkpoint**: ✅ ALL CHECKS PASS → **MILESTONE 3 COMPLETE** 🎉

---

## 🔄 Rollback Strategies

### Phase 3A Rollback
```bash
# Revert const.py
git checkout custom_components/ev_trip_planner/const.py

# Revert config_flow.py
git checkout custom_components/ev_trip_planner/config_flow.py

# Revert sensor.py
git checkout custom_components/ev_trip_planner/sensor.py

# Delete test files
rm tests/test_config_flow_milestone3.py
rm tests/test_sensors_milestone3.py

# Restart HA
docker restart homeassistant
```

### Phase 3B Rollback
```bash
# Delete new files
rm custom_components/ev_trip_planner/emhass_adapter.py
rm tests/test_emhass_adapter.py

# Revert modified files
git checkout custom_components/ev_trip_planner/__init__.py
git checkout custom_components/ev_trip_planner/trip_manager.py

# Restart HA
docker restart homeassistant
```

### Phase 3C Rollback
```bash
# Delete new files
rm custom_components/ev_trip_planner/vehicle_controller.py
rm tests/test_vehicle_controller.py

# Revert config_flow.py
git checkout custom_components/ev_trip_planner/config_flow.py

# Revert __init__.py
git checkout custom_components/ev_trip_planner/__init__.py

# Restart HA
docker restart homeassistant
```

### Phase 3D Rollback
```bash
# Delete new files
rm custom_components/ev_trip_planner/schedule_monitor.py
rm custom_components/ev_trip_planner/presence_monitor.py
rm tests/test_schedule_monitor.py
rm tests/test_presence_monitor.py
rm tests/test_integration.py

# Revert __init__.py
git checkout custom_components/ev_trip_planner/__init__.py

# Restart HA
docker restart homeassistant
```

### Phase 3E Rollback
```bash
# Revert services.yaml
git checkout custom_components/ev_trip_planner/services.yaml

# Revert trip_manager.py
git checkout custom_components/ev_trip_planner/trip_manager.py

# Revert __init__.py
git checkout custom_components/ev_trip_planner/__init__.py

# Restart HA
docker restart homeassistant
```

### Full Milestone 3 Rollback
```bash
# Restore from backup (taken before starting Milestone 3)
cp -r /home/malka/homeassistant.backup.YYYYMMDD /home/malka/homeassistant

# Or revert all git changes
cd /home/malka/ha-ev-trip-planner
git reset --hard HEAD~N  # N = number of commits to revert

# Restart HA
docker restart homeassistant
```

---

## 📊 Timeline & Milestones

| Phase | Duration | Start Date | End Date | Status |
|-------|----------|------------|----------|--------|
| 3A: Configuration | 1 week | Week 1 | Week 1 | 🟡 Ready |
| 3B: EMHASS Adapter | 1 week | Week 2 | Week 2 | ⚪ Pending |
| 3C: Vehicle Control | 1 week | Week 3 | Week 3 | ⚪ Pending |
| 3D: Schedule Monitor | 1 week | Week 4 | Week 4 | ⚪ Pending |
| 3E: Integration | 1 week | Week 5 | Week 5 | ⚪ Pending |

**Total Milestone 3 Duration**: 5 weeks  
**Buffer Time**: 1 week (for issues, testing, documentation)  
**Expected Completion**: 6 weeks from start date

---

## 🎯 Next Steps

### Immediate (Today)
1. ✅ Review this implementation plan
2. ✅ Validate EMHASS configuration in production
3. ✅ Validate presence sensors exist
4. ✅ Create feature branch: `git checkout -b milestone-3-emhass-integration`

### This Week (Phase 3A)
5. Implement Step 3A.1 (constants)
6. Implement Step 3A.2 (config flow EMHASS step)
7. Implement Step 3A.3 (config flow presence step)
8. Implement Step 3A.4 (status sensors)
9. Implement Step 3A.5 (unit tests)
10. **Deploy Phase 3A to test environment**
11. **Validate 3A deployment checkpoint**

### Next Week (Phase 3B)
12. Implement Step 3B.1 (EMHASSAdapter)
13. Implement Step 3B.2 (integration with TripManager)
14. Implement Step 3B.3 (multiple trips support)
15. Implement Step 3B.4 (unit tests)
16. **Deploy Phase 3B to test environment**
17. **Validate 3B deployment checkpoint**

### Week 3 (Phase 3C)
18. Implement Step 3C.1 (control strategies)
19. Implement Step 3C.2 (config flow integration)
20. Implement Step 3C.3 (controller instantiation)
21. **Deploy Phase 3C to test environment**
22. **Validate 3C deployment checkpoint**

### Week 4 (Phase 3D)
23. Implement Step 3D.1 (ScheduleMonitor)
24. Implement Step 3D.2 (PresenceMonitor)
25. Implement Step 3D.3 (component integration)
26. Implement Step 3D.4 (integration tests)
27. **Deploy Phase 3D to test environment**
28. **Run 24h manual test**
29. **Validate 3D deployment checkpoint**

### Week 5 (Phase 3E)
30. Implement Step 3E.1 (manual testing validation)
31. Implement Step 3E.2 (migration service)
32. Implement Step 3E.3 (final validation)
33. **Complete final validation checklist**
34. **Merge to main branch**
35. **Tag release v0.3.0-dev**

---

## ⚠️ Critical Warnings

1. **NEVER skip deployment checkpoints**: Each checkpoint validates that the phase works correctly. Skipping risks compounding errors.

2. **ALWAYS test in non-production first**: Use a separate HA instance or test environment for initial deployment of each phase.

3. **BACKUP before each phase**: Take snapshots/backups before deploying each phase for easy rollback.

4. **MONITOR logs continuously**: During manual testing, watch logs in real-time:
   ```bash
   docker logs -f homeassistant | grep ev_trip_planner
   ```

5. **START with "none" control type**: Test all functionality without actually controlling charging first, then enable control once confident.

6. **PRESENCE DETECTION is critical**: Without it, the system may try to charge when vehicle is away. Always configure presence detection before enabling control.

---

## 📞 Support & Troubleshooting

If issues arise during implementation:

1. **Check logs first**: `docker logs homeassistant --tail 100 | grep ev_trip_planner`
2. **Verify EMHASS**: Ensure EMHASS is running and schedule sensor exists
3. **Check entity IDs**: Verify all configured entity IDs exist
4. **Test manually**: Use Developer Tools → Services to test individual components
5. **Review docs**: Check `MILESTONE_3_REFINEMENT.md` for detailed specifications

**For help**: Open an issue on GitHub with:
- Phase number and step
- Error logs
- Configuration (redact sensitive data)
- Expected vs actual behavior

---

**Document Version**: 1.0  
**Last Updated**: 2025-12-08  
**Next Review**: After Phase 3A completion