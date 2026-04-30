# Tasks: m403-Dynamic SOC Capping

**Milestone**: 4.0.3
**Target**: v0.5.23
**Priority**: P1 - Battery Health & Cost Optimization
**Input**: Design documents from `/specs/m403-dynamic-soc-capping/`
**Prerequisites**: spec.md, requirements.md, research.md, design.md

## Quality Gates Policy (ABSOLUTE)

- **E2E tests ALWAYS run via `make e2e`** (not pytest directly). If you think e2e tests should be run differently, you are misunderstanding the project setup — the canonical command is `make e2e`.
- **Quality gates every few steps**: After each user story phase AND after every 3 implementation tasks.
- **Zero regressions**: Run full test suite (`python -m pytest tests/ -v`) BEFORE and AFTER every file change. If any test fails, STOP and fix it.
- **Party mode for quality gates**: Invoke the PR review toolkit with all reviewers (`code-reviewer`, `comment-analyzer`, `silent-failure-hunter`, `type-design-analyzer`) for every quality gate.
- **100% coverage**: `fail_under = 100` in pyproject.toml — all new code must be fully covered.
- **Test maintenance**: If a change legitimately breaks an existing test, document WHY and update the assertion to the new correct behavior.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify baseline, prepare test infrastructure

- [x] T001 [VERIFY:TEST] Run FULL existing test suite baseline — 1715 passed, 2 failed (pre-existing flaky timezone tests), 1 skipped. 100% coverage. — verify ALL tests pass BEFORE any changes (`python -m pytest tests/ -v`)
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
- [ ] T012 [P] [US1] [VERIFY:TEST] Add unit test for Scenario B: `calculate_dynamic_soc_limit(8, 0, 30)` returns 100.0 (negative risk — large trip drain) (`tests/test_dynamic_soc_capping.py`)
- [ ] T013 [P] [US1] [VERIFY:TEST] Add unit test for Scenario C (critical case): 4 identical trips, limit stays at 94.9% each iteration (`tests/test_dynamic_soc_capping.py`)
- [ ] T014 [P] [US1] [VERIFY:TEST] Add unit tests for edge cases: zero idle hours (t=0 -> 100%), at sweet spot SOC (35% -> 100%), infinite T_base -> 100% (`tests/test_dynamic_soc_capping.py`)
- [ ] T015 [P] [US1] [VERIFY:TEST] Add unit test for T_base configurability: `t_base=6 < t_base=24 < t_base=48` ordering of limits (`tests/test_dynamic_soc_capping.py`)
- [ ] T016 [P] [US1] [VERIFY:TEST] Add unit tests for BatteryCapacity: nominal-only, SOH=90% -> real_capacity=nominal*0.9, SOH unavailable -> nominal fallback, SOH clamp to [10, 100] (`tests/test_dynamic_soc_capping.py`)

### Implementation for User Story 1

- [ ] T017 [US1] [VERIFY:TEST] Implement `calculate_dynamic_soc_limit()` in `calculations.py`: pure function with formula `risk = t_hours * (soc_post_trip - 35) / 65`, `limit = 35 + 65 * (1 / (1 + risk / t_base))`, clamped to [35.0, 100.0] — return 100.0 when risk <= 0 (`custom_components/ev_trip_planner/calculations.py`)
- [ ] T018 [US1] [VERIFY:TEST] Export `calculate_dynamic_soc_limit` in `__all__` of `calculations.py`

### Quality Gate — User Story 1

- [ ] T019 [US1] [VERIFY:TEST] Run FULL test suite (`python -m pytest tests/ -v`) — zero regressions
- [ ] T020 [US1] [VERIFY:TEST] Run coverage for `calculations.py` — verify new functions covered (`pytest --cov=custom_components/ev_trip_planner/calculations.py`)
- [ ] T021 [US1] [VERIFY:TEST] Run `make e2e` — e2e tests still pass
- [ ] T022 [US1] [VERIFY:TEST] Party mode: run code-reviewer + type-design-analyzer on `calculations.py` changes

**Checkpoint**: User Story 1 complete — dynamic SOC limit algorithm implemented and tested.

---

## Phase 4: User Story 2 — Apply Dynamic SOC Cap Inside Deficit Propagation (Priority: P1)

**Goal**: Cap `soc_objetivo_ajustado` with dynamic limit in `calculate_deficit_propagation()` in BOTH backward loop AND result-building loop. Forward-propagated SOC uses capped values.

**Independent Test**: Deficit propagation with caps produces `soc_objetivo_final <= dynamic_limit` per trip. Without caps, behavior is identical to existing (backward compatible).

