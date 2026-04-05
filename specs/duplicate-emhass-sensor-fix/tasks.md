# Tasks: duplicate-emhass-sensor-fix

## Context

- **Spec**: duplicate-emhass-sensor-fix
- **Intent**: BUG_FIX (TRIVIAL - ~14 lines across 3 files)
- **Workflow**: Bug TDD (Phase 0 + TDD Phases 1-4)
- **Test runner**: `.venv/bin/pytest`
- **E2E Verification**: DISABLED (Home Assistant backend integration - no browser UI)

---

## Phase 0: Reproduce

- [x] 0.1 [VERIFY] Reproduce bug: verify `emhass_adapter.async_cleanup_vehicle_indices` is NOT called by `async_unload_entry`
  - **Do**: Read test_integration_uninstall.py line 171 comment confirming the gap, run existing tests to confirm they pass despite the missing cleanup call
  - **Files**: `tests/test_integration_uninstall.py`
  - **Done when**: Existing tests pass but document that `async_cleanup_vehicle_indices` is not called
  - **Verify**: `.venv/bin/pytest tests/test_integration_uninstall.py -v 2>&1 | tail -20`
  - **Commit**: None (Phase 0 - no code changes)

- [x] 0.2 [VERIFY] Confirm repro is consistent: bug documented gap is stable
  - **Do**: Run test_integration_uninstall.py twice more to confirm consistent behavior; verify the comment at line 171 accurately documents the missing call
  - **Files**: `tests/test_integration_uninstall.py`
  - **Done when**: Behavior is consistent; document BEFORE state in .progress.md
  - **Verify**: `.venv/bin/pytest tests/test_integration_uninstall.py -v --tb=no 2>&1 | grep -E "passed|PASSED"`
  - **Commit**: `chore(duplicate-emhass-sensor-fix): document reality check before`

---

## Phase 1: Red-Green-Yellow TDD Cycles

### Component 1: EMHASSAdapter.__init__ and publish_deferrable_loads - Entity Tracking

- [x] 1.1 [RED] Failing test: `EMHASSAdapter.__init__` has `_published_entity_ids` set and `publish_deferrable_loads` populates it
  - **Do**: Write test in `tests/test_emhass_adapter.py` asserting that after `publish_deferrable_loads()` is called, `adapter._published_entity_ids` contains the main sensor id `sensor.emhass_perfil_diferible_{entry_id}`
  - **Files**: `tests/test_emhass_adapter.py`
  - **Done when**: Test exists AND fails with AssertionError (attribute not found)
  - **Verify**: `.venv/bin/pytest tests/test_emhass_adapter.py -v -k "published_entity_ids" 2>&1 | grep -q "FAILED" && echo RED_PASS`
  - **Commit**: `test(emhass): red - failing test for _published_entity_ids tracking`
  - _Requirements: FR-1, AC-1.4_

- [x] 1.2 [GREEN] Pass test: add `_published_entity_ids` tracking to `EMHASSAdapter`
  - **Do**: In `emhass_adapter.py` `__init__`, add `self._published_entity_ids: Set[str] = set()`. In `publish_deferrable_loads()`, after successful `async_set` for the main sensor, add `self._published_entity_ids.add(sensor_id)`
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: Previously failing test now passes
  - **Verify**: `.venv/bin/pytest tests/test_emhass_adapter.py -v -k "published_entity_ids"`
  - **Commit**: `feat(emhass): green - add _published_entity_ids tracking`
  - _Requirements: FR-1, AC-1.4_

### Component 2: async_cleanup_vehicle_indices - Use async_remove instead of async_set(idle)

- [x] 1.3 [RED] Failing test: `async_cleanup_vehicle_indices` calls `async_remove` not `async_set(idle)`
  - **Do**: Write test in `tests/test_emhass_adapter.py` asserting that `hass.states.async_remove` is called for each tracked entity (config sensors and main sensor) and `_published_entity_ids` is cleared after cleanup
  - **Files**: `tests/test_emhass_adapter.py`
  - **Done when**: Test exists AND fails (async_remove not called, async_set(idle) called instead)
  - **Verify**: `.venv/bin/pytest tests/test_emhass_adapter.py -v -k "cleanup_vehicle" 2>&1 | grep -q "FAILED" && echo RED_PASS`
  - **Commit**: `test(emhass): red - failing test for async_remove in cleanup`
  - _Requirements: FR-2, AC-1.2_

- [x] 1.4 [GREEN] Pass test: replace `async_set(idle)` with `async_remove` in `async_cleanup_vehicle_indices`
  - **Do**: In `emhass_adapter.py` `async_cleanup_vehicle_indices()`, replace two `hass.states.async_set(config_sensor_id, "idle", {})` and `hass.states.async_set(sensor_id, "idle", {...})` calls with `hass.states.async_remove(config_sensor_id)` and `hass.states.async_remove(sensor_id)`. Add `self._published_entity_ids.clear()` after the cleanup loop
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: Previously failing test now passes
  - **Verify**: `.venv/bin/pytest tests/test_emhass_adapter.py -v -k "cleanup_vehicle"`
  - **Commit**: `feat(emhass): green - use async_remove in cleanup`
  - _Requirements: FR-2, AC-1.2_

