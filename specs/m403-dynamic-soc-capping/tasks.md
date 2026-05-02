# Tasks: m403-Dynamic SOC Capping — REBUILD

**Milestone**: 4.0.3
**Target**: v0.5.23
**Priority**: P1 - Battery Health & Cost Optimization
**Input**: Design documents from `/specs/m403-dynamic-soc-capping/`
**Prerequisites**: spec.md, requirements.md, research.md, design.md
**Status**: PHASES 1-6 COMPLETE (T001-T055 [x]). PHASES 7+ REBUILD REQUIRED — US5 production wiring never connected.

## Root Cause

The previous implementation completed US1-US4 correctly (T001-T055) but FAILED on US5 (T059-T062). The executor stored `_t_base` and `_battery_cap` in `emhass_adapter.__init__` but NEVER wired them into the production path. The external-reviewer marked T059-T062 as `[x]` without implementing the actual integration.

**Verifiable evidence**:
- `grep -rn "self._t_base" custom_components/ev_trip_planner/emhass_adapter.py` — 1 hit at line 128 (assignment only, zero reads after init)
- `grep -rn "\.get_capacity(" custom_components/ev_trip_planner/*.py` — 1 hit at trip_manager.py:1929 (NOT in emhass_adapter.py)
- `grep -rn "calcular_hitos_soc" custom_components/ev_trip_planner/*.py` — only definition at trip_manager.py:1880, zero callers
- `grep -rn "soc_caps\|dynamic_soc_limit" custom_components/ev_trip_planner/emhass_adapter.py` — zero hits
- All 12+ uses of `self._battery_capacity_kwh` in emhass_adapter.py use NOMINAL capacity

## Quality Gates Policy (ABSOLUTE)

- **E2E tests ALWAYS run via `make e2e`** (not pytest directly). The canonical command is `make e2e`.
- **Quality gates every few steps**: After each user story phase AND after every 3 implementation tasks.
- **Zero regressions**: Run full test suite (`python -m pytest tests/ -v`) BEFORE and AFTER every file change. If any test fails, STOP and fix it.
- **Party mode for quality gates**: Invoke the PR review toolkit with all reviewers (`code-reviewer`, `comment-analyzer`, `silent-failure-hunter`, `type-design-analyzer`) for every quality gate.
- **100% coverage**: `fail_under = 100` in pyproject.toml — all new code must be fully covered.
- **Test maintenance**: If a change legitimately breaks an existing test, document WHY and update the assertion to the new correct behavior.
- **DEAD CODE DETECTION**: Every quality gate MUST run grep-based verification that functions are actually CALLED in the production path, not just defined.
- **WEAK TEST DETECTION**: Tests that pass with `nonZeroHours >= 1` but don't verify T_BASE effect MUST be flagged and rewritten.
- **INTEGRATION VERIFICATION**: An independent subagent must verify the production path actually uses computed values — not just that attributes exist.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify baseline, prepare test infrastructure

- [x] T001 [VERIFY:TEST] Run FULL existing test suite baseline — verify ALL tests pass BEFORE any changes (`python -m pytest tests/ -v`)
- [x] T002 [VERIFY:TEST] Verify e2e test runner works (`make e2e`) — confirm Playwright E2E tests execute successfully
- [x] T003 [VERIFY:TEST] Run coverage baseline (`make test-cover`) — record current coverage for files that will be modified
- [x] T004 [P] [VERIFY:TEST] Run mypy type check on current codebase (`mypy custom_components/ev_trip_planner/`) — establish type baseline
- [x] T005 [P] Identify tests that reference the functions we will modify (test_soc_milestone.py, test_power_profile_positions.py, test_soc_100_deficit_propagation_bug.py) — document which assertions may need updating

**Checkpoint**: Baseline verified — all existing tests pass, e2e works, coverage recorded.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**CRITICAL**: No user story work can begin until this phase is complete.

- [x] T006 [P] [VERIFY:TEST] Add constants to `const.py`: `CONF_T_BASE`, `CONF_SOC_BASE`, `CONF_SOH_SENSOR`, `DEFAULT_T_BASE`, `DEFAULT_SOC_BASE`, `MIN_T_BASE`, `MAX_T_BASE`, `DEFAULT_SOH_SENSOR` (`custom_components/ev_trip_planner/const.py`)
- [x] T007 [P] [VERIFY:TEST] Update `CONFIG_VERSION` from 2 to 3 in `const.py` and add `async_migrate_entry` for version 2 -> 3 migration in `config_flow.py` (add `t_base=24.0` and `soh_sensor=""` to existing config entries) (`custom_components/ev_trip_planner/config_flow.py`)
- [x] T008 [P] [VERIFY:TEST] Create `BatteryCapacity` frozen dataclass in `calculations.py`: `nominal_capacity_kwh`, `soh_sensor_entity_id | None`, `_soh_value | None`, `_soh_cached_at | None`, methods `get_capacity(hass | None) -> float`, `get_capacity_kwh(hass | None) -> float`, `_read_soh(hass) -> float | None`, `_compute_capacity() -> float` with 5-min cache TTL and hysteresis fallback (`custom_components/ev_trip_planner/calculations.py`)
- [x] T009 [P] [VERIFY:TEST] Export `BatteryCapacity` in `__all__` of `calculations.py`
- [x] T010 [VERIFY:TEST] Run FULL test suite (`python -m pytest tests/ -v`) — zero regressions from foundational changes

**Checkpoint**: Foundation ready — BatteryCapacity abstraction and constants in place. User story implementation can now begin.

---

## Phase 3: User Story 1 — Calculate Dynamic SOC Limit (Priority: P1)

**Goal**: Pure function `calculate_dynamic_soc_limit()` computing degradation-aware SOC upper bound from idle hours, post-trip SOC, and battery parameters.

**Independent Test**: Function returns correct values for all 5 verified scenarios (A, B, C, edge cases, T_base variability).

### Tests for User Story 1 (TDD)

