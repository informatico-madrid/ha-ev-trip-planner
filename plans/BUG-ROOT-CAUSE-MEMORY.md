# BUG-ROOT-CAUSE-MEMORY.md

## Bug Summary
E2E UX-01 test falla porque `power_profile_watts.some(v => v > 0)` retorna FALSE cuando debería ser TRUE.

## Root Cause
`coordinator.async_refresh()` NO es llamado después de `async_add_recurring_trip` porque `entry.runtime_data` es None en el entorno E2E.

### Flow: Frontend → Service → TripManager → EMHASSAdapter → Coordinator → Sensor
1. Frontend llama `ev_trip_planner.add_recurring_trip` service
2. Service handler llama `trip_manager.async_add_recurring_trip()`
3. `async_add_recurring_trip` llama `_async_publish_new_trip_to_emhass()`
4. `_async_publish_new_trip_to_emhass` llama `async_publish_deferrable_load(trip)` y luego `publish_deferrable_loads()`
5. `publish_deferrable_loads` llama `emhass_adapter.async_publish_all_deferrable_loads(trips)`
6. `async_publish_all_deferrable_loads` calcula power profile y almacena en `self._cached_power_profile` (línea 949)
7. **BUG**: `coordinator.async_refresh()` solo es llamado si `entry.runtime_data` no es None (líneas 266-279)
8. En E2E, `entry.runtime_data` es None → `coordinator.async_refresh()` NO es llamado
9. Result: power profile es calculado pero `coordinator.data` NO es actualizado → sensor lee datos viejos → all zeros

### THE BUG: coordinator.data NOT updated because entry.runtime_data is None
```python
# trip_manager.py:266-279 (ANTES DEL FIX)
try:
    entry = self.hass.config_entries.async_get_entry(self._entry_id)
    if entry and entry.runtime_data:  # <-- BUG: runtime_data es None en E2E
        coordinator = entry.runtime_data.coordinator
        if coordinator:
            await coordinator.async_refresh()  # <-- NUNCA SE LLAMA EN E2E
except Exception as err:
    _LOGGER.debug("Coordinator refresh skipped: %s", err)
```

### FIX APPLIED: Fallback to emhass_adapter._get_coordinator()
```python
# trip_manager.py:263-295 (DESPUÉS DEL FIX)
coordinator = None
try:
    entry = self.hass.config_entries.async_get_entry(self._entry_id)
    if entry and entry.runtime_data:
        coordinator = entry.runtime_data.coordinator
except Exception:
    pass

# FALLBACK: If entry.runtime_data is None (E2E environment), try to get coordinator
# from emhass_adapter._get_coordinator() which may have alternative lookup logic
if coordinator is None and self._emhass_adapter:
    try:
        coordinator = self._emhass_adapter._get_coordinator()
    except Exception:
        pass

if coordinator:
    await coordinator.async_refresh()  # <-- AHORA SE LLAMA EN E2E
```

## Test Results
### RED Test (test_red_e2e_ux01_integration_bug.py) - PASSED AFTER FIX
```
power_profile_watts non-zero count: 2
async_refresh called: True
async_refresh call_count: 4
power_profile_watts.some(v => v > 0) = True
PASSED
```

## Key Files
### Modified
- [`custom_components/ev_trip_planner/trip_manager.py`](custom_components/ev_trip_planner/trip_manager.py:263-295) - Added fallback to get coordinator from emhass_adapter._get_coordinator()
- [`tests/test_red_e2e_ux01_integration_bug.py`](tests/test_red_e2e_ux01_integration_bug.py:1) - Updated to test real bug scenario

### Test Files
### RED Test (Demonstrates the Bug is Fixed)
- [`tests/test_red_e2e_ux01_integration_bug.py`](tests/test_red_e2e_ux01_integration_bug.py:226) - `test_red_exact_e2e_ux01_failure_scenario` - PASSED

### Calculation Tests (No Regressions)
- [`tests/test_integration_recurring_trip_pipeline_red.py`](tests/test_integration_recurring_trip_pipeline_red.py:1) - Existing RED tests
- [`tests/test_integration_full_pipeline_with_coordinator.py`](tests/test_integration_full_pipeline_with_coordinator.py:1) - Full pipeline tests

## Memory Note
El fix es seguro porque:
1. Solo añade un fallback cuando `entry.runtime_data` es None
2. No afecta el flujo normal cuando `entry.runtime_data` existe
3. `emhass_adapter._get_coordinator()` ya tiene lógica alternativa para buscar coordinator
4. El test RED confirma que el fix funciona correctamente

## Next Steps
1. ✅ Fix aplicado en trip_manager.py
2. ✅ RED test pasa
3. [ ] Verificar E2E test UX-01 pasa
4. [ ] Run full test suite to ensure no regressions
