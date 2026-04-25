# EV Trip Planner — Code Rules and Architecture (v2)
## PRIORITY NOTICE !!!
tasks.md is the source of truth for implementation order.
CODEGUIDELINESia.md is architectural reference. If they directly conflict, apply tasks.md but verify that no
requirement from CODEGUIDELINES is lost.
> Mandatory reference document for any AI agent or developer.
> Version: 2026-04-v2 · Multi-integration analysis: Bambu Lab (2085★), Bermuda (1695★), Battery Notes (1028★), Versatile Thermostat (1021★), Nordpool (Platinum)

***

## 1. Executive Summary of Critical Gaps

This analysis compared `ha-ev-trip-planner` against five active HACS reference integrations identified in 2025-2026. **12 critical gaps** were identified organized into 4 categories. Each gap has a code rule that closes it. THIS IS THE GENERAL GUIDE. IN VERY DETERMINED CASES EXCEPTIONS MAY BE MADE BUT THEY MUST BE JUSTIFIED AND DOCUMENTED IN THE CODEBASE WITH AN EXPLANATORY COMMENT AND APPROVED BY THE HUMAN.

| ID | Category | Severity | Visible Impact |
|---|---|---|---|
| | G-01 | Entity Identity | 🔴 Critical | Duplicate sensors on reinstall |
| | G-02 | Update Cycle | 🔴 Critical | Sensors don't reflect changes |
| | G-03 | Entity Architecture | 🔴 Critical | Code impossible to maintain |
| | G-04 | Integration Lifecycle | 🔴 Critical | Zombie sensors after uninstall |
| | G-05 | Runtime Data Storage | 🟠 High | Random failures after restarts |
| | G-06 | Test Code in Production | 🔴 Critical | Invented sensor states |
| | G-07 | `SensorEntityDescription` Pattern | 🟠 High | Duplicated code × each sensor |
| | G-08 | `RestoreEntity` / `RestoreSensor` | 🟠 High | Sensors show `Unknown` after HA restart |
| | G-09 | Incomplete `async_migrate_entry` | 🟠 High | Silently incorrect migrations |
| | G-10 | Missing `diagnostics.py` | 🟡 Medium | Impossible to debug in production |
| | G-11 | `ConfigEntryNotReady` Not Raised | 🟡 Medium | Silent setup errors |
| | G-12 | Separation of Responsibilities | 🔴 Critical | God Object of 5000+ lines |

***

## 2. Reference Integration Analysis

### 2.1 · ha-bambulab (2085★, updated daily)

**Key pattern missing in ev-trip-planner: `SensorEntityDescription` + `definitions.py`**

Bambu Lab separates sensor **definition** from sensor **implementation**. All sensors share a single base class and their differences are expressed as data, not as code.

```python
# bambu_lab/definitions.py
@dataclass(frozen=True)
class BambuLabSensorEntityDescription(SensorEntityDescription):
    """Extended sensor descriptor."""
    value_fn: Callable[[BambuDataUpdateCoordinator], StateType] = None
    exists_fn: Callable[[BambuDataUpdateCoordinator], bool] = lambda _: True
    is_restoring: bool = False

PRINTER_SENSORS: tuple[BambuLabSensorEntityDescription, ...] = (
    BambuLabSensorEntityDescription(
        key="stage",
        translation_key="stage",
        value_fn=lambda coordinator: coordinator.get_model().info.gcode_state,
        exists_fn=lambda coordinator: coordinator.get_model().has_full_printer_data,
        is_restoring=True,
    ),
    # ...dozens of sensors defined as data, NOT as classes
)
```

```python
# bambu_lab/sensor.py — A SINGLE class for all sensors
class BambuLabSensor(BambuLabEntity, SensorEntity):
    def __init__(self, coordinator, description: BambuLabSensorEntityDescription):
        self._attr_unique_id = f"{printer.serial}_{description.key}"  # ← ALWAYS present
        self.entity_description = description  # ← HA manages name, unit, device_class
    
    @property
    def native_value(self):
        return self.entity_description.value_fn(self.coordinator)  # ← Reads from coordinator
```

