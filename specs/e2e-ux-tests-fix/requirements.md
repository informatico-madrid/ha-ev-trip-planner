# Requirements: E2E UX-01 + UX-02 Fix with TDD Self-Healing Loop

**Spec**: e2e-ux-tests-fix
**Phase**: requirements
**Created**: 2026-04-22
**Status**: ready-for-implementation

---

## 1. Problem Statement

Multiple AI agents have failed over consecutive days trying to create working E2E tests for the EV Trip Planner Home Assistant integration. The tests exist in code (`tests/e2e/emhass-sensor-updates.spec.ts`) but never actually pass because the underlying root causes have never been addressed.

**Three root causes, ALL must be fixed before E2E tests can pass reliably:**

1. **Datetime naive/aware bug** in `trip_manager.py:1473` — `datetime.strptime()` produces naive datetime compared with `dt_util.now()` (aware) → `TypeError` caught silently by `except TypeError: pass` → `horas_disponibles = 0` → no charging alert fires → sensor attributes remain all zeros.

2. **Coordinator dual-writer race condition** — Both `_async_update_data()` (30s interval) and `EMHASSAdapter` directly mutate `coordinator.data` with no synchronization. Tests see stale/empty data even with the existing fix.

3. **Missing test infrastructure** — No server log capture on failure, no self-healing TDD loop in stories, hardcoded entity IDs and dates, `waitForTimeout()` anti-pattern throughout, `globalTeardown` points to non-existent file.

---

## 2. Story Catalog

| Story | ID | Title | Dependency |
|-------|----|-------|------------|
| S1 | code-fix-datetime | Fix datetime naive/aware bug in trip_manager.py | None (independent) |
| S2 | code-fix-coordinator | Fix coordinator dual-writer race condition | None (independent) |
| S3 | test-infrastructure | Fix test infrastructure (entity IDs, dates, timeouts, logs) | None (independent) |
| S4 | race-condition-regression | Add race condition regression tests | S1 + S2 (code fixes) |
| S5 | e2e-ux01 | E2E UX-01: Complete recurring trip lifecycle + sensor sync | S1 + S2 + S3 + S4 |
| S6 | e2e-ux02 | E2E UX-02: Multiple trips + no device/sensor duplication | S1 + S2 + S3 + S4 |

Stories S1-S3 are independent and should be executed FIRST. Stories S5-S6 depend on S1-S4 being complete.

**Critical ordering**: S1-S3 must pass their checkpoints before S5-S6 can begin. S5 and S6 share a self-healing loop — they must be executed together because they affect the same sensor state.

---

## 3. Story S1: Fix Datetime Naive/Aware Bug

### 3.1 Context

**Location**: `custom_components/ev_trip_planner/trip_manager.py`

**Line 1473 (CRITICAL)**:
```python
trip_time = datetime.strptime(trip_datetime, "%Y-%m-%dT%H:%M")  # NAIVE
now = dt_util.now()                                               # AWARE (UTC)
delta = trip_time - now                                           # TypeError!
```
When `trip_datetime` arrives as a string (common from UI/form data), it is parsed with `datetime.strptime()` producing a naive datetime. `dt_util.now()` returns an aware datetime (UTC). Subtracting them raises `TypeError: can't subtract offset-naive and offset-aware datetimes`, caught silently by `except (KeyError, ValueError, TypeError): pass`. Result: `horas_disponibles = 0` silently.

**Line 1318 (secondary)**:
```python
trip_time = datetime.combine(
    hoy, datetime.strptime(trip["hora"], "%H:%M").time()
)
```
Creates `time()` without timezone info. Less critical because it is used in `datetime.combine()` which produces a naive `datetime` used only for local date comparison within the same file.

### 3.2 Acceptance Criteria

1. [AC1] `trip_time = dt_util.parse_datetime(trip_datetime)` at line 1473 — replaces `datetime.strptime()` call, always returns timezone-aware datetime
2. [AC2] `datetime.strptime(trip["hora"], "%H:%M").time()` at line 1318 — change to `time(..., tzinfo=timezone.utc)` for consistency (or leave as-is if it causes no issues, since it is used only for local date comparison)
3. [AC3] Unit test `tests/test_trip_manager_datetime_tz.py` passes after fix (verifies the fix works end-to-end, not just via mocking)
4. [AC4] No other `datetime.strptime()` calls in the codebase produce naive datetimes that are compared with aware datetimes

### 3.3 Tasks

- [ ] Task 1.1: Fix line 1473 — RED first, then GREEN
  - Write a failing test in `tests/test_trip_manager_datetime_tz.py` that calls `async_calcular_energia_necesaria` with a string datetime (not datetime object), forcing the buggy path at line 1473
  - Run the test — it should FAIL with TypeError (proving the bug exists)
  - Replace `datetime.strptime(trip_datetime, "%Y-%m-%dT%H:%M")` with `dt_util.parse_datetime(trip_datetime)`
  - Run the test — it should PASS (proving the fix works)
- [ ] Task 1.2: SOLID-ize the touched function (per Section 9.1.1)
  - `async_calcular_energia_necesaria` is 95+ lines with mixed responsibilities (energy calculation + time calculation + datetime parsing)
  - Extract the datetime parsing into a private method: `def _parse_trip_datetime(self, trip_datetime: Any) -> datetime`
  - This method: if input is datetime, return it; if string, call `dt_util.parse_datetime()`; ensure result has tzinfo
  - Replace the inline `if/else` at lines 1470-1473 with a single call to `self._parse_trip_datetime(trip_datetime)`
  - Add docstring explaining the method and its return value
  - This is SOLID SRP locally — the parsing logic is separated from the energy calculation logic
- [ ] Task 1.3: Verify line 1318 doesn't need fixing
  - This creates a `time()` object used only in `datetime.combine(hoy, ...)` for local date comparison
  - Since it stays within the same file and is compared with other naive datetimes, it is likely safe
  - **DO NOT** change unless unit tests prove otherwise
