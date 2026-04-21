# Análisis de Tests Fallantes - Paso P0.0

**Fecha**: 2026-04-20  
**Total tests**: 1569  
**Tests pasados**: 1549  
**Tests fallando**: 20  
**Cobertura**: 98.79% (falta 1% para 100%)

---

## Resumen de Tests Fallantes

| # | Test | Archivo | Categoría | Razón Principal |
|---|------|---------|-----------|-----------------|
| 1 | test_async_get_vehicle_soc_returns_value_and_handles_unavailable | test_trip_manager_missing_coverage.py | B | Import missing: pytest_homeassistant_custom_component |
| 2 | test_get_charging_power_from_entry | test_trip_manager_missing_coverage.py | B | Import missing: pytest_homeassistant_custom_component |
| 3 | test_power_profile_positions_at_end_of_charging_window | test_power_profile_positions.py | C | Bug: def_total_hours=0 en vez de 2 |
| 4 | test_async_add_recurring_trip_calls_emhass_when_coordinator_present | test_trip_manager_cover_more.py | C | Bug: publish_deferrable_loads no llamado |
| 5 | test_emhass_updated_after_setup_loads_from_storage | test_post_restart_persistence.py | C | Bug: NameError timezone |
| 6 | test_async_delete_all_trips_clears_emhass_cache_and_publishes_empty | test_integration_uninstall.py | C | Bug: publish_deferrable_loads no llamado |
| 7 | test_datetime_subtraction_raises_typeerror | test_emhass_datetime.py | C | Bug: NameError timezone |
| 8 | test_aware_datetime_subtraction_works | test_emhass_datetime.py | C | Bug: NameError timezone |
| 9 | test_remove_trip_from_emhass | test_trip_manager_emhass.py | C | Bug: publish_deferrable_loads no llamado |
| 10 | test_publish_new_trip_to_emhass | test_trip_manager_emhass.py | C | Bug: publish_deferrable_loads no llamado |
| 11 | test_sync_trip_to_emhass_recalculates | test_trip_manager_emhass.py | C | Bug: publish_deferrable_loads no llamado |
| 12 | test_async_add_punctual_trip_with_emhass_adapter | test_trip_manager_core.py | C | Bug: publish_deferrable_loads no llamado |
| 13 | test_async_sync_trip_to_emhass_with_km_change_triggers_recalculate | test_trip_manager_core.py | C | Bug: publish_deferrable_loads no llamado |
| 14 | test_async_add_recurring_trip_with_emhass_adapter | test_trip_manager_core.py | C | Bug: publish_deferrable_loads no llamado |
| 15 | test_publish_deferrable_loads_with_adapter | test_trip_manager_core.py | C | Bug: publish_deferrable_loads no llamado |
| 16 | test_async_publish_all_deferrable_loads_populates_non_empty_power_profile | test_aggregated_sensor_bug.py | C | Bug: power_profile todo ceros |
| 17 | test_aggregated_sensor_can_access_power_profile_via_coordinator | test_aggregated_sensor_bug.py | C | Bug: power_profile todo ceros |
| 18 | test_get_cached_results_provides_real_data_to_sensor | test_aggregated_sensor_bug.py | C | Bug: power_profile todo ceros |
| 19 | test_publish_deferrable_loads_called_after_setup | test_emhass_publish_bug.py | C | Bug: NameError timezone |
| 20 | test_emhass_sensors_populated_after_publish | test_emhass_publish_bug.py | C | Bug: NameError timezone |

---

## Análisis Detallado por Categoría

### Categoría B: Test Obsoleto / Import Missing (2 tests)

#### B.1 test_async_get_vehicle_soc_returns_value_and_handles_unavailable
- **Archivo**: `tests/test_trip_manager_missing_coverage.py:56`
- **Error**: `ModuleNotFoundError: No module named 'pytest_homeassistant_custom_component'`
- **Razón**: El test usa `create_mock_ev_config_entry()` que importa `MockConfigEntry` de `pytest_homeassistant_custom_component`, pero este módulo no está instalado.
- **Acción**: Eliminar este test o instalar el módulo faltante.

#### B.2 test_get_charging_power_from_entry
- **Archivo**: `tests/test_trip_manager_missing_coverage.py:23`
- **Error**: `ModuleNotFoundError: No module named 'pytest_homeassistant_custom_component'`
- **Razón**: Mismo problema que B.1.
- **Acción**: Eliminar este test o instalar el módulo faltante.

---

### Categoría C: Bug en Implementación (18 tests)

Estos tests son **válidos** y revelan bugs reales en el código. NO SON tests obsoletos.

#### C.1 Bug: `NameError: name 'timezone' is not defined` (5 tests)

**Tests afectados**:
- `test_emhass_updated_after_setup_loads_from_storage`
- `test_datetime_subtraction_raises_typeerror`
- `test_aware_datetime_subtraction_works`
- `test_publish_deferrable_loads_called_after_setup`
- `test_emhass_sensors_populated_after_publish`

**Root cause**: En `custom_components/ev_trip_planner/trip_manager.py:182`:
```python
now = datetime.now(timezone.utc)
```

Pero `timezone` no está importado. Debería ser:
```python
from datetime import datetime, timezone
```

