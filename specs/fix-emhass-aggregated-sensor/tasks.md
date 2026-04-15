# Tasks: Fix EMHASS Aggregated Sensor

## Executive Summary

**Total Tasks:** 18 tasks across 4 phases
**Feasibility:** High | **Risk:** Medium | **Effort:** Small

This implementation follows POC-first workflow:
- **Phase 1 (POC):** 4 tasks - Prove datetime fix works
- **Phase 2 (Refactor):** 8 tasks - Complete all fixes
- **Phase 3 (Testing):** 4 tasks - Add test coverage
- **Phase 4 (Quality):** 2 tasks - Final quality gates

---

## Phase 1 (POC): Core Fix - Minimal Proof

### Task 1.1: Fix Datetime Offset Error

**Do:** Fix the datetime offset error in emhass_adapter.py that causes trip sync failures.

**Files:**
- `custom_components/ev_trip_planner/emhass_adapter.py` (lines 334, import section)

**Done when:**
- Import includes `timezone` from datetime module
- Line 334 uses `datetime.now(timezone.utc)` instead of `datetime.now()`
- No linting errors

**Verify:**
```bash
# Run existing test
pytest tests/test_emhass_adapter.py::test_async_publish_deferrable_load_uses_fallback_when_no_trip_data -v

# Check syntax
python -m py_compile custom_components/ev_trip_planner/emhass_adapter.py
```

**Commit:** `fix(emhass_adapter): use timezone-aware datetime`

---

### Task 1.2: Fix def_total_hours as Integer

**Do:** Change def_total_hours from float to integer to satisfy EMHASS validation.

**Files:**
- `custom_components/ev_trip_planner/emhass_adapter.py` (lines 379, 545)

**Done when:**
- Line 379: `round(total_hours, 2)` → `int(total_hours)`
- Line 545: `round(total_hours, 2)` → `int(total_hours)`
- Both locations updated consistently

**Verify:**
```bash
# Check syntax
python -m py_compile custom_components/ev_trip_planner/emhass_adapter.py

# Verify logic manually - grep for int(total_hours)
grep -n "int(total_hours)" custom_components/ev_trip_planner/emhass_adapter.py
```

**Commit:** `fix(emhass_adapter): convert def_total_hours to integer`

---

### Task 1.3: Test Datetime Fix Locally

**Do:** Verify the datetime fix works by creating a test trip.

**Files:** None (manual testing)

**Done when:**
- Home Assistant dev server running at http://192.168.1.100:8123
- Create a new trip in Home Assistant
- Logs show no "offset-naive/offset-aware" errors
- Trip's emhass_index is non-negative (not -1)

**Verify:**
```bash
# Check Home Assistant logs for datetime errors
ha logs | grep -i "offset"

# Verify trip created successfully
ha sensor show sensor.trip_planner_*_emhass_index
```

**Commit:** N/A (manual verification - document in PR notes)

---

### Task 1.4: Test def_total_hours Integer

**Do:** Verify def_total_hours is now an integer in sensor attributes.

**Files:** None (manual testing)

**Done when:**
- Create trip with duration resulting in fractional hours (e.g., 1.94 hours)
- Sensor attribute shows integer value (e.g., `1` not `1.94`)
- EMHASS accepts the value without schema error

**Verify:**
```bash
# Check sensor attribute
ha sensor show sensor.emhass_perfil_diferible_* --attribute def_total_hours

# Should show integer, not float
```

**Commit:** N/A (manual verification - document in PR notes)

---

## Phase 2 (Refactor): Core Fixes - Complete Implementation

### Task 2.1: Fix Entity ID Search Pattern

**Do:** Update panel.js entity ID search pattern to match actual sensor naming.

**Files:**
- `custom_components/ev_trip_planner/frontend/panel.js` (lines 883-886)

**Done when:**
- Pattern changed from: `entityId.startsWith('sensor.emhass_perfil_diferible_')`
- To: `entityId.startsWith('sensor.trip_planner_') && entityId.includes('emhass_perfil_diferible')`
- No JavaScript linting errors

**Verify:**
```bash
# Check syntax
node -c custom_components/ev_trip_planner/frontend/panel.js

# Verify pattern change
grep -A2 "startsWith.*trip_planner" custom_components/ev_trip_planner/frontend/panel.js
```

**Commit:** `fix(panel): update entity ID search pattern`

---

### Task 2.2: Fix Template Keys (Remove _array from Keys)

**Do:** Correct Jinja2 template keys to match EMHASS expected format.

**Files:**
- `custom_components/ev_trip_planner/frontend/panel.js` (lines 914-945)