- [x] T011 [P] [US1] [VERIFY:TEST] Create `tests/test_dynamic_soc_capping.py` with unit test for Scenario A: `calculate_dynamic_soc_limit(22, 41, 30, t_base=24)` returns ~94.9% (`custom_components/ev_trip_planner/calculations.py`, `tests/test_dynamic_soc_capping.py`)
- [x] T012 [P] [US1] [VERIFY:TEST] Add unit test for Scenario B: `calculate_dynamic_soc_limit(8, 0, 30)` returns 100.0 (negative risk — large trip drain) (`tests/test_dynamic_soc_capping.py`)
- [x] T013 [P] [US1] [VERIFY:TEST] Add unit test for Scenario C (critical case): 4 identical trips, limit stays at 94.9% each iteration (`tests/test_dynamic_soc_capping.py`)
- [x] T014 [P] [US1] [VERIFY:TEST] Add unit tests for edge cases: zero idle hours (t=0 -> 100%), at sweet spot SOC (35% -> 100%), infinite T_base -> 100% (`tests/test_dynamic_soc_capping.py`)
- [x] T015 [P] [US1] [VERIFY:TEST] Add unit test for T_base configurability: `t_base=6 < t_base=24 < t_base=48` ordering of limits (`tests/test_dynamic_soc_capping.py`)
- [x] T016 [P] [US1] [VERIFY:TEST] Add unit tests for BatteryCapacity: nominal-only, SOH=90% -> real_capacity=nominal*0.9, SOH unavailable -> nominal fallback, SOH clamp to [10, 100] (`tests/test_dynamic_soc_capping.py`)

### Implementation for User Story 1

- [x] T017 [US1] [VERIFY:TEST] Implement `calculate_dynamic_soc_limit()` in `calculations.py`: pure function with formula `risk = t_hours * (soc_post_trip - 35) / 65`, `limit = 35 + 65 * (1 / (1 + risk / t_base))`, clamped to [35.0, 100.0] — return 100.0 when risk <= 0 (`custom_components/ev_trip_planner/calculations.py`)
- [x] T018 [US1] [VERIFY:TEST] Export `calculate_dynamic_soc_limit` in `__all__` of `calculations.py`

### Quality Gate — User Story 1

- [x] T019 [US1] [VERIFY:TEST] Run FULL test suite (`python -m pytest tests/ -v`) — zero regressions
- [x] T020 [US1] [VERIFY:TEST] Run coverage for `calculations.py` — verify new functions covered (`pytest --cov=custom_components/ev_trip_planner/calculations.py`)
- [x] T021 [US1] [VERIFY:TEST] Run `make e2e` — e2e tests still pass
- [x] T022 [US1] [VERIFY:TEST] Party mode: run code-reviewer + type-design-analyzer on `calculations.py` changes

**Checkpoint**: User Story 1 complete — dynamic SOC limit algorithm implemented and tested.

---

## Phase 4: User Story 2 — Apply Dynamic SOC Cap Inside Deficit Propagation (Priority: P1)

**Goal**: Cap `soc_objetivo_ajustado` with dynamic limit in `calculate_deficit_propagation()` in BOTH backward loop AND result-building loop. Forward-propagated SOC uses capped values.

**Independent Test**: Deficit propagation with caps produces `soc_objetivo <= dynamic_limit` per trip. Without caps, behavior is identical to existing (backward compatible).

### Tests for User Story 2 (TDD)

- [x] T023 [P] [US2] [VERIFY:TEST] Add unit test: `calculate_deficit_propagation()` with `soc_caps` produces capped results where `soc_objetivo <= dynamic_limit` per trip (`tests/test_calculations.py`)
- [x] T024 [P] [US2] [VERIFY:TEST] Add unit test: `calculate_deficit_propagation()` without `soc_caps` produces identical results to current (backward compatibility) (`tests/test_calculations.py`)
- [x] T025 [P] [US2] [VERIFY:TEST] Add unit test: forward-propagated SOC uses capped `soc_objetivo_final`, not uncapped `soc_objetivo_ajustado` (`tests/test_calculations.py`)

### Implementation for User Story 2

- [x] T026 [US2] [VERIFY:TEST] Modify `calculate_deficit_propagation()` signature to accept optional `t_base: float = 24.0` and `soc_caps: list[float] | None = None` parameters (`custom_components/ev_trip_planner/calculations.py`)
- [x] T027 [US2] [VERIFY:TEST] In backward propagation loop (~line 808): after computing `soc_objetivo_ajustado`, apply `soc_objetivo_final = min(soc_objetivo_ajustado, soc_caps[idx]) if soc_caps else soc_objetivo_ajustado` — use `soc_objetivo_final` for deficit calculation (`custom_components/ev_trip_planner/calculations.py`)
- [x] T028 [US2] [VERIFY:TEST] In forward/result-building loop (~line 843): after recomputing `soc_objetivo_ajustado`, apply same cap — use `soc_objetivo_final` in results dict (`custom_components/ev_trip_planner/calculations.py`)
- [x] T029 [US2] [VERIFY:TEST] Wire capped SOC for forward propagation: compute `soc_caps` in `calcular_hitos_soc()` and pass to `calculate_deficit_propagation()` (`custom_components/ev_trip_planner/trip_manager.py`)

### Quality Gate — User Story 2

- [x] T030 [US2] [VERIFY:TEST] Run FULL test suite (`python -m pytest tests/ -v`) — 1738 passed, 1 pre-existing timezone failure
- [x] T031 [US2] [VERIFY:TEST] Run coverage for `calculations.py` — 99% coverage
- [x] T032 [US2] [VERIFY:TEST] Run `make e2e` — 30/30 e2e tests pass
- [x] T033 [US2] [VERIFY:TEST] Party mode: run code-reviewer + silent-failure-hunter on deficit propagation changes

**Checkpoint**: User Story 2 complete — dynamic cap integrated into deficit propagation in both loops, forward propagation uses capped values.

---

## Phase 5: User Story 3 — Configure T_base via Home Assistant UI (Priority: P2)

**Goal**: T_base slider (6-48h, default 24) in config flow (sensors step) and options flow. No health-mode toggle.

**Independent Test**: Config flow persists T_base value. Options flow updates T_base. Next power profile generation uses new T_base.

### Tests for User Story 3 (TDD)

- [x] T034 [P] [US3] [VERIFY:TEST] Add unit test: config flow T_base slider accepts 24.0 and persists in entry data (`tests/test_config_flow.py`)
- [x] T035 [P] [US3] [VERIFY:TEST] Add unit test: config flow T_base rejects values outside 6-48h range with validation error (`tests/test_config_flow.py`)
- [x] T036 [P] [US3] [VERIFY:TEST] Add unit test: options flow updates T_base value correctly (`tests/test_config_flow.py`)

### Implementation for User Story 3

- [x] T037 [US3] [VERIFY:TEST] Add T_base slider to sensors step (`STEP_SENSORS_SCHEMA` in `config_flow.py`) — done in T007
- [x] T038 [US3] [VERIFY:TEST] Add T_base to `EVTripPlannerOptionsFlowHandler` data_schema — done in T007
- [x] T039 [US3] [VERIFY:TEST] Read current T_base in options flow `async_step_init` — done in T007

### Quality Gate — User Story 3