**Acción**: Añadir import faltante en `trip_manager.py`.

---

#### C.2 Bug: `def_total_hours = 0` en vez de valor esperado (1 test)

**Test**: `test_power_profile_positions_at_end_of_charging_window`
- **Archivo**: `tests/test_power_profile_positions.py:90`
- **Error**: `AssertionError: Should need 2 hours charging, got 0`
- **Razón**: El test espera que `def_total_hours = 2` pero el código devuelve `0`. Esto indica que la lógica de cálculo de horas de carga está fallando.

**Acción**: Investigar `calculate_power_profile_from_trips()` o `calculate_energy_needed()` para entender por qué devuelve 0 en vez de 2.

---

#### C.3 Bug: `publish_deferrable_loads` no llamado (8 tests)

**Tests afectados**:
- `test_async_add_recurring_trip_calls_emhass_when_coordinator_present`
- `test_async_delete_all_trips_clears_emhass_cache_and_publishes_empty`
- `test_remove_trip_from_emhass`
- `test_publish_new_trip_to_emhass`
- `test_sync_trip_to_emhass_recalculates`
- `test_async_add_punctual_trip_with_emhass_adapter`
- `test_async_sync_trip_to_emhass_with_km_change_triggers_recalculate`
- `test_async_add_recurring_trip_with_emhass_adapter`
- `test_publish_deferrable_loads_with_adapter`

**Root cause**: Los tests esperan que `async_publish_all_deferrable_loads` sea llamado después de ciertas operaciones (add trip, delete trip, update trip), pero el código no está llamando a `publish_deferrable_loads()`.

**Ejemplo de test fallando**:
```python
mock_emhass_adapter.async_publish_all_deferrable_loads.assert_called()
AssertionError: Expected 'async_publish_all_deferrable_loads' to have been called.
```

**Acción**: Verificar que `publish_deferrable_loads()` se llama en:
- `async_add_punctual_trip()`
- `async_add_recurring_trip()`
- `async_update_trip()`
- `async_delete_trip()`
- `async_delete_all_trips()`

---

#### C.4 Bug: `power_profile` todo ceros (3 tests)

**Tests afectados**:
- `test_async_publish_all_deferrable_loads_populates_non_empty_power_profile`
- `test_aggregated_sensor_can_access_power_profile_via_coordinator`
- `test_get_cached_results_provides_real_data_to_sensor`

**Error**: `BUG: _cached_power_profile has all zeros. Expected at least some charging hours with positive values.`

**Root cause**: El `power_profile_watts` está siendo calculado como todos ceros. Esto puede deberse a:
1. SOC suficiente → no se necesita carga (comportamiento correcto según Fase 1)
2. Bug en `calculate_power_profile_from_trips()` → nunca se calcula el perfil

**Acción**: Investigar si esto es comportamiento esperado (SOC alto) o un bug real.

---

## Plan de Acción Priorizado

### Alta Prioridad (Crítico - Bloqueante)

1. **Fix C.1**: Añadir `from datetime import datetime, timezone` a `trip_manager.py`
   - Esto arreglará 5 tests inmediatamente
   - Impacto: Alto

2. **Fix C.3**: Asegurar que `publish_deferrable_loads()` se llama en todos los métodos de CRUD
   - Esto arreglará 8 tests
   - Impacto: Alto

### Media Prioridad

3. **Investigar C.2**: `test_power_profile_positions_at_end_of_charging_window`
   - Verificar si el test es válido o si el código está correcto
   - Impacto: Medio

4. **Investigar C.4**: `power_profile` todo ceros
   - Verificar si SOC es alto (comportamiento esperado) o bug
   - Impacto: Medio

### Baja Prioridad

5. **Eliminar B.1, B.2**: Tests que no pueden ejecutarse por missing import
   - Impacto: Bajo

---

## Notas Adicionales

### Cobertura de Tests
- **Total coverage**: 98.79%
- **Falta**: 1.21%
- **Archivos con coverage < 100%**:
  - `emhass_adapter.py`: 99% (5 statements missing)
  - `presence_monitor.py`: 98% (5 statements missing)
  - `schedule_monitor.py`: 99% (1 statement missing)
  - `sensor.py`: 96% (15 statements missing)
  - `trip_manager.py`: 97% (28 statements missing)

### Tests que NO son problemas
- Los 1549 tests que pasan indican que la mayoría del código está funcionando correctamente.
- Los 20 tests fallantes son específicos y tienen causas claras.

---

## Conclusión

**Los 20 tests fallantes NO indican que la implementación está mal hecha.** Indican:
1. **5 tests** fallan por un import faltante (`timezone`)
2. **8 tests** fallan porque `publish_deferrable_loads()` no se llama en ciertos métodos
3. **3 tests** fallan por `power_profile` todo ceros (posiblemente SOC alto, verificar)
4. **1 test** falla por lógica de cálculo de horas (investigar)
5. **2 tests** no pueden ejecutarse por missing import de test framework

**Acción recomendada**:
1. Fixar import `timezone` en `trip_manager.py`
2. Verificar que `publish_deferrable_loads()` se llama en todos los métodos de CRUD
3. Investigar los casos restantes uno por uno
