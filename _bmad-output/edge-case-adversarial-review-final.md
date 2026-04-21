# Adversarial Review: Edge Cases — Real Reachability Analysis

## Metodología

Cada edge case fue analizado trazando el flujo completo de ejecución desde el entry point hasta el punto potencial de fallo, identificando si existen validaciones defensivas en camino que hagan el edge case **inalcanzable** (código muerto) o **realmente alcanzable**.

---

## EC-001: Timer leak en unload — 🔴 REALMENTE ALCANZABLE

**Archivo:** [`__init__.py:168`](custom_components/ev_trip_planner/__init__.py:168)
**Descripción:** `async_track_time_interval` nunca se cancela en `async_unload_entry`

### Trazado de ejecución

```
async_unload_entry (__init__.py:177)
  → async_unload_entry_cleanup (services.py:1389)
    → hass.config_entries.async_unload_platforms (services.py:1454)
    → NO hay llamada a timer.cancel()
    → async_remove_entry_cleanup (services.py:1486)
      → NO hay llamada a timer.cancel()
```

### Validaciones existentes que PODRÍAN prevenir el leak:
- **Ninguna.** El timer se registra en `async_setup_entry` sin guardar referencia:
  ```python
  async_track_time_interval(hass, functools.partial(_hourly_refresh_callback, runtime_data=entry.runtime_data), timedelta(hours=1))
  ```
- No se guarda el retorno en ninguna variable.
- No hay cleanup en `async_unload_entry`.
- No hay cleanup en `async_remove_entry`.

### ¿Es código muerto?
**NO.** El timer se crea y se pierde referencia. Se ejecutará cada hora para siempre, incluso después de unload/remove. Cada ejecución llamará a `_hourly_refresh_callback` que accederá a `entry.runtime_data.trip_manager.publish_deferrable_loads()`.

### Consecuencia real
- Memory leak progresivo (callbacks acumulándose)
- `publish_deferrable_loads()` se ejecuta después de unload → accede a trip_manager con trips eliminados
- Posible crash si `entry.runtime_data` es None tras remove

### Reproducción exacta
1. Crear integración EV Trip Planner
2. Esperar 1 hora → timer dispara, `publish_deferrable_loads()` se ejecuta
3. Eliminar la integración (unload + remove)
4. Esperar 1 hora más → timer dispara de nuevo, accede a `entry.runtime_data.trip_manager` que puede ser None o tener trips eliminados

---

## EC-002: datetime.now() naive en trip_manager.py:206 — 🔴 REALMENTE ALCANZABLE

**Archivo:** [`trip_manager.py:206`](custom_components/ev_trip_planner/trip_manager.py:206)
**Descripción:** `datetime.now()` sin timezone

### Trazado de ejecución
```
publish_deferrable_loads (trip_manager.py:169)
  → for trip in trips (line 183)
    → calculate_next_recurring_datetime(day_js_format, time_str, datetime.now()) (line 205-207)
```

### ¿Existe validación en `calculate_next_recurring_datetime`?
En [`calculations.py:754`](custom_components/ev_trip_planner/calculations.py:754):
```python
def calculate_next_recurring_datetime(day, time_str, reference_dt=None):
    if reference_dt is None:
        reference_dt = datetime.now()  # TAMBIÉN naive aquí
```

La función acepta cualquier datetime (naive o aware) y lo usa para cálculos. No convierte a aware.

### ¿Es código muerto?
**NO.** `datetime.now()` se pasa directamente como `reference_dt` a `calculate_next_recurring_datetime`. Dentro de esa función:
- Línea 784: `candidate = reference_dt.replace(hour=hour, ...)` → produce datetime naive
- Línea 794: `if days_ahead == 0 and candidate < reference_dt:` → comparación naive vs naive, funciona
- Pero `next_occurrence.isoformat()` en línea 221 de trip_manager produce string sin timezone

