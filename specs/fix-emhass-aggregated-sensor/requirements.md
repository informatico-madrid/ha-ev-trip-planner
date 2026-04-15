# Requirements: Fix EMHASS Aggregated Sensor

## Goal

Corregir los bugs que impiden la correcta publicación de viajes EV a EMHASS, la visualización del panel frontend, y la generación del template Jinja2 para la configuración de EMHASS.

## User Stories

### US-1: Publicación de viajes a EMHASS sin errores

**As a** usuario de EV Trip Planner con integración EMHASS
**I want to** crear viajes y que se publiquen correctamente en EMHASS
**So that** la optimización de carga considere todos mis viajes activos

**Acceptance Criteria:**
- AC-1.1: Crear un viaje no genera errores `offset-naive/offset-aware` en logs
- AC-1.2: El `emhass_index` del viaje creado es ≥ 0 (no -1)
- AC-1.3: El sensor agregado incluye los datos del nuevo viaje
- AC-1.4: `def_total_hours` es un entero redondeado hacia arriba (`ceil`), no un float

### US-2: Panel muestra datos EMHASS correctos

**As a** usuario del panel EV Trip Planner
**I want to** ver la sección EMHASS siempre con datos actualizados y template correcto
**So that** pueda copiar el template Jinja2 funcional para mi configuración EMHASS

**Acceptance Criteria:**
- AC-2.1: El panel encuentra y muestra el sensor EMHASS sin importar el prefijo del entity_id
- AC-2.2: El template Jinja2 usa keys sin suffix `_array` (ej: `def_total_hours:`, no `def_total_hours_array:`)
- AC-2.3: Panel.css se carga correctamente (sin 404)
- AC-2.4: No aparece warning "EMHASS sensor not available" — la sección siempre es visible

### US-3: Formulario de edición muestra datos correctos

**As a** usuario que edita un viaje puntual
**I want to** ver "puntual" seleccionado en el modal
**So that** no cambie accidentalmente el tipo de viaje

**Acceptance Criteria:**
- AC-3.1: Al editar un viaje puntual, el dropdown muestra "puntual" seleccionado

## Functional Requirements

| ID | Requirement | Priority | Acceptance Criteria |
|----|-------------|----------|---------------------|
| FR-1 | `datetime.now(timezone.utc)` en todas las restas de datetime en emhass_adapter.py (líneas 126, 333, 534, 537, 721) | P0-Critical | Sin `TypeError` en logs al crear viajes |
| FR-2 | `math.ceil(total_hours)` en vez de `round(total_hours, 2)` para def_total_hours (líneas ~379, ~549) | P1-High | Valor entero redondeado hacia arriba (ej: 1.94→2) |
| FR-3 | Búsqueda de sensor EMHASS con `includes('emhass_perfil_diferible_')` en panel.js (5 ocurrencias: líneas 883, 893, 1210, 1218, 1233) | P0-Critical | Panel encuentra sensor con cualquier prefijo |
| FR-4 | Template Jinja2 keys sin suffix `_array` (panel.js líneas ~914-918) | P0-Critical | Keys: `def_total_hours`, `P_deferrable_nom`, `def_start_timestep`, `def_end_timestep`, `P_deferrable` |
| FR-5 | CSS path `/ev-trip-planner/panel.css` (guiones) en panel.js línea 723 | P1-High | CSS carga con HTTP 200, sin errores en consola |
| FR-6 | Eliminar warning "EMHASS sensor not available" (panel.js líneas ~942) | P2-Medium | Sección EMHASS siempre visible |
| FR-7 | Modal detecta trip type con 3 campos (panel.js línea ~1637) | P2-Medium | Usa `trip.tipo`, `trip.type`, `trip.recurring` |

## Non-Functional Requirements

| ID | Requirement | Metric | Target |
|----|-------------|--------|--------|
| NFR-1 | Rendimiento del sensor EMHASS | Tiempo de actualización | < 2 segundos |
| NFR-2 | Sin regresión en tests existentes | pytest suite completa | 0 fallos |
| NFR-3 | Compatibilidad | HA version | 2024.x+ |

## Glossary

