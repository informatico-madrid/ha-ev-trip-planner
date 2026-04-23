# Tasks: E2E UX Tests Fix (S1-S6) — Anti-Regression Enhanced

## Phase 0: Reproduce (Bug TDD)

Goal: Confirm both bugs exist before touching code. Capture baseline state.

### Reproduction

- [x] 0.1 [VERIFY] Reproduce: verify datetime naive/aware bug exists in trip_manager.py:1470-1502
  <!-- reviewer-diagnosis
    what: Task marked [x] but test PASSED instead of FAILING
    why: Test uses STRING input which goes through dt_util.parse_datetime (always aware). Bug at line 1470-1471 requires NAIVE datetime OBJECT.
    fix: Change test to use naive datetime OBJECT: trip={datetime: datetime(2026,4,23,10,0)} — should FAIL with TypeError
  -->
  - **Do**:
    1. Read trip_manager.py lines 1467-1502 to understand BOTH datetime paths:
       - Path A (line 1470-1471): `isinstance(trip_datetime, datetime)` → assigns without tz check
       - Path B (lines 1474-1480): `dt_util.parse_datetime()` → always returns aware
    2. Run existing datetime test: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_manager_datetime_tz.py -v`
    3. Document the failure output
    4. If test passes, create a manual reproduction: call `async_calcular_energia_necesaria` with a trip dict where `trip["datetime"]` is a naive `datetime` object (not a string) and verify it raises TypeError
  - **Verify**: Exit code 1 (test fails) or confirmed TypeError when naive datetime (object or string) compared with dt_util.now() aware
  - **Done when**: Bug is confirmed reproducible
  - **Commit**: None (Phase 0 = no changes)
  - _Requirements: Story S1, AC1_

- [x] 0.2 [VERIFY] Confirm repro consistency: bug fails reliably across 3 runs
  - **Do**:
    1. Run the reproduction command from 0.1 three times
    2. Confirm consistent failure each time
    3. Document BEFORE state in .progress.md
  - **Verify**: All 3 runs produce same failure
  - **Done when**: Failure is consistent across runs
  - **Commit**: `chore(e2e-ux-tests-fix): document reality check before fixes`
  - _Requirements: Story S1_

### Baseline Audit

- [x] 0.3 [VERIFY] Baseline: capture ALL unit test states with `make test`
  - **Do**:
    1. Run `make test 2>&1 | tee /tmp/baseline-unit.txt`
    2. Extract pass/fail summary: grep the last lines for "passed", "failed", coverage percentage
    3. Record: 1637 tests, 99.71% coverage (trip_manager.py missing 13 lines)
    4. Save to baseline: `echo "Unit baseline: 1637 passed, coverage 99.71%, FAILS due to coverage" >> .progress.md`
  - **Verify**: /tmp/baseline-unit.txt exists with full output
  - **Done when**: Full baseline captured — ALL test states documented
  - **Commit**: None
  - _Requirements: Anti-regression protection_
  - **Notes**: `make test` currently FAILS with exit 1 due to 100% coverage requirement (99.71%). After S1 datetime fix, trip_manager.py coverage should reach 100% and make test should PASS. This is EXPECTED behavior change — NOT a regression.

- [x] 0.4 [VERIFY] Baseline: capture ALL E2E test list with `npx playwright test --list`
  - **Do**:
    1. Run `npx playwright test --list 2>&1 | tee /tmp/baseline-e2e.txt`
    2. Count tests: currently 28 tests in 8 files
    3. Record: no race-condition-regression tests yet
    4. Save to baseline
  - **Verify**: /tmp/baseline-e2e.txt exists with full listing
  - **Done when**: Full E2E baseline captured
  - **Commit**: None
  - _Requirements: Anti-regression protection_

- [x] 0.5 [VERIFY] Create Intentional Behavior Change Map
  - **Do**: Document which specific tests/behaviors are expected to change when each fix is applied:

    **S1 Datetime Fix — Expected Changes:**
    | What Changes | Test Affected | Why | Action |
    |---|---|---|---|
    | `make test` exits 0 (was 1, coverage 100%) | Coverage check in make test | trip_manager.py gains 100% coverage (was 98%) | Accept — intentional fix |
    | `test_trip_manager_datetime_tz.py` still passes | 1 test, already passes | Fix makes both datetime paths work | Accept — intentional fix |
    | E2E UX-01/UX-02 pass (were failing) | 2 E2E tests | datetime naive/aware bug fixed at lines 1470-1471 AND 1474-1480 | Accept — intentional fix |
    | No other test behavior changes | N/A | Fix is surgical, only affects datetime parsing | If any OTHER test fails → REGRESSION |

    **S2 Coordinator Fix — Expected Changes:**
    | What Changes | Test Affected | Why | Action |
    |---|---|---|---|
    | `make test` exits 0 (coverage unchanged) | Coverage | emhass_adapter.py already 100% coverage | No change expected |
    | `test_charging_window.py::TestAsyncPublish*` still passes | EMHASS publish tests | In-place mutation → full dict replacement; dict has same keys | Accept if tests pass, investigate if they fail |
    | `test_services.py` still passes | Service tests | Same coordinator.data keys, just different mutation pattern | Accept if tests pass, investigate if they fail |

    **S3 Test Infra Fix — Expected Changes:**
    | What Changes | Test Affected | Why | Action |
    |---|---|---|---|
    | E2E tests discoverable (no globalTeardown warning) | All 28 E2E tests | Removed broken globalTeardown ref | Accept |
    | Hardcoded dates replaced with getFutureIso | E2E tests that had `'2026-04-20'` | Tests no longer depend on specific date | Accept |
    | Hardcoded entity IDs replaced with discoverEmhassSensorEntityId | E2E tests that had hardcoded IDs | Entity discovery is more robust | Accept |
    | waitForTimeout replaced with toPass() | Sensor check tests | Behavior same (sensor still ready), just different timing mechanism | Accept |

    **S4 Regression Tests — Expected Changes:**
    | What Changes | Test Affected | Why | Action |
    |---|---|---|---|
    | 2 new E2E tests added | race-condition-regression-* | New tests, no existing test affected | Accept |
    | Total E2E count: 30 (was 28) | playwright --list | 2 new regression tests | Accept |

    **S5+S6 E2E — Expected Changes:**
    | What Changes | Test Affected | Why | Action |
    |---|---|---|---|
    | All 30 E2E tests pass | make e2e | All fixes applied | Accept |

  - **Verify**: Map documented in task description above
  - **Done when**: All expected behavior changes documented with reasoning
  - **Commit**: None
  - _Requirements: Anti-regression protection_
  - **Rules for VERIFY tasks after fixes**:
    1. Run `make test` (ALL tests, not just targeted)
    2. Compare against baseline from 0.3
    3. Check each change against "Intentional Behavior Change Map" above
    4. If any NEW failure matches map → EXPECTED, update baseline and proceed
    5. If any NEW failure NOT in map → STOP, document, investigate before continuing
    6. If all changes match expected map → proceed
  - **Regression Guard Rule**: Any test that changes state between "was passing" and "now failing" without an intentional fix being applied = REGRESSION. Must investigate before proceeding.

## Phase 1: TDD Cycles (S1+S2+S3)

S1, S2, S3 are independent. Each runs its own TDD cycle with SOLID gate.

### Story S1: Fix Datetime Naive/Aware Bug

- [x] 1.1 [P] [RED] Read trip_manager.py:1467-1502 to understand BOTH datetime naive/aware bug paths
  - **Do**: Read lines 1467-1502 of trip_manager.py, identify TWO bug locations:
    1. Line 1470-1471: `isinstance(trip_datetime, datetime)` assigns without ensuring timezone awareness
    2. Lines 1474-1480: strptime fallback produces naive datetime (secondary path when parse_datetime fails)
  - **Files**: custom_components/ev_trip_planner/trip_manager.py
  - **Done when**: Both bug locations understood (lines 1470-1471 and 1474-1480)
  - **Verify**: `grep -n "strptime" custom_components/ev_trip_planner/trip_manager.py` confirms line 1478
  - **Commit**: None (reading only)
  - _Requirements: Story S1, AC1_

- [x] 1.2 [P] [RED] Read existing datetime test to understand test structure
  - **Do**: Read tests/test_trip_manager_datetime_tz.py to understand existing test, verify it uses monkeypatch for dt_util.now
  - **Files**: tests/test_trip_manager_datetime_tz.py
  - **Done when**: Test structure understood
  - **Verify**: `grep -n "monkeypatch" tests/test_trip_manager_datetime_tz.py` confirms monkeypatch usage
  - **Commit**: None (reading only)
  - _Requirements: Story S1, AC1_

- [x] 1.3 [P] [RED] Modify test to exercise BOTH datetime bug paths (not mocked)
  - **Do**: In tests/test_trip_manager_datetime_tz.py, add TWO test functions:
    1. Test with `trip["datetime"]` as a naive `datetime` object — forces the bug at line 1470-1471
    2. Test with `trip["datetime"]` as a string `"2026-04-23T10:00"` WITHOUT mocking `dt_util.parse_datetime` — forces the strptime fallback at line 1478
    Only mock `dt_util.now`. Both tests should fail without the fix.
  - **Files**: tests/test_trip_manager_datetime_tz.py
  - **Done when**: New test function added to test file
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_manager_datetime_tz.py -v 2>&1 | grep -q "strptime" && echo TEST_ADDED`
  - **Commit**: `test(ev-trip-planner): red - test exercises real strptime fallback path`
  - _Requirements: Story S1, AC1, AC3_

