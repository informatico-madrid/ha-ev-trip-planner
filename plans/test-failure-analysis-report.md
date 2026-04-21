# Informe de Análisis: 10 Tests Fallando + 2 Tests Skipped

## Resumen Ejecutivo

| # | Test | Estado | Error | Clasificación | Causa Raíz |
|---|------|--------|-------|--------------|-------------|
| 1 | `test_init.py::test_listener_activated_in_setup` | FALLO | `TypeError: unsupported operand type(s) for +: 'Mock' and 'float'` | **EFECTO COLATERAL** | Mi código T3.1 invoca `async_track_time_interval` que usa `loop.time()` - el mock no tiene `time.return_value` configurado |
| 2 | `test_init.py::test_async_setup_entry_vehicle_name_none` | FALLO | `TypeError: unsupported operand type(s) for +: 'Mock' and 'float'` | **EFECTO COLATERAL** | Mismo problema que #1 |
| 3 | `test_t31_hourly_refresh_tdd.py::test_t31_01_timer_registered_in_setup` | FALLO | `TypeError: object MagicMock can't be used in 'await' expression` | **TEST INCORRECTO** | Los mocks no tienen `async_forward_entry_setups` configurado como AsyncMock |
| 4 | `test_t31_hourly_refresh_tdd.py::test_t31_02_timer_cancelled_on_unload` | FALLO | `TypeError: object MagicMock can't be used in 'await' expression` | **TEST INCORRECTO** | Mismo problema que #3 |
| 5 | `test_t31_hourly_refresh_tdd.py::test_t31_03_timer_calls_publish_deferrable_loads` | FALLO | `TypeError: object MagicMock can't be used in 'await' expression` | **TEST INCORRECTO** | Mismo problema que #3 |
| 6 | `test_t31_hourly_refresh_tdd.py::test_t31_04_no_infinite_loop_between_coordinator_and_publish` | FALLO | `TypeError: object MagicMock can't be used in 'await' expression` | **TEST INCORRECTO** | Mismo problema que #3 |
| 7 | `test_t31_hourly_refresh_tdd.py::test_t31_05_timer_handles_exceptions_gracefully` | FALLO | `TypeError: object MagicMock can't be used in 'await' expression` | **TEST INCORRECTO** | Mismo problema que #3 |
| 8 | `test_t31_hourly_refresh_tdd.py::test_t31_06_timer_not_registered_multiple_times_on_reloading` | FALLO | `TypeError: object MagicMock can't be used in 'await' expression` | **TEST INCORRECTO** | Mismo problema que #3 |
| 9 | `test_emhass_datetime.py::test_datetime_subtraction_raises_typeerror` | FALLO | `assert -20.616735335277777 > 0` | **TEST OBSOLETO** | Fecha hardcodeada `"2026-04-20T10:00:00+02:00"` ya pasó (hoy es 2026-04-21) |
| 10 | `test_emhass_datetime.py::test_aware_datetime_subtraction_works` | FALLO | `assert -20.616744247222226 > 0` | **TEST OBSOLETO** | Mismo problema que #9 |
| 11 | `test_power_profile_positions.py::test_power_profile_positions_at_end_of_charging_window` | SKIP | N/A | **TEST OBSOLETO** | SOC-aware charging cambia el cálculo de `def_total_hours` |
| 12 | `test_power_profile_positions.py::test_power_profile_positions_spread_across_window` | SKIP | N/A | **TEST OBSOLETO** | SOC-aware charging cambia el cálculo de `def_total_hours` |

---

## Tests SKIPPED - Análisis Detallado

### test_power_profile_positions.py (2 tests)

**Estado:** `@pytest.mark.skip(reason="SOC-aware charging changes def_total_hours calculation - test needs update for new behavior")`

**Código del test:**
```python
@pytest.mark.asyncio
@pytest.mark.skip(reason="SOC-aware charging changes def_total_hours calculation - test needs update for new behavior")
async def test_power_profile_positions_at_end_of_charging_window(...):
```

**Causa raíz:**
- Mi implementación T3.1 (SOC-aware charging) calcula `kwh_needed` basado en el SOC actual vs energía requerida por el viaje
- El test espera `def_total_hours == 2` pero con SOC-aware:
  - Si SOC >= 50%, `kwh_needed = 0` → `def_total_hours = 0`
  - Si SOC = 20%, `kwh_needed = 7 kWh` → `def_total_hours = 2`
- El test usa `soc_current=20.0` pero la línea 94 verifica `assert def_total_hours == 2` que ahora depende del SOC

**Clasificación: TEST OBSOLETO**
- El test fue escrito para el comportamiento ANTES de SOC-aware charging
- Con SOC-aware, el comportamiento es correcto pero el test necesita actualización
- No es un bug en el código - es un test que no refleja el nuevo comportamiento esperado

**Solución recomendada:**
1. **Opción A (eliminar test):** El test es demasiado específico para un comportamiento que ahora es dinámico
2. **Opción B (actualizar test):** Modificar para verificar que `def_total_hours` se calcula correctamente DADO un SOC específico
3. **Opción C (desmarcar skip):** Si el SOC=20% produce `def_total_hours=2`, el test debería pasar sin cambios

**Análisis de la solución:**
- Revisando el test, usa `soc_current=20.0` que debería producir `kwh_needed=7` → `def_total_hours=2`
- El test debería pasar si el SOC-aware charging funciona correctamente
- El skip fue añadido temporalmente durante el desarrollo
- **Recomendación: Desmarcar el skip y verificar si pasa**

---

## Análisis Detallado por Grupo

### GRUPO A: tests/test_init.py (2 tests) - FALLO

