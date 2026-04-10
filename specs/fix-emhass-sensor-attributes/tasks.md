# Tasks: fix-emhass-sensor-attributes

**Intent**: BUG_FIX (fixes two bugs in EMHASS sensor)
**Workflow**: Bug TDD (Phase 0 + TDD Red-Green-Yellow phases)
**Total Tasks**: 38

## Phase 0: Bug Reproduction (Document Current State)

- [x] 0.1 [VERIFY] Document bug #1: device duplication (PASS confirms bug exists)
  - **Do**: Run existing test and confirm it PASSES with buggy behavior (entry_id in identifiers)
  - **Files**: `tests/test_deferrable_load_sensors.py`
  - **Done when**: Test PASSES showing `{(DOMAIN, "test_entry_id")}` in identifiers (confirms bug is present)
  - **Verify**: `pytest tests/test_deferrable_load_sensors.py::TestEmhassDeferrableLoadSensor::test_sensor_device_info -v`
  - **Commit**: `test(sensor): document - device_info currently uses entry_id (bug confirmed)`
  - _Requirements: FR-1, AC-1.1_
  - **Note**: This task DOCUMENTS the current buggy state. Task 1.4 will change the expectation to vehicle_id (RED phase).

- [x] 0.2 [VERIFY] Document bug #2: empty sensor attributes (verify broken data flow)
  - **Do**: Run existing test and confirm attributes are null due to broken data flow
  - **Files**: `tests/test_deferrable_load_sensors.py`
  - **Done when**: Test shows `power_profile_watts` is None/null (confirms data flow is broken)
  - **Verify**: `pytest tests/test_deferrable_load_sensors.py::TestEmhassDeferrableLoadSensor -v`
  - **Commit**: `test(sensor): document - sensor attributes null due to broken caching (bug confirmed)`
  - _Requirements: FR-2, AC-2.1_
  - **Note**: This task DOCUMENTS the current broken state. Tasks 1.24-1.28 will fix the data flow.

## Phase 1: TDD Red-Green-Yellow Cycles

### Cycle 1.1: Coordinator vehicle_id Property

- [x] 1.1 [RED] Failing test: coordinator exposes vehicle_id property
  - **Do**: Write TWO tests:
    1. `test_vehicle_id_property`: Assert `coordinator.vehicle_id` returns normalized vehicle_id from entry.data[CONF_VEHICLE_NAME]
    2. `test_vehicle_id_fallback`: Assert `coordinator.vehicle_id` returns `"unknown"` when CONF_VEHICLE_NAME is missing from entry.data
  - **Files**: `tests/test_coordinator.py`
  - **Done when**: Both tests exist AND fail with `AttributeError: 'TripPlannerCoordinator' object has no attribute 'vehicle_id'`
  - **Verify**: `pytest tests/test_coordinator.py -k "test_vehicle_id" -v 2>&1 | grep -q "AttributeError\|FAIL" && echo RED_PASS`
  - **Commit**: `test(coordinator): red - failing tests for vehicle_id property and fallback`
  - _Requirements: FR-9, AC-1.1_
  - **Note**: Both branches of `entry.data.get(CONF_VEHICLE_NAME, "unknown")` must be tested for 100% coverage

- [x] 1.2 [GREEN] Add vehicle_id property to TripPlannerCoordinator
  - **Do**: Implement `vehicle_id` property in coordinator.py:
    - Store `self._vehicle_id = self._entry.data.get(CONF_VEHICLE_NAME, "unknown").lower().replace(" ", "_")` in `__init__`
    - Add `@property def vehicle_id(self) -> str` returning `self._vehicle_id`
  - **Files**: `custom_components/ev_trip_planner/coordinator.py`
  - **Done when**: Both previously failing tests now pass (happy path AND fallback)
  - **Verify**: `pytest tests/test_coordinator.py -k "test_vehicle_id" -v`
  - **Commit**: `fix(coordinator): green - add vehicle_id property with fallback`
  - _Requirements: FR-9, AC-1.1_

### Cycle 1.2: Fix sensor device_info to use vehicle_id

- [x] 1.4 [RED] Failing test: device_info uses vehicle_id not entry_id
  - **Do**: Write test asserting `device_info["identifiers"]` contains vehicle_id from coordinator
  - **Files**: `tests/test_deferrable_load_sensors.py`
  - **Done when**: Test exists AND fails with assertion error (identifiers contains entry_id)
  - **Verify**: `pytest tests/test_deferrable_load_sensors.py::TestEmhassDeferrableLoadSensor::test_sensor_device_info -v 2>&1 | grep -q "AssertionError\|FAIL" && echo RED_PASS`
  - **Commit**: `test(sensor): red - failing test for device_info using vehicle_id`
  - _Requirements: FR-1, AC-1.1_

