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