**Error:**
```
TypeError: unsupported operand type(s) for +: 'Mock' and 'float'
```

**Traza del error:**
```python
# homeassistant/helpers/event.py:1650
self._timer_handle = loop.call_at(
    loop.time() + self.seconds, self._interval_listener, self._track_job
)
```

**Causa raíz:**
- El fixture `mock_hass` (línea 21-39) tiene `hass.loop = Mock()` sin configurar `time.return_value`
- Mi código T3.1 en `__init__.py` llama a `async_track_time_interval` que internamente usa `loop.time()`
- `loop.time()` devuelve un Mock, y `Mock + float` falla

**Clasificación: EFECTO COLATERAL**
- Los tests NO están probando el timer - están probando que `setup_config_entry_listener` se llama
- Mi código T3.1 añade código que invoca el timer, lo cual causa el error en tests que no mockearon esa parte
- Los tests estaban pasando ANTES de mis cambios

**Solución recomendada:**
1. **Opción A (recomendada):** Añadir `hass.loop.time.return_value = 0.0` al fixture `mock_hass`
   - Impacto bajo: afecta todos los tests que usan este fixture
   - Beneficio: todos los tests que usan `loop.time()` se benefician

---

### GRUPO B: tests/test_t31_hourly_refresh_tdd.py (6 tests) - FALLO

**Error:**
```
TypeError: object MagicMock can't be used in 'await' expression
```

**Traza del error:**
```python
# custom_components/ev_trip_planner/__init__.py:177
await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
```

**Causa raíz:**
- Los tests usan `create_mock_ev_config_entry()` que no configura `async_forward_entry_setups` como AsyncMock
- Cuando `async_setup_entry` intenta `await hass.config_entries.async_forward_entry_setups(...)`, falla porque es un MagicMock no-async

**Clasificación: TEST INCORRECTO**
- Estos tests fueron creados por mí para el T3.1
- Los mocks no están correctamente configurados para el flujo de `async_setup_entry`
- El problema es que los tests intentan mockear `async_track_time_interval` pero el código llega a `async_forward_entry_setups` primero

**Solución recomendada:**
1. Los tests necesitan configurar mocks completos para todos los métodos async en `hass.config_entries`:
   ```python
   hass.config_entries.async_forward_entry_setups = AsyncMock()
   hass.config_entries.async_unload_platforms = AsyncMock()
   ```

---

### GRUPO C: tests/test_emhass_datetime.py (2 tests) - FALLO

**Error:**
```
assert -20.616735335277777 > 0
```

**Causa raíz:**
- Las fechas hardcodeadas `"2026-04-20T10:00:00+02:00"` ya pasaron
- Hoy es `2026-04-21`, por lo que `hours_available` es negativo
- El test no es un "bug pre-existente" como se pensó antes - es simplemente **fecha expirada**

**Clasificación: TEST OBSOLETO**
- El test ya no tiene sentido porque la fecha pasó
- No es un bug en el código de producción ni en el test original
- Es simplemente un test que usa fechas relativas que ya no son válidas

**Solución recomendada:**
1. Usar fechas relativas en lugar de hardcodear:
   ```python
   from datetime import timedelta
   deadline = datetime.now(timezone.utc) + timedelta(days=1)
   ```

---

### GRUPO D: tests/test_power_profile_positions.py (2 tests) - SKIP

**Estado:** `@pytest.mark.skip(reason="SOC-aware charging changes def_total_hours calculation - test needs update for new behavior")`

**Causa raíz:**
- Mi implementación T3.1 (SOC-aware charging) calcula `kwh_needed` basado en el SOC actual
- El test espera `def_total_hours == 2` pero esto depende del SOC actual
- El test usa `soc_current=20.0` que debería producir `def_total_hours=2`

**Clasificación: TEST OBSOLETO (pero potencialmente válido)**
- El test fue escrito para el comportamiento ANTES de SOC-aware charging
- Con SOC-aware, el comportamiento es correcto pero el test necesita verificación
- **El test podría pasar si el SOC-aware charging funciona correctamente**

**Solución recomendada:**
1. **Desmarcar el skip y ejecutar el test**
2. Si falla, actualizar el test para verificar el comportamiento SOC-aware correcto
3. Si pasa, el skip era innecesario

---

## Plan de Acción por Prioridad

| Prioridad | Test | Acción | Complejidad |
|-----------|------|--------|-------------|
| 1 | test_init.py (2 tests) | Añadir `hass.loop.time.return_value = 0.0` al fixture | Baja |
| 2 | test_power_profile_positions.py (2 tests) | Desmarcar @pytest.mark.skip y verificar | Baja |
| 3 | test_emhass_datetime.py (2 tests) | Actualizar fechas hardcodeadas a futuro | Baja |
| 4 | test_t31_hourly_refresh_tdd.py (6 tests) | Configurar mocks async correctamente | Media |

---

## Confirmación de git stash

Según el análisis previo, los bugs de `test_emhass_datetime.py` fueron marcados como "pre-existentes". Sin embargo, tras examinar el código del test, la causa real es fecha hardcodeada expirada, no un bug en el código de producción.

Los tests de `test_t31_hourly_refresh_tdd.py` fueron creados por mí durante el sprint actual y tienen problemas de mock que necesito arreglar.

Los tests de `test_init.py` fallan debido a efectos secundarios de mi implementación T3.1 que añade un timer sin que los tests existentes lo esperen.

Los tests de `test_power_profile_positions.py` están skipados porque el SOC-aware charging cambia el comportamiento esperado. El test podría pasar si el SOC=20% produce el `def_total_hours=2` esperado.