### Consecuencia real
- `trip["datetime"] = next_occurrence.isoformat()` guarda datetime SIN timezone
- Cuando se lee después, se mezcla con datetimes aware de otras fuentes
- **PERO**: en la práctica, todos los datetimes en el sistema son naive, así que las comparaciones funcionan
- **El problema real** es si el usuario cambia zona horaria de HA → los cálculos se vuelven incorrectos

### Reproducción exacta
1. Crear trip recurrente con dia_semana="martes" y hora="08:00"
2. Esperar al hourly refresh
3. `calculate_next_recurring_datetime` retorna datetime naive (sin tzinfo)
4. `trip["datetime"]` se actualiza con valor naive
5. Si HA está en UTC, funciona correctamente
6. Si HA está en zona con DST → el datetime naive puede ser ambiguo

---

## EC-003: In-place mutation de trip dict — 🔴 REALMENTE ALCANZABLE

**Archivo:** [`trip_manager.py:221`](custom_components/ev_trip_planner/trip_manager.py:221)
**Descripción:** `trip["datetime"] = next_occurrence.isoformat()` muta el dict original

### Trazado de ejecución
```
publish_deferrable_loads (trip_manager.py:169)
  → trips = await self._get_all_active_trips() (line 178)
    → self._recurring_trips.values() → LISTA DE DICTS ORIGINALES
  → for trip in trips: trip["datetime"] = ... (line 221)
    → MUTA el dict original en self._recurring_trips
```

### ¿Existe validación que prevenga esto?
**NO.** `_get_all_active_trips()` retorna referencias a los dicts originales en `self._recurring_trips`:
```python
for trip in self._recurring_trips.values():
    if trip.get("activo", True):
        all_trips.append(trip)  # REFERENCIA DIRECTA, NO COPIA
```

### ¿Es código muerto?
**NO.** Se muta el dict original en memoria. Los cambios persisten hasta el siguiente save/load.

### Consecuencia real
- `trip["datetime"]` se sobrescribe cada hora con el próximo occurrence
- Si hay otro proceso leyendo los trips simultáneamente (coordinator refresh), ve datos inconsistentes
- **PERO**: el código ya depende de este comportamiento como parte del diseño T3.2
- El "bug" es que no se hace `trip.copy()` antes de mutar

### Reproducción exacta
1. Crear trip recurrente
2. Llamar `publish_deferrable_loads()`
3. Verificar que `trip_manager._recurring_trips[trip_id]["datetime"]` cambió
4. Leer el YAML storage → el datetime fue sobrescrito

---

## EC-004: Division by zero charging_power_kw=0 — 🟡 ALCANZABLE PERO CON GUARD

**Archivo:** [`emhass_adapter.py:1193`](custom_components/ev_trip_planner/emhass_adapter.py:971)
**Descripción:** `charging_power_kw=0` en `calculate_deferrable_parameters`

### Trazado de ejecución
```
publish_deferrable_loads (emhass_adapter.py:973)
  → calc_deferrable_parameters(trip, charging_power_kw) (line 971)
```

### ¿Qué hace `calc_deferrable_parameters`?
En [`calculations.py:1172`](custom_components/ev_trip_planner/calculations.py:1172):
```python
def calculate_deferrable_parameters(trip, charging_power_kw):
    ...
    if charging_power_kw > 0:
        horas_carga = energia_final / charging_power_kw
    else:
        horas_carga = 0
```

### ¿Es código muerto?
**PARCIALMENTE.** La función `calculate_deferrable_parameters` SÍ tiene guard:
```python
if charging_power_kw > 0:
    horas_carga = energia_final / charging_power_kw
else:
    horas_carga = 0
```

**PERO**: el guard está en `calculate_deferrable_parameters`, no en `calculate_energy_needed` que es llamada por `determine_charging_need`:
```python
# calculations.py:333
if charging_power_kw > 0:
    horas_carga = energia_final / charging_power_kw
else:
    horas_carga = 0
```

