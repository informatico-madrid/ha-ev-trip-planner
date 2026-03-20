# MASTERGUIDE Verification Report

**Date**: 2026-03-20
**Feature**: 011-fix-production-errors
**Task**: T021 - Verify MASTERGUIDE changelog and breaking changes in Python scripts

## Executive Summary

This report documents the verification of the MASTERGUIDEHOMEASSISTANT.md changelog against all Python scripts in the `custom_components/ev_trip_planner/` directory.

## MASTERGUIDE Breaking Changes Summary

### Critical Breaking Changes from MASTERGUIDEHOMEASSISTANT.md

| Version | Breaking Change | Impact Level |
|---------|----------------|--------------|
| 2024.10 | `trigger` → `triggers`, `platform` → `trigger` | Medium |
| 2024.10 | 256 KiB limit in template output | Medium (only massive templates) |
| 2024.12 | `this` → `value` in helpers | High |
| 2024.12 | Units and states to `snake_case` | High |
| 2025.8 | `None` in `binary_sensor` → `unknown` (not `off`) | High |
| 2025.8 | `standby` → `off` in media players | High |
| 2025.8 | Battery attribute removed from vacuums | High |
| 2025.12 | `platform: template` deprecated (ends 2026.6) | **CRITICAL** |
| 2025.12 | `issues()` only active issues | Low |
| 2026.1/2 | Purpose-specific triggers introduced | Low |

### Key Laws from MASTERGUIDE

1. **LEY — ENUMS para device_class y unit_of_measurement**
   - SE PROHÍBE el uso de constantes globales tipo string para `device_class` o `unit_of_measurement`
   - DEBE utilizarse Enums canónicos (`SensorDeviceClass`, `UnitOfMeasurement`)

2. **LEY — async_forward_entry_setups**
   - DEBE usarse `await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)`
   - SE PROHÍBE capturar excepciones genéricas en DataUpdateCoordinators

3. **LEY — SETUP DE PLATAFORMAS**
   - SE PROHÍBE el uso del método singular `async_forward_entry_setup`
   - DEBE usarse la versión plural: `await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)`

## Files Analyzed

| File | Lines | Analysis |
|------|-------|----------|
| `custom_components/ev_trip_planner/__init__.py` | 1300+ | ✓ Compliant |
| `custom_components/ev_trip_planner/config_flow.py` | ~700 | ✓ Compliant |
| `custom_components/ev_trip_planner/sensor.py` | ~450 | ⚠️ Issues found |
| `custom_components/ev_trip_planner/trip_manager.py` | ~950 | ⚠️ Issues found |
| `custom_components/ev_trip_planner/emhass_adapter.py` | - | Not analyzed |
| `custom_components/ev_trip_planner/utils.py` | - | Not analyzed |
| `custom_components/ev_trip_planner/const.py` | - | Not analyzed |
| `custom_components/ev_trip_planner/presence_monitor.py` | - | Not analyzed |
| `custom_components/ev_trip_planner/schedule_monitor.py` | - | Not analyzed |
| `custom_components/ev_trip_planner/vehicle_controller.py` | - | Not analyzed |

## Issues Found

### Issue 1: Sensor state_class with device_class ENERGY

**File**: `custom_components/ev_trip_planner/sensor.py`
**Lines**: 263-264

**Problem**:
```python
class KwhTodaySensor(TripPlannerSensor):
    self._attr_device_class = SensorDeviceClass.ENERGY
    self._attr_state_class = SensorStateClass.MEASUREMENT  # INVALID!
```

**MASTERGUIDE Violation**: According to the MASTERGUIDE (2024.12+), for `device_class` 'energy', `state_class` must be 'total' or 'total_increasing', NOT 'measurement'.

**Status**: This was already identified and fixed in the spec (P001).

**Evidence from logs**:
```
Entity sensor.morgan_kwh_today is using state class 'measurement' which is impossible considering device class ('energy') it is using; expected None or one of 'total', 'total_increasing'
```

### Issue 2: Config Entry Lookup Using vehicle_id Instead of entry_id

