# Issues Cerradas - Milestone 3

## Issues Resueltos en v0.3.0-dev

### Issue #12: Problemas con mocks de Store en tests de EMHASSAdapter
**Estado**: ✅ COMPLETADA (2025-12-08)

**Descripción**:
Los tests de `EMHASSAdapter` fallaban porque los mocks de `Store.async_load()` y `Store.async_save()` necesitaban usar `AsyncMock` en lugar de `MagicMock`. Esto causaba errores de tipo "object MagicMock can't be used in 'await' expression".

**Solución Implementada**:
1. Se añadió `AsyncMock` a las importaciones en `test_emhass_adapter.py`
2. Se creó un fixture `mock_store` en `conftest.py` con métodos async apropiadamente mockeados
3. Se actualizaron todos los tests para usar el fixture correcto
4. Se implementó persistencia de datos en el mock de Store para que `async_load` devuelva datos guardados por `async_save`
5. Se mejoró el mock de `hass.states` para que `async_set` almacene objetos de estado con atributos
6. Se corrigió `emhass_adapter.py` para usar `await` con `hass.states.async_set`

**Archivos Modificados**:
- `tests/conftest.py` - Añadido fixture `mock_store` con `AsyncMock` para `async_load` y `async_save`, implementada persistencia de datos y mejorado mock de estados
- `tests/test_emhass_adapter.py` - Añadida importación de `AsyncMock` y actualizados todos los tests para usar el fixture
- `custom_components/ev_trip_planner/emhass_adapter.py` - Corregida llamada a `hass.states.async_set` para usar `await`

**Resultado**:
- ✅ 11/11 tests pasando (100% de éxito)
- ✅ Todos los tests de EMHASSAdapter ahora pasan correctamente
- ✅ Mock de estados funciona correctamente con `async_set` y `get`
- ✅ Persistencia de datos en Store mock funciona correctamente

**Nota**: Esta issue fue identificada y resuelta como parte del desarrollo de Milestone 3. La próxima vez que se revisen los issues, esta ya está documentada como completada.

---

### Issue #13: Tests de EMHASSAdapter - Sensor state mock incompleto
**Estado**: ✅ COMPLETADA (2025-12-08)

**Descripción**:
Los tests `test_publish_single_trip`, `test_publish_multiple_trips_dynamic_indices`, `test_remove_deferrable_load`, y `test_update_deferrable_load` fallaban porque `hass.states.get(sensor_id)` devolvía `None`. El mock de `hass.states` no estaba configurado para devolver objetos de estado simulados.

**Causa Raíz**:
El fixture `hass` en `conftest.py` tenía:
```python
hass.states = MagicMock()
hass.states.get = MagicMock(return_value=None)
```

Pero los tests esperaban que devuelva un objeto con atributos `.state` y `.attributes`.

**Solución Implementada**:
Se configuró el mock de `hass.states.get` para que devuelva objetos `MagicMock` con atributos apropiados cuando se le pide un sensor específico. Se implementó un diccionario interno `_states_dict` para almacenar los estados creados por `async_set` y que `get` pueda recuperarlos.

**Archivos Modificados**:
- `tests/conftest.py` - Mejorado fixture `hass` con implementación funcional de `states.get` y `states.async_set`
- `tests/test_emhass_adapter.py` - Actualizados tests para usar el fixture mejorado

**Resultado**:
- ✅ Todos los tests de EMHASSAdapter pasan correctamente
- ✅ El mock de estados funciona correctamente con persistencia

---

### Issue #14: Tests de EMHASSAdapter - Persistencia de datos incompleta
**Estado**: ✅ COMPLETADA (2025-12-08)

**Descripción**:
El test `test_index_persistence` fallaba porque cuando se creaba una segunda instancia de `EMHASSAdapter`, el mock de `store.async_load()` no devolvía los datos que fueron "guardados" por la primera instancia.

**Causa Raíz**:
El mock `mock_store.async_save` no almacenaba realmente los datos, y `mock_store.async_load` siempre devolvía `None` (valor por defecto).

