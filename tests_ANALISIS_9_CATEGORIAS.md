# Análisis de Cobertura de Tests: 9 Categorías de Actualización del Sensor EMHASS

## Resumen Ejecutivo

**FALTAN TESTS CRÍTICOS**: De las 9 categorías que actualizan el sensor `sensor.trip_planner_chispitas_emhass_perfil_diferible_chispitas`, SOLO 3 tienen tests que verifican que el sensor SE ACTUALICE. Las otras 6 tienen tests que verifican que se llamen los métodos, PERO NO que el sensor se actualice.

---

## 1. REFRESH PERIÓDICO AUTOMÁTICO (cada 30 segundos)

### ¿Hay tests?
❌ **NO**

### Qué debería probar el test:
- Que cada 30 segundos el coordinator llama a `_async_update_data()`
- Que `_async_update_data()` llama a `get_cached_optimization_results()`
- **CRÍTICO**: Que si el cache es obsoleto, se regenera (actualmente NO lo hace)

### Test actual:
```python
# ❌ NO EXISTE
```

### Archivo donde debería estar:
`tests/test_coordinator.py`

---

## 2. CAMBIO DE SOC DEL VEHÍCULO (≥5%)

### ¿Hay tests?
✅ **SÍ** - `tests/test_presence_monitor_soc.py`

### Tests existentes:
- `test_soc_change_above_5_percent_triggers_recalculation_when_home_and_plugged`
- `test_soc_change_below_5_percent_does_not_trigger_recalculation`
- `test_soc_change_above_5_percent_does_not_trigger_when_not_home`
- `test_soc_change_above_5_percent_does_not_trigger_when_not_plugged`

### ¿Qué prueban?
✅ Verifican que `publish_deferrable_loads()` se llama cuando SOC cambia ≥5%
✅ Verifican que NO se llama cuando SOC cambia <5%

### ¿Qué NO prueban?
❌ **NO verifican que el sensor EMHASS se actualice** después del cambio de SOC
❌ Solo verifican que se llama al método, no el efecto final en el sensor

### Test faltante:
```python
async def test_soc_change_above_5_percent_updates_emhass_sensor():
    """
    Test que un cambio de SOC ≥5% actualiza el sensor EMHASS.

    1. Simular cambio de SOC 50% → 60% (≥5%)
    2. Verificar que publish_deferrable_loads() se llama ✅ (ya existe)
    3. ❌ FALTA: Verificar que coordinator.data se actualiza
    4. ❌ FALTA: Verificar que EmhassDeferrableLoadSensor muestra nuevos datos
    """
```

---

## 3. TIMER HORARIO (rotación de viajes recurrentes)

### ¿Hay tests?
⚠️ **PARCIAL** - `tests/test_coverage_100_percent.py`

### Tests existentes:
- `test_hourly_refresh_callback_with_none_trip_manager`
- `test_hourly_refresh_callback_handles_exception`

### ¿Qué prueban?
✅ Verifican que `_hourly_refresh_callback()` maneja errores
✅ Verifican que llama a `publish_deferrable_loads()`

### ¿Qué NO prueban?
❌ **NO verifican que el sensor EMHASS se actualice** después de la rotación
❌ Solo verifican manejo de errores, no el efecto final en el sensor

### Test faltante:
```python
async def test_hourly_refresh_updates_emhass_sensor():
    """
    Test que el timer horario actualiza el sensor EMHASS.

    1. Simular que pasa 1 hora
    2. Llamar a _hourly_refresh_callback()
    3. Verificar que publish_deferrable_loads() se llama ✅ (ya existe)
    4. ❌ FALTA: Verificar que coordinator.data se actualiza
    5. ❌ FALTA: Verificar que EmhassDeferrableLoadSensor muestra nuevos datos
    """
```

---

## 4. CAMBIO DE CONFIGURACIÓN (potencia de carga, battery capacity)

### ¿Hay tests?
❌ **NO**

### Tests existentes:
❌ No hay tests que verifiquen que cambiar la configuración actualiza el sensor

### Test faltante:
```python
async def test_config_entry_update_refreshes_emhass_sensor():
    """
    Test que cambiar charging_power_kw actualiza el sensor EMHASS.

    1. Configurar integración con charging_power_kw=3.4
    2. Cambiar a charging_power_kw=7.4
    3. Verificar que update_charging_power() se llama
    4. ❌ FALTA: Verificar que publish_deferrable_loads() se llama
    5. ❌ FALTA: Verificar que coordinator.data se actualiza
    6. ❌ FALTA: Verificar que EmhassDeferrableLoadSensor muestra nuevos datos
    """
```

### Archivo donde debería estar:
`tests/test_config_entry_updates.py` (crear)

---

## 5. SERVICIOS HA (CRUD de viajes) - 10 servicios

### ¿Hay tests?
⚠️ **PARCIAL** - `tests/test_services_core.py`

