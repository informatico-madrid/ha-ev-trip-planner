# Research: regression-orphaned-sensors-ha-core-investigation

## Executive Summary

The EV Trip Planner integration has **two critical bugs** and **one architectural debt** that cause orphaned sensors, duplicate entities, and trip data not appearing in EMHASS:

1. **TripPlannerSensors lack `unique_id`** — 7+ classes (`RecurringTripsCountSensor`, etc.) don't set `_attr_unique_id`, causing duplicates on every HA restart
2. **TripSensor 3-layer orphan bug** — `_async_create_trip_sensors()` (correct), `async_create_trip_sensor()` (orphan), `async_remove_trip_sensor()` (no registry cleanup)
3. **EMHASS dual writing** — `publish_deferrable_loads()` uses `hass.states.async_set()` while `EmhassDeferrableLoadSensor` uses proper SensorEntity path

The 5-phase plan fixes all three systematically, starting with characterization tests (Phase 0).

---

## Problem 1: Sensores Duplicados (Bug G-01)

### Root Cause

`TripPlannerSensor` base class and all subclasses (RecurringTripsCountSensor, PunctualTripsCountSensor, TripsListSensor, KwhTodaySensor, HoursTodaySensor, NextTripSensor, NextDeadlineSensor) **do NOT set `_attr_unique_id`**.

Without `unique_id`, Home Assistant cannot track entities. Each restart creates new entities, previous ones become "zombis" in the Entity Registry.

### Evidence

```python
# sensor.py line 65 - TripPlannerSensor base
class TripPlannerSensor(SensorEntity):
    def __init__(self, trip_manager, sensor_type):
        super().__init__(trip_manager.hass, trip_manager, sensor_type)
        self._attr_name = f"{vehicle_id} {sensor_type}"
        # ← MISSING: self._attr_unique_id = f"{DOMAIN}_{vehicle_id}_{sensor_type}"
```

7 sensor classes inherit from `TripPlannerSensor` but none set `unique_id`.

### Impact

- After clean HACS reinstall, old vehicles ("chispi", "chispitas") still show
- `chispitas_power_flow_color` and `chispitas_power_flow_color_2` (duplicate suffix)
- Each restart accumulates more orphaned entities

---

## Problem 2: TripSensor 3-Layer Orphan Bug (Critical)

### Three Creation Paths

| Layer | Method | Entity Registry | Result |
|-------|--------|-----------------|--------|
| 1 | `async_setup_entry()` → `_async_create_trip_sensors()` | ✅ YES (via `async_add_entities()`) | Correct |
| 2 | `async_create_trip_sensor()` | ❌ NO (stored in `hass.data[...]` dict) | Orphan Python object |
| 3 | `async_remove_trip_sensor()` | ❌ NO (only `del dict[trip_id]`) | Registry zombie |

### Layer 1: Correct Path

```python
# __init__.py - _async_create_trip_sensors()
def _async_create_trip_sensors(hass, trip_manager, vehicle_id, async_add_entities):
    for trip in all_trips:
        sensor = TripSensor(hass, trip_manager, trip)
        async_add_entities([sensor])  # ← Registers in Entity Registry
```

### Layer 2: Orphan Path

```python
# __init__.py - async_create_trip_sensor()
async def async_create_trip_sensor(...):
    new_sensor = TripSensor(hass, trip_manager, trip_data)
    hass.data[DATA_RUNTIME][namespace]["trip_sensors"][trip_id] = new_sensor
    # ← NEVER calls async_add_entities() — HA doesn't know this entity exists
```

**Result**: Sensor object exists in Python memory but is invisible to HA UI and automation.

### Layer 3: Orphan Cleanup

```python
# __init__.py - async_remove_trip_sensor()
async def async_remove_trip_sensor(...):
    del hass.data[DATA_RUNTIME][namespace]["trip_sensors"][trip_id]
    # ← Only removes from dict, never calls entity_registry.async_remove()
```

**Result**: Registry entries from Layer 1 become zombies.

### Correct Fix Pattern

```python
# When adding a trip from a service:
new_sensor = TripSensor(hass, trip_manager, trip_data)
async_add_entities([new_sensor])  # ← Use the same callable from setup

# When removing:
entity_registry = er.async_get(hass)
for entry in er.async_entries_for_config_entry(entity_registry, entry_id):
    if trip_id in entry.unique_id:
        entity_registry.async_remove(entry.entity_id)
```

---

## Problem 3: EMHASS Dual Writing Path

### Current State

Two parallel paths for the same EMHASS sensor:

**Path 1 (State-only)**: `emhass_adapter.publish_deferrable_loads()` at line ~514
```python
hass.states.async_set(
    sensor_id, "ready",
    {"power_profile_watts": ..., "deferrables_schedule": ..., "entry_id": entry_id}
)
```
- Creates ephemeral state-based entities NOT in entity registry
- Bypasses normal SensorEntity lifecycle

