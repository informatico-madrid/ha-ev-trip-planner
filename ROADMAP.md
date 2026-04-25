# 🗺️ Roadmap & Milestones - EV Trip Planner

## 📊 Project Status

**Current version**: 0.5.20
**Development phase**: Milestone 4.0.1 planned — not started  
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
- Insufficient time alerts
- 5-step config flow
- Lovelace dashboard with auto-import on config completion
- Retry logic: 3 attempts in 5-minute window
- 398 tests passing, 85%+ coverage

### SOLID Refactoring (Apr 2026 — feat/solid-refactor-coverage branch)
- `definitions.py`: `TripSensorEntityDescription` dataclass for sensor definitions
- `coordinator.py`: Refactored to comply with SOLID, no direct coupling
- `diagnostics.py`: HACS quality diagnostic support
- High test coverage >80% for all modules
- 793 Python tests + 10 E2E Playwright passing

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

#### P2 — Minor

- **🔧 Sidebar not removed when deleting vehicle** (Gap #1)
  - **Problem**: Missing `async_unregister_panel` call in `async_remove_entry_cleanup`
  - **Solution hypothesis**: 1 line in `services.py:1495`
  - **Files**: `services.py`

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

1. **⚠️ EMHASS automatic charge control NOT WORKING**: `schedule_monitor.py` exists in code but is NOT connected to the main flow. The vehicle controller (Switch/Service/Script strategies) is implemented but never activated because schedule_monitor is never instantiated. This is a P0 critical issue blocking the core functionality.
2. **Dashboard charts require apexcharts-card**: The full dashboard with power profile charts (`ev-trip-planner-full.yaml`) requires installing the `apexcharts-card` custom card manually in Home Assistant. Without this dependency, users only see the simple dashboard.
3. **SOH (State of Health) selector NOT IMPLEMENTED**: Code infrastructure exists but there is no UI selector in config flow to configure a SOH sensor. Battery capacity is fixed, not dynamic.
4. **One EMHASS index per trip**: User must manually configure EMHASS snippet for each potential index up to `max_deferrable_loads`. No auto-discovery because EMHASS does not support it.
5. **Manual EMHASS configuration**: Not plug-and-play; requires adding configuration to `configuration.yaml`.
6. **Single optimizer**: Only EMHASS supported. Architecture uses `emhass_adapter.py` as adapter, prepared to add others (Tibber, etc.) in v1.2.
7. **Fixed planning horizon**: 7 days by default, configurable but static. Does not dynamically adapt to EMHASS horizon.

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
- ✅ Single vehicle with automatic charging control
- ✅ Single vehicle with notifications only (no control)
- ✅ Weekly recurrent trips
- ✅ Punctual trips
- ✅ Energy and deadline calculations

### P1 — Should Have (v1.1)
- ⏳ Multi-vehicle with shared line
- ⏳ Dashboard with profile charts

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
├── MILESTONE_4_1_PLANNING.md         # Detailed Milestone 4.1 plan (not started)
├── MILESTONE_4_POWER_PROFILE.md      # M4 charging profile spec (completed)
├── TDD_METHODOLOGY.md                # TDD methodology applied to project
├── TESTING_E2E.md                    # E2E testing guide with Playwright
├── IMPROVEMENTS_POST_MILESTONE3.md   # UX improvements implemented in M3.1/M3.2
└── configuration_examples.yaml       # Complete YAML configuration examples

doc/
└── gaps/
    └── gaps.md                       # Production-detected problems with hypotheses
```

---

## 🤝 How to Contribute

**High priority**:
- Testing with different VE integrations (see pending list above)
- UX feedback on dashboard
- Translations to other languages
- Bug reports

**Medium priority**:
- Additional automation examples
- Performance optimizations

**Low priority** (wait for v1.0):
- Advanced features
- New optimizer integrations

---

**Last updated**: April 2026  
**Status review**: After merge of feat/solid-refactor-coverage  

---

📬 **Issues and discussions**:
- [GitHub Issues](https://github.com/informatico-madrid/ha-ev-trip-planner/issues)
- [GitHub Discussions](https://github.com/informatico-madrid/ha-ev-trip-planner/discussions)
