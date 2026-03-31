# Tasks: EV Trip Planner Integration Fixes

## Phase 1: POC - Fix Critical Bugs

Focus: Implement the 7 bug fixes end-to-end. Skip tests initially.

### BUG-1/2: Fix Panel Duplication (US-1, US-2)

- [x] 1.1 [[P]] [[US-1]] Normalize vehicle_id in __init__.py:471 [use: homeassistant-best-practices]
  Do:
    1. Read `custom_components/ev_trip_planner/__init__.py` around line 471
    2. Change `vehicle_id = entry.data.get("vehicle_name")` to normalize: `entry.data.get("vehicle_name").lower().replace(" ", "_")`
  Files:
    - custom_components/ev_trip_planner/__init__.py (line 471)
  Done when: vehicle_id is normalized to lowercase with underscores at line 471
  Verify: `grep -n "vehicle_id = entry.data.get" custom_components/ev_trip_planner/__init__.py | head -3`
  Commit: `fix(__init__): normalize vehicle_id to lowercase in async_setup_entry`

- [x] 1.2 [[P]] [[US-1]] Remove duplicate async_register_panel from config_flow.py [use: homeassistant-best-practices]
  Do:
    1. Read `custom_components/ev_trip_planner/config_flow.py` lines 835-854
    2. Remove the entire `async_register_panel` block (lines 838-851)
    3. Keep the error handling wrapper comment explaining panel registration is in __init__.py
  Files:
    - custom_components/ev_trip_planner/config_flow.py (lines 835-854)
  Done when: config_flow.py no longer calls async_register_panel
  Verify: `grep -n "async_register_panel" custom_components/ev_trip_planner/config_flow.py`
  Commit: `fix(config_flow): remove duplicate panel registration`

- [x] 1.3 [[P]] [[US-1]] Verify async_unregister_panel uses normalized vehicle_id [use: homeassistant-best-practices]
  Do:
    1. Read `custom_components/ev_trip_planner/__init__.py` around line 729
    2. Confirm `async_unregister_panel(hass, vehicle_id)` uses the normalized vehicle_id from line 471
  Files:
    - custom_components/ev_trip_planner/__init__.py (line 729-752)
  Done when: async_unregister_panel receives normalized vehicle_id
  Verify: `grep -n "async_unregister_panel" custom_components/ev_trip_planner/__init__.py`
  Commit: `fix(__init__): ensure unregister uses normalized vehicle_id`

### BUG-3: Implement Cascade Delete (US-3)

- [x] 1.4 [[P]] [[US-3]] Add async_delete_all_trips() method to TripManager [use: homeassistant-best-practices]
  Do:
    1. Read `custom_components/ev_trip_planner/trip_manager.py` to find existing delete methods
    2. Add new method `async_delete_all_trips()` that:
       - Clears `_recurring_trips` dict
       - Clears `_punctual_trips` dict
       - Calls `async_save_trips()` to persist the empty state
    3. Place method after existing `async_delete_trip` method
  Files:
    - custom_components/ev_trip_planner/trip_manager.py
  Done when: TripManager has async_delete_all_trips() method that clears all trips
  Verify: `grep -n "async_delete_all_trips" custom_components/ev_trip_planner/trip_manager.py`
  Commit: `feat(trip_manager): add async_delete_all_trips for cascade deletion`

### BUG-4: Entity Cleanup on Unload (US-4)

- [x] 1.5 [[P]] [[US-4]] Add async_will_remove_from_hass() to EmhassDeferrableLoadSensor [use: homeassistant-best-practices]
  Do:
    1. Read `custom_components/ev_trip_planner/sensor.py` around line 488-580 for EmhassDeferrableLoadSensor
    2. Add `async_will_remove_from_hass(self)` method that:
       - Checks if `self.trip_manager._emhass_adapter` exists
       - If adapter exists, calls `await adapter.async_cleanup_vehicle_indices()`
    3. Place method after `async_update` method
  Files:
    - custom_components/ev_trip_planner/sensor.py
  Done when: EmhassDeferrableLoadSensor has async_will_remove_from_hass() method
  Verify: `grep -n "async_will_remove_from_hass" custom_components/ev_trip_planner/sensor.py`
  Commit: `fix(sensor): add async_will_remove_from_hass for entity cleanup`