- **offset-naive**: Datetime de Python sin información de timezone (`datetime.now()`)
- **offset-aware**: Datetime con timezone (`datetime.now(timezone.utc)`, o con `+01:00`)
- **def_total_hours**: Horas totales que EMHASS debe programar para carga diferible
- **P_deferrable_nom**: Potencia nominal del cargador en watts
- **entity_id**: Identificador único de un sensor en Home Assistant
- **Jinja2 template**: Template generado por panel.js que el usuario copia a su config EMHASS
- **`math.ceil()`**: Redondeo hacia arriba — `ceil(1.94) = 2`, `ceil(0.5) = 1`

## Out of Scope

- Cambios en EMHASS core
- Modificaciones al Home Assistant core
- Nuevas features de integración EMHASS
- Cambios a la lógica de sensores individuales por viaje
- Cambios al coordinator o trip_manager (solo emhass_adapter.py y panel.js)

## Dependencies

- FR-1 (datetime fix) es root cause para: viajes no publicados, `emhass_index = -1`, sensor agregado incompleto
- FR-3 (entity search) causa que el warning de FR-6 aparezca (sensor no encontrado → warning visible)
- FR-4 (template keys) depende de FR-3 (sin sensor encontrado, no hay datos que mostrar)
- FR-2, FR-5, FR-7 son independientes entre sí

## Success Criteria

- `pytest tests/` pasa sin fallos (0 regresiones)
- Crear un viaje → `emhass_index ≥ 0` en el sensor del viaje
- Crear 2 viajes → `number_of_deferrable_loads = 2` en sensor agregado
- Panel se abre sin errores JS en consola
- Template Jinja2 copiable funciona con EMHASS REST API

## Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| Entity ID varía por config de usuario | Medium | Usar `includes()` en vez de `startsWith()` |
| `math.ceil()` podría sobreestimar horas | Low | Mejor sobrecargar que dejar el coche sin carga |
| Múltiples `datetime.now()` a fixear (5 puntos) | Medium | Verificar con grep que todas las ocurrencias están cubiertas |

## Verification Contract

> Populated by product-manager agent. Tells qa-engineer *what to observe*, not *how to test*.

**Project type**: fullstack (Python backend + JS frontend panel)

**Entry points**:
- `emhass_adapter.py`: `async_publish_deferrable_load()`, `_populate_per_trip_cache_entry()`, `async_load()`, `get_available_indices()`
- `panel.js`: Sección EMHASS (template, entity search, CSS, modal edit form)

**Observable signals**:
- PASS: Viaje creado → `emhass_index ≥ 0`, sensor agregado muestra N viajes, panel sin errores JS, template keys sin `_array`
- FAIL: `TypeError: can't subtract offset-naive and offset-aware datetimes` en logs, `emhass_index = -1`, CSS 404

**Hard invariants**: No romper tests existentes, no romper sensores individuales por viaje, no modificar sensor.py

**Seed data**: Al menos 1 vehículo configurado con 1+ trip activo con datetime ISO incluyendo timezone offset

**Dependency map**: `trip_manager.py` → `emhass_adapter.py` → `coordinator.py` → `sensor.py` → `panel.js`

**Escalate if**: El entity_id real en producción no contiene la substring `emhass_perfil_diferible_`
# Requirements: Fix EMHASS Aggregated Sensor

## Goal

Fix the EMHASS Aggregated Sensor integration to correctly display sensor values, properly publish trip data to EMHASS, and ensure the panel displays correctly with real-time updates.

---

## Acceptance Criteria

### AC 1: Datetime Offset Error Fixed

**Statement:**
All datetime calculations must use timezone-aware datetimes consistently to prevent `can't subtract offset-naive and offset-aware datetimes` errors.

**Verification Steps:**

1. Trigger a new trip creation in a test environment
2. Verify the trip syncs to EMHASS without errors in logs
3. Check that no `offset-naive` or `offset-aware` error messages appear
4. Confirm the trip's `emhass_index` is correctly assigned (not -1)

**Technical Requirement:**

- File: `custom_components/ev_trip_planner/emhass_adapter.py`
- Line ~334: Replace `datetime.now()` with `datetime.now(timezone.utc)`
- Ensure all datetime comparisons use consistent timezone awareness

**Acceptance Test:**

```python
# Before (fails):
now = datetime.now()  # offset-naive
deadline_dt = deadline  # offset-aware
hours = (deadline_dt - now).total_seconds() / 3600  # CRASH

# After (works):
from datetime import datetime, timezone
now = datetime.now(timezone.utc)  # offset-aware
deadline_dt = deadline  # offset-aware
hours = (deadline_dt - now).total_seconds() / 3600  # OK
```