### Veredicto: **NO ES EDGE CASE** — ya tiene guard en ambos lugares

---

## EC-005: Division by zero battery_capacity_kwh=0 — 🟡 ALCANZABLE PERO CON GUARD

**Archivo:** [`calculations.py:157`](custom_components/ev_trip_planner/calculations.py:157)
**Descripción:** `battery_capacity_kwh=0` en `calculate_charging_rate`

### Análisis del código
```python
def calculate_charging_rate(charging_power_kw, battery_capacity_kwh=50.0):
    if battery_capacity_kwh <= 0:
        return 0.0  # GUARD EXISTE
    return (charging_power_kw / battery_capacity_kwh) * 100
```

### ¿Es código muerto?
**NO es edge case alcanzable con crash.** El guard `if battery_capacity_kwh <= 0: return 0.0` previene la división por cero.

### Veredicto: **CÓDIGO MUERTO** — el guard existe y es efectivo

---

## EC-006: Floating point drift en SOC propagation — 🟡 ALCANZABLE PERO BAJO IMPACTO

**Archivo:** [`emhass_adapter.py:871`](custom_components/ev_trip_planner/emhass_adapter.py:871)
**Descripción:** Acumulación de error floating point en `projected_soc`

### Trazado de ejecución
```
async_publish_all_deferrable_loads (emhass_adapter.py:786)
  → projected_soc = soc_current (line 827)
  → for trip in trips:
      projected_soc = projected_soc + soc_ganado - soc_consumido (line 871)
      projected_soc = max(0.0, min(100.0, projected_soc)) (line 873)
```

### ¿Existe guard?
Sí, clamping a [0, 100] en línea 873. Pero NO hay `round()`.

### ¿Es código muerto?
**NO es código muerto.** El drift existe pero es mínimo: ~1e-14 por operación floating point. Después de 50 trips, el drift máximo es ~5e-13, completamente insignificante.

### Veredicto: **REAL PERO SIN IMPACTO PRÁCTICO** — el drift es ~0.000000000001% después de 50 trips

---

## EC-007: SOC puede exceder 100% o bajar de 0% — 🟡 ALCANZABLE PERO CON GUARD

**Archivo:** [`calculations.py:176`](custom_components/ev_trip_planner/calculations.py:176)
**Descripción:** `calculate_soc_target` sin clamp

### Análisis
```python
def calculate_soc_target(trip, battery_capacity_kwh, ...):
    ...
    soc_objetivo_base = energia_soc + soc_buffer_percent
    return soc_objetivo_base  # SIN CLAMP
```

### ¿Es alcanzable?
Si un trip necesita 90% SOC y el buffer es 5%, retorna 95%. OK.
Si un trip necesita 98% SOC y el buffer es 5%, retorna 103%. **SIN CLAMP.**

### ¿Dónde se usa?
En `calculate_deficit_propagation` (calculations.py:688):
```python
soc_objetivo = calculate_soc_target(trip, battery_capacity_kwh)
```
Y luego en línea 733:
```python
"soc_objetivo": round(soc_objetivo_ajustado, 2),
```

### En `determine_charging_need` (calculations.py:248-254):
```python
energia_info = calculate_energy_needed(trip, battery_capacity_kwh, soc_current, charging_power_kw, ...)
kwh_needed = energia_info["energia_necesaria_kwh"]
needs_charging = kwh_needed > 0
```

`calculate_energy_needed` (calculations.py:325-328):
```python
energia_necesaria = max(0.0, energia_objetivo - energia_actual)
energia_necesaria = min(energia_necesaria, battery_capacity_kwh)  # CLAMP AQUÍ
```

### Veredicto: **PARCIALMENTE PROTEGIDO** — `soc_target` puede retornar >100 pero `calculate_energy_needed` clampa `energia_necesaria` a `battery_capacity_kwh`. El soc_objetivo >100 solo afecta los cálculos de deficit propagation, que terminan en `kwh_necesarios = max(0.0, ...)`.