- [ ] 1.6 [VERIFY] Quality checkpoint: Verify first 5 bug fixes import correctly [use: ha-e2e-testing]
  Do:
    1. Run `cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner && python -c "from custom_components.ev_trip_planner import *" 2>&1`
    2. Run `python -c "from custom_components.ev_trip_planner.trip_manager import TripManager"` to verify TripManager imports
    3. Run `python -c "from custom_components.ev_trip_planner.sensor import EmhassDeferrableLoadSensor"` to verify sensor imports
  Verify: All imports succeed without errors
  Done when: All Python imports work correctly
  Commit: `chore: verify imports after first 5 bug fixes`

### BUG-5: Fix EMHASS Entry Lookup (US-5)

- [x] 1.7 [[P]] [[US-5]] Modify EMHASSAdapter to receive ConfigEntry [use: homeassistant-best-practices]
  Do:
    1. Read `custom_components/ev_trip_planner/emhass_adapter.py` lines 28-34
    2. Change `__init__` signature from `vehicle_config: Dict[str, Any]` to `entry: ConfigEntry`
    3. Store `self.entry_id = entry.entry_id`
    4. Use `entry.data.get(CONF_VEHICLE_NAME)` for `self.vehicle_id`
    5. Update all references to `vehicle_config.get(...)` to `entry.data.get(...)`
  Files:
    - custom_components/ev_trip_planner/emhass_adapter.py (lines 28-34 and all vehicle_config references)
  Done when: EMHASSAdapter.__init__ receives ConfigEntry and stores entry_id
  Verify: `grep -n "self.entry_id" custom_components/ev_trip_planner/emhass_adapter.py`
  Commit: `fix(emhass_adapter): receive ConfigEntry and store entry_id`

- [x] 1.8 [[P]] [[US-5]] Update EMHASSAdapter.publish_deferrable_loads to use entry_id [use: homeassistant-best-practices]
  Do:
    1. Read `custom_components/ev_trip_planner/emhass_adapter.py` line 499
    2. Change `sensor_id = f"sensor.emhass_perfil_diferible_{self.vehicle_id}"` to use `self.entry_id`
    3. Ensure sensor naming is consistent with entry_id
  Files:
    - custom_components/ev_trip_planner/emhass_adapter.py (line 499)
  Done when: Sensor ID uses entry_id instead of vehicle_id
  Verify: `grep -n "emhass_perfil_diferible" custom_components/ev_trip_planner/emhass_adapter.py`
  Commit: `fix(emhass_adapter): use entry_id for sensor naming`

- [x] 1.9 [[P]] [[US-5]] Update __init__.py to pass entry to EMHASSAdapter [use: homeassistant-best-practices]
  Do:
    1. Read `custom_components/ev_trip_planner/__init__.py` around line 535
    2. Change `emhass_adapter = EMHASSAdapter(hass, entry.data)` to `emhass_adapter = EMHASSAdapter(hass, entry)`
  Files:
    - custom_components/ev_trip_planner/__init__.py (line 535)
  Done when: __init__.py passes entry (not entry.data) to EMHASSAdapter
  Verify: `grep -n "EMHASSAdapter(hass" custom_components/ev_trip_planner/__init__.py`
  Commit: `fix(__init__): pass ConfigEntry to EMHASSAdapter`

### BUG-6: Fix SOC Display Using Configured Sensor (US-6)

- [x] 1.10 [[P]] [[US-6]] Update ev-trip-planner-simple.yaml SOC sensor reference [use: homeassistant-dashboard-designer]
  Do:
    1. Read `custom_components/ev_trip_planner/dashboard/ev-trip-planner-simple.yaml` line 134
    2. Change `{% set soc_sensor = states('sensor.{{ vehicle_id }}_soc') | default('N/A') %}`
      to `{% set soc_sensor = states('{{ config.soc_sensor }}') | default('N/A') %}`
  Files:
    - custom_components/ev_trip_planner/dashboard/ev-trip-planner-simple.yaml (line 134)
  Done when: Dashboard uses configured soc_sensor instead of hardcoded
  Verify: `grep -n "soc_sensor" custom_components/ev_trip_planner/dashboard/ev-trip-planner-simple.yaml | head -5`
  Commit: `fix(dashboard): use configured soc_sensor in simple dashboard`

