# Requirements: regression-orphaned-sensors-ha-core-investigation

## Context

Approved 5-phase plan from design interview. Design approved with 3 user adjustments.

### User Adjustments (incorporated)

1. **Phase 2 coordinator.data shape**: TripSensor reads SU trip by `trip_id` from `coordinator.data["recurring_trips"][trip_id]` or `coordinator.data["punctual_trips"][trip_id]`, NOT directly from trip_manager
2. **Phase 2 async_add_entities in entry.runtime_data from day one**: Not `hass.data[DOMAIN]`, use `entry.runtime_data.async_add_entities` — avoids migrating in Phase 4
3. **Phase 0 adds 2 more tests**: `test_no_duplicate_sensors_after_reload` + `test_two_vehicles_no_unique_id_collision`

---

## Phase 0: Characterization Tests (6 tests)

**Tier 1 — Entity Registry lifecycle tests (REQUIRED before refactor)**

| Test | File | What it verifies | Expected today |
|------|------|-------------------|-----------------|
| `test_sensor_unique_id_exists_after_setup` | `tests/test_entity_registry.py` | 8 sensors have unique_id | FAIL (missing) |
| `test_sensor_removed_after_unload` | `tests/test_entity_registry.py` | 0 sensors after unload | FAIL (orphans remain) |
| `test_trip_sensor_created_in_registry_after_add` | `tests/test_entity_registry.py` | TripSensor in registry after add | FAIL (orphan object) |
| `test_trip_sensor_removed_from_registry_after_delete` | `tests/test_entity_registry.py` | Registry clean after delete | FAIL (zombie) |
| `test_no_duplicate_sensors_after_reload` | `tests/test_entity_registry.py` | 8 sensors (not 16) after reload | FAIL (duplicates) |
| `test_two_vehicles_no_unique_id_collision` | `tests/test_entity_registry.py` | All unique_ids unique | FAIL (collision) |

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

### FR-6: async_add_entities in entry.runtime_data

**Requirement**: Store `async_add_entities` callable in `entry.runtime_data.async_add_entities` from day one (Phase 2), NOT in `hass.data`.

```python
@dataclass
class EVTripRuntimeData:
    coordinator: TripPlannerCoordinator
    trip_manager: TripManager
    async_add_entities: Callable[[list[SensorEntity], bool], None] = None

# During async_setup_entry:
entry.runtime_data = EVTripRuntimeData(
    coordinator=coordinator,
    trip_manager=trip_manager,
    async_add_entities=async_add_entities,  # ← Passed from platform setup
)
```

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

### FR-10: EmhassDeferrableLoadSensor is Sole Source of Truth

**Requirement**: `EmhassDeferrableLoadSensor` remains as-is (already has `unique_id`, already is `SensorEntity`). `async_update()` ensures `async_schedule_update_ha_state()` is called after attribute updates.

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
| **Phase 2** | TripSensor created in registry via `entry.runtime_data.async_add_entities`; deleted via `er.async_remove()` |
| **Phase 3** | EMHASS sensor updates via CoordinatorEntity only (no `async_set` path) |
| **Phase 4** | `__init__.py` < 150 lines, services extracted, `entry.runtime_data` used |
| **Phase 5** | Zero legacy fallbacks, zero MagicMock in production, DEBUG logs |

---

## Non-Goals (Explicitly Out of Scope)

- E2E test modifications (Tier 2 tests untouched)
- `hass.states.async_get()` integration tests (Tier 3, deferred)
- Frontend panel changes (handled separately if needed)
- EMHASS computation logic (only lifecycle, not the algorithm)