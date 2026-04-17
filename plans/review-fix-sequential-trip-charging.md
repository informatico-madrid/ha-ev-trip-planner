# Revisión: Spec `fix-sequential-trip-charging`

**Fecha**: 2026-04-16
**Spec**: `specs/fix-sequential-trip-charging/`
**Artículos revisados**: requirements.md, research.md, design.md, tasks.md, .research-codebase.md, .research-emhass-patterns.md

---

## Resumen Ejecutivo

La spec identifica correctamente el **root cause** del bug (`def_start_timestep_array: [0, 0]`) y propone un enfoque de fix válido (batch processing). Sin embargo, se han encontrado **5 issues críticos**, **2 issues medios** y **3 issues menores** que deben resolverse antes de la implementación para evitar regresiones y asegurar que el fix sea efectivo.

---

## ✅ Lo que está BIEN

1. **Root cause correcto**: La spec identifica acertadamente que [`calculate_multi_trip_charging_windows()`](custom_components/ev_trip_planner/calculations.py:339) se llama con un solo trip por vez en [`async_publish_deferrable_load()`](custom_components/ev_trip_planner/emhass_adapter.py:363) y [`_populate_per_trip_cache_entry()`](custom_components/ev_trip_planner/emhass_adapter.py:531), causando que la lógica secuencial (idx > 0) nunca se ejecute.

2. **Enfoque de fix válido**: Option A (batch process all trips antes del loop) es correcto y usa la función existente como fue diseñada.

3. **No se necesita cambiar `sensor.py`**: La agregación por `.extend()` en [`sensor.py:254-255`](custom_components/ev_trip_planner/sensor.py:254) ya funciona correctamente.

4. **`p_deferrable_matrix` y `def_end_timestep_array` no se modifican**: Correcto, estos ya funcionan bien.

5. **Research exhaustivo**: Los documentos `.research-codebase.md` y `.research-emhass-patterns.md` son completos y precisados.

6. **Test existente confirma la función funciona**: [`test_chained_trips_second_window_starts_at_previous_arrival`](tests/test_calculations.py:453) demuestra que cuando se llama con múltiples trips, la función produce resultados correctos.

---

## 🔴 Issues CRÍTICOS

### CRITICAL-1: Confusión semántica entre `duration_hours` y `return_buffer_hours`

**Problema**: El parámetro `duration_hours` en [`calculate_multi_trip_charging_windows()`](custom_components/ev_trip_planner/calculations.py:344) sirve un **doble propósito**:

- **Duración del viaje** (línea 382): `trip_arrival = trip_departure_time + timedelta(hours=duration_hours)` — calcula cuándo vuelve el coche
- **Fallback de ventana** (línea 376): `window_start = trip_departure_time - timedelta(hours=duration_hours)` — fallback cuando `hora_regreso` es None

La spec propone renombrar `duration_hours` → `return_buffer_hours`, pero esto es **semánticamente incorrecto** para la línea 382. Un "return buffer" de 4h no significa que el viaje dure 4h.

**Impacto**: Si se renombra sin más cambios, el `trip_arrival` se calculará con el valor del buffer (4h por defecto) en vez de la duración real del viaje (6h), produciendo `previous_arrival` incorrectos y ventanas de carga erróneas.

**Solución propuesta**:
- Mantener `duration_hours` como parámetro de duración del viaje (líneas 376, 382)
- Añadir un NUEVO parámetro `return_buffer_hours: float = 0.0` para el gap configurable
- Modificar la línea 419: `previous_arrival = trip_arrival + timedelta(hours=return_buffer_hours)`

### CRITICAL-2: No se implementa el return buffer real

**Problema**: El design.md dice "Keep internal logic unchanged" para Component 2, pero la función actual NO tiene concepto de "return buffer". En la línea 419:

```python
previous_arrival = trip_arrival  # NO hay buffer entre viajes
```

Sin modificar esta línea, el "return buffer configurable" (FR-3, AC-2.1 a AC-2.5) **no funcionará**. El siguiente viaje empezará exactamente cuando el anterior llega, sin gap configurable.

**Solución**: Ver CRITICAL-1.