- [x] 1.11 [[P]] [[US-6]] Update ev-trip-planner-full.yaml SOC sensor reference [use: homeassistant-dashboard-designer]
  Do:
    1. Read `custom_components/ev_trip_planner/dashboard/ev-trip-planner-full.yaml` line 150
    2. Change `{% set soc_sensor = states('sensor.{{ vehicle_id }}_soc') | default('N/A') %}`
      to `{% set soc_sensor = states('{{ config.soc_sensor }}') | default('N/A') %}`
  Files:
    - custom_components/ev_trip_planner/dashboard/ev-trip-planner-full.yaml (line 150)
  Done when: Dashboard uses configured soc_sensor instead of hardcoded
  Verify: `grep -n "soc_sensor" custom_components/ev_trip_planner/dashboard/ev-trip-planner-full.yaml | head -5`
  Commit: `fix(dashboard): use configured soc_sensor in full dashboard`

### BUG-7: kWh Auto-Calculation (US-7)

- [x] 1.12 [[P]] [[US-7]] Update ev-trip-planner-simple.yaml kWh field to readonly auto-calc [use: homeassistant-dashboard-designer]
  Do:
    1. Read `custom_components/ev_trip_planner/dashboard/ev-trip-planner-simple.yaml` lines 229-234
    2. Change kwh input_number to mode: display (readonly)
    3. Add template value: `{{ states('input_number.{{ vehicle_id }}_trip_km') | float * consumption / 100 }}`
    4. Verify the template contains the correct calculation formula
  Files:
    - custom_components/ev_trip_planner/dashboard/ev-trip-planner-simple.yaml (lines 229-234)
  Done when: kWh field is readonly (mode: display) and auto-calculated with correct formula
  Verify: `grep -n "mode: display" custom_components/ev_trip_planner/dashboard/ev-trip-planner-simple.yaml && grep -n "trip_kwh" custom_components/ev_trip_planner/dashboard/ev-trip-planner-simple.yaml`
  Commit: `fix(dashboard): make kWh readonly auto-calculated in simple dashboard`

- [x] 1.13 [[P]] [[US-7]] Update ev-trip-planner-full.yaml kWh field to readonly auto-calc [use: homeassistant-dashboard-designer]
  Do:
    1. Read `custom_components/ev_trip_planner/dashboard/ev-trip-planner-full.yaml` lines 239-244
    2. Change kwh input_number to mode: display (readonly)
    3. Add template value that calculates kWh from km * consumption / 100
    4. Verify the template contains the correct calculation formula
  Files:
    - custom_components/ev_trip_planner/dashboard/ev-trip-planner-full.yaml (lines 239-244, 317-318)
  Done when: kWh field is readonly (mode: display) and auto-calculated with correct formula
  Verify: `grep -n "mode: display" custom_components/ev_trip_planner/dashboard/ev-trip-planner-full.yaml && grep -n "trip_kwh" custom_components/ev_trip_planner/dashboard/ev-trip-planner-full.yaml`
  Commit: `fix(dashboard): make kWh readonly auto-calculated in full dashboard`

- [ ] 1.14 [VERIFY] Quality checkpoint: Verify all imports after bug fixes [use: ha-e2e-testing]
  Do:
    1. Run `python -c "from custom_components.ev_trip_planner import *" 2>&1`
    2. Run `python -c "from custom_components.ev_trip_planner.trip_manager import TripManager"` to verify TripManager imports
    3. Run `python -c "from custom_components.ev_trip_planner.sensor import EmhassDeferrableLoadSensor"` to verify sensor imports
    4. Run `python -c "from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter"` to verify adapter imports
  Verify: All imports succeed without errors
  Done when: All Python imports work correctly
  Commit: `chore: verify imports after all bug fixes`

## Phase 2: Refactoring

- [x] 2.1 [[P]] Verify consistent vehicle_id normalization in __init__.py [use: homeassistant-best-practices]
  Do:
    1. Read `custom_components/ev_trip_planner/__init__.py` around line 729
    2. Ensure vehicle_id normalization is applied before async_unregister_panel call
    3. Verify consistency between setup and unload
  Files:
    - custom_components/ev_trip_planner/__init__.py
  Done when: Unload uses same normalized vehicle_id as setup
  Verify: Code review of vehicle_id usage in __init__.py - both setup and unload use same normalization
  Commit: `refactor(__init__): ensure consistent vehicle_id normalization`