- [ ] Task 1.4: Update `tests/test_trip_manager_datetime_tz.py`
  - The existing test mocks `dt_util.now()` but the bug path uses `datetime.strptime` — the test may pass via mocking even when the bug is unfixable at runtime
  - After the fix, verify the test still passes (the fix makes it work without any mocking)
  - The test should call `async_calcular_energia_necesaria` with a string datetime to exercise the real parsing path (not via mock)
- [ ] Task 1.5: Grep for other `datetime.strptime` calls
  - Run: `grep -rn "datetime.strptime" custom_components/ev_trip_planner/`
  - Verify none produce naive datetimes that are later compared with aware datetimes

### 3.4 Checkpoint: Unit Tests + SOLID Quality Gate

**MANDATORY before proceeding to S2**:

1. SOLID Quality Gate (per Sections 9.1.2 + 9.1.3):
   - Run: `cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner && git diff custom_components/ev_trip_planner/trip_manager.py`
   - Spawn a `pr-review-toolkit:code-reviewer` subagent with the diff and SOLID criteria from Section 9.1.2
   - If reviewer flags a MUST criterion failure → fix it → re-request review (max 2 retries)
   - If 3 total attempts exhausted → launch `ralph-specum:architect-reviewer` fallback path (Section 9.1.3)
   - If architect gives fix instructions → apply them → re-request review
   - If final attempt also fails → abandon SOLID-ization, proceed with minimal fix, document limitation
2. Run: `cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner && make test`
   - All existing unit tests must pass
   - Specifically verify: `tests/test_trip_manager_datetime_tz.py` passes
3. Run: `make lint`
   - No pylint/mypy/ruff violations
4. Verify no regression: `grep -rn "datetime.strptime" custom_components/ev_trip_planner/` shows no naive/aware mixing

**GATE**: Do NOT proceed to S2 until SOLID Quality Gate passes AND all checkpoint tests pass.

### 3.5 Known Limitations

- TripManager remains a 2197-line God Object. Do NOT attempt to refactor it in this sprint.
- Only fix the specific datetime bug. No broader architectural changes.

---

## 4. Story S2: Fix Coordinator Dual-Writer Race Condition

### 4.1 Context

**Location**: `custom_components/ev_trip_planner/emhass_adapter.py`

The coordinator has TWO writers to `coordinator.data`:

1. **Writer A**: `_async_update_data()` in `coordinator.py` — runs on a 30s interval via `DataUpdateCoordinator`
2. **Writer B**: Direct mutations in `emhass_adapter.py` — lines 734-736, 1844-1863, 1949-1953

The existing fix (around line 729) already partially addresses this:
```python
coordinator.data = {
    **existing_data,
    "per_trip_emhass_params": {},
    "emhass_power_profile": [],
    ...
}
await coordinator.async_refresh()
```

However, there are still direct mutations at lines 1849-1853 and 1951-1954 that modify individual keys in-place:
```python
coordinator.data["per_trip_emhass_params"] = {}
coordinator.data["emhass_power_profile"] = []
```

The race condition: when `publish_deferrable_loads()` caches new trip data and then calls `coordinator.async_refresh()`, the coordinator's `_async_update_data()` may have already started a refresh cycle (due to the 30s interval) and will overwrite the fresh data with stale data from the cache.

The existing fix caches trip data BEFORE calling `coordinator.async_refresh()`, which should prevent the stale read. But the in-place mutations at lines 1849-1853 can conflict with `_async_update_data()` reading the same keys.

### 4.2 Acceptance Criteria

1. [AC1] All direct in-place mutations of `coordinator.data[...]` in `emhass_adapter.py` are replaced with full dict replacements (the `coordinator.data = { ... }` pattern)
2. [AC2] After trip creation via UI, `coordinator.async_refresh()` is called ONCE from `publish_deferrable_loads()` and no other concurrent refresh is possible
3. [AC3] The `publish_deferrable_loads()` method populates the cache BEFORE calling `coordinator.async_refresh()` — verified by code inspection
4. [AC4] `async_cleanup_vehicle_indices()` uses the same pattern (full dict replacement, not in-place mutation)

### 4.3 Tasks

- [ ] Task 2.1: Replace in-place mutation at lines 1849-1853
  - Current pattern: `coordinator.data["per_trip_emhass_params"] = {}`
  - Fix: Build a new dict with `coordinator.data = {**coordinator.data, "per_trip_emhass_params": {}, ...}`
- [ ] Task 2.2: Replace in-place mutation at lines 1951-1954
  - Same pattern as 2.1 — use full dict replacement
- [ ] Task 2.3: Verify the `publish_deferrable_loads()` sequence at lines 729-745 is correct
  - This is the main trip creation path — it should:
    1. Cache trip data in adapter `_cached_*` attributes
    2. Call `publish_deferrable_loads()` → which calls `coordinator.async_set_data()` then `async_refresh()`
  - No change needed here if the cache is populated BEFORE `async_refresh()`

### 4.4 Checkpoint: Unit Tests + SOLID Quality Gate

**MANDATORY before proceeding to S3**:

1. SOLID Quality Gate (per Sections 9.1.2 + 9.1.3):
   - Run: `cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner && git diff custom_components/ev_trip_planner/emhass_adapter.py`
   - Spawn a `pr-review-toolkit:code-reviewer` subagent with the diff and SOLID criteria from Section 9.1.2
   - If reviewer flags a MUST criterion failure → fix it → re-request review (max 2 retries)
   - If 3 total attempts exhausted → launch `ralph-specum:architect-reviewer` fallback path (Section 9.1.3)
   - If architect gives fix instructions → apply them → re-request review
   - If final attempt also fails → abandon SOLID-ization, proceed with minimal fix, document limitation
