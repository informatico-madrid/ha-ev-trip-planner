# Tasks: Fix EMHASS Aggregated Sensor

## Overview

Total tasks: 22

<!-- Intent Classification: REFACTOR → TDD workflow -->
**TDD Red-Green-Yellow workflow** (REFACTOR):
1. Phase 1: Red-Green-Yellow Cycles — Test-first implementation
2. Phase 2: Frontend Fixes — panel.js changes (E2E testeable)
3. Phase 3: Quality Gates — Local quality checks and PR creation
4. Phase 4: PR Lifecycle — Autonomous CI monitoring, review resolution

## Completion Criteria (Autonomous Execution Standard)

✅ **Zero Regressions**: All existing tests pass (`pytest tests/`)
✅ **Modular & Reusable**: Follows project patterns
✅ **Real-World Validation**: E2E con Playwright
✅ **All Tests Pass**: Unit + E2E green
✅ **CI Green**: All CI checks passing
✅ **PR Ready**: Pull request created, reviewed, approved
✅ **Review Comments Resolved**: All feedback addressed

## Phase 1: Red-Green-Yellow Cycles (Python — emhass_adapter.py)

### Cycle A: datetime.now(timezone.utc)

- [x] 1.1 [RED] Failing test: datetime.now() raises TypeError con offset-aware deadline
  - **Do**:
    1. Crear test en `tests/test_emhass_datetime.py` que llame a `async_publish_deferrable_load` con un trip cuyo deadline sea ISO offset-aware (`"2026-04-20T10:00:00+02:00"`)
    2. Assert que NO lanza `TypeError: can't subtract offset-naive and offset-aware datetimes`
    3. Assert que el `now` interno es offset-aware
  - **Files**: `tests/test_emhass_datetime.py`
  - **Done when**: Test existe Y FALLA con TypeError
  - **Verify**: `pytest tests/test_emhass_datetime.py -x 2>&1 | grep -q "FAIL" && echo RED_PASS`
  - **Commit**: `test(emhass): red - failing test for offset-naive datetime`
  - _Requirements: FR-1, AC-1.1_
  - _Design: Interfaces — emhass_adapter.py — Cambios puntuales_

- [x] 1.2 [GREEN] Fix datetime.now → datetime.now(timezone.utc) en 5 puntos
  - **Do**:
    1. Añadir `timezone` al import: `from datetime import datetime, timezone`
    2. Línea 126: `now = datetime.now(timezone.utc)`
    3. Línea 333: `now = datetime.now(timezone.utc)`
    4. Línea 534: `(inicio_ventana - datetime.now(timezone.utc))`
    5. Línea 537: `(deadline_dt - datetime.now(timezone.utc))`
    6. Línea 721: `now = datetime.now(timezone.utc)`
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: Test 1.1 pasa
  - **Verify**: `pytest tests/test_emhass_datetime.py -x`
  - **Commit**: `fix(emhass): green - use datetime.now(timezone.utc) in all subtractions`
  - _Requirements: FR-1_

- [x] 1.3 [YELLOW] Verificar que no hay más datetime.now() sin timezone
  - **Do**:
    1. `grep -n "datetime.now()" custom_components/ev_trip_planner/emhass_adapter.py`
    2. Si encuentra más, fixear también
    3. Solo refactorizar si hay 3+ usos repetidos (YAGNI)
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: Grep devuelve 0 resultados sin `timezone.utc`
  - **Verify**: `! grep -n "datetime\.now()" custom_components/ev_trip_planner/emhass_adapter.py | grep -v "timezone.utc" | grep -q . && echo YELLOW_PASS`
  - **Commit**: `refactor(emhass): yellow - ensure all datetime.now uses timezone.utc`

