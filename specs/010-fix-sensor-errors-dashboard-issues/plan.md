c# Implementation Plan: Fix Sensor Errors, Dashboard Issues

**Branch**: `010-fix-sensor-errors-dashboard-issues` | **Date**: 2026-03-20 | **Spec**: [spec.md](./spec.md)

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/plan-template.md` for the execution workflow.

## Summary

Fix 4 critical errors in Home Assistant Container installation:
- P001: VehicleController.get_charging_power() missing (crashes every 30s)
- P002: Sensors with incorrect device_class (warnings in logs)
- P003: NextTripSensor fails to create (ValueError)
- P004: Dashboard import fails in Container (Storage API unavailable)

Technical approach: Add missing methods, fix sensor device_class configuration, implement Container fallback for dashboard.

**Skills Required**:
- `python-testing-patterns` - Para tests con pytest, fixtures, mocking
- `homeassistant-best-practices` - Para código de sensores HA
- `homeassistant-dashboard-designer` - Para configuración YAML de dashboards
- `homeassistant-config` - Para configuración YAML

---

## Technical Context

**Language/Version**: Python 3.11+ (Home Assistant integration)  
**Primary Dependencies**: Home Assistant Core, voluptuous, PyYAML  
**Storage**: Home Assistant storage (JSON files)  
**Testing**: pytest, pytest-asyncio, pytest-cov  
**Target Platform**: Home Assistant Container (Linux)  
**Project Type**: Home Assistant Custom Component  
**Performance Goals**: N/A (small component)  
**Constraints**: Must work in HA Container (no Supervisor)  
**Scale/Scope**: 4 bugs to fix, ~200 lines of code affected

---

## Constitution Check

*Gate: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| Code Style (line length 88, type hints, docstrings) | ✅ PASS | Will follow Google style |
| Testing (>80% coverage) | ✅ PASS | Existing tests must still pass |
| Documentation (Conventional Commits) | ✅ PASS | Will follow commit format |
| TDD (Test first) | ✅ PASS | Each fix starts with failing test |

---

## Project Structure

### Documentation (this feature)

```text
specs/010-fix-sensor-errors-dashboard-issues/
├── plan.md              # This file
├── spec.md              # Feature specification
├── research.md          # (N/A - no research needed)
├── data-model.md        # (N/A - no new entities)
├── quickstart.md        # (N/A - no new features)
├── contracts/           # (N/A - no external contracts)
├── tasks.md             # Implementation tasks
└── checklists/
    └── requirements.md  # Quality checklist
```

### Source Code (repository root)

```text
custom_components/ev_trip_planner/
├── __init__.py          # Dashboard import logic (P004)
├── sensor.py            # Sensor classes (P001, P002, P003)
├── trip_manager.py      # TripManager class (P001)
└── vehicle_controller.py # VehicleController (P001)

tests/
├── test_sensor.py       # Sensor tests
├── test_sensor_coverage.py # Extended sensor tests
├── test_vehicle_controller.py # Vehicle controller tests
└── test_dashboard.py   # Dashboard tests
```

**Structure Decision**: Standard Home Assistant custom component structure. No changes to project layout needed.

---

## Problem Analysis

### P001: VehicleController.get_charging_power() missing

**Location**: [`sensor.py:90`](../custom_components/ev_trip_planner/sensor.py:90)

```python
# Current code:
charging_power = self.trip_manager.vehicle_controller.get_charging_power()
```

**Root Cause**: Method does not exist in VehicleController. TripManager has `_get_charging_power()` (private).

**Fix**: Add public `get_charging_power()` method to TripManager (returns kW).

---

### P002: Sensors with incorrect device_class

**Location**: [`sensor.py:58-60`](../custom_components/ev_trip_planner/sensor.py:58-60)

```python
# Current code in TripPlannerSensor base class:
self._attr_state_class = SensorStateClass.MEASUREMENT
self._attr_device_class = SensorDeviceClass.ENERGY
self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
```

**Root Cause**: Base class defines ENERGY device_class for ALL derived sensors, but many return non-energy values.

| Sensor | Current device_class | Should be |
|--------|---------------------|-----------|
| KwhTodaySensor | ENERGY | ENERGY |
| HoursTodaySensor | ENERGY | DURATION or None |
| NextTripSensor | ENERGY | None |
| NextDeadlineSensor | ENERGY | None |
| Count sensors | ENERGY | None |

**Fix**: Remove device_class from base class, define appropriately in each derived sensor.

---

### P003: NextTripSensor creation error

**Location**: [`sensor.py:103`](../custom_components/ev_trip_planner/sensor.py:103)

```python
# Current code:
self._attr_native_value = next_trip["descripcion"] if next_trip else "N/A"
```

**Root Cause**: Returns "N/A" (string) when no trip, but has device_class=ENERGY - incompatible.

**Error in logs**:
```
ValueError: Sensor sensor.chispitas_next_trip has device class 'energy',
state class 'measurement' unit 'kWh' thus indicating it has a numeric value;
however, it has the non-numeric value: 'No trips' (<class 'str'>)
```

**Fix**: Remove device_class/state_class from NextTripSensor.

---

### P004: Dashboard import fails in Container

**Location**: [`__init__.py:632-785`](../custom_components/ev_trip_planner/__init__.py:632)

**Root Cause**: HA Container has no:
- `hass.services.has_service("lovelace", "save")` - service doesn't exist
- `hass.storage` - Storage API not available

**Fix**: Implement fallback that generates YAML file and provides clear instructions for manual import.

**Robustness Requirements** (per user feedback):
- Handle duplicate dashboard names: append `-2-`, `-3-`, etc. to path
- No partial failures - all error cases must have fallback
- Tests must cover all failure modes

---

## Implementation Phases

### Phase 1: P001 - VehicleController.get_charging_power() (CRITICAL)

1. Create test reproducing the error
2. Add public method to TripManager
3. Verify test passes

### Phase 2: P003 - NextTripSensor (ERROR)

1. Create test reproducing the error
2. Remove device_class from NextTripSensor
3. Verify test passes

### Phase 3: P002 - Device class (WARNING)

1. Create tests for device_class validation
2. Remove device_class from base class
3. Define device_class in each derived sensor
4. Run all sensor tests

### Phase 4: P004 - Dashboard Container (ERROR)

1. Create test for Container environment
2. Implement fallback (YAML generation + instructions)
3. Verify test passes

---

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

---

## Notes

- **TDD**: Each fix follows Test-Driven Development: test first, then code
- **HA Container**: This is a special installation without Supervisor
- **All existing tests must pass** after changes
- **Coverage must remain >90%**