- [x] 2.2 [[P]] Verify EMHASSAdapter entry_id naming consistency [use: homeassistant-best-practices]
  Do:
    1. Verify all EMHASS sensor naming uses entry_id consistently
    2. Verify adapter is passed ConfigEntry (not entry.data) everywhere
  Files:
    - custom_components/ev_trip_planner/emhass_adapter.py
    - custom_components/ev_trip_planner/__init__.py
  Done when: All EMHASS sensor names use entry_id
  Verify: `grep -n "entry_id" custom_components/ev_trip_planner/emhass_adapter.py`
  Commit: `refactor(emhass_adapter): ensure entry_id naming consistency`

## Phase 3: Testing

- [ ] 3.1 [US-1] [VERIFY:TEST] Test: Verify single panel registration (no duplicate) [use: ha-e2e-testing]
  Do:
    1. Run existing tests: `pytest tests/test_config_flow.py -v -k "panel" 2>&1`
    2. Or run all config_flow tests: `pytest tests/test_config_flow.py -v`
  Files:
    - tests/test_config_flow.py
  Done when: Config flow tests pass
  Verify: `pytest tests/test_config_flow.py -v --tb=short 2>&1 | tail -30`
  Commit: `test(config_flow): verify single panel registration`

- [ ] 3.2 [US-3] [VERIFY:TEST] Test: Verify async_delete_all_trips exists and works [use: ha-e2e-testing]
  Do:
    1. Run: `pytest tests/test_trip_manager.py -v -k "delete_all" 2>&1`
    2. If no specific test exists, run full trip_manager tests: `pytest tests/test_trip_manager.py -v`
  Files:
    - tests/test_trip_manager.py
  Done when: Trip manager tests pass
  Verify: `pytest tests/test_trip_manager.py -v --tb=short 2>&1 | tail -30`
  Commit: `test(trip_manager): verify cascade delete works`

- [ ] 3.3 [US-4] [VERIFY:TEST] Test: Verify EmhassDeferrableLoadSensor cleanup [use: ha-e2e-testing]
  Do:
    1. Run: `pytest tests/test_sensor*.py -v 2>&1` to find sensor tests
    2. Check for tests covering async_will_remove_from_hass
  Files:
    - tests/test_sensor.py (or tests/test_deferrable_load_sensors.py if it exists)
  Done when: Sensor cleanup tests pass
  Verify: `pytest tests/ -v -k "sensor" --tb=short 2>&1 | tail -30`
  Commit: `test(sensor): verify entity cleanup on unload`

- [ ] 3.4 [US-5] [VERIFY:TEST] Test: Verify EMHASS entry lookup uses entry_id [use: ha-e2e-testing]
  Do:
    1. Run: `pytest tests/test_emhass_adapter.py -v 2>&1`
  Files:
    - tests/test_emhass_adapter.py
  Done when: EMHASS adapter tests pass
  Verify: `pytest tests/test_emhass_adapter.py -v --tb=short 2>&1 | tail -30`
  Commit: `test(emhass_adapter): verify entry_id lookup`

- [ ] 3.5 [US-6] [VERIFY:TEST] Test: Verify SOC uses configured sensor [use: ha-e2e-testing]
  Do:
    1. Run: `pytest tests/test_dashboard.py -v 2>&1`
  Files:
    - tests/test_dashboard.py
  Done when: Dashboard tests pass
  Verify: `pytest tests/test_dashboard.py -v --tb=short 2>&1 | tail -30`
  Commit: `test(dashboard): verify SOC from configured sensor`

- [ ] 3.6 [US-7] [VERIFY:TEST] Test: Verify kWh auto-calculation [use: ha-e2e-testing]
  Do:
    1. Run: `pytest tests/test_dashboard.py -v -k "kwh" 2>&1`
    2. Or run all dashboard tests: `pytest tests/test_dashboard.py -v`
  Files:
    - tests/test_dashboard.py
  Done when: kWh calculation tests pass
  Verify: `pytest tests/test_dashboard.py -v --tb=short 2>&1 | tail -30`
  Commit: `test(dashboard): verify kWh auto-calculation`