2. Run: `cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner && make test`
3. Run: `make lint`
4. Verify: `grep -n "coordinator.data\[" custom_components/ev_trip_planner/emhass_adapter.py` returns ZERO matches (no more in-place mutations)

**GATE**: Do NOT proceed to S3 until SOLID Quality Gate passes AND all checkpoint tests pass.

### 4.5 Known Limitations

- The coordinator still has the 30s interval refresh from `DataUpdateCoordinator`. We cannot remove this — it is HA's standard pattern. We can only ensure our explicit `async_refresh()` calls complete before the next interval refresh starts.
- No architectural refactoring of the coordinator/trip_manager boundary.

---

## 5. Story S3: Fix Test Infrastructure

### 5.1 Context

The existing E2E tests (`tests/e2e/emhass-sensor-updates.spec.ts`) have several issues that make them inherently flaky:

1. **Hardcoded entity IDs** (lines 308, 427): `'sensor.ev_trip_planner_test_vehicle_emhass_perfil_diferible_test_vehicle'` — entity ID format may vary
2. **Hardcoded dates** (lines 75-78, 136-138, 489-491): `'2026-04-20T10:00'` — fails after the date passes
3. **`waitForTimeout()` anti-pattern** (lines 82, 145, 496, etc.): Waits fixed time instead of checking for actual state
4. **Missing HA log level configuration**: No debug logs for `custom_components.ev_trip_planner`
5. **Missing log capture on failure**: `run-e2e.sh` logs to `/tmp/ha-e2e.log` but never dumps/errors on failure
6. **`globalTeardown` points to non-existent file**: `playwright.config.ts` line 18 references `./globalTeardown.ts` which does not exist

### 5.2 Acceptance Criteria

1. [AC1] All hardcoded entity IDs replaced with `discoverEmhassSensorEntityId()` helper
2. [AC2] All hardcoded dates replaced with `getFutureIso()` helper
3. [AC3] `waitForTimeout()` replaced with `toPass()` checks where possible
4. [AC4] `configuration.yaml` includes logger debug config for the integration
5. [AC5] `run-e2e.sh` includes timestamped log files and post-test failure dump
6. [AC6] `playwright.config.ts` `globalTeardown` removed or file created

### 5.3 Tasks

- [ ] Task 3.1: Add logger configuration to `configuration.yaml`
  - Add to `tests/ha-manual/configuration.yaml`:
    ```yaml
    logger:
      default: warning
      logs:
        custom_components.ev_trip_planner: debug
        homeassistant.components.sensor: debug
    ```
- [ ] Task 3.2: Fix hardcoded entity IDs
  - Line 308: Replace `sensor.ev_trip_planner_test_vehicle_emhass_perfil_diferible_test_vehicle` with `await discoverEmhassSensorEntityId(page)`
  - Line 427: Same replacement
  - Ensure `discoverEmhassSensorEntityId()` is defined at file level in `emhass-sensor-updates.spec.ts`
- [ ] Task 3.3: Fix hardcoded dates
  - Line 75: `'2026-04-20T10:00'` → use `getFutureIso(1, '10:00')`
  - Line 138: `'2026-04-20T10:00'` → use `getFutureIso(1, '10:00')`
  - Lines 489-491: `'2026-04-20T10:00'` → use `getFutureIso(1, '10:00')`
  - Ensure `getFutureIso()` is defined at file level in `emhass-sensor-updates.spec.ts`
- [ ] Task 3.4: Replace `waitForTimeout()` with `toPass()`
  - Replace `await page.waitForTimeout(3000)` with `await expect(async () => { ... }).toPass({ timeout: 15000 })` checking `emhass_status === 'ready'`
  - Note: For UX-02 multi-trip creation, a short `waitForTimeout(5000)` after creating 3 trips is acceptable per research.md, but sensor checks should still use `toPass()`
- [ ] Task 3.5: Enhance `run-e2e.sh` for log capture
  - Add timestamped log file: `HA_RUN_TIMESTAMP=$(date +%Y%m%d_%H%M%S)` and `HA_LOG_FILE="/tmp/ha-e2e-${HA_RUN_TIMESTAMP}.log"`
  - Add post-test failure dump:
    ```bash
    if [ $TEST_RESULT -ne 0 ]; then
      echo "E2E TESTS FAILED — Saving HA logs for debugging"
      cp "$HA_LOG_FILE" "/tmp/ha-e2e-failed-${HA_RUN_TIMESTAMP}.log"
      echo "Recent HA errors:"
      grep -i "error\|exception\|traceback\|failed" "$HA_LOG_FILE" | tail -50
      echo "EMHASS-related log entries:"
      grep -i "emhass\|deferrable\|power_profile\|coordinator" "$HA_LOG_FILE" | tail -50
    fi
    ```
- [ ] Task 3.6: Fix `globalTeardown` in `playwright.config.ts`
  - Remove line 18: `globalTeardown: './globalTeardown.ts',`
  - The file does not exist and causes Playwright initialization warnings

### 5.4 Checkpoint: Playwright Test Discovery

**MANDATORY before proceeding to S4-S6**:

1. Run: `npx playwright test --list` (from project root)
   - All test files should be discovered without errors
   - No references to missing `globalTeardown.ts`
2. Run: `grep -n "2026-04-20" tests/e2e/emhass-sensor-updates.spec.ts` should return ZERO matches
3. Run: `grep -n "waitForTimeout" tests/e2e/emhass-sensor-updates.spec.ts` should return minimal matches (only UX-02 multi-trip delay is acceptable)
4. Run: `grep -n "ev_trip_planner_test_vehicle_emhass" tests/e2e/emhass-sensor-updates.spec.ts` should return ZERO matches (no hardcoded entity IDs)

**GATE**: Do NOT proceed to S4-S6 until all checkpoint checks pass.

