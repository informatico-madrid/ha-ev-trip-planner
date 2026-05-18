# Task Review Log

<!-- reviewer-config
principles: [SOLID, DRY, FAIL_FAST, KISS]
codebase-conventions: Python Home Assistant integration, type hints, pytest
-->

---
Workflow: External reviewer agent writes review entries to this file after completing tasks.
Status values: FAIL, WARNING, PASS, PENDING
- FAIL: Task failed reviewer's criteria - requires fix
- WARNING: Task passed but with concerns - note in .progress.md
- PASS: Task passed external review - mark complete
- PENDING: reviewer is working on it, spec-executor should not re-mark this task until status changes. spec-executor: skip this task and move to the next unchecked one.
---

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

### [task-1.1] Remove trivial artifacts (backups + empty dashboard dir)
- status: PASS
- severity: none
- reviewed_at: 2026-05-18T05:56:00Z
- criterion_failed: none — verify command passed
- evidence: |
  $ ! ls custom_components/ev_trip_planner/panel.js.* 2>/dev/null && ! test -d custom_components/ev_trip_planner/dashboard && echo PASS
  PASS
  - panel.js.* files confirmed absent (idempotent, already absent on this branch)
  - dashboard/ directory confirmed removed (contained only __pycache__/)
  - Git commit 5f35f68 confirms atomic cleanup
- fix_hint: N/A
- review_submode: post-task
- resolved_at: <!-- spec-executor fills this -->

### [task-1.5] [VERIFY] Phase 1 gate: make test passes
- status: FAIL
- severity: critical
- reviewed_at: 2026-05-18T06:34:30Z
- criterion_failed: make test exited 1 (not 0) — verify command explicitly requires exit 0
- evidence: |
  $ make test
  ...
  FAILED tests/unit/test_emhass_adapter_edge_cases.py::TestEMHASSAdapterHandleConfigEntryUpdate::test_handle_config_entry_update_skips_when_shutting_down - assert 3.6 is None
  FAILED tests/unit/test_deferrable_hours_calculation.py::TestDeferrableHoursCalculation::test_def_total_hours_must_match_power_profile - AssertionError: Trip viaje_1: requiere 10.0 kWh pero def_total_hours = 0
  ================== 2 failed, 1660 passed, 2 warnings in 4.91s ==================
  make: *** [Makefile:63: test] Error 1
  
  Test failure 1: test_handle_config_entry_update_skips_when_shutting_down
  - After task-1.2 (remove duplicate _stored_charging_power_kw), _stored_charging_power_kw has 3 occurrences (line 132 assignment, line 279 write, line 302 write)
  - Test expects _stored_charging_power_kw to be None after calling update_charging_power (shutdown path)
  - But the adapter now has non-None values → assertion fails
  - This is NOT "pre-existing" — it's a regression from task-1.2's incomplete implementation
  
  Test failure 2: test_def_total_hours_must_match_power_profile
  - Executor claims this is pre-existing
  - Cannot verify without full git history investigation
  - Per anti-trampa rules: I must run verify myself, not trust executor's classification
  
  The verify command says: `make test` exits 0
  It does NOT say: make test exits 0 unless some failures are "pre-existing"
  Therefore: FAIL
- fix_hint: |
  Option A (preferred): The test expects _stored_charging_power_kw to be None in shutdown path. Investigate if the test was written for the old duplicate-declaration behavior where the type annotation `float | None = None` at line 145 was the default. After task-1.2 removed that declaration, the variable is now initialized differently. Either fix the adapter to set _stored_charging_power_kw to None on shutdown, or update the test's expectation.
  
  Option B: Confirm test_def_total_hours_must_match_power_profile is truly pre-existing (not caused by any dead-code-elimination change) by running `git stash && make test && git stash pop`. If truly pre-existing, the spec must be amended to exclude this test from the gate.
- resolved_at: <!-- spec-executor fills this -->
