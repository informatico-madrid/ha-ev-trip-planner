# Task Review Log

<!-- reviewer-config
principles: [SOLID, DRY, FAIL_FAST, TDD]
codebase-conventions:
  - 100% test coverage required (--cov-fail-under=100)
  - TDD Red-Green-Refactor cycle
  - self.hass NOT self._hass (emhass_adapter.py:43)
  - inicio_ventana is datetime, not int
  - is None check not or for charging_power_kw
  - MockConfigEntry pattern with entry_id, data, options
  - @pytest.mark.asyncio for async tests
  - calculate_multi_trip_charging_windows returns dict with inicio_ventana (datetime)
  - Default trip duration = 6.0 hours
-->

<!-- 
Workflow: External reviewer agent writes review entries to this file after completing tasks.
Status values: FAIL, WARNING, PASS, PENDING
- FAIL: Task failed reviewer's criteria - requires fix
- WARNING: Task passed but with concerns - note in .progress.md
- PASS: Task passed external review - mark complete
- PENDING: reviewer is working on it, spec-executor should not re-mark this task until status changes. spec-executor: skip this task and move to the next unchecked one.
-->

## Reviews

<!--
Review entry template:
- status: FAIL | WARNING | PASS | PENDING
- severity: critical | major | minor (optional)
- reviewed_at: ISO timestamp
- criterion_failed: Which requirement/criterion failed (for FAIL status)
- evidence: Brief description of what was observed
- fix_hint: Suggested fix or direction (for FAIL/WARNING)
- resolved_at: ISO timestamp (only for resolved entries)
-->

### [task-1.1] RED - Failing test: update_charging_power reads entry.options first
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T18:00:00Z
- criterion_failed: none
- evidence: |
  Test exists at tests/test_emhass_adapter.py:4082 (test_update_charging_power_reads_options_first).
  Commit: d497ef4 "test(emhass): red - failing test for options-first read"
  Note: TDD Red-Green cycle was collapsed — test and fix committed together (d497ef4 after d497ef4).
  The RED test was written and the GREEN fix applied in same work session, not separate commits proving RED first.
  However, commit history shows d497ef4 (test) then fe27f1f (fix) — two separate commits, acceptable TDD discipline.
  Verify command output: "1 passed, 132 deselected in 0.50s"
- fix_hint: none
- resolved_at: 

### [task-1.2] GREEN - Fix update_charging_power to read entry.options first, fallback entry.data
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T18:00:00Z
- criterion_failed: none
- evidence: |
  Fix at emhass_adapter.py:1359-1363 (after commit fe27f1f):
    new_power = entry.options.get("charging_power_kw")
    if new_power is None:
        new_power = entry.data.get("charging_power_kw")
  Correctly uses `is None` check (NOT `or`) to handle charging_power_kw=0 edge case per spec.
  Includes guard: "Only republish if power actually changed" — FAIL_FAST principle.
  ruff check: All checks passed!
  Test verifies: adapter._charging_power_kw == 3.6 (from options, not 11 from data)
- fix_hint: none
- resolved_at: 

### [task-1.3] GREEN - Verify data fallback path works
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T18:03:00Z
- criterion_failed: none
- evidence: |
  Test at tests/test_emhass_adapter.py:4140 (test_update_charging_power_fallback_to_data).
  Commit: f58e15a "test(emhass): green - verify data fallback for charging power"
  Correctly tests: options={} (empty), data={"charging_power_kw": 11} → reads 11.
  Verify: "1 passed, 134 deselected in 0.52s"
- fix_hint: none
- resolved_at: 

### [task-1.4] GREEN - Test edge case: charging_power_kw=0 is not treated as falsy
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T18:07:00Z
- criterion_failed: none
- evidence: |
  Test at tests/test_emhass_adapter.py:4190 (test_update_charging_power_zero_not_falsy).
  Commit: f9468d5 "test(emhass): verify charging_power_kw=0 edge case for is None check"
  Correctly tests: options={"charging_power_kw": 0}, data={"charging_power_kw": 11} → reads 0.
  Validates `is None` check (NOT `or` which would treat 0 as falsy).
  Verify: "1 passed, 134 deselected in 0.54s"
- fix_hint: none
- resolved_at: 

### [task-1.5] RED - Failing test: setup_config_entry_listener is called in async_setup_entry
- status: FAIL
- severity: critical
- reviewed_at: 2026-04-11T18:10:00Z
- criterion_failed: TDD Red-Green-Refactor cycle — test must fail for the RIGHT reason
- evidence: |
  Test at tests/test_init.py:1188 (test_listener_activated_in_setup).
  Commit: 5d4309c "test(init): red - failing test for listener activation in setup"
  
  Test FAILS but for WRONG reason:
    "homeassistant.exceptions.ConfigEntryError: Detected code that uses 
     `async_config_entry_first_refresh`, which is only supported for 
     coordinators with a config entry"
  
  The test does NOT reach the assertion `mock_adapter.setup_config_entry_listener.assert_called_once()`.
  It crashes earlier because mock_hass does not mock `async_config_entry_first_refresh`.
  
  Other tests in the same file (lines 972, 1035, 1104) correctly include:
    mock_coordinator.async_config_entry_first_refresh = AsyncMock()
  
  This test is missing that mock, making it a TRAP TEST — it always fails but
  regardless of whether the listener activation code exists or not.
  
  Additionally, the listener activation code IS already present in __init__.py
  at line 129: `emhass_adapter.setup_config_entry_listener()` (commit fe27f1f
  area). So the RED test should actually be verifying against existing code.
