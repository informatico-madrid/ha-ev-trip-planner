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