---

## EC-008: soc_target=None — 🟡 ALCANZABLE PERO CON GUARD

**Archivo:** [`emhass_adapter.py:949`](custom_components/ev_trip_planner/emhass_adapter.py:971)
**Descripción:** `calculate_deferrable_parameters` sin guard en soc_target

### Análisis
`calculate_deferrable_parameters` (calculations.py:1172) NO usa `soc_target`. Usa:
```python
energia_info = calculate_energy_needed(trip, battery_capacity_kwh, soc_current, charging_power_kw, ...)
```
Y `soc_current` viene de fuera, no de `soc_target`.

### ¿Es código muerto?
**SÍ, PARCIALMENTE.** `calculate_deferrable_parameters` no depende de `soc_target`. El soc_target se calcula en `_populate_per_trip_cache_entry` pero no se pasa a `calculate_deferrable_parameters`.

### Veredicto: **CÓDIGO MUERTO** — `calculate_deferrable_parameters` no usa soc_target

---

## EC-009: trip.get('id') retorna None — 🟡 ALCANZABLE PERO CON GUARD

**Archivo:** [`emhass_adapter.py:326`](custom_components/ev_trip_planner/emhass_adapter.py:326)
**Descripción:** `trip.get('id')` puede ser None

### Trazado de ejecución
```
async_publish_deferrable_load (emhass_adapter.py:326)
  → trip_id = trip.get("id") (line 350)
```

### ¿Qué pasa si trip_id es None?
En línea 352:
```python
if trip_id in self._index_map:  # None in dict → False, no crash
```

En línea 360:
```python
if trip_id not in self._index_map:
    await self.async_assign_index_to_trip(trip_id)  # async_assign_index_to_trip(None)
```

### ¿Qué hace `async_assign_index_to_trip(None)`?
En línea 252:
```python
async def async_assign_index_to_trip(self, trip_id: str) -> Optional[int]:
    if not self._available_indices:
        return None
    idx = self._available_indices.pop(0)
    self._index_map[trip_id] = idx  # None como key → OK en Python
    return idx
```

### ¿Es código muerto?
**NO.** `None` como key de dict es válido en Python. No crash.

### ¿Dónde se usa trip_id después?
En línea 365:
```python
self._published_trips.add(trip_id)  # None en set → OK
```

En línea 371:
```python
params = self.calculate_deferrable_parameters(trip, charging_power_kw)
```

### Veredicto: **ALCANZABLE PERO NO CRASH** — Python permite None como key de dict. El comportamiento es "correcto" en el sentido de que no crash, pero los datos son inconsistentes.

---

## EC-010: Race condition en get_available_indices — 🟡 ALCANZABLE PERO BAJA PROBABILIDAD

**Archivo:** [`emhass_adapter.py:926`](custom_components/ev_trip_planner/emhass_adapter.py:926)
**Descripción:** Dos publicaciones simultáneas pueden asignar mismo índice

### Análisis
```python
def get_available_indices(self):
    # Limpia expired...
    return self._available_indices  # RETORNA REFERENCIA DIRECTA
```

Si dos corutinas llaman a `get_available_indices()` simultáneamente, ambas reciben la MISMA lista. Si ambas hacen `pop(0)`, hay race condition.

### ¿Existe lock?
**NO.** No hay `asyncio.Lock` en `EMHASSAdapter`.

### ¿Es alcanzable en la práctica?
`async_publish_all_deferrable_loads` se llama desde:
1. `publish_deferrable_loads` (trip_manager.py:248) — single-threaded en HA event loop
2. Coordinator refresh — single-threaded en HA event loop

En HA, todo es single-threaded event-loop. Las "concurrency" son corutinas que se alternan en await points.

### Veredicto: **TEÓRICAMENTE ALCANZABLE PERO PRÁCTICAMENTE IMPOSIBLE** — HA event loop previene race conditions reales

---