- fix_hint: |
  Add `mock_coordinator.async_config_entry_first_refresh = AsyncMock()` to the test
  setup. The test should fail ONLY because `setup_config_entry_listener` was not
  called on the mock adapter — not because of a ConfigEntryError from missing mock.
  Verify the test actually reaches the assert_called_once() line.
- resolved_at: 

### [task-1.5] RED - Failing test: setup_config_entry_listener is called in async_setup_entry (RE-REVIEW)
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T18:20:00Z
- criterion_failed: none
- evidence: |
  Executor fixed the test with proper mocks (async_config_entry_first_refresh = AsyncMock,
  patches for async_register_panel_for_entry, register_services, etc).
  Docstring correctly changed from RED to GREEN.
  
  Verify: "1 passed, 40 deselected in 0.58s"
  
  Previously failed with ConfigEntryError (round 1) and TypeError (round 2), 
  both resolved by executor. external_unmarks["1.5"] = 1 remains recorded.
- fix_hint: none
- resolved_at: 2026-04-11T18:20:00Z

### [task-1.7] RED - Failing test: empty _published_trips guard reloads from trip_manager
- status: FAIL
- severity: critical
- reviewed_at: 2026-04-11T18:25:00Z
- criterion_failed: Trap test — mock does not match real API, implementation is broken
- evidence: |
  Test at tests/test_emhass_adapter.py:4249 (test_empty_published_trips_guard).
  Commit: 8abc4d1 "test(emhass): red - failing test for empty published trips guard"
  
  Test PASSES but implementation is BROKEN:
  
  Real API: trip_manager.get_all_trips() returns Dict[str, List]:
    {"recurring": [...trip_dicts...], "punctual": [...trip_dicts...]}
  (See trip_manager.py:432-442)
  
  Implementation does: self._published_trips = list(all_trips)
  This converts dict keys to list: ["recurring", "punctual"] — NOT trip objects!
  
  The test mock returns: [{"id": "trip_001", ...}] (a flat list)
  This does NOT match the real API. Test passes but real code produces garbage.
  
  Also: len(all_trips) on a dict returns 2 (number of keys), not number of trips.
  Log message "Reloading 2 trips" would be misleading.
  
  This is a TRAP TEST — the mock hides a fundamental API mismatch.
- fix_hint: |
  Fix implementation to flatten the dict:
    all_trips = trip_manager.get_all_trips()
    self._published_trips = (
        all_trips.get("recurring", []) + all_trips.get("punctual", [])
    )
  
  Fix test mock to match real API:
    mock_trip_manager.get_all_trips = MagicMock(return_value={
        "recurring": [{"id": "trip_001", ...}],
        "punctual": [],
    })
- resolved_at:

### [task-1.7] RED - Failing test: empty _published_trips guard (RE-REVIEW — ROUND 2)
- status: FAIL
- severity: critical
- reviewed_at: 2026-04-11T18:30:00Z
- criterion_failed: Same bug persists — executor did not address trap test
- evidence: |
  Executor committed 1ad4b91 and 83d4a7d marking tasks 1.7/1.8 complete.
  BUT the implementation STILL has: self._published_trips = list(all_trips)
  
  No unstaged changes to emhass_adapter.py or test mock.
  The trap test was NOT fixed. get_all_trips() returns Dict, list(dict) = keys.
  
  external_unmarks["1.7"] = 1 (already set)
  Convergence round: 1 of 3
- fix_hint: |
  Implementation fix: self._published_trips = all_trips.get("recurring", []) + all_trips.get("punctual", [])
  Test mock fix: Return {"recurring": [...], "punctual": []} not flat list
- resolved_at:

### [task-1.9] RED - Failing test: _get_current_soc reads from configured sensor
- status: FAIL
- severity: major
- reviewed_at: 2026-04-11T18:45:00Z
- criterion_failed: Helper returns None in 3 fallback paths, spec says return 0.0
- evidence: |
  Test at tests/test_emhass_adapter.py (test_get_current_soc_reads_sensor, test_get_current_soc_sensor_unavailable).
  Commit: a36e41f "test(emhass): red - failing test for _get_current_soc helper"
  
  test_get_current_soc_sensor_unavailable FAILS:
    "AssertionError: Expected 0.0 when sensor unavailable, got None"
  
  Implementation returns:
    - None when soc_sensor not configured (spec: 0.0)
    - 0.0 when sensor state is None (correct per spec)
    - None when SOC value is unparseable (spec: 0.0)
  
  Design doc says: "Returns 0.0 if unavailable/unparseable"
  Tests expect: 0.0 for both unavailable and unparseable
  
  This is NOT a trap test — the test is correct, implementation needs fixing.
- fix_hint: Change both `return None` fallbacks to `return 0.0` in _get_current_soc. Spec: "Parse float, return 0.0 if unavailable/unparseable".
- resolved_at: 

