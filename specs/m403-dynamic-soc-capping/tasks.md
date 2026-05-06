# Spec: m403-dynamic-soc-capping — Implementation Tasks

**Spec Version**: 2.0
**Branch**: feature-soh-soc-cap
**Base**: main
**Created**: 2026-04-28
**Last Updated**: 2026-05-04
**Task Count**: 225 (200 original + 25 Phase 8: GITO code review fix phase)

## Goals
- Integrate Dynamic SOC Capping: `risk = t * (soc_post_trip - 35) / 65`, `SOC_lim = 35 + 65 * [1 / (1 + risk/T)]`
- SOH-aware battery capacity: `real_capacity = nominal * SOH / 100`
- T_base user-configurable window (6-48h, default 24h)
- Health mode always-on, no toggle

## Quality Gates
- Gate 1: `python3 -m pytest tests/ -q --tb=no` — 0 failed
- Gate 2: `python3 -m ruff check custom_components/ tests/` — 0 errors
- Gate 3: `python3 -m pyright custom_components/` — 0 errors
- Gate 4: `python3 -m ruff format --check custom_components/ tests/` — 0 files to reformat
- Gate 5: E2E `make e2e` — all pass

## Phases

### Phase 1-7: Implementation and Quality Fix (T001-T200) — COMPLETED
All 200 original tasks completed. Quality gates: pytest 0 failed (1822 tests), ruff 0 errors, pyright 0 errors, coverage 100%, E2E 40/40 pass.

### Phase 8: GITO Code Review Fix (T201-T225) — 23 issues from Gito v4.0.3 review

- [x] T001 Baseline test suite
- [x] T002 E2E baseline
- [x] T003-T004: Research and spec
- [x] T005-T200: All implementation tasks
- [x] T200 [VERIFY:QUALITY-GATE] Quality gate

---

## Phase 8: GITO Code Review Fix Phase

**Scope**: 23 REAL issues identified by Gito v4.0.3 code review classification report. 13 of the original 36 issues were classified as FALSE POSITIVE (MagicMock/AsyncMock confusion, format awareness gaps, Playwright semantics, Python deprecation confusion, state blindness).

**Priority order**: Critical runtime bugs first, then medium priority (code quality), then low priority (cosmetic).

### Critical Runtime Bugs

- [x] T201 [GITO] Fix #9: Replace `.get()` call on set in device registry mock
  - **Do**: Change `device.config_entries.get(config_entry_id)` to `config_entry_id in device.config_entries` in `tests/conftest.py` line 385. Sets don't have `.get()`, causing AttributeError at runtime.
  - **Files**: `tests/conftest.py` (line 385)
  - **Done when**: `device.config_entries.get(config_entry_id)` replaced with `config_entry_id in device.config_entries`
  - **Verify**: `python3 -m pytest tests/conftest.py -q --tb=short 2>&1 | tail -3` — no AttributeError
  - **Commit**: `fix(test): fix .get() on set in conftest.py mock_device_registry (GITO #9)`
  - **GITO Issue**: #9

- [x] T202 [GITO] Fix #14: Event listener leak in deleteTestTrip — use page.once instead of manual removeListener
  - **Do**: Replace the `page.on('dialog', dialogHandler)` + `page.removeListener('dialog', dialogHandler)` pattern with `page.once('dialog', async (dialog) => { await dialog.accept(); })` in `tests/e2e-dynamic-soc/trips-helpers.ts` lines 217-239. This prevents stacking listeners if the function throws or times out before removeListener is reached.
  - **Files**: `tests/e2e-dynamic-soc/trips-helpers.ts` (lines 217-239)
  - **Done when**: `page.on('dialog', dialogHandler)` removed and replaced with single-use `page.once('dialog', ...)`. No `dialogCount` variable needed. No `page.removeListener` call.
  - **Verify**: Run the E2E test suite — `make e2e` all pass. Also verify no "listener already has been called" errors in repeated runs.
  - **Commit**: `fix(e2e): use page.once for dialog handling in deleteTestTrip (GITO #14)`
  - **GITO Issue**: #14

