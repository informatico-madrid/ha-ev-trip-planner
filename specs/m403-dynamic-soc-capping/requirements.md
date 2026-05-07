# Requirements: Dynamic SOC Capping

## Goal
Limit battery charging to a degradation-aware upper bound calculated from idle time and post-trip SOC, integrated as `min(required, dynamic_limit)` inside deficit propagation. SOH sensor always feeds real battery capacity. Zero regressions — all existing tests pass, code quality at maximum.

---

## User Stories

### US-1: Calculate dynamic SOC limit from trip parameters
**As a** system
**I want to** compute a continuous SOC upper bound from idle hours, projected post-trip SOC, and battery capacity
**So that** the system avoids unnecessary high-SOC charging when the car sits idle

**Acceptance Criteria:**
- [ ] AC-1.1: Formula is exact: `risk = t_hours * (soc_post_trip - 35) / 65`; `limit = 35 + 65 * (1 / (1 + risk / t_base))`
- [ ] AC-1.2: When `risk <= 0` (soc_post_trip <= 35 or t_hours == 0), returns 100.0
- [ ] AC-1.3: `t_base` defaults to 24.0, user-configurable 6-48h
- [ ] AC-1.4: `soc_base` is hardcoded to 35.0 (internal sweet spot), not user-configurable
- [ ] AC-1.5: For Scenario A (22h idle, 41% post-trip, 30kWh battery): limit == 94.9% (±1%)
- [ ] AC-1.6: For Scenario C (same inputs repeated 4x): limit stays at 94.9% each iteration

### US-2: Apply dynamic SOC cap inside deficit propagation
**As a** planner
**I want to** cap `soc_objetivo_ajustado` with the dynamic limit in `calculate_deficit_propagation()`
**So that** charging targets respect battery health without preventing trips from succeeding

**Acceptance Criteria:**
- [ ] AC-2.1: After computing `soc_objetivo_ajustado`, apply `soc_objetivo_final = min(soc_objetivo_ajustado, dynamic_limit)`
- [ ] AC-2.2: Dynamic limit is computed per-trip using the trip's projected idle hours and post-trip SOC
- [ ] AC-2.3: If a trip requires more charge than the dynamic limit, the trip requirement wins (full charge still allowed)
- [ ] AC-2.4: Cap applied to trip N does not cause SOC for trip N-1 to drop below that trip's required SOC. Verify: running deficit propagation with cap on trip 4 shows soc_objetivo for trip 1 unchanged from uncapped run
- [ ] AC-2.5: The `min()` formula ensures trips never charge ABOVE what they need. In practice, the dynamic limit (typically 85-100%) always exceeds normal trip SOC targets (30-61%), so the cap restricts surplus capacity, not trip needs. The hard invariant "trip energy needs always met" is guaranteed because the limit is only applied to surplus charging, not to trip requirements.
- [ ] AC-2.6: SOC cap is applied in BOTH the backward propagation loop AND the result-building loop of `calculate_deficit_propagation()` so that forward-propagated SOC values are consistent with capped targets
- [ ] AC-2.7: FR-7 is satisfied: `t_base` and SOH config values are threaded from config entry → trip_manager → `calculate_deficit_propagation()` (see FR-7)

### US-3: Configure T_base via Home Assistant UI
**As a** user
**I want to** set T_base (6-48h) in the EV Trip Planner integration configuration
**So that** I can tune how aggressively the system preserves battery health

**Acceptance Criteria:**
- [ ] AC-3.1: T_base slider appears in the battery health section (no health-mode toggle — always on)
- [ ] AC-3.2: T_base defaults to 24h
- [ ] AC-3.3: T_base accepts values 6-48h, rejects values outside range with validation error
- [ ] AC-3.4: Lower T_base produces tighter caps (aggressive preservation); higher T_base produces looser caps (conservative)
- [ ] AC-3.5: Changing T_base takes effect on the next power profile generation

### US-4: Configure SOH sensor for real battery capacity
**As a** user with battery degradation tracking
**I want to** select a Home Assistant sensor reporting State of Health (%)
**So that** the system uses real battery capacity (nominal × SOH/100) instead of nominal capacity everywhere