## EC-011: Timezone deadline naive — 🟡 ALCANZABLE PERO CON GUARD

**Archivo:** [`emhass_adapter.py:449`](custom_components/ev_trip_planner/emhass_adapter.py:449)
**Descripción:** `_calculate_deadline_from_trip` puede retornar datetime naive

### Análisis
```python
def _calculate_deadline_from_trip(self, trip):
    deadline_str = trip.get("datetime")
    if deadline_str:
        try:
            return datetime.fromisoformat(deadline_str)  # SI deadline_str tiene tz → aware
        ...
```

Si `deadline_str` es "2024-01-15T08:00:00" (sin tz) → naive.
Si `deadline_str` es "2024-01-15T08:00:00+00:00" → aware.

### ¿Existe guard?
En línea 496-503:
```python
try:
    from .calculations import calculate_next_recurring_datetime, calculate_day_index
    # ...
    deadline_dt = calculate_next_recurring_datetime(...)
```

`calculate_next_recurring_datetime` retorna datetime naive (línea 798 de calculations.py):
```python
return candidate + timedelta(days=days_ahead)  # candidate es naive
```

### ¿Dónde se usa deadline_dt?
En línea 589 de `_populate_per_trip_cache_entry`:
```python
hours_available = (deadline_dt - now).total_seconds() / 3600
```
`now` es `datetime.now(timezone.utc)` (línea 542) → aware.

Si `deadline_dt` es naive y `now` es aware → **TypeError en resta**.

### ¿Es código muerto?
**NO.** Si `deadline_dt` es naive y `now` es aware, Python 3 lanza `TypeError: can't subtract naive and aware datetimes`.

### Veredicto: **REALMENTE ALCANZABLE** — si un trip tiene datetime sin timezone, el cálculo de `hours_available` crasha.

---

## EC-012: day=7 inválido — 🟡 ALCANZABLE PERO CON GUARD

**Archivo:** [`trip_manager.py:251`](custom_components/ev_trip_planner/trip_manager.py:200)
**Descripción:** Trip con day=7 (fuera de rango 0-6)

### Análisis
```python
day_index = calculate_day_index(day_name)  # trip_manager.py:200
```

`calculate_day_index` en [`calculations.py:65`](custom_components/ev_trip_planner/calculations.py:65):
```python
def calculate_day_index(day_name):
    day_lower = day_name.lower().strip()
    if day_lower.isdigit():
        day_index = int(day_lower)
        if 0 <= day_index < len(DAYS_OF_WEEK):  # 0 <= day < 7
            return day_index
        return 0  # Monday on invalid index ← GUARD
```

### Veredicto: **CÓDIGO MUERTO** — `calculate_day_index` retorna 0 (lunes) para cualquier valor fuera de rango

---

## EC-013: Memory leak en per_trip_params — 🟡 ALCANZABLE PERO CON GUARD PARCIAL

**Archivo:** [`emhass_adapter.py:654`](custom_components/ev_trip_planner/emhass_adapter.py:654)
**Descripción:** `per_trip_emhass_params` crece indefinidamente

### Análisis
`async_remove_deferrable_load` (emhass_adapter.py:654):
```python
async def async_remove_deferrable_load(self, trip_id):
    try:
        if trip_id in self._index_map:
            idx = self._index_map.pop(trip_id)
            self._available_indices.append(idx)
            self._available_indices.sort()
        # NOTE: self._cached_per_trip_params.pop(trip_id, None)  ← NO EXISTE
```

**NO hay cleanup de `_cached_per_trip_params` en `async_remove_deferrable_load`.**

### ¿Existe cleanup en otro lado?
En `async_publish_all_deferrable_loads` (emhass_adapter.py:749-752):
```python
current_trip_ids = {trip.get("id") for trip in trips if trip.get("id")}
stale_ids = set(self._cached_per_trip_params.keys()) - current_trip_ids
for stale_id in stale_ids:
    del self._cached_per_trip_params[stale_id]
```

