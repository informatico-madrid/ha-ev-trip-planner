# Research: PR #35 Review Fixes

## Executive Summary

PR #35 review identified 6 claims; 3 are confirmed real bugs, 3 are false positives. The 3 real issues span initialization order (`__init__.py`), missing observability (`emhass_adapter.py`), and wrong data type in a Jinja2 template (`panel.js`). All fixes are surgical — no architectural changes needed. The boolean-vs-float bug in `panel.js` (#13) is the highest impact and should be addressed first.

## Key Findings

| # | File | Claim | Verdict | Severity |
|---|------|-------|---------|----------|
| 4 | `__init__.py:160` | Coordinator refresh skipped during init | **REAL** | LOW |
| 5 | `emhass_adapter.py:641` | Negative window_size | **FALSE** | N/A |
| 6 | `panel.js:977` | Extra space before YAML colon | **FALSE** | N/A |
| 7 | `panel.js:977` | state_attr returns string | **FALSE** | N/A |
| 12 | `emhass_adapter.py:640` | Missing warning log when capping | **REAL** | LOW-MEDIUM |
| 13 | `panel.js:977` | Boolean instead of float for startup_penalty | **REAL** | MEDIUM |

## Verification Results

### #4 Race condition — CONFIRMED

**Source**: `custom_components/ev_trip_planner/__init__.py` lines 150-168, `trip_manager.py` lines 300-312

**Execution order in `async_setup_entry()`**:
1. Line 150: `coordinator = TripPlannerCoordinator(...)`
2. Line 152: `await coordinator.async_config_entry_first_refresh()` — first refresh runs (empty EMHASS data)
3. Line 160: `await trip_manager.publish_deferrable_loads()` — publishes to EMHASS
4. Line 164: `entry.runtime_data = EVTripRuntimeData(...)` — **runtime_data assigned AFTER publish**

Inside `publish_deferrable_loads()` (trip_manager.py:300-301):
```python
entry = self.hass.config_entries.async_get_entry(self._entry_id)
if entry and entry.runtime_data:  # <-- falsy at line 160; runtime_data not set yet
    coordinator = entry.runtime_data.coordinator
    await coordinator.async_refresh()  # SKIPPED
```

The EMHASS publish at line 294 succeeds. The coordinator refresh (lines 303-308) is silently skipped because `entry.runtime_data` doesn't exist yet. This contradicts the stated intent at lines 156-158: *"triggers a coordinator refresh so sensors see the correct data immediately."*

**Impact**: Sensors show stale data until next periodic refresh. No crash. The `try/except` at lines 309-312 swallows the issue with a debug log.

### #12 Missing logging — CONFIRMED

**Source**: `custom_components/ev_trip_planner/emhass_adapter.py` lines 634-640

```python
window_size = def_end_timestep - def_start_timestep
if total_hours > window_size:
    total_hours = window_size  # No logging here
```

No `_LOGGER.warning()` or `_LOGGER.debug()` when the cap triggers. This is a data modification that directly affects charging behavior — the car won't get a full charge. The same file logs charging decisions at line 565-568, so the pattern exists; this just isn't using it.

**Impact**: Users can't diagnose why their car isn't fully charged. MEDIUM because the cap condition (`total_hours > window_size`) is likely to trigger frequently with SOC-aware calculations.

### #13 Wrong type (bool vs float) — CONFIRMED

**Source**: `custom_components/ev_trip_planner/frontend/panel.js` line 977, `calculations.py` line 1258

**panel.js line 977 generates**:
```yaml
set_deferrable_startup_penalty: [True, True, True, ...]
```

**EMHASS expects**: list of floats (per `calculations.py:1258`: `"startup_penalty": 0.0`)

**Verification**:
- `calculations.py:1258`: default is `0.0` (float)
- Line 1214 in calculations.py: docstring says "startup_penalty: Always 0.0"
- Jinja2 `[true] * 3` produces `[True, True, True]` — booleans serialize to YAML as `true`/`false`
- In Python, `True == 1`, so EMHASS sees penalty of `1.0` per load instead of `0.0`

This applies an unintended penalty to every deferrable load, potentially causing EMHASS to avoid scheduling charging starts.

**Also confirmed**: Extra space before colon on line 977 (`set_deferrable_startup_penalty :`) is cosmetic — YAML parses it correctly. Fix it for consistency anyway.

### #5, #6, #7 — False Positives

- **#5** (`emhass_adapter.py` negative window_size): Upstream guards in `calculations.py:492-493` and edge case fix at line 625-627 prevent `def_end < def_start`. `window_size` can be 0 but not negative.
- **#6** (extra space in YAML key): YAML spec treats `key : value` identically to `key: value`. Valid but inconsistent.
- **#7** (state_attr returns string): `state_attr()` returns native Python types. `sensor.py:323` sets `number_of_deferrable_loads` as `int`. `[true] * int` works fine.

## Related Specs