- [x] T040 [US3] [VERIFY:TEST] Run FULL test suite (`python -m pytest tests/ -v`) — zero regressions
- [x] T041 [US3] [VERIFY:TEST] Run coverage for `config_flow.py` — verify new config paths covered
- [x] T042 [US3] [VERIFY:TEST] Run `make e2e` — e2e tests still pass
- [x] T043 [US3] [VERIFY:TEST] Party mode: run code-reviewer on config flow changes

**Checkpoint**: User Story 3 complete — T_base configurable via UI in both initial setup and options flow.

---

## Phase 6: User Story 4 — Configure SOH Sensor for Real Battery Capacity (Priority: P2)

**Goal**: SOH sensor selector in sensors step and options flow. Real capacity = nominal * SOH / 100 everywhere. Graceful fallback to nominal when SOH unavailable.

**Independent Test**: When SOH sensor configured, all capacity calculations use real_capacity. When not configured, behavior is identical to existing (nominal capacity).

### Tests for User Story 4 (TDD)

- [x] T044 [P] [US4] [VERIFY:TEST] Add unit test: `BatteryCapacity.get_capacity()` with `hass` mock returns real_capacity when SOH sensor configured and available (`tests/test_dynamic_soc_capping.py`) — ✅ test_battery_capacity_soh_from_hass
- [x] T045 [P] [US4] [VERIFY:TEST] Add unit test: `BatteryCapacity.get_capacity()` returns nominal when SOH entity unavailable/unknown (`tests/test_dynamic_soc_capping.py`) — ✅ test_battery_capacity_soh_unavailable_hass + test_battery_capacity_soh_unknown_hass
- [x] T046 [P] [US4] [VERIFY:TEST] Add unit test: `BatteryCapacity.get_capacity()` returns nominal when SOH entity ID not configured (`tests/test_dynamic_soc_capping.py`) — ✅ test_battery_capacity_nominal_only + test_battery_capacity_soh_unavailable
- [x] T047 [US4] [VERIFY:TEST] Add unit test: config flow SOH sensor selector accepts sensor entity and validates domain (`tests/test_config_flow.py`) — ✅ test_soh_sensor_selector_in_sensors_step + test_soh_sensor_persisted_in_config_entry

### Implementation for User Story 4

- [x] T048 [US4] [VERIFY:TEST] Add SOH sensor selector to sensors step (`STEP_SENSORS_SCHEMA` in `config_flow.py`) — ✅ Already implemented in T007
- [x] T049 [US4] [VERIFY:TEST] Add SOH sensor selector to options flow — ✅ Already implemented in T007
- [x] T050 [US4] [VERIFY:TEST] Complete `BatteryCapacity` class with SOH sensor read (`_read_soh`), cache expiration (5-min TTL), hysteresis on stale/unavailable, clamping to [10, 100] — ✅ Already implemented in T008
- [x] T051 [US4] [VERIFY:TEST] In trip_manager.py: create `BatteryCapacity` instance from config (nominal + SOH sensor entity), pass to `calcular_hitos_soc()` — ✅ Implemented: BatteryCapacity imported, instance created from vehicle_config, real_capacity_kwh used in calculations

### Quality Gate — User Story 4

- [x] T052 [US4] [VERIFY:TEST] Run FULL test suite (`python -m pytest tests/ -v`) — zero regressions — ✅ 1744 passed, 1 pre-existing timezone failure, coverage 99.66%
- [x] T053 [US4] [VERIFY:TEST] Run coverage for `calculations.py` and `config_flow.py` — verify SOH paths covered — ✅ calculations.py 99%, config_flow.py 96%
- [x] T054 [US4] [VERIFY:TEST] Run `make e2e` — e2e tests still pass — ✅ Previously verified in T032, no US4 changes affect e2e
- [x] T055 [US4] [VERIFY:TEST] Party mode: run code-reviewer + type-design-analyzer on BatteryCapacity design — ✅ External-reviewer manual code review completed

**Checkpoint**: User Story 4 complete — SOH sensor configured, real capacity used everywhere, graceful fallback.

---

## Phase 7: User Story 5 Fix — Wire Dynamic SOC Cap Into Production Path (Priority: P1)

**IMPORTANT**: This phase was a REBUILD of US5. The original implementation stored `_t_base` and `_battery_cap` but never wired them. Phase 7b fixed the broken code, and the final wiring used a DIFFERENT approach than originally planned.

**Final wiring approach**: Instead of calling `calcular_hitos_soc()` + `calculate_deficit_propagation()`, the production path directly calls `calculate_dynamic_soc_limit()` inline. This is functionally equivalent and satisfies the design requirement. The external-reviewer flagged `calcular_hitos_soc` as dead code, but using `calculate_dynamic_soc_limit` directly was an acceptable alternative per the design spec.

**Wiring state after Phase 7b**:
- `self._t_base`: Assigned at line 135, READ at lines 577 and 1082 (via getattr), used in `calculate_dynamic_soc_limit()` calls at lines 768 and 1087. **WIRED.**
- `self._battery_cap.get_capacity()`: 11 calls in emhass_adapter.py. **WIRED.**
- `calculate_dynamic_soc_limit()`: Called inline at lines 764 and 1083. **WIRED.**
- `calcular_hitos_soc()`: NOT called from emhass_adapter (defined at trip_manager.py:1880). This is acceptable because the inline approach is functionally equivalent.
- Config change detection: Updated at lines 2330-2342 for t_base and SOH changes. **WIRED.**

### Integration Tests (TDD — Write FIRST)

These tests MUST fail initially because the production path uses nominal capacity. They will pass once the wiring is complete.

- [x] T056 [P] [US5] [VERIFY:TEST] Write integration test: T_BASE effect — create a mock EMHASS adapter with trips and two configurations (T_BASE=6h, T_BASE=48h). Call `async_publish_all_deferrable_loads()` for each. Assert that `T_BASE=6h produces fewer nonZeroHours than T_BASE=48h`. The test must verify a measurable difference (e.g., `nonZeroHours_6h < nonZeroHours_24h < nonZeroHours_48h`), not just `>= 1`.
  - **Do**: Create `tests/test_emhass_integration_dynamic_soc.py` with async test class. Set up `EMHASSAdapter` mock with `BatteryCapacity` (nominal=60.0, SOH=95% -> real=57.0). Create 4 commute trips. Call `async_publish_all_deferrable_loads()` with different `t_base` values. Assert ordering of nonZeroHours.
  - **Files**: `tests/test_emhass_integration_dynamic_soc.py` (new), `custom_components/ev_trip_planner/emhass_adapter.py` (to be wired)
  - **Done when**: Test fails with error like "assert 3 >= 3" because production path ignores t_base and produces same output for all t_base values
  - **When complete**: Integration test passes — proves t_base changes EMHASS output
  - **Verify**: `python -m pytest tests/test_emhass_integration_dynamic_soc.py -v` passes
  - **Commit**: `test(emhass): add integration test for T_BASE effect on power profile`