---

### AC 2: Entity ID Search Pattern Updated

**Statement:**
The panel must correctly find EMHASS sensors by matching the actual entity ID pattern.

**Verification Steps:**

1. Verify sensor entity ID format: `sensor.trip_planner_{name}_emhass_perfil_diferible_{name}`
2. Check panel.js searches for correct pattern
3. Confirm panel can locate sensor and display values
4. Verify no "EMHASS sensor not available" message when sensors exist

**Technical Requirement:**

- File: `custom_components/ev_trip_planner/frontend/panel.js`
- Line ~883-886: Change search pattern from:
  ```javascript
  if (entityId.startsWith('sensor.emhass_perfil_diferible_')) {
  ```
  To:
  ```javascript
  if (entityId.startsWith('sensor.trip_planner_') && entityId.includes('emhass_perfil_diferible')) {
  ```

**Acceptance Test:**

- Given a sensor named `sensor.trip_planner_chispitas_emhass_perfil_diferible_chispitas`
- When panel.js scans for EMHASS sensors
- Then the sensor must be found and its data displayed

---

### AC 3: Template Attribute Names - VERIFIED CORRECT

**Statement:**
The Jinja2 template uses correct attribute names that match the actual sensor attributes. This was verified and confirmed to be working correctly.

**Verification:**

The aggregated sensor (`EmhassDeferrableLoadSensor`) correctly exposes:
```yaml
def_total_hours_array:
  - 1.94
p_deferrable_nom_array:
  - 3600
def_start_timestep_array:
  - 0
def_end_timestep_array:
  - 2
number_of_deferrable_loads: 1
```

**Current template (CORRECT):**
```javascript
// panel.js lines 914-917
def_total_hours_array: {{ state_attr('${emhassSensorEntityId}', 'def_total_hours_array') | default([], true) }}
p_deferrable_nom_array: {{ state_attr('${emhassSensorEntityId}', 'p_deferrable_nom_array') | default([], true) }}
def_start_timestep_array: {{ state_attr('${emhassSensorEntityId}', 'def_start_timestep_array') | default([], true) }}
def_end_timestep_array: {{ state_attr('${emhassSensorEntityId}', 'def_end_timestep_array') | default([], true) }}
```

**Note:** The initial concern about `_array` suffix was a false positive due to Home Assistant's observability UI. The attributes are correctly defined as arrays in both the sensor code and template. No changes needed for attribute names.

---

### AC 4: def_total_hours as Integer

**Statement:**
The `def_total_hours` value must be an integer, not a float, per EMHASS requirements.

**Verification Steps:**

1. Create a trip with duration that results in fractional hours (e.g., 1.94 hours)
2. Check the sensor attribute shows integer value (e.g., `2` not `1.94`)
3. Verify EMHASS accepts the value without error
4. Confirm no rounding issues cause incorrect values

**Technical Requirement:**

- File: `custom_components/ev_trip_planner/emhass_adapter.py`
- Line ~379: Change:
  ```python
  "def_total_hours": round(total_hours, 2),  # Returns 1.94 (float)
  ```
  To:
  ```python
  "def_total_hours": int(total_hours),  # Returns 1 (integer)
  ```

- File: `custom_components/ev_trip_planner/emhass_adapter.py`
- Line ~545: Same change in `_populate_per_trip_cache_entry`

**Acceptance Test:**

```python
# Before (fails EMHASS validation):
"def_total_hours": 1.94  # float

# After (EMHASS accepts):
"def_total_hours": 1     # int
```

---

### AC 5: Second Trip Updates Aggregated Sensor

**Statement:**
When a new trip is created, the aggregated EMHASS sensor must include all trips in its calculations.

**Verification Steps:**

1. Create first trip and verify it appears in aggregated sensor
2. Create second trip
3. Verify both trips appear in `punctual_trips` list
4. Confirm aggregated sensor attributes include data from both trips
5. Check that `power_profile_watts` array contains profiles from all trips

**Technical Requirement:**

- File: `custom_components/ev_trip_planner/sensor.py`
- Ensure `EmhassDeferrableLoadSensor.async_update()` iterates through ALL trips
- Verify aggregation logic combines:
  - `p_deferrable_matrix`: Combined load profiles
  - `def_total_hours_array`: All trip durations
  - `def_start_timestep_array`: All trip start times
  - `def_end_timestep_array`: All trip end times