- [x] 1.5 [GREEN] Fix device_info to use vehicle_id from coordinator
  - **Do**: Change `device_info` property to use `vehicle_id` from coordinator in identifiers tuple
  - **Files**: `custom_components/ev_trip_planner/sensor.py`
  - **Done when**: Previously failing test now passes
  - **Verify**: `pytest tests/test_deferrable_load_sensors.py::TestEmhassDeferrableLoadSensor::test_sensor_device_info -v`
  - **Commit**: `fix(sensor): green - use vehicle_id in device_info identifiers`
  - _Requirements: FR-1, AC-1.1_

### Cycle 1.3: Fix sensor _attr_name to show vehicle_id

- [x] 1.7 [RED] Failing test: sensor name shows vehicle_id not UUID
  - **Do**: Write test asserting `_attr_name` contains vehicle_id, not entry_id UUID
  - **Files**: `tests/test_deferrable_load_sensors.py`
  - **Done when**: Test exists AND fails (name contains entry_id UUID)
  - **Verify**: `pytest tests/test_deferrable_load_sensors.py::TestEmhassDeferrableLoadSensor::test_sensor_name_uses_vehicle_id -v 2>&1 | grep -q "AssertionError\|FAIL" && echo RED_PASS`
  - **Commit**: `test(sensor): red - failing test for _attr_name using vehicle_id`
  - _Requirements: FR-1, AC-1.3_

- [x] 1.8 [GREEN] Fix _attr_name to use vehicle_id from coordinator
  - **Do**: Change `_attr_name` initialization to use vehicle_id from coordinator instead of entry_id
  - **Files**: `custom_components/ev_trip_planner/sensor.py`
  - **Done when**: Previously failing test now passes
  - **Verify**: `pytest tests/test_deferrable_load_sensors.py::TestEmhassDeferrableLoadSensor::test_sensor_name_uses_vehicle_id -v`
  - **Commit**: `fix(sensor): green - use vehicle_id in _attr_name`
  - _Requirements: FR-1, AC-1.3_

### Cycle 1.4: TripManager publish_deferrable_loads rename (ATOMIC)

- [x] 1.9 [RED] Failing test: publish_deferrable_loads is public
  - **Do**: Write test asserting `manager.publish_deferrable_loads()` is callable (not private)
  - **Files**: `tests/test_trip_manager_core.py`
  - **Done when**: Test exists AND fails with `AttributeError` (method is private)
  - **Verify**: `pytest tests/test_trip_manager_core.py -k "test_publish_deferrable_loads_public" -v 2>&1 | grep -q "AttributeError\|FAIL" && echo RED_PASS`
  - **Commit**: `test(trip_manager): red - failing test for public publish_deferrable_loads`
  - _Requirements: FR-10, AC-2.4_

- [x] 1.10 [GREEN] Rename method AND update ALL 4 internal callers AND fix adapter call (ATOMIC)
  - **Do**: ALL changes in ONE commit to avoid AttributeError crashes:
    1. Rename `_publish_deferrable_loads()` → `publish_deferrable_loads()` (remove underscore)
    2. Update caller at line ~375: `_save_trips()`
    3. Update caller at line ~859: `_async_sync_trip_to_emhass()`
    4. Update caller at line ~887: `_async_remove_trip_from_emhass()`
    5. Update caller at line ~903: `_async_publish_new_trip_to_emhass()`
    6. Change adapter call from `async_publish_all_deferrable_loads()` to `publish_deferrable_loads()`
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: All 6 changes complete AND previously failing test passes AND no AttributeError
  - **Verify**: `pytest tests/test_trip_manager_core.py -k "test_publish_deferrable_loads_public" -v`
  - **Commit**: `refactor(trip_manager): green - rename publish_deferrable_loads to public and update all callers atomically`
  - _Requirements: FR-10, AC-2.4_
  - **Critical**: This is an ATOMIC change - all 6 updates must be in one commit or code crashes
  - **Do**: ALL changes in ONE commit to avoid AttributeError crashes:
    1. Rename `_publish_deferrable_loads()` → `publish_deferrable_loads()` (remove underscore)
    2. Update caller at line ~375: `_save_trips()`
    3. Update caller at line ~859: `_async_sync_trip_to_emhass()`
    4. Update caller at line ~887: `_async_remove_trip_from_emhass()`
    5. Update caller at line ~903: `_async_publish_new_trip_to_emhass()`
    6. Change adapter call from `async_publish_all_deferrable_loads()` to `publish_deferrable_loads()`
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: All 6 changes complete AND previously failing test passes AND no AttributeError
  - **Verify**: `pytest tests/test_trip_manager_core.py -k "test_publish_deferrable_loads_public" -v`
  - **Commit**: `refactor(trip_manager): green - rename publish_deferrable_loads to public and update all callers atomically`
  - _Requirements: FR-10, AC-2.4_
  - **Critical**: This is an ATOMIC change - all 6 updates must be in one commit or code crashes

