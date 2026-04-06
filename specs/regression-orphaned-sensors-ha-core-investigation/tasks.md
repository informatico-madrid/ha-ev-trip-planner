# Tasks: regression-orphaned-sensors-ha-core-investigation

## Phase 0: Characterization Tests (6 tests - all FAIL today)

- [ ] 0.1 [RED] Failing test: test_sensor_unique_id_exists_after_setup
  - **Do**: Write characterization test in `tests/test_entity_registry.py` asserting that after `async_setup_entry`, all 8 sensors (7 TripPlanner + 1 Emhass) have `unique_id` set in the entity registry. This test documents the broken behavior: sensors currently lack unique_id.
  - **Files**: `tests/test_entity_registry.py` (CREATE)
  - **Done when**: Test exists, runs, and fails with AssertionError (no unique_id set on sensors)
  - **Verify**: `.venv/bin/pytest tests/test_entity_registry.py::test_sensor_unique_id_exists_after_setup -v 2>&1 | grep -q "FAILED\|AssertionError" && echo RED_PASS`
  - **Commit**: `test(phase-0): red - failing test for sensor unique_id after setup`
  - _Requirements: Phase 0 characterization_

- [ ] 0.2 [RED] Failing test: test_sensor_removed_after_unload
  - **Do**: Write characterization test asserting that after `async_unload_entry`, the entity registry has 0 entries for this config entry. Documents broken behavior: sensors become orphaned zombies.
  - **Files**: `tests/test_entity_registry.py`
  - **Done when**: Test exists, runs, and fails (orphaned sensors remain)
  - **Verify**: `.venv/bin/pytest tests/test_entity_registry.py::test_sensor_removed_after_unload -v 2>&1 | grep -q "FAILED\|AssertionError" && echo RED_PASS`
  - **Commit**: `test(phase-0): red - failing test for sensor cleanup after unload`
  - _Requirements: Phase 0 characterization_

- [ ] 0.3 [RED] Failing test: test_trip_sensor_created_in_registry_after_add
  - **Do**: Write characterization test asserting that after calling the add_trip service, a TripSensor appears in the entity registry. Documents broken behavior: `async_create_trip_sensor()` creates orphan Python objects (stored in `hass.data`) but never calls `async_add_entities()`.
  - **Files**: `tests/test_entity_registry.py`
  - **Done when**: Test exists, runs, and fails (TripSensor not in registry, only in `hass.data`)
  - **Verify**: `.venv/bin/pytest tests/test_entity_registry.py::test_trip_sensor_created_in_registry_after_add -v 2>&1 | grep -q "FAILED\|AssertionError" && echo RED_PASS`
  - **Commit**: `test(phase-0): red - failing test for trip sensor in registry after add`
  - _Requirements: Phase 0 characterization_

- [ ] 0.4 [RED] Failing test: test_trip_sensor_removed_from_registry_after_delete
  - **Do**: Write characterization test asserting that after delete_trip service, the registry entry is gone. Documents broken behavior: `async_remove_trip_sensor()` only deletes from dict, never calls `entity_registry.async_remove()`.
  - **Files**: `tests/test_entity_registry.py`
  - **Done when**: Test exists, runs, and fails (zombie entries remain)
  - **Verify**: `.venv/bin/pytest tests/test_entity_registry.py::test_trip_sensor_removed_from_registry_after_delete -v 2>&1 | grep -q "FAILED\|AssertionError" && echo RED_PASS`
  - **Commit**: `test(phase-0): red - failing test for trip sensor removal from registry`
  - _Requirements: Phase 0 characterization_

- [ ] 0.5 [RED] Failing test: test_no_duplicate_sensors_after_reload
  - **Do**: Write characterization test asserting that sensor count before and after reload is the same (no duplicates). Documents broken behavior: reload creates duplicate sensors because existing ones lack unique_id.
  - **Files**: `tests/test_entity_registry.py`
  - **Done when**: Test exists, runs, and fails (count doubles after reload)
  - **Verify**: `.venv/bin/pytest tests/test_entity_registry.py::test_no_duplicate_sensors_after_reload -v 2>&1 | grep -q "FAILED\|AssertionError" && echo RED_PASS`
  - **Commit**: `test(phase-0): red - failing test for no duplicates after reload`
  - _Requirements: Phase 0 characterization_

