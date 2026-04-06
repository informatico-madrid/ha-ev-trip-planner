# Design: regression-orphaned-sensors-ha-core-investigation

## Overview

Full architectural refactor of `ha-ev-trip-planner` following CODEGUIDELINESia.md v2 (12 gaps). Fixes 3 critical bugs: duplicate sensors (no unique_id), TripSensor orphan objects, and EMHASS dual-writing path. 5-phase approach starting with characterization tests.

**Approach**: Bottom-up phased refactor — safety net first, then core architecture, then peripheral fixes.

---

## Architecture

### Target File Structure

```
custom_components/ev_trip_planner/
├── __init__.py              # <150 lines: lifecycle only
├── definitions.py            # NEW: TripSensorEntityDescription + TRIP_SENSORS
├── coordinator.py           # NEW: TripPlannerCoordinator(DataUpdateCoordinator)
├── sensor.py                # TripPlannerSensor + EmhassDeferrableLoadSensor + TripSensor
├── services.py              # NEW: extracted from __init__.py
├── emhass_adapter.py       # MODIFIED: remove async_set, use coordinator.refresh
├── trip_manager.py          # KEPT: business logic (minimal changes)
├── config_flow.py           # KEPT: with version=2 migration
├── diagnostics.py           # NEW: async_get_config_entry_diagnostics
└── ...
```

### Single Data Flow Path

```
Service call (add_trip / remove_trip)
    ↓
services.py handler
    ↓
trip_manager.async_X_trip()
    ↓
entry.runtime_data.coordinator.async_request_refresh()
    ↓
coordinator._async_update_data() → updates coordinator.data
    ↓
CoordinatorEntity listeners notified automatically
    ↓
TripPlannerSensor.native_value reads coordinator.data
    ↓
async_write_ha_state() → HA UI updated
```

**No exceptions. No bypassing. No direct trip_manager calls from sensors.**

---

## Phase 0: Characterization Tests

### Tests to Write (6 tests - all FAIL today)

| Test | Verify | Expected Today |
|------|--------|----------------|
| `test_sensor_unique_id_exists_after_setup` | 8 sensors have unique_id in registry | FAIL |
| `test_sensor_removed_after_unload` | 0 sensors after async_unload | FAIL |
| `test_trip_sensor_created_in_registry_after_add` | TripSensor appears in registry after add_trip service | FAIL |
| `test_trip_sensor_removed_from_registry_after_delete` | Registry clean after delete_trip | FAIL |
| `test_no_duplicate_sensors_after_reload` | 8 sensors (not 16) after config_entry reload | FAIL |
| `test_two_vehicles_no_unique_id_collision` | All unique_ids globally unique | FAIL |

### Test Location

```python
# tests/test_entity_registry.py — NEW file
import pytest
from homeassistant.helpers import entity_registry as er

async def test_sensor_unique_id_exists_after_setup(hass, config_entry):
    """Each sensor must have unique_id in Entity Registry."""
    await hass.config_entries.async_setup(config_entry.entry_id)
    er = er.async_get(hass)
    entries = er.async_entries_for_config_entry(config_entry.entry_id)
    assert len(entries) == 8  # 7 TripPlanner + 1 Emhass
    for entry in entries:
        assert entry.unique_id is not None

# ... 5 more tests
```

### Test Strategy

- **Phase 0 tests define "done"** — When all 6 pass, Phase 1-5 are verified
- **Run after each phase** — Ensure no regression
- **Existing E2E untouched** — 16 tests in Tier 2 remain as safety net

---

## Phase 1: definitions.py + Base Architecture

### Component: definitions.py (NEW)

```python
# custom_components/ev_trip_planner/definitions.py
from dataclasses import dataclass
from homeassistant.components.sensor import SensorEntityDescription, SensorStateClass
from typing import Callable

@dataclass(frozen=True)
class TripSensorEntityDescription(SensorEntityDescription):
    value_fn: Callable[[dict], Any] = lambda data: None
    attrs_fn: Callable[[dict], dict] = lambda data: {}
    restore: bool = False

TRIP_SENSORS: tuple[TripSensorEntityDescription, ...] = (
    TripSensorEntityDescription(
        key="recurring_trips_count",
        translation_key="recurring_trips_count",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: len(data.get("recurring_trips", {})),
    ),
    TripSensorEntityDescription(
        key="punctual_trips_count",
        translation_key="punctual_trips_count",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: len(data.get("punctual_trips", {})),
    ),
    TripSensorEntityDescription(
        key="trips_list",
        translation_key="trips_list",
        value_fn=lambda data: str(list(data.get("recurring_trips", {}).keys())),
    ),
    TripSensorEntityDescription(
        key="kwh_needed_today",
        translation_key="kwh_needed_today",
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda data: data.get("kwh_today", 0.0),
        restore=True,
    ),
    TripSensorEntityDescription(
        key="hours_needed_today",
        translation_key="hours_needed_today",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.get("hours_today", 0.0),
        restore=True,
    ),
    TripSensorEntityDescription(
        key="next_trip",
        translation_key="next_trip",
        value_fn=lambda data: data.get("next_trip", {}).get("id"),
        restore=True,
    ),
    TripSensorEntityDescription(
        key="next_deadline",
        translation_key="next_deadline",
        value_fn=lambda data: data.get("next_trip", {}).get("_deadline"),
        restore=True,
    ),
)
```