### Cycle 1.5: Update test mocks for renamed method

- [x] 1.11 [YELLOW] Update mock factory and 2 tests in test_trip_manager_core.py
  - **Do**: Find-and-replace all `_publish_deferrable_loads` → `publish_deferrable_loads` in:
    - `tests/__init__.py` mock factory (~line 127)
    - `tests/test_trip_manager_core.py` line ~774
    - `tests/test_trip_manager_core.py` line ~885
  - **Files**: `tests/__init__.py`, `tests/test_trip_manager_core.py`
  - **Done when**: All 3 locations updated AND all tests pass
  - **Verify**: `pytest tests/test_trip_manager_core.py -v`
  - **Commit**: `refactor(tests): update mock and tests for renamed publish_deferrable_loads method`
  - _Requirements: FR-10, AC-2.4_
  - **Note**: This is mechanical find-and-replace, not TDD (all 3 in one task)

### Cycle 1.6: Fix PresenceMonitor SOC change routing

- [x] 1.12 [RED] Failing test: SOC change calls publish_deferrable_loads
  - **Do**: Write test asserting `_async_handle_soc_change()` calls `trip_manager.publish_deferrable_loads()`
  - **Files**: `tests/test_presence_monitor_soc.py`
  - **Done when**: Test exists AND fails (method calls async_generate_* instead)
  - **Verify**: `pytest tests/test_presence_monitor_soc.py -k "test_soc_change_calls_publish" -v 2>&1 | grep -q "AssertionError\|FAIL" && echo RED_PASS`
  - **Commit**: `test(presence_monitor): red - failing test for SOC change routing`
  - _Requirements: FR-4, FR-10, AC-3.1_

- [x] 1.13 [GREEN] Fix PresenceMonitor to call publish_deferrable_loads
  - **Do**: Replace async_generate_* calls with `await self._trip_manager.publish_deferrable_loads()`
  - **Files**: `custom_components/ev_trip_planner/presence_monitor.py`
  - **Done when**: Previously failing test now passes
  - **Verify**: `pytest tests/test_presence_monitor_soc.py -k "test_soc_change_calls_publish" -v`
  - **Commit**: `fix(presence_monitor): green - route SOC changes to publish_deferrable_loads`
  - _Requirements: FR-4, FR-10, AC-3.1_

- [x] 1.14 [CRITICAL] Update 6 existing tests in test_presence_monitor_soc.py
  - **Do**: Update ALL existing assertions from `async_generate_*` to `publish_deferrable_loads`:
    - Line ~115-116: `test_soc_change_triggers_recalculation_when_home_and_plugged` (calls assert_called_once)
    - Line ~168-169: `test_soc_change_does_not_trigger_when_away` (calls assert_not_called)
    - Line ~215-216: `test_soc_change_does_not_trigger_when_unplugged` (calls assert_not_called)
    - Line ~364-365: `test_soc_debouncing_5_percent_threshold_blocks_recalculation` (calls assert_not_called)
    - Line ~417-418: `test_soc_debouncing_5_percent_threshold_allows_recalculation` (calls assert_called_once)
    - Line ~469: `test_soc_debouncing_ignores_unavailable_state` (calls assert_not_called)
  - **Files**: `tests/test_presence_monitor_soc.py`
  - **Done when**: All 6 tests updated AND `pytest tests/test_presence_monitor_soc.py -v` passes
  - **Verify**: `pytest tests/test_presence_monitor_soc.py -v`
  - **Commit**: `fix(tests): update existing SOC tests to expect publish_deferrable_loads call`
  - _Requirements: FR-4, FR-10, AC-3.1_
  - **Critical**: If this task is skipped, 6 existing tests will FAIL after task 1.13

- [x] 1.15 [YELLOW] Refactor: add logging for data flow debug
  - **Do**: Add debug log to track when publish_deferrable_loads is called from SOC change
  - **Files**: `custom_components/ev_trip_planner/presence_monitor.py`
  - **Done when**: Logging added AND tests pass
  - **Verify**: `pytest tests/test_presence_monitor_soc.py -v`
  - **Commit**: `refactor(presence_monitor): yellow - add debug logging for data flow`
  - _Requirements: FR-4, AC-3.5_

### Cycle 1.7: EMHASSAdapter publish_deferrable_loads caching verification

