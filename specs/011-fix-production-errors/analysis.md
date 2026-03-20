# Analysis: Production Errors from HA Logs (2026-03-20)

## Errors Identified in Logs

### P001 (CRITICAL) - Sensor state_class Invalid
- **File**: `custom_components/ev_trip_planner/sensor.py`
- **Lines**: 263-264
- **Problem**: `KwhTodaySensor` has:
  ```python
  self._attr_device_class = SensorDeviceClass.ENERGY
  self._attr_state_class = SensorStateClass.MEASUREMENT  # INVALID!
  ```
- **Log Error**: "Entity sensor.morgan_kwh_today is using state class 'measurement' which is impossible considering device class ('energy') it is using; expected None or one of 'total', 'total_increasing'"
- **Fix**: Change `state_class` from `MEASUREMENT` to `TOTAL_INCREASING`

### P002 - Sensors Without Coordinator Data
- **Files**: `sensor.py` - `NextTripSensor`, `NextDeadlineSensor`, `KwhTodaySensor`, etc.
- **Log Error**: "no coordinator data available" (~40+ times in 20 minutes)
- **Root Cause**: Sensors use `coordinator.data` but coordinator is None or has no data
- **Fix**: Ensure coordinator is properly passed to all sensors

### P003 - Config Entry Lookup Error
- **File**: `sensor.py` line 441
- **Problem**: Code uses `async_get_entry(self._vehicle_id)` but expects `entry_id`, not `vehicle_id`
- **Log Error**: "No config entry found for chispitas" / "No config entry found for morgan"
- **Fix**: Use correct entry_id lookup

### P004 - Storage API Not Available in Container
- **File**: `trip_manager.py` lines 85, 119
- **Problem**: Uses `hass.storage.async_read()` and `hass.storage.async_write_dict()`
- **Log Error**: "'HomeAssistant' object has no attribute 'storage'" / "Storage API not available for vehicle morgan"
- **Root Cause**: Home Assistant Container doesn't have storage API
- **Fix**: Implement YAML fallback for trip data persistence

## Dashboard Errors Analysis

### Current Dashboard Import Flow Issues

From `__init__.py` analysis:

1. **Storage API fallback exists** (lines 792-906): `_save_dashboard_yaml_fallback()` generates YAML file
2. **Verification function exists** (lines 566-629): `_verify_storage_permissions()` checks if storage available
3. **Problem**: The dashboard import may be calling but not actually working in Container

### Root Causes for Dashboard Not Showing:

1. **Storage API unavailable in Container** - but YAML fallback should work
2. **Template not found** - dashboard templates may not be found
3. **Lovelace not available** - Container may not have Lovelace UI
4. **Import method failures** - all fallback methods may be failing silently

### Key Functions to Check:

```python
# __init__.py
- import_dashboard() (lines 325-466)
- _load_dashboard_template() (lines 469-563)
- _save_lovelace_dashboard() (lines 632-789)
- _save_dashboard_yaml_fallback() (lines 792-906)
- _verify_storage_permissions() (lines 566-629)
```

### Tests Missing for These Errors:

- No tests for P001 (state_class validation)
- No tests for P002 (coordinator data availability)
- No tests for P003 (config entry lookup with vehicle_id)
- No tests for P004 (storage API fallback in Container)

## Summary

The production logs reveal 4 CRITICAL errors that were NOT covered in previous specs:
1. P001: Sensor state_class invalid - causes CRITICAL warning
2. P002: Sensors have no coordinator data - causes 40+ warnings
3. P003: Config entry lookup fails - causes warnings
4. P004: Storage API not available in Container - causes errors

**These need tests + fixes immediately.**