- [ ] 0.6 [RED] Failing test: test_two_vehicles_no_unique_id_collision
  - **Do**: Write characterization test asserting that unique_ids from two different vehicles are globally unique. Documents broken behavior: collision possible because TripSensor unique_id is just `trip_{trip_id}` without vehicle prefix.
  - **Files**: `tests/test_entity_registry.py`
  - **Done when**: Test exists, runs, and fails (collision or overlap possible)
  - **Verify**: `.venv/bin/pytest tests/test_entity_registry.py::test_two_vehicles_no_unique_id_collision -v 2>&1 | grep -q "FAILED\|AssertionError" && echo RED_PASS`
  - **Commit**: `test(phase-0): red - failing test for unique_id collision across vehicles`
  - _Requirements: Phase 0 characterization_

- [ ] V0 [VERIFY] Quality checkpoint: Phase 0 tests run and fail as expected
  - **Do**: Run all 6 Phase 0 tests, verify they all fail (characterize broken behavior)
  - **Verify**: `.venv/bin/pytest tests/test_entity_registry.py -v 2>&1 | grep -E "^(tests/|PASSED|FAILED)" | head -20`
  - **Done when**: All 6 tests FAIL (documenting broken behavior)
  - **Commit**: `chore(phase-0): verify all 6 characterization tests fail as expected`

## Phase 1: definitions.py + TripPlannerSensor Refactor

- [ ] 1.1 [GREEN] Create definitions.py with TripSensorEntityDescription dataclass
  - **Do**: Create `custom_components/ev_trip_planner/definitions.py` with `TripSensorEntityDescription` dataclass (frozen=True, extends SensorEntityDescription) and `TRIP_SENSORS` tuple with 7 sensor descriptions (recurring_trips_count, punctual_trips_count, trips_list, kwh_needed_today, hours_needed_today, next_trip, next_deadline). Each description has `value_fn` and `attrs_fn` callables.
  - **Files**: `custom_components/ev_trip_planner/definitions.py` (CREATE)
  - **Done when**: File created with correct dataclass and 7 sensor descriptions
  - **Verify**: `.venv/bin/python -c "from custom_components.ev_trip_planner.definitions import TripSensorEntityDescription, TRIP_SENSORS; print(len(TRIP_SENSORS))"` outputs `7`
  - **Commit**: `feat(phase-1): add definitions.py with TripSensorEntityDescription and TRIP_SENSORS tuple`
  - _Requirements: FR-1_
  - **[P]**

- [ ] 1.2 [GREEN] Create coordinator.py with TripPlannerCoordinator
  - **Do**: Create `custom_components/ev_trip_planner/coordinator.py` with `TripPlannerCoordinator(DataUpdateCoordinator)`. The coordinator holds `coordinator.data` shape: `{"recurring_trips": {}, "punctual_trips": {}, "kwh_today": float, "hours_today": float, "next_trip": {}}`. `_async_update_data()` reads from trip_manager and builds this dict.
  - **Files**: `custom_components/ev_trip_planner/coordinator.py` (CREATE)
  - **Done when**: TripPlannerCoordinator class created, DataUpdateCoordinator subclass, correct data shape
  - **Verify**: `.venv/bin/python -c "from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator; print('ok')"`
  - **Commit**: `feat(phase-1): add coordinator.py with TripPlannerCoordinator`
  - _Requirements: FR-3_
  - **[P]**

- [ ] 1.3 [GREEN] Refactor TripPlannerSensor to use CoordinatorEntity pattern
  - **Do**: In `sensor.py`, replace `class TripPlannerSensor(SensorEntity)` with `class TripPlannerSensor(CoordinatorEntity[TripPlannerCoordinator], SensorEntity)`. Uses `self.coordinator` instead of `self.trip_manager`. Reads from `coordinator.data` via `entity_description.value_fn()`. Sets `_attr_unique_id = f"{DOMAIN}_{vehicle_id}_{description.key}"`.
  - **Files**: `custom_components/ev_trip_planner/sensor.py`
  - **Done when**: TripPlannerSensor inherits CoordinatorEntity, no longer has `async_update()` polling
  - **Verify**: `.venv/bin/pytest tests/test_sensor.py -v -k "TripPlannerSensor" 2>&1 | tail -5`
  - **Commit**: `refactor(phase-1): TripPlannerSensor inherits CoordinatorEntity`
  - _Requirements: FR-2, FR-3_
  - **[P]**