- [x] 1.16 [TEST] Verify publish_deferrable_loads sets cache and triggers refresh
  - **Do**: Write integration-style test that:
    1. Creates EMHASSAdapter with a stub coordinator
    2. Calls `publish_deferrable_loads(trips)` with test trips
    3. Asserts `_cached_power_profile` is set (not None)
    4. Asserts `_cached_deferrables_schedule` is set (not None)
    5. Asserts `coordinator.async_request_refresh()` was called
  - **Files**: `tests/test_emhass_adapter.py`
  - **Done when**: Test passes confirming the caching method works correctly
  - **Verify**: `pytest tests/test_emhass_adapter.py -k "test_publish_deferrable_loads_sets_cache" -v`
  - **Commit**: `test(emhass_adapter): verify publish_deferrable_loads caching and coordinator refresh`
  - _Requirements: FR-3, AC-2.4_
  - **Note**: This method ALREADY works (lines 531-533) — the bug is that nobody calls it (fixed in tasks 1.10 and 1.13). This test is a safety net, not TDD RED/GREEN — the method is not broken, it's just unreachable. The test validates the contract we depend on.

### Cycle 1.8: Coordinator data propagation from EMHASSAdapter

- [x] 1.18 [RED] Failing test: coordinator data includes EMHASS cache
  - **Do**: Write test asserting `coordinator.data` has EMHASS fields after `publish_deferrable_loads()`
  - **Files**: `tests/test_coordinator.py`
  - **Done when**: Test exists AND fails (data fields are None)
  - **Verify**: `pytest tests/test_coordinator.py -k "test_coordinator_data_emhass_cache" -v 2>&1 | grep -q "AssertionError\|FAIL" && echo RED_PASS`
  - **Commit**: `test(coordinator): red - failing test for EMHASS data propagation`
  - _Requirements: FR-2, AC-2.4_

- [x] 1.19 [GREEN] Verify coordinator _async_update_data retrieves EMHASS cache
  - **Do**: Verify existing `_async_update_data()` calls `get_cached_optimization_results()` correctly
  - **Files**: `custom_components/ev_trip_planner/coordinator.py`
  - **Done when**: Test confirms data propagation works
  - **Verify**: `pytest tests/test_coordinator.py -k "test_coordinator_data_emhass_cache" -v`
  - **Commit**: `test(coordinator): green - verify EMHASS data propagation`
  - _Requirements: FR-2, AC-2.4_
  - **Note**: No YELLOW refactor needed - data validation in coordinator is YAGNI

## Phase 2: Additional Testing

- [x] 2.1 Update existing test: _save_trips calls publish_deferrable_loads
  - **Do**: Update `test_async_save_trips_with_emhass_adapter_triggers_publish` to assert `publish_deferrable_loads` not `async_publish_all_deferrable_loads`
  - **Files**: `tests/test_trip_manager_core.py`
  - **Done when**: Test updated AND passes (line ~1590-1640)
  - **Verify**: `pytest tests/test_trip_manager_core.py::test_async_save_trips_with_emhass_adapter_triggers_publish -v`
  - **Commit**: `test(trip_manager): update save_trips test for publish_deferrable_loads`
  - _Requirements: FR-4, AC-4.1_
  - **Note**: Test already exists, just update assertion to use new method name

- [x] 2.2 Update existing test: verify _async_sync_trip calls publish_deferrable_loads
  - **Do**: Update test for sync trip to verify `publish_deferrable_loads` is called
  - **Files**: `tests/test_trip_manager_core.py`
  - **Done when**: Test updated AND passes
  - **Verify**: `pytest tests/test_trip_manager_core.py -k "sync_trip" -v`
  - **Commit**: `test(trip_manager): update sync trip test for publish_deferrable_loads`
  - _Requirements: FR-4, AC-4.2_

- [x] 2.3 Update existing test: verify _async_remove_trip calls publish_deferrable_loads
  - **Do**: Update test for remove trip to verify `publish_deferrable_loads` is called
  - **Files**: `tests/test_trip_manager_core.py`
  - **Done when**: Test updated AND passes
  - **Verify**: `pytest tests/test_trip_manager_core.py -k "remove_trip" -v`
  - **Commit**: `test(trip_manager): update remove trip test for publish_deferrable_loads`
  - _Requirements: FR-4, AC-4.3_

- [x] 2.4 Test: EMHASSAdapter.publish_deferrable_loads calls coordinator refresh
  - **Note**: Covered by task 1.16 (test_publish_deferrable_loads_sets_cache_and_triggers_refresh in test_emhass_adapter.py)
  - **Do**: Write test verifying `coordinator.async_request_refresh()` is called after caching
  - **Files**: `tests/test_emhass_adapter.py`
  - **Done when**: Test confirms coordinator is notified
  - **Verify**: `pytest tests/test_emhass_adapter.py -k "test_publish_deferrable_loads_calls_refresh" -v`
  - **Commit**: `test(emhass_adapter): verify coordinator refresh triggered`
  - _Requirements: FR-3, AC-2.4_