**ev-trip-planner has 8+ separate classes** (`RecurringTripsCountSensor`, `PunctualTripsCountSensor`, etc.) when it should have **1 base class + a definitions file**.

***

### 2.2 · Bermuda (1695★, updated yesterday)

**Key pattern missing: `entry.runtime_data` with `@dataclass` + `TypeAlias` of ConfigEntry**

```python
# bermuda/__init__.py
from dataclasses import dataclass

type BermudaConfigEntry = ConfigEntry[BermudaData]  # Typed TypeAlias

@dataclass
class BermudaData:
    """Runtime data stored in config_entry.runtime_data."""
    coordinator: BermudaDataUpdateCoordinator

async def async_setup_entry(hass: HomeAssistant, entry: BermudaConfigEntry) -> bool:
    coordinator = BermudaDataUpdateCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()  # ← Raises ConfigEntryNotReady if it fails
    entry.runtime_data = BermudaData(coordinator)  # ← Single line, typed, no strings
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: BermudaConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    # ← Does NOT need to clean hass.data because it used runtime_data
```

**ev-trip-planner uses** `DATA_RUNTIME = f"{DOMAIN}_runtime_data"` as a global string, with multiple namespaces (`f"{DOMAIN}_{entry_id}"`, `f"ev_trip_planner_{entry_id}"`) and nested legacy fallbacks. This causes random failures when HA tries to access data that was freed too early.

**Additional Bermuda pattern: `async_migrate_entries` for Entity Registry**

```python
# bermuda/__init__.py
from homeassistant.helpers.entity_registry import async_migrate_entries

async def async_migrate_entry(hass, config_entry):
    # Migrate existing entity unique_ids in the Entity Registry
    async def migrate_unique_id(entity_entry):
        if entity_entry.unique_id.startswith("OLD_PREFIX"):
            return {"new_unique_id": entity_entry.unique_id.replace("OLD_PREFIX", "NEW_PREFIX")}
    await async_migrate_entries(hass, config_entry.entry_id, migrate_unique_id)
    return True
```

ev-trip-planner has an `async_migrate_entry` that only migrates `config_entry.data` but **never migrates entity `unique_id`s in the Entity Registry**. If the `unique_id` format changes between versions, old entities become zombies.

***

### 2.3 · Battery Notes (1028★, updated yesterday)

**Key pattern missing: `diagnostics.py`**

Battery Notes implements `diagnostics.py` — a standard HA module that allows users to download a diagnostic report from the UI without accessing logs.

```python
# battery_notes/diagnostics.py
from homeassistant.components.diagnostics import async_redact_data

TO_REDACT = {"serial_number", "mac_address"}

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    """Returns diagnostic data for display in HA UI."""
    coordinator = entry.runtime_data.coordinator
    return async_redact_data({
        "config_entry": dict(entry.data),
        "coordinator_data": coordinator.data,
        "entity_count": len(coordinator.entities),
    }, TO_REDACT)
```

ev-trip-planner does not have `diagnostics.py`. When a user reports a bug, there is no standard way to get internal state without hacking the system.

**Additional pattern: `ConfigSubentry` for dynamic elements**

Battery Notes uses `ConfigSubentry` (available since HA 2024.x) to represent each battery as a config subentry. This solves the exact same problem ev-trip-planner has with trips: **user-created dynamic elements that need their own lifecycle**.

```python
# Each trip could be a ConfigSubentry with its own unique_id
subentry = ConfigSubentry(
    subentry_type="trip",
    unique_id=f"trip_{trip_id}",
    title=trip_name,
    data=trip_data,
)
hass.config_entries.async_add_subentry(config_entry, subentry)
```

***

### 2.4 · Versatile Thermostat (1021★)

