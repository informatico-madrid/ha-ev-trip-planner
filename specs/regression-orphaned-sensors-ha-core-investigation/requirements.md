# Requirements: regression-orphaned-sensors-ha-core-investigation

## Context

Approved 5-phase plan from design interview. Design approved with 3 user adjustments.

### User Adjustments (incorporated)

1. **Phase 2 coordinator.data shape**: TripSensor reads SU trip by `trip_id` from `coordinator.data["recurring_trips"][trip_id]` or `coordinator.data["punctual_trips"][trip_id]`, NOT directly from trip_manager
2. **Phase 2 async_add_entities platform-only**: HA passes `async_add_entities` ONLY to `sensor.py`'s platform `async_setup_entry()` — it CANNOT be stored in `entry.runtime_data` from `__init__.py`. TripSensors are created during platform setup.
3. **Phase 0 adds 2 more tests**: `test_no_duplicate_sensors_after_reload` + `test_two_vehicles_no_unique_id_collision`

---

## Phase 0: Characterization Tests (6 tests)

**Tier 1 — Entity Registry lifecycle tests (REQUIRED before refactor)**

| Test | File | What it verifies | Expected today |
|------|------|-------------------|-----------------|
| `test_sensor_unique_id_exists_after_setup` | `tests/test_entity_registry.py` | 7 TripPlanner + 1 Emhass sensors have unique_id in registry after setup | FAIL (no unique_id) |
| `test_sensor_removed_after_unload` | `tests/test_entity_registry.py` | 0 sensors after unload | FAIL (orphans remain) |
| `test_trip_sensor_created_in_registry_after_add` | `tests/test_entity_registry.py` | TripSensor appears in registry after add_trip service | FAIL (orphan object) |
| `test_trip_sensor_removed_from_registry_after_delete` | `tests/test_entity_registry.py` | Registry clean after delete_trip | FAIL (zombie) |
| `test_no_duplicate_sensors_after_reload` | `tests/test_entity_registry.py` | Same count before/after reload (not doubled) | FAIL (duplicates) |
| `test_two_vehicles_no_unique_id_collision` | `tests/test_entity_registry.py` | All unique_ids globally unique across vehicles | FAIL (collision) |

**Tier 2 — Existing E2E (DO NOT TOUCH)**
- 16 E2E tests cover trip CRUD + config flow — untouched safety net

**Tier 3 — Not prioritized now**
- `hass.states.async_get()` tests deferred

---

## Phase 1: definitions.py + Base Architecture

### FR-1: SensorEntityDescription Pattern

**Requirement**: Create `definitions.py` with `TripSensorEntityDescription` dataclass and `TRIP_SENSORS` tuple.

```python
@dataclass(frozen=True)
class TripSensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[dict], Any] = lambda data: None
    attrs_fn: Callable[[dict], dict] = lambda data: {}

TRIP_SENSORS: tuple[TripSensorEntityDescription, ...] = (
    TripSensorEntityDescription(
        key="recurring_trips_count",
        translation_key="recurring_trips_count",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: len(data.get("recurring_trips", {})),
    ),
    TripSensorEntityDescription(
        key="kwh_needed_today",
        translation_key="kwh_needed_today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda data: data.get("kwh_today", 0.0),
    ),
    # ... 7 total sensors as data, not classes
)
```

### FR-2: Single TripPlannerSensor Class

**Requirement**: Replace 7+ sensor subclasses with ONE `TripPlannerSensor(CoordinatorEntity, SensorEntity)` class.

```python
class TripPlannerSensor(CoordinatorEntity[TripPlannerCoordinator], SensorEntity):
    def __init__(self, coordinator, vehicle_id, description: TripSensorEntityDescription):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{vehicle_id}_{description.key}"  # ← R-01
        self._vehicle_id = vehicle_id
        self.entity_description = description

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)
```

### FR-3: CoordinatorEntity Inheritance

**Requirement**: All sensors inherit from `CoordinatorEntity`, read from `coordinator.data` only, NO `async_update()` polling.

### FR-4: No MagicMock in Production

**Requirement**: Remove all `from unittest.mock import MagicMock` from `sensor.py`. If coordinator is None, raise `ValueError`.

---

## Phase 2: TripSensor Lifecycle

### FR-5: TripSensor Uses CoordinatorEntity

**Requirement**: TripSensor class uses `CoordinatorEntity` pattern, reads its trip from `coordinator.data`.

**coordinator.data shape**:
```python
{
    "recurring_trips": {"trip_abc": {"id": "trip_abc", "estado": "active", ...}, ...},
    "punctual_trips": {"trip_xyz": {"id": "trip_xyz", "estado": "pending", ...}},
    "kwh_today": 12.5,
    "next_trip": {...},
}
```

**TripSensor reads its slice**:
```python
@property
def native_value(self):
    trips = self.coordinator.data.get("recurring_trips", {})
    trip = trips.get(self._trip_id)
    return trip.get("estado", "pendiente") if trip else None
```

### FR-6: TripSensor Creation via Platform Setup

