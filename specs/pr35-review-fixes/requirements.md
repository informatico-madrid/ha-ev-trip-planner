# Requirements: PR #35 Review Fixes

## Goal

Fix 3 real bugs identified during PR #35 code-level review: a race condition in init order, missing observability for a charging cap, and a wrong data type in the EMHASS payload. Plus 2 defensive improvements for flagged false positives.

## Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-1 | Move `entry.runtime_data = EVTripRuntimeData(...)` assignment before `await trip_manager.publish_deferrable_loads()` in `async_setup_entry()` so the coordinator refresh inside `publish_deferrable_loads()` is not silently skipped | High |
| FR-2 | Add `_LOGGER.warning()` when `total_hours > window_size` in `emhass_adapter.py` so users can see when charging is capped below what was calculated | Medium |
| FR-3 | Change `set_deferrable_startup_penalty` in `panel.js` from `[true, true, ...]` to `[0.0, 0.0, ...]` so EMHASS receives the correct float type instead of boolean (penalty 1.0) | High |
| FR-4 | Remove extra space before colon in `set_deferrable_startup_penalty :` in `panel.js` line 977 for template consistency | Low |
| FR-5 | Add `| int(0)` filter to `number_of_deferrable_loads` usage in `panel.js` as defense-in-depth against hypothetical type coercion from HA state serialization | Low |
| FR-6 | Add `max(0, ...)` clamp on `window_size` in `emhass_adapter.py` line 638 as defensive measure (upstream guards already prevent negative values) | Low |

## User Stories

### US-1: Sensors update immediately after plugin init
**As a** Home Assistant user with EV charging trips loaded from storage
**I want to** see the correct sensor data immediately after the integration loads
**So that** I don't see stale data until the next periodic refresh

**Acceptance Criteria:**
- [ ] AC-1.1: After `async_setup_entry()` completes, `entry.runtime_data` is assigned before `publish_deferrable_loads()` is called
- [ ] AC-1.2: The coordinator refresh inside `publish_deferrable_loads()` succeeds (not silently skipped due to None runtime_data)
- [ ] AC-1.3: Sensor attributes reflect the published EMHASS data without waiting for the next periodic refresh

### US-2: User can see when charging is capped
**As a** Home Assistant user whose car might not get a full charge
**I want to** see a warning log when the charging time is capped below what was calculated
**So that** I can diagnose why my car isn't fully charged

**Acceptance Criteria:**
- [ ] AC-2.1: When `total_hours > window_size`, a `_LOGGER.warning()` is emitted with trip_id, original total_hours, window_size, and def_start/end timestamps
- [ ] AC-2.2: The log message includes "Charging may be incomplete" or similar user-visible wording
- [ ] AC-2.3: The cap is still applied (total_hours = window_size) after logging

### US-3: EMHASS receives correct penalty type
**As a** Home Assistant user relying on EMHASS optimization
**I want to** receive a float penalty value (0.0) instead of a boolean (True = 1.0) in the `set_deferrable_startup_penalty` parameter
**So that** EMHASS does not apply an unintended startup penalty that could prevent charging scheduling

**Acceptance Criteria:**
- [ ] AC-3.1: The Jinja2 template generates `[0.0, 0.0, ...]` (floats) instead of `[True, True, ...]` (booleans)
- [ ] AC-3.2: When there are 0 deferrable loads, the value is `[]` (not `[0.0]`)
- [ ] AC-3.3: The YAML key is `set_deferrable_startup_penalty:` (no extra space before colon)

## Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR-1 | No behavioral regression | High — fixes must not change working behavior for users who are not affected by the bugs |
| NFR-2 | No log spam | Medium — the warning in FR-2 should only trigger when the cap actually applies |
| NFR-3 | Home Assistant integration compatibility | High — all changes must be compatible with HA 2024.x+ and the custom component lifecycle |

## Verification Contract

**Project type**: fullstack