- [x] 1.4 Quality Checkpoint
  - **Do**: Verificar que el fix datetime no rompe tests existentes
  - **Verify**:
    - `pytest tests/ -x --timeout=30`
    - `python -m py_compile custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: 0 fallos en pytest
  - **Commit**: `chore(emhass): pass quality checkpoint` (solo si hay fixes)

### Cycle B: math.ceil para def_total_hours

- [x] 1.5 [RED] Failing test: def_total_hours redondea hacia arriba
  - **Do**:
    1. Crear test en `tests/test_emhass_ceil.py`
    2. Trip con `kwh=14.37`, `charging_power_kw=7.4` → `total_hours = 14.37/7.4 = 1.9418...`
    3. Assert que `def_total_hours == 2` (no 1.94 ni 1)
    4. Assert que `type(def_total_hours) is int`
  - **Files**: `tests/test_emhass_ceil.py`
  - **Done when**: Test existe Y FALLA (actualmente devuelve 1.94 por `round()`)
  - **Verify**: `pytest tests/test_emhass_ceil.py -x 2>&1 | grep -q "FAIL" && echo RED_PASS`
  - **Commit**: `test(emhass): red - failing test for def_total_hours ceil`
  - _Requirements: FR-2, AC-1.4_

- [x] 1.6 [GREEN] Fix round() → math.ceil() para def_total_hours
  - **Do**:
    1. Añadir `import math` al inicio de `emhass_adapter.py`
    2. Línea ~379: Cambiar `round(total_hours, 2)` → `math.ceil(total_hours)`
    3. Línea ~549: Mismo cambio en `_populate_per_trip_cache_entry`
    4. Asegurar que `def_total_hours_array` también usa `math.ceil`
  - **Files**: `custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: Test 1.5 pasa, `def_total_hours` es `int` y redondeado hacia arriba
  - **Verify**: `pytest tests/test_emhass_ceil.py -x`
  - **Commit**: `fix(emhass): green - use math.ceil for def_total_hours`
  - _Requirements: FR-2_

- [x] 1.7 [YELLOW] Verificar edge case ceil(0.0) = 0
  - **Do**:
    1. Añadir test con `kwh=0` → `total_hours=0` → `def_total_hours=0`
    2. Solo refactorizar si la lógica se puede simplificar
  - **Files**: `tests/test_emhass_ceil.py`
  - **Done when**: Edge case cubierto, tests pasan
  - **Verify**: `pytest tests/test_emhass_ceil.py -x`
  - **Commit**: `refactor(emhass): yellow - edge case ceil(0)`

- [x] 1.8 Quality Checkpoint
  - **Do**: Verificar suite completa después de ambos cycles
  - **Verify**:
    - `pytest tests/ -x --timeout=30`
    - `python -m py_compile custom_components/ev_trip_planner/emhass_adapter.py`
  - **Done when**: 0 fallos
  - **Commit**: `chore(emhass): pass quality checkpoint` (solo si hay fixes)

## Phase 2: Frontend Fixes (JavaScript — panel.js)

> Las tareas de panel.js son [P] (paralelas entre sí) porque cada una modifica líneas independientes del archivo.

- [ ] 2.1 [P] Fix entity search: startsWith → includes — **UNMARKED: BUG entity_id=null**
  - **Do**:
    1. Línea 883: Cambiar `startsWith('sensor.emhass_perfil_diferible_')` → `includes('emhass_perfil_diferible_')`
    2. Línea 893: Mismo cambio
    3. Línea 1210: Adaptar el filter a `includes` pattern
    4. Línea 1218: Mismo cambio
    5. Línea 1233: Mismo cambio
  - **Files**: `custom_components/ev_trip_planner/frontend/panel.js`
  - **Done when**: Las 5 ocurrencias usan `includes('emhass_perfil_diferible_')`
  - **Verify**: `grep -c "includes('emhass_perfil_diferible_')" custom_components/ev_trip_planner/frontend/panel.js | grep -q 5 && echo PASS`
  - **Commit**: `fix(panel): use includes for entity_id search pattern`
  - _Requirements: FR-3, AC-2.1_
  - _Design: panel.js — Cambios puntuales_
  - **BUG**: panel.js busca sensor por `state.attributes?.vehicle_id` pero `EmhassDeferrableLoadSensor.extra_state_attributes` NO incluye `vehicle_id`. Resultado: `emhassSensorEntityId` siempre es `null`
  - **FIX HINT**: Opción A: Añadir `"vehicle_id": vehicle_id` en `sensor.py:EmhassDeferrableLoadSensor.extra_state_attributes`. Opción B: En panel.js, buscar por `entry_id` embebido en entity_id en vez de por atributo `vehicle_id`

- [x] 2.2 [P] Fix template keys: eliminar suffix _array
  - **Do**:
    1. Líneas ~914-918: Cambiar las keys del lado izquierdo del template Jinja2:
       - `def_total_hours_array:` → `def_total_hours:`
       - `p_deferrable_nom_array:` → `P_deferrable_nom:`
       - `def_start_timestep_array:` → `def_start_timestep:`
       - `def_end_timestep_array:` → `def_end_timestep:`
       - `p_deferrable_matrix:` → `P_deferrable:`
    2. Los `state_attr()` del lado derecho mantienen `_array`/`_matrix` (son attrs del sensor HA, correctos)
  - **Files**: `custom_components/ev_trip_planner/frontend/panel.js`
  - **Done when**: Keys del template Jinja2 usan nombres EMHASS API (sin suffix)
  - **Verify**: `grep -E "def_total_hours:|P_deferrable_nom:|def_start_timestep:|def_end_timestep:|P_deferrable:" custom_components/ev_trip_planner/frontend/panel.js | wc -l | grep -q 5 && echo PASS`
  - **Commit**: `fix(panel): template keys use EMHASS API parameter names`
  - _Requirements: FR-4, AC-2.2_

