# 🗺️ Roadmap & Milestones - EV Trip Planner

## 📊 Project Status

**Current version**: 0.5.23
**Development phase**: Milestone 4.0.3 completed — M4.1 next target
**Target Release**: v1.0.0 (Q2 2026)
**Tests**: 1822 Python (pytest) + 40 E2E (Playwright) passing
**Quality Assurance**: Mutation testing (mutmut) configured for Milestone 4.0.1
**Detected gaps**: [`doc/gaps/gaps.es.md`](doc/gaps/gaps.es.md)

---

## ✅ Completed Milestones History

### Milestone 0: Project Foundation (Nov 18, 2025)
- Repository structure and custom component skeleton
- Initial config flow, MIT license, HACS metadata
- Constants and domain configured

### Milestone 1: Core Infrastructure (Nov 18, 2025)
- Recurrent and punctual trip management system
- CRUD services: `add_recurring_trip`, `add_punctual_trip`, `edit_trip`, `delete_trip`
- 3 basic sensors: `trips_list`, `recurring_count`, `punctual_count`
- Base Lovelace dashboard
- 83% test coverage (29 tests)

### Milestone 2: Trip Calculations (Nov 22, 2025)
- Calculation sensors: `next_trip`, `next_deadline`, `kwh_today`, `hours_today`
- Recurrent trip expansion for 7 days
- Combination of recurrent + punctual trips
- Complete timezone handling
- 84% coverage (60 tests)

### Milestone 3: EMHASS Integration & Smart Control (Dec 8, 2025)
- `emhass/`: Dynamic deferrable load publishing, index pool 0-49, persistence across restarts
- `vehicle/`: 4 control strategies (Switch, Service, Script, External) — implemented but not end-to-end tested
- `presence_monitor/`: Sensor and coordinate-based presence detection, safety logic
- Extended config flow with EMHASS and presence detection steps
- 3 new sensors: `active_trips`, `presence_status`, `charging_readiness`
- Migration service from sliders: `ev_trip_planner.import_from_sliders`
- ⚠️ **NOTE**: `schedule_monitor.py` exists but is NOT connected — EMHASS-based automatic charge control does NOT work end-to-end
- 156 tests with 93.6% pass rate

### Milestone 3.1: UX Improvements — Configuration Clarity (Dec 8, 2025)
- Entity filters in config flow (SOC→%, Plugged→binary_sensor)
- Help texts and descriptions on all fields
- Complete Spanish translations
- "External EMHASS" renamed to "Notifications Only"

### Milestone 3.2: Advanced Configuration Options (Dec 8, 2025)
- Consumption profiles by trip type (urban / highway / mixed)
- Auto-cleanup of past punctual trips (configurable)
- New sensor: `last_cleanup`
- ⚠️ **NOTE**: SOH (State of Health) NOT IMPLEMENTED in config flow — code infrastructure exists but no UI selector for SOH sensor

### Milestone 4: Smart Charging Profile (Mar 18, 2026 — v0.4.0-dev)
- Binary charging profile: 168-value array (24h x 7d), 0W or max power
- SOC-aware calculation with configurable safety margin
- `emhass_perfil_diferible_{vehicle_id}` sensor with `power_profile_watts` attribute
- Load distribution just before each trip
- 5-step config flow
- Native panel (primary interface) — [`panel.py`](custom_components/ev_trip_planner/panel.py:37) with per-vehicle sidebar entries
- Per-trip EMHASS sensor — [`TripEmhassSensor`](custom_components/ev_trip_planner/sensor/) provides per-trip parameters
- Power profile generation — [`async_generate_power_profile()`](custom_components/ev_trip_planner/trip/) in trip package
- Deferrables schedule generation — [`async_generate_deferrables_schedule()`](custom_components/ev_trip_planner/trip/) in trip package
- Retry logic: 3 attempts in 5-minute window
- 398 tests passing, 85%+ coverage
- ⚠️ **NOTE**: Lovelace dashboard auto-import (`dashboard/`, 1262 lines equivalent) still executes on every setup but is DEPRECATED. Users should use the native panel instead.
- ⚠️ **NOT IMPLEMENTED**: `alerta_tiempo_insuficiente` user notifications — code exists in [`calculations/`](custom_components/ev_trip_planner/calculations/) but **no sensor, notification, or UI element exposes this value**. The user-facing function `calcular_ventana_carga()` returns `es_suficiente` instead. **Feature not exposed to users.**