**Key pattern missing: `RestoreSensor` / `RestoreEntity`**

Versatile Thermostat restores the last known state of its sensors after an HA restart, avoiding the initial `Unknown` state.

```python
from homeassistant.helpers.restore_state import RestoreEntity, RestoreSensor

class VersatileThermostatSensor(CoordinatorEntity, RestoreSensor):
    async def async_added_to_hass(self) -> None:
        """Restores state when added to HA."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_sensor_data()
        if last_state:
            self._attr_native_value = last_state.native_value
            # Sensor shows previous value until first real update
```

ev-trip-planner does not implement `RestoreSensor`. Every time HA restarts, all sensors show `Unknown` until the first polling cycle — which can take minutes if the coordinator has a long `update_interval`.

***

## 3. Code Rules (Complete Version)

### R-01 · Every Sensor Must Have `_attr_unique_id` — CRITICAL

```python
# ❌ CURRENT — without unique_id (produces duplicates)
class RecurringTripsCountSensor(TripPlannerSensor):
    def __init__(self, vehicle_id, coordinator):
        super().__init__(...)
        self._attr_name = f"{vehicle_id} recurring trips count"
        # ← NO unique_id

# ✅ CORRECT
class TripPlannerSensor(CoordinatorEntity[TripPlannerCoordinator], SensorEntity):
    def __init__(self, coordinator, vehicle_id, description: TripSensorEntityDescription):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{vehicle_id}_{description.key}"
        self.entity_description = description
```

### R-02 · Use `SensorEntityDescription` + `definitions.py` — CRITICAL

Remove the 8 separate sensor classes. Replace with a base class + descriptors.

```python
# ev_trip_planner/definitions.py
from dataclasses import dataclass
from homeassistant.components.sensor import SensorEntityDescription

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
        value_fn=lambda data: len(data.get("recurring_trips", [])),
    ),
    TripSensorEntityDescription(
        key="kwh_needed_today",
        translation_key="kwh_needed_today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        value_fn=lambda data: data.get("kwh_today", 0.0),
        restore=True,
    ),
    # ... all other sensors as data
)
```

```python
# ev_trip_planner/sensor.py — A SINGLE class
class TripPlannerSensor(CoordinatorEntity[TripPlannerCoordinator], SensorEntity):
    def __init__(self, coordinator, vehicle_id, description):
        super().__init__(coordinator)
        self._attr_unique_id = f"{DOMAIN}_{vehicle_id}_{description.key}"
        self._vehicle_id = vehicle_id
        self.entity_description = description

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

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._vehicle_id)},
            name=f"EV Trip Planner {self._vehicle_id}",
            entry_type=DeviceEntryType.SERVICE,
        )
```

### R-03 · Use `entry.runtime_data` with Typed `@dataclass` — CRITICAL

```python
# ev_trip_planner/__init__.py
from dataclasses import dataclass
from homeassistant.config_entries import ConfigEntry

type EVTripConfigEntry = ConfigEntry[EVTripRuntimeData]

@dataclass
class EVTripRuntimeData:
    coordinator: TripPlannerCoordinator
    trip_manager: TripManager

async def async_setup_entry(hass: HomeAssistant, entry: EVTripConfigEntry) -> bool:
    trip_manager = TripManager(hass, entry)
    coordinator = TripPlannerCoordinator(hass, entry, trip_manager)
    
    await coordinator.async_config_entry_first_refresh()  # Raises ConfigEntryNotReady if it fails
    
    entry.runtime_data = EVTripRuntimeData(
        coordinator=coordinator,
        trip_manager=trip_manager,
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: EVTripConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    # ← Does NOT need to clean hass.data
```

Completely remove `DATA_RUNTIME` and all `f"{DOMAIN}_{entry_id}"` namespaces.

### R-04 · `async_remove_entry` Cleans Entity Registry and uses runtime_data — CRITICAL