---

## 6. Story S4: Add Race Condition Regression Tests

### 6.1 Context

The existing UX-01/UX-02 tests use `waitForTimeout(3000-5000)` before checking sensor attributes, meaning they would PASS even with the original buggy code (the delay gives enough time for async data to propagate). We need two regression tests that check IMMEDIATELY after trip creation — without any artificial delay.

### 6.2 Acceptance Criteria

1. [AC1] Test "race-condition-regression-immediate-sensor-check" creates a trip and IMMEDIATELY checks sensor attributes (no `waitForTimeout()` before check)
2. [AC2] Test "rapid-successive-trip-creation" creates two trips back-to-back and verifies the second trip adds to (not overwrites) the sensor data
3. [AC3] Both tests use `toPass()` polling for sensor attribute verification
4. [AC4] Both tests use `discoverEmhassSensorEntityId()` and `getFutureIso()` (no hardcoded values)
5. [AC5] Both tests verify: `def_total_hours_array` has positive values, `p_deferrable_matrix` has non-zero entries, `emhass_status === 'ready'`

### 6.3 Tasks

- [ ] Task 4.1: Add regression test for immediate sensor check
  - Create trip via UI
  - Immediately discover sensor entity ID
  - Verify `def_total_hours_array.length > 0` and `some(v > 0)` via `toPass({ timeout: 15000 })`
  - Verify `p_deferrable_matrix.some(profile => profile.some(v > 0))`
  - Verify `emhass_status === 'ready'`
- [ ] Task 4.2: Add regression test for rapid successive creation
  - Create trip 1 at T+0
  - Immediately verify sensor shows trip 1 data
  - Create trip 2 at T+0 (no delay between)
  - Immediately verify sensor shows BOTH trips' data
  - Verify `emhass_status === 'ready'`

### 6.4 Checkpoint: ALL Tests Execute (NOT ISOLATED)

**CRITICAL: E2E tests share the same ephemeral HA container. They MUST be run as a complete suite, NEVER isolated.**

1. Run: `make e2e` — ALL E2E tests must pass, not just S4 tests
2. The regression tests in S4 are embedded in `tests/e2e/emhass-sensor-updates.spec.ts` alongside S5/S6 tests
3. Each test's `beforeEach` calls `cleanupTestTrips(page)` — tests depend on the same HA state lifecycle
4. The sensor state (`power_profile_watts`, `deferrables_schedule`) is shared across tests
5. Running only S4 tests in isolation would give false-positive results (the sensor state would be wrong without the full test suite running)
6. These tests serve as **proof** that the code fixes from S1 and S2 are working

**GATE**: Do NOT proceed to S5-S6 until ALL E2E tests pass in `make e2e`.

---

## 7. Story S5: E2E UX-01 — Complete Recurring Trip Lifecycle + Sensor Sync

### 7.1 Story

As a QA engineer, I want to verify that a complete recurring trip lifecycle (create → propagate → delete) synchronizes correctly with the EMHASS sensor, so that I can guarantee the race condition fix works in the most complex case (recurring, not just punctual).

### 7.2 Acceptance Criteria

1. [AC1] After creating a recurring trip, the trip appears in the UI with correct data
2. [AC2] The EMHASS sensor `power_profile_watts` attribute contains at least one NON-ZERO value
3. [AC3] The EMHASS sensor `deferrables_schedule` attribute is populated (array with length > 0)
4. [AC4] The EMHASS sensor `emhass_status` attribute equals "ready"
5. [AC5] After deleting the trip, the EMHASS sensor `power_profile_watts` attribute becomes ALL ZEROS
6. [AC6] After deleting the trip, the trip no longer appears in the UI

### 7.3 Validation Contract

| # | Validation | Criterion | Timeout | Playwright Tool |
|---|-----------|-----------|---------|-----------------|
| V1 | Recurring trip appears in UI | `getByText(description)` visible | 10s | `expect.toBeVisible()` |
| V2 | Sensor has `power_profile_watts` NON-ZERO | `attrs.power_profile_watts.some(v => v > 0)` | 15s polling | `expect.toBe(true)` |
| V3 | Sensor has `deferrables_schedule` populated | `Array.isArray(attrs.deferrables_schedule) && length > 0` | 15s polling | `expect.toBe(true)` |
| V4 | Sensor has `emhass_status === "ready"` | `attrs.emhass_status === "ready"` | 15s polling | `expect.toBe("ready")` |
| V5 | After delete: sensor goes to ALL ZEROS | `attrs.power_profile_watts.every(v => v === 0)` | 15s polling | `expect.toBe(true)` |
| V6 | Trip no longer appears in UI | `getByText(description)` not visible | 5s | `expect.toNotBeVisible()` |

### 7.4 Self-Healing Loop

**This is the MANDATORY execution pattern for S5+S6 (executed TOGETHER):**