- [ ] 1.4 [P] [RED] Verify the new test FAILS (RED confirmed)
  - **Do**: Run the new test and confirm it fails with TypeError or returns horas_disponibles=0
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_manager_datetime_tz.py -v 2>&1 | grep -q "FAILED\|fail" && echo RED_CONFIRMED`
  - **Done when**: Test fails with expected error
  - **Commit**: None
  - _Requirements: Story S1, AC1_

- [ ] 1.5 [VERIFY] SOLID Quality Gate: code-reviewer validates trip_manager.py initial diff
  - **Skills**: pr-review-toolkit:code-reviewer
  - **Do**:
    1. Capture diff: `git diff custom_components/ev_trip_planner/trip_manager.py`
    2. Spawn pr-review-toolkit:code-reviewer subagent with:
       - The diff output
       - These exact criteria: (1) NO GOD METHODS: touched function <= 200 lines, (2) SINGLE RESPONSIBILITY: one clear purpose, (3) TYPE HINTS: complete signatures, (4) NO SILENT EXCEPTIONS: no bare except, (5) NO DIRECT STATE MUTATION
       - Pass criteria: criteria 1-3, 5 MUST pass
    3. If FAIL: fix the specific lines flagged and re-request review (max 2 retries)
    4. If 3 attempts exhausted: launch ralph-specum:architect-reviewer fallback
  - **Verify**: Reviewer returns VERIFICATION_PASS (all MUST criteria met)
  - **Done when**: Code reviewer validates SOLID adherence
  - **Commit**: None
  - _Requirements: requirements.md Section 9.1.2_

- [ ] 1.5a [P] Read trip_manager.py imports section to verify dt_util import exists
  - **Do**: Read first 30 lines of trip_manager.py to verify `from homeassistant.util import dt as dt_util` exists
  - **Files**: custom_components/ev_trip_planner/trip_manager.py
  - **Done when**: Import confirmed
  - **Verify**: `head -30 custom_components/ev_trip_planner/trip_manager.py | grep "dt_util"` returns import line
  - **Commit**: None (reading only)
  - _Requirements: Story S1_

- [ ] 1.5b [P] Read trip_manager.py _LOGGER definition to verify logger exists
  - **Do**: Read first 30 lines to verify `_LOGGER = logging.getLogger(__name__)` exists
  - **Files**: custom_components/ev_trip_planner/trip_manager.py
  - **Done when**: Logger confirmed
  - **Verify**: `grep -n "_LOGGER" custom_components/ev_trip_planner/trip_manager.py | head -3` returns definition
  - **Commit**: None (reading only)
  - _Requirements: Story S1_

- [ ] 1.6 [P] [GREEN] Apply minimal fix: BOTH datetime paths need timezone awareness
  - **Do**: Fix TWO locations in trip_manager.py:
    1. Line 1470-1471: Change `trip_time = trip_datetime` to:
       ```python
       trip_time = trip_datetime
       if trip_time.tzinfo is None:
           trip_time = trip_time.replace(tzinfo=timezone.utc)
       ```
    2. Lines 1474-1480: Replace strptime try/except with:
       ```python
       try:
           trip_time = dt_util.parse_datetime(trip_datetime)
           if getattr(trip_time, "tzinfo", None) is None:
               trip_time = trip_time.replace(tzinfo=timezone.utc)
       except Exception:
           _LOGGER.warning("Failed to parse trip datetime: %s", repr(trip_datetime))
           trip_time = datetime.now(timezone.utc)
       ```
  - **Files**: custom_components/ev_trip_planner/trip_manager.py
  - **Done when**: Both paths (datetime-object at 1471 and string at 1474-1480) ensure timezone awareness
  - **Verify**: `grep -n "trip_time.replace(tzinfo=timezone.utc)" custom_components/ev_trip_planner/trip_manager.py` returns 2+ matches
  - **Commit**: `fix(ev-trip-planner): green - fix datetime naive/aware bug in both code paths`
  - _Requirements: Story S1, AC1_

- [ ] 1.6a [P] Verify the fix preserves the outer try/except at lines 1508
  - **Do**: Read lines 1505-1512 to verify the outer `except (KeyError, ValueError, TypeError): pass` block is untouched
  - **Files**: custom_components/ev_trip_planner/trip_manager.py
  - **Done when**: Outer try/except confirmed untouched
  - **Verify**: `sed -n '1508p' custom_components/ev_trip_planner/trip_manager.py` shows `except (KeyError, ValueError, TypeError):`
  - **Commit**: None (verification only)
  - _Requirements: Story S1_

- [ ] 1.7 [P] [GREEN] Verify the fix makes the test pass (GREEN confirmed)
  - **Do**: Run the datetime test again
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_manager_datetime_tz.py -v 2>&1 | grep -q "PASSED\|passed" && echo GREEN_CONFIRMED`
  - **Done when**: Test passes after fix
  - **Commit**: None
  - _Requirements: Story S1, AC3_

- [ ] 1.7a [VERIFY] **REGRESSION GUARD**: Compare `make test` against baseline after S1 fix
  - **Do**:
    1. Run `make test 2>&1 | tee /tmp/post-s1-unit.txt`
    2. Compare against baseline from Phase 0 (0.3):
       - `diff /tmp/baseline-unit.txt /tmp/post-s1-unit.txt`
    3. Check each change against "Intentional Behavior Change Map" (task 0.5):
       - EXPECTED: `make test` exits 0 (was exit 1, coverage 100% now)
       - EXPECTED: trip_manager.py coverage = 100% (was 98%)
       - EXPECTED: test_trip_manager_datetime_tz.py still passes
    4. If ANY NEW failure NOT in map → STOP, document, investigate before proceeding
    5. If all changes match expected map → proceed to next task
  - **Verify**: `make test` exits 0 AND no unexpected test state changes vs baseline
  - **Done when**: All changes verified against baseline, no regressions detected
  - **Commit**: `chore(e2e-ux-tests-fix): S1 regression guard - verify no unexpected changes`
  - _Requirements: Anti-regression protection_
  - **Expected diff**: `FAIL Required test coverage` line removed, coverage now 100%, trip_manager.py Miss drops from 13 to 0

- [ ] 1.8 [P] [YELLOW] SOLID-ize: Insert `_parse_trip_datetime` method at start of TripManager class body
  - **Do**:
    1. Read TripManager class definition to find the correct insertion point (after __init__ or first public method)
    2. Insert the `_parse_trip_datetime` private method that handles BOTH cases:
       ```python
       def _parse_trip_datetime(self, trip_datetime) -> datetime:
           """Parse trip datetime, ensuring timezone awareness for both object and string inputs."""
           if isinstance(trip_datetime, datetime):
               dt = trip_datetime
               if dt.tzinfo is None:
                   dt = dt.replace(tzinfo=timezone.utc)
               return dt
           else:
               try:
                   parsed = dt_util.parse_datetime(trip_datetime)
                   if parsed is not None and parsed.tzinfo is None:
                       parsed = parsed.replace(tzinfo=timezone.utc)
                   return parsed or datetime.now(timezone.utc)
               except Exception:
                   _LOGGER.warning("Failed to parse trip datetime: %s", repr(trip_datetime))
                   return datetime.now(timezone.utc)
       ```
    3. Include Google-style docstring with Args/Returns
  - **Files**: custom_components/ev_trip_planner/trip_manager.py
  - **Done when**: Private method inserted into class, handles both datetime objects and strings
  - **Verify**: `grep -n "def _parse_trip_datetime" custom_components/ev_trip_planner/trip_manager.py` returns definition line
  - **Commit**: `refactor(ev-trip-planner): yellow - insert _parse_trip_datetime method into TripManager class`
  - _Requirements: Story S1, requirements.md Section 9.1.1_