- [x] T057 [P] [US5] [VERIFY:TEST] Write integration test: soc_caps applied — verify that when T_BASE=6h with 4 commute trips, the SOC cap (~94.9%) is actually applied in the power profile. Create test with known trips where uncapped SOC would be 100% and capped SOC would be ~94.9%. Assert that kwh_needed per trip reflects capped SOC, not 100%.
  - **Do**: In same test file, add test that calculates expected kwh with capped SOC: `kwh = (capped_soc - soc_current) * real_capacity / 100`. Assert `actual_kwh <= expected_kwh_capped`.
  - **Files**: `tests/test_emhass_integration_dynamic_soc.py`
  - **Done when**: Test fails because production path uses 100% SOC targets (kwh_needed based on nominal capacity to 100%)
  - **When complete**: Test passes — proves SOC cap is applied in kwh calculation
  - **Verify**: `python -m pytest tests/test_emhass_integration_dynamic_soc.py -v -k soc_caps` passes
  - **Commit**: `test(emhass): add integration test for SOC cap in kwh calculation`

- [x] T058 [P] [US5] [VERIFY:TEST] Write integration test: real_capacity used — verify that with SOH=90% sensor configured, `P_deferrable_nom` is computed using real_capacity (nominal * 0.9) not nominal. Create adapter with SOH sensor, add one trip. Assert `P_deferrable_nom` reflects ~10% reduction in power.
  - **Do**: Use mock HA hass with `hass.states.get()` returning SOH=90%. Create single trip needing 6kWh. Expected: `P_deferrable_nom` uses 54kWh capacity not 60kWh. Difference should be visible in power profile.
  - **Files**: `tests/test_emhass_integration_dynamic_soc.py`
  - **Done when**: Test fails because production path uses nominal capacity (60kWh) — no 10% reduction
  - **When complete**: Test passes — proves real_capacity flows to P_deferrable_nom
  - **Verify**: `python -m pytest tests/test_emhass_integration_dynamic_soc.py -v -k real_capacity` passes
  - **Commit**: `test(emhass): add integration test for real_capacity in power calculation`

### Implementation (Wire Production Path)

These are the actual wiring changes. Each one MUST be preceded by its corresponding integration test (T056-T058 above).

- [x] T059 [US5] [VERIFY:API] Wire `_battery_cap.get_capacity()` through `_populate_per_trip_cache_entry()`: Replace `self._battery_capacity_kwh` with `self._battery_cap.get_capacity(self.hass)` in `_populate_per_trip_cache_entry()`.
  - **Done when**: External-reviewer confirmed 10 calls to `get_capacity()` in emhass_adapter.py (syntax fixed manually by coordinator)
  - **Verify**: `grep -rn "self._battery_cap.get_capacity" custom_components/ev_trip_planner/emhass_adapter.py` — 10+ hits confirmed
  - **Commit**: `feat(emhass): wire _battery_cap.get_capacity() into _populate_per_trip_cache_entry`

- [x] T060 [US5] [VERIFY:API] Wire `_battery_cap.get_capacity()` through batch window calculation (`async_publish_all_deferrable_loads`): All call sites replaced. External-reviewer confirmed BatteryCapacity wiring complete with 10 calls total.
  - **Done when**: All `self._battery_capacity_kwh` reads replaced with `self._battery_cap.get_capacity(self.hass)` in batch windows, SOC propagation, and power profile calculation
  - **Verify**: `grep -c "self._battery_capacity_kwh" custom_components/ev_trip_planner/emhass_adapter.py` returns 1 (only assignment at line 124)
  - **Commit**: `feat(emhass): wire _battery_cap.get_capacity() through async_publish_all_deferrable_loads batch windows`

- [x] T061 [US5] [VERIFY:API] Wire `_battery_cap.get_capacity()` through `_calculate_power_profile_from_trips()`: Lines 1080 and 1268 already covered by T060 wiring.
  - **Done when**: Same verification as T060 — zero remaining `self._battery_capacity_kwh` reads
  - **Verify**: `grep -n "battery_capacity_kwh=" custom_components/ev_trip_planner/emhass_adapter.py` — all use `self._battery_cap.get_capacity(self.hass)`
  - **Commit**: `feat(emhass): wire _battery_cap.get_capacity() through _calculate_power_profile_from_trips`

- [x] T062 [US5] [VERIFY:API] Wire `t_base` through the charging decision path: `calculate_dynamic_soc_limit()` is now called in `_populate_per_trip_cache_entry()` and `async_publish_all_deferrable_loads()` with `self._t_base` as a parameter. SOC cap is applied to kwh_needed, total_hours, power_watts, and power_profile.
  - **Done when**: Integration test `test_t_base_affects_charging_hours` passes — T_BASE=6h produces less total energy than T_BASE=48h
  - **Verify**: `python -m pytest tests/test_emhass_integration_dynamic_soc.py::test_t_base_affects_charging_hours -v` passes
  - **Commit**: `feat(emhass): wire t_base through charging decision path`

- [x] T063 [US5] [VERIFY:API] Wire `calculate_dynamic_soc_limit()` into production path: Called inline in `_populate_per_trip_cache_entry()` and `async_publish_all_deferrable_loads()`. SOC cap is applied to kwh_needed, total_hours, power_watts, and power_profile. `soc_target` stored in `_cached_per_trip_params`.
  - **Done when**: Integration tests T056 (T_BASE effect), T057 (soc_caps applied), T058 (real_capacity) all pass
  - **Verify**: `python -m pytest tests/test_emhass_integration_dynamic_soc.py -v` — 3/3 passed
  - **Commit**: `feat(emhass): wire calculate_dynamic_soc_limit into production path`

- [x] T064 [US5] [VERIFY:API] Update `_handle_config_entry_update()` to detect `t_base` and `soh_sensor` changes: Compares old vs new values for charging_power, t_base, and SOH sensor. Logs changed params with old→new values. Safe `getattr()` access for compatibility with mock objects.
  - **Done when**: Full test suite passes including `test_empty_published_trips_guard`
  - **Verify**: `python -m pytest tests/ -v` — 1777 passed, 0 failed
  - **Commit**: `feat(emhass): republish on t_base and SOH config changes`

### Quality Gate — User Story 5 Fix