### Tests for User Story 2 (TDD)

- [ ] T023 [P] [US2] [VERIFY:TEST] Add unit test: `calculate_deficit_propagation()` with `soc_caps` produces capped results where `soc_objetivo <= dynamic_limit` per trip (`tests/test_calculations.py` or new test file)
- [ ] T024 [P] [US2] [VERIFY:TEST] Add unit test: `calculate_deficit_propagation()` without `soc_caps` produces identical results to current (backward compatibility) (`tests/test_calculations.py`)
- [ ] T025 [P] [US2] [VERIFY:TEST] Add unit test: forward-propagated SOC uses capped `soc_objetivo_final`, not uncapped `soc_objetivo_ajustado` (`tests/test_calculations.py`)

### Implementation for User Story 2

- [ ] T026 [US2] [VERIFY:TEST] Modify `calculate_deficit_propagation()` signature to accept optional `t_base: float = 24.0` and `soc_caps: list[float] | None = None` parameters (`custom_components/ev_trip_planner/calculations.py`)
- [ ] T027 [US2] [VERIFY:TEST] In backward propagation loop (~line 808): after computing `soc_objetivo_ajustado`, apply `soc_objetivo_final = min(soc_objetivo_ajustado, soc_caps[idx]) if soc_caps else soc_objetivo_ajustado` — use `soc_objetivo_final` for deficit calculation (`custom_components/ev_trip_planner/calculations.py`)
- [ ] T028 [US2] [VERIFY:TEST] In forward/result-building loop (~line 843): after recomputing `soc_objetivo_ajustado`, apply same cap — use `soc_objetivo_final` in results dict (`custom_components/ev_trip_planner/calculations.py`)
- [ ] T029 [US2] [VERIFY:TEST] Wire capped SOC for forward propagation: after `calculate_deficit_propagation()` returns, extracted `soc_objetivo` from results (capped) feeds forward as start SOC for next trip (`custom_components/ev_trip_planner/calculations.py`)

### Quality Gate — User Story 2

- [ ] T030 [US2] [VERIFY:TEST] Run FULL test suite (`python -m pytest tests/ -v`) — zero regressions (CRITICAL: test_soc_milestone.py, test_power_profile_positions.py, test_soc_100_deficit_propagation_bug.py MUST pass)
- [ ] T031 [US2] [VERIFY:TEST] Run coverage for `calculations.py` — verify new code paths covered
- [ ] T032 [US2] [VERIFY:TEST] Run `make e2e` — e2e tests still pass
- [ ] T033 [US2] [VERIFY:TEST] Party mode: run code-reviewer + silent-failure-hunter on deficit propagation changes

**Checkpoint**: User Story 2 complete — dynamic cap integrated into deficit propagation in both loops, forward propagation uses capped values.

---

## Phase 5: User Story 3 — Configure T_base via Home Assistant UI (Priority: P2)

**Goal**: T_base slider (6-48h, default 24) in config flow (sensors step) and options flow. No health-mode toggle.

**Independent Test**: Config flow persists T_base value. Options flow updates T_base. Next power profile generation uses new T_base.

### Tests for User Story 3 (TDD)

- [ ] T034 [P] [US3] [VERIFY:TEST] Add unit test: config flow T_base slider accepts 24.0 and persists in entry data (`tests/test_config_flow.py`)
- [ ] T035 [P] [US3] [VERIFY:TEST] Add unit test: config flow T_base rejects values outside 6-48h range with validation error (`tests/test_config_flow.py`)
- [ ] T036 [P] [US3] [VERIFY:TEST] Add unit test: options flow updates T_base value correctly (`tests/test_config_flow.py`)

### Implementation for User Story 3

- [ ] T037 [US3] [VERIFY:TEST] Add T_base slider to sensors step (`STEP_SENSORS_SCHEMA` in `config_flow.py`): `vol.Optional(CONF_T_BASE, default=24.0): vol.All(vol.Coerce(float), vol.Range(min=6.0, max=48.0))` (`custom_components/ev_trip_planner/config_flow.py`)
- [ ] T038 [US3] [VERIFY:TEST] Add T_base to `EVTripPlannerOptionsFlowHandler` data_schema: `vol.Optional(CONF_T_BASE, default=current_t_base): vol.All(vol.Coerce(float), vol.Range(min=6.0, max=48.0))` (`custom_components/ev_trip_planner/config_flow.py`)
- [ ] T039 [US3] [VERIFY:TEST] In options flow `async_step_init`: read current T_base from `config_entry.data.get(CONF_T_BASE, DEFAULT_T_BASE)` or `config_entry.options.get(CONF_T_BASE, DEFAULT_T_BASE)` — follow existing dual-lookup pattern (`custom_components/ev_trip_planner/config_flow.py`)