**Done when:**
- Keys changed from `*_array` to no suffix:
  - `def_total_hours_array:` → `def_total_hours:`
  - `p_deferrable_nom_array:` → `P_deferrable_nom:`
  - `def_start_timestep_array:` → `def_start_timestep:`
  - `def_end_timestep_array:` → `def_end_timestep:`
  - `p_deferrable_matrix:` → `P_deferrable:`
- Attributes (2nd param) keep `_array` suffix: `state_attr('...','def_total_hours_array')`

**Verify:**
```bash
# Check template changes
grep -A10 "Keys (left of :)" custom_components/ev_trip_planner/frontend/panel.js

# Verify capitalization of P_deferrable
grep "P_deferrable" custom_components/ev_trip_planner/frontend/panel.js
```

**Commit:** `fix(panel): correct Jinja2 template keys for EMHASS`

---

### Task 2.3: Fix panel.css Route

**Do:** Update CSS path in panel.js to match services.py registration.

**Files:**
- `custom_components/ev_trip_planner/frontend/panel.js` (line 723)

**Done when:**
- Path changed from `/ev_trip_planner/panel.css` to `/ev-trip-planner/panel.css`
- Uses hyphens instead of underscores

**Verify:**
```bash
# Verify change
grep "ev-trip-planner.*panel.css" custom_components/ev_trip_planner/frontend/panel.js
```

**Commit:** `fix(panel): use hyphens in CSS path`

---

### Task 2.4: Remove EMHASS Availability Warning

**Do:** Remove the "sensor not available" warning message from panel.js.

**Files:**
- `custom_components/ev_trip_planner/frontend/panel.js` (lines 905-945)

**Done when:**
- `emhassAvailable` check removed
- Warning message `⚠️ EMHASS sensor not available` removed
- EMHASS section always renders

**Verify:**
```bash
# Verify warning removed
grep "EMHASS sensor not available" custom_components/ev_trip_planner/frontend/panel.js
# Should return nothing

# Verify section still renders
grep -A5 "emhass-config-section" custom_components/ev_trip_planner/frontend/panel.js
```

**Commit:** `fix(panel): always show EMHASS section without warning`

---

### Task 2.5: Fix Modal Trip Type Detection

**Do:** Update modal trip type detection to check all possible fields.

**Files:**
- `custom_components/ev_trip_planner/frontend/panel.js` (line ~1637)

**Done when:**
- Changed from: `trip.type === 'puntual' ? 'puntual' : 'recurrente'`
- To: Check all fields: `trip.tipo`, `trip.type`, `trip.recurring`
- Logic: `if (trip.tipo === 'puntual' || trip.type === 'puntual' || trip.recurring === false)`

**Verify:**
```bash
# Verify change
grep -A3 "trip.tipo.*puntual" custom_components/ev_trip_planner/frontend/panel.js
```

**Commit:** `fix(panel): check all fields for trip type detection`

---

### Task 2.6: Test Entity Pattern Fix

**Do:** Verify entity pattern fix correctly finds EMHASS sensors.

**Files:** None (manual testing)

**Done when:**
- Panel opens and scans entity registry
- Sensor `sensor.trip_planner_*_emhass_perfil_diferible_*` is found
- EMHASS data displays correctly
- No "EMHASS sensor not available" message

**Verify:**
```bash
# Open panel in browser
# Navigate to http://192.168.1.100:8123/ev-trip-planner/

# Check console for errors
# Should see no "Refused to apply style" or entity search errors
```

**Commit:** N/A (manual verification)

---

### Task 2.7: Test Template Keys Fix

**Do:** Verify template generates correct keys for EMHASS.

**Files:** None (manual testing)

**Done when:**
- Jinja2 template renders with correct keys
- Keys do NOT have `_array` suffix
- EMHASS receives: `def_total_hours`, `P_deferrable_nom`, `def_start_timestep`, `def_end_timestep`, `P_deferrable`

**Verify:**
```bash
# Open browser DevTools Network tab
# Look for EMHASS shell command curl
# Verify keys in JSON payload
```

**Commit:** N/A (manual verification)

---

## Phase 3 (Testing): Quality - Test Coverage

### Task 3.1: Add Datetime Test

**Do:** Add unit test for datetime handling in emhass_adapter.py.

**Files:**
- `tests/test_emhass_adapter.py` (append new test)

**Done when:**
- New test: `test_datetime_offset_aware`
- Tests `datetime.now(timezone.utc)` used in async_publish_deferrable_load
- Tests no error when deadline_dt is offset-aware

**Verify:**
```bash
pytest tests/test_emhass_adapter.py::test_datetime_offset_aware -v
```

**Commit:** `test(emhass_adapter): add datetime offset test`