**Entry points**:
- `async_setup_entry()` in `__init__.py` lines 140-168 — init flow
- `_populate_cache_from_trip_decisions()` in `emhass_adapter.py` line ~638 — charging decision path
- `async_register_panel()` in `frontend/panel.py` / `frontend/panel.js` lines 970-978 — EMHASS YAML payload generation
- `publish_deferrable_loads()` in `trip_manager.py` lines 299-312 — post-publish coordinator refresh

**Observable signals**:
- PASS: After HA startup, sensor attributes update within seconds (not minutes) of the first coordinator refresh
- PASS: When `total_hours > window_size`, a WARNING log line appears in the HA logs with trip details
- PASS: The EMHASS YAML payload contains `set_deferrable_startup_penalty: [0.0, 0.0, ...]` (not `[true, true, ...]`)
- FAIL: `entry.runtime_data` is still assigned after `publish_deferrable_loads()` — race condition persists
- FAIL: No warning log when cap applies — observability gap remains
- FAIL: YAML payload still contains `[True, True, ...]` — EMHASS receives penalty of 1.0

**Hard invariants**:
- Auth/session validity — not affected by these changes
- Sensor platform must continue to work after coordinator refresh — moving runtime_data assignment earlier must not break sensor initialization
- EMHASS integration must continue to publish and load successfully — changing penalty type must not cause EMHASS errors
- Hourly refresh timer (lines 175-178) depends on `entry.runtime_data` — must remain after the runtime_data assignment

**Seed data**:
- A Home Assistant instance with `ev_trip_planner` integration configured
- At least one vehicle with a charging trip loaded from storage (to exercise `publish_deferrable_loads`)
- A vehicle with SOC below 100% and a tight charging window (to trigger the cap for #12)

**Dependency map**:
- `trip_manager.py` — shares `publish_deferrable_loads()` with `__init__.py` (FR-1)
- `emhass_adapter.py` — `_populate_cache_from_trip_decisions()` calls into `calculations.py` (FR-2)
- `panel.js` → `panel.py` → `services.py` → `__init__.py` — all share config entry and panel registration
- `sensor.py` — reads coordinator state; FR-1 affects sensor update timing

**Escalate if**:
- Moving `entry.runtime_data` before `publish_deferrable_loads()` breaks any HA startup test
- Changing `true` to `0.0` in the Jinja2 template causes EMHASS to reject the YAML
- The warning log for FR-2 triggers excessively (>1 per trip per day) in normal operation

## Out of Scope
- Fix for #5 (negative window_size) — confirmed false positive; upstream guards prevent it
- Fix for #6 (extra space before YAML colon) — confirmed false positive; YAML handles it. FR-4 covers the cosmetic cleanup anyway
- Fix for #7 (state_attr type coercion) — confirmed false positive; state_attr returns native Python types. FR-5 covers the defensive filter anyway
- Any changes to EMHASS itself (external dependency)
- Changes to the coordinator refresh logic (only the init-order fix)
- Adding a UI notification for the capped charging (beyond log warnings)

## Dependencies
- Home Assistant 2024.x+ — the `entry.runtime_data` pattern is HA-recommended
- EMHASS — must accept float penalty values (it does; default is `0.0` in `calculations.py`)
- `async_register_panel_for_entry` — does not access `entry.runtime_data`; safe to reorder (verified in `services.py:1311`)

## Success Criteria
- All 3 confirmed bugs are fixed with surgical changes (single-line or small-block edits)
- No behavioral regression for existing users (sensors, charging schedules, panel display)
- The warning log in FR-2 only triggers when the cap actually applies
- The EMHASS payload in FR-3 matches the documented float type

## Unresolved Questions
- None — all three bugs are confirmed with clear fix approaches verified against source code

## Next Steps
1. Implement FR-3: Change `true` to `0.0` and remove space before colon in `panel.js` line 977
2. Implement FR-2: Add `_LOGGER.warning()` in `emhass_adapter.py` around line 639
3. Implement FR-1: Move `entry.runtime_data` assignment before `publish_deferrable_loads()` in `__init__.py`
4. Implement FR-4 through FR-6: Defensive improvements (optional cosmetic/type-safety)
5. Run existing tests to verify no regression (particularly SOC change tests mentioned in trip_manager.py comment)
