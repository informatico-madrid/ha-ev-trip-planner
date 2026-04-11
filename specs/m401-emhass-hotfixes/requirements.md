---
spec: m401-emhass-hotfixes
phase: requirements
created: 2026-04-11T00:00:00Z
---

# Requirements: m401-emhass-hotfixes

## Goal

Fix charging power config updates being silently ignored (Gap #5: 3 root causes) and add per-trip EMHASS sensors with dynamic lifecycle plus an auto-config `p_deferrable_matrix` attribute (Gap #8), so EMHASS can optimize each trip independently and the user never reconfigures manually when trips change.

## User Stories

### US-1: Charging Power Updates Reflected in EMHASS Profile
**As a** vehicle owner
**I want to** change `charging_power_kw` in the integration options and see the EMHASS sensor update immediately
**So that** charging schedules reflect actual charger capacity (e.g., 3.6 kW wall plug vs 11 kW Wallbox)

**Acceptance Criteria:**
- [ ] AC-1.1: After changing `charging_power_kw` via Options flow, `update_charging_power()` reads the new value from `entry.options` (with `entry.data` fallback)
- [ ] AC-1.2: `setup_config_entry_listener()` is called during `async_setup_entry` so the listener is active in production
- [ ] AC-1.3: When `_published_trips` is empty at listener fire time, trips are reloaded from `trip_manager` before republishing
- [ ] AC-1.4: `EmhassDeferrableLoadSensor` `power_profile_watts` recalculates with new power value within one coordinator refresh cycle

### US-2: Per-Trip EMHASS Sensors with Full Parameters
**As a** vehicle owner
**I want** a separate sensor per trip exposing all EMHASS deferrable load parameters
**So that** I can reference individual trip parameters in automations or debug charging plans per trip

**Acceptance Criteria:**
- [ ] AC-2.1: Each active trip has a visible `TripEmhassSensor` entity (no `EntityCategory.DIAGNOSTIC`)
- [ ] AC-2.2: Sensor `extra_state_attributes` include: `def_total_hours`, `P_deferrable_nom`, `def_start_timestep`, `def_end_timestep`, `power_profile_watts`, `trip_id`, `emhass_index`, `kwh_needed`, `deadline`
- [ ] AC-2.3: Sensor created when trip is added, updated on coordinator refresh, removed on hard delete
- [ ] AC-2.4: When trip is inactive (`activo=false`), sensor remains with zeroed values (`power_profile_watts` all zeros, `def_total_hours=0`, `P_deferrable_nom=0`)
- [ ] AC-2.5: Sensor `unique_id` format: `emhass_trip_{vehicle_id}_{trip_id}` (stable across restarts)
- [ ] AC-2.6: Sensor `device_info` uses `identifiers={(DOMAIN, vehicle_id)}` matching the device

### US-3: Dynamic P_deferrable Matrix for Auto-Config
**As a** vehicle owner using EMHASS
**I want** the aggregated EMHASS sensor to expose a `p_deferrable_matrix` attribute that contains all per-trip profiles as a 2D array
**So that** a single Jinja2 template auto-configures EMHASS without manual updates when trips change

**Acceptance Criteria:**
- [ ] AC-3.1: `EmhassDeferrableLoadSensor.extra_state_attributes` includes `p_deferrable_matrix` as `list[list[float]]`
- [ ] AC-3.2: Each inner list is a 168-element per-trip power profile in watts
- [ ] AC-3.3: Matrix rows ordered by `emhass_index` ascending (sorted iteration of `_index_map`); rows are contiguous with no gaps — only active trips included
- [ ] AC-3.4: `number_of_deferrable_loads` attribute added to aggregated sensor (equals number of active trips in matrix)
- [ ] AC-3.5: All aggregated array attributes compatible with `{{ state_attr('sensor.emhass_perfil_diferible_VEHICLE', 'ATTR') | tojson }}` — produces valid JSON for EMHASS curl POST

### US-4: Panel Jinja2 Config Display
**As a** vehicle owner
**I want** the panel to show the EMHASS Jinja2 config template with a copy button
**So that** I can paste it into my EMHASS configuration without typos

**Acceptance Criteria:**
- [ ] AC-4.1: Panel displays a dedicated EMHASS config section with the complete Jinja2 template for all EMHASS parameters (`number_of_deferrable_loads`, `def_total_hours`, `P_deferrable_nom`, `def_start_timestep`, `def_end_timestep`, `P_deferrable`)
- [ ] AC-4.2: Template references the correct sensor entity for the current vehicle
- [ ] AC-4.3: Copy button copies the template to clipboard and shows visual confirmation
- [ ] AC-4.4: Template auto-updates when vehicle sensor name changes

### US-5: EMHASS Setup Documentation
**As a** new user
**I want** documentation explaining how to configure EMHASS with the auto-config templates
**So that** I can set up optimized charging without reading source code

**Acceptance Criteria:**
- [ ] AC-5.1: Documentation covers Jinja2 template syntax for `P_deferrable` and `number_of_deferrable_loads`
- [ ] AC-5.2: Documentation explains what each per-trip sensor attribute means for EMHASS
- [ ] AC-5.3: Documentation includes example EMHASS `optimize` configuration using the templates

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | `update_charging_power()` reads `entry.options` first, falls back to `entry.data` for `charging_power_kw` | High | Unit test: mock `entry.options={"charging_power_kw": 3.6}`, `entry.data={"charging_power_kw": 11}`; assert reads 3.6 |
| FR-2 | `setup_config_entry_listener()` called in `async_setup_entry` after adapter creation | High | Unit test: verify listener registered; integration test: options change triggers republish |
| FR-3 | Empty `_published_trips` guard: reload from trip_manager before republishing | High | Unit test: `_published_trips=[]`, trip_manager has trips; assert trips loaded |
| FR-4 | `TripEmhassSensor` class in `sensor.py` extending `CoordinatorEntity` + `SensorEntity`; `native_value` = `emhass_index` (int), derived from `_index_map` | High | Sensor visible in HA entity list; `native_value` shows index; attributes match spec table |
| FR-5 | Per-trip EMHASS sensor creation/removal follows the same business logic trigger as existing TripSensor (trip added/deleted → sensor created/removed) but all NEW code must follow SOLID principles. New `async_create_trip_emhass_sensor` / `async_remove_trip_emhass_sensor` must be properly decoupled, testable in isolation, and not introduce tight coupling between trip_manager and sensor internals. Design phase determines the exact decoupling strategy | High | Add trip -> EMHASS sensor appears immediately alongside TripSensor; delete trip -> both removed; new code is SOLID and independently testable |
| FR-6 | Per-trip sensor removal on hard delete via `entity_registry.async_remove` | High | Delete trip -> sensor removed from entity registry |
| FR-7 | Per-trip sensor zeroed (not removed) when trip `activo=false` | High | Disable trip -> `power_profile_watts` all zeros, sensor persists |
| FR-8 | `p_deferrable_matrix` attribute on `EmhassDeferrableLoadSensor` | High | Matrix is `list[list[float]]`, rows = active trips, cols = 168 hours |
| FR-9 | `number_of_deferrable_loads` attribute on aggregated sensor | Medium | Equals number of rows in `p_deferrable_matrix` (= count of active trips) |
| FR-9a | `def_total_hours_array` attribute on aggregated sensor | Medium | `list[float]` of per-active-trip total hours, order matches matrix rows |
| FR-9b | `p_deferrable_nom_array` attribute on aggregated sensor | Medium | `list[int]` of per-active-trip nominal power in watts, order matches matrix rows |
| FR-9c | `def_start_timestep_array` attribute on aggregated sensor | Medium | `list[int]` of per-active-trip start timesteps, order matches matrix rows. NOT hardcoded to 0 — calculated from charging windows via `calculate_multi_trip_charging_windows()` in `calculations.py`. Trip 1 window starts at timestep 0 (car is home, can charge now). Trip 2 window starts when trip 1 returns home (car is away, cannot charge until back). Each subsequent trip's window opens only after the previous trip returns |
| FR-9d | `def_end_timestep_array` attribute on aggregated sensor | Medium | `list[int]` of per-active-trip end timesteps, order matches matrix rows |
| FR-10 | Panel Jinja2 config section with copy button | Medium | UI renders template string; click copies to clipboard |
| FR-11 | EMHASS setup documentation with template examples | Medium | Docs file exists with complete EMHASS config example |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Test coverage | `make test-cover` | 100% on all changed modules |
| NFR-2 | No regression on existing sensors | `make test` | All existing tests pass |
| NFR-3 | TDD compliance | Red-Green-Refactor cycle | Failing test before each implementation |
| NFR-4 | Sensor creation latency | Time from trip add to sensor visible | < 2 coordinator cycles (60s) |
| NFR-5 | Code quality | `make check` (lint + mypy + test) | Zero errors |
| NFR-6 | SOLID compliance | Class size, SRP | No class > 200 lines |
| NFR-7 | Real-time accuracy | Coordinator refresh cycle | All EMHASS sensor attributes (timesteps, power profiles, hours) recalculate every 30s via coordinator refresh. As time passes, `def_start_timestep` and `def_end_timestep` decrease, `power_profile_watts` shifts accordingly — sensor state always reflects current reality |

## Data Model

### Per-Trip Sensor Attributes (`TripEmhassSensor`)

| Attribute | Type | Unit | Description |
|-----------|------|------|-------------|
| `native_value` | `int` | -- | `emhass_index` from `_index_map` (stable, unique per trip). `-1` if no index assigned yet |
| `def_total_hours` | `float` | hours | `kwh_needed / charging_power_kw` |
| `P_deferrable_nom` | `float` | watts | `charging_power_kw * 1000` |
| `def_start_timestep` | `int` | index 0-167 | Start of charging window |
| `def_end_timestep` | `int` | index 0-167 | End of charging window / deadline |
| `power_profile_watts` | `list[float]` | watts | 168-element individual trip profile |
| `trip_id` | `str` | -- | Trip identifier |
| `emhass_index` | `int` | -- | Index from `_index_map` for EMHASS ordering |
| `kwh_needed` | `float` | kWh | Energy needed for trip |
| `deadline` | `str` | ISO 8601 | Trip deadline datetime |

### Aggregated Sensor New Attributes (`EmhassDeferrableLoadSensor`)

All array attributes include **only active trips** (trips with `activo=true`). Inactive trips are excluded from EMHASS config arrays. Matrix rows are ordered by `emhass_index` ascending, no gaps.

| Attribute | Type | Description |
|-----------|------|-------------|
| `p_deferrable_matrix` | `list[list[float]]` | 2D array: each row is a per-active-trip 168-hour power profile |
| `number_of_deferrable_loads` | `int` | Number of active trips (= number of rows in matrix) |
| `def_total_hours_array` | `list[float]` | Per-active-trip total charging hours `[5.56, 3.47, ...]` |
| `p_deferrable_nom_array` | `list[int]` | Per-active-trip nominal power in watts `[3600, 2200, ...]` |
| `def_start_timestep_array` | `list[int]` | Per-active-trip start timestep `[0, 20, ...]` |
| `def_end_timestep_array` | `list[int]` | Per-active-trip end timestep `[44, 24, ...]` |

### Jinja2 Template (Single Sensor, Auto-Updating)

All EMHASS parameters come from the same aggregated sensor. The template auto-updates when trips change — no manual reconfiguration needed. Uses `| tojson` for valid JSON output in curl POST body.

```yaml
number_of_deferrable_loads: {{ state_attr('sensor.emhass_perfil_diferible_VEHICLE', 'number_of_deferrable_loads') }}

def_total_hours: {{ state_attr('sensor.emhass_perfil_diferible_VEHICLE', 'def_total_hours_array') | tojson }}

P_deferrable_nom: {{ state_attr('sensor.emhass_perfil_diferible_VEHICLE', 'p_deferrable_nom_array') | tojson }}

def_start_timestep: {{ state_attr('sensor.emhass_perfil_diferible_VEHICLE', 'def_start_timestep_array') | tojson }}

def_end_timestep: {{ state_attr('sensor.emhass_perfil_diferible_VEHICLE', 'def_end_timestep_array') | tojson }}

P_deferrable: {{ state_attr('sensor.emhass_perfil_diferible_VEHICLE', 'p_deferrable_matrix') | tojson }}
```

## Glossary

- **Deferrable Load**: A load EMHASS can schedule within a time window (e.g., EV charging before departure)
- **`p_deferrable_matrix`**: 2D array where each row is a per-trip 168-hour power profile, used as EMHASS `P_deferrable` input
- **`_index_map`**: Persistent mapping `{trip_id -> emhass_index}` in `EMHASSAdapter`, survives restarts
- **`entry.options` vs `entry.data`**: HA stores initial config in `entry.data`, options flow edits in `entry.options`
- **`OptionsFlow`**: HA's built-in mechanism for editing integration settings post-setup; `async_create_entry(data=...)` writes to `entry.options`
- **CoordinatorEntity**: HA pattern where sensor state derives from `DataUpdateCoordinator.data`
- **`activo=false`**: Trip disabled flag; trip exists but should not be charged for
- **Hard delete**: User removes trip entirely (vs soft-disable with `activo=false`)

## Out of Scope

- `RestoreSensor` implementation for per-trip sensors (separate gap, not in M4.0.1)
- `diagnostics.py` module (separate gap)
- `ConfigSubentry` migration for trips (future architectural improvement)
- EMHASS API calls or direct EMHASS integration (this spec only produces sensor attributes)
- Changing the aggregated sensor's existing attributes (`power_profile_watts`, `deferrables_schedule`, `emhass_status`)
- Front-end panel redesign or new panel sections beyond the Jinja2 config section
- Migration of existing per-trip sensor `unique_id` formats (no prior per-trip EMHASS sensors exist)

## Dependencies

- All 4 prior EMHASS specs merged to main (device_info, method routing, index management, cascade delete)
- `EMHASSAdapter._index_map` for stable trip-to-index mapping
- `async_create_trip_sensor` / `async_remove_trip_sensor` patterns in `sensor.py`
- `sensor_async_add_entities` callback stored in `runtime_data` at `sensor.py:350`
- `async_publish_deferrable_load()` at `emhass_adapter.py:276` for per-trip param calculation
- `calculate_multi_trip_charging_windows()` at `calculations.py:332-353` for charging window logic (not currently used for `def_start_timestep`)
- Home Assistant entity_registry API for dynamic entity removal
- Coordinator refresh cycle (30s) drives all sensor updates — per-trip sensors read from `coordinator.data` like existing `TripSensor`

## Success Criteria

- Charging power changes in Options flow reflected in EMHASS sensor within one coordinator cycle
- Per-trip EMHASS sensors appear/disappear with trip lifecycle
- `p_deferrable_matrix` attribute auto-updates when any trip changes
- Panel shows copyable Jinja2 config
- `make test-cover` passes at 100% on all changed files
- `make check` passes with zero errors

## Verification Contract

**Project type**: fullstack

**Entry points**:
- `custom_components/ev_trip_planner/__init__.py:async_setup_entry` (listener activation)
- `custom_components/ev_trip_planner/emhass_adapter.py:update_charging_power` (options read fix)
- `custom_components/ev_trip_planner/emhass_adapter.py:setup_config_entry_listener` (dead code activation)
- `custom_components/ev_trip_planner/sensor.py:TripEmhassSensor` (new sensor class)
- `custom_components/ev_trip_planner/sensor.py:EmhassDeferrableLoadSensor` (matrix + EMHASS param array attributes)
- `custom_components/ev_trip_planner/sensor.py:async_create_trip_emhass_sensor` / `async_remove_trip_emhass_sensor` (sensor CRUD, following existing pattern)
- `custom_components/ev_trip_planner/trip_manager.py` (calls sensor CRUD alongside existing TripSensor creation)
- Panel JS: Jinja2 config section with copy button
- Entity registry: per-trip sensor CRUD

**Observable signals**:
- PASS looks like:
  - After options change: `state_attr('sensor.emhass_perfil_diferible_VEHICLE', 'power_profile_watts')` reflects new charging power
  - After trip add: new entity `sensor.emhass_trip_VEHICLE_TRIPID` visible in HA with all 9 attributes, `native_value` = `emhass_index`
  - After trip delete: entity removed from entity registry, `p_deferrable_matrix` has one fewer row, all EMHASS param arrays updated
  - After trip disable: entity persists with zeroed values, but `p_deferrable_matrix` and EMHASS param arrays EXCLUDE this trip
  - Aggregated sensor: `p_deferrable_matrix` = `[[3600, 3600, ...], [2200, 2200, ...]]` (only active trips)
  - Aggregated sensor: `def_total_hours_array` = `[5.56, 3.47]` (length matches matrix row count)
  - Aggregated sensor: `p_deferrable_nom_array` = `[3600, 2200]` (length matches matrix row count)
  - Aggregated sensor: `number_of_deferrable_loads` = 2 (matches matrix row count)
  - Panel: EMHASS config section renders complete template with all 6 parameters + copy button
- FAIL looks like:
  - Options change: sensor `power_profile_watts` unchanged (old power value)
  - Trip add: no new sensor entity appears
  - Trip delete: orphaned sensor entity remains
  - `p_deferrable_matrix`: empty list `[]` when active trips exist, or mismatched row count vs other arrays
  - `def_total_hours_array` / `p_deferrable_nom_array` / `def_start_timestep_array` / `def_end_timestep_array`: length != `number_of_deferrable_loads`
  - Unit test coverage < 100% on changed files

**Hard invariants**:
- Existing `EmhassDeferrableLoadSensor` attributes (`power_profile_watts`, `deferrables_schedule`, `emhass_status`) MUST NOT change format or semantics
- Existing `TripSensor` entities MUST NOT be affected
- `_index_map` stability MUST be preserved (no index reshuffling on trip add/remove)
- `entry.data` MUST remain fallback when `entry.options` lacks `charging_power_kw`
- All aggregated EMHASS param arrays (`def_total_hours_array`, `p_deferrable_nom_array`, `def_start_timestep_array`, `def_end_timestep_array`, `p_deferrable_matrix`) MUST have same length = `number_of_deferrable_loads`
- Auth/session validity, HA config entry lifecycle, and unrelated sensor flows MUST NOT break

**Seed data**:
- Config entry with `charging_power_kw=11` in `entry.data`, `charging_power_kw=3.6` in `entry.options`
- At least 2 recurring trips (one active, one inactive `activo=false`)
- At least 1 punctual trip with future deadline
- `_index_map` with stable indices assigned to existing trips
- EMHASS adapter initialized and `publish_deferrable_loads` called at least once

**Dependency map**:
- `sensor.py` shares `coordinator.data` with `coordinator.py`
- `sensor.py` uses `sensor_async_add_entities` from `runtime_data` (stored in `sensor.py:async_setup_entry`)
- `emhass_adapter.py` shares `_index_map` state with `trip_manager.py`
- `emhass_adapter.py` reads `config_entries` from `hass` (shared with `config_flow.py`)
- Panel JS reads sensor states via HA WebSocket API
- `__init__.py` orchestrates adapter creation and listener activation
- `trip_manager.py` calls sensor CRUD functions from `sensor.py` (existing pattern at lines 481, 524)

**Data flow note (design phase)**:
- Per-trip EMHASS sensor attributes derive from trip data + charging power config + charging window calculations
- Existing `TripSensor` reads from `coordinator.data["recurring_trips"][trip_id]` or `coordinator.data["punctual_trips"][trip_id]`
- `TripEmhassSensor` should follow same pattern — compute EMHASS params from trip data in coordinator, or extend coordinator data to include per-trip EMHASS params
- `def_start_timestep` must use `calculate_multi_trip_charging_windows()` instead of hardcoded 0
- **SOLID requirement**: All new code (TripEmhassSensor, sensor CRUD functions, param calculations) must follow SOLID principles. If modifying existing code is necessary to make the new functionality properly testable and decoupled, that refactor is allowed and encouraged. The goal is correct, testable architecture — not preserving legacy coupling

**Escalate if**:
- Entity registry removal fails silently (zombie entity)
- `_index_map` indices conflict after concurrent trip add/remove
- `entry.options` structure differs from expected schema (migration needed)
- `power_profile_watts` length != 168 on any per-trip sensor
- EMHASS param arrays have mismatched lengths (consistency violation)
- Panel JS cannot access sensor state attributes (permissions issue)

## Unresolved Questions

- None. All product decisions resolved during research phase (visible sensors, include `number_of_deferrable_loads`, zero on disable, `list[list[float]]` format, keep aggregated sensor).

## Next Steps

1. Approve requirements
2. Proceed to design phase (technical design for `TripEmhassSensor` class, coordinator listener integration, panel Jinja2 section)
3. Proceed to task generation from design