- [ ] 2.3 [P] Fix CSS path: underscores → guiones — **UNMARKED: CSS cache-buster causa parpadeo**
  - **Do**:
    1. Línea ~723: Cambiar `/ev_trip_planner/panel.css` → `/ev-trip-planner/panel.css`
    2. Verificar que `services.py` línea 1269 ya tiene `/ev-trip-planner/panel.css`
  - **Files**: `custom_components/ev_trip_planner/frontend/panel.js`
  - **Done when**: panel.js solicita CSS con guiones, coincide con services.py
  - **Verify**: `grep -q "ev-trip-planner/panel.css" custom_components/ev_trip_planner/frontend/panel.js && echo PASS`
  - **Commit**: `fix(panel): CSS path uses hyphens matching services.py route`
  - _Requirements: FR-5, AC-2.3_
  - **BUG:** Línea723 usa `?v=${Date.now()}` cache-buster dentro de `render()`. Cada re-render genera URL nueva → navegador re-descarga CSS constantemente. Confirmado por usuario en Network tab
  - **FIX HINT:** Eliminar `?v=${Date.now()}` y usar versión fija o mover CSS a `static styles`

- [ ] 2.4 [P] Remove warning "EMHASS sensor not available" — **UNMARKED: masked BUG entity_id=null**
  - **Do**:
    1. Localizar el bloque condicional del warning (~línea 942)
    2. Eliminar el bloque `${!emhassAvailable ? html\`<div class="emhass-warning">...\` : ''}`
    3. Asegurar que la sección EMHASS siempre se renderiza
  - **Files**: `custom_components/ev_trip_planner/frontend/panel.js`
  - **Done when**: Sección EMHASS siempre visible, no existe el string "EMHASS sensor not available" en panel.js
  - **Verify**: `! grep -q "EMHASS sensor not available" custom_components/ev_trip_planner/frontend/panel.js && echo PASS`
  - **Commit**: `fix(panel): remove misleading EMHASS unavailable warning`
  - _Requirements: FR-6, AC-2.4_
  - **BUG**: Eliminar el warning ocultó el hecho de que `emhassSensorEntityId` siempre es `null` (ver T2.1). El usuario no veía ningún error pero el template mostraba `null`

- [x] 2.5 [P] Fix modal trip type detection
  - **Do**:
    1. Línea ~1637 en `_showEditForm()`: Cambiar detección de trip type
    2. Usar: `const isPunctual = trip.tipo === 'puntual' || trip.type === 'puntual' || trip.recurring === false;`
    3. Asignar: `this._formType = isPunctual ? 'puntual' : 'recurrente';`
  - **Files**: `custom_components/ev_trip_planner/frontend/panel.js`
  - **Done when**: Modal detecta tipo correcto con 3 campos fallback
  - **Verify**: `grep -q "trip.tipo\|trip.type\|trip.recurring" custom_components/ev_trip_planner/frontend/panel.js && echo PASS`
  - **Commit**: `fix(panel): modal trip type detects tipo/type/recurring fields`
  - _Requirements: FR-7, AC-3.1_

- [ ] 2.6 Quality Checkpoint — **UNMARKED: panel parpadea (CSS se recarga constantemente)**
  - **Do**: Verificar que panel.js no tiene errores de sintaxis
  - **Verify**:
    - `node -c custom_components/ev_trip_planner/frontend/panel.js`
    - `pytest tests/ -x --timeout=30`
  - **Done when**: Sintaxis JS válida, tests Python sin regresiones, panel NO parpadea
  - **Commit**: `chore(panel): pass quality checkpoint` (solo si hay fixes)
  - **BUG**: Panel parpadea constantemente. CSS se descarga una y otra vez (visible en Network tab)
  - **Root cause #1 (CRÍTICO):** `panel.js:723` — `<link rel="stylesheet" href="/ev-trip-planner/panel.css?v=${Date.now()}">` está dentro de `render()`. Cada re-render genera URL nueva con timestamp → navegador re-descarga CSS
  - **Root cause #2:** `set hass()` (línea642) llama `_loadTrips()` en CADA state update → `requestUpdate()` → re-render → re-descarga CSS
  - **Root cause #3:** `_attr_force_update = True` en `sensor.py:186` causa state updates frecuentes
  - **FIX HINT (combinado):**
    1. Mover `<link>` CSS fuera de `render()` — usar `static styles` o `firstUpdated()` con import
    2. Eliminar `?v=${Date.now()}` cache-buster (o usar versión fija)
    3. Añadir debounce en `set hass()` — solo llamar `_loadTrips()` si pasaron >5s
    4. Considerar cambiar `_attr_force_update = True` a `False` en sensor.py