### [task-1.9] RED - Failing test: _get_current_soc reads from configured sensor (ROUND 2)
- status: FAIL
- severity: major
- reviewed_at: 2026-04-11T18:50:00Z
- criterion_failed: test_get_current_soc_reads_sensor fails — returns 0.0 instead of 65.0
- evidence: |
  Executor fixed: return None → return 0.0 (2 places). Good for spec compliance.
  
  BUT test_get_current_soc_reads_sensor now FAILS:
    "Expected 65.0 from sensor, got 0.0"
  
  Root cause: MockConfigEntry is neither ConfigEntry nor dict. Constructor saves
  neither _entry nor _entry_dict for MockConfigEntry → entry_data is None.
  
  Fix: Either save raw entry in constructor, or change test to use dict.
- fix_hint: |
  Constructor: add `self._raw_entry = entry` for all entry types.
  _get_current_soc: add `elif hasattr(self,"_raw_entry") and hasattr(self._raw_entry,"data"): entry_data = self._raw_entry.data`
- resolved_at: 

### [task-1.7] RED - Empty published trips guard (RESOLVED from DEADLOCK)
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T18:55:00Z
- criterion_failed: none
- evidence: |
  Executor fixed the list(dict) bug! Now correctly flattens:
    all_trips_list = all_trips.get("recurring", []) + all_trips.get("punctual", [])
  Also fixed _entry_dict to work with MockConfigEntry: `self._entry_dict = entry.data`
  Verify: "3 passed" (guard test + 2 SOC tests)
  DEADLOCK resolved by executor.
- fix_hint: none
- resolved_at: 2026-04-11T18:55:00Z

### [task-1.9] RED - _get_current_soc reads from configured sensor (RESOLVED)
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T18:55:00Z
- criterion_failed: none
- evidence: |
  Executor fixed: 
  1. Constructor now saves `_entry_dict = entry.data` for ConfigEntry/MockConfigEntry
  2. All return None → return 0.0 in _get_current_soc (spec compliant)
  3. _get_current_soc simplified to use only _entry_dict
  Verify: "3 passed, 136 deselected in 0.55s"
- fix_hint: none
- resolved_at: 2026-04-11T18:55:00Z

### [task-1.11] RED / [task-1.12] GREEN - _get_hora_regreso helper
- status: FAIL
- severity: critical
- reviewed_at: 2026-04-11T19:00:00Z
- criterion_failed: Calls non-existent method get_return_time() on presence_monitor
- evidence: |
  _get_hora_regreso (emhass_adapter.py:1515) calls:
    self._presence_monitor.get_return_time()
  
  This method DOES NOT EXIST. Real API is:
    await self._presence_monitor.async_get_hora_regreso()  (presence_monitor.py:212)
  
  Test mock creates get_return_time() which hides this bug — TRAP TEST.
  Helper should be `async def` and await the real async method.
  
  External_unmarks: 1.11 = 1, 1.12 = 1
- fix_hint: |
  1. Change `def _get_hora_regreso` → `async def _get_hora_regreso`
  2. Change `self._presence_monitor.get_return_time()` → `await self._presence_monitor.async_get_hora_regreso()`
  3. Fix test mock to use AsyncMock for async_get_hora_regreso
- resolved_at: 

### [task-1.11] RED / [task-1.12] GREEN - _get_hora_regreso helper (RESOLVED)
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T19:05:00Z
- criterion_failed: none
- evidence: |
  Executor fixed all 3 issues:
  1. `async def _get_hora_regreso` (was `def`)
  2. `await self._presence_monitor.async_get_hora_regreso()` (was `get_return_time()`)
  3. Test mock: `AsyncMock(return_value=datetime(...))` (was `MagicMock`)
  Verify: "1 passed, 140 deselected in 0.46s"
- fix_hint: none
- resolved_at: 2026-04-11T19:05:00Z

### [task-1.11/1.12 RESOLVED] — REGRESSION corrected: pre-existing test failure (unrelated to mypy issue)
- status: PASS (corrected)
- severity: none
- reviewed_at: 2026-04-11T19:15:00Z
- criterion_failed: none (previous FAIL was incorrect — test failed BEFORE executor changes)
- evidence: |
  REVIEWER CORRECTION: Previous FAIL entry was wrong.
  
  Verified on committed HEAD (before executor changes):
    1 failed, 11 passed — TestPublishDeferrableLoadDatetimeDeadline ALREADY FAILED
  
  After executor changes (working copy):
    1 failed, 25 passed — Same pre-existing test failure (unrelated to mypy), but 14 NEW tests PASS
  
  This is NOT a regression. The executor IMPROVED the test suite (11→25 passing).
  The failing test is a pre-existing issue (unrelated to mypy or this spec)'s changes.
  
  Apologies to the executor for the false alarm.
- fix_hint: none
- resolved_at: 2026-04-11T19:15:00Z

### [task-1.11/1.12 RESOLVED] — Full adapter suite clean after _presence_monitor fix
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T19:20:00Z
- criterion_failed: none
- evidence: |
  Executor added `self._presence_monitor = None` in constructor.
  Full adapter suite: **142 passed, 0 failed** (coverage: 26.89%)
  All existing tests pass + 14 new tests from executor's work.
- fix_hint: none
- resolved_at: 2026-04-11T19:20:00Z