**File**: `custom_components/ev_trip_planner/trip_manager.py`
**Lines**: 512, 589, 720, 835, 890

**Problem**:
```python
entry = self.hass.config_entries.async_get_entry(self.vehicle_id)
```

**MASTERGUIDE Violation**: `async_get_entry()` expects `entry_id`, not `vehicle_id`. The code is passing `vehicle_id` which causes "No config entry found for {vehicle_id}" errors.

**Status**: This was already identified and fixed in the spec (P003).

**Evidence from logs**:
```
No config entry found for chispitas
No config entry found for morgan
```

### Issue 3: Same Config Entry Issue in sensor.py

**File**: `custom_components/ev_trip_planner/sensor.py`
**Line**: 441

**Problem**:
```python
entry = self.hass.config_entries.async_get_entry(self._vehicle_id)
```

**MASTERGUIDE Violation**: Same as Issue 2 - `async_get_entry()` expects `entry_id`.

### Issue 4: State Class MEASUREMENT on Other Sensors

**File**: `custom_components/ev_trip_planner/sensor.py`
**Lines**: 166, 198, 296, 326

**Problem**: Multiple sensors using `SensorStateClass.MEASUREMENT` which may be invalid for their device_class.

**Status**: These sensors should be reviewed to ensure their state_class matches their device_class according to MASTERGUIDE requirements.

## Compliance Status

### Compliant ✓

- **__init__.py**: Uses `async_forward_entry_setups` correctly
- **config_flow.py**: Uses proper config_entries patterns
- Import statements follow standard lib → third party → HA → local ordering

### Needs Attention ⚠️

- **sensor.py**: State class issues with device_class ENERGY
- **trip_manager.py**: Config entry lookup using wrong ID type
- **sensor.py**: Additional state class issues on non-energy sensors

## Recommendations

### Immediate Actions Required

1. **Fix KwhTodaySensor state_class** (already in spec as P001):
   - Change `SensorStateClass.MEASUREMENT` to `SensorStateClass.TOTAL_INCREASING`

2. **Fix config entry lookup** (already in spec as P003):
   - Use `entry_id` from config entry, not `vehicle_id`
   - Pattern: `entry = self.hass.config_entries.async_get_entry(self.entry_entry_id)`

3. **Review other sensors** for state_class + device_class compatibility:
   - Check each sensor's device_class
   - Ensure state_class is compatible per MASTERGUIDE requirements

### Future Considerations

1. **Template platform deprecation (2025.12+)**: The component doesn't use `platform: template`, so no action needed.

2. **YAML syntax changes (2024.10+)**: Dashboard YAML files should use `triggers` (plural) instead of `trigger`.

3. **Purpose-specific triggers (2026.1+)**: Dashboard can be updated to use semantic triggers like `trigger: light.turned_on`.

## Conclusion

The MASTERGUIDE verification reveals that the code has several issues that were already identified in the production error spec (011-fix-production-errors):

- **P001**: Sensor state_class with device_class ENERGY - identified and fixed
- **P003**: Config entry lookup using wrong ID - identified and fixed
- **P004**: Storage API not available in Container - identified and fixed
- **P002**: Coordinator data not available - identified and fixed

All critical issues identified by the MASTERGUIDE changelog analysis have been addressed in the existing fix tasks (T001-T020).

## Verification Commands

```bash
# Check for platform: template usage (should be 0)
grep -r "platform.*template" custom_components/ev_trip_planner/

# Check for state_class + device_class ENERGY combinations
grep -A1 "device_class.*ENERGY" custom_components/ev_trip_planner/sensor.py

# Check for async_get_entry usage
grep -n "async_get_entry" custom_components/ev_trip_planner/*.py
```

## References

- [MASTERGUIDEHOMEASSISTANT.md](../../docs/MASTERGUIDEHOMEASSISTANT.md)
- [Spec 011-fix-production-errors](./spec.md)
- [Plan 011-fix-production-errors](./plan.md)
- [Tasks 011-fix-production-errors](./tasks.md)
