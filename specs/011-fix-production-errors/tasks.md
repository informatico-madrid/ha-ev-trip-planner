---

description: "Task list for fixing production errors in EV Trip Planner"

---

# Tasks: Fix Production Errors - SPEC 011

**Input**: Production logs analysis, MASTERGUIDEHOMEASSISTANT.md, code review

**Prerequisites**: None (new issues from production)

**Tests**: Following TDD - tests must be written FIRST, then implementation

**Organization**: Tasks grouped by bug fix priority (P001 → P003 → P004 → P002)

---

## Skills Required

**MUST use these skills for relevant tasks**:

| Task Types | Skill | Purpose |
|-----------|-------|---------|
| All test tasks | `python-testing-patterns` | pytest, fixtures, mocking, TDD |
| HA sensor code | `homeassistant-best-practices` | HA entity patterns, sensor config |
| Dashboard YAML | `homeassistant-dashboard-designer` | Lovelace dashboard config |
| HA config | `homeassistant-config` | YAML configuration |
| HA ops | `homeassistant-ops` | Storage API patterns |

**IMPORTANT**: Load skill before implementing tasks. Use: `/skill python-testing-patterns`

---

## Format: `[ID] [P?] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- Include exact file paths in descriptions

---

## MASTERGUIDE Reference

**Breaking Changes from MASTERGUIDEHOMEASSISTANT.md relevant to this spec:**

- **LEY — ENUMS para device_class y unit_of_measurement**: DEBE utilizarse Enums canónicos
- **2025.12**: `platform: template` deprecado (fin en 2026.6)
- **state_class + device_class**: Para device_class 'energy', state_class debe ser 'total' o 'total_increasing', NO 'measurement'

---

## Phase 1: Setup (Verification)

**Purpose**: Verify current test state before making changes

- [ ] T001 Verify existing tests pass: `cd src && pytest tests/ -v`

---

## Phase 2: P001 - Sensor state_class Invalid (CRITICAL)

**Goal**: Fix "state_class 'measurement' which is impossible considering device_class 'energy'"

**MASTERGUIDE Reference**:
- "LEY — ENUMS para device_class y unit_of_measurement" - DEBE utilizarse Enums canónicos
- Para device_class 'energy', state_class debe ser 'total' o 'total_increasing', NO 'measurement'

**Test**: Test must FAIL before implementation

### Tests for P001

- [ ] T002 [P] [P001] Add test reproducing state_class warning in tests/test_sensor.py
  - Test: Create KwhTodaySensor with MEASUREMENT + ENERGY device_class
  - Expected: FAIL with warning before fix
  - **Skill**: Use `python-testing-patterns`
  - **MASTERGUIDE**: Verificar que el test reproduce el warning de state_class inválido

### Implementation for P001

- [ ] T003 [P001] Fix KwhTodaySensor state_class in custom_components/ev_trip_planner/sensor.py
  - Change: `self._attr_state_class = SensorStateClass.MEASUREMENT`
  - To: `self._attr_state_class = SensorStateClass.TOTAL_INCREASING`
  - **Skill**: Use `homeassistant-best-practices`
  - **MASTERGUIDE**: Confirmar contra `/home/malka/homeassistant` que TOTAL_INCREASING es el enum correcto

### Verification P001

- [ ] T004 Run test to verify fix: `cd src && pytest tests/test_sensor.py -v -k state_class`

---

## Phase 3: P003 - Config Entry Lookup Error

**Goal**: Fix "No config entry found for {vehicle_id}"

**Test**: Test must FAIL before implementation

### Tests for P003

- [ ] T005 [P] [P003] Add test for config entry lookup with vehicle_id in tests/test_sensor.py
  - Test: Call async_get_entry with vehicle_id (wrong) vs entry_id (correct)
  - Expected: FAIL before fix
  - **Skill**: Use `python-testing-patterns`

### Implementation for P003

- [ ] T006 [P003] Fix EmhassDeferrableLoadSensor config entry lookup in custom_components/ev_trip_planner/sensor.py
  - Current: `entry = self.hass.config_entries.async_get_entry(self._vehicle_id)`
  - Fix: Use entry_id from config entry, not vehicle_id
  - **Skill**: Use `homeassistant-config`
  - **MASTERGUIDE**: Verificar que async_get_entry espera entry_id, no vehicle_id

### Verification P003

- [ ] T007 Run test to verify fix: `cd src && pytest tests/test_sensor.py -v -k config_entry`

---

## Phase 4: P004 - Storage API Not Available in Container

**Goal**: Fix "'HomeAssistant' object has no attribute 'storage'"

**MASTERGUIDE Reference**:
- Storage API no disponible en Container - verificar con `hasattr(hass, "storage")`

**Test**: Test must FAIL before implementation

### Tests for P004

- [ ] T008 [P] [P004] Add test for Container storage not available in tests/test_trip_manager.py
  - Mock: `hass.storage` is None
  - Expected: FAIL before fix
  - **Skill**: Use `python-testing-patterns`

### Implementation for P004