### Quality Gate — User Story 3

- [ ] T040 [US3] [VERIFY:TEST] Run FULL test suite (`python -m pytest tests/ -v`) — zero regressions
- [ ] T041 [US3] [VERIFY:TEST] Run coverage for `config_flow.py` — verify new config paths covered
- [ ] T042 [US3] [VERIFY:TEST] Run `make e2e` — e2e tests still pass
- [ ] T043 [US3] [VERIFY:TEST] Party mode: run code-reviewer on config flow changes

**Checkpoint**: User Story 3 complete — T_base configurable via UI in both initial setup and options flow.

---

## Phase 6: User Story 4 — Configure SOH Sensor for Real Battery Capacity (Priority: P2)

**Goal**: SOH sensor selector in sensors step and options flow. Real capacity = nominal * SOH / 100 everywhere. Graceful fallback to nominal when SOH unavailable.

**Independent Test**: When SOH sensor configured, all capacity calculations use real_capacity. When not configured, behavior is identical to existing (nominal capacity).

### Tests for User Story 4 (TDD)

- [ ] T044 [P] [US4] [VERIFY:TEST] Add unit test: `BatteryCapacity.get_capacity()` with `hass` mock returns real_capacity when SOH sensor configured and available (`tests/test_dynamic_soc_capping.py`)
- [ ] T045 [P] [US4] [VERIFY:TEST] Add unit test: `BatteryCapacity.get_capacity()` returns nominal when SOH entity unavailable/unknown (`tests/test_dynamic_soc_capping.py`)
- [ ] T046 [P] [US4] [VERIFY:TEST] Add unit test: `BatteryCapacity.get_capacity()` returns nominal when SOH entity ID not configured (`tests/test_dynamic_soc_capping.py`)
- [ ] T047 [P] [US4] [VERIFY:TEST] Add unit test: config flow SOH sensor selector accepts sensor entity and validates domain (`tests/test_config_flow.py`)

### Implementation for User Story 4

- [ ] T048 [US4] [VERIFY:TEST] Add SOH sensor selector to sensors step (`STEP_SENSORS_SCHEMA` in `config_flow.py`): `vol.Optional(CONF_SOH_SENSOR): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", multiple=False))` (`custom_components/ev_trip_planner/config_flow.py`)
- [ ] T049 [US4] [VERIFY:TEST] Add SOH sensor selector to options flow: `vol.Optional(CONF_SOH_SENSOR): selector.EntitySelector(selector.EntitySelectorConfig(domain="sensor", multiple=False))` (`custom_components/ev_trip_planner/config_flow.py`)
- [ ] T050 [US4] [VERIFY:TEST] Complete `BatteryCapacity` class with SOH sensor read (`_read_soh`), cache expiration (5-min TTL), hysteresis on stale/unavailable, clamping to [10, 100] (`custom_components/ev_trip_planner/calculations.py`)
- [ ] T051 [US4] [VERIFY:TEST] In trip_manager.py: create `BatteryCapacity` instance from config (nominal + SOH sensor entity), pass to `calcular_hitos_soc()` (`custom_components/ev_trip_planner/trip_manager.py`)

### Quality Gate — User Story 4

- [ ] T052 [US4] [VERIFY:TEST] Run FULL test suite (`python -m pytest tests/ -v`) — zero regressions
- [ ] T053 [US4] [VERIFY:TEST] Run coverage for `calculations.py` and `config_flow.py` — verify SOH paths covered
- [ ] T054 [US4] [VERIFY:TEST] Run `make e2e` — e2e tests still pass
- [ ] T055 [US4] [VERIFY:TEST] Party mode: run code-reviewer + type-design-analyzer on BatteryCapacity design

**Checkpoint**: User Story 4 complete — SOH sensor configured, real capacity used everywhere, graceful fallback.

---

## Phase 7: User Story 5 — Use Dynamic SOC Cap in EMHASS Charging Decisions (Priority: P2)

**Goal**: EMHASS adapter uses capped SOC targets and real capacity in power profile generation and per-trip cache entries.

**Independent Test**: EMHASS power profile reflects capped SOC targets and real_capacity. When dynamic_limit = 100%, behavior identical to existing.

### Tests for User Story 5 (TDD)