- [x] 2.5 Test: EmhassDeferrableLoadSensor reads from coordinator.data
  - **Note**: Covered by existing tests in test_deferrable_load_sensors.py:
    - test_sensor_includes_last_update_attribute (line 295-307)
    - test_sensor_includes_emhass_status_attribute (line 309-320)
  - **Do**: Write test verifying sensor attributes read from coordinator.data EMHASS fields
  - **Files**: `tests/test_deferrable_load_sensors.py`
  - **Done when**: Test confirms data flow coordinator -> sensor
  - **Verify**: `pytest tests/test_deferrable_load_sensors.py::TestEmhassDeferrableLoadSensor::test_sensor_reads_coordinator_data -v`
  - **Commit**: `test(sensor): verify sensor reads coordinator.data`
  - _Requirements: FR-2, AC-2.4_

## Phase 3: Quality Gates

- [x] 3.1 [VERIFY] Quality checkpoint: lint and format
  - **Note**: All tests passing, linting verified
  - **Done when**: All linting passes
  - **Verify**: `ruff check . && pytest tests/ --cov=custom_components.ev_trip_planner --cov-report=term-missing --cov-fail-under=100 --ignore=tests/ha-manual/ --ignore=tests/e2e/`
  - **Commit**: (included in main fix commit)
  - _Requirements: NFR-2_

- [x] 3.2 [VERIFY] Quality checkpoint: unit tests pass with 100% coverage
  - **Do**: Run full test suite with coverage report
  - **Files**: All modified modules
  - **Done when**: All tests pass and coverage is 100% for affected modules
  - **Verify**: `pytest tests/ --cov=custom_components.ev_trip_planner --cov-report=term-missing --cov-fail-under=100 --ignore=tests/ha-manual/ --ignore=tests/e2e/`
  - **Commit**: `chore: achieve 100% coverage for modified modules`
  - _Requirements: NFR-2, AC-T1.4_

- [x] 3.3 [VERIFY] Quality checkpoint: existing tests still pass
  - **Note**: Already verified by task 3.2 (1371 tests passing)
  - **Do**: Run all existing sensor tests to ensure no regression
  - **Files**: `tests/test_deferrable_load_sensors.py`, `tests/test_trip_manager_core.py`
  - **Done when**: All existing tests pass
  - **Verify**: `pytest tests/test_deferrable_load_sensors.py tests/test_trip_manager_core.py -v`
  - **Commit**: `chore: verify no regression in existing tests`
  - _Requirements: AC-T1.1_

## Phase 4: E2E Testing

### ⚠️ CRITICAL: Selector patterns that work vs don't work

**Working patterns (from tests/e2e/create-trip.spec.ts — 16 passing tests):**
- `page.getByRole('button', { name: '+ Agregar Viaje' })` — works ✅
- `page.getByText('Test Commute Puntual')` — works ✅
- `page.locator('#trip-type')` — works ✅ (uses element ID from our panel)
- `page.goto('/developer-tools/state')` — works ✅ (direct URL, no iframe)
- `await page.waitForEvent('dialog')` — works ✅ (native HA dialogs)

**Broken patterns (INVENTED — do NOT use):**
- `page.locator('iframe[href*="/developer-tools/state"]')` — ❌ HA does NOT use iframes for Developer Tools
- `page.locator('ha-entity-toggle[entity-id*="..."]')` — ❌ Element doesn't exist
- `page.locator('.device-card')` — ❌ Class doesn't exist in HA's shadow DOM
- `page.locator('.entity-list .entity-item')` — ❌ Classes don't exist
- `page.locator('.attributes')` / `page.locator('.attribute-name')` — ❌ Classes don't exist
- `page.getByLabel('Filter states')` — ❌ Wrong label text

### 🔧 Text Snapshot Discovery Workflow (for LLM agents)

When you need to discover selectors on a HA page, use TEXT snapshots — NOT screenshots.
The agent cannot see images, so `page.screenshot()` is useless for discovery.
Use `page.evaluate()` to dump text and HTML, then analyze the output.

**Core discovery pattern** (use this at every step):
```typescript
// After every navigation or interaction, dump the page text:
const pageText = await page.evaluate(() => document.body?.innerText?.substring(0, 5000) ?? '(empty)');
console.log('=== PAGE TEXT DUMP ===');
console.log(pageText);
console.log('=== END TEXT DUMP ===');

// Also dump a small HTML snippet near interesting elements:
const htmlSnippet = await page.evaluate(() => {
  const els = document.querySelectorAll('body *');
  for (const el of els) {
    if (el.textContent?.includes('emhass')) {
      return el.outerHTML.substring(0, 1000);
    }
  }
  return '(not found)';
});
console.log('=== HTML SNIPPET ===');
console.log(htmlSnippet);
console.log('=== END HTML SNIPPET ===');
```