### Component: sensor.py — Single TripPlannerSensor Class

```python
# custom_components/ev_trip_planner/sensor.py
class TripPlannerSensor(CoordinatorEntity[TripPlannerCoordinator], SensorEntity):
    def __init__(
        self,
        coordinator: TripPlannerCoordinator,
        vehicle_id: str,
        description: TripSensorEntityDescription,
    ):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{vehicle_id}_{description.key}"  # R-01
        self._vehicle_id = vehicle_id
        self.entity_description = description

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._vehicle_id)},
            name=f"EV Trip Planner {self._vehicle_id}",
            entry_type=DeviceEntryType.SERVICE,
        )

    @property
    def native_value(self):
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self):
        if self.coordinator.data is None:
            return {}
        return self.entity_description.attrs_fn(self.coordinator.data)
```

### Changes Summary

| Before | After |
|--------|-------|
| 7+ sensor classes (RecurringTripsCountSensor, etc.) | 1 TripPlannerSensor class |
| No `_attr_unique_id` | `_attr_unique_id = f"{DOMAIN}_{vehicle_id}_{description.key}"` |
| `SensorEntity` + manual `async_update()` | `CoordinatorEntity` + `coordinator.data` read |
| MagicMock for None coordinator | `raise ValueError` if None |

---

## Phase 2: TripSensor Lifecycle

### Component: TripSensor with CoordinatorEntity

```python
# coordinator.data shape
{
    "recurring_trips": {
        "trip_abc": {"id": "trip_abc", "tipo": "recurrente", "estado": "active", ...},
        "trip_def": {"id": "trip_def", "tipo": "recurrente", "estado": "active", ...},
    },
    "punctual_trips": {"trip_xyz": {...}},
    "kwh_today": 12.5,
    "hours_today": 1.2,
    "next_trip": {...},
}

class TripSensor(CoordinatorEntity[TripPlannerCoordinator], SensorEntity):
    def __init__(self, coordinator, vehicle_id, trip_id, trip_data):
        super().__init__(coordinator)
        self._trip_id = trip_id
        self._attr_unique_id = f"{DOMAIN}_{vehicle_id}_trip_{trip_id}"

    @property
    def native_value(self):
        trips = self.coordinator.data.get("recurring_trips", {})
        trip = trips.get(self._trip_id)
        if not trip:
            trips = self.coordinator.data.get("punctual_trips", {})
            trip = trips.get(self._trip_id)
        return trip.get("estado", "pendiente") if trip else None
```

### Component: entry.runtime_data with async_add_entities

```python
# __init__.py
@dataclass
class EVTripRuntimeData:
    coordinator: TripPlannerCoordinator
    trip_manager: TripManager
    async_add_entities: Callable[[list[SensorEntity], bool], None] = None

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # ... coordinator and trip_manager creation ...
    entry.runtime_data = EVTripRuntimeData(
        coordinator=coordinator,
        trip_manager=trip_manager,
        async_add_entities=async_add_entities,  # Passed from platform setup
    )
```

### Component: Delete with Registry Cleanup

```python
async def async_remove_trip(hass, entry, trip_id):
    # 1. Delete from trip_manager
    await entry.runtime_data.trip_manager.async_delete_trip(trip_id)

    # 2. Clean Entity Registry
    entity_registry = er.async_get(hass)
    for entity_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        if trip_id in entity_entry.unique_id:
            entity_registry.async_remove(entity_entry.entity_id)

    # 3. Trigger refresh
    entry.runtime_data.coordinator.async_request_refresh()
```

---

## Phase 3: EMHASS Single Path

### Remove async_set from emhass_adapter.py

**BEFORE** (emhass_adapter.py):
```python
hass.states.async_set(
    sensor_id, "ready",
    {"power_profile_watts": profile, "deferrables_schedule": schedule, "entry_id": self.entry_id}
)
```

**AFTER** (emhass_adapter.py):
```python
# REMOVED: all hass.states.async_set() calls

# publish_deferrable_loads() now does:
# 1. Updates internal state
# 2. Calls: entry.runtime_data.coordinator.async_request_refresh()
```

### EmhassDeferrableLoadSensor (no changes needed)

`EmhassDeferrableLoadSensor` already:
- Has `_attr_unique_id = f"emhass_perfil_diferible_{entry_id}"`
- Inherits from `SensorEntity`
- Has `async_update()` method