---

### Task 3.2: Add def_total_hours Type Test

**Do:** Add unit test verifying def_total_hours is integer.

**Files:**
- `tests/test_emhass_adapter.py` (append new test)

**Done when:**
- New test: `test_def_total_hours_is_integer`
- Tests that `int(total_hours)` produces integer type
- Tests EMHASS payload has integer def_total_hours

**Verify:**
```bash
pytest tests/test_emhass_adapter.py::test_def_total_hours_is_integer -v
```

**Commit:** `test(emhass_adapter): add def_total_hours integer test`

---

### Task 3.3: Add Aggregated Sensor Test

**Do:** Add integration test for second trip aggregation.

**Files:**
- `tests/test_aggregated_sensor_bug.py` (append new test)

**Done when:**
- New test: `test_second_trip_aggregated`
- Creates two trips
- Verifies `def_total_hours_array` has length 2
- Verifies both trips in `punctual_trips`

**Verify:**
```bash
pytest tests/test_aggregated_sensor_bug.py::test_second_trip_aggregated -v
```

**Commit:** `test(aggregated sensor): add second trip aggregation test`

---

### Task 3.4: E2E Verification - Full Flow

**Do:** Run complete end-to-end verification of all fixes.

**Files:** None (manual testing via Cypress or manual)

**Done when:**
- Create first trip → verify emhass_index = 0
- Create second trip → verify both trips aggregated
- Check panel shows EMHASS data without warning
- Check template keys correct in network tab
- Verify CSS loads (no 404 errors)

**Verify:**
```bash
# Start dev server
cd custom_components/ev_trip_planner
# ... (dev server setup)

# Open browser
# Follow verification checklist from requirements.md
```

**Commit:** N/A (E2E verification - document results in PR)

---

## Phase 4 (Quality): CI/PR - Final Quality Gates

### Task 4.1: Run All Existing Tests

**Do:** Run complete test suite to ensure no regressions.

**Files:** None (test execution)

**Done when:**
```bash
pytest tests/ -v --tb=short
```

All existing tests pass:
- `test_emhass_adapter.py`
- `test_aggregated_sensor_bug.py`
- All other component tests

**Verify:**
```bash
# Check test results
# All green, no failures
```

**Commit:** N/A (test execution - document in PR)

---

### Task 4.2: Manual Verification Checklist

**Do:** Complete manual verification checklist from requirements.md.

**Files:** None

**Done when:**
All ACs verified manually:
- AC 1: Datetime offset fixed ✓
- AC 2: Entity pattern finds sensors ✓
- AC 3: def_total_hours is integer ✓
- AC 4: CSS route works (no 404) ✓
- AC 5: Second trip aggregated ✓
- AC 6: emhass_index assigned ✓
- AC 7: EMHASS section always visible ✓
- AC 9: Template keys correct ✓
- AC 10: Modal trip type correct ✓

**Verify:**
Create checklist document in PR with all items checked off.

**Commit:** N/A (manual verification - document in PR)

---

## Implementation Summary

### Files Modified

| File | Tasks | Lines Changed |
|------|-------|---------------|
| `emhass_adapter.py` | 1.1, 1.2 | ~4 lines |
| `panel.js` | 2.1, 2.2, 2.3, 2.4, 2.5 | ~40 lines |
| `test_emhass_adapter.py` | 3.1, 3.2 | ~50 lines |
| `test_aggregated_sensor_bug.py` | 3.3 | ~30 lines |

### Verification Tooling

- **Dev Server:** Home Assistant at http://192.168.1.100:8123
- **Browser:** Chrome DevTools for console/network inspection
- **Tests:** `pytest tests/ -v`
- **Linter:** `flake8`, `pylint` for Python; `eslint` for JavaScript

### Acceptance Criteria Coverage

| AC | Task | Status |
|----|------|--------|
| AC 1 | 1.1, 1.3 | Implemented |
| AC 2 | 2.1, 2.6 | Implemented |
| AC 3 | 1.2, 1.4 | Implemented |
| AC 4 | 2.3 | Implemented |
| AC 5 | 3.3, 2.7 | Implemented |
| AC 6 | 1.3 | Implemented |
| AC 7 | 2.4, 2.6 | Implemented |
| AC 9 | 2.2, 2.7 | Implemented |
| AC 10 | 2.5 | Implemented |

---

## POC Milestone

**After Phase 1 (Tasks 1.1-1.2):**
- Datetime fix proven working
- trips sync without errors
- emhass_index assigned correctly
- def_total_hours as integer

**Total POC Progress:** 4/18 tasks (22%)

## Next Steps

After approval, run: `/ralph-specum:implement` to start execution.