- [x] T203 [GITO] Fix #17: Complete incomplete test test_duplicate_dashboard_name_appends_suffix
  - **Do**: The test at `tests/test_dashboard.py` lines 673-687 sets up a config directory but ends without performing any dashboard imports or assertions. Add actual implementation: import the dashboard service, call it with a path that already exists, then assert that a file with `-2-` suffix was created. Look at the companion test `test_duplicate_dashboard_name_overwrites` (line 690) and `test_duplicate_dashboard_name_creates_backup` (line 800) for the existing pattern to follow.
  - **Files**: `tests/test_dashboard.py` (lines 673-687)
  - **Done when**: Test sets up existing dashboard path, calls dashboard import, asserts a new file with `-2-` suffix exists, and cleans up.
  - **Verify**: `python3 -m pytest tests/test_dashboard.py::TestDashboardCreationAndImport::test_duplicate_dashboard_name_appends_suffix -q --tb=short` — passes
  - **Commit**: `fix(test): complete empty test_duplicate_dashboard_name_appends_suffix (GITO #17)`
  - **GITO Issue**: #17

- [x] T204 [GITO] Fix #18: Fix tautological assertion `assert len(new_files) >= 0`
  - **Do**: Change `assert len(new_files) >= 0` to `assert len(new_files) >= 1` at `tests/test_dashboard.py` line 746. The current assertion is always true (list length is never negative).
  - **Files**: `tests/test_dashboard.py` (line 746)
  - **Done when**: Assertion reads `assert len(new_files) >= 1`
  - **Verify**: `python3 -m pytest tests/test_dashboard.py::TestDashboardCreationAndImport::test_duplicate_dashboard_name_overwrites -q --tb=short` — passes
  - **Commit**: `fix(test): fix tautological assertion len >= 0 -> len >= 1 (GITO #18)`
  - **GITO Issue**: #18

- [x] T205 [GITO] Fix #35: Dedent nested test functions with underscore prefix in test_trip_manager_fix_branches.py
  - **Do**: Move `_test_generate_power_profile_finds_entry_via_async_entries` (line 83) and `_test_generate_deferrables_schedule_uses_entry_from_async_entries` (line 120) from nested inside `test_async_entries_exception_uses_default_battery` to module level. Remove the leading underscore from both names. Both are currently invisible to pytest due to the `_` prefix and nested inside another test.
  - **Files**: `tests/test_trip_manager_fix_branches.py` (lines 82-117, 119-155)
  - **Done when**: Both functions are at module level, named `test_generate_power_profile_finds_entry_via_async_entries` and `test_generate_deferrables_schedule_uses_entry_from_async_entries`. They are discoverable by pytest.
  - **Verify**: `python3 -m pytest tests/test_trip_manager_fix_branches.py --collect-only -q 2>&1 | grep -E "test_generate_" | head -5` — both appear
  - **Commit**: `fix(test): dedent nested test functions with underscore prefix (GITO #35)`
  - **GITO Issue**: #35

### Medium Priority — Code Quality

- [x] T206 [GITO] Fix #1: Translate Spanish text in CLAUDE.md TEST E2E section to English
  - **Do**: Translate lines 43-47 of `CLAUDE.md` from Spanish to English. Change `## TEST E2E` to `## E2E TESTS`. Translate "Siempre se ejecutan con makefile" to "Always run them via the Makefile". Translate "Prohibido usar llamadas API" to "API calls are strictly prohibited". Translate the final sentence to "Must replicate real user behavior. If the test cannot replicate real user behavior, it is invalid, indicating either a flaw in the test design or an error in the application code."
  - **Files**: `CLAUDE.md` (lines 43-47)
  - **Done when**: All text in the E2E TESTS section is in English
  - **Verify**: No Spanish text remains in the TEST E2E section
  - **Commit**: `docs: translate CLAUDE.md TEST E2E section from Spanish to English (GITO #1)`
  - **GITO Issue**: #1