- [ ] 3.7 [US-1] [VERIFY:BROWSER] E2E: Add vehicle "Chispitas" and verify single panel [use: ha-e2e-testing]
  Do:
    1. Add vehicle named "Chispitas" via HA UI
    2. Verify exactly ONE panel appears in sidebar
    3. Verify URL is /ev-trip-planner-chispitas (lowercase)
  Files:
    - E2E test in tests/e2e/
  Done when: E2E test passes
  Verify: Manual verification or Playwright test
  Commit: `test(e2e): verify single panel for vehicle`

- [ ] 3.8 [US-3] [VERIFY:BROWSER] E2E: Delete integration and verify trips removed [use: ha-e2e-testing]
  Do:
    1. Create trips for a vehicle
    2. Delete the vehicle integration
    3. Verify trips are removed from storage
  Files:
    - E2E test in tests/e2e/
  Done when: E2E test passes
  Verify: Manual verification or Playwright test
  Commit: `test(e2e): verify cascade delete of trips`

- [ ] 3.9 [US-5] [VERIFY:BROWSER] E2E: EMHASS sensor shows 3600W (not 0W) [use: ha-e2e-testing]
  Do:
    1. Configure EMHASS with a vehicle
    2. Create a trip requiring charging
    3. Verify sensor shows 3600W during charging window
  Files:
    - E2E test in tests/e2e/
  Done when: E2E test passes - sensor shows correct power
  Verify: Manual verification in HA developer tools
  Commit: `test(e2e): verify EMHASS shows correct power`

- [ ] 3.10 [VERIFY] Quality checkpoint: Run full test suite [use: ha-e2e-testing]
  Do:
    1. Run: `pytest tests/ -v --tb=short 2>&1`
    2. Count passed/failed tests
  Verify: All tests pass with minimal failures
  Done when: Test suite passes
  Commit: `chore: run full test suite`

## Phase 4: Quality Gates

- [ ] 4.1 [VERIFY] Local type check [use: homeassistant-best-practices]
  Do:
    1. Run mypy: `python -m mypy custom_components/ev_trip_planner/ --ignore-missing-imports 2>&1`
  Verify: No type errors
  Done when: mypy passes
  Commit: `fix(types): address type errors if any`

- [ ] 4.2 [VERIFY] Local lint check [use: homeassistant-best-practices]
  Do:
    1. Run ruff: `python -m ruff check custom_components/ev_trip_planner/ 2>&1`
  Verify: No critical lint errors
  Done when: ruff passes
  Commit: `fix(lint): address lint errors if any`

- [ ] 4.3 Create PR and verify CI [use: ha-e2e-testing]
  Do:
    1. Verify branch: `git branch --show-current`
    2. Add and commit all changes: `git add -A && git commit -m "fix: resolve 7 critical bugs in EV Trip Planner integration"`
    3. Push: `git push -u origin HEAD`
    4. Create PR using gh CLI
  Verify: CI pipeline shows all green checks
  Done when: PR created and CI passes
  Commit: None

- [ ] 4.4 [VERIFY] Final verification: All acceptance criteria [use: ha-e2e-testing]
  Do:
    1. Read requirements.md and verify each US acceptance criteria
    2. Run final test suite
  Verify: All 7 user stories have working fixes
  Done when: All acceptance criteria met
  Commit: None

## Notes

### Skills Available for Implementation
- `homeassistant-best-practices` - For HA patterns, panel registration, config entries, entity cleanup
- `homeassistant-dashboard-designer` - For dashboard YAML changes (SOC, kWh)
- `ha-e2e-testing` - For verification tests and E2E validation

### POC Shortcuts Taken
- No unit tests written in Phase 1 (using existing test infrastructure)
- Dashboard YAML changes use hardcoded consumption reference (may need refinement)

### Production TODOs
- Add unit test for async_delete_all_trips() method
- Add unit test for EmhassDeferrableLoadSensor.async_will_remove_from_hass()
- Verify consumption value retrieval in dashboard kWh auto-calculation

### Dependencies
- Home Assistant Core >= 2024.x
- pytest with asyncio_mode enabled
- ruff for linting, mypy for type checking
