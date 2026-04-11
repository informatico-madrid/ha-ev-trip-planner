---
spec: m401-emhass-hotfixes
phase: research
created: 2026-04-11T00:00:00Z
---

# Research: m401-emhass-hotfixes

## Executive Summary

Two critical EMHASS bugs. **Gap #5** has two root causes: (1) `update_charging_power()` reads `entry.data` but `OptionsFlow.async_create_entry()` writes to `entry.options`, so the new value is invisible; (2) `setup_config_entry_listener()` is never called in production code -- the listener exists but is dead code. **Gap #8** requires per-trip EMHASS sensors with lifecycle tied to trips, plus a dynamic `P_deferrable` matrix attribute on the aggregated sensor. The HA pattern for dynamic entities is well-documented (`coordinator.async_add_listener` + `async_add_entities`).

## Gap #5 Analysis: Charging Power Not Updating

### Root Cause #1: `entry.data` vs `entry.options`

**Confirmed via HA docs and code**:

| Where | Code | Stores To |
|-------|------|-----------|
| `config_flow.py:822` | `self.async_create_entry(title=vehicle_name, data=vehicle_data)` | `entry.data` |
| `config_flow.py:921` | `return self.async_create_entry(title="", data=update_data)` | `entry.options` |

The second line is in `EVTripPlannerOptionsFlowHandler` (an `OptionsFlow` subclass). Per HA docs, `OptionsFlow.async_create_entry(data=...)` writes to `entry.options`, **not** `entry.data`.

But `update_charging_power()` reads:
```python
# emhass_adapter.py:1359
new_power = entry.data.get("charging_power_kw")  # ALWAYS reads from data
```

After an options flow edit, `entry.data` is unchanged. The new `charging_power_kw` sits in `entry.options`. The listener callback fires, but the new power is never found.

**Fix**: Read from both, with `options` taking precedence:
```python
new_power = entry.options.get("charging_power_kw") or entry.data.get("charging_power_kw")
```

### Root Cause #2: Listener Never Activated

`setup_config_entry_listener()` is defined at `emhass_adapter.py:1311` but **never called in production code**.

| File | Called? |
|------|---------|
| `__init__.py` | No |
| `services.py` | No |
| `tests/test_emhass_adapter.py:679` | Yes (test only) |
| `tests/test_config_updates.py:180` | Yes (test only) |

The adapter is created at `__init__.py:118` and stored in `entry.runtime_data` at line 133, but `setup_config_entry_listener()` is never invoked. This means `_handle_config_entry_update` is never registered as a callback, so config entry updates are completely ignored.

**Fix**: Add `emhass_adapter.setup_config_entry_listener()` call in `__init__.py` after adapter creation:
```python
# After line 120 in __init__.py
emhass_adapter.setup_config_entry_listener()
```

### Root Cause #3: `_published_trips` May Be Empty

Even if the listener fires and finds the new power, it calls:
```python
await self.publish_deferrable_loads(self._published_trips, new_power)
```

`self._published_trips` is populated in `publish_deferrable_loads()` at line 539. If the listener fires before any trips are published, the list is empty, producing an all-zeros profile.

**Fix**: If `_published_trips` is empty, reload from `trip_manager`:
```python
if not self._published_trips:
    coordinator = self._get_coordinator()
    if coordinator and coordinator._trip_manager:
        recurring = await coordinator._trip_manager.async_get_recurring_trips()
        punctual = await coordinator._trip_manager.async_get_punctual_trips()
        self._published_trips = recurring + punctual
```

### Gap #5 Fix Summary

| Issue | Location | Fix |
|-------|----------|-----|
| `entry.data` vs `entry.options` | `emhass_adapter.py:1359` | Read `options` first, fallback `data` |
| Listener never activated | `__init__.py:118-120` | Add `setup_config_entry_listener()` call |
| Empty `_published_trips` | `emhass_adapter.py:1380` | Reload from trip_manager if empty |

---

## Gap #8 Analysis: Per-Trip EMHASS Sensors

### Current Architecture

```
TripManager
    └── async_generate_power_profile()  → aggregated 168-hour array
    └── async_get_recurring_trips()     → list of trips
    └── async_get_punctual_trips()      → list of trips

EMHASSAdapter
    └── publish_deferrable_loads()      → aggregated profile, caches to _cached_power_profile
    └── async_publish_deferrable_load() → per-trip params (def_total_hours, P_deferrable_nom, etc.)
    └── _index_map: {trip_id → emhass_index}  → persistent index mapping
    └── get_cached_optimization_results() → {emhass_power_profile, emhass_deferrables_schedule, emhass_status}

Coordinator (TripPlannerCoordinator)
    └── _async_update_data() → merges trip data + emhass_data
    └── data["recurring_trips"]  → {trip_id: trip_dict}
    └── data["punctual_trips"]   → {trip_id: trip_dict}

Sensors
    └── EmhassDeferrableLoadSensor → aggregated sensor (KEEP)
        └── native_value = emhass_status
        └── extra_state_attributes = {power_profile_watts, deferrables_schedule, emhass_status}
    └── TripSensor → per-trip sensor (EXISTS, for trip status)
        └── reads from coordinator.data["recurring_trips"][trip_id]
```

