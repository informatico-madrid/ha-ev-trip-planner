# Implementation Plan: 011-fix-production-errors

**Branch**: `011-fix-production-errors` | **Date**: 2026-03-20 | **Spec**: [spec.md](./spec.md)

## Input

Production logs analysis from `docs/LOGS_ANALYSIS_2026-03-20.md` and MASTERGUIDEHOMEASSISTANT.md

## Summary

This plan addresses 4 critical production errors identified in Home Assistant logs:
- P001: Sensor state_class invalid with device_class energy (CRITICAL)
- P002: Sensors without coordinator data
- P003: Config entry lookup error
- P004: Storage API not available in Container

## Technical Context

### Errors Found

| Error | File | Line | Problem |
|-------|------|------|---------|
| P001 | sensor.py | 263-264 | state_class MEASUREMENT with device_class ENERGY |
| P002 | sensor.py | Multiple | coordinator.data is None |
| P003 | sensor.py | 441 | async_get_entry(vehicle_id) not entry_id |
| P004 | trip_manager.py | 85, 119 | hass.storage not available in Container |

### Root Causes

1. **P001**: HA 2024+ requires state_class 'total' or 'total_increasing' for device_class 'energy'
2. **P002**: Sensors not properly receiving coordinator reference
3. **P003**: Using vehicle_id instead of entry_id for config lookup
4. **P004**: Container environment doesn't have hass.storage API

### Technology Stack

- Python 3.11+
- Home Assistant 2026.x
- pytest-homeassistant-custom-component
- Custom component structure

---

## Implementation Phases

### Phase 1: P001 - Fix Sensor state_class

**Approach**: Change state_class from MEASUREMENT to TOTAL_INCREASING for energy sensors

**Files to modify**:
- `custom_components/ev_trip_planner/sensor.py`

**Tests to add**:
- `tests/test_sensor.py` - Test state_class validation

### Phase 2: P003 - Fix Config Entry Lookup

**Approach**: Use correct entry_id for config entry lookup

**Files to modify**:
- `custom_components/ev_trip_planner/sensor.py`

**Tests to add**:
- `tests/test_sensor.py` - Test config entry lookup

### Phase 3: P004 - Storage API Fallback

**Approach**: Implement YAML fallback for Container environment

**Files to modify**:
- `custom_components/ev_trip_planner/trip_manager.py`

**Tests to add**:
- `tests/test_trip_manager.py` - Test storage fallback

### Phase 4: P002 - Coordinator Data

**Approach**: Ensure coordinator is passed correctly to all sensors

**Files to modify**:
- `custom_components/ev_trip_planner/sensor.py`
- `custom_components/ev_trip_planner/__init__.py`

**Tests to add**:
- `tests/test_sensor.py` - Test coordinator availability

### Phase 5: Dashboard Verification

**Approach**: Verify dashboard loads correctly after all fixes

**Files to verify**:
- `custom_components/ev_trip_planner/__init__.py`
- `custom_components/ev_trip_planner/dashboard/`

**Tests to add**:
- `tests/test_dashboard.py` - Test dashboard import

---

## Skills Required

| Skill | Purpose |
|-------|---------|
| `python-testing-patterns` | TDD, pytest, fixtures |
| `homeassistant-best-practices` | Sensor patterns |
| `homeassistant-ops` | Storage API |
| `homeassistant-dashboard-designer` | Dashboard verification |

---

## Execution Order

```
Phase 1 (P001) → Phase 2 (P003) → Phase 3 (P004) → Phase 4 (P002) → Phase 5 (Dashboard)
```

---

## Coverage Requirements

- Minimum 80% test coverage
- All tests must pass
- No warnings in production logs

---

## Dependencies

- No external dependencies
- Uses existing test infrastructure
- Verified against HA source code in `/home/malka/homeassistant`

---

## Notes

- TDD approach: Tests first, then implementation
- All fixes must be verified against HA source code
- No excuses: Everything must work perfectly