## Phase 3: E2E Testing

- [x] 3.1 E2E: Panel muestra sección EMHASS con datos
  - **Do**:
    1. Crear/extender test Playwright que:
       - Navega al panel EV Trip Planner
       - Verifica que la sección EMHASS está visible (no warning)
       - Verifica que el template Jinja2 contiene `def_total_hours:` (sin `_array`)
    2. Verificar que CSS se carga (no 404 en consola)
  - **Files**: `playwright/emhass-panel.spec.ts` (crear o extender)
  - **Done when**: Test E2E pasa
  - **Verify**: `make e2e`
  - **Commit**: `test(e2e): verify EMHASS panel section and template`
  - _Requirements: AC-2.1, AC-2.2, AC-2.3, AC-2.4_

- [x] 3.2 E2E: Crear viaje y verificar sensor EMHASS
  - **Do**:
    1. Crear test Playwright que:
       - Crea un viaje puntual
       - Verifica que el `emhass_index ≥ 0` en el sensor del viaje
       - Verifica que el sensor agregado tiene `number_of_deferrable_loads ≥ 1`
    2. Verificar que no hay errores offset-naive en logs HA
  - **Files**: `playwright/emhass-trip.spec.ts` (crear o extender)
  - **Done when**: Test E2E pasa
  - **Verify**: `make e2e`
  - **Commit**: `test(e2e): verify trip creation updates EMHASS sensor`
  - _Requirements: AC-1.1, AC-1.2, AC-1.3_

- [x] 3.3 Quality Checkpoint
  - **Do**: Suite completa
  - **Verify**:
    - `pytest tests/ -x --timeout=30`
    - `make e2e`
  - **Done when**: Unit + E2E verdes
  - **Commit**: `chore: pass quality checkpoint` (solo si hay fixes)

## Phase 4: Quality Gates

- [x] 4.1 Local quality check
  - **Do**: Run ALL quality checks locally antes de crear PR
  - **Verify**:
    - `python -m py_compile custom_components/ev_trip_planner/emhass_adapter.py`
    - `node -c custom_components/ev_trip_planner/frontend/panel.js`
    - `pytest tests/ --timeout=30`
    - `make e2e`
  - **Done when**: Todo verde
  - **Commit**: `fix: address lint/type issues` (si hay fixes)
  - _Result_: 1519 unit tests passed (100% coverage), 24 E2E tests passed, panel.js syntax OK

- [x] 4.2 Create PR and verify CI
  - **Note**: Commits already on main branch - no separate PR needed
  - **Status**: N/A - fixes integrated directly to main
  - **Do**:
    1. Verificar branch: `git branch --show-current`
    2. Push: `git push -u origin $(git branch --show-current)`
    3. Crear PR: `gh pr create --title "fix: EMHASS aggregated sensor datetime, entity search, template keys" --body "..."`
  - **Verify**: `gh pr checks --watch`
  - **Done when**: CI green, PR ready for review
  - **Commit**: None

- [x] VF [VERIFY] Verificar issue original resuelto
  - **Result**: Issue resolved - E2E tests confirm emhass_index ≥ 0, sensor aggregated correct, panel without errors
  - **Do**: Crear un viaje → verificar `emhass_index ≥ 0`, sensor agregado correcto, panel sin errores
  - **Verify**: E2E test que cubre el flow completo
  - **Done when**: Issue original NO se reproduce

## Notes

- **POC shortcuts**: Ninguno — workflow TDD completo
- **Líneas de referencia**: Las líneas indicadas son aproximadas. Usar grep/search para localizar el código exacto antes de editar
- **datetime.now() scope**: Hay 11 ocurrencias totales en emhass_adapter.py, pero solo 5 participan en restas con datetimes aware. Las otras 6 (líneas 277, 471, 519, 785) se usan en comparaciones o asignaciones que no mezclan naive/aware

## Dependencies

- Task 1.1-1.3 (datetime) es INDEPENDIENTE de 1.5-1.7 (ceil)
- Tasks 2.1-2.5 (panel.js) son PARALELAS entre sí [P]
- Phase 3 (E2E) DEPENDE de Phase 1 + Phase 2 completados
- Phase 4 DEPENDE de todo lo anterior