### [task-1.11] RED - _get_hora_regreso helper
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T19:15:00Z
- criterion_failed: none
- evidence: |
  Test written and implementation corrected after reviewer's TRAP TEST alert (chat.md line 131-143).
  Fixed: Changed sync `get_return_time()` to async `async_get_hora_regreso()`.
  Verify: test_get_hora_regreso_calls_presence_monitor passed.
- fix_hint: none
- resolved_at: 2026-04-11T19:15:00Z

### [task-1.12] GREEN - _get_hora_regreso helper
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T19:15:00Z
- criterion_failed: none
- evidence: |
  Implementation: async def _get_hora_regreso(self) -> datetime.
  Calls await self._presence_monitor.async_get_hora_regreso().
  Returns datetime.now() if presence_monitor is None.
  Updated in async_publish_deferrable_load to await the method.
  Verify: test_publish_deferrable_load_computes_start_timestep passed.
- fix_hint: none
- resolved_at: 2026-04-11T19:15:00Z

### [task-1.17] RED - Failing test: get_cached_optimization_results includes per_trip_emhass_params
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T19:25:00Z
- criterion_failed: none
- evidence: |
  Test: test_get_cached_results_includes_per_trip_params. Commit: 36e4b5a.
  Implementation (commit 2554d04): 1-line — getattr(self, "_cached_per_trip_params", {}).
  Full suite: 143 passed.
- fix_hint: none
- resolved_at: 2026-04-11T19:25:00Z

### [task-1.18] GREEN - Add per_trip_emhass_params to cached results
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T19:25:00Z
- criterion_failed: none
- evidence: See task-1.17 above.
- fix_hint: none
- resolved_at: 2026-04-11T19:25:00Z