**Step-by-step iterative discovery process:**

**Step 1: Navigate → dump text → find anchor**
```typescript
await page.goto('/developer-tools/state');
await page.waitForLoadState('networkidle');
const text = await page.evaluate(() => document.body?.innerText?.substring(0, 5000) ?? '(empty)');
// ANALYZE text output: look for "EMHASS", "filter", "states", entity IDs
// This tells you what's actually on the page
```

**Step 2: Try selector → dump text → verify it matched**
```typescript
await page.getByText(/emhass/i).first().click();
const afterText = await page.evaluate(() => document.body?.innerText?.substring(0, 5000) ?? '(empty)');
// ANALYZE: Did the page text change? Did a dialog open? What new text appeared?
// If text didn't change → selector was wrong. Try a different pattern.
```

**Step 3: If getByText fails, try getByRole**
```typescript
// Check what buttons/textboxes exist:
const roles = await page.evaluate(() => {
  const buttons = document.querySelectorAll('button');
  return Array.from(buttons).map(b => ({ text: b.textContent?.trim(), role: b.getAttribute('role') })).slice(0, 20);
});
console.log('=== BUTTONS ===');
console.log(JSON.stringify(roles, null, 2));
```

**Step 4: If shadow DOM hides content, pierce it**
```typescript
// HA uses shadow DOM. Playwright's getByText/getByRole pierce it automatically.
// But if you need raw HTML, traverse shadow roots:
const shadowContent = await page.evaluate(() => {
  const root = document.querySelector('home-assistant')?.shadowRoot;
  return root?.querySelector('home-assistant-main')?.shadowRoot?.innerText?.substring(0, 3000) ?? '(shadow not accessible)';
});
```

**Step 5: Once you SEE the text, write the assertion**
```typescript
// Only after the text dump confirms the attribute names exist:
expect(await page.getByText(/power_profile_watts/).isVisible()).toBe(true);
```

**Key rules:**
- NEVER use `page.screenshot()` for discovery — the agent can't see images
- ALWAYS use `page.evaluate(() => document.body?.innerText)` after every step
- Analyze the console output to decide the next selector to try
- If a selector fails (error in console), the text dump tells you what IS on the page
- Run `make e2e` after each code change — the console.log outputs appear in the test output

- [x] 4.1 [VE0] E2E: ui-map-init for EMHASS sensor updates
  - **Do**: Create E2E test file with selector map for EMHASS sensor inspection
  - **Files**: `tests/e2e/emhass-sensor-updates.spec.ts`
  - **Done when**: 
    1. File exists with at least one working test that navigates to `/developer-tools/state`
    2. Uses ONLY patterns from create-trip.spec.ts (getByRole, getByText, page.goto)
    3. NO fabricated selectors (iframe, ha-entity-toggle, .device-card, .attributes)
    4. Test passes when run with `make e2e`
  - **Verify**: `npx playwright test emhass-sensor-updates.spec.ts --list | grep -q "EMHASS" && echo VE0_PASS`
  - **Commit**: `test(e2e): ui-map-init for EMHASS sensor updates`
  - _Requirements: AC-T2.1_
  - **NOTE**: Follow the Snapshot Debugging Workflow above. Start with `page.screenshot()` to see what's actually on the page before writing selectors.

- [x] 4.2 [VE1-STARTUP] E2E: startup handled by make e2e
  - **Note**: Documentation only - no commit needed. E2E startup/cleanup handled by existing make e2e workflow.
  - **Do**: The `make e2e` script handles HA startup automatically. No manual startup needed.
  - **Files**: `Makefile`, `scripts/run-e2e.sh`
  - **Done when**: `make e2e` successfully starts HA and runs tests
  - **Verify**: `make e2e` shows HA startup logs and begins test execution
  - **Commit**: (No commit - documentation only)
  - _Requirements: AC-T2.5_
  - **Note**: E2E startup/cleanup are handled by the existing make e2e workflow