**Requirement**: `async_add_entities` is passed by HA's platform setup mechanism directly to `sensor.py`'s `async_setup_entry()`. It CANNOT be stored in `entry.runtime_data` from `__init__.py` (that scope doesn't have access to it).

**Correct pattern** (Bermuda/Battery Notes):
```python
# sensor.py - sensor platform's async_setup_entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # async_add_entities IS PASSED BY HA as a parameter — use it directly, don't wrap it
    runtime_data: EVTripRuntimeData = entry.runtime_data

    entities = []
    # Create static sensors during platform setup
    for description in TRIP_SENSORS:
        entities.append(TripPlannerSensor(runtime_data.coordinator, vehicle_id, description))

    # Create TripSensors from existing trips already in trip_manager
    for trip_id, trip_data in runtime_data.trip_manager.async_get_trips().items():
        entities.append(TripSensor(runtime_data.coordinator, vehicle_id, trip_id, trip_data))

    # Register all entities with HA using the callback HA passed to us
    await async_add_entities(entities, True)

    return True
```

**Alternative (ConfigSubentry)**: HA 2024.x ConfigSubentry pattern where each trip is a sub-entry with its own lifecycle. More complex but correct. Deferred for now.

**Key constraint**: `async_add_entities` is ONLY available inside the platform's `async_setup_entry()` callback — it cannot escape to `__init__.py` or `entry.runtime_data`.

### FR-7: entity_registry.async_remove() on Trip Delete

**Requirement**: When deleting a trip, clean up Entity Registry entries.

```python
async def async_remove_trip_sensor(hass, entry, trip_id):
    # 1. Remove from trip_manager
    await trip_manager.async_delete_trip(trip_id)

    # 2. Remove from Entity Registry
    entity_registry = er.async_get(hass)
    for entity_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if trip_id in entity_entry.unique_id:
            entity_registry.async_remove(entity_entry.entity_id)

    # 3. Refresh coordinator
    entry.runtime_data.coordinator.async_request_refresh()
```

---

## Phase 3: EMHASS Single Path

### FR-8: Remove hass.states.async_set() from emhass_adapter

**Requirement**: Remove ALL `hass.states.async_set()` calls from `emhass_adapter.py`.

### FR-9: publish_deferrable_loads uses coordinator.refresh

**Requirement**: `publish_deferrable_loads()` replaced with call to `coordinator.async_request_refresh()`.

```python
# REMOVE: hass.states.async_set(sensor_id, "ready", {...})

# INSTEAD:
entry.runtime_data.coordinator.async_request_refresh()
```

### FR-10: EmhassDeferrableLoadSensor Fix

**Requirement**: `EmhassDeferrableLoadSensor` currently does NOT inherit from `CoordinatorEntity` (sensor.py:494 — `class EmhassDeferrableLoadSensor(SensorEntity)`). Two problems:

1. **Dual-writing conflict**: `publish_deferrable_loads()` via `hass.states.async_set()` overwrites `_cached_attrs` that `async_update()` writes to — two writers for same entity
2. **No trigger path**: If we remove `publish_deferrable_loads()` and call `coordinator.async_request_refresh()` instead, `EmhassDeferrableLoadSensor` WON'T update because it doesn't listen to the coordinator

**Fix**: `EmhassDeferrableLoadSensor` must either:
- **Option A** (preferred): Inherit from `CoordinatorEntity` and read from `coordinator.data` — unified update path
- **Option B**: Keep independent refresh mechanism — BUT this requires `publish_deferrable_loads()` to remain and NOT use `hass.states.async_set()` (use a proper sensor update instead)

**Chosen**: Option A — Make `EmhassDeferrableLoadSensor` inherit from `CoordinatorEntity` and add EMHASS data to `coordinator.data`. This unifies the update path.

---

## Phase 4: __init__.py Extraction

### FR-11: __init__.py < 150 Lines

**Requirement**: `__init__.py` contains ONLY:
- `PLATFORMS` constant
- `EVTripRuntimeData` dataclass
- `async_setup_entry(hass, entry)`
- `async_unload_entry(hass, entry)`
- `async_remove_entry(hass, entry)`
- `async_migrate_entry(hass, entry)`

### FR-12: Services Extracted to services.py

**Requirement**: All service handlers (add_trip, remove_trip, update_trip, trip_list, etc.) moved to `services.py`.

### FR-13: entry.runtime_data Used

**Requirement**: All runtime data access uses `entry.runtime_data` NOT `hass.data[DATA_RUNTIME]` or legacy namespace patterns.

---

## Phase 5: Global Cleanup

### FR-14: No Legacy Namespace Fallbacks

**Requirement**: Remove all `f"ev_trip_planner_{entry_id}"`, `f"{DOMAIN}_{entry_id}"` legacy patterns.

### FR-15: No MagicMock in Production

**Requirement**: Verify zero `from unittest.mock` imports in `custom_components/` (except `tests/`).

### FR-16: DEBUG Not WARNING for Flow Logs

**Requirement**: Replace `WARNING` spam (flow traces) with `DEBUG` level. `WARNING` only for recoverable anomalies.

---

## Acceptance Criteria Summary

| Phase | Criteria |
|-------|----------|
| **Phase 0** | 6 characterization tests FAIL today (document broken behavior) |
| **Phase 1** | All 7 TripPlannerSensors use single class with unique_id, CoordinatorEntity, no MagicMock |
| **Phase 2** | TripSensor created via platform setup (HA passes `async_add_entities` to `sensor.py`'s `async_setup_entry()`); deleted via `er.async_remove()` |
| **Phase 3** | EMHASS sensor updates via CoordinatorEntity only (no `async_set` path) |
| **Phase 4** | `__init__.py` < 150 lines, services extracted, `entry.runtime_data` used |
| **Phase 5** | Zero legacy fallbacks, zero MagicMock in production, DEBUG logs |

---

## Non-Goals (Explicitly Out of Scope)

- E2E test modifications (Tier 2 tests untouched)
- `hass.states.async_get()` integration tests (Tier 3, deferred)
- Frontend panel changes (handled separately if needed)
- EMHASS computation logic (only lifecycle, not the algorithm)