```python
async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Completely removes all traces of the integration."""
    from homeassistant.helpers import entity_registry as er
    
    # 1. Clean Entity Registry
    entity_registry = er.async_get(hass)
    for entity_entry in er.async_entries_for_config_entry(entity_registry, entry.entry_id):
        entity_registry.async_remove(entity_entry.entity_id)
    
    # 2. Clean trip_manager storage
    if hasattr(entry, 'runtime_data') and entry.runtime_data:
        await entry.runtime_data.trip_manager.async_remove_all_data()
    
    # 3. Remove input helpers if they exist
    # (cleanup code for input_datetime, etc.)
```

### R-05 · Implement `RestoreSensor` for Sensors with Valuable Data — HIGH

```python
# For energy sensors, next trip, etc.
from homeassistant.helpers.restore_state import RestoreSensor

class TripPlannerSensor(CoordinatorEntity[TripPlannerCoordinator], RestoreSensor):
    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        # Restore previous state to avoid Unknown after restart
        last_data = await self.async_get_last_sensor_data()
        if last_data and self.coordinator.data is None:
            self._attr_native_value = last_data.native_value
```

Only apply to sensors where showing the previous value is better than `Unknown`:
- `kwh_needed_today`, `hours_needed_today`, `next_trip`, `next_deadline`

### R-06 · No `unittest.mock` in Production — CRITICAL

```python
# ❌ ABSOLUTELY PROHIBITED in any file outside tests/
from unittest.mock import MagicMock

# ✅ CORRECT: If coordinator is None, it's a bug. Fail fast.
if coordinator is None:
    raise ConfigEntryError(f"coordinator cannot be None for vehicle {vehicle_id}")
```

### R-07 · Implement `diagnostics.py` — MEDIUM (required for HACS Quality)

```python
# ev_trip_planner/diagnostics.py
from homeassistant.components.diagnostics import async_redact_data

TO_REDACT = {"vehicle_name", "license_plate", "home_address"}

async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict[str, Any]:
    runtime = entry.runtime_data
    return async_redact_data({
        "config_version": entry.version,
        "coordinator_last_update": str(runtime.coordinator.last_update_success),
        "coordinator_data_keys": list(runtime.coordinator.data.keys()) if runtime.coordinator.data else [],
        "trip_count": {
            "recurring": len(runtime.coordinator.data.get("recurring_trips", [])) if runtime.coordinator.data else 0,
            "punctual": len(runtime.coordinator.data.get("punctual_trips", [])) if runtime.coordinator.data else 0,
        },
    }, TO_REDACT)
```

Add `"diagnostics"` to `manifest.json`:
```json
{
  "quality_scale": "silver"
}
```

### R-08 · `async_migrate_entry` Must Migrate Entity Registry — HIGH

```python
from homeassistant.helpers.entity_registry import async_migrate_entries

async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    current_version = entry.version
    
    if current_version < 2:
        # Migrate unique_id format: "ev_trip_planner_kwh_today" → "ev_trip_planner_{vehicle_id}_kwh_today"
        vehicle_id = entry.data.get("vehicle_id", "default")
        
        async def migrate_unique_id(entity_entry):
            old = entity_entry.unique_id
            if old.startswith(f"{DOMAIN}_") and f"_{vehicle_id}_" not in old:
                suffix = old.removeprefix(f"{DOMAIN}_")
                return {"new_unique_id": f"{DOMAIN}_{vehicle_id}_{suffix}"}
        
        await async_migrate_entries(hass, entry.entry_id, migrate_unique_id)
        hass.config_entries.async_update_entry(entry, version=2)
    
    return True
```

### R-09 · `ConfigEntryNotReady` Mandatory in `async_setup_entry` — MEDIUM