### Tests existentes:
- `test_services_use_seeded_trip_manager_instance`
- Tests que verifican que los servicios se registran

### ¿Qué prueban?
✅ Verifican que los servicios se registran correctamente
✅ Verifican que se llaman los métodos del TripManager

### ¿Qué NO prueban?
❌ **NO verifican que el sensor EMHASS se actualice** después de llamar al servicio
❌ Solo verifican que se llama al método, no el efecto final en el sensor

### Test faltante (ejemplo para add_recurring_trip):
```python
async def test_add_recurring_trip_service_updates_emhass_sensor():
    """
    Test que el servicio add_recurring_trip actualiza el sensor EMHASS.

    1. Llamar al servicio ev_trip_planner.add_recurring_trip
    2. Verificar que async_add_recurring_trip() se llama ✅ (ya existe)
    3. ❌ FALTA: Verificar que publish_deferrable_loads() se llama
    4. ❌ FALTA: Verificar que coordinator.async_refresh() se llama
    5. ❌ FALTA: Verificar que EmhassDeferrableLoadSensor muestra nuevos datos
    """
```

### Servicios sin tests de actualización de sensor:
1. `ev_trip_planner.add_recurring_trip`
2. `ev_trip_planner.add_punctual_trip`
3. `ev_trip_planner.trip_create`
4. `ev_trip_planner.trip_update`
5. `ev_trip_planner.edit_trip`
6. `ev_trip_planner.delete_trip`
7. `ev_trip_planner.pause_recurring_trip`
8. `ev_trip_planner.resume_recurring_trip`
9. `ev_trip_planner.complete_punctual_trip`
10. `ev_trip_planner.cancel_punctual_trip`

---

## 6. SINCRONIZACIÓN INTERNA DEL TRIP_MANAGER

### ¿Hay tests?
⚠️ **PARCIAL** - `tests/test_trip_manager_core.py`

### Tests existentes:
- `test_async_add_recurring_trip_calls_publish_deferrable_loads_when_adapter_set`
- `test_async_add_punctual_trip_calls_publish_deferrable_loads_when_adapter_set`
- `test_async_update_trip_calls_sync_trip_to_emhass_when_adapter_set`
- `test_async_delete_trip_calls_remove_trip_from_emhass_when_adapter_set`
- `test_async_cancel_punctual_trip_calls_remove_trip_from_emhass_when_adapter_set`
- `test_async_sync_trip_to_emhass_with_inactive_trip`
- `test_async_sync_trip_to_emhass_with_km_change_triggers_recalculate`
- `test_async_sync_trip_to_emhass_handles_exception`

### ¿Qué prueban?
✅ Verifican que `_async_publish_new_trip_to_emhass()` se llama
✅ Verifican que `_async_sync_trip_to_emhass()` se llama
✅ Verifican que `_async_remove_trip_from_emhass()` se llama
✅ Verifican que `publish_deferrable_loads()` se llama

### ¿Qué NO prueban?
❌ **NO verifican que el sensor EMHASS se actualice** después de la sincronización
❌ Solo verifican que se llamen los métodos, no el efecto final en el sensor

### Test faltante:
```python
async def test_async_publish_new_trip_to_emhass_updates_sensor():
    """
    Test que _async_publish_new_trip_to_emhass actualiza el sensor.

    1. Llamar a async_add_recurring_trip()
    2. Verificar que publish_deferrable_loads() se llama ✅ (ya existe)
    3. ❌ FALTA: Verificar que coordinator.async_refresh() se llama
    4. ❌ FALTA: Verificar que EmhassDeferrableLoadSensor muestra nuevos datos
    """
```

---

## 7. INICIO / REINICIO DE HOME ASSISTANT

### ¿Hay tests?
⚠️ **PARCIAL** - `tests/test_sensor_exists_fn.py`, `tests/test_entity_registry.py`

### Tests existentes:
- Tests que mockean `async_config_entry_first_refresh`
- Tests que verifican que `async_setup_entry` crea sensores

### ¿Qué prueban?
✅ Verifican que los sensores se crean correctamente
✅ Verifican que `async_config_entry_first_refresh` se llama

### ¿Qué NO prueban?
❌ **NO verifican que el sensor EMHASS tenga datos correctos** después del inicio
❌ Solo verifican que se creen los sensores, no que tengan datos actualizados

### Test faltante:
```python
async def test_async_setup_entry_populates_emhass_sensor_with_current_data():
    """
    Test que async_setup_entry carga datos actuales en el sensor EMHASS.

    1. Llamar a async_setup_entry()
    2. Verificar que async_config_entry_first_refresh() se llama ✅ (ya existe)
    3. ❌ FALTA: Verificar que publish_deferrable_loads() se llama
    4. ❌ FALTA: Verificar que coordinator.data tiene datos EMHASS
    5. ❌ FALTA: Verificar que EmhassDeferrableLoadSensor muestra datos iniciales
    """
```

---