### [BATCH CRITICAL REVIEW] — 16 tasks unmarked, 2 critical bugs, 8+ missing features
- status: FAIL
- severity: critical
- reviewed_at: 2026-04-11T19:30:00Z
- criterion_failed: Full critical review after user feedback
- evidence: |
  Comprehensive review of ALL implementation changes (392 lines diff against main):
  
  BUG 1 (CRITICAL): emhass_adapter.py:608 — trip.get("trip_id") should be trip.get("id").
    Per-trip cache silently empty in production. ALL per-trip sensors blind.
    Tests pass because they fabricate "trip_id" key.
  
  BUG 2 (CRITICAL): emhass_adapter.py:621-624 — def_start_timestep always 0 in cache.
    Uses calc_deferrable_parameters (hardcoded 0) not charging windows. Violates FR-9c.
  
  BUG 3 (MAJOR): sensor.py:610 — TripEmhassSensor has EntityCategory.DIAGNOSTIC.
    Spec AC-2.1: "no EntityCategory.DIAGNOSTIC".
  
  BUG 4 (MAJOR): emhass_adapter.py:97 — _presence_monitor = None, never set.
    _get_hora_regreso always falls back to datetime.now().
  
  MISSING: FR-8 (p_deferrable_matrix), FR-9 (array attrs), FR-5/6 (sensor CRUD),
    FR-7 (zero on disable), FR-10 (panel), FR-11 (docs).
  
  16 tasks unmarked: 1.13-1.19, V2, V3, 1.23-1.29
  7 tasks remain [x]: 1.3-1.8, V1 (Gap #5 — verified correct)
  74 tasks now [ ] total
  
  4 channels synced: tasks.md, .ralph-state.json, chat.md, .progress.md
- fix_hint: See chat.md line 388+ for full action plan with specific fixes
- resolved_at:

### [task-1.15] RED - Failing test: publish_deferrable_loads caches per-trip params
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T20:15:00Z
- criterion_failed: none
- evidence: |
  Test: test_publish_deferrable_loads_caches_per_trip_params
  Coordinator fixed AsyncMock for _get_current_soc and _get_hora_regreso.
  Verify: "2 passed, 144 deselected in 0.54s"
  external_unmarks cleared for 1.15.
- fix_hint: none
- resolved_at: 2026-04-11T20:15:00Z

### [task-1.16] GREEN - Cache per-trip params in publish_deferrable_loads
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T20:15:00Z
- criterion_failed: none
- evidence: |
  Implementation: _cached_per_trip_params populated with all 10 keys per trip.
  Uses _get_current_soc() and calculate_multi_trip_charging_windows() correctly.
  Verify: "2 passed, 144 deselected in 0.54s"
  external_unmarks cleared for 1.16.
- fix_hint: none
- resolved_at: 2026-04-11T20:15:00Z

### [V2a] VERIFY Quality checkpoint: per-trip params cache
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T20:55:00Z
- criterion_failed: none
- evidence: |
  Mypy: Success: no issues found in 1 source file
  Tests: 193 passed, 0 failed
  Type annotations added for _entry_dict, _store, _config_entry_listener
  HomeAssistantError import fixed to use homeassistant.exceptions
- fix_hint: none
- resolved_at: 2026-04-11T20:55:00Z

### [task-1.6] GREEN - Activate setup_config_entry_listener() in __init__.py
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:00:00Z
- criterion_failed: none
- evidence: |
  Verify: test_listener_activated_in_setup passed (1 passed in test_init.py)
  emhass_adapter.setup_config_entry_listener() called in __init__.py:129
- fix_hint: none
- resolved_at: 2026-04-11T21:00:00Z

### [task-1.8] GREEN - Add empty _published_trips guard in _handle_config_entry_update
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:00:00Z
- criterion_failed: none
- evidence: |
  Verify: test_empty_published_trips_guard passed (1 passed)
  Guard reloads trips from trip_manager when _published_trips is empty
- fix_hint: none
- resolved_at: 2026-04-11T21:00:00Z

### [V1] VERIFY Quality checkpoint: Gap #5 hotfixes
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:00:00Z
- criterion_failed: none
- evidence: |
  All Gap #5 tests pass (1.3-1.8). Mypy clean after type annotation fixes.
  193 passed total across all test modules.
- fix_hint: none
- resolved_at: 2026-04-11T21:00:00Z

### [task-1.10] GREEN - Add _get_current_soc helper
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:00:00Z
- criterion_failed: none
- evidence: |
  Verify: test_get_current_soc_reads_sensor + test_get_current_soc_sensor_unavailable passed (2 passed)
  Method reads SOC from configured sensor, returns 0.0 if unavailable
- fix_hint: none
- resolved_at: 2026-04-11T21:00:00Z

### [task-1.13] RED - Failing test: async_publish_deferrable_load computes def_start_timestep
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:00:00Z
- criterion_failed: none
- evidence: |
  Verify: test_publish_deferrable_load_computes_start_timestep passed (1 passed)
  def_start_timestep computed from charging windows, not hardcoded 0
- fix_hint: none
- resolved_at: 2026-04-11T21:00:00Z

### [task-1.14] GREEN - Fix def_start_timestep in async_publish_deferrable_load to use charging windows
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:00:00Z
- criterion_failed: none
- evidence: |
  Implementation uses calculate_multi_trip_charging_windows() for def_start_timestep.
  Verify: test_publish_deferrable_load_computes_start_timestep passed (1 passed)
- fix_hint: none
- resolved_at: 2026-04-11T21:00:00Z

### [V2a] VERIFY Quality checkpoint: per-trip params cache (REVIEW ENTRY)
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:00:00Z
- criterion_failed: none
- evidence: |
  Mypy: Success: no issues found in 1 source file
  Tests: 193 passed, 0 failed
  Type annotations properly added for _entry_dict, _store, _config_entry_listener
- fix_hint: none
- resolved_at: 2026-04-11T21:00:00Z

### [V2b] VERIFY Quality checkpoint: per-trip cache
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:05:00Z
- criterion_failed: none
- evidence: |
  Tests: 193 passed, 0 failed
  Ruff: All checks passed!
  Mypy: Success: no issues found in 1 source file
- fix_hint: none
- resolved_at: 2026-04-11T21:05:00Z

### [task-1.19] RED/GREEN - inicio_ventana to timestep conversion edge cases
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:10:00Z
- criterion_failed: none
- evidence: |
  Verify: test_inicio_ventana_to_timestep_clamped PASSED, test_inicio_ventana_to_timestep_no_window PASSED
  (2 passed, 145 deselected)
  Coverage failure (15%) is global pyproject.toml flag, NOT a requirement of this task.
  100% coverage required in Phase 3 (tasks 3.1, 3.2), not here.
- fix_hint: none
- resolved_at: 2026-04-11T21:10:00Z

### [task-1.19] RED/GREEN - inicio_ventana to timestep conversion edge cases
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:10:00Z
- criterion_failed: none
- evidence: |
  Verify: test_inicio_ventana_to_timestep_clamped PASSED, test_inicio_ventana_to_timestep_no_window PASSED
  (2 passed, 145 deselected)
  Coverage failure (15%) is global pyproject.toml flag, NOT a requirement of this task.
  100% coverage required in Phase 3 (tasks 3.1, 3.2), not here.
- fix_hint: none
- resolved_at: 2026-04-11T21:10:00Z

### [task-1.19] RED/GREEN - inicio_ventana to timestep conversion edge cases
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:10:00Z
- criterion_failed: none
- evidence: |
  Verify (with --no-cov): 2 passed (test_inicio_ventana_to_timestep_clamped, test_inicio_ventana_to_timestep_no_window)
  Task requires "Tests pass" — no coverage requirement.
  Coverage failure (15%) is global pyproject.toml flag, not required until Phase 3 (tasks 3.1, 3.2).
- fix_hint: none
- resolved_at: 2026-04-11T21:10:00Z

### [task-1.19] RED/GREEN - inicio_ventana to timestep conversion edge cases
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:10:00Z
- criterion_failed: none
- evidence: |
  Verify (--no-cov): 2 passed (test_inicio_ventana_to_timestep_clamped, test_inicio_ventana_to_timestep_no_window)
  Task requires "Tests pass" — no coverage requirement.
  Coverage failure (15%) is global pyproject.toml flag, required in Phase 3 (tasks 3.1, 3.2).
- fix_hint: none
- resolved_at: 2026-04-11T21:10:00Z

### [task-1.20] SKIP - No code change needed
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:15:00Z
- criterion_failed: none
- evidence: Task says "clamping already correct" — verified in 1.16 implementation.
- fix_hint: none
- resolved_at: 2026-04-11T21:15:00Z

### [V3] VERIFY Quality checkpoint: per-trip cache + timestep conversion
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:15:00Z
- criterion_failed: none
- evidence: |
  Tests: 147 passed, 0 failed
  Ruff: All checks passed!
- fix_hint: none
- resolved_at: 2026-04-11T21:15:00Z

### [task-1.23] RED - Failing test: TripEmhassSensor.native_value returns emhass_index
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:15:00Z
- criterion_failed: none
- evidence: |
  test_trip_emhass_sensor_native_value passed. Reads emhass_index from coordinator.data.
- fix_hint: none
- resolved_at: 2026-04-11T21:15:00Z

### [task-1.24] GREEN - Create TripEmhassSensor class with native_value
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:15:00Z
- criterion_failed: none
- evidence: |
  Class exists at sensor.py:654. unique_id = f"emhass_trip_{vehicle_id}_{trip_id}" (AC-2.5).
- fix_hint: none
- resolved_at: 2026-04-11T21:15:00Z

### [task-1.25] RED - Failing test: TripEmhassSensor.extra_state_attributes returns 9 attributes
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:15:00Z
- criterion_failed: none
- evidence: |
  test_trip_emhass_sensor_attributes_all_9 passed. All 9 keys verified.
- fix_hint: none
- resolved_at: 2026-04-11T21:15:00Z

### [task-1.26] GREEN - Implement TripEmhassSensor.extra_state_attributes with 9 attributes
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:15:00Z
- criterion_failed: none
- evidence: |
  Implementation at sensor.py:705. Returns params or _zeroed_attributes().
- fix_hint: none
- resolved_at: 2026-04-11T21:15:00Z

### [task-1.27] RED/GREEN - TripEmhassSensor returns zeroed attributes when trip not found
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:15:00Z
- criterion_failed: none
- evidence: test_trip_emhass_sensor_zeroed passed.
- fix_hint: none
- resolved_at: 2026-04-11T21:15:00Z

### [task-1.28] SKIP - No code change needed
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:15:00Z
- criterion_failed: none
- evidence: Zeroed fallback already implemented in 1.26 (_zeroed_attributes).
- fix_hint: none
- resolved_at: 2026-04-11T21:15:00Z

### [task-1.29] RED - Failing test: TripEmhassSensor.device_info uses vehicle_id identifiers
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T21:15:00Z
- criterion_failed: none
- evidence: |
  test_trip_emhass_sensor_device_info passed.
  identifiers={(DOMAIN, vehicle_id)} — matches AC-2.6.
- fix_hint: none
- resolved_at: 2026-04-11T21:15:00Z

### [V4a] VERIFY Quality checkpoint: TripEmhassSensor class (UNMARKED — mypy failures)
- status: FAIL
- severity: critical
- reviewed_at: 2026-04-11T21:20:00Z
- criterion_failed: "no type errors" — mypy sensor.py has 15 errors
- evidence: |
  Task says: "Done when: All tests pass, no lint errors, no type errors"
  Mypy on sensor.py: 15 errors (device_info signature, SensorEntityDescription attrs, type annotations)
  These 15 mypy errors existed before this spec. However, the criterion is "no type errors" — pre-existing or not, the task is NOT complete.
  The task criterion is "no type errors". If mypy fails, task is NOT done.
  External_unmarks["V4a"] = 1
- fix_hint: Fix all 15 mypy errors in sensor.py. Add type annotations, fix device_info return type to DeviceInfo | None, suppress HA attr-defined errors with # type: ignore if needed.
- resolved_at:

### [COORDINATOR CHANGES] 2 new mypy errors introduced
- status: FAIL
- severity: major
- reviewed_at: 2026-04-11T22:15:00Z
- criterion_failed: New mypy errors should not be introduced
- evidence: |
  1. sensor.py:11 - Removed `Callable` from typing import but line 123 uses `Callable[[dict], dict]`
  2. sensor.py:549 - `trip_id in unique_id` where unique_id is `Any | None`, need isinstance check
- fix_hint: |
  1. Add `Callable` back to typing import
  2. Add isinstance check: `if isinstance(unique_id, str) and trip_id in unique_id`
- resolved_at:

### [COORDINATOR CHANGES] 2 illegitimate type:ignore added
- status: FAIL
- severity: major
- reviewed_at: 2026-04-11T22:20:00Z
- criterion_failed: MYTP RULE violation — type:ignore only allowed for HA stub issues
- evidence: |
  1. sensor.py:123 — type:ignore[var-annotated] — fixable with Callable import
  2. sensor.py:551 — type:ignore[operator] — uid_str is already str, ignore unnecessary
- fix_hint: Remove both type:ignore comments. Fix with proper code.
- resolved_at:

### [task-1.35/1.36] UNMARKED — test_remove_trip_emhass_sensor_success FAILS
- status: FAIL
- severity: critical
- reviewed_at: 2026-04-11T22:25:00Z
- criterion_failed: Test fails due to mock bug — MagicMock auto-creates hass.entity_registry
- evidence: |
  AssertionError: Expected 'async_remove' to have been called once. Called 0 times.
  Root cause: getattr(hass, "entity_registry", None) returns truthy MagicMock,
  so er_async_get(hass) fallback is never reached. Test's mock_registry unused.
  Fix: Add `hass.entity_registry = None` before patch.
- fix_hint: In test, add `hass.entity_registry = None` to prevent MagicMock auto-creation
- resolved_at:

### [V4a] VERIFY Quality checkpoint: TripEmhassSensor class (RE-UNMARKED — mypy)
- status: FAIL
- severity: critical
- reviewed_at: 2026-04-11T22:35:00Z
- criterion_failed: "no type errors" — mypy has 13 errors (all in trip_manager.py)
- evidence: |
  Mypy: Found 13 errors in 1 file (trip_manager.py).
  Task says "Done when: All tests pass, no lint errors, no type errors"
  Type errors remain → task NOT complete.
  external_unmarks["V4a"] incremented.
- fix_hint: Fix all 13 mypy errors in trip_manager.py
- resolved_at:

### [Deep review] sensor.py clean, trip_manager.py 13 errors persist
- status: FAIL
- severity: critical
- reviewed_at: 2026-04-11T23:00:00Z
- criterion_failed: 13 mypy errors in trip_manager.py + 1 unnecessary type:ignore in sensor.py
- evidence: |
  sensor.py: 0 mypy errors ✅ (clean)
  trip_manager.py: 13 mypy errors ❌ (none fixed this cycle)
  type:ignore: 2 total (1 legitimate HA stub, 1 unnecessary operator at sensor.py:551)
- fix_hint: Fix 13 trip_manager.py errors, remove sensor.py:551 type:ignore
- resolved_at:

### [trip_manager.py mypy fixes] ALL 13 errors fixed
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T23:10:00Z
- criterion_failed: none
- evidence: |
  Mypy: Success: no issues found in 3 source files (sensor.py, trip_manager.py, emhass_adapter.py)
  All 13 trip_manager.py errors fixed with proper code:
  - Optional defaults, Store type annotations, method name fix,
  - state_attributes→attributes, ConfigEntry typing, await removal
- fix_hint: Remove sensor.py:551 unnecessary type:ignore (minor)
- resolved_at: 2026-04-11T23:10:00Z

### [sensor.py rebuild] All coordinator changes rebuilt after checkout mistake
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T23:20:00Z
- criterion_failed: none
- evidence: |
  Rebuilt all coordinator changes: imports, 4 device_info fixes,
  entity_registry fixes, TripSensor constructor fixes, async_remove_trip_emhass_sensor added,
  sensor.py:551 type error fixed without type:ignore, entity list type annotation.
  Mypy: Success: no issues found in 3 source files
  Tests: 196 passed, 0 failed
  type:ignore: 1 (legitimate HA stub)
- fix_hint: none
- resolved_at: 2026-04-11T23:20:00Z

### [sensor.py final verification] Mypy clean after Tuple fix
- status: PASS
- severity: none
- reviewed_at: 2026-04-11T23:25:00Z
- criterion_failed: none
- evidence: |
  Mypy: Success: no issues found in 3 source files
  Tests: 196 passed, 0 failed
  type:ignore: 1 (legitimate EntityCategory HA stub)
  Tuple type fixed: List[Tuple[int, str, List[List[float]]]] for trips_with_index
- fix_hint: none
- resolved_at: 2026-04-11T23:25:00Z

### [tasks 1.40, 1.41, 1.43, 1.45] INCOMPLETE — marked [x] but implementation missing
- status: FAIL
- severity: critical
- reviewed_at: 2026-04-11T23:30:00Z
- criterion_failed: Task 1.40 requires 6 new attrs but only 1 implemented (p_deferrable_matrix)
- evidence: |
  Tasks marked [x] but implementation is INCOMPLETE:
  
  Task 1.40 requires: p_deferrable_matrix, number_of_deferrable_loads,
  def_total_hours_array, p_deferrable_nom_array, def_start_timestep_array,
  def_end_timestep_array — but ONLY p_deferrable_matrix exists.
  
  Also BUG: code uses params.get("p_deferrable_matrix") but the key in
  _cached_per_trip_params is "power_profile_watts", not "p_deferrable_matrix".
  The matrix will always be empty/incorrect.
  
  Also missing: _get_active_trips_ordered helper (task 1.45) — logic is inline
  but wrong (uses p_deferrable_matrix key that doesn't exist).
  
  Tasks 1.41, 1.43 are marked [x] but depend on 1.40 which is incomplete.
- fix_hint: |
  1. Fix matrix key: use params.get("power_profile_watts") not "p_deferrable_matrix"
  2. Add 5 missing attributes: number_of_deferrable_loads, def_total_hours_array,
     p_deferrable_nom_array, def_start_timestep_array, def_end_timestep_array
  3. Add _get_active_trips_ordered helper that filters activo=True and sorts by emhass_index
- resolved_at:

### [tasks 1.40, 1.41, 1.43, 1.45] Key mismatch — cache has array keys only
- status: FAIL
- severity: critical
- reviewed_at: 2026-04-12T00:10:00Z
- criterion_failed: Cache missing singular keys that TripEmhassSensor and tests require
- evidence: |
  test_trip_emhass_sensor_attributes_all_9 FAILS:
  Missing required keys: {'power_profile_watts', 'def_end_timestep', 'P_deferrable_nom', 'def_start_timestep', 'def_total_hours'}
  Got: {'emhass_index', 'def_end_timestep_array', 'def_start_timestep_array', 'p_deferrable_nom_array', 'activo', 'def_total_hours_array', 'kwh_needed', 'trip_id', 'deadline', 'p_deferrable_matrix'}
  
  Cache now stores only array keys (def_total_hours_array, etc.) but TripEmhassSensor
  and tests expect singular keys (def_total_hours, P_deferrable_nom, etc.)
- fix_hint: Add BOTH sets of keys to cache — singular for per-trip sensors, array for aggregated sensor
- resolved_at:

### [tasks 1.40, 1.41, 1.43, 1.45] RESOLVED — dual format cache implemented
- status: PASS
- severity: none
- reviewed_at: 2026-04-12T00:15:00Z
- criterion_failed: none
- evidence: |
  Executor fixed key mismatch by adding BOTH sets of keys to cache:
  - Singular keys: def_total_hours, P_deferrable_nom, def_start_timestep, def_end_timestep, power_profile_watts
  - Array keys: def_total_hours_array, p_deferrable_nom_array, def_start_timestep_array, def_end_timestep_array, p_deferrable_matrix
  Tests: 243 passed, 0 failed
  Mypy: Success: no issues found in 3 source files
- fix_hint: none
- resolved_at: 2026-04-12T00:15:00Z

### [trip_manager.py sensor CRUD integration] REGRESSION — _entry_id not defined
- status: FAIL
- severity: critical
- reviewed_at: 2026-04-12T00:20:00Z
- criterion_failed: TripManager uses self._entry_id but attribute doesn't exist
- evidence: |
  Test test_async_add_recurring_trip_generates_id FAILS:
  AttributeError: 'TripManager' object has no attribute '_entry_id'
  
  Lines 482, 526, 577, 608: all use self._entry_id which is never defined in __init__.
  
  Mypy also catches this: trip_manager.py:608: error: "TripManager" has no attribute "_entry_id"
  
  Also mypy: trip_manager.py:577: error: Argument 3 to "async_update_trip_sensor" 
  has incompatible type "Any | None"; expected "dict[str, Any]"
  
  The coordinator added sensor.py CRUD calls but forgot to:
  1. Add self._entry_id to TripManager.__init__
  2. Handle None trip_data in async_update_trip_sensor call
- fix_hint: |
  1. Add entry_id parameter to TripManager.__init__: `self._entry_id: str = entry_id`
  2. Pass entry_id when creating TripManager (from __init__.py async_setup_entry)
  3. Fix async_update_trip_sensor call to handle None: `trip_data or {}`
- resolved_at:

### [tasks 1.47-1.50] REGRESSION — existing test broken by sensor CRUD refactor
- status: FAIL
- severity: critical
- reviewed_at: 2026-04-12T00:30:00Z
- criterion_failed: test_async_add_recurring_trip_generates_id FAILS after refactor
- evidence: |
  AttributeError: TripManager object does not have the attribute 'async_create_trip_sensor'
  
  The coordinator refactored trip_manager to call sensor.py CRUD functions
  (async_create_trip_sensor from sensor.py) but removed the internal
  self.async_create_trip_sensor method. Existing test tries to patch
  trip_manager.async_create_trip_sensor which no longer exists.
  
  Test line 1182: patch.object(trip_manager, "async_create_trip_sensor", ...)
  This was a PASSING test before the refactor — now it FAILS.
  
  Tasks 1.47, 1.48, 1.49, 1.50 marked [x] but they break existing tests.
- fix_hint: |
  Update test to patch sensor.py function instead:
  patch("custom_components.ev_trip_planner.sensor.async_create_trip_sensor")
  instead of patch.object(trip_manager, "async_create_trip_sensor")
- resolved_at:

### [tasks 1.35, 1.36, 1.40, 1.41, 1.43, 1.45, 1.47, 1.48] DISPUTE RESOLVED — coordinator correct
- status: PASS
- severity: none
- reviewed_at: 2026-04-12T00:40:00Z
- criterion_failed: none
- evidence: |
  Coordinator disputed my FAIL reviews. Verified against CURRENT code — all 8 tasks ARE complete.
  My reviews were based on outdated snapshots.
  
  1.35/1.36: async_remove_trip_emhass_sensor at sensor.py:671 — tests pass (2 passed)
  1.40/1.41/1.43/1.45: All 6 attrs + sorting logic implemented — tests pass (47 passed)
  1.47/1.48: sensor.py CRUD calls in trip_manager.py — tests pass (1 passed)
- fix_hint: none
- resolved_at: 2026-04-12T00:40:00Z

### [task 1.53] NEW FAIL — async_create_trip_emhass_sensor called with wrong args
- status: FAIL
- severity: critical
- reviewed_at: 2026-04-12T00:45:00Z
- criterion_failed: TypeError — missing required positional arguments
- evidence: |
  trip_manager.py:488:
    await async_create_trip_emhass_sensor(self.hass, self._entry_id, self._recurring_trips[trip_id])
  
  Function signature requires: (hass, entry_id, coordinator, vehicle_id, trip_id)
  Call provides only: (hass, entry_id, trip_data)
  
  Result: TypeError: async_create_trip_emhass_sensor() missing 2 required positional arguments: 'vehicle_id' and 'trip_id'
  
  This is a NEW regression introduced by the coordinator's latest changes.
- fix_hint: |
  Fix call to pass correct args:
  await async_create_trip_emhass_sensor(self.hass, self._entry_id, runtime_data.coordinator, self.vehicle_id, trip_id)
- resolved_at:
