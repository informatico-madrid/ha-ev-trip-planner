# Tasks: SOC Milestone Algorithm

## Phase 1: Implementation (POC)

Focus: Implement backward deficit propagation algorithm for SOC milestones.

### Core Algorithm Implementation

- [ ] 1.1 [P] Add DEFAULT_SOC_BUFFER_PERCENT constant
  - **Do**:
    1. Add `DEFAULT_SOC_BUFFER_PERCENT = 10` to `const.py`
    2. This represents the minimum SOC buffer as a percentage
  - **Files**: `custom_components/ev_trip_planner/const.py`
  - **Done when**: Constant added and importable
  - **Verify**: `grep -n "DEFAULT_SOC_BUFFER_PERCENT" custom_components/ev_trip_planner/const.py`
  - **Commit**: `feat(soc-milestone): add DEFAULT_SOC_BUFFER_PERCENT constant`
  - _Design: Buffer Definition_

- [x] 1.2 [P] Define type hints for calcular_hitos_soc return structure
  - **Do**:
    1. Add TypedDict or type hints for return structure in trip_manager.py
    2. Fields: trip_id, soc_objetivo, kwh_necesarios, deficit_acumulado, ventana_carga
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: Type hints defined for return structure
  - **Verify**: `grep -n "SOCMilestoneResult\|Dict\[str" custom_components/ev_trip_planner/trip_manager.py | head -10`
  - **Commit**: `feat(soc-milestone): define type hints for SOC milestone results`
  - _Requirements: Interface Contract_

- [ ] 1.3 [P] Implement charging rate calculation helper
  - **Do**:
    1. Add `_calcular_tasa_carga_soc` method to TripManager
    2. Formula: `charging_power_kw / battery_capacity_kwh * 100` = % SOC/hour
    3. Handle battery_capacity_kwh fallback to 50.0 kWh
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: Method returns % SOC/hour based on charging power and battery capacity
  - **Verify**: `grep -n "_calcular_tasa_carga_soc" custom_components/ev_trip_planner/trip_manager.py`
  - **Commit**: `feat(soc-milestone): add charging rate calculation helper`
  - _Requirements: AC-3_
  - _Design: Technical Details section_

- [ ] 1.4 [P] Implement base SOC target calculation
  - **Do**:
    1. Calculate energy needed for trip from kwh field or km * consumption
    2. Convert energy to SOC percentage: `energia_kwh / battery_capacity_kwh * 100`
    3. Add buffer: `soc_objetivo_base = energia_soc + DEFAULT_SOC_BUFFER_PERCENT`
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: Method returns base SOC target percentage for a trip
  - **Verify**: `grep -n "soc_objetivo_base\|_calcular_soc_objetivo_base" custom_components/ev_trip_planner/trip_manager.py`
  - **Commit**: `feat(soc-milestone): add base SOC target calculation`
  - _Requirements: AC-4_
  - _Design: Algorithm step 1_

- [x] 1.5 [P] Implement SOC at trip start calculation using calcular_ventana_carga_multitrip
  - **Do**:
    1. Call existing `calcular_ventana_carga_multitrip` to get windows
    2. For each trip, SOC at start = previous trip arrival SOC after charging
    3. For first trip: use soc_inicial parameter
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: Method returns correct SOC at trip start from previous charging window
  - **Verify**: `grep -n "soc_inicio\|calcular_ventana_carga_multitrip" custom_components/ev_trip_planner/trip_manager.py | head -15`
  - **Commit**: `feat(soc-milestone): implement SOC at trip start calculation`
  - _Dependencies: charging-window-calculation (Spec 2)_
  - _Design: Algorithm step 2_

- [x] 1.6 [P] Implement backward deficit detection and propagation
  - **Do**:
    1. Sort trips by departure time
    2. Iterate in REVERSE order (last trip to first)
    3. Calculate `capacidad_carga = tasa_carga_soc * ventana_horas`
    4. If `soc_inicio + capacidad_carga < soc_objetivo`:
       - `deficit = soc_objetivo - (soc_inicio + capacidad_carga)`
       - Add deficit to PREVIOUS trip's (earlier trip's) soc_objetivo
    5. Store deficit_acumulado for current trip
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: Deficit correctly propagates backward to previous trip
  - **Verify**: `grep -n "deficit_acumulado\|deficit.*propag" custom_components/ev_trip_planner/trip_manager.py`
  - **Commit**: `feat(soc-milestone): implement backward deficit detection and propagation`
  - _Requirements: AC-1, AC-2_
  - _Design: Algorithm section (BACKWARD PROPAGATION)_