**Acceptance Criteria:**
- [ ] AC-4.1: SOH sensor selector appears in the sensors step of the config flow
- [ ] AC-4.2: SOH selector accepts only `sensor` domain entities
- [ ] AC-4.3: When SOH sensor is configured, real capacity = nominal_capacity × SOH_value / 100
- [ ] AC-4.4: When SOH sensor is not configured, system uses nominal capacity (no behavior change)
- [ ] AC-4.5: Real capacity feeds into ALL energy calculations: trip kWh estimation, deficit propagation, EMHASS params, power profile generation
- [ ] AC-4.6: Invalid SOH values (< 10 or > 100) are rejected with validation error
- [ ] AC-4.7: SOH value is used consistently everywhere capacity is used — no code path uses nominal capacity when SOH sensor is configured (SOLID: Single Responsibility, DRY)
- [ ] AC-4.8: SOH sensor integration is SOLID — `BatteryCapacity` abstraction encapsulates nominal + SOH, no duplicated capacity calculation across files (see FR-8)

### US-5: Use dynamic SOC limit in EMHASS charging decisions
**As a** power profile generator
**I want to** incorporate the dynamic SOC cap into EMHASS deferrable load parameters
**So that** the optimizer receives charging windows consistent with battery health limits

**Acceptance Criteria:**
- [ ] AC-5.1: EMHASS adapter uses the capped SOC target when building per-trip cache entries
- [ ] AC-5.2: `P_deferrable_nom = (capped_soc - soc_current) / 100 * real_capacity_kWh / charging_hours` (numerically different from uncapped by exactly `(soc_objetivo - capped_soc) / 100 * real_capacity_kWh / charging_hours`); charging window hours reflect capped SOC delta
- [ ] AC-5.3: Power profile positions (168-element array) are computed from capped targets
- [ ] AC-5.4: Existing EMHASS integration behavior is preserved when dynamic limit is 100% (no capping active)

### US-6: Handle critical Scenario C (daily commute without capping hit)
**As a** commuter with multiple daily short trips
**I want to** be charged only to the minimum SOC needed per trip rather than 100%
**So that** the battery does not sit at >80% SOC for extended idle periods

**Acceptance Criteria:**
- [ ] AC-6.1: For 4 identical 30km trips with 22.5h idle each and 6kWh consumption per trip: system charges to ~61% each time, not 100%
- [ ] AC-6.2: Post-trip SOC with capping is ~41% vs ~80% without capping
- [ ] AC-6.3: The dynamic limit (94.9%) does not block any trip because needed SOC (61%) < limit (94.9%)
- [ ] AC-6.4: Week total at >80% SOC drops from 90h to 0h

### US-7: Handle Scenario A and B (large trips unlock full charge)
**As a** driver planning a large trip
**I want to** automatically get full 100% charge when the trip will drain the battery below the sweet spot
**So that** I never miss a large trip because of battery health capping

**Acceptance Criteria:**
- [ ] AC-7.1: When a large trip drains battery to 0% (soc_post_trip = 0 < 35%), dynamic limit = 100%
- [ ] AC-7.2: For Scenario A (commute 30km, then 150km drain, then commute 30km, then semi 80km): all trips succeed at their required SOC
- [ ] AC-7.3: For Scenario B (150km drain first, then 3 commutes): first trip at 100%, commutes at capped limit — all succeed
- [ ] AC-7.4: Negative risk always returns 100% (regardless of idle hours)