Just needs to be sole writer — no more `publish_deferrable_loads()` bypassing it.

---

## Phase 4: __init__.py Extraction

### Target: < 150 Lines

```python
# __init__.py — FINAL STATE
PLATFORMS = ["sensor", "binary_sensor", "switch", "number"]  # adjust as needed

@dataclass
class EVTripRuntimeData:
    coordinator: TripPlannerCoordinator
    trip_manager: TripManager
    async_add_entities: Callable[[list[SensorEntity], bool], None] = None

type EVTripConfigEntry = ConfigEntry[EVTripRuntimeData]

async def async_setup_entry(hass: HomeAssistant, entry: EVTripConfigEntry) -> bool:
    """Set up integration from config entry."""
    # Create coordinator, trip_manager
    # entry.runtime_data = EVTripRuntimeData(...)
    # await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: EVTripConfigEntry) -> bool:
    """Unload config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Remove config entry."""
    # entity_registry cleanup + storage cleanup
    pass

async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entry."""
    # Entity Registry migration if needed
    return True
```

### Extract to services.py

```python
# services.py — EXTRACTED from __init__.py
async def handle_add_trip(hass, entry, call.data):
    trip_manager = entry.runtime_data.trip_manager
    coordinator = entry.runtime_data.coordinator

    await trip_manager.async_add_trip(call.data["trip_data"])
    await coordinator.async_request_refresh()

# Register in __init__.py:
hass.services.async_register(DOMAIN, "add_trip", handle_add_trip, schemas.ADD_TRIP_SCHEMA)
```

---

## Phase 5: Global Cleanup

### Remove Legacy Patterns

| Pattern | Replace With |
|---------|--------------|
| `hass.data[DATA_RUNTIME][namespace]["trip_sensors"]` | `entry.runtime_data` |
| `f"ev_trip_planner_{entry_id}"` | `entry.entry_id` |
| `f"{DOMAIN}_{entry_id}"` | `entry.entry_id` |
| `from unittest.mock import MagicMock` | `raise ValueError` if None |

### Log Level Correction

```python
# REMOVE: _LOGGER.warning("=== async_setup_entry START ===")
# REMOVE: _LOGGER.warning("=== _get_manager - runtime_data keys: %s ===")

# REPLACE with:
_LOGGER.debug("async_setup_entry start vehicle=%s", vehicle_id)  # flow normal
_LOGGER.info("Integration setup complete vehicle=%s", vehicle_id)  # event important
_LOGGER.warning("Coordinator failed, will retry: %s", err)  # recoverable anomaly
_LOGGER.error("Cannot initialize trip_manager: %s", err)  # critical
```

---

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Phase 0 characterization tests first | Without tests, refactoring risks regressions |
| Phase 1 definitions.py before services | Sensor architecture is foundation; services depend on it |
| entry.runtime_data from day one (Phase 2) | Avoids migrating from hass.data later; HA-promoted pattern |
| TripSensor reads from coordinator.data by trip_id | Enforces single data flow; trip_manager is persistence layer only |
| EMHASS: remove async_set, not rebuild | EmhassDeferrableLoadSensor already correct; just needs to be sole writer |
| __init__.py extraction last | Cosmetic but critical for long-term maintainability |

---

## Files Summary

| Phase | Create | Modify | Delete |
|-------|--------|--------|--------|
| Phase 0 | `tests/test_entity_registry.py` | — | — |
| Phase 1 | `definitions.py`, `coordinator.py` | `sensor.py` | — |
| Phase 2 | — | `__init__.py`, `services.py` (extract) | — |
| Phase 3 | — | `emhass_adapter.py` | — |
| Phase 4 | `services.py` (complete) | `__init__.py`, `config_flow.py` | — |
| Phase 5 | `diagnostics.py` | `__init__.py` cleanup | — |

---

## Verification

| Phase | Verification Command |
|-------|---------------------|
| Phase 0 | `.venv/bin/pytest tests/test_entity_registry.py -v` (6 tests FAIL) |
| Phase 1 | `.venv/bin/pytest tests/test_sensor.py tests/test_entity_registry.py -v` |
| Phase 2 | `.venv/bin/pytest tests/test_entity_registry.py -v -k "trip"` |
| Phase 3 | `.venv/bin/pytest tests/test_emhass_adapter.py -v` |
| Phase 4 | `.venv/bin/pytest tests/test_init.py -v` |
| Phase 5 | Full suite + `pylint --disable=all --enable=E,F` |

---

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Phase 1 refactor breaks existing sensors | Phase 0 tests catch immediately |
| TripSensor registry changes affect other sensors | Phase 2 isolated from Phase 1 |
| EMHASS loses data during transition | Phase 3 is cutover (remove async_set, add refresh call) |
| __init__.py extraction causes regression | All phases verified by Phase 0 tests |
| 3-layer TripSensor bug harder to test | Add specific test for each layer (add, remove) |