```python
from homeassistant.exceptions import ConfigEntryNotReady

async def async_setup_entry(hass, entry):
    coordinator = TripPlannerCoordinator(hass, entry, trip_manager)
    
    try:
        await coordinator.async_config_entry_first_refresh()
        # ← async_config_entry_first_refresh raises ConfigEntryNotReady automatically
        # if _async_update_data raises UpdateFailed or any exception
    except ConfigEntryNotReady:
        raise  # Re-raise to let HA retry setup
```

If the first refresh fails, HA will retry setup automatically with exponential backoff. Without `ConfigEntryNotReady`, setup fails silently and sensors remain in `Unavailable` state permanently.

### R-10 · `__init__.py` Lifecycle Only (<150 lines) — CRITICAL

The `__init__.py` file can only contain:
- `PLATFORMS` constant
- `EVTripRuntimeData` dataclass
- `async_setup(hass, config)` (if exists)
- `async_setup_entry(hass, entry)`
- `async_unload_entry(hass, entry)`
- `async_remove_entry(hass, entry)`
- `async_migrate_entry(hass, entry)`

**Everything else goes in its own module:**
- Service handlers → `services.py`
- Coordinator logic → `coordinator.py` (create this file)
- Dashboard helpers → `dashboard.py` (already exists, keep)
- Sensor definitions → `definitions.py` (create)

### R-11 · Logs with Correct Level — MEDIUM

```python
# ❌ PROHIBITED — WARNING spam in normal flow
_LOGGER.warning("=== async_setup_entry START === vehicle=%s", vehicle_id)
_LOGGER.warning("=== _get_manager - runtime_data keys: %s ===", ...)

# ✅ CORRECT
_LOGGER.debug("async_setup_entry start vehicle=%s", vehicle_id)  # normal flow
_LOGGER.info("Integration setup complete vehicle=%s", vehicle_id)  # important event
_LOGGER.warning("Coordinator failed, will retry: %s", err)  # recoverable anomalous situation
_LOGGER.error("Cannot initialize trip_manager: %s", err)  # critical failure
```

### R-12 · No Duplicating Classes for Test Compatibility — CRITICAL

```python
# ❌ PROHIBITED — compatibility aliases that diverge from real implementation
class RecurringTripsCountSensor(TripPlannerSensor):
    """Sensor for counting recurring trips (alias for backward compatibility)."""
    # ... completely different implementation from base class

# ✅ CORRECT — one class, tests use the same implementation
# If tests fail because the interface changed, update the tests
```

***

## 4. Comparative Gap Table vs. Reference Integrations

| Pattern | ev-trip-planner | Bambu Lab | Bermuda | Battery Notes | Versatile Thermostat |
|---|---|---|---|---|---|
| `_attr_unique_id` on all sensors | ❌ 7/8 missing | ✅ | ✅ | ✅ | ✅ |
| `CoordinatorEntity` as base | ❌ | ✅ | ✅ | ✅ | ✅ |
| `SensorEntityDescription` + `definitions.py` | ❌ | ✅ | ✅ | ✅ | ❌ |
| Typed `entry.runtime_data` | ❌ uses global string | ✅ | ✅ | ✅ | ❌ partial |
| `RestoreSensor` / `RestoreEntity` | ❌ | ✅ | ✅ | ✅ | ✅ |
| `diagnostics.py` | ❌ | ✅ | ❌ | ✅ | ❌ |
| `async_migrate_entry` + Entity Registry | ❌ only config data | ❌ | ✅ | ✅ | ❌ |
| `ConfigEntryNotReady` on first refresh | ✅ partial | ✅ | ✅ | ✅ | ✅ |
| `__init__.py` < 200 lines | ❌ 5000+ | ✅ ~460 | ✅ ~140 | ✅ ~360 | ✅ ~210 |
| Zero `unittest.mock` imports | ❌ | ✅ | ✅ | ✅ | ✅ |
| No compatibility alias classes | ❌ | ✅ | ✅ | ✅ | ✅ |
| Clean Entity Registry on remove | ❌ | ✅ via HA | ✅ via HA | ✅ explicit | ✅ via HA |

