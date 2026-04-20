---
title: 'Migrate TripManager tests to pass entry_id consistently'
type: 'refactor'
created: '2026-04-18T16:52:00.000Z'
status: 'done'
baseline_commit: 'fix-panel-in-blank'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** ~180 TripManager instantiations in tests lack `entry_id`, causing `publish_deferrable_loads()` to fail silently when it tries to refresh the coordinator. The remaining ~45 have entry_id but the inconsistency means EMHASS integration tests are unreliable.

**Approach:** Add `entry_id` parameter to all TripManager instantiations in tests, following the pattern already established in ~45 correct instances. Phase the migration: Phase A (critical EMHASS tests), Phase B (SOC tests), Phase C (pure function tests).

## Boundaries & Constraints

**Always:**
- Tests must test the SAME behavior as before - only the constructor signature changes
- `entry_id` must be a string, e.g., `"test_entry_123"`
- All 1370 passing tests must still pass after migration
- Use `entry_id` keyword argument, not positional: `TripManager(..., entry_id="test_entry")`

**Ask First:**
- If a test fails after adding entry_id, investigate before continuing
- If coverage drops below 95%, halt and report

**Never:**
- Do not modify production code constructor signature
- Do not remove existing TripManager instantiations that already have entry_id
- Do not change test assertions or expectations

</frozen-after-approval>

## Code Map

- `custom_components/ev_trip_planner/trip_manager.py` -- TripManager constructor accepts entry_id as 3rd positional/4th overall param
- `tests/conftest.py` -- Fixtures for mock_hass, mock_store that tests dependend on
- `tests/test_trip_manager_core.py` -- ~90 TripManager instantiations needing entry_id
- `tests/test_trip_manager.py` -- ~60 TripManager instantiations, mixed (some have entry_id)
- `tests/test_trip_manager_emhass.py` -- EMHASS integration tests (Phase A)
- `tests/test_post_restart_persistence.py` -- Persistence tests (Phase A)
- `tests/test_integration_uninstall.py` -- Cleanup tests (Phase A)
- `tests/test_soc_milestone.py` -- SOC tests (Phase B)
- `tests/test_presence_monitor_soc.py` -- SOC from presence (Phase B)
- `tests/test_power_profile_tdd.py` -- Pure calculations (Phase C)
- `tests/test_calculations.py` -- Pure functions (Phase C)

## Tasks & Acceptance

**Execution:**
- [ ] `tests/conftest.py` -- Add `trip_manager_with_entry_id` fixture -- Consistent TripManager instance for all tests
- [ ] `tests/test_trip_manager_core.py` -- Add entry_id to all ~90 TripManager calls -- Phase A critical
- [ ] `tests/test_trip_manager.py` -- Add entry_id to ~50 TripManager calls missing it -- Phase A/B
- [ ] `tests/test_trip_manager_emhass.py` -- Add entry_id to all TripManager calls -- Phase A critical
- [ ] `tests/test_post_restart_persistence.py` -- Add entry_id to all TripManager calls -- Phase A critical
- [ ] `tests/test_integration_uninstall.py` -- Add entry_id to all TripManager calls -- Phase A critical
- [ ] `tests/test_soc_milestone.py` -- Add entry_id to TripManager fixture call -- Phase B
- [ ] `tests/test_presence_monitor_soc.py` -- Add entry_id to TripManager calls -- Phase B
- [ ] `tests/test_power_profile_tdd.py` -- Add entry_id to ~10 TripManager calls -- Phase C
- [ ] `tests/test_trip_calculations.py` -- Add entry_id to ~5 TripManager calls -- Phase C

**Acceptance Criteria:**
- Given a test that creates TripManager, when it runs, then it has entry_id and publish_deferrable_loads works
- Given Phase A tests (EMHASS), when executed, then coordinator refresh is triggered correctly
- Given Phase B tests (SOC), when executed, then async_get_vehicle_soc returns correct value
- Given Phase C tests (pure functions), when executed, then test results unchanged
- Given all tests, when pytest runs, then 1370+ pass with no new failures

## Spec Change Log

<!-- Empty until first bad_spec loopback. -->

## Design Notes

**Pattern to apply:**
```python
# ANTES
trip_manager = TripManager(mock_hass, vehicle_id)

# DESPUÉS
trip_manager = TripManager(mock_hass, vehicle_id, entry_id="test_entry_123")
```

**Files to ignore (dependency issues, not entry_id problem):**
- `test_coverage_edge_cases.py` -- missing pytest_homeassistant_custom_component
- `test_trip_manager_missing_coverage.py` -- missing pytest_homeassistant_custom_component
- `test_trip_manager_cover_more.py` -- missing pytest_homeassistant_custom_component
- `test_emhass_adapter.py::test_publish_deferrable_load_computes_start_timestep` -- missing freezegun

## Verification

**Commands:**
- `pytest --ignore=tests/test_coverage_edge_cases.py --ignore=tests/test_trip_manager_missing_coverage.py --ignore=tests/test_trip_manager_cover_more.py -q --tb=no` -- expected: 1370+ passed, 0 failed
- `pytest tests/test_trip_manager_core.py tests/test_trip_manager_emhass.py -v --tb=short` -- Phase A gate: all pass
- `pytest tests/test_soc_milestone.py tests/test_presence_monitor_soc.py -v` -- Phase B gate: all pass
- `pytest tests/test_calculations.py tests/test_trip_calculations.py -v` -- Phase C gate: all pass

**Manual checks (if no CLI):**
- Grep for `TripManager(` in tests/ and verify no bare `TripManager(hass, "veh")` without entry_id