---

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | Add `calculate_dynamic_soc_limit()` to `calculations.py` | High | Unit tests pass for all 5 scenarios (A, B, C, edge cases, T_base variability) |
| FR-2 | Integrate dynamic limit into `calculate_deficit_propagation()` at line ~808 | High | `soc_objetivo_final = min(soc_objetivo_ajustado, dynamic_limit)` applied in both backward loop and result-building loop |
| FR-3 | Add constants to `const.py`: `CONF_SOC_BASE`, `CONF_T_BASE`, `CONF_SOH_SENSOR`, defaults, ranges | High | Constants imported and available to config_flow and calculations modules |
| FR-4 | Add SOH sensor selector to sensors step in `config_flow.py` | High | Entity selector appears in sensors step; validated sensor entity accepted or rejected |
| FR-5 | Add T_base slider to config flow (no battery health toggle) | High | Slider appears; 6-48h range; default 24h; validates and persists value |
| FR-6 | EMHASS adapter uses capped SOC in `_populate_per_trip_cache_entry()` | High | Per-trip cache contains capped SOC; power profile reflects capped targets using real capacity |
| FR-7 | Trip manager passes battery health config to deficit propagation | High | `t_base` and SOH config values threaded through from config entry to `calculate_deficit_propagation()` |
| FR-8 | Extract `BatteryCapacity` class/abstraction that encapsulates nominal + SOH | High | Single source of truth for capacity; used by calculations, EMHASS adapter, trip manager — no duplicated capacity math |
| FR-9 | Forward-propagated SOC values are consistent with capped targets | High | After capping, forward propagation (soc_current for next trip) uses capped SOC, not original `soc_objetivo_ajustado` |
| FR-10 | New test file `tests/test_dynamic_soc_capping.py` with 5 unit tests | Medium | All tests pass with `pytest`; covers scenarios A, B, C, edge cases, T_base configurability |
| FR-11 | Define `t_hours` formula: idle hours between trip N completion and trip N+1 departure | High | `t_hours = (trip_N_plus_1_start_time - trip_N_end_time).total_seconds() / 3600`; clamped to >= 0; when no next trip exists, use `anticipation_hours` config value |
| FR-12 | Bridge T_base config value → algorithm parameter: config flow `t_base` slider value is passed as `t_base` parameter to `calculate_dynamic_soc_limit()` | High | FR-5 covers UI, FR-7 covers threading, FR-1 covers algorithm — FR-12 is the wiring between them |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | **Zero regression — all existing tests pass** | Full test suite | Every test in `test_soc_milestone.py` (1499 lines), `test_power_profile_positions.py`, `test_soc_100_deficit_propagation_bug.py`, and ALL existing test files passes without modification |
| NFR-2 | **Code quality — maximum standards** | Code review | Type hints on all new functions; docstrings explaining WHY not WHAT; no code duplication (DRY); SOLID principles; mypy clean (zero type errors); passes existing linting |
| NFR-3 | **SOH everywhere, always** | Code coverage | Zero code paths use nominal capacity when SOH sensor is configured; `BatteryCapacity` abstraction is the single source of truth |
| NFR-4 | **SOC cap integrated end-to-end** | Integration test | Capped SOC flows: calculations.py → trip_manager.py → emhass_adapter.py → EMHASS API; forward-propagated SOC reflects capping |
| NFR-5 | Performance overhead | Added CPU time per trip | < 1ms per trip in `calculate_dynamic_soc_limit()` (single formula evaluation) |
| NFR-6 | Config validation | User input | Reject T_base outside 6-48h; reject SOH outside 10-100% |
| NFR-7 | Backward compatibility | Existing installs | No config changes break existing integrations; SOH is optional |
| NFR-8 | **Quality gate — phased verification** | Gate checklist | Before moving from one phase to the next, all quality gates for the current phase MUST pass. No phase skipping. |

---

## Quality Gates

**Principle**: Every phase has explicit gates that must pass before proceeding. No phase skipping.

### Gate 1: Requirements → Design
- [ ] All user stories have clear, testable acceptance criteria
- [ ] All functional/non-functional requirements have measurable metrics
- [ ] No unresolved contradictions between requirements
- [ ] Dependencies on existing code/test files are identified
- [ ] Success criteria are observable and verifiable

### Gate 2: Design → Tasks
- [ ] Design documents integration points with exact file paths and line numbers
- [ ] `BatteryCapacity` abstraction design documented (interface, methods, where used)
- [ ] SOC cap integration design covers BOTH backward propagation loop AND result-building loop
- [ ] Forward propagation design specifies capped SOC feeds next trip
- [ ] SOH integration design ensures single source of truth, no nominal capacity leaks
- [ ] Config flow design shows T_base slider + SOH sensor selector (no health toggle)
- [ ] EMHASS adapter design shows capped SOC + real capacity flow
- [ ] All design decisions documented (trade-offs, rationale)

### Gate 3: Tasks → Implementation
- [ ] Tasks are small enough to implement in one session
- [ ] Each task has explicit verification steps
- [ ] Test-first order: tests before implementation
- [ ] SOH integration task ensures `BatteryCapacity` abstraction created first
- [ ] Regression safety task: verify existing tests pass BEFORE adding new code