- [x] T207 [GITO] Fix #2: Correct ROADMAP.md milestone status — M4.0.2 next target -> M4.1 next target
  - **Do**: Change line 6 of `ROADMAP.md` from `**Development phase**: Milestone 4.0.3 completed — M4.0.2 next target` to `**Development phase**: Milestone 4.0.3 completed — M4.1 next target`. M4.0.2 is documented as a prerequisite for M4.0.3, so it cannot be the "next target" after M4.0.3 is completed.
  - **Files**: `ROADMAP.md` (line 6)
  - **Done when**: Line 6 reads "Milestone 4.0.3 completed — M4.1 next target"
  - **Verify**: `grep -n "next target" ROADMAP.md` — shows M4.1
  - **Commit**: `docs: fix ROADMAP.md inconsistent milestone status — M4.1 is next target (GITO #2)`
  - **GITO Issue**: #2

- [x] T208 [GITO] Fix #3: Correct "Vive Coding" -> "Vibe Coding" typo in PORTFOLIO.md
  - **Do**: Change line 178 of `_ai/PORTFOLIO.md` from `Vive Coding` to `Vibe Coding`. All other references to this term in the document (lines 9, 79) use "Vibe Coding".
  - **Files**: `_ai/PORTFOLIO.md` (line 178)
  - **Done when**: Line 178 reads `Vibe Coding`
  - **Verify**: `grep -c "Vive Coding" _ai/PORTFOLIO.md` — 0
  - **Commit**: `docs: fix Vive Coding -> Vibe Coding typo in PORTFOLIO.md (GITO #3)`
  - **GITO Issue**: #3

- [x] T209 [GITO] Fix #4: Update misleading comment in calculations.py L483
  - **Do**: Change the comment at `custom_components/ev_trip_planner/calculations.py` line 483 from `# Proactive charging trigger: charge when SOC drops below trip energy.` to `# Proactive charging trigger: ensure capacity for trip chains even when SOC covers the current target.` The condition on line 486 checks `if energia_actual >= energia_objetivo:` (i.e., when SOC IS sufficient), but the comment says the opposite (when SOC drops below).
  - **Files**: `custom_components/ev_trip_planner/calculations.py` (line 483)
  - **Done when**: Comment accurately describes the condition: charging when current energy is sufficient to prepare for future trips
  - **Verify**: `grep "Proactive charging" custom_components/ev_trip_planner/calculations.py` — shows updated comment
  - **Commit**: `fix(calculations): fix misleading comment for proactive charging trigger (GITO #4)`
  - **GITO Issue**: #4

- [x] T210 [GITO] Fix #5: Make BatteryCapacity dataclass frozen
  - **Do**: Change `@dataclass` to `@dataclass(frozen=True)` at `custom_components/ev_trip_planner/calculations.py` line 53. The docstring describes it as a "Frozen abstraction for real battery capacity" but the class is not frozen, allowing accidental mutation.
  - **Files**: `custom_components/ev_trip_planner/calculations.py` (line 53)
  - **Done when**: Decorator reads `@dataclass(frozen=True)`
  - **Verify**: `python3 -c "from custom_components.ev_trip_planner.calculations import BatteryCapacity; bc = BatteryCapacity(60, None); bc.nominal_capacity_kwh = 50" 2>&1 | grep -i "frozeninstanceerror" && echo "PASS" || echo "FAIL"` — should show FrozenInstanceError
  - **Commit**: `fix(calculations): make BatteryCapacity frozen dataclass as documented (GITO #5)`
  - **GITO Issue**: #5