- [ ] 1.4 [GREEN] Remove 7 TripPlannerSensor subclasses
  - **Do**: Remove `RecurringTripsCountSensor`, `PunctualTripsCountSensor`, `TripsListSensor`, `KwhTodaySensor`, `HoursTodaySensor`, `NextTripSensor`, `NextDeadlineSensor` from `sensor.py`. Replace with single `TripPlannerSensor` class using `TRIP_SENSORS` from definitions.py.
  - **Files**: `custom_components/ev_trip_planner/sensor.py`
  - **Done when**: 7 old subclasses removed, single class with entity descriptions used
  - **Verify**: `.venv/bin/python -c "from custom_components.ev_trip_planner.sensor import TripPlannerSensor; print('ok')"`
  - **Commit**: `refactor(phase-1): remove 7 sensor subclasses, use single TripPlannerSensor`
  - _Requirements: FR-2_
  - **[P]**

- [ ] 1.5 [GREEN] Remove MagicMock from sensor.py production code
  - **Do**: In sensor.py, remove all `from unittest.mock import MagicMock` imports. Replace any `if coordinator is None: return` (MagicMock guard) with `raise ValueError("coordinator is required")`. All sensors must require a valid coordinator.
  - **Files**: `custom_components/ev_trip_planner/sensor.py`
  - **Done when**: Zero `MagicMock` imports in sensor.py
  - **Verify**: `grep -c "MagicMock" custom_components/ev_trip_planner/sensor.py` returns `0`
  - **Commit**: `refactor(phase-1): remove MagicMock from production code, raise ValueError if coordinator None`
  - _Requirements: FR-4_
  - **[P]**

- [ ] 1.6 [GREEN] Update sensor platform async_setup_entry to use new TripPlannerSensor
  - **Do**: In `sensor.py` `async_setup_entry`, update sensor creation to use new `TripPlannerSensor(runtime_data.coordinator, vehicle_id, description)` pattern. Create instances from `TRIP_SENSORS` tuple instead of subclass constructors.
  - **Files**: `custom_components/ev_trip_planner/sensor.py`
  - **Done when**: Platform setup creates sensors from TRIP_SENSORS descriptions
  - **Verify**: `.venv/bin/pytest tests/test_sensor_setup_entry_core.py -v 2>&1 | tail -10`
  - **Commit**: `refactor(phase-1): platform setup uses new TripPlannerSensor pattern`
  - _Requirements: FR-2_

- [ ] V1 [VERIFY] Quality checkpoint: Phase 1 lint + type check + sensor tests
  - **Do**: Run lint, type check, and sensor tests
  - **Verify**: `.venv/bin/python -m flake8 custom_components/ev_trip_planner/sensor.py custom_components/ev_trip_planner/definitions.py custom_components/ev_trip_planner/coordinator.py && .venv/bin/python -m mypy custom_components/ev_trip_planner/sensor.py custom_components/ev_trip_planner/definitions.py custom_components/ev_trip_planner/coordinator.py && .venv/bin/pytest tests/test_sensor.py -v --tb=short 2>&1 | tail -15`
  - **Done when**: No lint errors, no type errors, tests pass
  - **Commit**: `chore(phase-1): pass quality checkpoint`

## Phase 2: TripSensor Lifecycle

- [ ] 2.1 [GREEN] Create TripSensor using CoordinatorEntity pattern
  - **Do**: Create new `TripSensor(CoordinatorEntity[TripPlannerCoordinator], SensorEntity)` class in `sensor.py`. Reads trip data from `coordinator.data["recurring_trips"][trip_id]` or `coordinator.data["punctual_trips"][trip_id]`. Sets `_attr_unique_id = f"{DOMAIN}_{vehicle_id}_trip_{trip_id}"`.
  - **Files**: `custom_components/ev_trip_planner/sensor.py`
  - **Done when**: TripSensor inherits CoordinatorEntity, reads from coordinator.data
  - **Verify**: `.venv/bin/python -c "from custom_components.ev_trip_planner.sensor import TripSensor; print('ok')"`
  - **Commit**: `feat(phase-2): add CoordinatorEntity-based TripSensor class`
  - _Requirements: FR-5_