Este cleanup solo se ejecuta cuando se republiquen trips. Si se elimina un trip individual (no todos), el cache stale persiste.

### Veredicto: **REALMENTE ALCANZABLE** — eliminar un trip individual no limpia su entry en `_cached_per_trip_params`

---

## EC-014: start_time > end_time — 🟡 ALCANZABLE PERO CON GUARD

**Archivo:** [`calculations.py:352`](custom_components/ev_trip_planner/calculations.py:352)
**Descripción:** `calculate_charging_window_pure` no maneja start > end

### Análisis
```python
def calculate_charging_window_pure(...):
    ...
    window_hours = (deadline - now).total_seconds() / 3600
    if window_hours <= 0:
        return {"start_timestep": 0, "end_timestep": 0, "ventana_horas": 0}  # GUARD
```

### Veredicto: **CÓDIGO MUERTO** — el guard `if window_hours <= 0` previene valores negativos

---

## EC-015: Race condition en delete_all_trips — 🟡 ALCANZABLE PERO BAJA PROBABILIDAD

**Archivo:** [`trip_manager.py:775`](custom_components/ev_trip_planner/trip_manager.py:775)
**Descripción:** `async_delete_all_trips` sin lock

### Análisis
En HA event loop, todo es single-threaded. Las operaciones concurrentes solo ocurren en await points.

`async_delete_all_trips`:
```python
async def async_delete_all_trips(self):
    self._recurring_trips.clear()
    self._punctual_trips.clear()
    await self.async_save_trips()
```

Si `publish_deferrable_loads` está en medio de `for trip in trips` cuando se llama `async_delete_all_trips`:
- `trips` es una lista ya materializada (línea 178: `trips = await self._get_all_active_trips()`)
- `self._recurring_trips.clear()` no afecta la lista `trips` ya creada

### Veredicto: **PARCIALMENTE PROTEGIDO** — la lista `trips` ya está materializada antes del clear. No hay corrupción.

---

## EC-016: time_str format inválido — 🟡 ALCANZABLE PERO CON GUARD

**Archivo:** [`calculations.py:754`](custom_components/ev_trip_planner/calculations.py:778)
**Descripción:** `calculate_next_recurring_datetime` sin validación de time_str

### Análisis
```python
def calculate_next_recurring_datetime(day, time_str, reference_dt=None):
    if day is None or time_str is None:
        return None  # GUARD 1
    try:
        hour, minute = map(int, time_str.split(':'))  # GUARD 2
    except (ValueError, AttributeError):
        return None
```

### Veredicto: **CÓDIGO MUERTO** — los guards previenen crash

---

## EC-017: _get_current_soc retorna None — 🟡 ALCANZABLE PERO CON GUARD

**Archivo:** [`emhass_adapter.py:2178`](custom_components/ev_trip_planner/emhass_adapter.py:2178)
**Descripción:** `_get_current_soc` puede retornar None

### Análisis
```python
async def _get_current_soc(self):
    soc_sensor = self._entry.data.get("soc_sensor")
    if not soc_sensor:
        return None
    state = self.hass.states.get(soc_sensor)
    if state is None:
        return None  # RETORNA NONE
    return float(state.state)
```

### ¿Dónde se usa?
En `async_publish_all_deferrable_loads` (emhass_adapter.py:772-774):
```python
soc_current = await self._get_current_soc()
if soc_current is None:
    soc_current = 50.0  # GUARD EXISTE
```

En `_populate_per_trip_cache_entry` (emhass_adapter.py:548-551):
```python
decision = determine_charging_need(trip, soc_current, ...)
```

### En `determine_charging_need` (calculations.py:304-305):
```python
if soc_current is None or not isinstance(soc_current, (int, float)):
    soc_current = 0.0  # GUARD EXISTE
```

### Veredicto: **CÓDIGO MUERTO** — guards existen en todos los puntos de uso

---