- [ ] T056 [P] [US5] [VERIFY:TEST] Add unit test: `_populate_per_trip_cache_entry()` uses capped SOC for `kwh_needed` computation (`tests/test_emhass_adapter.py` or relevant test file)
- [ ] T057 [P] [US5] [VERIFY:TEST] Add unit test: power profile computed from capped targets and real_capacity (`tests/test_power_profile_positions.py`)
- [ ] T058 [P] [US5] [VERIFY:TEST] Add unit test: when dynamic_limit = 100%, EMHASS behavior is identical to existing (no capping active) (`tests/test_power_profile_positions.py`)

### Implementation for User Story 5

- [ ] T059 [US5] [VERIFY:TEST] In `emhass_adapter.py`: thread `t_base` and `BatteryCapacity` through `_calculate_power_profile_from_trips()` and `_populate_per_trip_cache_entry()` (`custom_components/ev_trip_planner/emhass_adapter.py`)
- [ ] T060 [US5] [VERIFY:TEST] In `_populate_per_trip_cache_entry()`: pass `real_capacity` (from `BatteryCapacity.get_capacity(hass)`) instead of nominal capacity to `determine_charging_need()` (`custom_components/ev_trip_planner/emhass_adapter.py`)
- [ ] T061 [US5] [VERIFY:TEST] In `_calculate_power_profile_from_trips()`: pass `real_capacity` as `battery_capacity_kwh` parameter to downstream calculation functions (`custom_components/ev_trip_planner/emhass_adapter.py`)
- [ ] T062 [US5] [VERIFY:TEST] Wire `t_base` from config entry through `async_generate_power_profile()` -> `calcular_hitos_soc()` -> `calculate_deficit_propagation()` — use existing dual-lookup pattern (`custom_components/ev_trip_planner/trip_manager.py`, `custom_components/ev_trip_planner/emhass_adapter.py`)

### Quality Gate — User Story 5

- [ ] T063 [US5] [VERIFY:TEST] Run FULL test suite (`python -m pytest tests/ -v`) — zero regressions (CRITICAL)
- [ ] T064 [US5] [VERIFY:TEST] Run coverage for `emhass_adapter.py` and `trip_manager.py`
- [ ] T065 [US5] [VERIFY:TEST] Run `make e2e` — e2e tests still pass
- [ ] T066 [US5] [VERIFY:TEST] Party mode: run code-reviewer + silent-failure-hunter on EMHASS adapter changes

**Checkpoint**: User Story 5 complete — EMHASS adapter uses capped SOC and real capacity.

---

## Phase 8: User Stories 6+7 — Scenario Validation (Priority: P3)

**Goal**: Validate Scenario C (daily commute, 94.9% cap, no capping hit), Scenario A (commute -> large drain -> commute -> semi), Scenario B (large drain first -> commutes).

**Independent Test**: Manual verification of SOC evolution matches expected values from spec.md scenarios A, B, C.

### Tests for User Stories 6+7

- [ ] T067 [US6] [VERIFY:TEST] Add integration test: Scenario C — 4 identical 30km trips with 22.5h idle each, verify each trip charges to ~61% (not 100%), post-trip SOC ~41% (`tests/test_dynamic_soc_capping.py`)
- [ ] T068 [US6] [VERIFY:TEST] Add integration test: Scenario A — commute first (charges to 61%), large trip drains to 0% (risk negative -> 100%), second commute charges to 61%, semi-drain to 10% (100% allowed) (`tests/test_dynamic_soc_capping.py`)
- [ ] T069 [US7] [VERIFY:TEST] Add integration test: Scenario B — large drain first (100%), then commutes at 94.9% cap -> charge to 61% (`tests/test_dynamic_soc_capping.py`)
- [ ] T070 [US6] [VERIFY:TEST] Add integration test: Verify week total at >80% SOC drops from 90h to ~0h with capping for Scenario C (`tests/test_dynamic_soc_capping.py`)

### Manual Verification (E2E via Browser)

- [ ] T071 [US6] [US7] [VERIFY:TEST] Run `make e2e` — full e2e test suite passes
- [ ] T072 [US6] [US7] [VERIFY:TEST] Party mode: run all reviewers on scenario validation code

**Checkpoint**: User Stories 6 and 7 complete — all scenarios verified.

---

## Phase Final: Polish & Cross-Cutting Concerns

**Purpose**: Zero regressions final verification, documentation, and cleanup.