- [ ] 2.2 [GREEN] Add entity_registry.async_remove() on trip delete
  - **Do**: In `async_remove_trip_sensor` (sensor.py), add entity registry cleanup: `entity_registry = er.async_get(hass); for entry in er.async_entries_for_config_entry(entity_registry, entry_id): if trip_id in entry.unique_id: entity_registry.async_remove(entry.entity_id)`.
  - **Files**: `custom_components/ev_trip_planner/sensor.py`
  - **Done when**: Deleting a trip also removes its registry entry
  - **Verify**: `.venv/bin/pytest tests/test_entity_registry.py::test_trip_sensor_removed_from_registry_after_delete -v 2>&1 | tail -5`
  - **Commit**: `fix(phase-2): add entity_registry.async_remove on trip delete`
  - _Requirements: FR-7_

- [ ] 2.3 [GREEN] TripSensor created via platform setup using async_add_entities
  - **Do**: In sensor.py `async_setup_entry`, create TripSensor instances for existing trips using the `async_add_entities` callback passed by HA. HA passes `async_add_entities` ONLY to platform setup. Do NOT store it in entry.runtime_data.
  - **Files**: `custom_components/ev_trip_planner/sensor.py`
  - **Done when**: TripSensors created during platform setup via async_add_entities
  - **Verify**: `.venv/bin/pytest tests/test_sensor.py -v -k "trip_sensor" 2>&1 | tail -10`
  - **Commit**: `feat(phase-2): create TripSensors via platform setup async_add_entities`
  - _Requirements: FR-6_

- [ ] 2.4 [GREEN] Fix async_create_trip_sensor to use async_add_entities
  - **Do**: Refactor `async_create_trip_sensor` to call `async_add_entities([sensor])` instead of storing in `hass.data[...]` dict. Store a reference to the async_add_entities callable so service handlers can use it.
  - **Files**: `custom_components/ev_trip_planner/sensor.py`
  - **Done when**: TripSensors created via service are registered in entity registry
  - **Verify**: `.venv/bin/pytest tests/test_entity_registry.py::test_trip_sensor_created_in_registry_after_add -v 2>&1 | tail -5`
  - **Commit**: `fix(phase-2): async_create_trip_sensor uses async_add_entities not dict storage`
  - _Requirements: FR-6_

- [ ] 2.5 [GREEN] Update __init__.py EVTripRuntimeData dataclass
  - **Do**: Create `@dataclass class EVTripRuntimeData` in `__init__.py` with fields: `coordinator: TripPlannerCoordinator`, `trip_manager: TripManager`. Replace all `hass.data[DATA_RUNTIME][namespace]` accesses with `entry.runtime_data`.
  - **Files**: `custom_components/ev_trip_planner/__init__.py`
  - **Done when**: EVTripRuntimeData dataclass exists, used for all runtime data access
  - **Verify**: `.venv/bin/python -c "from custom_components.ev_trip_planner import EVTripRuntimeData; print('ok')"`
  - **Commit**: `refactor(phase-2): add EVTripRuntimeData dataclass to __init__.py`
  - _Requirements: FR-6_

- [ ] V2 [VERIFY] Quality checkpoint: Phase 2 type check + entity registry tests
  - **Do**: Run type check on modified files and entity registry tests
  - **Verify**: `.venv/bin/python -m mypy custom_components/ev_trip_planner/__init__.py custom_components/ev_trip_planner/sensor.py && .venv/bin/pytest tests/test_entity_registry.py -v 2>&1 | tail -20`
  - **Done when**: No type errors, Phase 0 tests progressing
  - **Commit**: `chore(phase-2): pass quality checkpoint`

## Phase 3: EMHASS Single Path