### Component 3: EmhassDeferrableLoadSensor.async_update - Persist attribute changes

- [x] 1.5 [RED] Failing test: `async_update` calls `async_schedule_update_ha_state` on success, not on exception
  - **Do**: Write test in `tests/test_sensor.py` asserting `async_schedule_update_ha_state` is called exactly once when `async_update()` succeeds, and NOT called when it raises an exception
  - **Files**: `tests/test_sensor.py`
  - **Done when**: Test exists AND fails (method not called)
  - **Verify**: `.venv/bin/pytest tests/test_sensor.py -v -k "async_update" 2>&1 | grep -q "FAILED" && echo RED_PASS`
  - **Commit**: `test(sensor): red - failing test for async_schedule_update_ha_state`
  - _Requirements: FR-3, AC-2.1_

- [x] 1.6 [GREEN] Pass test: add `async_schedule_update_ha_state` call to `async_update`
  - **Do**: In `sensor.py` `EmhassDeferrableLoadSensor.async_update()`, after `self._attr_native_value = EMHASS_STATE_READY` and before the debug log, add `self.async_schedule_update_ha_state()`
  - **Files**: `custom_components/ev_trip_planner/sensor.py`
  - **Done when**: Previously failing test now passes
  - **Verify**: `.venv/bin/pytest tests/test_sensor.py -v -k "async_update"`
  - **Commit**: `feat(sensor): green - call async_schedule_update_ha_state in async_update`
  - _Requirements: FR-3, AC-2.1_

### Component 4: async_unload_entry - Call cleanup before unload

- [x] 1.7 [RED] Failing test: `async_unload_entry` calls `emhass_adapter.async_cleanup_vehicle_indices()` before `async_unload_platforms`
  - **Do**: Write test in `tests/test_init.py` asserting that during `async_unload_entry`, the emhass_adapter's cleanup method is called before platforms are unloaded
  - **Files**: `tests/test_init.py`
  - **Done when**: Test exists AND fails (method not called)
  - **Verify**: `.venv/bin/pytest tests/test_init.py -v -k "unload_cleanup" 2>&1 | grep -q "FAILED" && echo RED_PASS`
  - **Commit**: `test(init): red - failing test for cleanup call in unload`
  - _Requirements: FR-1, AC-1.3_

- [x] 1.8 [GREEN] Pass test: call `async_cleanup_vehicle_indices()` from `async_unload_entry`
  - **Do**: In `__init__.py` `async_unload_entry()`, after `await trip_manager.async_delete_all_trips()`, add code to retrieve `emhass_adapter` from hass.data and call `await emhass_adapter.async_cleanup_vehicle_indices()`
  - **Files**: `custom_components/ev_trip_planner/__init__.py`
  - **Done when**: Previously failing test now passes
  - **Verify**: `.venv/bin/pytest tests/test_init.py -v -k "unload_cleanup"`
  - **Commit**: `feat(init): green - call async_cleanup_vehicle_indices on unload`
  - _Requirements: FR-1, AC-1.3_

### Component 5: Startup orphan cleanup - Remove sensors from deleted integrations

- [x] 1.9 [RED] Failing test: startup orphan cleanup removes sensors with stale entry_id, keeps active ones
  - **Do**: Write test in `tests/test_init.py` asserting that during `async_setup_entry`, sensors with `entry_id` not in `hass.config_entries.async_entries()` are removed via `async_remove`, while sensors with valid active entry_ids are preserved
  - **Files**: `tests/test_init.py`
  - **Done when**: Test exists AND fails (orphans not cleaned at startup)
  - **Verify**: `.venv/bin/pytest tests/test_init.py -v -k "orphan_cleanup" 2>&1 | grep -q "FAILED" && echo RED_PASS`
  - **Commit**: `test(init): red - failing test for startup orphan cleanup`
  - _Requirements: FR-4, FR-5, AC-3.1, AC-3.2, AC-3.3, AC-3.4_

- [x] 1.10 [GREEN] Pass test: add startup orphan cleanup block to `async_setup_entry`
  - **Do**: In `__init__.py` `async_setup_entry()`, after line ~470 (before namespace setup), add block that scans for `sensor.emhass_perfil_diferible_*` states, checks if their `entry_id` attribute is not in `hass.config_entries.async_entries()`, and calls `async_remove` for orphaned ones
  - **Files**: `custom_components/ev_trip_planner/__init__.py`
  - **Done when**: Previously failing test now passes
  - **Verify**: `.venv/bin/pytest tests/test_init.py -v -k "orphan_cleanup"`
  - **Commit**: `feat(init): green - add startup orphan cleanup`
  - _Requirements: FR-4, FR-5, AC-3.1, AC-3.2, AC-3.3, AC-3.4_

