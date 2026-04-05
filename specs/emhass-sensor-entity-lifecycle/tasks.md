# Implementation Tasks: EMHASS Sensor Entity Lifecycle Fix

## Overview

This spec implements fixes for EMHASS sensor entity lifecycle issues using a POC-first approach across 5 phases.

**Total Tasks**: 20 across 4 phases (19 implementation + 1 baseline checkpoint)

## Phase Breakdown

- **Phase 0 (Baseline)**: 1 task - verify all existing tests pass before changes
- **Phase 1 (POC)**: 5 tasks - proves the core fixes work
- **Phase 2 (Refactor)**: 5 tasks - clean up and consolidate
- **Phase 3 (Testing)**: 5 tasks - add comprehensive test coverage
- **Phase 4 (Quality)**: 4 tasks - CI/PR readiness

---

## Verification Tooling

**Testing Commands** (from `Makefile`):
- `make test` - Run all Python unit tests (ignores e2e)
- `make test-cover` - Run tests with coverage report
- `make e2e` - Run E2E tests (auto-starts HA via `scripts/run-e2e.sh`)
- `make lint` - Run ruff and pylint
- `make mypy` - Run type checking
- `make check` - Run all checks (test + lint + mypy)

**E2E Environment** (from `scripts/run-e2e.sh`):
- Config directory: `/tmp/ha-e2e-config`
- HA starts: `hass -c /tmp/ha-e2e-config`
- HA URL: `http://localhost:8123`
- E2E tests: `npx playwright test tests/e2e/`
- Script handles: kill existing HA, clean config, start HA, run onboarding

**Development**:
- Python: 3.11+ (pyproject.toml)
- Virtualenv: `.venv/bin/python`
- Test framework: pytest with asyncio support
- Coverage threshold: 80%

---

## Tasks

### Phase 0: Baseline - Verify Tests Pass First

#### Task 0.0: Baseline Verification - All Tests Green

**Do**: Verify all existing tests pass BEFORE starting implementation

**Files**:
- All test files
- Use `make test` command

**Done When**:
- [ ] Run `make test` and all tests pass
- [ ] Document test count and any failures
- [ ] Create baseline snapshot for regression comparison
- [ ] Ensure `.venv` is activated/available

**Verify**:
```bash
cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner
make test
# Expected: All tests pass before any changes
```

**Commit**: `baseline: verify all tests pass before implementation`

**Important**: If tests fail, fix them first before proceeding. Do not implement new features with failing baseline.

---

### Phase 1: POC - Core Fixes

#### Task 1.1: Add entry_id attribute to state-only sensors

**Do**: Add `entry_id` attribute to state-only EMHASS sensors in `publish_deferrable_loads()`

**Files**:
- `custom_components/ev_trip_planner/emhass_adapter.py`

**Done When**:
- [ ] `publish_deferrable_loads()` sets `state.attributes["entry_id"]` to `self.entry_id`
- [ ] State sensors include entry_id attribute alongside deferrables_schedule and power_profile_watts

**Verify**:
```bash
cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner
python -c "from custom_components.ev_trip_planner.emhass_adapter import EmhassAdapter; print('Syntax OK')"
```

**Commit**: `fix(emhass_adapter): add entry_id attribute to state sensors`

---

#### Task 1.2: Add entity registry cleanup to async_cleanup_vehicle_indices

**Do**: Add `entity_registry.async_remove()` calls to `async_cleanup_vehicle_indices()`

**Files**:
- `custom_components/ev_trip_planner/emhass_adapter.py`
- Import `entity_registry` from `homeassistant.helpers`

**Done When**:
- [ ] `async_cleanup_vehicle_indices()` calls `entity_registry.async_remove()` for each entity
- [ ] Try/except handles already-removed entries gracefully
- [ ] Both state and registry cleanup run in the same loop

**Verify**:
```python
# Verify cleanup includes both paths
grep -A 20 "async_cleanup_vehicle_indices" custom_components/ev_trip_planner/emhass_adapter.py | grep -E "(states.async_remove|registry.async_remove)"
```

**Commit**: `fix(emhass_adapter): add entity registry cleanup to vehicle indices cleanup`

---

#### Task 1.3: Add config entry update listener

**Do**: Add `setup_config_entry_listener()` method to subscribe to config entry updates

**Files**:
- `custom_components/ev_trip_planner/emhass_adapter.py`
- Call in `__init__.py` after adapter creation

**Done When**:
- [ ] `setup_config_entry_listener()` subscribes to `config_entries` bus events
- [ ] Listens for `action == "updated"` events
- [ ] Extracts `charging_power_kw` from updated entry