## 8. MIGRACIÓN DE CONFIG ENTRY

### ¿Hay tests?
⚠️ **PARCIAL** - `tests/test_migrate_entry.py`

### Tests existentes:
- `test_migrate_entry_version2_entity_registry`
- Tests que verifican que `battery_capacity` → `battery_capacity_kwh`

### ¿Qué prueban?
✅ Verifican que los datos de configuración se migran correctamente
✅ Verifican que el entity registry se actualiza

### ¿Qué NO prueban?
❌ **NO verifican que el sensor EMHASS se actualice** después de la migración
❌ Solo verifican migración de datos, no actualización del sensor

### Test faltante:
```python
async def test_migrate_entry_updates_emhass_sensor_with_new_config():
    """
    Test que async_migrate_entry actualiza el sensor EMHASS.

    1. Migrar de version 1 a version 2
    2. Verificar que battery_capacity_kw se migra ✅ (ya existe)
    3. ❌ FALTA: Verificar que update_charging_power() se llama
    4. ❌ FALTA: Verificar que publish_deferrable_loads() se llama
    5. ❌ FALTA: Verificar que EmhassDeferrableLoadSensor muestra datos actualizados
    """
```

---

## 9. ELIMINACIÓN / CLEANUP

### ¿Hay tests?
⚠️ **PARCIAL** - `tests/test_coverage_100_percent.py`, `tests/test_entity_registry.py`, `tests/test_post_restart_persistence.py`

### Tests existentes:
- `test_async_delete_all_trips_h欠exceptions`
- `test_delete_all_trips_removes_from_storage`
- Tests que mockean `async_delete_all_trips`

### ¿Qué prueban?
✅ Verifican que `async_delete_all_trips()` se llama
✅ Verifican que los viajes se eliminan del storage

### ¿Qué NO prueban?
❌ **NO verifican que el sensor EMHASS se actualice** después de eliminar
❌ Solo verifican que se eliminen los datos, no que el sensor se actualice

### Test faltante:
```python
async def test_delete_all_trips_updates_emhass_sensor_to_empty():
    """
    Test que async_delete_all_trips actualiza el sensor EMHASS a estado vacío.

    1. Llamar a async_delete_all_trips()
    2. Verificar que publish_deferrable_loads([]) se llama ✅ (ya existe)
    3. ❌ FALTA: Verificar que coordinator.async_refresh() se llama
    4. ❌ FALTA: Verificar que EmhassDeferrableLoadSensor muestra schedule vacío
    """
```

---

## 🚨 CONCLUSIÓN: Tests FLOJOS

### Problema General:
**TODOS los tests existentes son TESTS FLOJOS**:

```python
# ❌ TEST FLOJO (lo que hay ahora)
async def test_xxx():
    await some_action()
    mock_method.assert_called_once()  # Solo verifica que se llama

# ✅ TEST COMPLETO (lo que falta)
async def test_xxx_updates_emhass_sensor():
    await some_action()

    # 1. Verificar que se llama al método
    mock_method.assert_called_once()  # ✅ Ya existe

    # 2. Verificar que el coordinator se actualiza
    assert coordinator.data["emhass_power_profile"] is not None  # ❌ FALTA

    # 3. Verificar que el sensor muestra los nuevos datos
    assert sensor.native_value == expected_value  # ❌ FALTA
```

### Tests que FALTAN:

1. **Categoría 1** (Refresh periódico): 0/1 tests
2. **Categoría 2** (Cambio SOC): 1/2 tests (falta verificar actualización del sensor)
3. **Categoría 3** (Timer horario): 1/2 tests (falta verificar actualización del sensor)
4. **Categoría 4** (Cambio config): 0/1 tests
5. **Categoría 5** (Servicios HA): 0/10 tests (uno por cada servicio)
6. **Categoría 6** (Sincronización interna): 4/8 tests (falta verificar actualización del sensor en 4)
7. **Categoría 7** (Inicio/Reinicio): 0/1 tests
8. **Categoría 8** (Migración): 0/1 tests
9. **Categoría 9** (Eliminación): 0/1 tests

**TOTAL: 5/27 tests completos (18.5% de cobertura)**

### Lo que esto explica:

**Esto explica POR QUÉ el bug del cache obsoleto no se detectó**:

- Los tests verifican que se llamen los métodos ✅
- PERO NO verifican que el sensor se actualice ❌
- El coordinator llama a `get_cached_optimization_results()` ✅
- PERO ese método solo lee cache obsoleto, nunca lo regenera ❌
- Los tests PASAN porque solo verifican que se llame al método ❌
- El usuario ve el sensor obsoleto porque el cache nunca se regenera ❌

### Solución:

Crear **tests de integración completa** que verifiquen el flujo end-to-end:

```
TRIGGER → publish_deferrable_loads() → coordinator.data → Sensor actualizado
```

NO solo:

```
TRIGGER → publish_deferrable_loads() ✅ (lo que hay ahora)
```