- [ ] 3.1 [GREEN] Remove hass.states.async_set() from emhass_adapter.py
  - **Do**: Remove all `hass.states.async_set()` calls from `emhass_adapter.py`. These include the main `publish_deferrable_loads()` call at line ~534 and all other `async_set` calls in the file. The EMHASS data should flow through coordinator instead.
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: Zero `async_set` calls remain in emhass_adapter.py
  - **Verify**: `grep -c "async_set" custom_components/ev_trip_planner/emhass_adapter.py` returns `0`
  - **Commit**: `fix(phase-3): remove hass.states.async_set calls from emhass_adapter`
  - _Requirements: FR-8_
  - **[P]**

- [ ] 3.2 [GREEN] Make publish_deferrable_loads call coordinator.async_request_refresh()
  - **Do**: In `emhass_adapter.py`, replace `hass.states.async_set()` with `entry.runtime_data.coordinator.async_request_refresh()`. Store computed EMHASS data so coordinator.data includes it for EmhassDeferrableLoadSensor to read.
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: publish_deferrable_loads triggers coordinator refresh instead of direct state set
  - **Verify**: `grep -c "async_request_refresh" custom_components/ev_trip_planner/emhass_adapter.py`
  - **Commit**: `fix(phase-3): publish_deferrable_loads uses coordinator refresh`
  - _Requirements: FR-9_
  - **[P]**

- [ ] 3.3 [GREEN] Make EmhassDeferrableLoadSensor inherit from CoordinatorEntity
  - **Do**: In `sensor.py`, change `class EmhassDeferrableLoadSensor(SensorEntity)` to `class EmhassDeferrableLoadSensor(CoordinatorEntity[TripPlannerCoordinator], SensorEntity)`. Read EMHASS data from `coordinator.data` instead of calling `trip_manager` directly. Keep `_attr_unique_id = f"emhass_perfil_diferible_{entry_id}"`.
  - **Files**: `custom_components/ev_trip_planner/sensor.py`
  - **Done when**: EmhassDeferrableLoadSensor inherits CoordinatorEntity, reads from coordinator.data
  - **Verify**: `.venv/bin/pytest tests/test_deferrable_load_sensors.py -v 2>&1 | tail -10`
  - **Commit**: `fix(phase-3): EmhassDeferrableLoadSensor inherits CoordinatorEntity`
  - _Requirements: FR-10_

- [ ] 3.4 [GREEN] Update coordinator.data to include EMHASS fields
  - **Do**: Update `TripPlannerCoordinator._async_update_data()` to include EMHASS data: `coordinator.data["emhass_power_profile"]` and `coordinator.data["emhass_deferrables_schedule"]`. This data comes from emhass_adapter computation.
  - **Files**: `custom_components/ev_trip_planner/coordinator.py`
  - **Done when**: coordinator.data includes EMHASS fields read by EmhassDeferrableLoadSensor
  - **Verify**: `.venv/bin/python -c "from custom_components.ev_trip_planner.coordinator import TripPlannerCoordinator; print('ok')"`
  - **Commit**: `feat(phase-3): coordinator.data includes EMHASS fields`
  - _Requirements: FR-10_

- [ ] V3 [VERIFY] Quality checkpoint: Phase 3 lint + type check + EMHASS tests
  - **Do**: Run lint, type check, and EMHASS-related tests
  - **Verify**: `.venv/bin/python -m flake8 custom_components/ev_trip_planner/emhass_adapter.py custom_components/ev_trip_planner/sensor.py custom_components/ev_trip_planner/coordinator.py && .venv/bin/python -m mypy custom_components/ev_trip_planner/emhass_adapter.py custom_components/ev_trip_planner/sensor.py custom_components/ev_trip_planner/coordinator.py && .venv/bin/pytest tests/test_deferrable_load_sensors.py tests/test_emhass_adapter.py -v 2>&1 | tail -15`
  - **Done when**: No lint errors, no type errors, EMHASS tests pass
  - **Commit**: `chore(phase-3): pass quality checkpoint`

## Phase 4: __init__.py Extraction