**Verify**:
```bash
grep -A 10 "setup_config_entry_listener" custom_components/ev_trip_planner/emhass_adapter.py
```

**Commit**: `feat(emhass_adapter): add config entry update listener`

---

#### Task 1.4: Add update_charging_power method

**Do**: Add `update_charging_power()` method that republishes when power changes

**Files**:
- `custom_components/ev_trip_planner/emhass_adapter.py`

**Done When**:
- [ ] `update_charging_power()` compares new power with stored `_charging_power_kw`
- [ ] Calls `publish_deferrable_loads()` only when power actually changed
- [ ] Updates `_charging_power_kw` after republish

**Verify**:
```python
grep -A 10 "def update_charging_power" custom_components/ev_trip_planner/emhass_adapter.py
```

**Commit**: `feat(emhass_adapter): add charging power update method`

---

#### Task 1.5: Wire config update to config flow

**Do**: Call `adapter.update_charging_power()` after `async_update_entry` in config flow

**Files**:
- `custom_components/ev_trip_planner/config_flow.py`

**Done When**:
- [ ] After `async_update_entry()` returns, call `await adapter.update_charging_power()`
- [ ] Adapter reference obtained from `hass.data[DATA_COMPONENT]`
- [ ] Entry ID from `config` or `data` dict

**Verify**:
```bash
grep -B 5 -A 5 "update_charging_power" custom_components/ev_trip_planner/config_flow.py
```

**Commit**: `feat(config_flow): trigger charging power update on config change`

---

### Quality Checkpoint - Phase 1 Verification

**Run these verifications before proceeding:**

```bash
# Verify syntax
cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner
python -m py_compile custom_components/ev_trip_planner/emhass_adapter.py
python -m py_compile custom_components/ev_trip_planner/config_flow.py

# Run unit tests
python -m pytest tests/test_emhass_adapter.py -v
```

**Verify POC is working:**
1. Start dev server: `python -m homeassistant --config /tmp/ha-config`
2. Add vehicle with EMHASS integration
3. Check sensor has `entry_id` attribute
4. Change charging power in config flow
5. Verify sensor attributes update

---

#### Task 1.6: Verify async_schedule_update_ha_state call

**Do**: Ensure `EmhassDeferrableLoadSensor.async_update()` calls `async_schedule_update_ha_state()`

**Files**:
- `custom_components/ev_trip_planner/sensor.py`

**Done When**:
- [ ] `async_update()` calls `async_schedule_update_ha_state()` after `_cached_attrs` update
- [ ] Call is NOT mocked in production code
- [ ] Attribute changes propagate to HA state machine

**Verify**:
```bash
grep -A 5 "_cached_attrs" custom_components/ev_trip_planner/sensor.py | grep "async_schedule_update_ha_state"
```

**Commit**: `fix(sensor.py): ensure async_schedule_update_ha_state() is called`

---

#### Task 1.7: Tighten panel sensor filtering

**Do**: Replace `sensor.ev_trip_planner` pattern with exact `entry_id` match in panel.js

**Files**:
- `custom_components/ev_trip_planner/panel.js`

**Done When**:
- [ ] `_getVehicleStates()` filters by `state.attributes?.entry_id === currentEntryId`
- [ ] No longer uses `sensor.ev_trip_planner` pattern
- [ ] Only shows sensors with matching entry_id

**Verify**:
```bash
grep -A 5 "_getVehicleStates" custom_components/ev_trip_planner/panel.js | grep "entry_id"
```

**Commit**: `fix(panel.js): filter sensors by exact entry_id match`

---

#### Task 1.8: Remove if unload_ok guard for panel cleanup

**Do**: Remove `if unload_ok:` guard and always call panel cleanup

**Files**:
- `custom_components/ev_trip_planner/__init__.py`

**Done When**:
- [ ] `async_unregister_panel()` is called regardless of `unload_ok` status
- [ ] Success logging added for panel cleanup
- [ ] Error logging for failures preserved

**Verify**:
```bash
grep -B 2 -A 5 "async_unregister_panel" custom_components/ev_trip_planner/__init__.py
```

**Commit**: `fix(__init__.py): always call panel cleanup on vehicle deletion`

---

### Phase 2: Refactor - Clean Up

#### Task 2.1: Consolidate cleanup loops

**Do**: Merge state and registry cleanup into single loop in `async_cleanup_vehicle_indices()`

**Files**:
- `custom_components/ev_trip_planner/emhass_adapter.py`

**Done When**:
- [ ] Single loop iterates through vehicle indices
- [ ] Both state and registry cleanup in same iteration
- [ ] Clear comments explaining both cleanup paths

**Verify**:
```python
grep -A 30 "async_cleanup_vehicle_indices" custom_components/ev_trip_planner/emhass_adapter.py | head -40
```