- [ ] 1.7 [P] Implement kWh needed calculation
  - **Do**:
    1. Calculate: `kwh_necesarios = (soc_objetivo - soc_inicio) * battery_capacity_kwh / 100`
    2. Store in result dict
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: kWh needed correctly calculated for each trip
  - **Verify**: `grep -n "kwh_necesarios" custom_components/ev_trip_planner/trip_manager.py`
  - **Commit**: `feat(soc-milestone): add kWh needed calculation`
  - _Design: Algorithm step 4_

- [x] 1.8 [P] Implement main calcular_hitos_soc function
  - **Do**:
    1. Create `async def calcular_hitos_soc(trips, soc_inicial, charging_power_kw, battery_capacity_kwh)`
    2. Sort trips by departure time (chronological order)
    3. Iterate in REVERSE to propagate deficit backward
    4. Return list of dicts with required fields
    5. Use existing `calcular_ventana_carga_multitrip` for window calculation
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: Function signature matches interface contract and processes trips correctly
  - **Verify**: `grep -A 20 "async def calcular_hitos_soc" custom_components/ev_trip_planner/trip_manager.py`
  - **Commit**: `feat(soc-milestone): implement main calcular_hitos_soc function`
  - _Requirements: Interface Contract, AC-1, AC-2_
  - _Design: Algorithm section_