- [x] V1 [VERIFY] Quality check: lint and type check pass
  - **Do**: Run `pylint custom_components/ev_trip_planner/emhass_adapter.py custom_components/ev_trip_planner/sensor.py custom_components/ev_trip_planner/__init__.py --disable=all --enable=E,F` and `mypy custom_components/ev_trip_planner` (or project equivalents)
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py`, `custom_components/ev_trip_planner/sensor.py`, `custom_components/ev_trip_planner/__init__.py`
  - **Verify**: Commands exit 0
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(duplicate-emhass-sensor-fix): pass quality checkpoint`

---

## Phase 2: Additional Testing

- [x] 2.1 [TEST] Integration test: full unload cycle cleans all entities
  - **Do**: Write integration test in `tests/test_integration_uninstall.py` that creates an EMHASSAdapter with published sensors, calls `async_unload_entry`, and verifies `hass.states.async_remove` was called for all published entity ids
  - **Files**: `tests/test_integration_uninstall.py`
  - **Done when**: Test passes
  - **Verify**: `.venv/bin/pytest tests/test_integration_uninstall.py -v -k "full_unload"`
  - **Commit**: `test(integration): add full unload cycle test`

- [x] 2.2 [TEST] Test: multiple vehicles - deleting one does not affect another
  - **Do**: Write test in `tests/test_emhass_adapter.py` with two EMHASSAdapter instances, cleanup one, verify the other's entities are not removed
  - **Files**: `tests/test_emhass_adapter.py`
  - **Done when**: Test passes
  - **Verify**: `.venv/bin/pytest tests/test_emhass_adapter.py -v -k "multiple_vehicles"`
  - **Commit**: `test(emhass): add multiple vehicles isolation test`

---

## Phase 3: Quality Gates

- [x] V2 [VERIFY] Full test suite: all existing tests pass
  - **Do**: Run `.venv/bin/pytest tests/test_emhass_adapter.py tests/test_sensor.py tests/test_init.py tests/test_integration_uninstall.py -v`
  - **Files**: `tests/test_emhass_adapter.py`, `tests/test_sensor.py`, `tests/test_init.py`, `tests/test_integration_uninstall.py`
  - **Verify**: All tests pass with exit code 0
  - **Done when**: Full test suite green
  - **Commit**: `chore(duplicate-emhass-sensor-fix): pass full test suite`

- [x] V3 [VERIFY] Smoke test passes
  - **Do**: Run `npm test` (if available) or verify project-specific smoke test
  - **Files**: N/A (verification only)
  - **Verify**: Exit code 0
  - **Done when**: Smoke test green
  - **Commit**: `chore(duplicate-emhass-sensor-fix): pass smoke test`

---

## Phase 4: PR Lifecycle

- [x] VF [VERIFY] Goal verification: original bug is fixed
  - **Do**:
    1. Read BEFORE state from .progress.md
    2. Re-run test_integration_uninstall.py to confirm cleanup is now called
    3. Verify `async_cleanup_vehicle_indices` uses `async_remove` not `async_set(idle)`
    4. Document AFTER state in .progress.md
  - **Files**: `.progress.md`
  - **Verify**: `.venv/bin/pytest tests/test_integration_uninstall.py -v && .venv/bin/pytest tests/test_emhass_adapter.py -v -k "cleanup_vehicle" && echo "ALL_PASS"`
  - **Done when**: All verification commands pass
  - **Commit**: `chore(duplicate-emhass-sensor-fix): verify fix resolves original issue`

- [x] V4 [VERIFY] PR ready: code reviewed and all checks green
  - **Do**: Create PR, ejecute local e2e `make e2e` all tests pass local, verify CI pipeline passes, ensure no regressions
  - **Files**: N/A (verification only)
  - **Verify**: `gh pr checks` shows all green
  - **Done when**: PR merged or approved all tests local and ci pass. unit and e2e tests pass with no regressions. First pass local tests. when all local tests pass, push branch and verify CI pipeline passes with no regressions.
  - **Commit**: None
  - **Note**: PR #19 merged - fix is on main branch.

---

## Summary

| Phase | Tasks | Description |
|-------|-------|-------------|
| Phase 0 | 0.1-0.2 | Reproduce bug - verify gap exists in existing tests |
| Phase 1 | 1.1-1.10 + V1 | TDD cycles for 5 components (10 RED/GREEN pairs + quality gate) |
| Phase 2 | 2.1-2.2 | Additional integration tests |
| Phase 3 | V2-V3 | Quality gates - full test suite + smoke test |
| Phase 4 | VF, V4 | Final verification and PR lifecycle |
| **Total** | **17 tasks** | |

**Checkbox count**: `grep -c '- \[.\]' /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner/specs/duplicate-emhass-sensor-fix/tasks.md`