- [ ] 4.1 [GREEN] Extract service handlers to services.py
  - **Do**: Create `custom_components/ev_trip_planner/services.py`. Move all service handler functions (handle_add_trip, handle_delete_trip, etc.) from `__init__.py` to this new file. Register services in `__init__.py` by importing from services.py.
  - **Files**: `custom_components/ev_trip_planner/services.py` (CREATE), `custom_components/ev_trip_planner/__init__.py` (MODIFY)
  - **Done when**: Service handlers in services.py, __init__.py imports and registers them
  - **Verify**: `.venv/bin/python -c "from custom_components.ev_trip_planner.services import handle_add_trip; print('ok')"`
  - **Commit**: `refactor(phase-4): extract service handlers to services.py`
  - _Requirements: FR-12_
  - **[P]**

- [ ] 4.2 [GREEN] Reduce __init__.py to under 150 lines
  - **Do**: In `__init__.py`, keep only: `PLATFORMS` constant, `EVTripRuntimeData` dataclass, `async_setup_entry`, `async_unload_entry`, `async_remove_entry`, `async_migrate_entry`. Move everything else to services.py or coordinator.py. Ensure total line count is under 150.
  - **Files**: `custom_components/ev_trip_planner/__init__.py`
  - **Done when**: __init__.py < 150 lines, contains only lifecycle code
  - **Verify**: `wc -l custom_components/ev_trip_planner/__init__.py` outputs `< 150`
  - **Commit**: `refactor(phase-4): reduce __init__.py to lifecycle only (<150 lines)`
  - _Requirements: FR-11_

- [ ] 4.3 [GREEN] Ensure all data access uses entry.runtime_data
  - **Do**: Replace all `hass.data[DATA_RUNTIME][namespace]` accesses in services.py and sensor.py with `entry.runtime_data`. Ensure EVTripRuntimeData dataclass has all needed fields.
  - **Files**: `custom_components/ev_trip_planner/services.py`, `custom_components/ev_trip_planner/__init__.py`, `custom_components/ev_trip_planner/sensor.py`
  - **Done when**: Zero `hass.data[DATA_RUNTIME]` accesses remain in production code
  - **Verify**: `grep -c "hass.data\[DATA_RUNTIME\]" custom_components/ev_trip_planner/services.py custom_components/ev_trip_planner/sensor.py` returns `0`
  - **Commit**: `refactor(phase-4): use entry.runtime_data instead of hass.data[DATA_RUNTIME]`
  - _Requirements: FR-13_

- [ ] V4 [VERIFY] Quality checkpoint: Phase 4 full test suite
  - **Do**: Run full test suite to verify no regressions from extraction
  - **Verify**: `.venv/bin/pytest tests/ -v --ignore=tests/e2e --ignore=tests/ha-manual -x 2>&1 | tail -30`
  - **Done when**: All tests pass, __init__.py < 150 lines
  - **Commit**: `chore(phase-4): pass quality checkpoint`

## Phase 5: Global Cleanup

- [ ] 5.1 [GREEN] Remove legacy namespace fallback patterns
  - **Do**: Search for and remove all `f"ev_trip_planner_{entry_id}"` and `f"{DOMAIN}_{entry_id}"` legacy patterns. Replace with direct `entry.entry_id` usage. These were fallbacks for old namespace patterns.
  - **Files**: `custom_components/ev_trip_planner/__init__.py`, `custom_components/ev_trip_planner/services.py`, `custom_components/ev_trip_planner/sensor.py`
  - **Done when**: Legacy namespace patterns removed
  - **Verify**: `grep -r "ev_trip_planner_" custom_components/ev_trip_planner/*.py | grep -v "__pycache__" | wc -l` returns `0`
  - **Commit**: `refactor(phase-5): remove legacy namespace fallback patterns`
  - _Requirements: FR-14_
  - **[P]**

- [ ] 5.2 [GREEN] Verify zero MagicMock imports in production code
  - **Do**: Confirm no `from unittest.mock import MagicMock` in any `custom_components/ev_trip_planner/*.py` files (excluding tests/). If found, remove or replace with proper typing.
  - **Files**: `custom_components/ev_trip_planner/*.py`
  - **Done when**: Zero MagicMock imports in custom_components/
  - **Verify**: `grep -r "MagicMock" custom_components/ev_trip_planner/*.py | grep -v "__pycache__" | wc -l` returns `0`
  - **Commit**: `refactor(phase-5): verify zero MagicMock in production code`
  - _Requirements: FR-15_
  - **[P]**