- [ ] T009 [P004] Implement YAML fallback in custom_components/ev_trip_planner/trip_manager.py
  - Add check: `if not hasattr(self.hass, "storage")`
  - Use YAML file for persistence instead
  - Store in config directory
  - **Skill**: Use `homeassistant-ops`
  - **MASTERGUIDE**: Verificar que Container no tiene hass.storage, usar archivo YAML en su lugar

### Verification P004

- [ ] T010 Run test to verify fix: `cd src && pytest tests/test_trip_manager.py -v -k storage`

---

## Phase 5: P002 - Coordinator Data Not Available

**Goal**: Fix "no coordinator data available" warnings

**Test**: Test must FAIL before implementation

### Tests for P002

- [ ] T011 [P] [P002] Add test for sensors without coordinator data in tests/test_sensor.py
  - Test: Create sensor with coordinator=None
  - Expected: FAIL before fix
  - **Skill**: Use `python-testing-patterns`

### Implementation for P002

- [ ] T012 [P002] Fix sensor setup to ensure coordinator is passed correctly
  - Verify async_setup_entry passes coordinator to all sensors
  - Add fallback when coordinator is None
  - **Skill**: Use `homeassistant-best-practices`
  - **MASTERGUIDE**: Verificar patrón correcto de coordinator en HA 2026

### Verification P002

- [ ] T013 Run test to verify fix: `cd src && pytest tests/test_sensor.py -v -k coordinator`

---

## Phase 6: Intensive Tests

**Purpose**: Ensure all edge cases are covered

### Tests Coverage

- [ ] T014 [P] Add tests for all failure modes in tests/test_production_errors.py
  - Storage unavailable
  - Config entry not found
  - Coordinator None
  - Vehicle not configured
  - **Skill**: Use `python-testing-patterns`

- [ ] T015 [P] Add tests for all success modes in tests/test_production_errors.py
  - Storage available
  - Config entry found
  - Coordinator with data
  - Vehicle configured
  - **Skill**: Use `python-testing-patterns`

- [ ] T016 Verify against HA source code
  - Check `/home/malka/homeassistant` for correct APIs
  - Verify sensor state_class/device_class combinations
  - Verify storage API usage
  - **Skill**: Use `homeassistant-best-practices`
  - **MASTERGUIDE**: Confirmar todas las APIs contra código fuente de HA

### Coverage Requirement

- [ ] T017 Run full test suite: `cd src && pytest tests/ -v --cov=custom_components/ev_trip_planner`
  - Must achieve >= 80% coverage
  - All tests must pass

---

## Phase 7: Dashboard Verification

**Goal**: Verify dashboard loads and CRUD works

### Dashboard Tests

- [ ] T018 [P] Test dashboard import in tests/test_dashboard.py
  - Verify dashboard created after vehicle setup
  - Verify no errors in logs
  - **Skill**: Use `homeassistant-dashboard-designer`
  - **MASTERGUIDE**: Verificar que dashboard usa APIs actuales de Lovelace

- [ ] T019 [P] Test CRUD operations via dashboard
  - Create trip via dashboard
  - Read trips
  - Update trip
  - Delete trip
  - **Skill**: Use `homeassistant-dashboard-designer`

- [ ] T020 Verify no dashboard errors in logs
  - Check for import errors
  - Check for YAML errors
  - Check for Lovelace errors

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - verify baseline first
- **P001 (Phase 2)**: Critical - causes CRITICAL warnings
- **P003 (Phase 3)**: Error - config entry not found
- **P004 (Phase 4)**: Error - storage not available
- **P002 (Phase 5)**: Warning - logs pollution
- **Tests (Phase 6)**: After all fixes
- **Dashboard (Phase 7)**: After all fixes

### Execution Order (by priority)

```
Phase 1 (Setup) → P001 (CRITICAL) → P003 (ERROR) → P004 (ERROR) → P002 (WARNING) → Tests (Phase 6) → Dashboard (Phase 7)
```

### Coverage Requirement (CRITICAL)

Per Constitution: **MUST achieve >= 80% test coverage**

- T017: Verify coverage >= 80%
- All tests must pass

If coverage < 80% after all fixes:
- Add more tests for untested paths
- Re-run coverage until passing
- **This is a mandatory gate - cannot proceed without 80%+**

### Within Each Fix

1. Write failing test first (use `python-testing-patterns`)
2. Run test to confirm failure
3. Implement fix (use `homeassistant-best-practices`)
4. Run test to confirm pass
5. Run full test suite

---

## Parallel Opportunities

- **T002, T005, T008, T011**: All test creation tasks can run in parallel
- **T003, T006, T009, T012**: Implementation tasks in different files can run in parallel
- **P001, P003, P004, P002**: Can be implemented in parallel (different files)

---

## Notes

- **TDD**: All fixes follow Test-Driven Development - tests first!
- **Critical first**: P001 causes CRITICAL warnings in logs
- **All existing tests must still pass** after changes
- **HA Container**: No Supervisor, special handling needed
- **Commit after each task**: Small, focused commits
- **Skills**: MUST load relevant skills before implementing tasks
- **NO EXCUSAS**: Todo debe funcionar perfectamente
- **Verify against HA source**: Check `/home/malka/homeassistant` for correct APIs