**Acceptance Test:**

- Given 2 active trips with different durations
- When aggregated sensor updates
- Then `def_total_hours_array` contains 2 values
- And `p_deferrable_matrix` contains 2 load profiles

---

### AC 6: emhass_index Correctly Assigned

**Statement:**
New trips must be assigned a valid `emhass_index` (not -1) when published to EMHASS.

**Verification Steps:**

1. Create a new trip
2. Check `sensor.trip_planner_{name}_emhass_index` shows non-negative value
3. Verify the value corresponds to the trip's position in EMHASS queue
4. Confirm trip data appears in EMHASS with correct index

**Technical Requirement:**

- File: `custom_components/ev_trip_planner/emhass_adapter.py`
- Ensure trip publishing returns valid index
- Fix any early returns or error paths that set index to -1
- Root cause: The datetime error in AC 1 prevents proper index assignment

**Acceptance Test:**

```python
# Before (broken):
emhass_index: -1  # Indicates failure

# After (works):
emhass_index: 0   # Valid index
```

---

### AC 7: def_start_timestep Calculation Correct

**Statement:**
The `def_start_timestep` must correctly calculate the start time for each trip based on its position relative to other trips and the current time.

**Verification Steps:**

1. Create multiple trips with different start times
2. Verify each trip's `def_start_timestep` reflects its actual start window
3. Confirm calculations account for:
   - Current time
   - Charging window start
   - Trip position in sequence
   - Previous trip's end time

**Technical Requirement:**

- File: `custom_components/ev_trip_planner/emhass_adapter.py`
- Lines ~364-370: Review charging window calculation logic
- Ensure each trip's window is calculated independently based on:
  - `charging_windows[i].get("inicio_ventana")` for that specific trip
  - Proper offset from current time

**Acceptance Test:**

- Given trip A starts in 5 hours and trip B starts in 10 hours
- When calculating def_start_timestep
- Then trip A gets 5 and trip B gets 10 (not both 0 or both based on first trip)

---

### AC 5: Route Correct (Panel CSS Loading)

**Statement:**
The panel.js must use the correct route for CSS files to match the registration in services.py.

**Current State:**
- **Services registers:** `/ev-trip-planner/panel.css` (with hyphens)
  ```python
  # services.py line 1269
  StaticPathConfig("/ev-trip-planner/panel.css", ...)
  ```
- **Panel.js requests:** `/ev_trip_planner/panel.css` (with underscores)
  ```javascript
  // panel.js line 723
  <link rel="stylesheet" href="/ev_trip_planner/panel.css?v=${Date.now()}">
  ```

**Impact:**
- CSS returns 404 when accessed directly
- Browser console shows repeated "Refused to apply style" errors
- Panel styling is broken/incomplete

**Technical Requirement:**

- File: `custom_components/ev_trip_planner/frontend/panel.js`
- Line 723: Change from:
  ```javascript
  <link rel="stylesheet" href="/ev_trip_planner/panel.css?v=${Date.now()}">
  ```
  To:
  ```javascript
  <link rel="stylesheet" href="/ev-trip-planner/panel.css?v=${Date.now()}">
  ```

**Acceptance Test:**

- Navigate to `http://192.168.1.100:8123/ev-trip-planner/panel.css` → Should load CSS (not 404)
- Panel renders with correct styling
- No "Refused to apply style" errors in browser console

---

### AC 6: Second Trip Updates Aggregated Sensor

**Statement:**
When a new trip is created, the aggregated EMHASS sensor must include all trips in its calculations.

**Root Cause:**
The datetime error in AC 1 prevents new trips from being published to EMHASS, so they never appear in `_cached_per_trip_params`.

**Verification Steps:**

1. Create first trip and verify it appears in aggregated sensor
2. Fix datetime error (AC 1)
3. Create second trip
4. Verify both trips appear in `punctual_trips` list
5. Confirm aggregated sensor attributes include data from both trips
6. Check that `def_total_hours_array` contains 2 values

**Acceptance Test:**

- Given 2 active trips with different durations
- When aggregated sensor updates
- Then `def_total_hours_array` contains 2 values
- And `number_of_deferrable_loads` equals 2

---

### AC 7: emhass_index Correctly Assigned

**Statement:**
New trips must be assigned a valid `emhass_index` (not -1) when published to EMHASS.