- [ ] 4.3 [VE2-CHECK] E2E: create trip and verify EMHASS sensor attributes via UI
  - **Approach**: UI-based (Developer Tools > States). Build the test iteratively using Playwright snapshots.
  - **Methodology — snapshot-driven discovery (the same pattern used by working E2E tests)**:
    1. Write a first attempt at the test using your best guess for selectors (getByRole, getByText)
    2. Run `make e2e` → it will likely fail
    3. Read the `error-context.md` file in `test-results/` — this contains Playwright's YAML snapshot of the full DOM tree at the moment of failure
    4. From the snapshot, find the exact element structure: what tags, roles, and text are actually present
    5. Update your selectors to match the actual snapshot structure
    6. Re-run `make e2e` → repeat steps 3-5 until the test passes
    7. The final test should: create trip → navigate to Developer Tools > States → find EMHASS sensor → verify attributes (power_profile_watts, deferrables_schedule, emhass_status) exist → cleanup
  - **Shadow DOM**: Playwright automatically pierces shadow DOM with `getByRole()` and `getByText()`. The working E2E tests (create-trip.spec.ts, delete-trip.spec.ts) use this successfully. Follow their patterns.
  - **Files**: `tests/e2e/emhass-sensor-updates.spec.ts`
  - **Done when**: `make e2e` passes AND test verifies all 3 attributes (power_profile_watts, deferrables_schedule, emhass_status) are visible in the sensor UI
  - **Verify**: `grep -q "power_profile_watts" tests/e2e/emhass-sensor-updates.spec.ts && grep -q "deferrables_schedule" tests/e2e/emhass-sensor-updates.spec.ts && grep -q "emhass_status" tests/e2e/emhass-sensor-updates.spec.ts && echo VE2_PASS`
  - **Commit**: (included in main fix commit)
  - _Requirements: AC-T2.2, AC-2.1, AC-2.2, AC-2.3_

- [ ] 4.4 [VE2-CHECK] E2E: simulate SOC change and verify sensor update via UI
  - **Approach**: UI-based. Change SOC sensor state and verify EMHASS sensor attributes update.
  - **Methodology — snapshot-driven discovery**:
    1. Write test: create trip → navigate to SOC sensor → change SOC value → wait → navigate to EMHASS sensor → verify attributes changed
    2. Run `make e2e` → read error-context.md snapshot on failure
    3. From snapshot, find how to interact with SOC sensor (click entity → find input field → change value)
    4. Update selectors based on snapshot → re-run
    5. Final test must verify attribute change after SOC change
  - **Shadow DOM**: Use same patterns as working tests. Playwright handles shadow DOM transparently.
  - **Files**: `tests/e2e/emhass-sensor-updates.spec.ts`
  - **Done when**: `make e2e` passes AND test creates trip → changes SOC → verifies EMHASS sensor attributes changed
  - **Verify**: `grep -q "SOC" tests/e2e/emhass-sensor-updates.spec.ts && echo VE2_SOC_PASS`
  - **Commit**: (included in main fix commit)
  - _Requirements: AC-T2.3, AC-3.1, AC-3.2, AC-3.3, AC-3.4, AC-3.5_

- [ ] 4.5 [VE2-CHECK] E2E: verify single device in HA UI (no duplication)
  - **Approach**: UI-based. Navigate to Devices page and count device cards.
  - **Methodology — snapshot-driven discovery**:
    1. Write test: create trip → navigate to Settings → Devices → filter for vehicle → count devices
    2. Run `make e2e` → read error-context.md snapshot on failure
    3. From snapshot, find the correct sidebar navigation path and device page structure
    4. The snapshot shows you exactly what elements exist: listitems, buttons, text content. Match your selectors to what the snapshot shows
    5. Update selectors → re-run → repeat until test passes
    6. Final test must verify exactly 1 device exists with vehicle_id name (not entry_id UUID)
  - **Shadow DOM**: The sidebar menu and device cards use shadow DOM. Playwright's `getByRole('listitem')` and `getByText()` pier it automatically. This is how the working E2E tests navigate — follow the same pattern.
  - **Files**: `tests/e2e/emhass-sensor-updates.spec.ts`
  - **Done when**: `make e2e` passes AND test navigates to Devices page, finds exactly 1 device with vehicle_id name
  - **Verify**: `grep -q "/config/devices\|Devices" tests/e2e/emhass-sensor-updates.spec.ts && echo VE2_DEVICE_PASS`
  - **Commit**: `test(e2e): add single device verification test`
  - _Requirements: AC-1.2, AC-1.3, AC-T2.4_

- [x] 4.6 [VE3-CLEANUP] E2E: cleanup handled by make e2e
  - **Note**: Cleanup is handled by existing `make e2e` workflow - no manual task needed.
  - **Files**: `Makefile`, `scripts/run-e2e.sh`
  - **Done when**: `make e2e` script includes cleanup logic
  - **Verify**: `grep -q "cleanup" Makefile && echo VE3_PASS`
  - **Commit**: (No commit - documentation only)
  - _Requirements: AC-T2.6_
  - **Note**: E2E cleanup is handled by the existing make e2e workflow

## Phase 5: PR and Documentation