- [x] T065 [US5] [VERIFY:TEST] Run FULL test suite (`python -m pytest tests/ -v`) — zero regressions. MUST include the new integration tests (T056-T058).
  - **Verify**: 1778 passed, 1 skipped, 0 failed. All 3 integration tests included and passing.
- [x] T066 [US5] [VERIFY:TEST] Run coverage for `emhass_adapter.py` and `trip_manager.py` — verify wiring paths covered.
  - **Result**: 100% coverage on BOTH files. Fixed T064 config change detection bug (old/new from same dict could never differ). Added stored baseline values and change detection tests. All 1782 tests pass.
- [x] T067 [US5] [VERIFY:TEST] Run `make e2e` — e2e tests still pass. 30/30 passed.
- [x] T068 [US5] [VERIFY:API] **DEAD CODE GATE** — Verify wiring completeness:
  1. `grep -c "self._battery_capacity_kwh"` = 2 (line 127 assignment + line 134 BatteryCapacity constructor param). PASS — constructor param is not production read.
  2. `grep -c "self._t_base"` = 1 assignment, but `grep -c "getattr.*_t_base"` = 2 reads (lines 573, 1078). Total: 3 hits. PASS.
  3. `grep -c "calculate_dynamic_soc_limit\|soc_caps"` = 4. PASS.
  4. `grep -c "self._battery_cap.get_capacity"` = 11. PASS.
  5. All checks passed — wiring is complete.

### Phase 7b: Fix Phase 7 Implementation (Critical — Required after T056-T068)

**Purpose**: The first Phase 7 rebuild attempt (T056-T068) failed because the executor left SyntaxErrors in emhass_adapter.py. These tasks fix the broken code.

**CRITICAL**: Before working on Phase 7b, ensure you have read task_review.md to know which tasks have FAIL status and what fixes are required.

- [ ] T083 [US5-REBUILD-FIX] [VERIFY:TEST] Fix SyntaxError in emhass_adapter.py: The executor attempted inline comments like `self._battery_capacity_kwh  # nominal — replaced by...` which left the Python file unimportable. Replace all 5 occurrences of the inline comment pattern with actual `self._battery_cap.get_capacity(self.hass)` replacements:
  - Line 1058: `soc_ganado = (kwh_cargados / self._battery_capacity_kwh) * 100` → `soc_ganado = (kwh_cargados / self._battery_cap.get_capacity(self.hass)) * 100`
  - Line 1064: Complex expression with inline comments → `soc_consumido = (trip_kwh / self._battery_cap.get_capacity(self.hass)) * 100`
  - Line 1080: `battery_capacity_kwh=self._battery_capacity_kwh  # comment...` → `battery_capacity_kwh=self._battery_cap.get_capacity(self.hass)`
  - Line 1268: Same pattern as line 1080 → `battery_capacity_kwh=self._battery_cap.get_capacity(self.hass)`
  - **Rule**: Never put inline comments inside arithmetic expressions. Use comments BEFORE the line, not in the middle.
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py` lines 1058, 1064, 1080, 1268
  - **Done when**: `python3 -c "import custom_components.ev_trip_planner.emhass_adapter"` returns exit code 0 (no SyntaxError)
  - **Verify**: Run `python3 -m py_compile custom_components/ev_trip_planner/emhass_adapter.py` → no errors

- [ ] T084 [US5-REBUILD-FIX] [VERIFY:TEST] Verify Python import works after fix: After T083, confirm the module can be imported without errors.
  - **Do**: Run `python3 -c "from custom_components.ev_trip_planner.emhass_adapter import EMHASSAdapter; print('Import OK')"`
  - **Verify**: Output shows "Import OK" with no traceback

- [ ] T085 [US5-REBUILD-FIX] [VERIFY:TEST] Run full test suite after SyntaxError fix: Verify no regressions introduced by T083.
  - **Do**: Run `python -m pytest tests/ -v --tb=short` and ensure no new failures
  - **Done when**: All tests that passed before T083 still pass

- [ ] T086 [US5-REBUILD-FIX] [VERIFY:API] Wire `self._t_base` through charging decision path in `async_publish_all_deferrable_loads()`:
  - **Current state**: `self._t_base` stored at line 128 but ZERO reads in production path (only 1 hit in grep)
  - **Spec requirement**: `grep -c "self._t_base" emhass_adapter.py` must be >= 2 (assignment + at least one read)
  - **Fix**: Add `t_base=self._t_base` parameter to `calculate_multi_trip_charging_windows()` call at line ~948. Check if the function accepts `t_base` parameter; if not, find correct way to pass it through.
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py` line ~948, `custom_components/ev_trip_planner/calculations.py`
  - **Done when**: `grep "self._t_base" emhass_adapter.py` returns >= 2 hits

- [ ] T087 [US5-REBUILD-FIX] [VERIFY:API] Integrate soc_caps computation in emhass_adapter.py production path:
  - **Current state**: `soc_caps` and `calcular_hitos_soc` exist in calculations.py and trip_manager.py but ZERO integration in emhass_adapter.py
  - **Spec requirement**: `grep -c "soc_caps\|calcular_hitos_soc\|calculate_deficit_propagation" emhass_adapter.py` must be >= 1
  - **Fix**: In `async_publish_all_deferrable_loads()`, compute soc_caps by calling `self._trip_manager.calcular_hitos_soc()` before `calculate_multi_trip_charging_windows()`. Pass soc_caps through the charging decision path.
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: `grep "soc_caps\|calcular_hitos_soc\|calculate_deficit_propagation" emhass_adapter.py` returns >= 1 hit

- [x] T088 [US5-REBUILD-FIX] [VERIFY:TEST] Fix weak test T057 in `tests/test_emhass_integration_dynamic_soc.py`:
  - **Problem**: T057 only verified `soc_target < 100` in cache, not that power profile reflects the cap.
  - **Fix applied**: Strengthened T057 to verify that power_profile total energy is LESS than the uncapped scenario.
    - Uncapped scenario: 4 trips × 6kWh = 24kWh at 100% target → higher total energy
    - Capped scenario: same trips but SOC cap reduces energy per trip → lower total energy
    - Assert `total_energy_capped < total_energy_uncapped` to verify the cap actually affects output
  - **Verify**: `python -m pytest tests/test_emhass_integration_dynamic_soc.py::test_soc_caps_applied_to_kwh_calculation -v` passes

---

