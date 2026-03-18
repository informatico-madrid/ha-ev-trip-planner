# Quickstart: Running Tests for Milestone 3

**Branch**: `007-complete-milestone-3-verify-1-2`  
**Date**: 2026-03-18  
**Purpose**: Quick guide to run tests for Milestone 3 completion

---

## Prerequisites

- Python 3.11
- Home Assistant 2026.x
- pytest-homeassistant-custom-component
- All dependencies installed

---

## Quick Start Commands

### 1. Run All Tests with Coverage

```bash
cd /home/malka/ha-ev-trip-planner
pytest tests/ -v --cov=custom_components/ev_trip_planner
```

**Expected Output**:
- ✅ 0 skipped tests
- ✅ 0 failed tests
- ✅ 0 warnings
- ✅ Coverage ≥79%

### 2. Run Specific Test Files

#### Trip Calculation Tests
```bash
pytest tests/test_trip_calculations.py -v
```

#### SOC-Aware Power Profile Tests
```bash
pytest tests/test_trip_manager_power_profile.py -v
```

#### CRUD Tests (Backward Compatibility)
```bash
pytest tests/test_trip_manager_core.py -v
```

#### EMHASS Integration Tests (Backward Compatibility)
```bash
pytest tests/test_trip_manager_emhass.py -v
```

### 3. Run with Coverage Report

```bash
pytest tests/ -v --cov=custom_components/ev_trip_planner --cov-report=html
```

Opens `htmlcov/index.html` in browser for detailed coverage report.

### 4. Verify No Skipped Tests

```bash
pytest tests/ -v 2>&1 | grep "SKIPPED"
```

**Expected**: No output (all tests should run)

### 5. Verify No Failed Tests

```bash
pytest tests/ -v 2>&1 | grep "FAILED"
```

**Expected**: No output (all tests should pass)

### 6. Verify No Warnings

```bash
pytest tests/ -v 2>&1 | grep -i "warning"
```

**Expected**: No warnings (clean output)

---

## Test Execution Order

Tests should be run in this order to catch issues early:

1. **Enable tests** (remove skip markers)
2. **Run enabled tests** (verify they pass)
3. **Run existing tests** (verify no regressions)
4. **Run full suite** (verify coverage)

---

## Troubleshooting

### Issue: Tests are skipped

**Symptom**: `pytest tests/ -v` shows SKIPPED tests

**Solution**: 
1. Check if `pytestmark = pytest.mark.skip(...)` exists in test file
2. Remove skip marker if test is valid
3. Re-run tests

### Issue: Tests are failing

**Symptom**: `pytest tests/ -v` shows FAILED tests

**Solution**:
1. Run with detailed output: `pytest tests/test_file.py -v --tb=short`
2. Check error message for root cause
3. Verify implementation matches test expectations
4. Fix implementation or adjust test if test is incorrect

### Issue: Coverage is too low

**Symptom**: Coverage <79%

**Solution**:
1. Check which lines are not covered: `pytest tests/ --cov-report=term-missing`
2. Add tests for uncovered functions
3. Verify coverage is ≥79%

---

## Expected Test Results

### Before Changes

```bash
pytest tests/ -v
# Output:
# 7 SKIPPED tests
# 45% coverage
# Some tests failed
```

### After Changes

```bash
pytest tests/ -v
# Output:
# 0 SKIPPED tests
# 0 FAILED tests
# 0 warnings
# Coverage ≥79%
```

---

## Verification Checklist

- [ ] Run `pytest tests/ -v` → 0 SKIPPED
- [ ] Run `pytest tests/ -v` → 0 FAILED
- [ ] Run `pytest tests/ -v` → 0 warnings
- [ ] Run `pytest tests/ -v --cov=custom_components/ev_trip_planner` → Coverage ≥79%
- [ ] Run `pytest tests/test_trip_calculations.py -v` → 5 tests PASSED
- [ ] Run `pytest tests/test_trip_manager_power_profile.py -v` → 5 tests PASSED
- [ ] Run `pytest tests/test_trip_manager_core.py -v` → All CRUD tests PASSED
- [ ] Run `pytest tests/test_trip_manager_emhass.py -v` → All EMHASS tests PASSED

---

## Test File Locations

```
tests/
├── test_trip_calculations.py        # 5 tests (enabled)
├── test_trip_manager_power_profile.py # 5 tests (enabled)
├── test_trip_manager_core.py        # CRUD tests (existing)
├── test_trip_manager_emhass.py      # EMHASS tests (existing)
├── test_config_flow_core.py         # Config flow tests (existing)
├── test_config_flow_milestone3.py   # Milestone 3 config tests (existing)
├── test_emhass_adapter.py           # EMHASS adapter tests (existing)
├── test_presence_monitor.py         # Presence detection tests (existing)
├── test_vehicle_controller.py       # Vehicle control tests (existing)
├── test_calculation_sensors.py      # Calculation sensor tests (existing)
└── ... (other existing tests)
```

---

## Notes

- **No obsolete tests remain**: test_trip_manager_storage.py and test_ui_issues_post_deployment.py are deleted
- **All tests are valid**: No duplicate test coverage
- **Backward compatibility**: Existing tests still pass (no regressions)
- **SOC-aware profile**: Implemented and tested

---

## References

- **Spec**: specs/007-complete-milestone-3-verify-1-2/spec.md
- **Plan**: specs/007-complete-milestone-3-verify-1-2/plan.md
- **Research**: specs/007-complete-milestone-3-verify-1-2/research.md
- **Data Model**: specs/007-complete-milestone-3-verify-1-2/data-model.md
- **Tasks**: specs/007-complete-milestone-3-verify-1-2/tasks.md