### Gate 4: Implementation Complete — Pre-Review
- [ ] `calculate_dynamic_soc_limit()` implemented and unit tested
- [ ] `BatteryCapacity` abstraction implemented and used everywhere
- [ ] Dynamic cap integrated in BOTH loops of `calculate_deficit_propagation()`
- [ ] Forward-propagated SOC uses capped targets
- [ ] SOH sensor configured → real capacity used everywhere (zero nominal capacity leaks)
- [ ] Config flow: T_base slider + SOH sensor selector (no health toggle)
- [ ] EMHASS adapter uses capped SOC + real capacity
- [ ] **ALL existing tests pass** (test_soc_milestone.py, test_power_profile_positions.py, test_soc_100_deficit_propagation_bug.py, every test in the project)
- [ ] New unit tests pass (5 scenarios)
- [ ] mypy clean, lint clean
- [ ] Zero code duplication for capacity calculations

### Gate 5: Review → Complete
- [ ] Code review passed (no review comments blocking)
- [ ] Scenario A/B/C verified with manual testing
- [ ] Scenario C verified: post-trip SOC ~41% vs ~80% without capping
- [ ] Large trip scenario verified: 100% when justified
- [ ] SOH integration verified: real capacity used in all calculations
- [ ] Zero regressions confirmed

## Glossary

- **SOC**: State of Charge, battery charge level as percentage (0-100%)
- **SOC_base**: Battery chemistry sweet spot (35% for NMC/NCA), internal constant not exposed to user
- **T_base**: User-configurable time parameter in hours (6-48h, default 24h) that controls capping aggressiveness
- **SOH**: State of Health, battery degradation metric as percentage (100% = new battery)
- **real_capacity**: Nominal battery capacity adjusted by SOH: `nominal × SOH / 100`
- **deficit_acumulado**: Accumulated deficit from backward propagation of charging shortfalls across chained trips
- **soc_objetivo_ajustado**: Base SOC target adjusted by accumulated deficit from later trips
- **soc_objetivo_final**: Final SOC target after applying dynamic cap: `min(soc_objetivo_ajustado, dynamic_limit)`
- **risk**: Degradation risk score = `t_hours × (soc_post_trip - 35) / 65`
- **dynamic_limit**: Upper bound on charging, computed from risk and T_base
- **idle hours (t_hours)**: Hours between trip completion and next available charging opportunity
- **BatteryCapacity**: Abstraction class/encapsulation providing real capacity, single source of truth

---

## Out of Scope

- User-facing battery health mode toggle (health mode is always on)
- Per-vehicle SOC_base customization (hardcoded to 35% — the mathematically-validated sweet spot)
- LFP battery chemistry support (different sweet spot ~45-50%)
- UI/visual indicators for battery health status
- Historical battery degradation analytics
- V2G (vehicle-to-grid) discharge optimization
- Dynamic T_base adjustment based on battery age (T_base is manually configurable)

---

## Dependencies

- `propagate-charge-deficit-algo` (m401): m403 layers ON TOP of existing deficit propagation. No breaking changes.
- `charging-window-calculation` (m401): Uses same timestep system. Dynamic limit affects SOC targets which feed charging windows.
- SOH sensor entity: Must exist in Home Assistant instance if user wants real capacity calculation.
- EMHASS integration: Relies on existing EMHASS adapter infrastructure for power profile publishing.
- `tests/test_soc_milestone.py`: 1499-line test suite (regression baseline — MUST pass)
- `tests/test_power_profile_positions.py`: Power profile position tests (regression baseline)
- `tests/test_soc_100_deficit_propagation_bug.py`: SOC 100% deficit propagation tests (regression baseline)

---

## Success Criteria

- [ ] All 5 unit tests in `test_dynamic_soc_capping.py` pass
- [ ] **All existing test files pass without modification** (zero regressions): test_soc_milestone.py, test_power_profile_positions.py, test_soc_100_deficit_propagation_bug.py, and every other test in the project
- [ ] Scenario C produces measurable battery health improvement: post-trip SOC ~41% vs ~80% without capping
- [ ] Large trips (Scenario A/B drain to <35%) always succeed at 100% charge
- [ ] T_base slider in config flow accepts and persists values correctly
- [ ] SOH sensor drives real capacity everywhere — no nominal capacity leaks
- [ ] Forward-propagated SOC values are consistent with capped targets
- [ ] mypy clean, lint clean, zero code duplication for capacity calculations

---

## Verification Contract

**Project type**: `fullstack`

