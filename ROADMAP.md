# 🗺️ Roadmap & Milestones - EV Trip Planner

## 📊 Project Status

**Current version**: 0.5.20
**Development phase**: Milestone 4.0.1 hotfixes planned — M4 core features fully implemented
**Target Release**: v1.0.0 (Q2 2026)
**Tests**: 793+ Python (pytest) + 10 E2E (Playwright) passing
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
- `emhass_adapter.py`: Dynamic deferrable load publishing, index pool 0-49, persistence across restarts
- `vehicle_controller.py`: 4 control strategies (Switch, Service, Script, External) — implemented but not end-to-end tested
- `presence_monitor.py`: Sensor and coordinate-based presence detection, safety logic
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
- Per-trip EMHASS sensor — [`TripEmhassSensor`](custom_components/ev_trip_planner/sensor.py:853) provides per-trip parameters
- Power profile generation — [`async_generate_power_profile()`](custom_components/ev_trip_planner/trip_manager.py:2068)
- Deferrables schedule generation — [`async_generate_deferrables_schedule()`](custom_components/ev_trip_planner/trip_manager.py:2244)
- Retry logic: 3 attempts in 5-minute window
- 398 tests passing, 85%+ coverage
- ⚠️ **NOTE**: Lovelace dashboard auto-import (`dashboard.py`, 1262 lines) still executes on every setup but is DEPRECATED. Users should use the native panel instead.
- ⚠️ **NOT IMPLEMENTED**: `alerta_tiempo_insuficiente` user notifications — code exists in [`async_calcular_energia_necesaria()`](custom_components/ev_trip_planner/trip_manager.py:1545) but **no sensor, notification, or UI element exposes this value**. The user-facing function [`calcular_ventana_carga()`](custom_components/ev_trip_planner/trip_manager.py:1550) returns `es_suficiente` instead. **Feature not exposed to users.**

### SOLID Refactoring (Apr 2026 — feat/solid-refactor-coverage branch)
- `definitions.py`: `TripSensorEntityDescription` dataclass for sensor definitions
- `coordinator.py`: Refactored to comply with SOLID, no direct coupling
- `diagnostics.py`: HACS quality diagnostic support
- High test coverage >80% for all modules
- 793 Python tests + 10 E2E Playwright passing

---

### ⚠️ Vehicle Control — Implemented but NOT Wired to UI

**Status**: Code exists in production, but NOT accessible to users through the config flow.

| Component | File | Lines | Status |
|-----------|------|-------|--------|
| `VehicleControlStrategy` ABC | [`vehicle_controller.py:83`](custom_components/ev_trip_planner/vehicle_controller.py:83) | 430 | ✅ Implemented |
| `SwitchStrategy` | [`vehicle_controller.py:107`](custom_components/ev_trip_planner/vehicle_controller.py:107) | — | ✅ Implemented |
| `ServiceStrategy` | [`vehicle_controller.py:146`](custom_components/ev_trip_planner/vehicle_controller.py:146) | — | ✅ Implemented |
| `ScriptStrategy` | [`vehicle_controller.py:189`](custom_components/ev_trip_planner/vehicle_controller.py:189) | — | ✅ Implemented |
| `ExternalStrategy` | [`vehicle_controller.py:230`](custom_components/ev_trip_planner/vehicle_controller.py:230) | — | ✅ Implemented |
| `VehicleController` | [`vehicle_controller.py:280`](custom_components/ev_trip_planner/vehicle_controller.py:280) | — | ✅ Implemented |
| `PresenceMonitor` | [`presence_monitor.py:34`](custom_components/ev_trip_planner/presence_monitor.py:34) | 770 | ✅ Implemented |
| `ScheduleMonitor` | [`schedule_monitor.py:14`](custom_components/ev_trip_planner/schedule_monitor.py:14) | 324 | ✅ File exists, NEVER instantiated |
| `VehicleScheduleMonitor` | [`schedule_monitor.py:55`](custom_components/ev_trip_planner/schedule_monitor.py:55) | — | ✅ File exists, NEVER used |

**Gap**: `schedule_monitor.py` is **never imported** in `__init__.py`. The `control_strategy` / `control_type` configuration is **NOT exposed** in the config flow. Users cannot select a vehicle control strategy through the UI.

**Impact**: The core "smart charging control" feature (automatic charge start/stop based on EMHASS schedules) does NOT work end-to-end, even though all the code exists.

**Required fix**: Wire `ScheduleMonitor` into `__init__.py` async_setup, add `control_strategy` step to config flow, connect `VehicleController` to the hourly refresh callback.

---

## 🚧 Next: Milestone 4.0.1 — Critical M4 Hotfixes

**Status**: 📋 PLANNED — not started  
**Problem details**: [`doc/gaps/gaps.es.md`](doc/gaps/gaps.es.md)  
**Target**: v0.4.3-dev  
**Priority**: Blocks M4.1 start — these issues prevent EMHASS integration from working correctly in production

### Production-detected problems

After Milestone 4 production validation, critical issues were documented in [`doc/gaps/gaps.es.md`](doc/gaps/gaps.es.md).

### Planned features / Fixes

#### P0 — Critical (blocks EMHASS)

- **🔧 Incorrect EMHASS architecture** (Gap #8)
  - **Problem**: The `EmhassDeferrableLoadSensor` aggregates all trips into a single `power_profile_watts`. EMHASS needs separate deferrable profiles per trip to optimize each charge independently.
  - **Status**: `TripEmhassSensor` implemented at `sensor.py:853` — provides per-trip EMHASS parameters. Architecture gap may still exist if individual trip sensors are not properly published to EMHASS.
  - **Impact**: Without proper per-trip publishing, EMHASS optimizes all trips as a single load
  - **Files**: `sensor.py:853`, `emhass_adapter.py`, `trip_manager.py`, `panel.js`

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

5. **SOH (State of Health) selector NOT IMPLEMENTED**: Code infrastructure exists but there is no UI selector in config flow to configure a SOH sensor. Battery capacity is fixed, not dynamic.

6. **One EMHASS index per trip**: User must manually configure EMHASS snippet for each potential index up to `max_deferrable_loads`. No auto-discovery because EMHASS does not support it.

7. **Manual EMHASS configuration**: Not plug-and-play; requires adding configuration to `configuration.yaml`.

8. **Single optimizer**: Only EMHASS supported. Architecture uses `emhass_adapter.py` as adapter, prepared to add others (Tibber, etc.) in v1.2.

9. **Fixed planning horizon**: 7 days by default, configurable but static. Does not dynamically adapt to EMHASS horizon.

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

**Last updated**: April 25, 2026
**Status review**: After merge of feat/solid-refactor-coverage + full codebase audit (2026-04-25)

---

📬 **Issues and discussions**:
- [GitHub Issues](https://github.com/informatico-madrid/ha-ev-trip-planner/issues)
- [GitHub Discussions](https://github.com/informatico-madrid/ha-ev-trip-planner/discussions)