### What Per-Trip EMHASS Sensors Need

Each per-trip sensor must expose these EMHASS parameters (from `async_publish_deferrable_load` at line 276):

| Attribute | Type | Source |
|-----------|------|--------|
| `def_total_hours` | float | `kwh / charging_power_kw` |
| `P_deferrable_nom` | float | `charging_power_kw * 1000` |
| `def_start_timestep` | int | Start of charging window (index 0-167) |
| `def_end_timestep` | int | End of charging window / deadline |
| `power_profile_watts` | list[168] | Individual trip power profile |
| `trip_id` | str | Trip identifier |
| `emhass_index` | int | Index in EMHASS deferrable loads |
| `kwh_needed` | float | Energy needed for trip |
| `deadline` | str | ISO datetime of trip deadline |

### Dynamic Sensor Pattern (HA Best Practice)

From HA developer docs (`dynamic-devices` rule):

```python
# In async_setup_entry (sensor.py)
known_trips: set[str] = set()

def _check_trips() -> None:
    """Check for new trips and create sensors dynamically."""
    if coordinator.data is None:
        return
    current_trips = set(coordinator.data.get("recurring_trips", {}).keys())
    current_trips |= set(coordinator.data.get("punctual_trips", {}).keys())
    new_trips = current_trips - known_trips
    if new_trips:
        known_trips.update(new_trips)
        async_add_entities(
            [TripEmhassSensor(coordinator, vehicle_id, trip_id) for trip_id in new_trips]
        )

_check_trips()  # Initial creation
entry.async_on_unload(coordinator.async_add_listener(_check_trips))
```

This is the HA-recommended pattern. New trips automatically get sensors when coordinator refreshes. Removed trips' sensors are cleaned via entity_registry.

### Per-Trip Sensor Lifecycle

| Event | Action | Mechanism |
|-------|--------|-----------|
| Trip created | Create sensor | `async_add_entities` via coordinator listener |
| Trip updated | Update sensor attributes | Coordinator refresh (data-driven) |
| Trip deleted | Remove sensor | `entity_registry.async_remove` (already exists in `async_remove_trip_sensor`) |
| Trip completed | Sensor shows 0 | `power_profile_watts` all zeros, `def_total_hours` = 0 |

### Aggregated `P_deferrable` Matrix (Dynamic JSON)

User wants a single attribute that EMHASS can read as the complete `P_deferrable` matrix. This should be on the aggregated sensor:

```python
# In EmhassDeferrableLoadSensor.extra_state_attributes
"p_deferrable_matrix": [
    [0, 0, 0, 3600, 3600, ...],  # Trip 1 profile
    [0, 0, 2200, 2200, 0, ...],  # Trip 2 profile
]
```

This is a `list[list[float]]` where each inner list is a per-trip 168-hour profile. EMHASS reads this directly as `P_deferrable`.

**Jinja2 template for EMHASS config**:
```yaml
P_deferrable: {{ state_attr('sensor.emhass_perfil_diferible_VEHICLE', 'p_deferrable_matrix') }}
```

Single line, always up-to-date, no manual reconfiguration when trips change.

### Design Decision: Option A (1 sensor per trip with all attributes)

From gaps.md analysis, Option A is recommended:
- 1 `TripEmhassSensor` per trip, all EMHASS params in `extra_state_attributes`
- Reuse existing `TripSensor` pattern (CoordinatorEntity)
- Reuse existing index management from `EMHASSAdapter._index_map`

### What to Keep

- **Aggregated sensor** (`EmhassDeferrableLoadSensor`): Keep for panel weekly graph. Add `p_deferrable_matrix` attribute.
- **`EMHASSAdapter._index_map`**: Keep for stable EMHASS index assignment.
- **`EMHASSAdapter.publish_deferrable_loads()`**: Keep for aggregated profile calculation.
- **`async_create_trip_sensor` / `async_remove_trip_sensor`**: Extend or create parallel functions for EMHASS sensors.

---

## Codebase Analysis

### Existing Patterns