- [ ] 5.3 [GREEN] Replace WARNING debug spam with DEBUG level
  - **Do**: Replace `_LOGGER.warning("=== async_setup_entry START ===")` and similar debug-only WARNING logs with `_LOGGER.debug()`. Keep WARNING for recoverable anomalies (retries, missing optional config) and ERROR for critical failures.
  - **Files**: `custom_components/ev_trip_planner/__init__.py`
  - **Done when**: Debug flow logs use DEBUG level, not WARNING
  - **Verify**: `grep -c "WARNING.*===" custom_components/ev_trip_planner/__init__.py` returns `0`
  - **Commit**: `refactor(phase-5): replace WARNING debug spam with DEBUG level`
  - _Requirements: FR-16_
  - **[P]**

- [ ] 5.4 [GREEN] Create diagnostics.py for HA Quality
  - **Do**: Create `custom_components/ev_trip_planner/diagnostics.py` with `async_get_config_entry_diagnostics` function. Export integration diagnostics (config entry data, coordinator state, trip counts) for HA diagnostic tooling.
  - **Files**: `custom_components/ev_trip_planner/diagnostics.py` (CREATE)
  - **Done when**: diagnostics.py exists with proper HA diagnostics support
  - **Verify**: `.venv/bin/python -c "from custom_components.ev_trip_planner.diagnostics import async_get_config_entry_diagnostics; print('ok')"`
  - **Commit**: `feat(phase-5): add diagnostics.py for HA Quality`
  - _Requirements: HA Quality requirements_

- [ ] 5.5 [GREEN] Update CONFIG_VERSION for entity registry migration
  - **Do**: In `const.py`, increment `CONFIG_VERSION` to 2. Add `async_migrate_entry` in `__init__.py` to handle entity registry migration if needed (e.g., if unique_id format changed).
  - **Files**: `custom_components/ev_trip_planner/const.py`, `custom_components/ev_trip_planner/__init__.py`
  - **Done when**: CONFIG_VERSION = 2, migration handler present
  - **Verify**: `grep "CONFIG_VERSION = " custom_components/ev_trip_planner/const.py` outputs `CONFIG_VERSION = 2`
  - **Commit**: `feat(phase-5): increment CONFIG_VERSION to 2 for migration`

- [ ] VF [VERIFY] Goal verification: all Phase 0 characterization tests pass
  - **Do**: Run all 6 Phase 0 characterization tests, verify they all PASS. Document the before/after state in .progress.md.
  - **Verify**: `.venv/bin/pytest tests/test_entity_registry.py -v 2>&1 | tail -10`
  - **Done when**: All 6 tests PASS — original broken behavior is now fixed
  - **Commit**: `chore(phase-5): verify all Phase 0 characterization tests pass`

- [ ] V5 [VERIFY] Final quality checkpoint: full test suite
  - **Do**: Run full test suite excluding E2E, lint, and type check
  - **Verify**: `.venv/bin/python -m flake8 custom_components/ev_trip_planner/ && .venv/bin/python -m mypy custom_components/ev_trip_planner/ && .venv/bin/pytest tests/ --ignore=tests/e2e --ignore=tests/ha-manual -v 2>&1 | tail -20`
  - **Done when**: No lint errors, no type errors, all tests pass
  - **Commit**: `chore(phase-5): final quality checkpoint - full suite passes`

## Learnings

- Phase 0 characterization tests define "done" — they FAIL today documenting broken behavior, PASS after fix
- async_add_entities is passed by HA ONLY to platform async_setup_entry, cannot be stored in entry.runtime_data
- Phase 2 TripSensor creation must happen via platform setup using the async_add_entities callback directly
- Phase 3 EmhassDeferrableLoadSensor must inherit CoordinatorEntity to receive coordinator refresh updates
- __init__.py extraction is Phase 4 because it depends on services.py being stable first
- Bug TDD workflow: Phase 0 (reproduce) + Phase 1-4 (TDD cycles) + Phase 5 (cleanup)