### CRITICAL-3: Test existente afirma el comportamiento BUGGY — REGRESIÓN SEGURA

**Problema**: En [`test_sensor_coverage.py:1358`](tests/test_sensor_coverage.py:1358):

```python
assert attrs["def_start_timestep_array"] == [0, 0, 0], (
    f"def_start_timestep_array should be in sorted order, got {attrs['def_start_timestep_array']}"
)
```

Este test **afirma explícitamente que `def_start_timestep_array` es `[0, 0, 0]`**, que es exactamente el bug que queremos corregir. Después del fix, este test FALLARÁ.

La spec **no menciona este test** en ninguna tarea. Esto causará una regresión de test garantizada.

**Solución**: Añadir una tarea para actualizar este test con los valores esperados post-fix. El nuevo assertion debe verificar offsets secuenciales, no `[0, 0, 0]`.

### CRITICAL-4: No hay test que falle ANTES del fix (violación TDD)

**Problema**: El usuario pidió explícitamente "que haya test que primero detecten el problema para que no se vuelva a reproducir sin un test que lo detecte". Sin embargo:

- **Phase 1** (tareas 1.1-1.22): Toda la implementación
- **Phase 3** (tareas 3.1-3.15): Todos los tests

No hay ningún test que falle con el código actual y pase después del fix. Esto viola el principio TDD y no garantiza que el test detecte el bug.

**Solución**: Añadir una **Phase 0** con un test que:
1. Llame a `_populate_per_trip_cache_entry` con 2 trips secuenciales
2. Verifique que `def_start_timestep_array[1] > 0` (falla con código actual)
3. Este test debe fallar antes del fix y pasar después

### CRITICAL-5: No hay test E2E planificado

**Problema**: El usuario pidió específicamente que los tests E2E sigan el patrón `make e2e` existente. La spec no incluye NINGÚN test E2E.

**Contexto**: Los tests E2E existentes (en [`tests/e2e/`](tests/e2e/)) siguen un patrón claro:
- [`auth.setup.ts`](auth.setup.ts) maneja autenticación via `globalSetup`
- [`trips-helpers.ts`](tests/e2e/trips-helpers.ts) provee `navigateToPanel()`, `createTestTrip()`, `deleteTestTrip()`
- Cada spec usa `test.beforeEach` → `navigateToPanel(page)` → `cleanupTestTrips(page)`
- Se ejecutan via `make e2e` → [`scripts/run-e2e.sh`](scripts/run-e2e.sh) que levanta HA limpio

**Solución**: Añadir un test E2E que:
1. Cree 2 viajes secuenciales
2. Verifique via API REST de HA que el sensor muestra `def_start_timestep_array` con offsets correctos
3. Siga el patrón existente de `navigateToPanel` + helpers

---

## 🟡 Issues MEDIOS

### MEDIUM-1: Tarea 1.9 es innecesaria

**Problema**: La tarea 1.9 pide actualizar [`async_publish_deferrable_load()`](custom_components/ev_trip_planner/emhass_adapter.py:363) para usar `return_buffer_hours=self._return_buffer_hours`. Sin embargo, el `def_start_timestep` calculado en esa función (líneas 372-378) se almacena en `attributes` dict que **nunca se escribe a HA state** (las líneas 402-405 están comentadas). El resultado es efectivamente **unused**.

El cache real se popula en [`_populate_per_trip_cache_entry()`](custom_components/ev_trip_planner/emhass_adapter.py:489) (segundo loop).

**Impacto**: No rompe nada, pero añade complejidad innecesaria.

**Solución**: Eliminar tarea 1.9 o marcarla como opcional. El foco debe estar en `_populate_per_trip_cache_entry()`.

### MEDIUM-2: Falta claridad en la integración del batch con el loop existente

**Problema**: [`async_publish_all_deferrable_loads()`](custom_components/ev_trip_planner/emhass_adapter.py:606) tiene DOS loops:

1. **Loop 1** (línea 633): `async_publish_deferrable_load(trip)` — asigna índices
2. **Loop 2** (línea 671): `_populate_per_trip_cache_entry()` — popula cache