| Pattern | File:Line | Notes |
|---------|-----------|-------|
| CoordinatorEntity sensors | `sensor.py:57` | `TripPlannerSensor` base class |
| Per-trip sensors (TripSensor) | `sensor.py:204` | Already creates sensors per trip |
| Dynamic sensor creation | `sensor.py:435-498` | `async_create_trip_sensor` uses `async_add_entities` |
| Dynamic sensor removal | `sensor.py:554-584` | `async_remove_trip_sensor` uses entity_registry |
| `sensor_async_add_entities` stored | `sensor.py:350` | Callback saved in `runtime_data` for service use |
| EMHASS index management | `emhass_adapter.py:202-269` | `async_assign_index_to_trip`, `async_release_trip_index` |
| Per-trip EMHASS params calc | `emhass_adapter.py:276-369` | `async_publish_deferrable_load` calculates all params |
| Config entry listener | `emhass_adapter.py:1311-1344` | Defined but never called in prod |

### Dependencies

| Component | Version | Role |
|-----------|---------|------|
| Home Assistant | 2026.3.4 | Core platform |
| DataUpdateCoordinator | built-in | Sensor data refresh |
| Entity Registry | built-in | Dynamic entity management |
| `calculations.py` | internal | Pure power profile calculation functions |

### Constraints

- HA entity_registry removal is async, must be awaited
- `async_add_entities` callback must be stored at setup for service-time use (already done at `sensor.py:350`)
- Per-trip sensors need stable `unique_id` for entity_registry tracking
- Coordinator refresh interval is 30s (coordinator.py:68)
- EMHASS expects coherent arrays: all parameter arrays must have same length

---

## Feasibility Assessment

| Aspect | Assessment | Notes |
|--------|------------|-------|
| Gap #5 fix (entry.options) | **High** | 1-line fix in `update_charging_power()`, well-understood |
| Gap #5 fix (listener activation) | **High** | 1-line addition in `__init__.py` |
| Gap #5 fix (empty trips) | **High** | Small guard clause |
| Gap #8 per-trip sensors | **High** | Pattern already exists (TripSensor), HA docs confirm approach |
| Gap #8 p_deferrable_matrix | **High** | Concatenate per-trip profiles in aggregated sensor |
| Gap #8 Jinja2 config | **Medium** | Panel JS changes + documentation |

**Overall Technical Viability**: High
**Effort Estimate**: M (3-5 days)
**Risk Level**: Low-Medium (mostly extending existing patterns)

---

## Related Specs (All Merged to Main)

| Spec | PR/Commit | What It Delivered (in current main) |
|------|-----------|--------------------------------------|
| `emhass-sensor-entity-lifecycle` | #21 (`f319d66`) | Entity registry cleanup, panel deletion guard, `async_remove_trip_sensor` |
| `fix-emhass-sensor-attributes` | #25 (`41b628f`) | `device_info` uses `vehicle_id` (not `entry_id`), method routing to `publish_deferrable_loads`, sensor attribute fixes |
| `emhass-sensor-enhancement` | `a6bfdc6` | Soft-delete with 24h cooldown in `_index_map`, index stability, PR #7 |
| `emhass-integration-with-fixes` | `edc846d` | Cascade delete, sensor CRUD sync with trip lifecycle |
| `solid-refactor-coverage` | #24 (`47cc5d0`) | SOLID refactor, definitions.py, coordinator.py, diagnostics.py |

### What We DON'T Need to Reimplement (already in main)

- `_index_map` soft-delete with cooldown — from `emhass-sensor-enhancement`
- `device_info` with `vehicle_id` — from `fix-emhass-sensor-attributes`
- Correct method routing (`publish_deferrable_loads`) — from `fix-emhass-sensor-attributes`
- `async_remove_trip_sensor` using entity_registry — from `emhass-sensor-entity-lifecycle`
- Cascade delete synced with trip CRUD — from `emhass-integration-with-fixes`

### What We BUILD ON (patterns to reuse)

- `async_create_trip_sensor` / `async_remove_trip_sensor` — extend for EMHASS sensors
- `TripSensor` pattern (CoordinatorEntity per trip) — replicate for `TripEmhassSensor`
- `_index_map` stable trip-to-index mapping — use for `emhass_index` attribute
- `sensor_async_add_entities` callback stored in runtime_data — reuse for dynamic creation

---

## Quality Commands

| Type | Command | Source |
|------|---------|--------|
| Lint | `ruff check .` | Makefile lint target |
| Lint (pylint) | `pylint custom_components/ tests/` | Makefile lint target |
| TypeCheck | `mypy custom_components/ tests/ --exclude tests/ha-manual --no-namespace-packages` | Makefile mypy target |
| Unit Test | `make test` (pytest, ignores e2e) | Makefile test target |
| Test with coverage | `make test-cover` (100% coverage required) | Makefile test-cover target |
| Build | N/A (Python HA custom component) | Not applicable |
| Full check | `make check` (test + lint + mypy) | Makefile check target |