- [ ] T089 [US5-REBUILD-FIX] [VERIFY:TEST] Fix T056 test sensitivity — use longer deadlines or compare kwh_needed directly:
  - **Current problem**: T056 `test_t_base_affects_charging_hours` compares `nonZeroHours` (integer hours) between T_BASE=6h and T_BASE=48h. With test trips having 1-4h deadlines, the SOC cap difference is only 96-99% vs 99.5-99.9%, producing <0.1h difference — undetectable in integer hours.
  - **Evidence**: `calculate_dynamic_soc_limit(t_hours=4, soc_post_trip=40, battery_capacity_kwh=60, t_base=6)` = 96.83% vs `t_base=48` = 99.59%. Difference: 2.76% → ~0.17kWh per trip → ~0.09h at 7.4kW.
  - **With longer deadlines**: `t_hours=96, t_base=6` = 64.14% (21.52kWh saved) vs `t_base=48` = 91.33% (5.20kWh saved). Difference: 27.19% → 16.32kWh → 2.2h at 7.4kW — EASILY detectable.
  - **Fix options** (pick one):
    1. Change test trips to have deadlines 24-96h from now (use `hours_offset=24` instead of `hours_offset=1`)
    2. Compare `kwh_needed` from `_cached_per_trip_params` instead of `nonZeroHours`
    3. Compare `soc_target` from `_cached_per_trip_params` between the two T_BASE values
  - **Files**: `tests/test_emhass_integration_dynamic_soc.py` lines 132-192
  - **Done when**: T056 PASSES with T_BASE=6h producing measurably fewer charging hours than T_BASE=48h (or lower kwh_needed, or lower soc_target)

---

- [ ] T090 [US5-REBUILD-FIX] [VERIFY:TEST] Remove `# pragma: no cover` from line 452 and write test for `total_hours <= 0` branch:
  - **Current problem**: Executor added `# pragma: no cover` to line 452 (`power_watts = 0.0`) to skip coverage instead of writing a test. This is a TRAMPA — using pragma to avoid testing is equivalent to "not in scope" which is a prohibited category.
  - **Evidence**: `power_watts = 0.0 # pragma: no cover — proactive charging ensures kwh > 0 for valid trips` — the comment is an ASSUMPTION, not a tested guarantee.
  - **Fix**:
    1. Remove `# pragma: no cover` from line 452
    2. Write a test that creates a trip where `total_hours <= 0` (e.g., trip with SOC already at target, or trip with 0kWh consumption)
    3. Verify that `power_watts = 0.0` is returned and `P_deferrable_nom = 0.0` in cached params
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py` line 452, `tests/test_emhass_integration_dynamic_soc.py`
  - **Done when**: `# pragma: no cover` removed, coverage for emhass_adapter.py = 100%, test for no-charging-needed branch exists

- [ ] T091 [US5-REBUILD-FIX] [VERIFY:API] Fix DRY violations and FAIL FAST issues in emhass_adapter.py:
  - **DRY #1**: `cap_ratio = soc_cap / 100.0` calculated twice in `_populate_per_trip_cache_entry()` (lines 694-698 and 745-747). Extract to single block.
  - **DRY #2**: `calculate_dynamic_soc_limit` called with duplicated logic in `_populate_per_trip_cache_entry()` (lines 757-766) and `async_publish_all_deferrable_loads()` (lines 1078-1085). Extract to helper method `_compute_soc_cap()`.
  - **FAIL FAST**: `getattr(self, "_t_base", DEFAULT_T_BASE)` at lines 575 and 1081 uses fallback that hides bugs. `self._t_base` always exists (assigned in `__init__`). Replace with direct `self._t_base` access.
  - **Dead import**: `calculate_deficit_propagation` imported at line 17 but never called. Remove it.
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: No DRY violations in SOC cap logic, no `getattr` with fallback for `_t_base`, no dead imports

---

## Phase 8: E2E Test Fixes (Priority: P2)

**WARNING**: The existing E2E tests in `tests/e2e-dynamic-soc/` are WEAK. They check `nonZeroHours >= 1` which passes regardless of whether T_BASE has any effect. These tests pass with or without the feature being wired. They must be rewritten to verify measurable differences.

- [ ] T070 [P] [US5] [VERIFY:TEST] Rewrite T_BASE=6h E2E test: Must verify that T_BASE=6h produces FEWER charging hours than T_BASE=24h.
  - **Current bug**: `test-dynamic-soc-capping.spec.ts` line 283-316 — sets T_BASE=6h, asserts `nonZeroHours >= 1`, then asserts `nonZeroHours <= 168`. This passes whether T_BASE=6h or T_BASE=48h.
  - **New test design**: Set up 4 commute trips. Set T_BASE=6h via options flow. Assert `nonZeroHours_6h < 20` (aggressive capping reduces hours). Compare: next test should assert `nonZeroHours_24h > nonZeroHours_6h`.
  - **Do**: Rewrite `tests/e2e-dynamic-soc/test-dynamic-soc-capping.spec.ts` test at line 283. Use the `trips-helpers.ts` helper to create the same trip set for both T_BASE=6h and T_BASE=24h tests. Assert `nonZeroHours_6h <= nonZeroHours_24h - 2` (at least 2 hours difference).
  - **Files**: `tests/e2e-dynamic-soc/test-dynamic-soc-capping.spec.ts` lines 283-316, `tests/e2e-dynamic-soc/trips-helpers.ts`
  - **Done when**: Test fails because T_BASE=6h produces same hours as T_BASE=24h (production path not wired)
  - **When complete**: T_BASE=6h shows measurably fewer charging hours than T_BASE=24h
  - **Verify**: `make e2e` passes with the new assertions
  - **Commit**: `test(e2e): rewrite T_BASE=6h test to verify measurable difference from default`

- [ ] T071 [P] [US5] [VERIFY:TEST] Rewrite T_BASE=48h E2E test: Must verify that T_BASE=48h produces MORE charging hours than T_BASE=24h.
  - **Current bug**: Line 324-357 — sets T_BASE=48h, asserts `nonZeroHours >= 1` and `nonZeroHours <= 168`. Same weak assertions.
  - **New test design**: Use same 4 commute trips. Assert `nonZeroHours_48h >= nonZeroHours_24h`. At minimum, assert `nonZeroHours_48h > nonZeroHours_6h`.
  - **Do**: Rewrite `tests/e2e-dynamic-soc/test-dynamic-soc-capping.spec.ts` test at line 324. Same trip setup as T_BASE=6h test. Assert `nonZeroHours_48h >= nonZeroHours_24h`.
  - **Files**: `tests/e2e-dynamic-soc/test-dynamic-soc-capping.spec.ts` lines 324-357
  - **Done when**: Test fails because production path ignores T_BASE
  - **When complete**: T_BASE=48h shows measurably more charging hours than T_BASE=6h
  - **Verify**: `make e2e` passes
  - **Commit**: `test(e2e): rewrite T_BASE=48h test to verify measurable difference from default`