- Evidence: Home Assistant custom component (Python package) with UI configuration flow, REST/HA integration layer, energy calculation engine, EMHASS API client
- Browser entry point: Home Assistant UI (lovelace panels) for trip management and config
- API endpoints: HA config flow (multi-step UI), EMHASS JSON API for power profile submission

**Entry points**:
- `custom_components/ev_trip_planner/calculations.py:calculate_dynamic_soc_limit()` — core algorithm
- `custom_components/ev_trip_planner/calculations.py:calculate_deficit_propagation()` — integration point (line ~808), applies cap in both loops
- `custom_components/ev_trip_planner/config_flow.py:STEP_SENSORS_SCHEMA` — SOH sensor selector
- `custom_components/ev_trip_planner/config_flow.py` — T_base slider (no toggle)
- `custom_components/ev_trip_planner/emhass_adapter.py:_populate_per_trip_cache_entry()` — pass capped SOC + real capacity to EMHASS
- `custom_components/ev_trip_planner/trip_manager.py:calcular_hitos_soc()` — threads battery config through
- `custom_components/ev_trip_planner/calculations.py:BatteryCapacity` (new abstraction) — single source of truth for real capacity
- `tests/test_dynamic_soc_capping.py` — new test file

**Observable signals**:
- PASS looks like: `soc_objetivo` in deficit propagation results <= `dynamic_limit`; EMHASS receives capped `P_deferrable_nom` and `def_total_hours` using real capacity; forward-propagated SOC matches capped targets; config flow persists T_base and SOH sensor; ALL tests pass
- FAIL looks like: `soc_objetivo` > `dynamic_limit` when trip needs are below limit (capping should not apply); trips fail to charge when required SOC > available charging window; any existing test regression failure; nominal capacity used when SOH sensor configured; forward SOC inconsistent with cap

**Hard invariants**:
- Trip energy needs always met: `min(required_soc, dynamic_limit)` never reduces SOC below trip minimum
- Capped SOC feeds forward: forward-propagated SOC for the next trip uses `soc_objetivo_final` (capped), not `soc_objetivo_ajustado` (uncapped)
- Deficit propagation continues correctly: cap does not create artificial deficits in earlier trips
- Existing SOC milestone behavior preserved: when dynamic_limit >= 100%, behavior is identical to pre-m403
- **Zero regression**: all existing test files pass without modification
- **SOH is universal**: when SOH sensor is configured, `real_capacity` is used everywhere — no code path uses nominal capacity
- **Single source of truth**: `BatteryCapacity` abstraction is the only place capacity math lives
- `dynamic_limit` is clamped to [35.0, 100.0] — values below 35 are raised to 35, values above 100 are capped at 100
- SOH sensor missing or invalid: system falls back to nominal capacity (no crash)
- Auth/session: not applicable (internal calculation, no auth)

**Seed data**:
- At least 1 configured vehicle with battery_capacity_kwh (e.g., 60.0)
- At least 2 trips with defined departure times and energy needs (km or kWh)
- SOH sensor not required (optional, defaults to 100% — nominal capacity)
- T_base = 24.0 (default) for baseline verification

**Dependency map**:
- `propagate-charge-deficit-algo` (m401): shared function `calculate_deficit_propagation()`, shared trip data structures
- `charging-window-calculation` (m401): shared charging window calculations that consume SOC targets
- `soc-integration-baseline` (m401): shared SOC sensor reading and baseline calculations
- EMHASS integration: shared power profile array (168 elements)

**Escalate if**:
- Any existing test fails — requires analysis of whether cap interacts with existing logic in unexpected ways
- SOH sensor value is unstable (frequent updates) — may need debounce logic before implementation
- T_base range (6-48h) proves insufficient for user workflow — may need broader range
- Battery degradation science assumptions (35% sweet spot) are challenged for specific battery chemistry — LFP users will not see optimal behavior

---

## Next Steps

1. Create `BatteryCapacity` abstraction (single source of truth for real capacity)
2. Create test file `tests/test_dynamic_soc_capping.py` with 5 unit tests
3. Add constants to `const.py`
4. Implement `calculate_dynamic_soc_limit()` in `calculations.py`
5. Integrate cap into `calculate_deficit_propagation()` in BOTH loops
6. Wire forward-propagated SOC to use capped values
7. Add SOH sensor selector to `config_flow.py` sensors step
8. Add T_base slider to config flow
9. Update EMHASS adapter to use capped SOC + real capacity
10. **Run ALL existing tests — zero regressions allowed**