**Solución Implementada**:
Se implementó lógica en el mock para que `async_save` almacene datos en un diccionario interno `_storage` y `async_load` los devuelva en llamadas subsecuentes.

**Archivos Modificados**:
- `tests/conftest.py` - Añadido diccionario `_storage` al fixture `mock_store` y implementada lógica de persistencia

**Resultado**:
- ✅ El test `test_index_persistence` pasa correctamente
- ✅ Los datos persisten a través de instancias del adapter
- ✅ Simula correctamente el comportamiento de Store de Home Assistant

---

### Issue #15: Tests de Config Flow - Mock de estados no funciona
**Estado**: 🔄 EN PROGRESO (2025-12-08)

**Descripción**:
Los tests de config flow que usan `hass.states.async_set()` para crear sensores de prueba fallan porque `hass.states.get()` devuelve `None` en lugar de los estados creados.

**Tests Afectados**:
- `test_step_presence_with_sensors`
- `test_step_presence_plugged_sensor_not_found`
- `test_complete_config_flow_with_emhass_and_presence`

**Error**:
```
DEBUG: hass.states.get('binary_sensor.test_home') -> None
AssertionError: assert <FlowResultType.FORM: 'form'> == <FlowResultType.CREATE_ENTRY: 'create_entry'>
```

**Causa Raíz**:
Aunque se aplicó `await` a `hass.states.async_set()` en los tests, el fixture `hass` en `conftest.py` no está correctamente configurado para que `async_set` almacene los estados y `get` los recupere.

**Solución Requerida**:
Actualizar el fixture `hass` en `conftest.py` para asegurar que:
1. `hass.states.async_set()` es una función async que almacena estados
2. `hass.states.get()` recupera los estados almacenados
3. Los estados creados en un test están disponibles para el código bajo prueba

**Archivos a Modificar**:
- `tests/conftest.py` - Mejorar implementación del mock de `hass.states`

---

### Issue #16: Tests con Store.async_load en TripManager y Coordinator
**Estado**: 🔄 EN PROGRESO (2025-12-08)

**Descripción**:
Múltiples tests fallan con `TypeError: object MagicMock can't be used in 'await' expression` cuando `Store.async_load()` es llamado desde `TripManager` y `Coordinator`.

**Tests Afectados**:
- `test_coordinator_data_returns_trip_info` (ERROR)
- `test_coordinator_actualiza_datos_correctamente` (FAILED)
- `test_sensors_no_se_actualizan_automaticamente` (FAILED)
- `test_sensor_updates_on_coordinator_refresh` (FAILED)
- `test_recurring_trips_count_sensor` (ERROR)
- `test_punctual_trips_count_sensor` (ERROR)
- `test_trips_list_sensor` (ERROR)

**Error**:
```
TypeError: object MagicMock can't be used in 'await' expression
Location: custom_components/ev_trip_planner/trip_manager.py:79
```

**Causa Raíz**:
Los fixtures en tests que usan `Store` de Home Assistant no están usando `AsyncMock` para los métodos async. El fixture `mock_store` creado para EMHASSAdapter no está siendo usado en estos otros tests.

**Solución Requerida**:
1. Crear un fixture `mock_store` genérico en `conftest.py` que pueda ser usado por todos los tests
2. Actualizar los fixtures de `mock_trip_manager` y `coordinator` para usar el nuevo `mock_store`
3. Asegurar que `Store.async_load()` y `Store.async_save()` usen `AsyncMock`

**Archivos a Modificar**:
- `tests/conftest.py` - Crear fixture `mock_store` reutilizable
- `tests/test_coordinator.py` - Actualizar para usar `mock_store`
- `tests/test_sensors.py` - Actualizar para usar `mock_store`
- `tests/test_coordinator_update.py` - Actualizar para usar `mock_store`

---

**Last Updated**: 2025-12-08
**Milestone 3 Status**: 93.6% tests passing (146/156)
**Remaining Issues**: 2 issues en progreso (#15, #16)