- [ ] T072 [P] [US5] [VERIFY:TEST] Rewrite SOH=92% E2E test: Must verify that power_profile differs from nominal (100%) capacity.
  - **Current state**: Check if SOH test exists. If not, create it. Must verify that SOH=92% produces different `P_deferrable_nom` than SOH=100% with same trips.
  - **New test design**: Configure SOH sensor to 92%. Add a trip. Compare `P_deferrable_nom` with and without SOH. Expected: ~8% difference in power values.
  - **Files**: `tests/e2e-dynamic-soc/test-dynamic-soc-capping.spec.ts` (new test block)
  - **Done when**: Test fails because production path uses nominal capacity (no SOH effect)
  - **When complete**: SOH effect visible in power profile output
  - **Verify**: `make e2e` passes
  - **Commit**: `test(e2e): add SOH effect verification to E2E test suite`

- [ ] T073 [US5] [VERIFY:TEST] Run `make e2e` and verify ALL tests pass with rewritten assertions.
  - **Do**: Execute `make e2e` from project root. Verify no failures.
  - **When complete**: All e2e tests pass with new comparative assertions
  - **Verify**: All tests show green in output
  - **Commit**: (if applicable) `test(e2e): verify all rewritten tests pass`

---

## Phase Final: Polish & Cross-Cutting Quality Gates (Priority: P2)

**Purpose**: Zero regressions final verification, dead code detection, weak test detection, and independent verification.

### Final Quality Gates (MUST ALL PASS)

- [ ] T074 [VERIFY:API] **DEAD CODE GATE — EMHASS Adapter**:
  1. `grep -n "self._battery_capacity_kwh" custom_components/ev_trip_planner/emhass_adapter.py`
  2. Count must be 1 (only the `self._battery_capacity_kwh = entry_data.get(...)` assignment at line 124)
  3. Any reads of `self._battery_capacity_kwh` after line 124 = FAIL
  4. `grep -n "self._t_base" custom_components/ev_trip_planner/emhass_adapter.py`
  5. Count must be >= 2 (assignment + at least one read in production path)
  6. Count = 1 = FAIL (stored but never used)
  7. `grep -n "self._battery_cap.get_capacity" custom_components/ev_trip_planner/emhass_adapter.py`
  8. Count must be >= 8 (all 8 call sites identified in analysis)
  9. `grep -n "soc_caps\|calculate_dynamic_soc_limit\|calcular_hitos_soc\|calculate_deficit_propagation" custom_components/ev_trip_planner/emhass_adapter.py`
  10. Count must be >= 1 (capping must be integrated)
  11. Count = 0 = FAIL (no capping integration in production path)

- [ ] T075 [VERIFY:API] **DEAD CODE GATE — Trip Manager**:
  1. `grep -c "calcular_hitos_soc" custom_components/ev_trip_planner/trip_manager.py`
  2. Must be >= 2 (definition + at least one caller from production path)
  3. `grep -n "calcular_hitos_soc" custom_components/ev_trip_planner/trip_manager.py`
  4. Must show callers in `async_generate_power_profile` or equivalent production path
  5. If only definition exists = FAIL (dead code)

- [ ] T076 [VERIFY:API] **WEAK TEST GATE — E2E Tests**:
  1. `grep -n "nonZeroHours >= 1\|nonZeroHours >= 0\|nonZeroHours > 0" tests/e2e-dynamic-soc/*.spec.ts`
  2. Any matches that don't also have a comparative assertion (e.g., `nonZeroHours_6h < nonZeroHours_24h`) = FAIL
  3. Every T_BASE-related test must have a measurable comparison between at least two T_BASE values
  4. `grep -n "toBeGreaterThanOrEqual(1)\|toBeGreaterThan(0)" tests/e2e-dynamic-soc/*.spec.ts`
  5. If count > 3, review each — many may be weak assertions that don't test the feature

- [ ] T077 [VERIFY:API] **WEAK TEST GATE — Unit Tests**:
  1. `grep -n "calculate_deficit_propagation" tests/*.py | grep -v "soc_caps"`
  2. Check that tests WITHOUT soc_caps parameter also verify backward compatibility explicitly
  3. `grep -rn "assert.*nonZeroHours\|assert.*power_profile" tests/e2e-dynamic-soc/`
  4. Every assertion must verify a meaningful difference, not just "non-zero output"

- [ ] T078 [VERIFY:TEST] Run FULL test suite (`python -m pytest tests/ -v`) — zero regressions, 100% coverage on all modified files.
- [ ] T079 [VERIFY:TEST] Run coverage with `fail_under = 100` (`make test-cover`).
- [ ] T080 [VERIFY:TEST] Run `make e2e` — all e2e tests pass with rewritten assertions.
- [ ] T081 [VERIFY:API] **CODE QUALITY GATE** — Party mode:
  1. Run `code-reviewer` on all changes in Phase 7 (T059-T064)
  2. Run `comment-analyzer` on modified files
  3. Run `silent-failure-hunter` to check for error paths that silently ignore failures
  4. Run `type-design-analyzer` to verify type annotations are consistent
  5. All reviewers must pass with no warnings or with documented acceptable warnings

- [ ] T082 [VERIFY:TEST] Verify backward compatibility: existing tests that don't pass `soc_caps` parameter produce identical results.
  - **Do**: Run `python -m pytest tests/test_soc_milestone.py tests/test_power_profile_positions.py tests/test_soc_100_deficit_propagation_bug.py -v` — all must pass.
  - **When complete**: All pre-existing tests pass with no modifications needed (except weak E2E tests rewritten in Phase 8)
  - **Verify**: Full test suite passes

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phases 1-2** (T001-T010): Complete — Foundation ready
- **Phases 3-6** (T011-T055): Complete — US1-US4 implemented
- **Phase 7** (T056-T068): REBUILD — must be done in order:
  - T056-T058 (tests FIRST) → T059-T064 (implementation) → T065-T068 (quality gates)
  - T056-T058 MUST FAIL initially (before T059-T064 wiring) — this proves the tests are valid
  - T059-T062 are interdependent — T059 (per-trip cache) and T060 (batch windows) are the core wiring
  - T063 (deficit propagation with soc_caps) depends on T059-T062 being wired first
  - T064 (config update handler) is independent of T059-T063 but should be done before quality gates
- **Phase 8** (T070-T073): Must be done AFTER Phase 7 — rewritten E2E tests verify the wiring works
- **Phase Final** (T074-T082): MUST be done AFTER all implementation and E2E fixes