La spec propone añadir batch computation ANTES del loop 1 (tarea 1.11) y mapear resultados en el loop 2 (tarea 1.12). Pero no aclara qué hacer con la llamada a `calculate_multi_trip_charging_windows()` dentro de `_populate_per_trip_cache_entry()` (línea 531). La tarea 1.14 añade `pre_computed_def_start_timestep` pero el método sigue llamando a `calculate_multi_trip_charging_windows()` con un solo trip para otros cálculos (ventana_horas, etc.).

**Solución**: Clarificar en la spec que `_populate_per_trip_cache_entry()` debe aceptar el `inicio_ventana` pre-computado del batch y usarlo directamente, evitando la llamada redundante a `calculate_multi_trip_charging_windows()`.

---

## 🟢 Issues MENORES

### LOW-1: Tarea 1.3 redundante con 1.2

La tarea 1.3 (añadir import) debería ser parte de la tarea 1.2 (añadir al schema), no una tarea separada. Ambas modifican el mismo archivo.

### LOW-2: POC checkpoint (1.22) asume renombrado ya hecho

El script POC usa `return_buffer_hours=4.0` como keyword argument, pero el parámetro no se renombra hasta la tarea 1.6. Si se ejecutan en orden, funciona, pero si alguien intenta el POC antes de completar 1.6, fallará.

### LOW-3: Default 6.0 → 4.0 en dos fases añade complejidad

La spec cambia el default de 6.0 a 4.0 en dos pasos (Phase 1 mantiene 6.0, Phase 2 cambia a 4.0). Esto es innecesariamente complejo. Se debería usar el default final desde el inicio.

---

## 📊 Matriz de Regresión

| Test existente | Impacto del fix | Acción requerida |
|---|---|---|
| [`test_sensor_coverage.py:1358`](tests/test_sensor_coverage.py:1358) — `assert [0,0,0]` | **ROMPERÁ** — espera `[0,0,0]`, recibirá offsets | Actualizar assertion |
| [`test_calculations.py:453`](tests/test_calculations.py:453) — chained trips | Sin impacto — prueba la función pura directamente | Ninguna |
| [`test_emhass_adapter.py`](tests/test_emhass_adapter.py) — mock de `calculate_multi_trip_charging_windows` | Posible impacto — mock puede necesitar actualización si cambia la firma | Verificar |
| [`test_charging_window.py`](tests/test_charging_window.py) — integration tests | Posible impacto — usan TripManager real | Verificar |
| Tests E2E existentes | Sin impacto — no verifican `def_start_timestep_array` | Ninguna |

---

## 📋 Recomendaciones de Reordenación

El orden correcto debería ser:

```
Phase 0: Test que falle (TDD)
  0.1 Escribir test que demuestre el bug (def_start_timestep_array = [0,0] para trips secuenciales)
  0.2 Verificar que el test falla con código actual

Phase 1: Fix mínimo
  1.1 Añadir constantes a const.py
  1.2 Añadir return_buffer_hours a config_flow.py
  1.3 Almacenar return_buffer_hours en EMHASSAdapter.__init__
  1.4 Modificar calculate_multi_trip_charging_windows() para aceptar return_buffer_hours separado
  1.5 Añadir batch computation en async_publish_all_deferrable_loads()
  1.6 Modificar _populate_per_trip_cache_entry() para usar batch results
  1.7 Actualizar test_sensor_coverage.py assertion [0,0,0]
  1.8 Verificar test de Phase 0 ahora pasa

Phase 2: Tests complementarios
  2.1 Tests de edge cases
  2.2 Tests de integración
  2.3 Test E2E (opcional pero recomendado)

Phase 3: Calidad
  3.1 Full test suite
  3.2 Lint + mypy
  3.3 PR
```

---

## Conclusión

La spec tiene una base sólida pero necesita correcciones importantes antes de implementarse:

1. **No renombrar** `duration_hours` — añadir `return_buffer_hours` como parámetro NUEVO
2. **Implementar** el buffer real modificando `previous_arrival`
3. **Actualizar** el test que afirma `[0,0,0]`
4. **Añadir** Phase 0 con test que falle primero
5. **Considerar** test E2E siguiendo patrón `make e2e`