```
Iteration 0 — PRE-FLIGHT CHECKS (before each make e2e):
  1. Verify SOC is 20%: check input_number.test_vehicle_soc in configuration.yaml
  2. Verify no hardcoded dates: grep '2026-04' tests/e2e/emhass-sensor-updates.spec.ts should return 0 matches
  3. Verify no hardcoded entity IDs: grep 'ev_trip_planner_test_vehicle_emhass' tests/e2e/ should return 0 matches
  4. Verify logger config exists in configuration.yaml
  5. If ANY check fails → fix immediately before running tests

Iteration 1+:
  1. Run: cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner && make e2e
  2. If ALL tests pass:
     a. Verify 100% of S5 AND S6 acceptance criteria met
     b. Check /tmp/logs/ha-e2e-*.log for errors/exceptions:
        grep -i "error\|exception\|traceback" /tmp/logs/ha-e2e-*.log
        grep -i "emhass\|deferrable\|power_profile" /tmp/logs/ha-e2e-*.log
     c. Mark S5 and S6 COMPLETE
  3. If tests FAIL:
     a. Read most recent HA log: tail -200 /tmp/logs/ha-e2e-*.log
     b. Search for errors: grep -i "error\|exception\|traceback" /tmp/logs/ha-e2e-*.log
     c. Search for EMHASS: grep -i "emhass\|deferrable" /tmp/logs/ha-e2e-*.log
     d. Search for coordinator: grep -i "coordinator\|async_refresh\|async_set_data" /tmp/logs/ha-e2e-*.log
     e. Classify failure:
        - UI element not found → Fix Playwright locator (use getByRole > getByLabel > ...)
        - Sensor attribute wrong → Check coordinator async_set_data() flow
        - Timeout → Increase toPass() timeout
        - HA startup error → Check configuration.yaml
        - TypeError/naive/aware → Re-check S1 datetime fix
     f. Fix root cause (ONE change at a time)
     g. Re-run: make e2e
     h. Max 3 iterations. If still failing after 3 → mark BLOCKED with diagnosis
```

### 7.5 Pre-flight Checks

**Must verify BEFORE test execution:**

1. **SOC Level**: `tests/ha-manual/configuration.yaml` must have `initial: 20` for `test_vehicle_soc`
2. **No hardcoded dates**: `grep -rn "2026-04-20" tests/e2e/` should return zero matches
3. **No hardcoded entity IDs**: `grep -rn "ev_trip_planner_test_vehicle_emhass" tests/e2e/` should return zero matches
4. **Logger config**: `tests/ha-manual/configuration.yaml` must include `custom_components.ev_trip_planner: debug`
5. **Clean state**: No leftover trips from previous test runs

### 7.6 Known Issues

- TripManager is a 2197-line God Object. No refactoring in this sprint.
- EMHASSAdapter is a 2266-line God Object. No refactoring in this sprint.
- The 30s coordinator refresh interval still exists. We minimize damage by ensuring `publish_deferrable_loads()` completes its cache + refresh cycle before the next interval triggers.

---

## 8. Story S6: E2E UX-02 — Multiple Trips + No Device/Sensor Duplication

### 8.1 Story

As a QA engineer, I want to verify that creating MULTIPLE simultaneous trips (2 recurring + 1 punctual) does not duplicate devices or sensors in Home Assistant, and that deleting one trip individually does not affect the others, so that I can guarantee system integrity under load.

### 8.2 Acceptance Criteria

1. [AC1] After creating 3 simultaneous trips (2 recurring + 1 punctual), all 3 appear in the UI
2. [AC2] Only 1 device exists in `/config/devices` for "EV Trip Planner test_vehicle"
3. [AC3] Only 1 EMHASS sensor entity exists in `/config/entities` (no duplication)
4. [AC4] After deleting 1 of 3 trips, the other 2 trips remain visible in the UI
5. [AC5] After deleting 1 of 3 trips, the EMHASS sensor still has NON-ZERO values
6. [AC6] After deleting ALL trips, the EMHASS sensor `power_profile_watts` becomes ALL ZEROS

### 8.3 Validation Contract

| # | Validation | Criterion | Timeout | Playwright Tool |
|---|-----------|-----------|---------|-----------------|
| V1 | 3 trips appear in UI | `getByText('UX02 Trip 1')`, `getByText('UX02 Trip 2')`, `getByText('UX02 Trip 3')` all visible | 10s each | `expect.toBeVisible()` |
| V2 | Only 1 device in `/config/devices` | Count of rows with "EV Trip Planner test_vehicle" === 1 | 10s | `expect.toBe(1)` |
| V3 | Only 1 EMHASS sensor in `/config/entities` | Count of entities with `emhass_perfil_diferible` === 1 | 10s | `expect.toBe(1)` |
| V4 | After deleting 1 trip, other 2 remain visible | `getByText('UX02 Trip 1')` AND `getByText('UX02 Trip 3')` visible | 5s each | `expect.toBeVisible()` |
| V5 | After deleting 1 of 3, sensor still NON-ZERO | `attrs.power_profile_watts.some(v => v > 0) === true` | 15s polling | `expect.toBe(true)` |
| V6 | After deleting ALL, sensor goes to zeros | `attrs.power_profile_watts.every(v => v === 0)` | 15s polling | `expect.toBe(true)` |

### 8.4 Test Code Structure

```typescript
test('should verify multiple trips with no device/sensor duplication (UX-02)', async ({ page }) => {
  // Setup: Create 3 trips (mixed types)
  await createTestTrip(page, 'recurrente', getFutureIso(1, '08:00'), 50, 10, 'UX02 Trip 1', { day: '1', time: '08:00' });
  await createTestTrip(page, 'recurrente', getFutureIso(2, '10:00'), 30, 7, 'UX02 Trip 2', { day: '2', time: '10:00' });
  await createTestTrip(page, 'puntual', getFutureIso(3, '14:00'), 20, 5, 'UX02 Trip 3');

  // Allow time for 3 trips to propagate (acceptable delay for multi-trip)
  await page.waitForTimeout(5000);

  // V1: Verify 3 trips visible
  // V2: Verify 1 device in /config/devices
  // V3: Verify 1 sensor in /config/entities
  // Delete middle trip
  // V4-V6: Verify partial deletion integrity

  // Sensor checks MUST use toPass() polling, not waitForTimeout()
});
```

### 8.5 Self-Healing Loop

**Same self-healing loop as S5 — execute S5 and S6 TOGETHER in the same `make e2e` run.**

### 8.6 Known Issues

- Same as S5 (God Objects, coordinator interval).
- `waitForTimeout(5000)` after creating 3 trips is the one acceptable use of `waitForTimeout()` — multi-trip propagation takes longer.

---

## 9. Execution Constraints

### 9.1 MUST DO