**Local CI**: `make check`

---

## Verification Tooling

| Tool | Command | Detected From |
|------|---------|---------------|
| Dev Server | `docker compose up -d` | docker-compose.yml |
| Browser Automation | `playwright` | package.json devDependencies |
| E2E Config | `playwright.config.ts` | project root |
| Port | `8123` | docker-compose.yml |
| Health Endpoint | N/A (HA admin API) | -- |
| Docker | `docker-compose.yml` | project root |

**UI Present**: Yes -- HA panel at `/ev_trip_planner/{vehicle_id}`, sensor states in Developer Tools
**Browser Automation Installed**: Yes (`playwright`)
**Project Type**: Web App (HA custom component with panel)
**VE Task Strategy**: UI Present + Browser Automation = VE tasks with playwright
**Verification Strategy**: Run `make test` for unit tests, `make e2e` for browser E2E against docker HA instance

---

## Recommendations for Requirements

1. **Gap #5**: Fix `entry.data` vs `entry.options` read in `update_charging_power()`, activate the listener in `__init__.py`, add empty-trips guard. Three small surgical fixes.

2. **Gap #8**: Create `TripEmhassSensor(CoordinatorEntity, SensorEntity)` class in `sensor.py`. Use HA's `coordinator.async_add_listener` pattern in `async_setup_entry` for dynamic creation. Add `p_deferrable_matrix` attribute to existing aggregated sensor. Keep old aggregated sensor unchanged.

3. **EMHASS auto-config**: The `p_deferrable_matrix` attribute makes EMHASS config a single Jinja2 template that auto-updates when trips change. No `number_of_deferrable_loads` recalculation needed if using the matrix approach.

4. **Panel documentation**: Add a section in the panel that generates and displays the EMHASS Jinja2 config with a copy button. This is purely frontend JS work.

5. **Test strategy**: Gap #5 fixes need unit tests for the `options` read path and listener activation. Gap #8 needs tests for per-trip sensor creation/removal via coordinator listener pattern.

## Resolved Product Decisions

These questions were resolved via product discussion with the user:

1. **EntityCategory for per-trip sensors**: **Visible (no EntityCategory)**. The user needs sensors visible in HA UI for EMHASS config and panel display. `DIAGNOSTIC` would hide them by default.

2. **`number_of_deferrable_loads` in aggregated sensor**: **YES**. Include as attribute in the aggregated sensor. EMHASS requires this parameter, and having it auto-generated avoids manual counting.

3. **Sensor lifecycle when `activo=false`**: **Keep sensor, set to zeros**. Only remove on hard delete. Removing on soft-disable would break EMHASS config (array length mismatch).

4. **`p_deferrable_matrix` format**: **`list[list[float]]` via `| tojson`**. The project already uses this pattern in `shell_command_example.yaml`. HA's `state_attr()` returns native Python objects, `| tojson` produces valid JSON `[[0,...],[3600,...]]`, EMHASS parses JSON (not YAML).

5. **Aggregated sensor**: **KEEP**. Useful for weekly charging plan visualization in panel. The per-trip sensors are additive, not replacement.

## Sources

- `custom_components/ev_trip_planner/__init__.py` -- adapter creation, no listener activation
- `custom_components/ev_trip_planner/sensor.py` -- EmhassDeferrableLoadSensor, TripSensor, dynamic sensor functions
- `custom_components/ev_trip_planner/emhass_adapter.py:1311-1380` -- listener (dead code), update_charging_power
- `custom_components/ev_trip_planner/emhass_adapter.py:276-369` -- per-trip deferrable load params
- `custom_components/ev_trip_planner/emhass_adapter.py:488-601` -- publish_deferrable_loads (aggregated)
- `custom_components/ev_trip_planner/config_flow.py:887-951` -- options flow (saves to entry.options)
- `custom_components/ev_trip_planner/coordinator.py` -- TripPlannerCoordinator data contract
- `custom_components/ev_trip_planner/definitions.py` -- TRIP_SENSORS entity descriptions
- `doc/gaps/gaps.md` -- Problem descriptions and hypotheses
- [HA Developer Docs: Options Flow](https://developers.home-assistant.io/docs/config_entries_options_flow_handler/) -- OptionsFlow.async_create_entry saves to entry.options
- [HA Developer Docs: Dynamic Devices](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/dynamic-devices) -- coordinator.async_add_listener pattern