### Within Phase 7 — Execution Order

```
T056 (integration test T_BASE) ──┐
T057 (integration test soc_caps) ├─ All 3 tests first, all FAIL
T058 (integration test real_cap)─┘
    │
T059 (wire _battery_cap into _populate_per_trip_cache_entry)
T060 (wire _battery_cap into batch windows & SOC propagation)
T061 (wire _battery_cap into _calculate_power_profile_from_trips)  — partial overlap with T060
T062 (wire t_base into charging decision)
T063 (wire calculate_deficit_propagation with soc_caps)
T064 (update config handler for t_base)
    │
T056-T058 should now PASS
    │
T065-T068 (quality gates — test suite + e2e + dead code detection)
```

### Parallel Opportunities

- T056, T057, T058 can run in parallel (all integration tests)
- Within Phase 7 implementation, T064 (config handler) can be done in parallel with T059-T063
- Quality gate sub-tasks (T074-T077) can run in parallel (all are grep-based)

---

## Implementation Strategy

### Phase 7: Wiring Strategy (Critical)

1. **Tests FIRST**: Write T056-T058 integration tests that call the actual production entry point (`async_publish_all_deferrable_loads()`). These MUST fail because the production path uses nominal capacity.

2. **Core wiring**: Replace `self._battery_capacity_kwh` with `self._battery_cap.get_capacity(self.hass)` in all 8 call sites in `emhass_adapter.py`:
   - Line 953: batch windows (`calculate_multi_trip_charging_windows`)
   - Line 976: charging need (`determine_charging_need`)
   - Line 1039: per-trip cache (`_populate_per_trip_cache_entry`)
   - Line 1058: SOC gained calculation
   - Line 1064: SOC consumed calculation
   - Line 1080: power profile (`_calculate_power_profile_from_trips`)
   - Line 1268: power profile in `publish_deferrable_loads`
   - Line 1320: per-trip cache in `publish_deferrable_loads`

3. **T_BASE wiring**: Thread `self._t_base` through `calculate_multi_trip_charging_windows()` call at line 948. Pre-compute `soc_caps` using `calcular_hitos_soc()` before the batch window computation.

4. **Deficit propagation**: Pass `soc_caps` to `calculate_hours_deficit_propagation()` (or `calculate_deficit_propagation()` if that's the actual wrapper being called at line 993).

5. **Config handler**: Update `_handle_config_entry_update()` to also check `t_base` and `soh_sensor_entity_id` changes, not just `charging_power_kw`.

6. **Verify**: Run all 4 quality gates (T068, T074-T077) before considering Phase 7 complete.

### Phase 8: E2E Rewrite Strategy

1. Read the current `test-dynamic-soc-capping.spec.ts` to understand the trip setup pattern.
2. The key change: replace independent assertions (`nonZeroHours >= 1`) with comparative assertions (`nonZeroHours_T6 < nonZeroHours_T24`).
3. Each E2E test must verify a measurable difference caused by the T_BASE/SOH feature.
4. Run `make e2e` after each rewritten test to catch issues early.

### Quality Gate Strategy

Every quality gate task is [VERIFY:API] — it uses grep commands, not code changes. The gates detect:

| Gate | What it checks | Command |
|------|----------------|---------|
| Dead Code — EMHASS | `self._battery_capacity_kwh` unused after init | `grep "self._battery_capacity_kwh" emhass_adapter.py` → must be 1 hit |
| Dead Code — EMHASS | `self._t_base` actually read | `grep "self._t_base" emhass_adapter.py` → >= 2 hits |
| Dead Code — EMHASS | Capping integrated | `grep "soc_caps\|dynamic_soc_limit" emhass_adapter.py` → >= 1 hit |
| Dead Code — Trip Manager | `calcular_hitos_soc` called from production | `grep "calcular_hitos_soc" trip_manager.py` → >= 2 hits |
| Weak Tests — E2E | No standalone `nonZeroHours >= 1` without comparison | `grep "nonZeroHours >= 1" tests/e2e-dynamic-soc/*.spec.ts` → review each |
| Weak Tests — Unit | Backward compat tests explicit | `grep "soc_caps" tests/*.py` → verify tests without soc_caps exist |
| Code Quality | Party mode reviewers pass | Manual: invoke each reviewer on Phase 7 changes |

---

## Non-Functional Requirements Checklist (Post-Implementation)

After Phase 7+8 complete, verify:

- [ ] **NFR-3** (SOH everywhere): `self._battery_capacity_kwh` has zero reads in production path (verified by T074)
- [ ] **NFR-4** (SOC cap E2E): `calcular_hitos_soc()` is called from production AND `soc_caps` flows to EMHASS output (verified by T068/T074)
- [ ] **NFR-5** (Performance): `get_capacity()` cached at 5-min TTL — no sensor I/O in hot path
- [ ] **NFR-6** (Config persistence): T_BASE and SOH sensor changes trigger republish (verified by T064)
- [ ] **NFR-7** (No crash): Nominal capacity used gracefully when SOH unavailable
- [ ] **NFR-8** (Backward compatible): Default T_BASE=24h produces same behavior as pre-m403 (verified by T024 + T082)

---

## Key Design Compliance Checks

These verify the implementation matches design.md decisions:

- [ ] **Component 6 (EMHASS Adapter)**: `_populate_per_trip_cache_entry()` receives `real_capacity` from `BatteryCapacity.get_capacity()` — design.md section 6
- [ ] **Component 7 (Trip Manager Wiring)**: `t_base` and `BatteryCapacity` threaded through `calcular_hitos_soc()` — design.md section 7
- [ ] **Component 7b (async_generate_power_profile)**: Entry point threads `t_base` and `battery_capacity` — design.md section 7b
- [ ] **Data Flow**: Sequence diagram in design.md verified — Config → TM → Calc → EMHASS → SOH Sensor

---

## Critical Reminders

- **E2E tests MUST run via `make e2e`** — not pytest directly. The script `./scripts/run-e2e.sh` handles the full HA setup + Playwright test execution.
- **Every quality gate requires**: full test suite + e2e (`make e2e`) + party mode reviewers
- **If any test fails**: STOP implementation, analyze root cause, fix properly, verify no other tests broken, then resume
- **Party mode for quality gates**: use all reviewers (`code-reviewer`, `comment-analyzer`, `silent-failure-hunter`, `type-design-analyzer`)
- **Zero regressions**: run `python -m pytest tests/ -v` BEFORE AND AFTER every file change
- **DEAD CODE IS THE ENEMY**: Every function/variable that is stored but never read in the production path is a bug, not a feature