- [x] T211 [GITO] Fix #6: Remove redundant dir() check in trip_manager.py
  - **Do**: At `custom_components/ev_trip_planner/trip_manager.py` lines 2178-2183, replace the `precomputed_trip_times = (precomputed_trip_times if "precomputed_trip_times" in dir() else [])` pattern with a direct assignment or a simple comment. Since `calculate_deficit_propagation()` has an early return `if not trips: return []` at line 2140, `precomputed_trip_times` is guaranteed defined when this code is reached. The `"precomputed_trip_times" in dir()` check is always true and misleading.
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py` (lines 2181-2183)
  - **Done when**: The conditional `precomputed_trip_times` assignment is replaced with either the bare variable or removed entirely. Only a comment remains.
  - **Verify**: `python3 -m ruff check custom_components/ev_trip_planner/trip_manager.py` — no issues
  - **Commit**: `fix(trip_manager): remove redundant dir() check for precomputed_trip_times (GITO #6)`
  - **GITO Issue**: #6

- [x] T212 [GITO] Fix #10: Remove contradictory [VERIFY:API] tag from test-config-flow-soh.spec.ts
  - **Do**: In `tests/e2e-dynamic-soc/test-config-flow-soh.spec.ts`, line 17 has the tag `[VERIFY:API]` but line 10 says "No REST API calls". Remove `[VERIFY:API]` from line 17 since the test only interacts with the Home Assistant UI (no API calls).
  - **Files**: `tests/e2e-dynamic-soc/test-config-flow-soh.spec.ts` (line 17)
  - **Done when**: Line 17 reads `* [VE0] E2E Config Flow Validation` (no [VERIFY:API])
  - **Verify**: `grep "VERIFY:API" tests/e2e-dynamic-soc/test-config-flow-soh.spec.ts` — 0 matches
  - **Commit**: `fix(e2e): remove contradictory VERIFY:API tag from config flow test (GITO #10)`
  - **GITO Issue**: #10

- [x] T213 [GITO] Fix #16: Add assertions to exception handling tests in test_coverage_remaining.py
  - **Do**: In `tests/test_coverage_remaining.py`, add assertions to `test_weekly_trip_exception_in_calculate_next_recurring_datetime` (line 69) and `test_weekly_trip_exception_in_day_index_calculation` (line 120). Currently these tests lack assertions — they just call `publish_deferrable_loads()` inside a try/except. Add `assert` statements to verify expected side effects, such as the mock being invoked or the exception being handled cleanly. Use caplog to verify warnings were logged if applicable.
  - **Files**: `tests/test_coverage_remaining.py` (lines 60-72, 110-123)
  - **Done when**: Both tests have at least one assertion verifying expected side effects (mock call, log capture, or exception handling)
  - **Verify**: `python3 -m pytest tests/test_coverage_remaining.py -q --tb=short` — all pass with assertions
  - **Commit**: `fix(test): add assertions to exception handling tests (GITO #16)`
  - **GITO Issue**: #16

- [x] T214 [GITO] Fix #20: Align test name and docstring with actual assertion in test_deferrable_load_sensors.py
  - **Do**: In `tests/test_deferrable_load_sensors.py` lines 311-325, the test is named `test_sensor_includes_last_update_attribute` and the docstring says "Test that last_update timestamp is present", but the assertions only check `emhass_status`. Either: (a) add an assertion for `last_update` in attrs, or (b) rename the test to match the actual assertion. Since `last_update` is the attribute the sensor sets after coordinator update, add `assert "last_update" in attrs` to actually test the stated purpose.
  - **Files**: `tests/test_deferrable_load_sensors.py` (lines 311-325)
  - **Done when**: Test asserts both `"last_update" in attrs` and `"emhass_status" in attrs`, matching the test name and docstring
  - **Verify**: `python3 -m pytest tests/test_deferrable_load_sensors.py::TestEmhassDeferrableLoadSensor::test_sensor_includes_last_update_attribute -q --tb=short` — passes
  - **Commit**: `fix(test): add last_update assertion to match test name (GITO #20)`
  - **GITO Issue**: #20

- [x] T215 [GITO] Fix #21: Refactor test_sensor_emhass_status_error_on_exception to simulate actual exception
  - **Do**: In `tests/test_deferrable_load_sensors.py` lines 342-354, `test_sensor_emhass_status_error_on_exception` manually sets `"emhass_status": "error"` on mock coordinator data instead of triggering an actual exception path in the sensor code. Refactor to mock the coordinator's `async_update()` method to raise an exception, then verify the sensor sets `emhass_status` to `"error"` as a result of the exception handling.
  - **Files**: `tests/test_deferrable_load_sensors.py` (lines 342-354)
  - **Done when**: Test triggers an actual exception through the coordinator, and asserts the sensor's error handling sets `native_value == "error"` and `extra_state_attributes["emhass_status"] == "error"`
  - **Verify**: `python3 -m pytest tests/test_deferrable_load_sensors.py::TestEmhassDeferrableLoadSensor::test_sensor_emhass_status_error_on_exception -q --tb=short` — passes
  - **Commit**: `fix(test): simulate actual exception in error_on_exception test (GITO #21)`
  - **GITO Issue**: #21

- [x] T216 [GITO] Fix #23: Rename test_datetime_subtraction_raises_typeerror to reflect actual behavior
  - **Do**: In `tests/test_emhass_datetime.py`, rename `test_datetime_subtraction_raises_typeerror` to `test_aware_datetime_subtraction_succeeds` (line 22). The test currently asserts that subtraction succeeds, not that it raises TypeError. Update the docstring to match. Remove the misleading "RED Phase / GREEN Phase" references since this is not testing the emhass_adapter code path directly — it only tests datetime objects.
  - **Files**: `tests/test_emhass_datetime.py` (lines 22-47)
  - **Done when**: Test is named `test_aware_datetime_subtraction_succeeds`, docstring accurately describes what it tests, and the emhass_adapter references are removed or corrected.
  - **Verify**: `python3 -m pytest tests/test_emhass_datetime.py --collect-only -q 2>&1 | grep "test_aware_datetime_subtraction"` — appears in output
  - **Commit**: `fix(test): rename misleading test_datetime_subtraction_raises_typeerror (GITO #23)`
  - **GITO Issue**: #23

- [x] T217 [GITO] Fix #28: Correct assertion message in test_panel_entity_id.py
  - **Do**: In `tests/test_panel_entity_id.py` line 144, the assertion message says "to extract vehicle ID" but the regex only checks for `includes('emhass_perfil_diferible_')`. Change the message to accurately describe the check: "to verify the EMHASS sensor prefix filter is present".
  - **Files**: `tests/test_panel_entity_id.py` (line 144)
  - **Done when**: Assertion message reads "to verify the EMHASS sensor prefix filter is present"
  - **Verify**: `python3 -m pytest tests/test_panel_entity_id.py -q --tb=short` — passes
  - **Commit**: `fix(test): fix misleading assertion message in panel entity ID test (GITO #28)`
  - **GITO Issue**: #28

- [x] T218 [GITO] Fix #30: Align assertion method in SOC debouncing test with suite convention
  - **Do**: In `tests/test_presence_monitor_soc.py` line 483, change `mock_trip_manager.async_generate_power_profile.assert_not_called()` to `mock_trip_manager.publish_deferrable_loads.assert_not_called()`. This test is in the `test_presence_monitor_soc.py` file where all other tests use `publish_deferrable_loads.assert_not_called()`.
  - **Files**: `tests/test_presence_monitor_soc.py` (line 483)
  - **Done when**: Assertion reads `mock_trip_manager.publish_deferrable_loads.assert_not_called()`
  - **Verify**: `python3 -m pytest tests/test_presence_monitor_soc.py -q --tb=short` — passes
  - **Commit**: `fix(test): align assertion with suite convention in SOC debouncing test (GITO #30)`
  - **GITO Issue**: #30

- [x] T219 [GITO] Fix #31: Translate Spanish comments in test_soc_100_propagation_bug.py to English
  - **Do**: In `tests/test_soc_100_propagation_bug.py`, translate all Spanish comments and docstrings to English. Key locations: line 2 (file header), line 5 (docstring), line 186 (comment with em-dash), lines 209-211 (docstring with Spanish), line 249-252 (print statements with Spanish). Use the existing English patterns in the file as a guide for style.
  - **Files**: `tests/test_soc_100_propagation_bug.py` (multiple lines)
  - **Done when**: No Spanish text remains in the file. All comments and docstrings are in English.
  - **Verify**: `grep -n "principio físico\|se puede cargar\|test de integridad" tests/test_soc_100_propagation_bug.py` — 0 matches
  - **Commit**: `fix(test): translate Spanish comments in SOC 100 propagation test (GITO #31)`
  - **GITO Issue**: #31

- [x] T220 [GITO] Fix #32: Remove debug print statements from test_t32_and_p11_tdd.py
  - **Do**: In `tests/test_t32_and_p11_tdd.py` lines 100-106, remove the two `print()` debug statements around `publish_deferrable_loads` calls. These clutter CI output. Replace with `logging.debug()` calls if debug information is needed for future development.
  - **Files**: `tests/test_t32_and_p11_tdd.py` (lines 100-106)
  - **Done when**: No `print(` calls remain in the test file
  - **Verify**: `grep -n "print(" tests/test_t32_and_p11_tdd.py` — 0 matches
  - **Commit**: `fix(test): remove debug print statements from T32/P11 test (GITO #32)`
  - **GITO Issue**: #32

- [x] T221 [GITO] Fix #33: Translate Spanish comments in test_t32_and_p11_tdd.py to English
  - **Do**: In `tests/test_t32_and_p11_tdd.py`, translate all Spanish comments to English. Key locations: line 45 (docstring "TDD: Sensor con 0 cargas"), line 48 (comment "Sin trips"), line 88 (docstring "TDD: Viaje recurrente pasado"), line 108 (comment "El datetime debe ser diferente"), lines 147-149 (comments "Todos los viajes recurrentes deben tener datetime actualizado", "este test no falla porque", "Cuando se implemente T3.2").
  - **Files**: `tests/test_t32_and_p11_tdd.py` (multiple lines)
  - **Done when**: No Spanish text remains in the file
  - **Verify**: `grep -c "Sin trips\|este test no falla\|Cuando se implemente T3.2\|El datetime debe ser diferente" tests/test_t32_and_p11_tdd.py` — 0
  - **Commit**: `fix(test): translate Spanish comments in T32/P11 test to English (GITO #33)`
  - **GITO Issue**: #33

- [x] T222 [GITO] Fix #36: Fix test name/docstring vs assertion contradiction in test_vehicle_id_vs_entry_id_cleanup.py
  - **Do**: In `tests/test_vehicle_id_vs_entry_id_cleanup.py`, the test `test_cleanup_fails_when_vehicle_id_differs_from_entry_id` (line 56) docstring says "This test SHOULD FAIL with the current code" but the assertions expect cleanup to succeed. The test was originally designed to demonstrate a bug, but the fix was already applied and the test now verifies the successful behavior. Rename the test to `test_cleanup_succeeds_when_vehicle_id_differs_from_entry_id` and update the docstring to reflect the current positive behavior.
  - **Files**: `tests/test_vehicle_id_vs_entry_id_cleanup.py` (line 56, docstring)
  - **Done when**: Test name reads `test_cleanup_succeeds_when_vehicle_id_differs_from_entry_id`. Docstring reflects that cleanup successfully removes the sensor.
  - **Verify**: `python3 -m pytest tests/test_vehicle_id_vs_entry_id_cleanup.py --collect-only -q 2>&1 | grep "test_cleanup_succeeds"` — appears in output
  - **Commit**: `fix(test): rename to match successful assertion behavior (GITO #36)`
  - **GITO Issue**: #36

### Verification Checkpoints

- [x] T223 [VERIFY] Quality check batch 1: Run pytest + ruff after critical bug fixes
  - **Do**: Run `python3 -m pytest tests/ -q --tb=no && python3 -m ruff check custom_components/ tests/` after completing T201-T205
  - **Verify**: All commands exit 0
  - **Done when**: pytest 0 failed, ruff 0 errors
  - **Commit**: None (verification only)

- [x] T224 [VERIFY] Quality check batch 2: Run pytest + ruff after medium priority fixes
  - **Do**: Run `python3 -m pytest tests/ -q --tb=no && python3 -m ruff check custom_components/ tests/` after completing T206-T222
  - **Verify**: All commands exit 0
  - **Done when**: pytest 0 failed, ruff 0 errors
  - **Commit**: None (verification only)

### Final Verification

- [x] T225 [VERIFY:FINAL] Full CI: pytest 0 failed, ruff 0 errors, pyright 0 errors, ruff format 0 files to reformat
  - **Do**: Run full CI suite: `python3 -m pytest tests/ -q --tb=no && python3 -m ruff check custom_components/ tests/ && python3 -m pyright custom_components/ && python3 -m ruff format --check custom_components/ tests/`
  - **Verify**: All pass
  - **Done when**: All quality gates pass
  - **Commit**: None