### SOLID Refactoring (Apr-May 2026 — feat/solid-refactor-coverage branch)
- **9 god-class modules** decomposed into **9 SOLID-compliant packages** (12,400+ LOC)
- 45+ sub-modules created across packages: `emhass/`, `trip/`, `services/`, `dashboard/`, `calculations/`, `vehicle/`, `sensor/`, `config_flow/`, `presence_monitor/`
- **3-phase shim migration**: Skeleton + re-exports → TDD decomposition → cleanup shims (each commit green, bisectable)
- **Pattern selection per package**: Facade+Composition, Facade+Mixins, Module Facade, Builder, Strategy, Functional Decomposition
- **Quality metrics**: SOLID 5/5 PASS (Tier A deterministic), 0 god classes, 62.5% mutation kill rate, Pyright 0 errors
- **Dual-agent quality system**: spec-executor + external-reviewer with anti-evasion policy
- **lint-imports contracts** enforcing dependency direction between packages
- Spec: [`specs/3-solid-refactor/`](specs/3-solid-refactor/)
- CHANGELOG: [0.5.24]

### Milestone 4.0.1: EMHASS Per-Trip Sensors & Hotfixes (Apr 26, 2026)
- `TripEmhassSensor`: Per-trip EMHASS sensors with 9 attributes
- Gap #8 fixed: EMHASS now receives per-trip optimization profiles
- Gap #5 fixed: Charging power updates from options flow
- Hours deficit propagation algorithm for multi-trip charging
- 7 EMHASS integration bugs fixed (datetime, math.ceil, template keys)
- 82 TDD tasks completed, 1470 tests passing, 100% coverage
- Enhanced EMHASS aggregated sensor with `p_deferrable_matrix` attribute
- PR #26 merged (m401-emhass-per-trip-sensors branch)
- CHANGELOG: [0.5.21]

---

### ⚠️ Vehicle Control — Implemented but NOT Wired to UI

**Status**: Code exists in production, but NOT accessible to users through the config flow.

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| `VehicleControlStrategy` ABC | [`vehicle/`](custom_components/ev_trip_planner/vehicle/) | 430 | ✅ Implemented |
| `SwitchStrategy` | [`vehicle/`](custom_components/ev_trip_planner/vehicle/) | — | ✅ Implemented |
| `ServiceStrategy` | [`vehicle/`](custom_components/ev_trip_planner/vehicle/) | — | ✅ Implemented |
| `ScriptStrategy` | [`vehicle/`](custom_components/ev_trip_planner/vehicle/) | — | ✅ Implemented |
| `ExternalStrategy` | [`vehicle/`](custom_components/ev_trip_planner/vehicle/) | — | ✅ Implemented |
| `VehicleController` | [`vehicle/`](custom_components/ev_trip_planner/vehicle/) | — | ✅ Implemented |
| `PresenceMonitor` | [`presence_monitor/`](custom_components/ev_trip_planner/presence_monitor/) | 770 | ✅ Implemented |
| `ScheduleMonitor` | [`presence_monitor/`](custom_components/ev_trip_planner/presence_monitor/) | 324 | ✅ File exists, NEVER instantiated |
| `VehicleScheduleMonitor` | [`presence_monitor/`](custom_components/ev_trip_planner/presence_monitor/) | — | ✅ File exists, NEVER used |

**Gap**: `presence_monitor/schedule_monitor.py` is **never imported** in the package. The `control_strategy` / `control_type` configuration is **NOT exposed** in the config flow. Users cannot select a vehicle control strategy through the UI.