## EC-018: Publish duplicado — 🟡 ALCANZABLE PERO CON GUARD

**Archivo:** [`emhass_adapter.py:1151`](custom_components/ev_trip_planner/emhass_adapter.py:996)
**Descripción:** `publish_deferrable_loads` sin lock puede publicar dos veces

### Análisis
```python
async def publish_deferrable_loads(self, trips=None, charging_power_kw=None):
    if self._shutting_down:  # GUARD 1
        return True
    ...
    if not trips:  # GUARD 2: clears cache
        self._cached_per_trip_params.clear()
```

`_shutting_down` se setea en `async_unload_entry_cleanup`:
```python
emhass_adapter._shutting_down = True  # ANTES de eliminar trips
```

### ¿Existe guard contra duplicación?
**NO hay lock ni re-entrancy guard.** Pero en HA event loop, dos llamadas concurrentes solo son posibles si ambas tienen await points.

### Veredicto: **TEÓRICAMENTE ALCANZABLE, PRÁCTICAMENTE RARO** — el guard `_shutting_down` previene publish durante deletion, pero no previene duplicación normal

---

## EC-019: Rounding off-by-one — 🟡 ALCANZABLE PERO BAJO IMPACTO

**Archivo:** [`calculations.py:940`](custom_components/ev_trip_planner/calculations.py:940)
**Descripción:** Rounding puede causar off-by-one en horas

### Análisis
```python
def calculate_power_profile_from_trips(...):
    ...
    energia_kwh = trip.get("kwh", 0.0)
    if not energia_kwh:
        distance_km = trip.get("km", 0.0)
        energia_kwh = distance_km * consumption  # PUEDE TENER DECIMALES
```

Luego en `_generate_schedule_from_trips`:
```python
def _generate_schedule_from_trips(self, trips, charging_power_kw):
    ...
    for entry in schedule:
        hours = entry.get("def_total_hours", 0)  # YA CALCULADO CON math.ceil
```

`def_total_hours` viene de `determine_charging_need` (calculations.py:259):
```python
total_hours = int(math.ceil(kwh_needed / charging_power_kw)) if charging_power_kw > 0 else 0
```

`math.ceil` ya redondea hacia arriba, previniendo off-by-one.

### Veredicto: **PARCIALMENTE PROTEGIDO** — `math.ceil` previene off-by-one hacia abajo. El rounding de `energia_final` (calculations.py:339) es a 3 decimales, suficiente para evitar floating point issues.

---

## EC-020: Partial rollback en publish_all — 🔴 REALMENTE ALCANZABLE

**Archivo:** [`emhass_adapter.py:786`](custom_components/ev_trip_planner/emhass_adapter.py:754-756)
**Descripción:** Si trip N falla, trips 1..N-1 ya publicados

### Trazado de ejecución
```python
for trip in trips:  # line 754
    if await self.async_publish_deferrable_load(trip):  # line 755
        success_count += 1
```

Si `async_publish_deferrable_load(trip_N)` retorna False o lanza exception:
- Los trips 0..N-1 YA fueron publicados (índice asignado, cache actualizado)
- No hay rollback automático

### ¿Existe guard?
**NO.** El loop for no tiene try/except ni rollback.

### ¿Es código muerto?
**NO.** Si trip N falla (ej: índice agotado, sensor no disponible), los trips anteriores quedan publicados inconsistentemente.

### Veredicto: **REALMENTE ALCANZABLE** — fallo en trip medio de la lista deja estado inconsistente

---

## Resumen Final: Clasificación Rigurosa

### 🔴 REALMENTE ALCANZABLES (requieren corrección)
| ID | Archivo | Descripción | Severidad |
|----|---------|-------------|-----------|
| EC-001 | `__init__.py:168` | Timer leak en unload | CRITICAL |
| EC-003 | `trip_manager.py:221` | In-place mutation de trip dict | HIGH |
| EC-011 | `emhass_adapter.py:449` | Timezone naive/aware mix crash | HIGH |
| EC-020 | `emhass_adapter.py:754` | Partial rollback en publish loop | HIGH |
| EC-013 | `emhass_adapter.py:654` | Memory leak en per_trip_params | MEDIUM |