- [ ] 1.9 [VERIFY] Quality checkpoint: lint and type check
  - **Do**: Run quality commands on modified files
  - **Verify**: `make lint && make mypy 2>&1 | tail -30`
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(soc-milestone): pass quality checkpoint` (only if fixes needed)

- [ ] 1.10 POC Checkpoint: AC-1 scenario verification
  - **Do**:
    1. Trace through algorithm with test data: morning trip 12:00 (30% SOC needed), night trip 22:00 (80% SOC needed)
    2. 4 hour window, 10% SOC/hour charging
    3. Night trip arrives at 20% SOC
    4. Night needs 80% - 20% = 60% but only gets 40% → 20% deficit
    5. Morning trip target: 30% + 10% buffer + 20% (night's deficit) = **60%**
  - **Done when**: AC-1 scenario produces correct results via manual calculation trace
  - **Verify**: Manual trace through algorithm shows morning target = 60%
  - **Commit**: `feat(soc-milestone): verify AC-1 scenario`

### Edge Cases and Integration

- [x] 1.11 [P] Handle empty trips list
  - **Do**:
    1. Return empty list if trips is empty or None
    2. No deficit propagation needed
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: Function handles empty input gracefully
  - **Verify**: Empty trips returns []
  - **Commit**: `feat(soc-milestone): handle empty trips list`

- [x] 1.12 [P] Handle single trip (no propagation needed)
  - **Do**:
    1. For single trip, calculate base SOC target only
    2. No deficit propagation since no previous trip
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: Single trip returns base SOC target with deficit_acumulado=0
  - **Verify**: Single trip test case passes
  - **Commit**: `feat(soc-milestone): handle single trip case`

- [x] 1.13 [P] Handle multiple consecutive deficits
  - **Do**:
    1. If multiple trips cannot fully charge, accumulate deficit
    2. Each trip's deficit adds to the PREVIOUS trip's target
    3. Track cumulative deficit through chain
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: Consecutive deficits correctly accumulated
  - **Verify**: Multi-trip deficit chain test passes
  - **Commit**: `feat(soc-milestone): handle consecutive deficits`

- [x] 1.14 [P] Handle battery_capacity_kwh fallback
  - **Do**:
    1. Extract battery_capacity_kwh from vehicle_config if available
    2. Fallback to 50.0 kWh if not available
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: Function handles battery_capacity_kwh parameter correctly
  - **Verify**: `grep -n "battery_capacity_kwh" custom_components/ev_trip_planner/trip_manager.py | head -10`
  - **Commit**: `feat(soc-milestone): add battery_capacity_kwh fallback`
  - _Requirements: Data Source_

- [ ] 1.15 [VERIFY] Quality checkpoint: lint and type check
  - **Do**: Run quality commands
  - **Verify**: `make lint && make mypy 2>&1 | tail -20`
  - **Done when**: No lint errors, no type errors
  - **Commit**: `chore(soc-milestone): pass quality checkpoint` (only if fixes needed)

## Phase 2: Testing

Focus: Add comprehensive unit tests for the SOC milestone algorithm.

### Unit Tests

- [ ] 2.1 [P] Create test file for SOC milestone algorithm
  - **Do**:
    1. Create `tests/test_soc_milestone.py`
    2. Add fixtures for mock_hass, trip_manager
    3. Add test data factories for trips with various energy requirements
  - **Files**: `tests/test_soc_milestone.py`
  - **Done when**: Test file created with basic fixtures
  - **Verify**: `ls -la tests/test_soc_milestone.py`
  - **Commit**: `test(soc-milestone): create test file with fixtures`
  - _Design: Test Strategy_

- [x] 2.2 [P] Test AC-1: Morning/Night trip deficit propagation (BACKWARD)
  - **Do**:
    1. Create trips: morning 12:00 (30% SOC needed), night 22:00 (80% SOC needed)
    2. Night arrives at 20% SOC
    3. 4 hour window, 10% SOC/hour charging = +40% SOC capacity
    4. Night: 20% + 40% = 60% but needs 80% → 20% deficit
    5. Deficit propagates BACKWARD to morning trip
    6. Morning target = 30% + 10% buffer + 20% deficit = **60%**
  - **Files**: `tests/test_soc_milestone.py`
  - **Done when**: AC-1 test passes with correct backward deficit propagation
  - **Verify**: `python3 -m pytest tests/test_soc_milestone.py::TestAC1 -v`
  - **Commit**: `test(soc-milestone): add AC-1 morning/night backward deficit propagation test`
  - _Requirements: AC-1_

- [x] 2.3 [P] Test AC-2: Morning trip has more kWh than night trip
  - **Do**:
    1. Using AC-1 scenario, verify morning trip kwh_necesarios > night trip kwh_necesarios
    2. This proves deficit was propagated backward
  - **Files**: `tests/test_soc_milestone.py`
  - **Done when**: Morning trip has more kWh needed than night trip
  - **Verify**: `python3 -m pytest tests/test_soc_milestone.py::TestAC2 -v`
  - **Commit**: `test(soc-milestone): add AC-2 morning trip kWh verification test`
  - _Requirements: AC-2_

- [ ] 2.4 [P] Test AC-3: Faster charging rate (no deficit)
  - **Do**:
    1. If charging rate is 20% SOC/hour instead of 10%
    2. 4 hour window = +80% SOC capability
    3. Night: 20% arrival + 80% charge = 100% > 80% needs → no deficit
    4. Morning target = 30% + 10% buffer = 40% (no deficit propagated)
  - **Files**: `tests/test_soc_milestone.py`
  - **Done when**: Higher charging rate produces no deficit scenario
  - **Verify**: `python3 -m pytest tests/test_soc_milestone.py::TestAC3 -v`
  - **Commit**: `test(soc-milestone): add AC-3 faster charging rate test`
  - _Requirements: AC-3_

- [x] 2.5 [P] Test AC-4: No previous trips (standard buffer only)
  - **Do**:
    1. Single trip scenario with no previous deficit
    2. Verify SOC target = trip energy + 10% buffer only
    3. deficit_acumulado = 0
  - **Files**: `tests/test_soc_milestone.py`
  - **Done when**: Single trip has no accumulated deficit
  - **Verify**: `python3 -m pytest tests/test_soc_milestone.py::TestAC4 -v`
  - **Commit**: `test(soc-milestone): add AC-4 standard buffer test`
  - _Requirements: AC-4_

- [x] 2.6 [P] Test edge case: very short charging window
  - **Do**:
    1. 30 minute window, 10% SOC/hour = 5% SOC capacity
    2. Large deficit should be calculated and propagate backward
  - **Files**: `tests/test_soc_milestone.py`
  - **Done when**: Short window produces large deficit
  - **Verify**: `python3 -m pytest tests/test_soc_milestone.py::TestEdgeShortWindow -v`
  - **Commit**: `test(soc-milestone): add short window edge case test`

- [x] 2.7 [P] Test edge case: exactly enough charging
  - **Do**:
    1. Window provides exactly the SOC needed
    2. deficit = 0 (no propagation needed)
  - **Files**: `tests/test_soc_milestone.py`
  - **Done when**: Exactly sufficient charging produces zero deficit
  - **Verify**: `python3 -m pytest tests/test_soc_milestone.py::TestEdgeExact -v`
  - **Commit**: `test(soc-milestone): add exactly sufficient charging edge case test`

- [x] 2.8 [P] Test edge case: more than enough charging (surplus)
  - **Do**:
    1. Window provides more SOC than needed
    2. No deficit, possible surplus for next trip
  - **Files**: `tests/test_soc_milestone.py`
  - **Done when**: Surplus charging scenario handled correctly
  - **Verify**: `python3 -m pytest tests/test_soc_milestone.py::TestEdgeSurplus -v`
  - **Commit**: `test(soc-milestone): add surplus charging edge case test`

- [x] 2.9 [P] Test three trips consecutive deficit propagation (BACKWARD)
  - **Do**:
    1. Create 3 trips with insufficient charging windows between them
    2. Verify deficit accumulates and propagates backward through all trips
    3. Last trip deficit → middle trip deficit → first trip target increased
  - **Files**: `tests/test_soc_milestone.py`
  - **Done when**: Three-trip chain correctly propagates accumulated deficit backward
  - **Verify**: `python3 -m pytest tests/test_soc_milestone.py::TestThreeTripChain -v`
  - **Commit**: `test(soc-milestone): add three-trip consecutive deficit test`

- [ ] 2.10 [P] Test empty trips list handling
  - **Do**:
    1. Call calcular_hitos_soc with empty list
    2. Verify returns empty list
  - **Files**: `tests/test_soc_milestone.py`
  - **Done when**: Empty input returns empty output
  - **Verify**: `python3 -m pytest tests/test_soc_milestone.py::TestEmptyTrips -v`
  - **Commit**: `test(soc-milestone): add empty trips handling test`

- [ ] 2.11 [P] Test single trip handling
  - **Do**:
    1. Call calcular_hitos_soc with single trip
    2. Verify base SOC target calculated, deficit_acumulado = 0
  - **Files**: `tests/test_soc_milestone.py`
  - **Done when**: Single trip returns correct base target
  - **Verify**: `python3 -m pytest tests/test_soc_milestone.py::TestSingleTrip -v`
  - **Commit**: `test(soc-milestone): add single trip handling test`

- [x] 2.12 [P] Test battery_capacity_kwh fallback
  - **Do**:
    1. Pass battery_capacity_kwh = 50.0 explicitly
    2. Pass battery_capacity_kwh = None and verify fallback to 50.0
  - **Files**: `tests/test_soc_milestone.py`
  - **Done when**: Battery capacity fallback works correctly
  - **Verify**: `python3 -m pytest tests/test_soc_milestone.py::TestBatteryFallback -v`
  - **Commit**: `test(soc-milestone): add battery capacity fallback test`

- [x] 2.13 [P] Test charging_power_kw affects SOC rate
  - **Do**:
    1. Test with 3.6 kW charging (low rate)
    2. Test with 11.0 kW charging (high rate)
    3. Verify different deficits produced
  - **Files**: `tests/test_soc_milestone.py`
  - **Done when**: Different charging powers produce different SOC rates
  - **Verify**: `python3 -m pytest tests/test_soc_milestone.py::TestChargingPowerAffectsRate -v`
  - **Commit**: `test(soc-milestone): add charging power rate test`

- [x] 2.14 [P] Test result structure has all required fields
  - **Do**:
    1. Verify each result dict has: trip_id, soc_objetivo, kwh_necesarios, deficit_acumulado, ventana_carga
    2. Verify ventana_carga has inicio and fin datetime fields
  - **Files**: `tests/test_soc_milestone.py`
  - **Done when**: Result structure matches interface contract
  - **Verify**: `python3 -m pytest tests/test_soc_milestone.py::TestResultStructure -v`
  - **Commit**: `test(soc-milestone): add result structure validation test`
  - _Requirements: Interface Contract_

- [ ] 2.15 [VERIFY] Quality checkpoint: all SOC milestone tests pass
  - **Do**: Run all SOC milestone tests
  - **Verify**: `python3 -m pytest tests/test_soc_milestone.py -v`
  - **Done when**: All tests pass
  - **Commit**: `chore(soc-milestone): pass quality checkpoint` (only if fixes needed)

## Phase 3: Refactoring

Focus: Clean up implementation, improve code quality.

- [ ] 3.1 Extract SOC calculation logic into separate helper methods
  - **Do**:
    1. Review existing helper methods added in Phase 1
    2. Ensure they are single-responsibility
    3. Move any inline calculations to helper methods
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: Code is modular with clear helper methods
  - **Verify**: `make lint && make mypy`
  - **Commit**: `refactor(soc-milestone): extract SOC calculation helpers`
  - _Design: Architecture section_

- [x] 3.2 Add docstrings to all new methods
  - **Do**:
    1. Add Google-style docstrings to `calcular_hitos_soc`
    2. Add docstrings to all helper methods
    3. Document parameters and return values
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: All methods have clear docstrings
  - **Verify**: `grep -A 5 'def _calcular\|async def calcular_hitos' custom_components/ev_trip_planner/trip_manager.py | head -40`
  - **Commit**: `docs(soc-milestone): add docstrings to SOC calculation methods`

- [x] 3.3 Add logging for deficit propagation
  - **Do**:
    1. Add _LOGGER.debug for deficit calculation steps
    2. Log when deficit is propagated to previous trip
    3. Log final SOC targets for each trip
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: Deficit propagation is logged for debugging
  - **Verify**: `grep -n "_LOGGER.*deficit\|deficit.*_LOGGER" custom_components/ev_trip_planner/trip_manager.py`
  - **Commit**: `feat(soc-milestone): add deficit propagation logging`

- [ ] 3.4 Optimize trip sorting
  - **Do**:
    1. Ensure trips are sorted by departure time once at start
    2. Don't re-sort in each iteration
    3. Cache trip times if used multiple times
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: Trips sorted only once, cached values used
  - **Verify**: Code review of sorting logic
  - **Commit**: `refactor(soc-milestone): optimize trip sorting`

- [ ] 3.5 Handle datetime serialization in results
  - **Do**:
    1. Ensure datetime objects in ventana_carga are serializable
    2. Use isoformat() for JSON compatibility if needed
  - **Files**: `custom_components/ev_trip_planner/trip_manager.py`
  - **Done when**: Results can be serialized to JSON
  - **Verify**: Import test with json.dumps on results
  - **Commit**: `fix(soc-milestone): ensure datetime serialization in results`

- [ ] 3.6 [VERIFY] Quality checkpoint: lint, type check, tests
  - **Do**: Run full quality checks
  - **Verify**: `make check 2>&1 | tail -30`
  - **Done when**: All checks pass
  - **Commit**: `chore(soc-milestone): pass quality checkpoint` (only if fixes needed)

## Phase 4: Quality Gates

Focus: Verify all acceptance criteria, ensure CI passes.

- [ ] 4.1 Local quality check
  - **Do**: Run ALL quality checks locally
  - **Verify**: All commands must pass:
    - `make lint` - ruff and pylint
    - `make mypy` - type checking
    - `python3 -m pytest tests/test_soc_milestone.py -v` - new tests
    - `python3 -m pytest tests/ -v --ignore=tests/e2e` - existing tests (regression)
  - **Done when**: All commands pass with no errors
  - **Commit**: `fix(soc-milestone): address any lint/type/test issues`

- [ ] 4.2 Create branch and commit
  - **Do**:
    1. Verify current branch: `git branch --show-current`
    2. If on main, create new branch: `git checkout -b feature/soc-milestone-algorithm`
    3. Stage and commit all changes: `git add -A && git commit -m "feat(soc-milestone): implement SOC milestone algorithm with backward deficit propagation"`
  - **Verify**: `git log --oneline -3`
  - **Done when**: All changes committed to feature branch
  - **Commit**: None (already committed)

- [ ] 4.3 Push branch to remote
  - **Do**:
    1. Push branch: `git push -u origin feature/soc-milestone-algorithm`
  - **Verify**: `git log --oneline -3`
  - **Done when**: Branch pushed successfully
  - **Commit**: None

- [ ] 4.4 Create PR and verify CI
  - **Do**:
    1. Create PR using gh CLI: `gh pr create --title "feat(soc-milestone): implement SOC milestone algorithm" --body "## Summary\n- Implements calcular_hitos_soc() function\n- Propagates SOC deficit BACKWARD between consecutive trips\n- AC-1: Morning trip gets 20% deficit from night trip (60% target)\n- AC-2: Morning trip has more kWh needed than night trip (deficit propagated)\n- AC-3: Uses actual charging rate from charging_power_kw\n- AC-4: Standard 10% buffer for trips without previous deficit"`
    2. Wait for CI: `gh pr checks --watch`
  - **Verify**: `gh pr checks` shows all green
  - **Done when**: All CI checks green, PR ready for review
  - **If CI fails**:
    1. Read failure details: `gh pr checks`
    2. Fix issues locally
    3. Push fixes: `git push`

## Phase 5: PR Lifecycle

Focus: Continuous validation until all completion criteria met.

- [ ] 5.1 Monitor CI pipeline
  - **Do**:
    1. Check CI status: `gh pr checks`
    2. If any check fails, investigate and fix
  - **Verify**: All checks pass
  - **Done when**: CI pipeline is green

- [ ] 5.2 Address review comments
  - **Do**:
    1. If PR has review comments, address each one
    2. Push fixes and re-request review if needed
  - **Verify**: All comments addressed
  - **Done when**: PR approved

- [ ] 5.3 Final verification: AC checklist
  - **Do**: Read requirements, verify each acceptance criterion:
    - AC-1: Morning trip 12:00 (30% SOC) + Night trip 22:00 (80% SOC) produces 60% morning target (40% base + 20% backward deficit)
    - AC-2: Morning trip has more kWh needed than night trip after deficit propagation
    - AC-3: Actual charging rate used when faster than 10% SOC/hour
    - AC-4: No deficit = only standard 10% buffer
  - **Verify**: `grep -r "60%" tests/test_soc_milestone.py` to confirm AC-1 verification
  - **Done when**: All ACs confirmed via test results
  - **Commit**: None

- [ ] 5.4 VE1 [VERIFY] E2E startup: verify component loads
  - **Do**:
    1. For HA custom component, verify component loads correctly
    2. Check for import errors
  - **Verify**: `python3 -c "from custom_components.ev_trip_planner.trip_manager import TripManager; print('OK')"`
  - **Done when**: Component loads without errors
  - **Commit**: None

- [ ] 5.5 VE2 [VERIFY] E2E check: verify SOC milestone integration
  - **Do**:
    1. Run the test suite to verify SOC milestone calculation end-to-end
    2. Create test trips and verify deficit propagation backward
    3. Verify results match expected AC values
  - **Verify**: `python3 -m pytest tests/test_soc_milestone.py -v`
  - **Done when**: SOC milestone works in full environment
  - **Commit**: None

- [ ] 5.6 VE3 [VERIFY] E2E cleanup: remove test artifacts
  - **Do**:
    1. Clean up any test data created
    2. Verify no residual state
  - **Verify**: Cleanup complete
  - **Done when**: Clean state
  - **Commit**: None

## Notes

- **Algorithm Direction**: BACKWARD PROPAGATION - deficit from later trip propagates to earlier trip (reverse chronological order iteration)
- **POC shortcuts taken**: Hardcoded 6-hour trip duration from existing calcular_ventana_carga_multitrip, using battery_capacity_kwh fallback of 50.0 kWh
- **Production TODOs**: Consider making trip duration configurable, add more sophisticated SOC sensor handling
- **Dependencies**: charging-window-calculation (Spec 2) - function `calcular_ventana_carga_multitrip` at line 1228 is used

## Acceptance Criteria Checklist

- [ ] AC-1: Morning trip 12:00 (30% SOC) + Night trip 22:00 (80% SOC) → Morning target = **60%** (40% base + 20% backward deficit)
- [ ] AC-2: Morning trip has more kWh needed than night trip (deficit propagated backward)
- [ ] AC-3: Actual charging rate used when faster than 10% SOC/hour
- [ ] AC-4: No previous deficit → only standard 10% buffer