**Verification Steps:**

1. Create a new trip
2. Check `sensor.trip_planner_{name}_emhass_index` shows non-negative value
3. Verify the value corresponds to the trip's position in EMHASS queue
4. Confirm trip data appears in EMHASS with correct index

**Root Cause:**
The datetime error in AC 1 prevents proper index assignment. The trip fails before `emhass_index` is calculated.

**Acceptance Test:**

```python
# Before (broken):
emhass_index: -1  # Indicates failure

# After (works):
emhass_index: 0   # Valid index
```

---

### AC 8: EMHASS Section Always Visible

**Statement:**
The EMHASS configuration section must ALWAYS be visible, regardless of whether trips exist or not. The "sensor not available" warning message should be removed entirely.

**Current Behavior:**
- Message "⚠️ EMHASS sensor not available. Make sure you have active trips..." appears
- Message persists even when trips are created with EMHASS data
- Section may be hidden depending on sensor availability logic

**Technical Requirement:**

- File: `custom_components/ev_trip_planner/frontend/panel.js`
- Lines ~905-945: Remove availability check and warning message

**Solution:**
- Remove the `emhassAvailable` check that shows warning message
- Always display the EMHASS configuration section
- Jinja2 template will show default values when data is empty:
  ```
  number_of_deferrable_loads: 0
  def_total_hours: []
  P_deferrable_nom: []
  def_start_timestep: []
  def_end_timestep: []
  P_deferrable: []
  ```

**Acceptance Test:**

- No warning message "EMHASS sensor not available" under any circumstances
- EMHASS configuration section always visible
- With active trips: Shows actual EMHASS data
- With no trips: Shows empty/zero values from Jinja2 `default()`
- Panel loads immediately without waiting for sensor availability check

---

### AC 9: Panel Reactivity Fixed

**Statement:**
The panel must maintain reactivity and update its display when sensor data changes. Content must not disappear after being viewed for extended periods.

**Verification Steps:**

1. Open panel and observe content
2. Create/modify a trip while panel is open
3. Verify panel updates without requiring page reload
4. Keep panel open for extended period (5+ minutes)
5. Confirm content remains visible and functional

**Technical Requirement:**

- File: `custom_components/ev_trip_planner/frontend/panel.js`
- Ensure Lit component properly calls `requestUpdate()` after state changes
- Verify property decorators trigger reactivity
- Check that coordinator updates properly notify components

**Acceptance Test:**

- Panel content visible at T=0 minutes
- Panel content still visible at T=5 minutes
- Panel content still visible at T=10 minutes
- No JavaScript errors in console during extended view

---

### AC 10: Jinja2 Template Keys Corrected

**Statement:**
The Jinja2 template must use EMHASS-compatible keys (without `_array` suffix) while reading from the correct sensor attributes (with `_array` suffix).

**Current Template (INCORRECT):**
```jinja2
def_total_hours_array: {{ state_attr('${emhassSensorEntityId}', 'def_total_hours_array') | default([], true) }}
p_deferrable_nom_array: {{ state_attr('${emhassSensorEntityId}', 'p_deferrable_nom_array') | default([], true) }}
def_start_timestep_array: {{ state_attr('${emhassSensorEntityId}', 'def_start_timestep_array') | default([], true) }}
def_end_timestep_array: {{ state_attr('${emhassSensorEntityId}', 'def_end_timestep_array') | default([], true) }}
p_deferrable_matrix: {{ state_attr('${emhassSensorEntityId}', 'p_deferrable_matrix') | default([], true) }}
```

**Expected Format (from real EMHASS shell command):**
```yaml
emhass_dayahead_optim_with_soc_limit: >
  curl -d '{
    "def_total_hours": [1.5, 2.5],
    "P_deferrable_nom": [3600, 3600],
    "def_start_timestep": [0, 0],
    "def_end_timestep": [168, 168],
    "P_deferrable": [...]
  }' http://192.168.1.100:5000/action/dayahead-optim"
```

**Technical Requirement:**

- File: `custom_components/ev_trip_planner/frontend/panel.js`
- Lines ~914-918: Update template to use correct keys