### 🟡 ALCANZABLES PERO CON GUARD (no crash)
| ID | ID | Descripción | Severidad |
|----|----|-------------|-----------|
| EC-002 | `trip_manager.py:206` | datetime.now() naive → funciona pero semánticamente incorrecto | MEDIUM |
| EC-006 | `emhass_adapter.py:871` | Floating point drift → ~0 después de 50 trips | LOW |
| EC-007 | `calculations.py:176` | SOC target > 100 → protegido por clamp en downstream | LOW |
| EC-009 | `emhass_adapter.py:326` | trip_id=None → None como key de dict, no crash | LOW |
| EC-010 | `emhass_adapter.py:926` | Race condition en indices → imposible en HA event loop | LOW |
| EC-015 | `trip_manager.py:775` | Race en delete_all → lista ya materializada, no corrupción | LOW |
| EC-018 | `emhass_adapter.py:996` | Publish duplicado → _shutting_down previene en deletion | LOW |

### 🟢 CÓDIGO MUERTO (guards existentes previenen crash)
| ID | Archivo | Guard existente |
|----|---------|-----------------|
| EC-004 | `emhass_adapter.py:971` | `if charging_power_kw > 0: ... else: horas_carga = 0` |
| EC-005 | `calculations.py:157` | `if battery_capacity_kwh <= 0: return 0.0` |
| EC-008 | `emhass_adapter.py:949` | `calculate_deferrable_parameters` no usa soc_target |
| EC-012 | `trip_manager.py:251` | `calculate_day_index` retorna 0 para valores fuera de rango |
| EC-014 | `calculations.py:352` | `if window_hours <= 0: return {...ventana_horas: 0}` |
| EC-016 | `calculations.py:754` | `try/except` en `time_str.split(':')` |
| EC-017 | `emhass_adapter.py:2178` | `if soc_current is None: soc_current = 50.0` |
| EC-019 | `calculations.py:940` | `math.ceil` previene off-by-one |

---

## Descubrimientos Clave del Análisis

### 1. EC-001 (Timer Leak) — El único CRITICAL
El timer de `async_track_time_interval` se crea sin guardar referencia. Es el único edge case que causa memory leak real y potencial crash post-unload.

**Reproducción:** Crear integración → esperar 1 hora → eliminar integración → esperar 1 hora más → crash o comportamiento indefinido.

### 2. EC-011 (Timezone Crash) — Más grave de lo estimado
La mezcla de datetime naive (de `calculate_next_recurring_datetime`) con datetime aware (de `datetime.now(timezone.utc)`) en `_populate_per_trip_cache_entry:589` causa `TypeError: can't subtract naive and aware datetimes`.

**Reproducción:** Crear trip recurrente → esperar hourly refresh → el datetime del trip queda naive → siguiente publish intenta calcular `hours_available = (deadline_dt - now).total_seconds()` → crash.

### 3. EC-003 (In-place Mutation) — Diseño vs Bug
La mutación in-place de trip dicts es parte del diseño T3.2 (rotación de trips). El "fix" sería hacer `trip.copy()` antes de mutar, pero eso significaría que los trips originales nunca se actualizan. El comportamiento actual es INTENCIONAL pero FRÁGIL.

### 4. 7 de 20 edge cases son CÓDIGO MUERTO
Los guards existentes en el código previenen crash en EC-004, EC-005, EC-008, EC-012, EC-014, EC-016, EC-017, EC-019. Agregar más guards solo agregaría código muerto.

### 5. HA Event Loop como protector natural
Varios edge cases de race condition (EC-010, EC-015) son teóricamente posibles pero prácticamente imposibles en Home Assistant debido al modelo de event loop single-threaded.