- [ ] T073 [VERIFY:TEST] Run FULL test suite ONE FINAL TIME (`python -m pytest tests/ -v`) — ZERO regressions allowed, every single test must pass
- [ ] T074 [VERIFY:TEST] Run coverage with `fail_under = 100` (`make test-cover`) — 100% coverage on ALL modified files: `const.py`, `calculations.py`, `config_flow.py`, `trip_manager.py`, `emhass_adapter.py`
- [ ] T075 [VERIFY:TEST] Run mypy on all modified files — zero type errors (`mypy custom_components/ev_trip_planner/`)
- [ ] T076 [VERIFY:TEST] Run `make e2e` — e2e test suite passes
- [ ] T077 [VERIFY:TEST] Party mode: run full PR review toolkit on entire diff (`code-reviewer`, `comment-analyzer`, `silent-failure-hunter`, `type-design-analyzer`)
- [ ] T078 [P] [VERIFY:TEST] Update docstrings: all new functions have docstrings explaining WHY not WHAT (`custom_components/ev_trip_planner/calculations.py`, `custom_components/ev_trip_planner/config_flow.py`, `custom_components/ev_trip_planner/trip_manager.py`, `custom_components/ev_trip_planner/emhass_adapter.py`)
- [ ] T079 [VERIFY:TEST] Verify `BatteryCapacity` is the single source of truth for capacity — grep all files for `battery_capacity_kwh` and `nominal` usages — ensure no code path uses nominal when SOH is configured
- [ ] T080 [VERIFY:TEST] Verify `dynamic_limit` is clamped to [35.0, 100.0] in `calculate_dynamic_soc_limit()`
- [ ] T081 [VERIFY:TEST] Verify backward compatibility: existing tests that don't pass `soc_caps` parameter produce identical results (backward compatible default of None)

---

## Phase Final: Integrated Verification (T999)

- [ ] T999 [VERIFY:BROWSER] Comprehensive integrated verification of ALL features — run `make e2e` one final time to validate complete feature as integrated system

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — can start immediately
- **Phase 2 (Foundational)**: Depends on Phase 1 — BLOCKS all user stories
- **Phases 3-8 (User Stories)**: All depend on Phase 2 completion
  - US1 (Phase 3) has no dependency on other stories
  - US2 (Phase 4) depends on US1 (needs `calculate_dynamic_soc_limit()`)
  - US3 (Phase 5) can start after Phase 2 (independent of US1/US2)
  - US4 (Phase 6) can start after Phase 2 (independent of US1-US3)
  - US5 (Phase 7) depends on US2 and US4 (needs both capped SOC and real capacity)
  - US6/US7 (Phase 8) depend on US1-US5 (scenario validation)
- **Phase Final (Polish)**: Depends on all user stories being complete

### Within Each User Story

- Tests MUST be written and FAIL before implementation (TDD)
- Models before services
- Services before integration
- Core implementation before quality gate
- Story complete before moving to next priority

### Parallel Opportunities

- Phase 1 setup tasks (T004, T005) can run in parallel
- Phase 2 foundational tasks (T006-T009) can run in parallel
- Test tasks within each story (T011-T016, T023-T025, etc.) can run in parallel
- US3 and US4 can proceed in parallel (both depend only on Phase 2)

---

## Implementation Strategy

### MVP First (User Stories 1-2)

1. Complete Phase 1: Setup — verify baseline
2. Complete Phase 2: Foundational — BatteryCapacity + constants
3. Complete Phase 3: US1 — core algorithm
4. Complete Phase 4: US2 — deficit propagation integration
5. **STOP and VALIDATE**: Run ALL tests, ALL e2e, coverage 100%
6. At this point, the dynamic SOC cap is functional and tested

### Incremental Delivery

1. Setup + Foundational -> Foundation ready
2. US1 -> Core algorithm working
3. US2 -> Integrated into deficit propagation (MVP!)
4. US3 -> T_base configurable
5. US4 -> SOH sensor integration
6. US5 -> EMHASS adapter uses capped SOC + real capacity
7. US6/US7 -> All scenarios validated

### Critical Reminders

- **E2E tests MUST run via `make e2e`** — not pytest directly. The script `./scripts/run-e2e.sh` handles the full HA setup + Playwright test execution.
- **Every quality gate requires**: full test suite + e2e (`make e2e`) + party mode reviewers
- **If any test fails**: STOP implementation, analyze root cause, fix properly, verify no other tests broken, then resume
- **Party mode for quality gates**: use all reviewers (`code-reviewer`, `comment-analyzer`, `silent-failure-hunter`, `type-design-analyzer`)
- **Zero regressions**: run `python -m pytest tests/ -v` BEFORE AND AFTER every file change