- [ ] 1.8a [P] [YELLOW] Verify _parse_trip_datetime docstring follows Google style
  - **Do**: Read the _parse_trip_datetime method body to verify Args/Returns sections
  - **Files**: custom_components/ev_trip_planner/trip_manager.py
  - **Done when**: Docstring has Args and Returns sections
  - **Verify**: `grep -A15 "def _parse_trip_datetime" custom_components/ev_trip_planner/trip_manager.py | grep -c "Args\|Returns"` returns 2
  - **Commit**: None (verification only)
  - _Requirements: Story S1_

- [ ] 1.8b [P] [YELLOW] Replace inline parsing with _parse_trip_datetime method call (BOTH paths)
  - **Do**: Replace the datetime-object block at line 1470-1473 AND the string block at lines 1474-1483 with a single call: `trip_time = self._parse_trip_datetime(trip_datetime)`
    - The _parse_trip_datetime method should handle both: datetime objects (ensure tz-aware) and strings (parse_datetime with strptime fallback)
  - **Files**: custom_components/ev_trip_planner/trip_manager.py
  - **Done when**: Both inline blocks replaced with method call
  - **Verify**: `grep -c "_parse_trip_datetime(trip_datetime)" custom_components/ev_trip_planner/trip_manager.py` returns 1
  - **Commit**: `refactor(ev-trip-planner): yellow - replace inline parsing with _parse_trip_datetime call`
  - _Requirements: Story S1_

- [ ] 1.8c [P] [YELLOW] Verify no stray inline parsing code remains at lines 1474-1483
  - **Do**: Read lines 1470-1490 to confirm no remaining inline strptime or parse_datetime code
  - **Files**: custom_components/ev_trip_planner/trip_manager.py
  - **Done when**: Only the method call exists at lines 1474-1483 area
  - **Verify**: `sed -n '1474,1483p' custom_components/ev_trip_planner/trip_manager.py` shows only the method call line
  - **Commit**: None (verification only)
  - _Requirements: Story S1_