**Path 2 (Registry)**: `EmhassDeferrableLoadSensor` class at sensor.py line 494
```python
class EmhassDeferrableLoadSensor(SensorEntity):
    self._attr_unique_id = f"emhass_perfil_diferible_{entry_id}"  # ← Correct
```
- Proper SensorEntity registered via platform setup
- Has `unique_id` (unlike TripPlannerSensors)
- Updates via `async_update()` but missing `async_schedule_update_ha_state()`

### Why Both Are Wrong

1. **Two writers for same entity_id** — Race condition, inconsistent state
2. **`publish_deferrable_loads()` not triggered on vehicle param changes** — `power_profile_watts` doesn't update when charging_power changes
3. **`async_update()` missing `async_schedule_update_ha_state()`** — Attributes updated internally but not propagated to HA state machine

### Correct Fix

```python
# emhass_adapter.py - REMOVE all hass.states.async_set() calls

# INSTEAD: publish_deferrable_loads() calls:
coordinator.async_request_refresh()  # ← Triggers EmhassDeferrableLoadSensor update

# EmhassDeferrableLoadSensor.async_update() already works correctly
# Just needs to be the SOLE source of truth
```

---

## Problem 4: __init__.py God Object (Bug G-12)

Current `__init__.py`: **1864 lines**

Contains:
- Lifecycle functions (setup, unload, remove)
- ALL service handlers (add_trip, remove_trip, update_trip, etc.)
- Dashboard registration
- Sensor creation logic
- Storage cleanup
- EMHASS adapter management
- Panel registration

**Violates**: R-10 from CODEGUIDELINESia.md v2

Target: `<150 lines` (lifecycle only)

---

## Architecture: Target State

### File Structure

```
custom_components/ev_trip_planner/
├── __init__.py              # <150 lines: PLATFORMS, EVTripRuntimeData, lifecycle
├── definitions.py           # NEW: TripSensorEntityDescription + TRIP_SENSORS tuple
├── coordinator.py          # NEW: TripPlannerCoordinator(DataUpdateCoordinator)
├── sensor.py                # TripPlannerSensor(CoordinatorEntity) + EmhassDeferrableLoadSensor
├── services.py             # NEW: extracted service handlers
├── emhass_adapter.py       # REMOVE async_set, use coordinator.refresh
├── trip_manager.py          # KEPT: business logic
├── config_flow.py           # KEPT: with version=2 migration
├── diagnostics.py           # NEW: async_get_config_entry_diagnostics
└── ...
```

### Data Flow (Single Path)

```
Service (add_trip)
    ↓
services.py handler
    ↓
trip_manager.async_add_trip()
    ↓
coordinator.async_request_refresh()
    ↓
coordinator._async_update_data()
    ↓
coordinator.data = {
    "recurring_trips": {"trip_abc": {...}, "trip_def": {...}},
    "punctual_trips": {"trip_xyz": {...}},
    "kwh_today": 12.5,
    "next_trip": {...},
}
    ↓
CoordinatorEntity listeners notified
    ↓
TripPlannerSensor.native_value reads from coordinator.data
    ↓
HA UI updated via async_write_ha_state()
```

---

## Research Sources

1. **Full interview transcript**: `specs/regression-orphaned-sensors-ha-core-investigation/fullinterview.txt`
2. **Code guidelines**: `docs/CODEGUIDELINESia.md` (v2, 12 gaps, R-01 through R-12)
3. **Logs**: `docs/logsdebug/logsdebug` (28K lines, orphaned sensor patterns)
4. **Related specs**: `emhass-sensor-entity-lifecycle` (research.md, design.md, tasks.md)
5. **Prior spec**: `duplicate-emhass-sensor-fix` (partial fix, insufficient)

---

## Related Files Analyzed

| File | Lines | Key Finding |
|------|-------|-------------|
| `sensor.py` | 494-634, 637-674 | EmhassDeferrableLoadSensor + TripSensor classes |
| `emhass_adapter.py` | 509-548, 1111-1161 | publish_deferrable_loads(), async_cleanup_vehicle_indices() |
| `__init__.py` | 802-853, 856-973 | async_unload_entry, async_remove_entry, trip sensor creation |
| `panel.js` | 1008-1064 | Too-broad sensor patterns causing cross-vehicle contamination |

---

## Key Code References

- `sensor.py:65` — TripPlannerSensor base (no unique_id)
- `sensor.py:210-482` — 7 TripPlannerSensor subclasses (no unique_id)
- `sensor.py:494-634` — EmhassDeferrableLoadSensor (unique_id correct, missing async_schedule_update_ha_state)
- `sensor.py:637-674` — TripSensor (3-layer creation bug)
- `emhass_adapter.py:509-548` — publish_deferrable_loads() (async_set bypass)
- `emhass_adapter.py:1111-1161` — async_cleanup_vehicle_indices() (state-only cleanup)
- `__init__.py:802-853` — async_unload_entry (no entity_registry cleanup)
- `__init__.py:856-973` — async_remove_entry (no entity_registry cleanup)