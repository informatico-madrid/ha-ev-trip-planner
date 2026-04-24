# Design: PR #35 Review Fixes

## Architecture Impact
Minimal — all fixes are surgical code changes in existing files. No new components, interfaces, or architectural decisions.

## Fix Details

### Fix 1: Move runtime_data assignment before publish_deferrable_loads (Bug #4)

**File**: `custom_components/ev_trip_planner/__init__.py`

**Current code** (lines 159-168):
```python
if emhass_adapter is not None:
    await trip_manager.publish_deferrable_loads()   # line 160 — reads entry.runtime_data.coordinator (None!)
await async_register_panel_for_entry(hass, entry, vehicle_id, vehicle_name)

# Store runtime data using entry.runtime_data (HA-recommended pattern)
entry.runtime_data = EVTripRuntimeData(          # line 164 — too late
    coordinator=coordinator,
    trip_manager=trip_manager,
    emhass_adapter=emhass_adapter,
)
```

**New code** — swap the block order so `runtime_data` is set before `publish_deferrable_loads`:
```python
# Store runtime data FIRST
entry.runtime_data = EVTripRuntimeData(
    coordinator=coordinator,
    trip_manager=trip_manager,
    emhass_adapter=emhass_adapter,
)

if emhass_adapter is not None:
    await trip_manager.publish_deferrable_loads()   # now reads entry.runtime_data.coordinator (real)
await async_register_panel_for_entry(hass, entry, vehicle_id, vehicle_name)
```

**Risk assessment**: Low. This is a reordering of independent setup steps. `publish_deferrable_loads()` internally accesses `entry.runtime_data.coordinator` at line 300-308 of `trip_manager.py` — with the old order it was `None`, so coordinator refresh was silently skipped. No functional side effects from the new order since `entry.runtime_data` is only read later (timer setup at line 175 also reads `entry.runtime_data`, which now also benefits from being set earlier).

### Fix 2: Add logging before total_hours cap (Bug #12)

**File**: `custom_components/ev_trip_planner/emhass_adapter.py`

**Current code** (lines 638-640):
```python
window_size = def_end_timestep - def_start_timestep
if total_hours > window_size:
    total_hours = window_size
```

**New code**:
```python
window_size = def_end_timestep - def_start_timestep
if total_hours > window_size:
    _LOGGER.warning(
        "Capped charging hours for trip %s from %.2f to %d (window=%d). "
        "Charging time exceeds available window.",
        trip_id, decision.def_total_hours, window_size, window_size,
    )
    total_hours = window_size
```

**Risk assessment**: Zero. This is a logging-only addition. The cap logic itself is unchanged. Follows existing logging patterns in the same file (e.g., lines 565-568 `_LOGGER.info` for charging decisions).

### Fix 3: Fix startup_penalty type in Jinja2 template (Bug #13)

**File**: `custom_components/ev_trip_planner/frontend/panel.js`

**Current code** (line 977):
```javascript
set_deferrable_startup_penalty : {{ ([true] * (state_attr('${emhassSensorEntityId}', 'number_of_deferrable_loads') | default(0))) | default([], true) }}
```

**New code**:
```javascript
set_deferrable_startup_penalty: {{ ([0.0] * (state_attr('${emhassSensorEntityId}', 'number_of_deferrable_loads') | default(0) | int(0))) | default([], true) }}
```

Changes:
1. `true` → `0.0` (EMHASS expects floats, not booleans; `0.0` means "no startup penalty")
2. Remove extra space before `:` (FR-4)
3. Add `| int(0)` filter for type safety (FR-5)
4. Add `max(0, ...)` clamp — not needed here since `number_of_deferrable_loads` is inherently non-negative; adding the `int(0)` filter and `[0.0] * N` with `N=0` produces `[]` naturally (FR-6 handled by int filter)

**Risk assessment**: Low. This affects the Jinja2 template displayed in the frontend for users to copy. The old `[true, true, ...]` maps to `[1.0, 1.0, ...]` in EMHASS's calculations.py:1258, applying an unintended 1.0 startup penalty. This penalty may cause EMHASS to avoid scheduling charging. Fixing to `0.0` removes this artificial barrier. Users who already copied the template will need to re-copy (minor UX note).

## Existing Codebase Patterns Followed

- **Bug #12 logging**: Follows the structured logging pattern at lines 565-568 of `emhass_adapter.py` — `_LOGGER.info`/`_LOGGER.warning` with trip_id and computed values.
- **Bug #13 Jinja2**: Follows existing Jinja2 template patterns in the same file — `state_attr() | default(...)` filters.
- **Bug #4 reorder**: Consistent with the comment at line 148-149 ("Create coordinator BEFORE publishing to EMHASS") — the code should reflect this intent.

## Test Strategy

### Test File Conventions (discovered from codebase)
- **Test runner**: pytest (1631 tests collected)
- **Test file location**: `tests/` directory, files like `test_init.py`, `test_emhass_adapter.py`
- **Mock cleanup**: Standard pytest-homeassistant-custom-component fixtures handle cleanup
- **Fixture/factory location**: Co-located in `tests/`

### Existing Tests That Cover This Code
| Module | Test file | Relevant tests |
|--------|-----------|----------------|
| `__init__.py` | `tests/test_init.py` | `TestVerifyStoragePermissions`, import/dashboard tests, setup entry tests |
| `emhass_adapter.py` | `tests/test_emhass_adapter.py` | Full coverage of publish, cache, indices |
| `emhass_adapter.py` | `tests/test_emhass_adapter_def_end_bug.py` | `_populate_per_trip_cache_entry` tests |
| `trip_manager.py` | `tests/test_trip_manager_core.py` | `test_publish_deferrable_loads_*` tests |

### What to Verify (no new tests needed)
These are 3-line fixes — existing tests should pass without modification:

1. **Bug #4**: `test_init.py` tests that call `async_setup_entry` already have fixtures that set `entry.runtime_data`. The reordering moves the assignment earlier but doesn't change observable behavior for tests (coordinator refresh still happens). No new test needed.

2. **Bug #12**: The cap logic at lines 638-640 of `emhass_adapter.py` is tested implicitly via `test_emhass_adapter_def_end_bug.py` which exercises `_populate_per_trip_cache_entry`. Adding logging does not change behavior — existing tests pass. No new test needed.

3. **Bug #13**: This is a frontend JavaScript file change. No Python tests affected. The template is rendered client-side in Home Assistant's browser. No automated test for this pattern exists in the repo (frontend Jinja2 templates are not tested). Manual verification: copy the template and verify `set_deferrable_startup_penalty` shows `[0.0, 0.0, ...]` not `[true, true, ...]`.

## Rollback Plan

Each fix is independently revertable:
- **Bug #4**: Move the two code blocks back to original order. No data loss.
- **Bug #12**: Remove the three `_LOGGER.warning` lines. No data loss.
- **Bug #13**: Revert the single template line. Users who already copied the old template would need to re-copy — cosmetic issue only, no functional impact on the integration.