**Corrected Template:**
```jinja2
{# Keys (left of :) without _array, attribute (2nd param) with _array #}
def_total_hours: {{ state_attr('${emhassSensorEntityId}', 'def_total_hours_array') | default([], true) }}
P_deferrable_nom: {{ state_attr('${emhassSensorEntityId}', 'p_deferrable_nom_array') | default([], true) }}
def_start_timestep: {{ state_attr('${emhassSensorEntityId}', 'def_start_timestep_array') | default([], true) }}
def_end_timestep: {{ state_attr('${emhassSensorEntityId}', 'def_end_timestep_array') | default([], true) }}
P_deferrable: {{ state_attr('${emhassSensorEntityId}', 'p_deferrable_matrix') | default([], true) }}
```

**Note:** The key names must match exactly what EMHASS expects:
- `def_total_hours` (not `def_total_hours_array`)
- `P_deferrable_nom` (not `p_deferrable_nom_array`) - note capital P
- `def_start_timestep` (not `def_start_timestep_array`)
- `def_end_timestep` (not `def_end_timestep_array`)
- `P_deferrable` (not `p_deferrable_matrix`) - note capital P

**Acceptance Test:**

- Jinja2 template generates correct keys for EMHASS
- EMHASS shell command receives: `def_total_hours`, `P_deferrable_nom`, etc.
- EMHASS optimization runs successfully with generated configuration

---

### AC 11: Modal Trip Type Display Correct

**Statement:**
When editing a trip, the trip type select must show the correct current selection (puntual or recurrente).

**Current Behavior:**
- Editing a puntual trip shows "recurrente" selected
- This is confusing and risks accidentally changing trip type

**Technical Requirement:**

- File: `custom_components/ev_trip_planner/frontend/panel.js`
- Line ~1637: Update trip type detection logic

**Current Code (INCORRECT):**
```javascript
this._formType = trip.type === 'puntual' ? 'puntual' : 'recurrente';
```

**Corrected Code:**
```javascript
// Check all possible trip type fields
if (trip.tipo === 'puntual' || trip.type === 'puntual' || trip.recurring === false) {
  this._formType = 'puntual';
} else {
  this._formType = 'recurrente';
}
```

**Acceptance Test:**

- Create a puntual trip
- Click edit on the puntual trip
- Modal opens with "puntual" selected in the type dropdown
- Create a recurrente trip
- Click edit on the recurrente trip
- Modal opens with "recurrente" selected in the type dropdown

---

## Non-Functional Requirements

### Performance

- EMHASS sensor updates must complete within 2 seconds
- Panel must respond to data changes within 500ms
- No memory leaks in Lit component during extended use

### Compatibility

- Must work with Home Assistant 2024.x and later
- Must work with EMHASS latest stable version
- Must not break existing individual EMHASS sensors

### Error Handling

- All datetime operations must handle timezone awareness
- Missing sensor attributes must default to safe values (0, [], null)
- Failed EMHASS sync must log error but not crash the component

### Logging

- All EMHASS sync operations must be logged at appropriate level
- Errors must include trip_id and relevant context
- Success messages should be at DEBUG level to reduce log noise

---

## Priority Matrix

| AC | Priority | Blocks | Severity |
|----|----------|--------|----------|
| 1 (datetime) | P0 | 10, 5, 6 | Critical |
| 2 (entity_id) | P0 | 7 | Critical |
| 3 (def_total_hours int) | P1 | EMHASS | High |
| 4 (panel.css route) | P1 | UX | Medium |
| 5 (second trip) | P1 | 10 | High |
| 6 (emhass_index) | P1 | 10 | High |
| 7 (EMHASS message) | P2 | - | Medium |
| 8 (panel reactivity) | P2 | - | Medium |
| 9 (template keys) | P0 | EMHASS | Critical |
| 10 (modal trip type) | P2 | UX | Medium |

---

## Dependencies

- AC 1 (datetime fix) is the root cause for AC 5 (second trip), AC 6 (emhass_index), and AC 9 (template keys - data must exist)
- AC 2 (entity_id pattern) must be fixed for AC 7 (EMHASS message) to work correctly
- AC 3 (def_total_hours int) and AC 9 (template keys) both affect EMHASS data format
- AC 4 (panel.css route) is independent but affects UX significantly
- AC 9 (template keys) depends on AC 1 (datetime fix) so there's data to display
- AC 10 (modal trip type) is independent

---

## Out of Scope

- Changes to EMHASS core functionality
- Modifications to Home Assistant core
- New features for EMHASS integration
- Changes to individual trip sensor logic (only aggregation affected)