- **TDD RED → GREEN → REFACTOR**: All Python changes must be preceded by a failing test
- **Code quality**: black (88 chars), isort, pylint, mypy, Google-style docstrings
- **E2E selectors**: `getByRole()` > `getByLabel()` > `getByPlaceholder()` > `getByText()` > `getByTestId()` > CSS. **XPath PROHIBITED**
- **Log format**: `%s` style — NO f-strings in log payloads
- **Self-healing**: Max 3 iterations of `make e2e` → diagnose → fix → retry before marking BLOCKED
- **Completion gate**: Stories marked COMPLETE ONLY after `make e2e` passes ALL tests (not just the story's tests, but the entire suite)

### 9.1.1 Rule: "If You Touch It, Make It SOLID" (INCREMENTAL SOLID-IZATION)

This is a **working rule**, NOT a refactoring mandate. It means:

**When you touch a function/class to make a fix:**

1. **First**: Make the minimal fix (the bug you're solving) — RED → GREEN
2. **Second**: Look at the touched function. Is it SOLID?
   - Does it have a single responsibility? (or is it doing 3+ things?)
   - Are its interfaces clean? (or are they bloated?)
   - Does it depend on concrete types or abstractions?
   - Is there duplicated logic that belongs in a helper?
3. **If NOT SOLID**: Apply a SOLID fix to that specific function/class
   - Extract a private helper method
   - Add type hints if missing
   - Break a conditional into a strategy/pattern if applicable
   - Add a docstring explaining the WHY
4. **Then**: Run checkpoint (`make test` + `make lint`)
5. **If SOLID enough**: No further action needed

**What this does NOT mean:**
- Do NOT refactor the entire TripManager or EMHASSAdapter
- Do NOT create new files just for SOLID-ization
- Do NOT change interfaces of public methods
- Do NOT add abstractions that don't improve testability immediately
- Do NOT spend more than 30 minutes on SOLID-ization of one function

**What this DOES mean:**
- Every function you modify must end up MORE SOLID than it started
- If the fix is at `trip_manager.py:1473` and that function is `async_calcular_energia_necesaria` (60+ lines with mixed responsibilities), extract the datetime parsing logic into its own private method `_parse_trip_datetime()` — this is SOLID SRP locally
- If the fix at `emhass_adapter.py:1849` touches a 200-line method, extract the coordinator data update into a private `_update_coordinator_data()` method — this is SOLID SRP locally
- The SOLID-ization is **local and surgical**, not global and sweeping

**Checkpoint impact**: After applying the SOLID-ization fix, the checkpoint must still pass. If the SOLID-ization introduces a regression, revert it and keep the minimal fix.

**SOLID certification**: The implementing agent MUST NOT self-certify SOLID-ness. After attempted SOLID-ization, a separate reviewer agent (`pr-review-toolkit:code-reviewer`) validates against objective criteria in Section 9.1.2. See Section 9.1.2 for the full Quality Gate procedure.

### 9.1.2 Objective SOLID Quality Gate (MANDATORY)

The implementing agent MUST NOT self-certify SOLID-ness. After every code fix (S1, S2, S3 Python changes), a **separate reviewer agent** must validate SOLID adherence using **objective, measurable criteria** — not opinions.

**When**: After the minimal fix is applied and SOLID-ization attempted, but BEFORE the checkpoint (`make test` + `make lint`) is considered complete.

**How**: Launch a `pr-review-toolkit:code-reviewer` subagent with the **diff** (not the full file) and these specific instructions:

```
Review the staged diff for SOLID adherence using these OBJECTIVE criteria:

1. NO GOD METHODS: No touched function exceeds 200 lines AFTER the fix
2. SINGLE RESPONSIBILITY: Each touched method has ONE clear purpose
   - Check: does the method have 3+ distinct "phases" (e.g., calculate + update + log)? → FAIL
   - Check: are there duplicated code patterns that could be extracted? → FAIL
3. TYPE HINTS: All touched function signatures have complete type hints
   - Parameters → return type
   - No "Any" type used unnecessarily (except for HA state data)
4. DIP (DEPENDENCE INVERSION): Touched code depends on abstractions, not concretions
   - Check: does it import concrete HA classes it shouldn't? → FAIL (informational)
5. NO HARDCODED STRINGS: No magic strings in touched code
   - Check: are entity names, attribute names, service names string literals? → FAIL
6. DOCSTRINGS: All touched public methods have Google-style docstrings
   - Args, Returns, Raises sections
7. NO SILENT EXCEPTIONS: No bare `except:` or `except Exception:`
   - Specific exception types only
8. NO DIRECT STATE MUTATION: Touched code does not directly mutate shared state
   - Check: any `self.coordinator.data[...] = ` in touched code? → FAIL (should use full replacement)

Pass criteria: Criteria 1, 2, 3, 7, 8 MUST pass. Criteria 4, 5, 6 are informational.
If any MUST criterion fails, the reviewer MUST list the specific line and required change.
The implementing agent MUST fix the failure and re-request review (max 2 retries).
```

**What to pass to the reviewer**:
```bash
# Pass ONLY the diff, not the full file
cd /mnt/bunker_data/ha-ev-trip-planner/ha-ev-trip-planner
git diff custom_components/ev_trip_planner/trip_manager.py
git diff custom_components/ev_trip_planner/emhass_adapter.py
```

**Failure handling**:
- If reviewer flags a SOLID violation → fix it → re-request review (max 2 retries)
- If 2 retries exhausted → proceed to fallback agent path (Section 9.1.3)

**This prevents**: The implementing agent from saying "the code is SOLID" when it is not.
**This enables**: An objective, measurable assessment that any reviewer would agree with.

### 9.1.3 SOLID Quality Gate Fallback Agent Path (MANDATORY after 3 failures)

When the SOLID Quality Gate fails after 3 total attempts (1 initial + 2 retries), the implementing agent MUST NOT escalate to a human. Instead, a **different reviewer agent** (an architect, not a code reviewer) diagnoses WHY the SOLID-ization keeps failing and provides specific fix instructions.

**Trigger**: SOLID Quality Gate has failed 3 times on the same story/fix.

**Procedure**:

1. Launch a `ralph-specum:architect-reviewer` subagent with:
   - The full diff from all 3 failed attempts
   - The reviewer's feedback for each attempt
   - The implementing agent's fix attempts for each attempt
   - These instructions:

```
You are diagnosing why SOLID-ization keeps failing for a specific code change.

Context: The implementing agent has tried 3 times to make a function SOLID but keeps failing the objective SOLID Quality Gate.

Input:
- Original buggy code (what needed fixing)
- The diff after each of 3 SOLID-ization attempts
- The reviewer feedback for each attempt (which criteria failed)
- The implementing agent's attempted fixes

Diagnosis:
1. Analyze WHY the SOLID-ization keeps failing. Is it:
   - Fundamental coupling in the existing code that prevents local extraction?
   - The function is too large and tightly coupled to split?
   - The SOLID criteria themselves are too strict for this code pattern?
   - The implementing agent is making incorrect fixes?
2. Identify the ROOT CAUSE, not symptoms.

3. Provide SPECIFIC fix instructions:
   - Not "make it more SOLID" — but EXACT lines to change
   - If the fix requires changing a different function than the one being touched → state it explicitly
   - If the fix requires accepting a known limitation (e.g., this pattern is inherently coupled) → explain why and what the acceptable degradation is
   - Include the EXACT code to add/change

4. Output format:
   - Root cause: [one sentence]
   - Why previous fixes failed: [line-by-line analysis]
   - Recommended fix: [exact code changes]
   - Acceptable limitation: [if any criteria must be relaxed and why]
```

2. The architect-reviewer outputs a diagnosis with specific fix instructions.

3. The implementing agent applies the architect's instructions and re-requests review from the original reviewer (`pr-review-toolkit:code-reviewer`).

4. If the gate passes → proceed. If it fails again → this is the FINAL attempt. The implementing agent MUST:
   - Document WHY the gate still fails
   - Document the architect's recommendations
   - Accept that the code cannot be made MORE SOLID in its current form (the God object constraint is real)
   - Proceed to checkpoint with the MINIMAL fix only (the SOLID-ization is abandoned for this story)
   - Record this in the story's progress as a known limitation

**Key principle**: The SOLID Quality Gate is aspirational, not blocking. The worst that can happen is the code stays at its current SOLID level (which is poor, but that's a known constraint — we're not refactoring God Objects). We do NOT block the entire sprint on this.

**This prevents**: Infinite loops where the implementing agent can't make God Objects SOLID and keeps trying.
**This enables**: A bounded investigation that produces a diagnosis, then moves forward.

**This prevents**: The implementing agent from saying "the code is SOLID" when it is not.
**This enables**: An objective, measurable assessment that any reviewer would agree with.

### 9.2 MUST NOT DO

- **No refactoring of TripManager or EMHASSAdapter** (beyond the specific fixes in S1, S2, and local SOLID-izations per 9.1.1)
- **No Docker** — tests run via `make e2e` which starts HA as a Python process
- **No class > 200 lines** in new code
- **No f-strings in log messages** (project convention: `%s` style)
- **No changing SOC from 20%** — this is required for non-zero sensor attributes
- **No parallel test execution** — `workers: 1` is required (single HA instance)
- **No isolated E2E test execution** — ALL E2E tests must run as a complete suite (`make e2e`), never with `--grep` or isolation. Tests share the same ephemeral HA container and sensor state. Running only a subset produces false results.

### 9.3 Completion Gates

A story is COMPLETE only when ALL of the following are true:

1. `make e2e` passes ALL tests (not just the story's tests)
2. `/tmp/logs/ha-e2e-*.log` contains no ERROR/EXCEPTION entries
3. All acceptance criteria from the validation table are verified
4. Self-healing loop has been executed (at least once)
5. Pre-flight checks pass on a second verification run

---

## 10. Self-Healing Loop — Detailed Instructions

### 10.1 Failure Classification

| Symptom | Root Cause Category | Diagnostic Action |
|---------|-------------------|-------------------|
| `Element not found` / `Target not visible` | UI locator issue | Check `test-results/*/error-context.md`, trace HTML, fix locator |
| `AssertionError: power_profile_watts is empty` | Sensor data not populated | Check HA logs for EMHASS errors, coordinator refresh issues |
| `TimeoutError: test timeout exceeded` | Slow propagation | Verify `toPass()` timeout is sufficient (15000ms), check HA startup logs |
| `TypeError: naive/aware` | Datetime fix not applied | Verify S1 fix is in place, check import of `dt_util` |
| `HA did not become ready` | Configuration error | Check `configuration.yaml`, look at HA startup log |
| `Entity not found` | Entity ID mismatch | Verify `discoverEmhassSensorEntityId()` works, check HA entity registry |

### 10.2 Log Analysis Patterns

```bash
# Python errors (most critical)
grep -i "error\|exception\|traceback" /tmp/logs/ha-e2e-*.log | tail -50

# EMHASS service calls
grep -i "emhass\|deferrable\|power_profile" /tmp/logs/ha-e2e-*.log | tail -50

# Coordinator refresh cycles
grep -i "coordinator\|async_refresh\|async_set_data" /tmp/logs/ha-e2e-*.log | tail -50

# Service call bus events
grep -i "Bus: handling" /tmp/logs/ha-e2e-*.log | tail -50

# Integration-specific events
grep -i "ev_trip_planner" /tmp/logs/ha-e2e-*.log | tail -100

# HA startup errors
tail -200 /tmp/logs/ha-e2e-*.log | grep -i "error\|warning\|failed"
```

### 10.3 Recovery Procedure

```
1. Run: make e2e 2>&1 | tee /tmp/make-e2e-output.log
2. Check exit code: echo $?
3. If exit code != 0:
   a. tail -100 /tmp/make-e2e-output.log for test failure details
   b. tail -200 /tmp/logs/ha-e2e-*.log for HA errors
   c. Look in test-results/*/error-context.md for Playwright diagnostics
   d. Apply ONE fix
   e. Re-run: make e2e
   f. Repeat max 3 times
4. If still failing after 3 iterations: mark BLOCKED with diagnosis evidence
```

---

## 11. File Inventory

### 11.1 Files to Modify

| File | Story | Changes |
|------|-------|---------|
| `custom_components/ev_trip_planner/trip_manager.py:1473` | S1 | Replace `datetime.strptime` with `dt_util.parse_datetime` |
| `custom_components/ev_trip_planner/emhass_adapter.py:1849-1853` | S2 | Replace in-place mutation with full dict replacement |
| `custom_components/ev_trip_planner/emhass_adapter.py:1951-1954` | S2 | Replace in-place mutation with full dict replacement |
| `tests/ha-manual/configuration.yaml` | S3 | Add logger debug config |
| `scripts/run-e2e.sh` | S3 | Add timestamped logs, failure dump |
| `playwright.config.ts:18` | S3 | Remove `globalTeardown` reference |
| `tests/e2e/emhass-sensor-updates.spec.ts` | S3, S4, S5, S6 | Fix hardcoded IDs/dates, replace waitForTimeout, add helpers, add tests |

### 11.2 Files to Create

| File | Story | Content |
|------|-------|---------|
| *(new regression tests inline in emhass-sensor-updates.spec.ts)* | S4 | Race condition regression tests |

### 11.3 Files to Read (but not modify)

| File | Purpose |
|------|---------|
| `tests/e2e/trips-helpers.ts` | Existing helpers (navigateToPanel, createTestTrip, deleteTestTrip, cleanupTestTrips) |
| `tests/e2e/zzz-integration-deletion-cleanup.spec.ts` | `discoverEmhassSensorEntityId` and `getFutureIso` source |
| `tests/test_trip_manager_datetime_tz.py` | Existing datetime regression test |
| `custom_components/ev_trip_planner/coordinator.py` | Understand coordinator data flow |
| `custom_components/ev_trip_planner/emhass_adapter.py` | Understand dual-writer pattern |

---

## 12. Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| Datetime fix changes behavior of existing unit tests | HIGH | Run `make test` before and after; compare output |
| Coordinator fix breaks sensor updates | HIGH | Verify with `make e2e` after each change |
| Test infrastructure changes break test discovery | MEDIUM | Run `npx playwright test --list` after changes |
| `toPass()` replaces `waitForTimeout()` in a test that actually needs the delay | MEDIUM | UX-02 multi-trip delay (5000ms) is explicitly allowed |
| HA startup fails in E2E environment | HIGH | Verify `configuration.yaml` is valid before each run |
| SOC=20% not applied in test environment | MEDIUM | Verify in pre-flight checks |
| Test state contamination between runs | MEDIUM | Each test's `beforeEach` calls `cleanupTestTrips()` |
| Ralph context overflow (seen in previous runs) | HIGH | Keep stories focused; avoid reading entire files unnecessarily |

---

## 13. References

| Reference | Relevance |
|-----------|-----------|
| `research.md` | Full SOLID analysis, race condition design, log capture patterns |
| `2-1-e2e-ux01-sensor-sync.md` | Original story spec (template for S5) |
| `2-2-e2e-ux02-multiple-trips-no-duplication.md` | Original story spec (template for S6) |
| `sprint-change-proposal-e2e-ux-tests-2026-04-22.md` | Detailed test specifications |
| `tests/e2e/emhass-sensor-updates.spec.ts` | Existing test code (lines 560-666 have UX-01/UX-02) |
| `tests/e2e/trips-helpers.ts` | Shared helper functions |
| `scripts/run-e2e.sh` | E2E test runner script |
| `tests/ha-manual/configuration.yaml` | HA configuration for E2E tests |
| `playwright.config.ts` | Playwright test configuration |
| `tests/test_trip_manager_datetime_tz.py` | Existing datetime regression test |
| `.github/copilot-instructions.md` | Project conventions (TDD, selectors, code style) |
| `docs/CODEGUIDELINESia.md` | TDD workflow, coverage requirements |

---

## 14. Completion Checklist

- [ ] S1: Datetime fix applied at line 1473 in trip_manager.py
- [ ] S1: Unit tests pass (`make test`)
- [ ] S1: No pylint/mypy/ruff violations (`make lint`)
- [ ] S2: In-place coordinator mutations replaced with full dict replacements
- [ ] S2: Unit tests pass (`make test`)
- [ ] S2: No more `coordinator.data[...]` in-place mutations in emhass_adapter.py
- [ ] S3: Logger config added to configuration.yaml
- [ ] S3: Timestamped logs in run-e2e.sh
- [ ] S3: No hardcoded dates in test files
- [ ] S3: No hardcoded entity IDs in test files
- [ ] S3: `waitForTimeout()` replaced with `toPass()` (except UX-02 multi-trip delay)
- [ ] S3: `globalTeardown` removed from playwright.config.ts
- [ ] S4: Race condition regression tests added
- [ ] S4: S4 tests pass (`make e2e`)
- [ ] S5: All 6 acceptance criteria verified
- [ ] S5: Self-healing loop executed
- [ ] S6: All 6 acceptance criteria verified
- [ ] S6: Self-healing loop executed
- [ ] FINAL: `make e2e` passes ALL tests
- [ ] FINAL: `/tmp/logs/ha-e2e-*.log` has no ERROR/EXCEPTION entries
- [ ] FINAL: Second verification run passes