**Commit**: `refactor(emhass_adapter): consolidate cleanup into single loop`

---

#### Task 2.2: Add cleanup documentation

**Do**: Add docstrings and comments explaining cleanup logic

**Files**:
- `custom_components/ev_trip_planner/emhass_adapter.py`

**Done When**:
- [ ] `async_cleanup_vehicle_indices()` has comprehensive docstring
- [ ] Comments explain why both state and registry cleanup needed
- [ ] Error handling documented

**Verify**:
```bash
grep -B 5 "async_cleanup_vehicle_indices" custom_components/ev_trip_planner/emhass_adapter.py | grep -E '(""")|# '
```

**Commit**: `docs(emhass_adapter): add cleanup documentation`

---

#### Task 2.3: Clean up config listener

**Do**: Add cleanup for config listener in `async_unload_entry()`

**Files**:
- `custom_components/ev_trip_planner/emhass_adapter.py`
- `custom_components/ev_trip_planner/__init__.py`

**Done When**:
- [ ] Config listener stored as instance variable for cleanup
- [ ] `async_unload_entry()` removes listener when adapter unloaded
- [ ] No memory leaks on reload

**Verify**:
```bash
grep -A 5 "async_unload_entry" custom_components/ev_trip_planner/__init__.py | grep -E "(bus.async_unlisten|cleanup)"
```

**Commit**: `refactor(emhass_adapter): clean up config listener on unload`

---

#### Task 2.4: Standardize error logging

**Do**: Standardize logging levels for cleanup operations

**Files**:
- `custom_components/ev_trip_planner/emhass_adapter.py`
- `custom_components/ev_trip_planner/__init__.py`

**Done When**:
- [ ] INFO for successful cleanup
- [ ] WARNING for skipped operations
- [ ] ERROR for failed operations

**Verify**:
```bash
grep "_LOGGER\." custom_components/ev_trip_planner/emhass_adapter.py | grep -E "(info|warning|error)"
```

**Commit**: `refactor: standardize error logging levels`

---

#### Task 2.5: Add cleanup verification helper

**Do**: Add helper method to verify cleanup state

**Files**:
- `custom_components/ev_trip_planner/emhass_adapter.py`

**Done When**:
- [ ] `verify_cleanup()` method checks both state and registry
- [ ] Returns dict with cleanup status
- [ ] Used in tests for verification

**Verify**:
```bash
grep -A 10 "def verify_cleanup" custom_components/ev_trip_planner/emhass_adapter.py
```

**Commit**: `feat(emhass_adapter): add cleanup verification helper`

---

### Phase 3: Testing - Add Coverage

#### Task 3.1: Add entity registry cleanup tests

**Do**: Create `tests/test_entity_cleanup.py` with cleanup verification tests

**Files**:
- `tests/test_entity_cleanup.py` (new file)

**Done When**:
- [ ] `test_entity_registry_cleanup` verifies `entity_registry.async_remove()` called
- [ ] `test_state_sensor_has_entry_id` verifies attribute set
- [ ] Tests use proper HA test fixtures

**Verify**:
```bash
cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner
python -m pytest tests/test_entity_cleanup.py -v
```

**Commit**: `test: add entity registry cleanup tests`

---

#### Task 3.2: Add config update tests

**Do**: Create `tests/test_config_updates.py` with config change tests

**Files**:
- `tests/test_config_updates.py` (new file)

**Done When**:
- [ ] `test_config_update_triggers_republish` verifies republish on power change
- [ ] `test_no_republish_when_no_change` verifies no action when power unchanged
- [ ] Tests mock config entry update events

**Verify**:
```bash
python -m pytest tests/test_config_updates.py -v
```

**Commit**: `test: add config update tests`

---

#### Task 3.3: Add panel filtering tests

**Do**: Create `tests/test_panel_filtering.py` with panel sensor tests

**Files**:
- `tests/test_panel_filtering.py` (new file)

**Done When**:
- [ ] `test_panel_filters_by_entry_id` verifies vehicle-specific filtering
- [ ] `test_no_cross_vehicle_contamination` verifies no sensor bleed between vehicles
- [ ] Tests create mock states with entry_id attributes

**Verify**:
```bash
python -m pytest tests/test_panel_filtering.py -v
```

**Commit**: `test: add panel filtering tests`

---

#### Task 3.4: Add integration cleanup tests

**Do**: Add integration tests for full vehicle deletion lifecycle

**Files**:
- `tests/test_integration_uninstall.py` (update existing file)

**Done When**:
- [ ] `test_full_vehicle_deletion` verifies state + registry + panel cleanup
- [ ] Tests verify no orphaned sensors after deletion
- [ ] Tests use real HA integration test patterns