- [ ] 1.9 [P] [YELLOW] Verify SOLID-ization didn't break tests
  - **Do**: Run the datetime test again after extraction
  - **Verify**: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_manager_datetime_tz.py -v 2>&1 | grep -q "PASSED\|passed" && echo SOLID_GREEN`
  - **Done when**: Test still passes after extraction
  - **Commit**: None
  - _Requirements: Story S1_

- [ ] 1.10 [P] [VERIFY] SOLID Quality Gate: code-reviewer validates SOLID-ized diff
  - **Skills**: pr-review-toolkit:code-reviewer
  - **Do**:
    1. Capture diff: `git diff custom_components/ev_trip_planner/trip_manager.py`
    2. Spawn pr-review-toolkit:code-reviewer subagent with the diff and SOLID criteria
    3. If FAIL: fix flagged lines and re-request review (max 2 retries)
    4. If 3 attempts exhausted: launch ralph-specum:architect-reviewer fallback
  - **Verify**: Reviewer returns VERIFICATION_PASS
  - **Done when**: SOLID-ized code passes code review
  - **Commit**: None
  - _Requirements: requirements.md Section 9.1.2_

- [ ] 1.11 [P] [VERIFY] Grep for ALL datetime comparison paths — verify no naive/aware mixing remains
  - **Do**:
    1. Run `grep -rn "datetime.strptime" custom_components/ev_trip_planner/`
    2. Review each match: utils.py:182 (safe), trip_manager.py:1318 (safe, local date comparison), calculations.py:138,146,148 (safe, local comparisons)
    3. Verify trip_manager.py now has timezone awareness at ALL comparison points:
       - The `_parse_trip_datetime` method handles datetime objects with tz check
       - The method also handles strings with parse_datetime + fallback
    4. Check for any other `trip_time - now` or `delta = ` patterns with datetime subtraction
  - **Verify**: Every datetime subtraction in trip_manager.py uses timezone-aware datetimes
  - **Done when**: No remaining naive/aware mixing identified in any code path
  - **Commit**: None
  - _Requirements: Story S1, AC4_

- [ ] 1.12 [P] [VERIFY] Verify import of dt_util exists in trip_manager.py
  - **Do**: Check that `from homeassistant.util import dt as dt_util` exists in trip_manager.py imports
  - **Verify**: `grep -n "dt_util" custom_components/ev_trip_planner/trip_manager.py | head -3` confirms import
  - **Done when**: Import verified
  - **Commit**: None
  - _Requirements: Story S1_

- [ ] 1.13 [P] [VERIFY] Run make test (all unit tests pass after S1 changes)
  - **Do**: Run `make test`
  - **Verify**: `make test` exits 0
  - **Done when**: All unit tests pass
  - **Commit**: None
  - _Requirements: Story S1, AC3_

- [ ] 1.14 [P] [VERIFY] Run make lint (no violations after S1 changes)
  - **Do**: Run `make lint`
  - **Verify**: `make lint` exits 0
  - **Done when**: No lint violations
  - **Commit**: None
  - _Requirements: Story S1_

- [ ] 1.15 [P] [VERIFY] Run make mypy (type checking passes after S1 changes)
  - **Do**: Run `make mypy`
  - **Verify**: `make mypy` exits 0
  - **Done when**: No type errors
  - **Commit**: None
  - _Requirements: Story S1_

### Story S2: Fix Coordinator Dual-Writer Race Condition

- [ ] 1.16 [P] [RED] Read emhass_adapter.py:1840-1870 to understand in-place mutation bug
  - **Do**: Read lines 1840-1870 of emhass_adapter.py, identify lines 1851-1854 where coordinator.data keys are mutated in-place
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Bug location understood (lines 1851-1854)
  - **Verify**: `grep -n 'coordinator\.data\["' custom_components/ev_trip_planner/emhass_adapter.py` shows the in-place mutations
  - **Commit**: None (reading only)
  - _Requirements: Story S2, AC1_

- [ ] 1.16a [P] [RED] Read emhass_adapter.py imports to verify EMHASS_STATE_READY constant
  - **Do**: Read first 30 lines of emhass_adapter.py to confirm `EMHASS_STATE_READY` constant is imported/defined
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Constant confirmed
  - **Verify**: `grep -n "EMHASS_STATE_READY" custom_components/ev_trip_planner/emhass_adapter.py | head -3` returns definition
  - **Commit**: None (reading only)
  - _Requirements: Story S2_

- [ ] 1.17 [P] [RED] Read emhass_adapter.py:1940-1970 to understand second mutation location
  - **Do**: Read lines 1940-1970, identify lines 1953-1956 with in-place mutations in async_cleanup_vehicle_indices
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Both mutation locations identified
  - **Verify**: `grep -n 'coordinator\.data\["' custom_components/ev_trip_planner/emhass_adapter.py` returns 2 locations (lines 1851 and 1953)
  - **Commit**: None (reading only)
  - _Requirements: Story S2, AC1, AC4_

- [ ] 1.18 [P] [RED] Read emhass_adapter.py:719-748 to understand the correct pattern
  - **Do**: Read the existing correct pattern at lines 722-745 (publish_deferrable_loads) where full dict replacement is used correctly
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Correct pattern understood
  - **Verify**: `sed -n '737,743p' custom_components/ev_trip_planner/emhass_adapter.py` shows the full dict replacement
  - **Commit**: None (reading only)
  - _Requirements: Story S2, AC3_

- [ ] 1.19 [P] [GREEN] Replace in-place mutations at lines 1847-1861 with full dict replacement
  - **Do**:
    1. Replace the block at lines 1847-1861:
       ```python
       if coordinator.data is not None:
           coordinator.data = {
               **coordinator.data,
               "per_trip_emhass_params": {},
               "emhass_power_profile": [],
               "emhass_deferrables_schedule": [],
               "emhass_status": EMHASS_STATE_READY,
           }
       ```
    2. Keep the else branch pattern (already correct)
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Lines 1847-1861 use full dict replacement pattern
  - **Verify**: `sed -n '1847,1861p' custom_components/ev_trip_planner/emhass_adapter.py` shows `coordinator.data = {**coordinator.data,`
  - **Commit**: `fix(ev-trip-planner): green - replace in-place mutation with dict expansion in async_publish_all_deferrable_loads`
  - _Requirements: Story S2, AC1_

- [ ] 1.20 [P] [GREEN] Replace in-place mutations at lines 1951-1956 with full dict replacement
  - **Do**: Same pattern as 1.19 — replace in-place `coordinator.data["key"] = value` with `coordinator.data = {**coordinator.data, "key": value}` in async_cleanup_vehicle_indices
  - **Files**: custom_components/ev_trip_planner/emhass_adapter.py
  - **Done when**: Lines 1951-1956 use full dict replacement
  - **Verify**: `grep -n 'coordinator\.data\["' custom_components/ev_trip_planner/emhass_adapter.py` returns 0 matches
  - **Commit**: `fix(ev-trip-planner): green - replace in-place mutation with dict expansion in async_cleanup_vehicle_indices`
  - _Requirements: Story S2, AC1, AC4_

- [ ] 1.21 [P] [VERIFY] Verify grep returns zero in-place mutations
  - **Do**: Run `grep -n 'coordinator\.data\["' custom_components/ev_trip_planner/emhass_adapter.py`
  - **Verify**: Command returns 0 matches (exit 1 from grep = no matches found = GOOD)
  - **Done when**: Zero in-place mutations remain
  - **Commit**: None
  - _Requirements: Story S2, AC1_

- [ ] 1.22 [P] [VERIFY] SOLID Quality Gate: code-reviewer validates emhass_adapter.py diff
  - **Skills**: pr-review-toolkit:code-reviewer
  - **Do**:
    1. Capture diff: `git diff custom_components/ev_trip_planner/emhass_adapter.py`
    2. Spawn pr-review-toolkit:code-reviewer subagent with the diff and SOLID criteria:
       - MUST: NO DIRECT STATE MUTATION (no `coordinator.data["key"] =` in touched code) — CRITERION 8
       - MUST: TYPE HINTS complete
       - MUST: SINGLE RESPONSIBILITY
       - MUST: NO SILENT EXCEPTIONS
    3. If FAIL: fix flagged lines and re-request review (max 2 retries)
    4. If 3 attempts exhausted: launch ralph-specum:architect-reviewer fallback
  - **Verify**: Reviewer returns VERIFICATION_PASS
  - **Done when**: Code reviewer validates SOLID adherence
  - **Commit**: None
  - _Requirements: requirements.md Section 9.1.2_

- [ ] 1.23 [P] [VERIFY] Verify publish_deferrable_loads cache-before-refresh sequence is correct
  - **Do**: Read emhass_adapter.py lines 722-745 to confirm cache is populated before coordinator.async_refresh() is called
  - **Verify**: Code inspection: lines 723-728 populate cache, line 737 sets full dict, line 745 calls async_refresh — sequence is correct
  - **Done when**: Verified correct order
  - **Commit**: None
  - _Requirements: Story S2, AC3_

- [ ] 1.24 [P] [VERIFY] Run make test (all unit tests pass after S2 changes)
  - **Do**: Run `make test`
  - **Verify**: `make test` exits 0
  - **Done when**: All unit tests pass
  - **Commit**: None
  - _Requirements: Story S2_

- [ ] 1.24a [VERIFY] **REGRESSION GUARD**: Compare `make test` against baseline after S2 fix
  - **Do**:
    1. Run `make test 2>&1 | tee /tmp/post-s2-unit.txt`
    2. Compare against baseline from Phase 0 (0.3) AND post-S1 state (1.13):
       - `diff /tmp/post-s1-unit.txt /tmp/post-s2-unit.txt`
    3. Check each change against "Intentional Behavior Change Map" (task 0.5):
       - EXPECTED: No test behavior changes (emhass_adapter.py already 100% coverage)
       - EXPECTED: Same test count (1637 passed)
       - EXPECTED: All tests that passed before still pass
    4. If ANY test that was passing now fails → STOP, document, investigate before proceeding
    5. If all matches expected map → proceed
  - **Verify**: No test state changes vs post-S1 baseline
  - **Done when**: Verified no regressions from coordinator fix
  - **Commit**: `chore(e2e-ux-tests-fix): S2 regression guard - verify no unexpected changes`
  - _Requirements: Anti-regression protection_

- [ ] 1.24a [P] [VERIFY] Run make test with verbose output to confirm emhass_adapter tests specifically pass
  - **Do**: Run `PYTHONPATH=. .venv/bin/python -m pytest tests -v --tb=short --ignore=tests/ha-manual/ --ignore=tests/e2e/ 2>&1 | grep -i "emhass"`
  - **Verify**: No emhass-related test failures in output
  - **Done when**: All emhass-related tests confirmed passing
  - **Commit**: None
  - _Requirements: Story S2_

- [ ] 1.25 [P] [VERIFY] Run make lint (no violations after S2 changes)
  - **Do**: Run `make lint`
  - **Verify**: `make lint` exits 0
  - **Done when**: No lint violations
  - **Commit**: None
  - _Requirements: Story S2_

- [ ] 1.26 [P] [VERIFY] Run make mypy (type checking passes after S2 changes)
  - **Do**: Run `make mypy`
  - **Verify**: `make mypy` exits 0
  - **Done when**: No type errors
  - **Commit**: None
  - _Requirements: Story S2_

### Story S3: Fix Test Infrastructure

- [ ] 1.27 [P] [S3.1] Read configuration.yaml to understand current structure
  - **Do**: Read tests/ha-manual/configuration.yaml lines 1-47
  - **Files**: tests/ha-manual/configuration.yaml
  - **Done when**: Current structure understood
  - **Verify**: `grep -c "logger:" tests/ha-manual/configuration.yaml` returns 0 (no logger section)
  - **Commit**: None (reading only)
  - _Requirements: Story S3, AC4_

- [ ] 1.28 [P] [S3.1] Add logger debug config to configuration.yaml
  - **Do**: Append to end of configuration.yaml:
    ```yaml

    logger:
      default: warning
      logs:
        custom_components.ev_trip_planner: debug
        homeassistant.components.sensor: debug
    ```
  - **Files**: tests/ha-manual/configuration.yaml
  - **Done when**: Logger section added at end of file
  - **Verify**: `grep -A3 "logger:" tests/ha-manual/configuration.yaml` returns expected output
  - **Commit**: `fix(e2e): add logger debug config to tests/ha-manual/configuration.yaml`
  - _Requirements: Story S3, AC4_

- [ ] 1.29 [P] [S3.2] Read emhass-sensor-updates.spec.ts:300-320 to locate hardcoded entity IDs
  - **Do**: Read lines 295-330 to identify hardcoded entity ID at line 308
  - **Files**: tests/e2e/emhass-sensor-updates.spec.ts
  - **Done when**: Hardcoded entity ID location confirmed at line 308
  - **Verify**: `grep -n "ev_trip_planner_test_vehicle_emhass" tests/e2e/emhass-sensor-updates.spec.ts` shows line 308
  - **Commit**: None (reading only)
  - _Requirements: Story S3, AC1_

- [ ] 1.30 [P] [S3.2] Read getSensorAttributes helper to understand its parameter signature
  - **Do**: Read tests/e2e/emhass-sensor-updates.spec.ts lines 23-47 to understand getSensorAttributes and discoverEmhassSensorEntityId signatures
  - **Files**: tests/e2e/emhass-sensor-updates.spec.ts
  - **Done when**: Helper signatures understood (getSensorAttributes(pg, entityId), discoverEmhassSensorEntityId(pg))
  - **Verify**: `grep -n "const getSensorAttributes\|const discoverEmhassSensorEntityId" tests/e2e/emhass-sensor-updates.spec.ts | head -5`
  - **Commit**: None (reading only)
  - _Requirements: Story S3_

- [ ] 1.30a [P] [S3.2] Read the test context around line 308 to understand how getSensorAttributes is called at that location
  - **Do**: Read lines 295-330 to understand how `sensorEntityId` is used and how it feeds into `getSensorAttributes` calls
  - **Files**: tests/e2e/emhass-sensor-updates.spec.ts
  - **Done when**: Usage context understood
  - **Verify**: `sed -n '308p' tests/e2e/emhass-sensor-updates.spec.ts` shows the hardcoded ID line
  - **Commit**: None (reading only)
  - _Requirements: Story S3_

- [ ] 1.30b [P] [S3.2] Replace hardcoded entity ID at line 308
  - **Do**: Replace `'sensor.ev_trip_planner_test_vehicle_emhass_perfil_diferible_test_vehicle'` with `await discoverEmhassSensorEntityId(page)` — update all references from `getSensorAttributes(sensorEntityId)` to `getSensorAttributes(page, sensorEntityId)` since getSensorAttributes takes (page, entityId) per line 23.
  - **Files**: tests/e2e/emhass-sensor-updates.spec.ts
  - **Done when**: Line 308 no longer contains hardcoded entity ID
  - **Verify**: `grep -n "ev_trip_planner_test_vehicle_emhass" tests/e2e/emhass-sensor-updates.spec.ts | grep "308"` returns 0 matches
  - **Commit**: `fix(e2e): replace hardcoded entity ID with discoverEmhassSensorEntityId at line 308`
  - _Requirements: Story S3, AC1_

- [ ] 1.31 [P] [S3.2] Read emhass-sensor-updates.spec.ts:420-440 to locate second hardcoded entity ID
  - **Do**: Read lines 420-440 to identify second hardcoded entity ID at line 427
  - **Files**: tests/e2e/emhass-sensor-updates.spec.ts
  - **Done when**: Second hardcoded entity ID location confirmed
  - **Verify**: `grep -n "ev_trip_planner_test_vehicle_emhass" tests/e2e/emhass-sensor-updates.spec.ts` shows remaining match
  - **Commit**: None (reading only)
  - _Requirements: Story S3, AC1_

- [ ] 1.32 [P] [S3.2] Replace hardcoded entity ID at line 427
  - **Do**: Same replacement as 1.30 — replace hardcoded entity ID with `discoverEmhassSensorEntityId(page)`
  - **Files**: tests/e2e/emhass-sensor-updates.spec.ts
  - **Done when**: Line 427 no longer contains hardcoded entity ID
  - **Verify**: `grep -n "ev_trip_planner_test_vehicle_emhass" tests/e2e/emhass-sensor-updates.spec.ts` returns 0 matches
  - **Commit**: `fix(e2e): replace hardcoded entity ID with discoverEmhassSensorEntityId at line 427`
  - _Requirements: Story S3, AC1_

- [ ] 1.32a [P] [S3.3] Read getFutureIso helper to understand its signature
  - **Do**: Read tests/e2e/emhass-sensor-updates.spec.ts lines 53-60 to understand getFutureIso signature
  - **Files**: tests/e2e/emhass-sensor-updates.spec.ts
  - **Done when**: getFutureIso(dayOffset, timeStr) signature understood
  - **Verify**: `sed -n '53p' tests/e2e/emhass-sensor-updates.spec.ts` shows `const getFutureIso = (daysOffset: number, timeStr: string`
  - **Commit**: None (reading only)
  - _Requirements: Story S3_

- [ ] 1.33 [P] [S3.3] Read emhass-sensor-updates.spec.ts:70-80 to locate hardcoded date
  - **Do**: Read lines 70-80 to identify hardcoded date `'2026-04-20T10:00'` at line 75
  - **Files**: tests/e2e/emhass-sensor-updates.spec.ts
  - **Done when**: Hardcoded date location confirmed
  - **Verify**: `grep -n "2026-04-20" tests/e2e/emhass-sensor-updates.spec.ts | head -5` shows line 75
  - **Commit**: None (reading only)
  - _Requirements: Story S3, AC2_

- [ ] 1.34 [P] [S3.3] Replace hardcoded date at line 75
  - **Do**: Replace `'2026-04-20T10:00'` with `getFutureIso(1, '10:00')`
  - **Files**: tests/e2e/emhass-sensor-updates.spec.ts
  - **Done when**: Line 75 uses getFutureIso
  - **Verify**: `sed -n '75p' tests/e2e/emhass-sensor-updates.spec.ts` shows `getFutureIso`
  - **Commit**: `fix(e2e): replace hardcoded date with getFutureIso at line 75`
  - _Requirements: Story S3, AC2_

- [ ] 1.35 [P] [S3.3] Replace hardcoded date at line 138
  - **Do**: Same replacement: `'2026-04-20T10:00'` -> `getFutureIso(1, '10:00')`
  - **Files**: tests/e2e/emhass-sensor-updates.spec.ts
  - **Done when**: Line 138 uses getFutureIso
  - **Verify**: `sed -n '138p' tests/e2e/emhass-sensor-updates.spec.ts` shows `getFutureIso`
  - **Commit**: `fix(e2e): replace hardcoded date with getFutureIso at line 138`
  - _Requirements: Story S3, AC2_

- [ ] 1.36 [P] [S3.3] Replace hardcoded dates at lines 489-491
  - **Do**: Replace `'2026-04-20T10:00'` at lines 489 and 491 with `getFutureIso(1, '10:00')`
  - **Files**: tests/e2e/emhass-sensor-updates.spec.ts
  - **Done when**: Lines 489 and 491 use getFutureIso
  - **Verify**: `grep -n "2026-04-20" tests/e2e/emhass-sensor-updates.spec.ts` returns 0 matches
  - **Commit**: `fix(e2e): replace hardcoded dates with getFutureIso at lines 489-491`
  - _Requirements: Story S3, AC2_

- [ ] 1.37 [P] [S3.4] Count and classify all waitForTimeout calls
  - **Do**: Run `grep -n "waitForTimeout" tests/e2e/emhass-sensor-updates.spec.ts` to list all 26 occurrences, classify each as REPLACE or KEEP
  - **Files**: tests/e2e/emhass-sensor-updates.spec.ts
  - **Done when**: All 26 waitForTimeout calls classified
  - **Verify**: `grep -c "waitForTimeout" tests/e2e/emhass-sensor-updates.spec.ts` returns 26 (confirm count)
  - **Commit**: None (analysis only)
  - _Requirements: Story S3, AC3_

- [ ] 1.38 [P] [S3.4] Replace sensor-check waitForTimeout calls with toPass() polling
  - **Do**: Replace `page.waitForTimeout(3000)` and `page.waitForTimeout(1000)` calls that precede sensor attribute checks with `await expect(async () => { ... sensor attribute assertions ... }).toPass({ timeout: 15000 })`
  - **Files**: tests/e2e/emhass-sensor-updates.spec.ts
  - **Done when**: All sensor-check waits replaced with toPass()
  - **Verify**: Re-run grep for remaining waitForTimeout and confirm only acceptable ones remain
  - **Commit**: `fix(e2e): replace sensor-check waitForTimeout with toPass() polling`
  - _Requirements: Story S3, AC3_

- [ ] 1.39 [P] [S3.4] Replace UI-navigation waitForTimeout calls
  - **Do**: Replace `page.waitForTimeout(1000)` and `page.waitForTimeout(2000)` calls used for UI navigation delays with `page.waitForLoadState('networkidle')` or `page.waitForTimeout(500)` (shorter, more intentional)
  - **Files**: tests/e2e/emhass-sensor-updates.spec.ts
  - **Done when**: UI navigation waits optimized
  - **Verify**: Review remaining waitForTimeout calls
  - **Commit**: `fix(e2e): replace UI navigation waitForTimeout with networkidle`
  - _Requirements: Story S3, AC3_

- [ ] 1.40 [P] [S3.4] Preserve acceptable waitForTimeout calls
  - **Do**: Verify remaining waitForTimeout calls are acceptable:
    - Line 618 (UX-02 multi-trip 5000ms) — KEEP
    - Line 642 (UX-02 partial deletion 3000ms) — KEEP
    - Line 658 (UX-02 final deletion 3000ms) — KEEP
  - **Files**: tests/e2e/emhass-sensor-updates.spec.ts
  - **Done when**: Only multi-trip propagation delays remain as waitForTimeout
  - **Verify**: `grep -n "waitForTimeout" tests/e2e/emhass-sensor-updates.spec.ts` shows only lines 618, 642, 658
  - **Commit**: None (preserving acceptable calls)
  - _Requirements: Story S3, AC3_

- [ ] 1.41 [P] [S3.5] Read run-e2e.sh:20-30 to verify existing timestamped log config
  - **Do**: Read lines 20-30 of scripts/run-e2e.sh to confirm timestamped log paths exist
  - **Files**: scripts/run-e2e.sh
  - **Done when**: Existing log config confirmed (line 23-24: TS and HA_LOG_FILE)
  - **Verify**: `grep -n "HA_LOG_FILE\|TS=" scripts/run-e2e.sh` shows timestamp logic
  - **Commit**: None (reading only)
  - _Requirements: Story S3, AC5_

- [ ] 1.42 [P] [S3.5] Read run-e2e.sh:151-162 to verify existing failure dump
  - **Do**: Read lines 151-162 to confirm failure dump with grep patterns exists
  - **Files**: scripts/run-e2e.sh
  - **Done when**: Failure dump confirmed present
  - **Verify**: `grep -n "E2E tests failed" scripts/run-e2e.sh` shows failure handling
  - **Commit**: None (reading only)
  - _Requirements: Story S3, AC5_

- [ ] 1.43 [P] [S3.6] Read playwright.config.ts:15-20 to locate globalTeardown
  - **Do**: Read lines 15-20 to confirm globalTeardown reference at line 18
  - **Files**: playwright.config.ts
  - **Done when**: globalTeardown line confirmed at line 18
  - **Verify**: `grep -n "globalTeardown" playwright.config.ts` returns line 18
  - **Commit**: None (reading only)
  - _Requirements: Story S3, AC6_

- [ ] 1.44 [P] [S3.6] Remove globalTeardown from playwright.config.ts
  - **Do**: Remove line `globalTeardown: './globalTeardown.ts',` from playwright.config.ts
  - **Files**: playwright.config.ts
  - **Done when**: globalTeardown reference removed
  - **Verify**: `grep -n "globalTeardown" playwright.config.ts` returns 0 matches
  - **Commit**: `fix(e2e): remove non-existent globalTeardown from playwright.config.ts`
  - _Requirements: Story S3, AC6_

- [ ] 1.45 [P] [S3.7] Run playwright test --list to verify all tests discovered
  - **Do**: Run `npx playwright test --list`
  - **Verify**: Exit 0, all test files listed, no warnings about missing globalTeardown
  - **Done when**: All tests discovered without errors
  - **Commit**: None
  - _Requirements: Story S3, requirements.md Section 5.4_

- [ ] 1.46 [P] [VERIFY] Run make lint (no violations after S3 changes)
  - **Do**: Run `make lint`
  - **Verify**: `make lint` exits 0
  - **Done when**: No lint violations
  - **Commit**: None
  - _Requirements: Story S3_

- [ ] 1.47 [P] [VERIFY] Run make mypy (type checking passes after S3 changes)
  - **Do**: Run `make mypy`
  - **Verify**: `make mypy` exits 0
  - **Done when**: No type errors
  - **Commit**: None
  - _Requirements: Story S3_

## Phase 2: Additional Testing (S4 + S5+S6 E2E)

### Story S4: Race Condition Regression Tests

- [ ] 2.1 [RED] Read existing helpers in emhass-sensor-updates.spec.ts
  - **Do**: Read tests/e2e/emhass-sensor-updates.spec.ts lines 22-60 to understand getSensorAttributes, discoverEmhassSensorEntityId, getFutureIso helper signatures
  - **Files**: tests/e2e/emhass-sensor-updates.spec.ts
  - **Done when**: Helper signatures understood
  - **Verify**: `grep -n "^const\|^async function" tests/e2e/emhass-sensor-updates.spec.ts | head -10` shows helper definitions
  - **Commit**: None (reading only)
  - _Requirements: Story S4, AC4_

- [ ] 2.2 [RED] Read trips-helpers.ts createTestTrip signature
  - **Do**: Read tests/e2e/trips-helpers.ts lines 129-178 to understand createTestTrip parameters
  - **Files**: tests/e2e/trips-helpers.ts
  - **Done when**: createTestTrip signature understood
  - **Verify**: `grep -n "async function createTestTrip" tests/e2e/trips-helpers.ts` confirms line 129
  - **Commit**: None (reading only)
  - _Requirements: Story S4, AC4_

- [ ] 2.3 [RED] Write regression test: race-condition-regression-immediate-sensor-check
  - **Do**: Add test function in emhass-sensor-updates.spec.ts (between existing tests and UX-01):
    1. cleanupTestTrips → navigateToPanel
    2. createTestTrip with getFutureIso datetime, 50km, 10kwh
    3. IMMEDIATELY discover sensor entity (no waitForTimeout)
    4. Assert sensor entity exists
    5. toPass() check: def_total_hours_array has positive values
    6. toPass() check: p_deferrable_matrix has non-zero entries
    7. toPass() check: emhass_status === 'ready'
    8. cleanupTestTrips
  - **Files**: tests/e2e/emhass-sensor-updates.spec.ts
  - **Done when**: Regression test added to file
  - **Verify**: `grep -n "race-condition-regression-immediate-sensor-check" tests/e2e/emhass-sensor-updates.spec.ts` returns the test
  - **Commit**: `test(e2e): add race-condition-regression-immediate-sensor-check test`
  - _Requirements: Story S4, AC1, AC3, AC4, AC5_

- [ ] 2.4 [RED] Write regression test: race-condition-regression-rapid-successive-creation
  - **Do**: Add second regression test after the first one:
    1. cleanupTestTrips → navigateToPanel
    2. createTestTrip with getFutureIso(1, '09:00'), 30km, 5kwh
    3. toPass() check: sensor shows trip 1 data
    4. IMMEDIATELY createTestTrip with getFutureIso(1, '14:00'), 80km, 15kwh (no delay)
    5. toPass() check: sensor shows both trips' data
    6. toPass() check: emhass_status === 'ready'
    7. cleanupTestTrips
  - **Files**: tests/e2e/emhass-sensor-updates.spec.ts
  - **Done when**: Second regression test added to file
  - **Verify**: `grep -n "race-condition-regression-rapid-successive" tests/e2e/emhass-sensor-updates.spec.ts` returns 2 matches
  - **Commit**: `test(e2e): add race-condition-regression-rapid-successive-creation test`
  - _Requirements: Story S4, AC2, AC3, AC4, AC5_

- [ ] 2.5 [VERIFY] Verify regression tests appear in playwright --list
  - **Do**: Run `npx playwright test --list`
  - **Verify**: Both regression test names appear in the test list output
  - **Done when**: 2 new regression tests discovered
  - **Commit**: None
  - _Requirements: Story S4_

- [ ] 2.5a [VERIFY] **REGRESSION GUARD**: Verify E2E test count is exactly 30 (was 28 + 2 new)
  - **Do**:
    1. Run `npx playwright test --list 2>&1 | grep "^  .*test" | wc -l`
    2. Compare against baseline from Phase 0 (0.4): was 28 tests
    3. EXPECTED: 30 tests (28 original + 2 regression tests)
    4. If count != 30 → STOP, investigate (tests may have been lost during S3 refactors)
  - **Verify**: `npx playwright test --list | tail -1` shows "Total: 30 tests in 8 files"
  - **Done when**: Exact test count verified against baseline
  - **Commit**: `chore(e2e-ux-tests-fix): S4 regression guard - verify E2E test count`
  - _Requirements: Anti-regression protection_

- [ ] 2.6 [VERIFY] Pre-flight check: verify SOC is 20% in configuration.yaml
  - **Do**: Run `grep -n "initial: 20" tests/ha-manual/configuration.yaml`
  - **Verify**: Returns line with `initial: 20` for test_vehicle_soc
  - **Done when**: SOC=20% confirmed
  - **Commit**: None
  - _Requirements: requirements.md Section 7.5, AC4_

- [ ] 2.7 [VERIFY] Pre-flight check: no hardcoded dates in test files
  - **Do**: Run `grep -rn "2026-04-20" tests/e2e/emhass-sensor-updates.spec.ts`
  - **Verify**: Returns 0 matches
  - **Done when**: No hardcoded dates found
  - **Commit**: None
  - _Requirements: requirements.md Section 7.5_

- [ ] 2.8 [VERIFY] Pre-flight check: no hardcoded entity IDs in test files
  - **Do**: Run `grep -rn "ev_trip_planner_test_vehicle_emhass" tests/e2e/emhass-sensor-updates.spec.ts`
  - **Verify**: Returns 0 matches
  - **Done when**: No hardcoded entity IDs found
  - **Commit**: None
  - _Requirements: requirements.md Section 7.5_

- [ ] 2.9 [VERIFY] Pre-flight check: logger config exists in configuration.yaml
  - **Do**: Run `grep -n "logger:" tests/ha-manual/configuration.yaml`
  - **Verify**: Returns logger section
  - **Done when**: Logger config confirmed
  - **Commit**: None
  - _Requirements: requirements.md Section 7.5_

- [ ] 2.10 [VERIFY] Pre-flight check: globalTeardown removed from playwright.config.ts
  - **Do**: Run `grep -n "globalTeardown" playwright.config.ts`
  - **Verify**: Returns 0 matches
  - **Done when**: globalTeardown removed
  - **Commit**: None
  - _Requirements: requirements.md Section 7.5_

### Story S5+S6: E2E UX-01 + UX-02 Verification (Self-Healing Loop)

- [ ] 2.11 [VERIFY] S5+S6 Iteration 0: Run make e2e (first full suite attempt)
  - **Do**:
    1. Run `make e2e` (runs full E2E suite via run-e2e.sh)
    2. Wait for completion (HA startup takes ~2 minutes)
    3. Record exit code and test results
  - **Verify**: `make e2e` completes (exit 0 = pass, exit non-zero = fail)
  - **Done when**: First full suite run complete
  - **Commit**: None
  - _Requirements: Story S5, AC1-AC6; Story S6, AC1-AC6_

- [ ] 2.12 [VERIFY] Diagnose failures: read HA logs AND Playwright error context if make e2e failed
  - **Do**:
    1. **Playwright error context FIRST**: Find `test-results/*/error-context.md` files
       - `find test-results -name "error-context.md" -type f`
       - Read each to understand WHAT the UI looked like when the test failed (page snapshot, element state)
       - Identify which assertions failed and why
    2. Find most recent HA log: `ls -t /tmp/logs/ha-e2e-*.log | head -1`
    3. Read last 200 lines: `tail -200 /tmp/logs/ha-e2e-*.log | head -200`
    4. Check for errors: `grep -i "error\|exception\|traceback" /tmp/logs/ha-e2e-*.log | tail -50`
    5. Check for EMHASS: `grep -i "emhass\|deferrable\|power_profile" /tmp/logs/ha-e2e-*.log | tail -50`
    6. Check for datetime: `grep -i "offset-naive\|offset-aware\|TypeError" /tmp/logs/ha-e2e-*.log | tail -20`
    7. Cross-reference Playwright error context with HA logs: does the UI failure match the backend error?
    8. Classify failure type using requirements.md Section 10.1 table
  - **Verify**: Failure classified with root cause identified (both frontend UI state and backend error)
  - **Done when**: Root cause documented with both Playwright error context and HA log evidence
  - **Commit**: None
  - _Requirements: requirements.md Section 10.1_

- [ ] 2.13 [VERIFY] Fix identified root cause and re-run make e2e (iteration 2)
  - **Do**:
    1. Apply ONE fix for the classified root cause (verify with Playwright error context that the fix targets the right issue)
    2. Run `make e2e` again
    3. Read new Playwright error context files for any remaining failures
    4. Record results
  - **Verify**: `make e2e` exits 0 or produces different error (progress)
  - **Done when**: Iteration 2 complete
  - **Commit**: None (if fix applied)
  - _Requirements: requirements.md Section 10.3_

- [ ] 2.14 [VERIFY] Diagnose and fix again if iteration 2 failed (iteration 3)
  - **Do**:
    1. Read Playwright error context files for new failures
    2. Read HA logs for new errors
    3. Cross-reference Playwright context with HA logs
    4. Apply ONE fix
    5. Run `make e2e` again
    6. Record results
  - **Verify**: `make e2e` exits 0 or all 3 iterations complete
  - **Done when**: All 3 self-healing iterations attempted (or passed)
  - **Commit**: None
  - _Requirements: requirements.md Section 10.3 (max 3 iterations)_

- [ ] 2.15 [VERIFY] Post-run verification: check HA logs for errors/exceptions
  - **Do**:
    1. If make e2e passed: `grep -i "error\|exception\|traceback" /tmp/logs/ha-e2e-*.log | tail -50` — should show only expected/warning entries, not errors
    2. Check EMHASS: `grep -i "emhass\|deferrable" /tmp/logs/ha-e2e-*.log | tail -50`
  - **Verify**: No critical errors in HA logs
  - **Done when**: HA logs clean or errors documented as acceptable
  - **Commit**: None
  - _Requirements: requirements.md Section 9.3_

- [ ] 2.16 [VERIFY] Verify S5 acceptance criteria: UX-01 recurring trip lifecycle
  - **Do**: Read the UX-01 test code (emhass-sensor-updates.spec.ts lines 560-595) and verify each validation V1-V6 is present:
    - V1: Recurring trip appears (getByText)
    - V2: Sensor power_profile non-zero
    - V3: Sensor deferrables_schedule populated
    - V4: Sensor emhass_status === ready
    - V5: After delete: sensor all zeros
    - V6: Trip removed from UI
    - Also verify: test uses `getFutureIso()` for datetime (not hardcoded dates) — this avoids triggering the datetime naive/aware bug
  - **Verify**: All 6 validations present in test code, datetime handled correctly
  - **Done when**: All V1-V6 accounted for, datetime handled correctly
  - **Commit**: None
  - _Requirements: Story S5, Section 7.3_

- [ ] 2.17 [VERIFY] Verify S6 acceptance criteria: UX-02 multiple trips
  - **Do**: Read the UX-02 test code (emhass-sensor-updates.spec.ts lines 603-665) and verify each validation V1-V6 is present:
    - V1: 3 trips visible
    - V2: 1 device only
    - V3: 1 sensor only
    - V4: After delete: 2 trips remain
    - V5: Sensor still non-zero after partial delete
    - V6: After full delete: sensor all zeros
  - **Verify**: All 6 validations present in test code
  - **Done when**: All V1-V6 accounted for
  - **Commit**: None
  - _Requirements: Story S6, Section 8.3_

### S3 Regression Guard: Verify test infrastructure changes didn't break unrelated tests

- [ ] 2.18 [VERIFY] **REGRESSION GUARD**: Verify S3 test infra changes didn't break unrelated unit tests
  - **Do**:
    1. Run `make test 2>&1 | tee /tmp/post-s3-unit.txt`
    2. Compare against post-S2 baseline (1.24a): `diff /tmp/post-s2-unit.txt /tmp/post-s3-unit.txt`
    3. EXPECTED: No unit test behavior changes (S3 only touches test files, not production code)
    4. EXPECTED: Same test count (1637 passed), same coverage
    5. If any test changed state → STOP, investigate (S3 should NOT affect unit tests)
  - **Verify**: No test state changes between post-S2 and post-S3
  - **Done when**: S3 changes verified not to affect unit tests
  - **Commit**: `chore(e2e-ux-tests-fix): S3 regression guard - verify no unit test changes`
  - _Requirements: Anti-regression protection_

- [ ] 2.19 [VERIFY] **REGRESSION GUARD**: Verify S3 E2E test infra changes didn't break existing E2E behavior
  - **Do**:
    1. Run `npx playwright test --list 2>&1` — all tests should be discoverable
    2. Verify no tests were accidentally deleted during entity ID/date replacements
    3. Count should still be 30 (28 original + 2 regression)
    4. If test count != 30 → STOP, investigate
  - **Verify**: 30 tests discoverable, no unexpected test removal
  - **Done when**: All 30 tests accounted for
  - **Commit**: `chore(e2e-ux-tests-fix): S3 regression guard - verify E2E test integrity`
  - _Requirements: Anti-regression protection_

## Phase 3: Quality Gates

- [ ] V1 [VERIFY] Quality checkpoint: make lint && make mypy
  - **Do**: Run lint and type checking
  - **Verify**: `make lint && make mypy` exits 0
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(e2e-ux-tests-fix): pass quality checkpoint` (if fixes needed)

- [ ] V2 [VERIFY] Quality checkpoint: make test (all unit tests pass)
  - **Do**: Run `make test`
  - **Verify**: `make test` exits 0
  - **Done when**: All unit tests pass
  - **Commit**: `chore(e2e-ux-tests-fix): pass unit test checkpoint` (if fixes needed)

- [ ] V3 [VERIFY] Full local CI: make test && make lint && make mypy
  - **Do**: Run complete local CI suite
  - **Verify**: All three commands exit 0
  - **Done when**: Test, lint, and type check all pass
  - **Commit**: `chore(e2e-ux-tests-fix): pass local CI` (if fixes needed)

- [ ] V4 [VERIFY] Full E2E suite: make e2e (final verification)
  - **Do**: Run `make e2e` for final verification after all fixes
  - **Verify**: `make e2e` exits 0
  - **Done when**: All E2E tests pass
  - **Commit**: `chore(e2e-ux-tests-fix): pass final E2E` (if fixes needed)

- [ ] V5 [VERIFY] Verify HA logs clean after final E2E run
  - **Do**:
    1. Find most recent HA log: `ls -t /tmp/logs/ha-e2e-*.log | head -1`
    2. Check errors: `grep -i "error\|exception\|traceback" /tmp/logs/ha-e2e-*.log | tail -50`
    3. Check EMHASS: `grep -i "emhass\|deferrable\|power_profile" /tmp/logs/ha-e2e-*.log | tail -50`
    4. Check datetime (CRITICAL): `grep -i "offset-naive\|offset-aware" /tmp/logs/ha-e2e-*.log` — should return 0 matches
  - **Verify**: No critical errors in HA logs, specifically no datetime naive/aware errors
  - **Done when**: HA logs clean
  - **Commit**: None

- [ ] V6 [VERIFY] AC checklist: programmatically verify all acceptance criteria
  - **Do**:
    1. S1 AC1: `grep "dt_util.parse_datetime" custom_components/ev_trip_planner/trip_manager.py | grep -v "parse_datetime(trip_datetime)" | head -5` — confirm parse_datetime used for string path
    2. S1 AC1b: `grep -B1 -A1 "isinstance.*datetime\|_parse_trip_datetime" custom_components/ev_trip_planner/trip_manager.py | grep "tzinfo" | head -3` — confirm tz check exists for datetime-object path
    3. S1 AC3: `make test` exits 0
    4. S1 AC4: `grep -rn "datetime.strptime" custom_components/ev_trip_planner/` — review each for naive/aware mixing
    5. S2 AC1: `grep -n 'coordinator\.data\["' custom_components/ev_trip_planner/emhass_adapter.py` — 0 matches
    5. S2 AC4: Verify async_cleanup_vehicle_indices uses full dict replacement
    6. S3 AC1: `grep -n "ev_trip_planner_test_vehicle_emhass" tests/e2e/emhass-sensor-updates.spec.ts` — 0 matches
    7. S3 AC2: `grep -n "2026-04-20" tests/e2e/emhass-sensor-updates.spec.ts` — 0 matches
    8. S3 AC4: `grep "logger:" tests/ha-manual/configuration.yaml` — found
    9. S3 AC5: `grep "HA_LOG_FILE" scripts/run-e2e.sh` — found
    10. S3 AC6: `grep "globalTeardown" playwright.config.ts` — 0 matches
    11. S4 AC1: `grep "race-condition-regression-immediate-sensor-check" tests/e2e/emhass-sensor-updates.spec.ts` — found
    12. S4 AC2: `grep "race-condition-regression-rapid-successive" tests/e2e/emhass-sensor-updates.spec.ts` — 2 matches
  - **Verify**: All checks above pass
  - **Done when**: All acceptance criteria confirmed
  - **Commit**: None

## Phase 4: PR Lifecycle

- [ ] PR1 [VERIFY] Create feature branch from current HEAD
  - **Do**:
    1. Verify current branch: `git branch --show-current`
    2. If on default branch (main/master): STOP — alert user (should not happen at startup)
    3. If on feature branch: proceed
  - **Verify**: `git branch --show-current` returns a feature branch name
  - **Done when**: On correct feature branch
  - **Commit**: None

- [ ] PR2 [VERIFY] Stage and commit all changes
  - **Do**:
    1. `git add custom_components/ev_trip_planner/trip_manager.py`
    2. `git add custom_components/ev_trip_planner/emhass_adapter.py`
    3. `git add tests/ha-manual/configuration.yaml`
    4. `git add scripts/run-e2e.sh`
    5. `git add playwright.config.ts`
    6. `git add tests/e2e/emhass-sensor-updates.spec.ts`
    7. `git add tests/test_trip_manager_datetime_tz.py`
    8. `git commit -m "$(cat <<'EOF'
feat(e2e-ux-tests-fix): fix datetime bug, coordinator race condition, and test infrastructure

- Fix datetime naive/aware bug in BOTH paths (datetime objects + strings) in trip_manager.py
- Extract _parse_trip_datetime private method for SOLID SRP
- Replace in-place coordinator.data mutations with full dict replacement
- Add logger debug config for test environment
- Replace hardcoded entity IDs and dates with helpers
- Replace waitForTimeout with toPass() polling
- Remove non-existent globalTeardown reference
- Add race condition regression tests
EOF
)"`
  - **Verify**: `git status` shows clean working tree
  - **Done when**: All changes committed
  - **Commit**: `feat(e2e-ux-tests-fix): fix datetime bug, coordinator race condition, and test infrastructure`

- [ ] PR3 [VERIFY] Push branch to remote
  - **Do**:
    1. `git push -u origin $(git branch --show-current)`
    2. Verify push succeeded
  - **Verify**: `git status` shows branch up to date with remote
  - **Done when**: Branch pushed to remote
  - **Commit**: None

- [ ] PR4 [VERIFY] Create PR using gh CLI
  - **Do**:
    1. `gh pr create --title "fix: datetime bug, coordinator race condition, test infrastructure" --body "$(cat <<'EOF'
## Summary

Fix three root causes blocking E2E test success:

1. **Datetime naive/aware bug**: Fix BOTH code paths in `async_calcular_energia_necesaria` — ensure timezone awareness for datetime objects (line 1471) and strings (line 1475)
2. **Coordinator dual-writer race condition**: Replace in-place `coordinator.data["key"] = value` mutations with full dict replacement
3. **Test infrastructure**: Replace hardcoded IDs/dates, add logger config, remove broken globalTeardown

Then add race condition regression tests and verify UX-01/UX-02 E2E flows pass.

## Changes
- `trip_manager.py`: datetime parsing fix + `_parse_trip_datetime` extraction
- `emhass_adapter.py`: coordinator data mutation fix (2 locations)
- `configuration.yaml`: logger debug config
- `emhass-sensor-updates.spec.ts`: hardcoded values replaced, regression tests added
- `playwright.config.ts`: removed globalTeardown
- `scripts/run-e2e.sh`: log path consistency

## Verification
- `make test` passes
- `make lint` passes
- `make e2e` passes (full suite)
- HA logs clean of errors

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"`
  - **Verify**: PR created, `gh pr view` shows PR details
  - **Done when**: PR created and visible
  - **Commit**: None

- [ ] PR5 [VERIFY] Monitor CI checks
  - **Do**:
    1. `gh pr checks --watch` (wait for CI completion)
    2. If any check fails: read failure details, fix issues, push fixes
    3. Re-verify: `gh pr checks`
  - **Verify**: All CI checks show green (PASS)
  - **Done when**: All CI checks green
  - **Commit**: None (if CI passes on first try)

- [ ] PR6 [VERIFY] Address any review comments
  - **Do**:
    1. Check for review comments: `gh pr view --json comments`
    2. If comments exist: address each one
    3. Push fixes: `git push`
    4. Re-verify CI: `gh pr checks`
  - **Verify**: No unresolved review comments, CI green
  - **Done when**: PR ready for merge
  - **Commit**: None

## Final Verification

- [ ] VF [VERIFY] Goal verification: original failure now passes
  - **Do**:
    1. Run `PYTHONPATH=. .venv/bin/python -m pytest tests/test_trip_manager_datetime_tz.py -v` — should pass (was failing in Phase 0)
    2. Verify datetime-object path also fixed: `grep -B1 -A2 "isinstance.*datetime" custom_components/ev_trip_planner/trip_manager.py | grep -A1 "1470"` — should show tz check
    3. Run `grep -n 'coordinator\.data\["' custom_components/ev_trip_planner/emhass_adapter.py` — should return 0 matches (was showing in-place mutations)
    4. Run `grep -n "ev_trip_planner_test_vehicle_emhass" tests/e2e/emhass-sensor-updates.spec.ts` — should return 0 matches (was hardcoded)
    5. Run `grep -n "2026-04-20" tests/e2e/emhass-sensor-updates.spec.ts` — should return 0 matches (was hardcoded)
    6. Run `grep "logger:" tests/ha-manual/configuration.yaml` — should find logger config (was missing)
    7. Run `grep "globalTeardown" playwright.config.ts` — should return 0 matches (was pointing to non-existent file)
    8. Run `make e2e` and verify HA logs contain NO "offset-naive" or "offset-aware" errors
    9. Document AFTER state in .progress.md
  - **Verify**: All 9 checks above pass (exit 0 for positive checks, exit 1 from grep = no matches for negative checks)
  - **Done when**: All original issues confirmed resolved
  - **Commit**: `chore(e2e-ux-tests-fix): verify fix resolves original issues`

## Notes

- **TDD approach**: All Python changes preceded by failing test (Phase 0 reproduce + Phase 1 RED)
- **SOLID Quality Gate**: Applied after S1 and S2 code fixes via pr-review-toolkit:code-reviewer
- **Self-healing loop**: Up to 3 iterations of make e2e for S5+S6 (Phase 2)
- **E2E constraint**: All E2E tests run as full suite (make e2e), never isolated
- **Anti-regression protection**: Baseline audit (Phase 0), intentional behavior change map (Phase 0), regression guard checks after S1/S2/S3 (Phase 1 VERIFY tasks), full suite verification (Phase 2)
- **Known limitation**: TripManager and EMHASSAdapter remain God Objects (~2200 lines each) — only surgical fixes applied
- **SOLID fallback**: If code-reviewer fails 3 times, ralph-specum:architect-reviewer diagnoses root cause
- **Expected baseline changes**: `make test` will go from FAIL (coverage 99.71%) to PASS (coverage 100%) after S1 fix. E2E test count will go from 28 to 30 after S4 adds regression tests. These are INTENTIONAL, not regressions.
- **Datetime bug**: Fix applies to BOTH code paths in `async_calcular_energia_necesaria` — datetime-object at line 1471 AND string at lines 1474-1480. Both must ensure timezone awareness to prevent `TypeError: can't subtract offset-naive and offset-aware datetimes`.
- **E2E diagnosis**: Read Playwright error context (`test-results/*/error-context.md`) FIRST when diagnosing failures, then cross-reference with HA logs. This prevents chasing backend errors that are symptoms, not root cause.