| Spec | Relation | May Need Update |
|------|----------|-----------------|
| `m401-emhass-hotfixes` | Direct overlap — EMHASS integration fixes | Low — these are pre-existing bugs, not new behavior |
| `emhass-integration-with-fixes` | Direct overlap — EMHASS sensor attributes | No — fixes are orthogonal (logging, type, init order) |
| `fix-emhass-aggregated-sensor` | Indirect — sensors use coordinator | No — same symptom, different root cause |
| `fix-emhass-sensor-attributes` | Indirect — sensor attributes affected by coordinator refresh | Low — if coordinator refresh timing changes, sensor attrs update timing changes |
| `soc-integration-baseline` / `soc-milestone-algorithm` | Indirect — #12 cap often triggered by SOC calculations | No — these calculate the values; #12 just logs the cap |

## Recommended Approach

### Must Fix (3 real problems)

**1. #13 — panel.js boolean→float (MEDIUM severity, highest impact)**
```javascript
// Before (line 977):
set_deferrable_startup_penalty : {{ ([true] * (state_attr(...) | default(0))) | default([], true) }}

// After:
set_deferrable_startup_penalty: {{ ([0.0] * (state_attr('${emhassSensorEntityId}', 'number_of_deferrable_loads') | default(0))) | default([], true) }}
```
Two changes: `true` → `0.0` and remove extra space before colon. Single-line edit.

**2. #12 — Add logging when cap triggers (LOW-MEDIUM severity)**
```python
window_size = def_end_timestep - def_start_timestep
if total_hours > window_size:
    _LOGGER.warning(
        "Trip %s: Capping total_hours from %.1f to window_size %d "
        "(def_start=%d, def_end=%d). Charging may be incomplete.",
        trip_id, total_hours, window_size, def_start_timestep, def_end_timestep,
    )
    total_hours = window_size
```
`trip_id` is available in scope from line 583. Add `_LOGGER` import if needed (check if already imported).

**3. #4 — Move runtime_data assignment before publish_deferrable_loads (LOW severity)**
```python
# Before:
await trip_manager.publish_deferrable_loads()          # line 160
await async_register_panel_for_entry(...)               # line 161
entry.runtime_data = EVTripRuntimeData(...)             # line 164

# After:
entry.runtime_data = EVTripRuntimeData(
    coordinator=coordinator,
    trip_manager=trip_manager,
    emhass_adapter=emhass_adapter,
)
await trip_manager.publish_deferrable_loads()
await async_register_panel_for_entry(...)
```
One concern: `async_register_panel_for_entry` at line 161 might depend on something set by `publish_deferrable_loads`. Need to verify. If not, move `runtime_data` assignment to right after line 154 (after the first refresh, before publish).

### Optional Defensive Improvements

- Add `| int(0)` filter to `panel.js` line 975-977 for defense-in-depth against hypothetical type coercion (Cost: trivial. Benefit: minimal.)
- Add `_LOGGER.info` when `window_size == 0` in `emhass_adapter.py` (Cost: trivial. Benefit: edge case visibility.)

## Risks

| Fix | Risk | Mitigation |
|-----|------|------------|
| #13 (panel.js) | Breaking EMHASS if it somehow handles booleans differently | Unlikely — EMHASS uses `startup_penalty: 0.0` internally, expects floats |
| #12 (logging) | None — only adds a log line | N/A |
| #4 (init order) | `async_register_panel_for_entry` might depend on panel being set up before runtime_data | Move `runtime_data` AFTER `async_register_panel_for_entry` if panel setup needs it; or check if `async_register_panel_for_entry` uses `entry.runtime_data` |

**#4 risk analysis**: Need to verify that `async_register_panel_for_entry` doesn't access `entry.runtime_data`. If it doesn't (which is likely — it registers the panel, doesn't read data), then moving `runtime_data` before `publish_deferrable_loads` is safe. If it does, keep `runtime_data` where it is but pass `coordinator` directly to `publish_deferrable_loads()`.

## Sources

| Source | Key Point |
|--------|-----------|
| `.research/pr35_code_analysis.md` | Original code analysis with line-level claims |
| `custom_components/ev_trip_planner/__init__.py:140-168` | Verified async_setup_entry execution order |
| `custom_components/ev_trip_planner/trip_manager.py:208-312` | Verified publish_deferrable_loads accesses entry.runtime_data |
| `custom_components/ev_trip_planner/emhass_adapter.py:634-640` | Verified missing log on cap |
| `custom_components/ev_trip_planner/frontend/panel.js:970-978` | Verified Jinja2 template with boolean vs float |
| `custom_components/ev_trip_planner/calculations.py:1258` | Verified startup_penalty default is 0.0 (float) |
| `custom_components/ev_trip_planner/sensor.py:323` | Verified number_of_deferrable_loads stored as int |

## Next Steps

1. Fix #13 in panel.js (boolean→float, remove space)
2. Add warning log in emhass_adapter.py for cap
3. Investigate #4 race condition — verify whether `async_register_panel_for_entry` needs runtime_data before moving assignment
4. Apply optional defensive improvements if time allows