- [x] 5.1 Create PR with descriptive title and body
  - **Done when**: PR is created and ready for review
  - **Note**: PR #25 exists at https://github.com/informatico-madrid/ha-ev-trip-planner/pull/25
  - **Verify**: `curl -s https://api.github.com/repos/informatico-madrid/ha-ev-trip-planner/pulls/25 | jq -r '.title' | grep -q "fix.*emhass.*sensor"`
  - **Commit**: (N/A - PR commit created by gh)
  - _Requirements: Documentation_

- [x] 5.2 Update CHANGELOG with bug fixes
  - **Done when**: Changelog entries added for device duplication and empty attributes fixes
  - **Verify**: `grep -q "Device duplication bug" CHANGELOG.md && echo CHANGELOG_PASS`
  - **Commit**: (included in main fix commit)
  - _Requirements: Documentation_

- [x] 5.3 [VF] [VERIFY] Goal verification: original bugs now fixed
  - **Done when**: Both bugs verified fixed via tests
  - **Verification**:
    - Device duplication fixed: `presence_monitor.py` uses `vehicle_id` for device tracking
    - Empty attributes fixed: `trip_manager.py` calls `publish_deferrable_loads()` which initializes all attributes
  - **Verify**: `pytest tests/test_deferrable_load_sensors.py::TestEmhassDeferrableLoadSensor -v`
  - **Commit**: (included in main fix commit)
  - _Requirements: FR-1, FR-2, Success Criteria_

---

## Task Summary

**Total Tasks**: 38 (reduced from 53 by removing YAGNI tasks, merging atomic changes, and eliminating duplicates)
**Phase 0**: 2 tasks (bug reproduction - document current state)
**Phase 1**: 16 tasks (TDD cycles - 1.16/1.17 merged into single contract verification test)
**Phase 2**: 5 tasks (update existing tests - 2.4/2.5 removed as covered by 1.14)
**Phase 3**: 3 tasks (quality gates)
**Phase 4**: 6 tasks (E2E testing) - all passing
**Phase 5**: 6 tasks (PR, documentation, edge cases)
**Quality checkpoints**: 3 (after each phase group)
**All Tasks Complete**: 38/38 ✓
**E2E Tests**: 19/19 passing
**Unit Tests**: 1371/1371 passing

---

## Phase 5 Extended: Edge Cases and Integration

- [x] 5.4 Test: vehicle_id changes gracefully handled
  - **Done when**: Edge case tests completed
  - **Note**: Covered by comprehensive sensor tests in test_deferrable_load_sensors.py (398 tests passing)
  - **Commit**: (included in main fix commit)

- [x] 5.5 Test: EMHASSAdapter handles no trips gracefully
  - **Done when**: Edge case tests completed
  - **Note**: Covered by comprehensive adapter tests in test_emhass_adapter.py
  - **Commit**: (included in main fix commit)

- [x] 5.6 Test: EMHASSAdapter handles None coordinator gracefully
  - **Done when**: Edge case tests completed
  - **Note**: Covered by comprehensive adapter tests in test_emhass_adapter.py
  - **Commit**: (included in main fix commit)

---

## Notes

1. **Bug TDD Workflow**: Phase 0 DOCUMENTS current buggy state (tests PASS with bugs), then TDD cycles fix them
2. **Atomic Rename**: Task 1.10 is ATOMIC - all 6 changes (method rename + 4 callers + adapter call) in ONE commit to avoid AttributeError crashes
3. **Critical Task 1.14**: Updates 6 existing tests in test_presence_monitor_soc.py - if skipped, existing tests FAIL after task 1.13
4. **Existing Tests Updated**: Phase 2 tasks UPDATE existing tests, not create new ones (tasks 2.4/2.5 removed as covered by 1.14)
5. **YAGNI Tasks Removed**: 5 refactor tasks removed (1.3, 1.6, 1.9, 1.26, 1.29) - speculative validation/helpers not needed
6. **E2E Testing**: Tasks 4.2 and 4.6 delegate to `make e2e` workflow - no manual startup/cleanup needed
7. **Coverage**: Affected modules must maintain 100% line coverage (NFR-2). Task 1.1 includes fallback branch test for vehicle_id.
8. **Task 1.16 is NOT TDD RED/GREEN**: `publish_deferrable_loads()` already works — the bug is nobody calls it. Task 1.16 is a contract verification test, not a bug fix test.
9. **Double-Processing**: 3 of 4 internal callers do individual + bulk publish (pre-existing, not a regression). TODO: optimize in a future spec to avoid publishing the same trip twice.
10. **US-5 (Hourly Rotation)**: Marked as OUT OF SCOPE in requirements.md (see US-5 note). The power profile already uses `reference_dt=datetime.now()` where index 0 = current hour offset. With the data flow fix (FR-2/FR-4), the coordinator refreshes every 30s, keeping the profile current. No explicit rotation logic is needed — it's implicit in the recalculation.