***

## 5. Target Architecture

```
custom_components/ev_trip_planner/
├── __init__.py          # <150 lines: ONLY lifecycle (setup/unload/remove/migrate)
│                        # Exports: EVTripRuntimeData, EVTripConfigEntry
├── coordinator.py       # TripPlannerCoordinator(DataUpdateCoordinator) — CREATE
├── definitions.py       # TRIP_SENSORS tuple[TripSensorEntityDescription] — CREATE
├── diagnostics.py       # async_get_config_entry_diagnostics — CREATE
├── sensor.py            # One class: TripPlannerSensor(CoordinatorEntity, RestoreSensor)
├── services.py          # Service handlers + registration — EXTRACT from __init__.py
├── trip_manager.py      # Business logic (keep, few changes)
├── config_flow.py       # Config flow (keep, add version=2)
├── const.py             # Constants (keep)
└── ...rest unchanged
```

**Correct data flow (only valid path):**

```
HA Service Invoked (add_trip / remove_trip / etc.)
        │
        ▼
services.py handler
        │  only calls:
        ▼
trip_manager.async_add_trip(...)
        │
        ▼
coordinator.async_refresh()   ← only call that triggers updates
        │
        ▼
coordinator._async_update_data()
        │  builds coordinator.data = {...}
        ▼
CoordinatorEntity listeners notified automatically
        │
        ▼
TripPlannerSensor.native_value reads coordinator.data
        │
        ▼
async_write_ha_state() → HA UI updated
```

***

## 6. Refactoring Priority Order

Implement in this order to maximize stability with minimum changes:

1. **Sprint 1 (Critical — eliminates duplicates and zombies):**
   - Add `_attr_unique_id` to all existing sensors
   - Create `coordinator.py` with `TripPlannerCoordinator(DataUpdateCoordinator)`
   - Change sensor inheritance to `CoordinatorEntity`
   - Clean `unittest.mock` imports

2. **Sprint 2 (High — lifecycle stability):**
   - Migrate to `entry.runtime_data` with typed `@dataclass`
   - Refactor `__init__.py` extracting services to `services.py`
   - Implement `async_remove_entry` with Entity Registry cleanup
   - Add `ConfigEntryNotReady` in `async_config_entry_first_refresh`

3. **Sprint 3 (Medium — quality and maintainability):**
   - Create `definitions.py` with `SensorEntityDescription`
   - Consolidate 8 sensor classes into 1
   - Implement `RestoreSensor`
   - Create `diagnostics.py`
   - Migrate `async_migrate_entry` to include Entity Registry

***

## 7. PR Review Checklist

Before merging any PR:

**Entity Identity:**
- [ ] Do all `SensorEntity` have `_attr_unique_id = f"{DOMAIN}_{vehicle_id}_{description.key}"`?
- [ ] Does `device_info` use `identifiers={(DOMAIN, vehicle_id)}` consistently?

**Architecture:**
- [ ] Do sensors inherit from `CoordinatorEntity`?
- [ ] Does `native_value` read from `self.coordinator.data`, never directly from `trip_manager`?
- [ ] Are there no `async_update()` calls in sensors that use coordinator?

**Clean Code:**
- [ ] Zero `unittest.mock` imports outside `tests/`?
- [ ] No "alias" classes created for test compatibility?
- [ ] Are normal flow logs using `DEBUG`, not `WARNING`?

**Lifecycle:**
- [ ] Is `__init__.py` under 200 lines?
- [ ] Does `async_remove_entry` clean Entity Registry?
- [ ] Does `async_setup_entry` NOT clean existing storage?
- [ ] Is `entry.runtime_data` used instead of `hass.data[DATA_RUNTIME]`?

**New Code:**
- [ ] Do new sensors use `TripSensorEntityDescription` in `definitions.py`?
- [ ] Do sensors with valuable data implement `RestoreSensor`?