**Impact**: The core "smart charging control" feature (automatic charge start/stop based on EMHASS schedules) does NOT work end-to-end, even though all the code exists.

**Required fix**: Wire `ScheduleMonitor` into `__init__.py` async_setup, add `control_strategy` step to config flow, connect `VehicleController` to the hourly refresh callback.

---

## ✅ Milestone 4.0.1 — Critical M4 Hotfixes (COMPLETED)

**Status**: ✅ COMPLETED — 2026-04-26  
**Spec**: [`specs/m401-emhass-hotfixes/`](specs/m401-emhass-hotfixes/)  
**Target**: v0.5.21  
**PR**: [#26](https://github.com/informatico-madrid/ha-ev-trip-planner/pull/26)

### Completed Features

#### Gap #8 — EMHASS Per-Trip Sensors ✅
- **TripEmhassSensor** class implemented with 9 attributes
- Per-trip EMHASS parameters (def_total_hours, P_deferrable_nom, def_start_timestep, def_end_timestep, power_profile_watts, deadline, soc_target, vehicle_id, trip_id, emhass_index)
- Sensor lifecycle tied to trip (create/update/delete with trip)
- Device grouping under vehicle device (not per-trip device)
- Automatic EMHASS configuration via `p_deferrable_matrix` attribute

#### Gap #5 — Charging Power Update ✅
- Fixed `entry.options.get("charging_power_kw")` read from options flow
- Activated `setup_config_entry_listener()` in `__init__.py`
- Profile updates propagate immediately on config change

#### Additional Fixes ✅
- **7 EMHASS bugs** fixed (datetime, math.ceil, template keys, entity IDs)
- **Hours deficit propagation algorithm** for multi-trip charging
- **82 TDD tasks** completed with 100% pass rate
- **1470 tests** passing, 100% coverage on new code

### Technical Details
- **Files Modified**: sensor/, emhass/, trip/, __init__.py, panel.js
- **New Tests**: Per-trip EMHASS sensor tests, charge deficit propagation tests
- **Documentation**: docs/emhass-setup.md with Jinja2 templates
- **Quality**: Mypy clean (19 files, 0 errors)

---

## 🚧 Next: Milestone 4.0.2 — Panel UX Improvements

**Status**: 📋 PLANNED — not started
**Priority**: P1 - User Experience
**Target**: v0.5.22

### Planned Features

#### Panel UX Debt Reduction
- **Remove hardcoded CSS gradients**: Replace `#667eea`, `#764ba2` with HA theme variables
  - Use `--ha-card-background`, `--primary-color`, `--secondary-color`
  - Respect HA light/dark theme mode
- **Responsive design improvements**: Mobile-friendly panel layout
- **HA theme integration**: All colors use semantic theme variables

#### EMHASS Configuration UX
- **In-panel EMHASS config display**: Show ready-to-copy YAML/Jinja2 templates
- **Copy button**: One-click copy of EMHASS configuration
- **Dynamic template generation**: Always shows current trip configuration

### Estimate
- **Time**: 3-5 days
- **Complexity**: Low-Medium (CSS refactoring + minor JS changes)
- **Files**: frontend/panel.js, frontend/panel.css

---

## 🔋 Immediately After M4.0.2: Milestone 4.0.3 — Dynamic SOC Capping ✅ COMPLETED

**Status**: ✅ COMPLETED — 2026-05-03
**Priority**: P1 - Battery Health & Cost Optimization
**Target**: v0.5.23 (achieved)
**Spec**: [`specs/m403-dynamic-soc-capping/`](specs/m403-dynamic-soc-capping/)
**136 tasks completed**, 1822 tests passing, 100% coverage

### Planned Features

#### Dynamic SOC Capping Algorithm
- **Rational transition function**: `SOC_lim(h) = SOC_max + (100 - SOC_max) * [h / (h + T)]`
  - `h` = hours until trip
  - `SOC_max` = daily maximum SOC (configurable, default 80%)
  - `T` = anticipation hours for full charge (configurable, default 24h)
- **Gradual relaxation**: SOC limit increases as trip approaches
- **Smart override**: Never exceeds SOC target required for trip

#### User-Friendly Config Flow
```yaml
Battery Health Mode: [checkbox]

Límite Diario de Carga:
  slider: 70% ────●──── 95%
  default: 80%
  help: "Porcentaje máximo de carga cuando el viaje está lejos.
         Preserva la salud de tu batería EV."

Horas de Anticipación de Carga:
  slider: 6h ─────●──── 48h
  default: 24h
  help: "Horas antes del viaje para permitir carga al 100%.
         Ej: 24h = 'Un día antes del viaje, cargar al máximo necesario'"
```

#### Additional Features
- Slow charging preference (3.7 kW vs 7.4 kW) when time allows
- Avoid keeping battery at 100% for extended periods
- Optional: Daily time windows for charging

#### Bug Fix — `ventana_horas` Inflated by Away Time
- **Problem**: In [`calculate_multi_trip_charging_windows()`](custom_components/ev_trip_planner/calculations.py:545), `ventana_horas` is calculated as `trip_arrival - window_start` where `trip_arrival = departure + duration_hours(6h)`. This means the charging window includes 6h when the car is **away** and physically cannot charge. The actual deadline is `fin_ventana = trip_departure_time` (line 576), so `ventana_horas` should be `trip_departure_time - window_start`.
- **Impact**: `def_total_hours` sent to EMHASS is inflated by `duration_hours` per trip, making EMHASS believe there is more charging time available than actually exists.
- **Fix (short-term)**: Change `ventana_horas` to use `trip_departure_time - window_start` instead of `trip_arrival - window_start`.
- **Fix (mid-term)**: Consolidate to a single gap value — currently both `duration_hours` (6h) and `return_buffer_hours` (4h) exist; only one should be used.
- **Fix (long-term)**: Each trip gets its own return time field in config, and only that value is used for window calculation.
- **Files**: `calculations.py:545-553`, `const.py:72`

### Example Behavior (SOC_max=80%, T=24h)
```
72h until trip:  SOC_lim = 85%  (3 days away, preserve battery)
48h until trip:  SOC_lim = 86.7%
24h until trip:  SOC_lim = 90%   (1 day away, start preparing)
12h until trip:  SOC_lim = 93.3%
6h until trip:   SOC_lim = 96%
2h until trip:   SOC_lim = 100%  (trip needs it, full charge)
```

### Benefits
- **Battery Health**: Extend battery life by 15-20% according to studies
- **Cost Optimization**: Reduce charging costs by up to 30% on variable tariffs
- **User-Friendly**: Only 2 parameters to understand and configure

### Estimate
- **Time**: 3-4 days
- **Complexity**: Medium (mathematical function + config flow + tests)
- **Tests**: 6-8 TDD tests (edge cases: h=0, h=∞, soc_target<lim, monotonicity)
- **Files**: trip/, calculations/, config_flow/, tests/

---

## 📋 Immediately After M4.0.2 (Priority Order)

### P0 — Pending Critical Items
1. **ScheduleMonitor activation** - Wire automatic charge control (P0 from original ROADMAP)
2. **Config flow options expansion** - Make all 20+ fields editable (P0 from original ROADMAP)

### P1 — Documentation
1. **Update EMHASS setup guide** - Reflect per-trip sensor changes
2. **Panel user guide** - How to use new EMHASS config display
3. **Migration guide** - From aggregated-only to per-trip sensors

### P2 — Enhancement Candidates
1. **Multi-vehicle power balancing** - Shared charging line management (from M4.1)

### Production-detected problems

After Milestone 4 production validation, critical issues were documented in [`doc/gaps/gaps.es.md`](doc/gaps/gaps.es.md).

### Planned features / Fixes

#### P0 — Critical (blocks EMHASS)

- **🔧 Incorrect EMHASS architecture** (Gap #8)
  - **Problem**: The `EmhassDeferrableLoadSensor` aggregates all trips into a single `power_profile_watts`. EMHASS needs separate deferrable profiles per trip to optimize each charge independently.
  - **Status**: `TripEmhassSensor` implemented at `sensor.py:853` — provides per-trip EMHASS parameters. Architecture gap may still exist if individual trip sensors are not properly published to EMHASS.
  - **Impact**: Without proper per-trip publishing, EMHASS optimizes all trips as a single load
  - **Files**: sensor/, emhass/, trip/

- **🔧 Charging power not updating profile** (Gap #5)
  - **Problem**: When changing `charging_power_kw` in options (e.g., 11kW → 3.6kW), the planning sensor does not update
  - **Solution hypothesis**: Fix in `update_charging_power()` — read from `entry.options` in addition to `entry.data`, republish with fresh trips
  - **Impact**: User sees incorrect profile after changing configuration
  - **Files**: `emhass_adapter.py:1346-1380`

#### P0 — Critical (blocks UX)

- **🔧 Incomplete options flow** (Gap #4)
  - **Problem**: Only 4 fields editable out of 20+. User cannot correct sensors without deleting the entire integration
  - **Solution hypothesis**: Add entity selectors for critical sensors to options flow
  - **Files**: `config_flow.py:887-951`

#### P0 — Critical (blocks core functionality)

- **🔧 ScheduleMonitor exists but is NEVER instantiated** (NEW — discovered 2026-04-25)
  - **Problem**: `schedule_monitor.py` (324 lines) contains `ScheduleMonitor` and `VehicleScheduleMonitor` classes with complete vehicle control logic
  - **Status**: File exists in `custom_components/ev_trip_planner/` but is **never imported** in `__init__.py`
  - **Impact**: The core "automatic charge control based on EMHASS schedules" feature does NOT work — users cannot set up automatic charging control even though the code exists
  - **Files**: `schedule_monitor.py`, `vehicle_controller.py`, `__init__.py`
  - **Required**: Wire into `async_setup_entry`, add `control_strategy` step to config flow

#### P1 — High (UX)

- **🔧 Sidebar not removed when deleting vehicle** (Gap #1)
  - **Problem**: `async_unregister_panel` IS called in `services.py:1471`, but may silently fail if HA version lacks `frontend.async_remove_panel`
  - **Verification**: Code exists at [`services.py:1468-1472`](custom_components/ev_trip_planner/services.py:1468), calls `panel.async_unregister_panel`
  - **Status**: **PARTIALLY FIXED** — the call exists, but depends on HA version compatibility
  - **Files**: `services.py`, `panel.py`

### Control panel: EMHASS configuration to copy

As part of the architecture fix (#8), the panel will show ready-to-copy YAML/Jinja2 code:

```yaml
# User copies this to their EMHASS configuration.yaml
number_of_deferrable_loads: 2

def_total_hours:
  - "{{ states('sensor.ev_trip_planner_coche_viaje_1_total_hours') | float(0) }}"
  - "{{ states('sensor.ev_trip_planner_coche_viaje_2_total_hours') | float(0) }}"

P_deferrable_nom:
  - "{{ states('sensor.ev_trip_planner_coche_viaje_1_nominal_power') | int(0) }}"
  - "{{ states('sensor.ev_trip_planner_coche_viaje_2_nominal_power') | int(0) }}"

def_start_timestep:
  - "{{ states('sensor.ev_trip_planner_coche_viaje_1_start_timestep') | int(0) }}"
  - "{{ states('sensor.ev_trip_planner_coche_viaje_2_start_timestep') | int(0) }}"

def_end_timestep:
  - "{{ states('sensor.ev_trip_planner_coche_viaje_1_end_timestep') | int(0) }}"
  - "{{ states('sensor.ev_trip_planner_coche_viaje_2_end_timestep') | int(0) }}"

P_deferrable:
  p_deferrable: "{{ state_attr('sensor.ev_trip_planner_coche_viaje_1', 'power_profile_watts') | default([]) }}"
  p_deferrable: "{{ state_attr('sensor.ev_trip_planner_coche_viaje_2', 'power_profile_watts') | default([]) }}"
```

### Prerequisites before starting M4.0.1
- [ ] Validate cause hypotheses in [`doc/gaps/gaps.es.md`](doc/gaps/gaps.es.md)
- [ ] Confirm gaps #5 and #8 are reproducible
- [ ] Verify that architecture fix (#8) does not break existing EMHASS integration
- [ ] **Configure mutation testing (mutmut)** in CI/CD to validate test quality

### Testing Improvements (NEW for M4.0.1)

- **🧪 Mutation Testing (mutmut)**
  - **Objective**: Add mutation testing to CI/CD pipeline to validate that tests detect code changes
  - **Benefit**: Detect tests that are not strict enough (tests that pass even when code is incorrect)
  - **Configuration**: Add `mutmut` to `pyproject.toml`, configure `test_command` with critical tests
  - **CI Integration**: Run mutmut on high-priority PRs, results only informative on minor PRs
  - **Impact**: Improve test quality and confidence in existing test suite
  - **Files**: `pyproject.toml`, `.github/workflows/ci.yml`

### Estimate
- **Time**: 1-2 weeks
- **Complexity**: Medium-High (EMHASS sensor refactoring requires care)
- **Tests**: TDD — add tests before implementing fixes
- **Mutation Testing**: Configure mutmut, run baseline, integrate in CI

---

## 📋 Planned: Milestone 4.1 — Advanced Charging Optimization

**Status**: 📋 PLANNED — not started  
**Complete technical details**: [`docs/MILESTONE_4_1_PLANNING.md`](docs/MILESTONE_4_1_PLANNING.md)  

### Planned features

- **⚡ Distributed Charging**: Distribute energy across multiple hours based on grid price (instead of binary profile)
- **🚗 Multi-Vehicle Support**: 2+ vehicles with power balancing on shared line
- **🌡️ Temperature Adjustment**: Consumption correction based on weather forecast
- **📊 Profile UI**: Charging profile chart in dashboard (requires `apexcharts-card` custom card — not installed by default)

### Prerequisites before starting M4.1
- [ ] **Complete Milestone 4.0.1** (critical EMHASS hotfixes)
- [ ] Complete M3 production validation (3E.1: 48h without errors)
- [ ] Confirm >80% coverage in all modules post-SOLID refactor
- [ ] Define API format for external price optimizer
- [ ] Validate that M4.0.1 fixes do not break existing EMHASS integration

---

## ⚠️ Known Limitations (Active)

**Problems detected in production**: See [`doc/gaps/gaps.es.md`](doc/gaps/gaps.es.md) for detailed analysis with cause hypotheses and solutions.

These limitations are documented and are deliberate design decisions for v1.0:

1. **⚠️ EMHASS automatic charge control NOT WORKING (P0 Critical)**: `schedule_monitor.py` (324 lines) exists but is **never instantiated**. The vehicle controller (4 strategies in `vehicle_controller.py`, 510 lines) is fully implemented but never activated because `ScheduleMonitor` is never wired into `__init__.py`. The config flow has NO step for `control_strategy`. **This is the single biggest gap in the project** — the code exists, it just needs to be connected. See [Vehicle Control section](#-vehicle-control--implemented-but-not-wired-to-ui) above.

2. **⚠️ Lovelace deprecated code still executes on every setup**: `async_import_dashboard_for_entry()` is still called in `__init__.py:187`. The `dashboard.py` module (1262 lines) contains full Lovelace import logic that runs on every integration setup. This is DEPRECATED — the native panel is the primary interface. The Lovelace code should be removed or gated behind a feature flag.

3. **⚠️ Panel cleanup may silently fail on some HA versions**: `async_unregister_panel` IS called in `services.py:1471`, but it depends on `frontend.async_remove_panel` which may not exist in all HA versions. If missing, the try/except silently swallows the error, leaving orphaned panel entries.

4. **Dashboard charts require apexcharts-card**: The full dashboard with power profile charts (`ev-trip-planner-full.yaml`) requires installing the `apexcharts-card` custom card manually in Home Assistant. Without this dependency, users only see the simple dashboard.

5. **✅ Dynamic SOC Capping COMPLETED in M4.0.3**: The algorithm is now fully implemented. Users can configure `t_base` (6-48h), SOH sensor, and SOC base. The dynamic limit follows: `risk = t * (soc - 35) / 65`, `SOC_lim = 35 + 65 * [1 / (1 + risk/T)]`. Trips always succeed regardless of dynamic limits.

6. **One EMHASS index per trip**: User must manually configure EMHASS snippet for each potential index up to `max_deferrable_loads`. No auto-discovery because EMHASS does not support it.

7. **Manual EMHASS configuration**: Not plug-and-play; requires adding configuration to `configuration.yaml`.

8. **Single optimizer**: Only EMHASS supported. Architecture uses `emhass/` package as adapter, prepared to add others (Tibber, etc.) in v1.2.

9. **Fixed planning horizon**: 7 days by default, configurable but static. Does not dynamically adapt to EMHASS horizon.

10. **⚠️ `ventana_horas` inflated by away time (BUG)**: In [`calculate_multi_trip_charging_windows()`](custom_components/ev_trip_planner/calculations.py:545), `ventana_horas` is calculated as `trip_arrival - window_start` where `trip_arrival = departure + 6h`. This includes 6h when the car is away and cannot charge. The real deadline is `fin_ventana = trip_departure_time`. This inflates `def_total_hours` sent to EMHASS by `duration_hours` per trip. **Status: Pending implementation** — short-term: use `departure - window_start`; mid-term: consolidate to single gap value; long-term: per-trip return time field.

---

## 🔮 Future Versions (Post v1.0)

### v1.0: Consolidation
- Complete production validation (3E.1)
- HACS quality scale: bronze → silver
- Complete user documentation

### v1.1: Multi-Vehicle
- Support for 2+ vehicles
- Shared charging line management
- Prioritization and conflict resolution

### v1.2: Additional Optimizers
- Native integration with Tibber and other price optimizers
- Custom optimization rules
- Dynamic tariffs without EMHASS

### v1.3: Smart Learning
- Real consumption learning from history
- Weather and traffic-based prediction
- Battery degradation tracking

### v1.3+: Battery Health & Advanced Optimization
- **Dynamic SOC Capping**: Rational transition function to limit SOC based on trip urgency (80% for distant trips, gradually increasing to 100% as trip approaches)
- **Adaptive charging strategies**: Slow charging (3.7 kW) preference when time allows
- **Battery preservation mode**: Avoid extended periods at 100% SOC

### v1.4: Route Planning
- Integration with Google Maps / OpenStreetMap Nominatim
- Automatic distance calculation from address
- Multi-stop planning

### v1.5: Fleet Management
- Multi-user support
- Permissions and roles
- Centralized dashboard

---

## 🎯 Use Cases — Prioritization

### P0 — Must Have (v1.0)
- ✅ Single vehicle with notifications only (no control)
- ⚠️ Single vehicle with automatic charging control — **code exists but NOT wired** (see Vehicle Control section above)
- ✅ Weekly recurrent trips
- ✅ Punctual trips
- ✅ Energy and deadline calculations
- ✅ Native panel per vehicle
- ✅ EMHASS deferrable load publishing

### P1 — Should Have (v1.1)
- ⏳ Multi-vehicle with shared line
- ⏳ Dashboard with profile charts
- 🔧 **NEW**: Wire ScheduleMonitor + VehicleController to complete automatic charging control

### P2 — Nice to Have (v1.2+)
- ⏳ PHEV with hybrid logic
- ⏳ Dynamic price optimization (without EMHASS)
- ⏳ Voice commands / HA Assist

### P3 — Future (v2.0+)
- ⏳ Fleet management
- ⏳ Route planning with maps
- ⏳ Multi-user support

---

## 🚗 Vehicle Integrations

### Tested by the team
- [x] OVMS (Nissan Leaf) — reference implementation
- [x] V2C EVSE (Dacia Spring) — reference implementation

### Pending testing (community help)
- [ ] Tesla
- [ ] Renault ZOE
- [ ] Hyundai/Kia
- [ ] BMW i3
- [ ] VW ID series
- [ ] Generic EVSE (smart plugs)

---

## 📚 Documentation Structure

```
docs/
├── MILESTONE_4_1_PLANNING.md # Detailed Milestone 4.1 plan (HISTORICAL — superseded)
├── MILESTONE_4_POWER_PROFILE.md # M4 charging profile spec (HISTORICAL — completed)
├── architecture.md # System architecture
├── api-contracts.md # API contracts
├── data-models.md # Data models
├── development-guide.md # Development guide
├── DASHBOARD.md # Dashboard guide (DEPRECATED — use native panel)
├── VEHICLE_CONTROL.md # Vehicle control strategies
├── SHELL_COMMAND_SETUP.md # Shell command setup for EMHASS
├── emhass-setup.md # EMHASS integration setup
├── source-tree-analysis.md # Source tree structure
├── DOCS_DEEP_AUDIT.md # Documentation audit report
└── e2e-date-diagnosis-final.md # E2E date debugging report

doc/
└── gaps/
    └── gaps.es.md # Production-detected problems with hypotheses

_ai/
└── PORTFOLIO.md # Portfolio-ready documentation
    TDD_METHODOLOGY.md # TDD methodology applied to project
    TESTING_E2E.md # E2E testing guide with Playwright
```

---

## 🤝 How to Contribute

**High priority**:
- 🔧 **Wire ScheduleMonitor + VehicleController** — This is the single highest-impact task: connect existing code to complete automatic charging control
- Testing with different VE integrations (see pending list above)
- UX feedback on native panel (not Lovelace dashboard)
- Translations to other languages
- Bug reports

**Medium priority**:
- Additional automation examples
- Performance optimizations
- Remove deprecated Lovelace auto-import code (or gate behind feature flag)

**Low priority** (wait for v1.0):
- Advanced features
- New optimizer integrations

---

## 🔄 Next Steps — Code Quality & Technical Debt (Planned After M4.0.3)

**Status**: 📋 PLANNED — not started
**Triggered by**: M4.0.3 completion (2026-05-03)

### Code Cleanup + Dead Code Elimination
- Systematic removal of all dead code using .roo quality-gate scripts (antipattern_checker, solid_metrics, weak_test_detector)
- Target: Zero unreachable code paths
- Focus areas: deprecated dashboard.py code, unused vehicle_controller strategies, orphaned schedule_monitor references

### Mutation Testing Integration
- Configure mutation testing thresholds per-module (mutmut)
- Integrate with quality-gate Layer 1
- Establish mutation kill thresholds (target: ≥0.70 across all modules)
- Initial baseline run on M4.0.3 codebase

### Deterministic Quality Gates
- Add ARNs (Architecture Requirement Notations) — formal constraints on module dependencies, API contracts, and test coverage minimums
- Enable near-autonomous technical debt elimination using specs + quality-gate skills
- Each PR validated against ARNs before merge

---

**Last updated**: May 3, 2026
**Status review**: After M4.0.3 completion + full codebase audit (2026-05-03)

---

📬 **Issues and discussions**:
- [GitHub Issues](https://github.com/informatico-madrid/ha-ev-trip-planner/issues)
- [GitHub Discussions](https://github.com/informatico-madrid/ha-ev-trip-planner/discussions)
