---
spec: fix-emhass-aggregated-sensor
phase: research
created: 2026-04-15
---

# Research: Fix EMHASS Aggregated Sensor

## Executive Summary

Se identificaron **7 problemas** en la integración EMHASS que causan fallos en la publicación de viajes, visualización del panel y comunicación con EMHASS. La causa raíz principal es el uso de `datetime.now()` (offset-naive) en 11 puntos del código, que impide la resta de datetimes offset-aware que vienen de ISO strings con timezone. Esto bloquea la publicación de viajes nuevos, causando efecto cascada: `emhass_index = -1`, sensor agregado incompleto, y datos EMHASS faltantes.

## External Research

### Best Practices
- EMHASS REST API espera parámetros `def_total_hours`, `P_deferrable_nom`, `def_start_timestep`, `def_end_timestep` como listas (sin sufijo `_array`) — [EMHASS docs](https://emhass.readthedocs.io/)
- Python `datetime` docs: operaciones entre naive y aware lanzan `TypeError` — es obligatorio usar `datetime.now(timezone.utc)` al interactuar con ISO strings que incluyen offset

### Prior Art
- El propio proyecto ya usa `_array` como sufijo en atributos del sensor HA para distinguir scalars de arrays — esto es correcto como convención interna
- `docs/shell_command_example.yaml` y `docs/SHELL_COMMAND_SETUP.md` muestran que solo se pasa `P_deferrable` al shell command (no los 6 parámetros completos)

### Pitfalls to Avoid
- **No usar `int()` para truncar horas** — `int(1.94) = 1`, lo que causa que EMHASS programe menos tiempo del necesario. Usar `math.ceil()` → `ceil(1.94) = 2`
- **No asumir el entity_id** del sensor — con `has_entity_name=True`, HA genera entity_id desde `device_name + entity_name`. El device name `"EV Trip Planner {vehicle_id}"` genera `sensor.ev_trip_planner_{vehicle_id}_emhass_perfil_diferible_{vehicle_id}`, NO `sensor.emhass_perfil_diferible_*`



## Codebase Analysis

### Existing Patterns

#### `datetime.now()` — Uso masivo y peligroso (11 ocurrencias)

Todas las ocurrencias en `emhass_adapter.py` (verificadas con grep):

| Línea | Método | Contexto | ¿Bug? |
|-------|--------|----------|-------|
| 126 | `async_load()` | `now = datetime.now()` resta con `released_time` (de fromisoformat) | **Sí** — si `released_time` tiene tz |
| 277 | `async_release_trip_index()` | `self._released_indices[idx] = datetime.now()` | No — solo almacena |
| 333 | `async_publish_deferrable_load()` | `now = datetime.now()` → `deadline_dt - now` | **Sí — CONFIRMADO por logs** |
| 471 | `_calculate_deadline_from_trip()` | pasado a `calculate_next_recurring_datetime()` | No — input de referencia |
| 519 | `_populate_per_trip_cache_entry()` | `deadline_dt = datetime.now()` fallback | No — fallback (deben ser iguales) |
| 534 | `_populate_per_trip_cache_entry()` | `inicio_ventana - datetime.now()` | **Sí — MISMO BUG que 333** |
| 537 | `_populate_per_trip_cache_entry()` | `deadline_dt - datetime.now()` | **Sí — MISMO BUG que 333** |
| 721 | `get_available_indices()` | `now = datetime.now()` resta con `released_time` | **Sí** — si `released_time` tiene tz |
| 785 | otro método | `now = datetime.now()` | Por verificar |
| 1177 | `async_notify_error()` | `self._last_error_time = datetime.now()` | No — solo almacena |
| 1219 | persistencia | `datetime.now().isoformat()` | No — serialización |

**Conclusión:** Hay al menos **5 ocurrencias** con bug potencial (133, 333, 534, 537, 721), no solo 1 como indicaba la spec anterior.

#### `_populate_per_trip_cache_entry()` — Bug gemelo ignorado

```python
# Líneas 534-537 — la spec original solo mencionaba línea 334
def_start_timestep = 0
if charging_windows:
    inicio_ventana = charging_windows[0].get("inicio_ventana")
    if inicio_ventana:
        delta_hours = (inicio_ventana - datetime.now()).total_seconds() / 3600  # L534 BUG
        def_start_timestep = max(0, min(int(delta_hours), 168))

hours_available = (deadline_dt - datetime.now()).total_seconds() / 3600  # L537 BUG
```

Este método se llama desde `async_publish_all_deferrable_loads()` para cada viaje. Si `deadline_dt` viene de `datetime.fromisoformat()` con offset (ej: `"+01:00"`), crash idéntico.

#### `def_total_hours` — `round()` vs `int()` vs `math.ceil()`

```python
# emhass_adapter.py línea ~379
"def_total_hours": round(total_hours, 2),  # Devuelve 1.94 (float)
```

La spec anterior proponía `int()`, pero `int(1.94) = 1` — eso programa 1h de carga cuando se necesitan 1.94h. El vehículo NO se cargaría lo suficiente. La corrección es `math.ceil(total_hours)` → `ceil(1.94) = 2`.

Misma lógica en `_populate_per_trip_cache_entry` línea ~549:
```python
"def_total_hours": round(total_hours, 2),
"def_total_hours_array": [round(total_hours, 2)],
```

#### Entity ID — Patrón real vs asumido

El sensor `EmhassDeferrableLoadSensor` define:
- `unique_id = f"emhass_perfil_diferible_{entry_id}"`
- `has_entity_name = True`
- `name = f"EMHASS Perfil Diferible {vehicle_id}"`
- Device name: `f"EV Trip Planner {vehicle_id}"`

Con `has_entity_name=True`, HA genera: `sensor.{device_slug}_{entity_slug}`
→ `sensor.ev_trip_planner_{vehicle_id}_emhass_perfil_diferible_{vehicle_id}`

Panel.js busca: `sensor.emhass_perfil_diferible_` — 5 ocurrencias (líneas 883, 893, 1210, 1218, 1233).

**Esto NO COINCIDE** con el entity_id generado por HA. La búsqueda fallará porque el entity_id real empieza con `sensor.ev_trip_planner_*`, no con `sensor.emhass_perfil_diferible_*`.

**Fix robusto:** Usar `entityId.includes('emhass_perfil_diferible_')` en vez de `startsWith`. Esto funciona independientemente del prefijo del dispositivo.

#### Template Jinja2 — Dos problemas distintos (NO es falso positivo)

**Clarificación crítica** — la spec anterior mezclaba dos conceptos:

1. **Atributos del sensor HA** (CORRECTOS): El sensor `EmhassDeferrableLoadSensor` expone `def_total_hours_array`, `p_deferrable_nom_array`, etc. Esto es correcto como convención de HA.

2. **Keys del template Jinja2** (INCORRECTOS): El template genera YAML con keys `def_total_hours_array:` — pero EMHASS REST API espera `def_total_hours:` (sin suffix `_array`). Las keys deben mapearse:
   - `def_total_hours_array:` → `def_total_hours:` (leyendo de attr `def_total_hours_array`)
   - `p_deferrable_nom_array:` → `P_deferrable_nom:` (capital P, leyendo de attr `p_deferrable_nom_array`)
   - `p_deferrable_matrix:` → `P_deferrable:` (capital P, leyendo de attr `p_deferrable_matrix`)

#### CSS Route — Confirmado con grep

`services.py` línea 1269 registra `/ev-trip-planner/panel.css` (guiones).
`panel.js` línea 723 solicita `/ev_trip_planner/panel.css` (guiones bajos).
→ 404 confirmado.

#### Modal Trip Type — `_showEditForm()` línea 1637

El código actual:
```javascript
this._formType = trip.type === 'puntual' ? 'puntual' : 'recurrente';
```

Pero en línea 1605 (mismo archivo), el trip_type se calcula con `trip.tipo`:
```javascript
trip.trip_type = trip.tipo === 'recurrente' ? 'recurrente' : 'puntual';
```

Y en línea 1069, la detección usa 3 campos:
```javascript
const isPunctual = trip.tipo === 'puntual' || trip.type === 'puntual' || trip.recurring === false;
```

`_showEditForm()` solo comprueba `trip.type`, pero los trips usan `trip.tipo` (español). Fix: alinear con el patrón de 3 campos de línea 1069.

### Dependencies

- `datetime` y `timezone` de la stdlib Python — ya disponible, no requiere nuevos paquetes
- `math.ceil` de la stdlib — ya disponible

### Constraints

- El entity_id exacto depende de la configuración del usuario (puede haber sido renombrado en el entity registry de HA)
- Los 5 puntos de `datetime.now()` con bug están en métodos que se llaman en cadena — el fix debe ser consistente en todos

## Related Specs

| Spec | Relevance | Relationship | May Need Update |
|------|-----------|--------------|-----------------|
| N/A | — | No hay specs relacionadas activas | No |

## Feasibility Assessment

| Aspect | Assessment | Notes |
|--------|------------|-------|
| Technical Viability | High | Todos los cambios son modificaciones quirúrgicas a código existente |
| Effort Estimate | S | ~20 líneas de cambios en Python, ~15 líneas en JS |
| Risk Level | Medium | El fix de datetime afecta múltiples code paths en cadena |

## Recommendations for Requirements

1. Cambiar `round(total_hours, 2)` a `math.ceil(total_hours)` — NO usar `int()` que trunca
2. Usar `datetime.now(timezone.utc)` en TODAS las ocurrencias dentro de `emhass_adapter.py` que participan en restas con datetimes offset-aware (5 puntos mínimo)
3. Buscar sensor EMHASS con `includes('emhass_perfil_diferible_')` en vez de `startsWith` — robusto ante cualquier prefijo de device
4. Corregir las keys del template Jinja2: leer de attrs `*_array` pero emitir keys sin suffix para EMHASS API
5. Corregir la ruta CSS de `/ev_trip_planner/` a `/ev-trip-planner/`
6. Eliminar el warning "EMHASS sensor not available" y mostrar siempre la sección con `default()` del Jinja2
7. Alinear `_showEditForm()` con el patrón de detección de 3 campos de línea 1069

## Open Questions

- ¿El `_attr_has_entity_name = True` genera siempre `sensor.ev_trip_planner_*` o depende de config de usuario? → Verificar en sistema real. Se puede mitigar usando `includes()` en vez de `startsWith()`.
- ¿EMHASS acepta `def_total_hours` como float o requiere estrictamente entero? → Los docs oficiales no son 100% explícitos, pero la convención de EMHASS usa enteros (ver `docs/MILESTONE_4_POWER_PROFILE.md` línea 306: `def_total_hours: 0.53` — muestra float). Se puede dejar como `math.ceil()` (entero) por seguridad.

## Sources

- `custom_components/ev_trip_planner/emhass_adapter.py` — 11 ocurrencias de `datetime.now()`
- `custom_components/ev_trip_planner/sensor.py` líneas 155-270 — definición de `EmhassDeferrableLoadSensor`
- `custom_components/ev_trip_planner/frontend/panel.js` líneas 883, 893, 914-918, 723, 942, 1210, 1637
- `custom_components/ev_trip_planner/services.py` línea 1269 — registro CSS path
- `docs/SHELL_COMMAND_SETUP.md` — formato EMHASS API (`P_deferrable`)
- `docs/emhass-setup.md` — template de referencia con keys `*_array`
- `docs/MILESTONE_4_POWER_PROFILE.md` línea 306 — ejemplo `def_total_hours: 0.53`
| Modal tipo viaje | Media | Edición de viajes |

---

## Recomendaciones

### Priority 1 (Crítico - Bloquea funcionalidad):
1. **Fix datetime offset** - Permite que los viajes se publiquen correctamente
2. **Fix entity_id pattern** - El panel puede encontrar los sensores
3. **Fix template Jinja2 keys** - EMHASS recibe keys correctas

### Priority 2 (Alto - Funcionalidad degradada):
4. **Fix def_total_hours to int** - EMHASS acepta los datos
5. **Fix panel.css route** - CSS se carga correctamente (guiones vs guiones bajos)
6. **Fix modal trip type** - Modal muestra tipo correcto al editar

### Priority 3 (Medio - Mejora UX):
7. **Fix EMHASS availability message** - Mostrar datos aunque estén vacíos
8. **Fix panel disappearance** - Experiencia de usuario estable

**Nota:** El problema inicial de atributos `_array` era parcialmente correcto. El sensor agregado expone atributos con sufijo `_array` (como `def_total_hours_array`), PERO el template Jinja2 debe usar keys SIN sufijo para que EMHASS las entienda correctamente. La corrección es:
- **Keys del template (izquierda de `:`):** Sin `_array` (ej: `def_total_hours`)
- **Atributo del sensor (2do param):** Con `_array` (ej: `def_total_hours_array`)

---

## Feasibility: High | Risk: Medium | Effort: M