**Verify**:
```bash
python -m pytest tests/test_integration_uninstall.py::test_full_vehicle_deletion -v
```

**Commit**: `test: add full vehicle deletion integration test`

---

#### Task 3.5: Run full test suite

**Do**: Run all tests to verify implementation

**Files**:
- All test files

**Done When**:
- [ ] All existing tests pass
- [ ] All new tests pass
- [ ] Test coverage report generated

**Verify**:
```bash
python -m pytest tests/ -v --cov=custom_components.ev_trip_planner
```

**Commit**: `test: run full test suite`

---

### Phase 4: Quality - CI/PR Readiness

#### Task 4.1: Add type hints

**Do**: Add type hints to new methods

**Files**:
- `custom_components/ev_trip_planner/emhass_adapter.py`

**Done When**:
- [ ] All new methods have type hints
- [ ] Return types specified
- [ ] Parameter types specified

**Verify**:
```bash
python -m mypy custom_components/ev_trip_planner/emhass_adapter.py --ignore-missing-imports
```

**Commit**: `type: add type hints to new methods`

---

#### Task 4.2: Code quality checks

**Do**: Run flake8 and other code quality tools

**Files**:
- All modified files

**Done When**:
- [ ] flake8 passes with no errors
- [ ] pylint passes or has acceptable score
- [ ] No new warnings introduced

**Verify**:
```bash
python -m flake8 custom_components/ev_trip_planner/emhass_adapter.py
python -m flake8 custom_components/ev_trip_planner/config_flow.py
python -m flake8 custom_components/ev_trip_planner/__init__.py
```

**Commit**: `quality: run code quality checks`

---

#### Task 4.3: Update CHANGELOG

**Do**: Add entry to CHANGELOG.md for this fix

**Files**:
- `CHANGELOG.md`

**Done When**:
- [ ] Entry under "Unreleased" section
- [ ] Lists all fixes: sensor deletion, panel filtering, config updates
- [ ] References related issues if any

**Verify**:
```bash
head -20 CHANGELOG.md
```

**Commit**: `docs: update CHANGELOG for EMHASS sensor fixes`

---

#### Task 4.4: Final E2E Verification

**Do**: Run full E2E test suite to verify all changes work end-to-end

**Files**:
- Use `make e2e` command (auto-starts HA via `scripts/run-e2e.sh`)

**Done When**:
- [ ] Run `make e2e` and all E2E tests pass
- [ ] Verify EMHASS sensor lifecycle works end-to-end
- [ ] Vehicle deletion cleans all entities
- [ ] Panel filtering shows correct sensors
- [ ] Config updates reflect in sensors
- [ ] No regression in existing functionality

**Verify**:
```bash
cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner

# Run E2E tests (auto-starts HA, runs onboarding, executes Playwright tests)
make e2e

# Expected: All E2E tests pass
# Script: ./scripts/run-e2e.sh
# Config: /tmp/ha-e2e-config
# HA URL: http://localhost:8123
```

**Alternative (manual)**:
```bash
# Start HA manually if needed
./scripts/run-e2e.sh

# Wait for HA to be ready
curl http://localhost:8123/api/healthcheck

# Run Playwright tests
npx playwright test tests/e2e/
```

**Commit**: `verify: run full E2E test suite`

---

## POC Milestone

**Task 1.5** completes the POC milestone. At this point:
- State sensors include `entry_id` attribute
- Entity registry cleanup works
- Config updates trigger republish
- Basic attribute propagation is working

After Task 1.5, you can:
1. Test the changes in a dev environment
2. Verify sensors update when charging power changes
3. Confirm no errors in logs
4. Proceed to Phase 2 if POC is successful

---

## Summary

| Phase | Tasks | Purpose |
|-------|-------|---------|
| Phase 0 | 0.0 | Baseline - Verify tests pass |
| Phase 1 | 1.1-1.8 | POC - Core fixes |
| Phase 2 | 2.1-2.5 | Refactor - Clean up |
| Phase 3 | 3.1-3.5 | Testing - Add coverage |
| Phase 4 | 4.1-4.4 | Quality - CI/PR |

**Total**: 20 tasks (1 baseline + 19 implementation)

**Files to modify**: 7
**Files to create**: 4 test files

**POC Milestone**: Task 1.5 completes the POC. At this point:
- State sensors include `entry_id` attribute
- Entity registry cleanup works
- Config updates trigger republish
- Basic attribute propagation is working

After Task 1.5, you can:
1. Run `make test` to verify no regressions
2. Test changes in dev environment if needed
3. Proceed to Phase 2 if POC is successful
