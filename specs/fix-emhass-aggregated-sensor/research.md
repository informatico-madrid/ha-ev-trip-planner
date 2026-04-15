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

---

## Problema 1: Entity ID Incorrecto en panel.js

**Archivo:** `custom_components/ev_trip_planner/frontend/panel.js`

**Código actual (líneas 883-886):**
```javascript
if (entityId.startsWith('sensor.emhass_perfil_diferible_')) {
```

**Problema:** El código busca sensores con patrón `sensor.emhass_perfil_diferible_`, pero el sensor real creado es:
```
sensor.trip_planner_chispitas_emhass_perfil_diferible_chispitas
```

**Solución:** Actualizar el patrón de búsqueda en panel.js para buscar `sensor.trip_planner_*_emhass_perfil_diferible_*`.

---

## Problema 2: def_total_hours debe ser entero

**Archivo:** `custom_components/ev_trip_planner/emhass_adapter.py`

**Código actual (línea 379 y 545):**
```python
"def_total_hours": round(total_hours, 2),  # Devuelve 1.94 (float)
```

**Problema:** EMHASS requiere valores enteros, no floats.

**Ejemplo del error reportado:**
```
def_total_hours: 1.94  # INCORRECTO (float)
def_total_hours: 2     # CORRECTO (entero)
```

**Solución:** Usar `int(total_hours)` en lugar de `round(total_hours, 2)`.

---

## Problema 3: Atributos `_array` - FALSO POSITIVO

**Verificación final:** El usuario aclaró que los atributos del sensor agregado están **CORRECTOS**:

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

**Análisis:**

1. **El sensor agregado (EmhassDeferrableLoadSensor) define atributos con sufijo `_array` CORRECTAMENTE como listas:**
   ```python
   # custom_components/ev_trip_planner/sensor.py líneas 234-237
   def_total_hours_array: List[float] = []
   p_deferrable_nom_array: List[float] = []
   def_start_timestep_array: List[int] = []
   def_end_timestep_array: List[int] = []
   ```

2. **Los params individuales SÍ envuelven valores en arrays de 1 elemento:**
   ```python
   # emhass_adapter.py línea 551-554
   "def_total_hours_array": [round(total_hours, 2)],  # [1.94]
   "p_deferrable_nom_array": [round(power_watts, 0)], # [3600.0]
   ```

3. **El template del panel usa los nombres CORRECTOS:**
   ```javascript
   // panel.js líneas 914-917
   def_total_hours_array: {{ state_attr('${emhassSensorEntityId}', 'def_total_hours_array') | default([], true) }}
   ```

4. **La confusión fue de observabilidad:** En Home Assistant, cuando se ven los atributos individualmente en la UI básica, pueden parecer escalares. Pero al ver el detalle completo, se ve que son arrays con 1 elemento.

**Conclusión:** **NO HAY PROBLEMA** con los nombres de atributos o el formato array. El sensor agregado funciona correctamente.

---

## Problema 3: Segundo Viaje No se Actualiza en Sensor Agregado

**Evidencia del usuario:**
```
sensor.trip_planner_chispitas_ev_trip_planner_trips_list
punctual_trips:
- id: pun_20260415_0pykgn
- id: pun_20260423_jz4twj  # SEGUNDO VIAJE
```

Pero el sensor agregado `sensor.emhass_perfil_diferible_chispitas` **no incluye el segundo viaje**.

**Causa raíz:** El nuevo viaje tiene `emhass_index: -1` (ver Problema 4), lo que significa que **falló al publicarse** en EMHASS por el error de datetime.

**Mecanismo del fallo:**
1. Usuario crea segundo viaje
2. `trip_manager.sync_trip_to_emhass()` llama a `emhass_adapter.async_publish_deferrable_load()`
3. El método intenta calcular `hours_available` restando datetime offset-naive y offset-aware
4. **Excepción lanzada** → viaje no se añade a `_cached_per_trip_params`
5. `async_publish_all_deferrable_loads()` no incluye el nuevo viaje
6. `coordinator.async_refresh()` actualiza `coordinator.data["per_trip_emhass_params"]` **sin el nuevo viaje**
7. `EmhassDeferrableLoadSensor.extra_state_attributes` lee `per_trip_params` **sin el segundo viaje**
8. El sensor agregado sigue mostrando datos solo del primer viaje

**Evidencia adicional:**
- Nuevo viaje sensor muestra: `emhass_index: -1`, `def_total_hours: 0`, `power_profile_watts: []`
- Esto confirma que el viaje nunca se publicó correctamente

---

## Problema 4: emhass_index = -1 para Nuevo Viaje

**Sensor reportado por usuario:**
```
sensor.trip_planner_chispitas_emhass_index_for_pun_20260423_jz4twj
Estado: -1
def_total_hours: 0
P_deferrable_nom: 0
def_start_timestep: 0
def_end_timestep: 24
power_profile_watts: []  # VACÍO
trip_id: pun_20260423_jz4twj
emhass_index: -1
kwh_needed: 0
deadline: null
```

**Análisis:**
- `emhass_index: -1` es el valor inicial por defecto (ver emhass_adapter.py línea 300)
- Significa que el viaje **nunca fue asignado un índice válido**
- `kwh_needed: 0` - El cálculo falló porque el error de datetime ocurrió antes de calcular kwh
- `deadline: null` - El deadline no se calculó (ver Problema 5)
- `power_profile_watts: []` - Perfil vacío porque no hubo datos válidos

**Causa raíz:** Error `can't subtract offset-naive and offset-aware datetimes` (ver Problema 5) impide que el viaje se publique correctamente.

---

## Problema 5: Error datetime offset -naive vs -aware

**Error en logs:**
```
ERROR: custom_components.ev_trip_planner.trip_manager:938
Error syncing trip pun_20260423_jz4twj to EMHASS:
can't subtract offset-naive and offset-aware datetimes
```

**Código problemático (calculations.py línea 781):**
```python
delta = deadline_dt - now
```

**Causa:**
- `deadline_dt` es un datetime **con timezone** (offset-aware)
- `now` es un datetime **sin timezone** (offset-naive)
- Python no puede restar dos datetime con diferentes timezone awareness

**Lugar exacto del error:**
- `custom_components/ev_trip_planner/emhass_adapter.py` línea 334:
  ```python
  hours_available = (deadline_dt - now).total_seconds() / 3600
  ```

**Solución:** Usar `datetime.now(timezone.utc)` en lugar de `datetime.now()`.

---

## Problema 6: Ruta Incorrecta de panel.css (404)

**Error en consola del navegador:**
```
Refused to apply style from 'http://192.168.1.100:8123/ev_trip_planner/panel.css?v=...'
because its MIME type ('text/plain') is not a supported stylesheet MIME type
```

**Causa raíz:** Discrepancia de rutas entre registration y uso:

- **Services registra en:** `/ev-trip-planner/panel.css` (con guiones)
  ```python
  # services.py línea 1269
  StaticPathConfig("/ev-trip-planner/panel.css", str(panel_css_path), ...)
  ```

- **Panel.js busca en:** `/ev_trip_planner/panel.css` (con guiones bajos)
  ```javascript
  // panel.js línea 723
  <link rel="stylesheet" href="/ev_trip_planner/panel.css?v=${Date.now()}">
  ```

**Verificación:** Acceder directamente a `http://192.168.1.100:8123/ev_trip_planner/panel.css` devuelve **404 Page not found**.

**Impacto:**
- El CSS no se carga correctamente
- El panel se ve con estilos básicos o incompletos
- El mensaje de error 404 se repite muchas veces en la consola

**Solución:** Unificar la ruta en panel.js para usar `/ev-trip-planner/panel.css` con guiones.

---

## Problema 7: Mensaje "EMHASS sensor not available" Persistente

**Reporte del usuario:**
> "el mensaje '⚠️ EMHASS sensor not available...' no desaparece cuando creo el primer viaje"

**Comportamiento actual:**
- El mensaje "EMHASS sensor not available" persiste incluso cuando hay trips activos con datos EMHASS
- El usuario tiene trips activos pero el mensaje no desaparece

**Lógica actual (panel.js línea ~905):**
```javascript
const emhassAvailable = emhassState && 
                        emhassState.state !== 'unavailable' && 
                        emhassState.state !== 'unknown';
```

**Problema:** La lógica solo verifica si el sensor existe y no está "unavailable" o "unknown", pero **no verifica si hay datos válidos**.

**Causa posible:**
1. El panel busca el sensor EMHASS incorrecto (ver Problema 1 - entity_id pattern)
2. El sensor existe pero está "unavailable" porque no hay trips con datos EMHASS válidos

**Propuesta de solución:**
- Eliminar el mensaje de error "EMHASS sensor not available" por completo
- Siempre mostrar la sección EMHASS Configuration, incluso cuando no hay viajes
- Mostrar valores 0/vacíos en lugar de ocultar la sección
- El template Jinja2 ya maneja valores por defecto con `default()`

**Comportamiento esperado:**
- Siempre mostrar la sección EMHASS Configuration (sin mensaje de error)
- Cuando hay trips activos: Mostrar datos EMHASS reales
- Cuando no hay trips: Mostrar valores 0/vacíos:
  ```
  number_of_deferrable_loads: 0
  def_total_hours: []
  P_deferrable_nom: []
  def_start_timestep: []
  def_end_timestep: []
  P_deferrable: []
  ```

---

## Problema 8: Keys del Template Jinja2 Incorrectas

**Reporte del usuario:**
El template Jinja2 del panel usa keys con sufijo `_array`, pero EMHASS espera keys sin sufijo:

**Template actual del panel (INCORRECTO):**
```jinja2
def_total_hours_array: {{ state_attr('${emhassSensorEntityId}', 'def_total_hours_array') | default([], true) }}
p_deferrable_nom_array: {{ state_attr('${emhassSensorEntityId}', 'p_deferrable_nom_array') | default([], true) }}
def_start_timestep_array: {{ state_attr('${emhassSensorEntityId}', 'def_start_timestep_array') | default([], true) }}
def_end_timestep_array: {{ state_attr('${emhassSensorEntityId}', 'def_end_timestep_array') | default([], true) }}
p_deferrable_matrix: {{ state_attr('${emhassSensorEntityId}', 'p_deferrable_matrix') | default([], true) }}
```

**Formato que espera EMHASS (shell command real):**
```yaml
emhass_dayahead_optim_with_soc_limit: >
  curl -d '{
    "def_total_hours": [1.5, 2.5],        # Sin _array
    "P_deferrable_nom": [3600, 3600],     # Sin _array
    "def_start_timestep": [0, 0],         # Sin _array
    "def_end_timestep": [168, 168],       # Sin _array
    "P_deferrable": [...]                  # Sin _array (power profiles)
  }' http://192.168.1.100:5000/action/dayahead-optim"
```

**Análisis:**

1. **El sensor agregado expone atributos con sufijo `_array`:**
   ```python
   # sensor.py línea 260-267
   attrs["def_total_hours_array"] = def_total_hours_array  # [1.94]
   attrs["p_deferrable_nom_array"] = p_deferrable_nom_array  # [3600.0]
   attrs["def_start_timestep_array"] = def_start_timestep_array  # [0]
   attrs["def_end_timestep_array"] = def_end_timestep_array  # [2]
   attrs["p_deferrable_matrix"] = matrix  # [[...]]
   ```

2. **Pero EMHASS espera keys SIN sufijo `_array`:**
   - `def_total_hours` (no `def_total_hours_array`)
   - `P_deferrable_nom` (no `p_deferrable_nom_array`)
   - `def_start_timestep` (no `def_start_timestep_array`)
   - `def_end_timestep` (no `def_end_timestep_array`)
   - `P_deferrable` (no `p_deferrable_matrix`)

3. **Corrección necesaria:**
   ```jinja2
   # Keys (left of :) deben ser sin _array, pero el atributo (2nd param) SÍ con _array
   def_total_hours: {{ state_attr('${emhassSensorEntityId}', 'def_total_hours_array') | default([], true) }}
   P_deferrable_nom: {{ state_attr('${emhassSensorEntityId}', 'p_deferrable_nom_array') | default([], true) }}
   def_start_timestep: {{ state_attr('${emhassSensorEntityId}', 'def_start_timestep_array') | default([], true) }}
   def_end_timestep: {{ state_attr('${emhassSensorEntityId}', 'def_end_timestep_array') | default([], true) }}
   P_deferrable: {{ state_attr('${emhassSensorEntityId}', 'p_deferrable_matrix') | default([], true) }}
   ```

**Impacto:**
- El template Jinja2 genera keys incorrectas para EMHASS
- EMHASS recibirá `def_total_hours_array` en lugar de `def_total_hours`
- La optimización de EMHASS fallará o usará valores por defecto incorrectos

**Solución:**
Actualizar el template en panel.js para usar keys sin sufijo `_array` en la izquierda de `:`.

---

## Problema 9: Modal de Edición - Tipo de Viaje Incorrecto

**Reporte del usuario:**
> "Cuando edito un viaje puntual y se abre el modal para editar, el Tipo de Viaje que sale seleccionado es 'recurrente'. Debería estar seleccionado 'puntual'."

**Problema:**
- Al editar un viaje puntual, el select muestra incorrectamente "recurrente" seleccionado
- Esto confunde al usuario y puede causar errores si no se corrige manualmente

**Lugar probable del bug:**
- File: `custom_components/ev_trip_planner/frontend/panel.js` línea ~1637
```javascript
this._formType = trip.type === 'puntual' ? 'puntual' : 'recurrente';
```

**Análisis:**

1. **Código actual (línea 1637):**
   ```javascript
   this._formType = trip.type === 'puntual' ? 'puntual' : 'recurrente';
   ```

2. **El problema:**
   - Solo verifica `trip.type`
   - Viajes puntuales pueden tener `trip.tipo === 'puntual'` o `trip.recurring === false`
   - Si `trip.type` es undefined pero `trip.tipo === 'puntual'`, el modal mostrará "recurrente"

3. **Código correcto debería ser (como en línea 1068-1069):**
   ```javascript
   const isRecurring = trip.tipo === 'recurrente' || trip.type === 'recurrente' || trip.recurring === true;
   const isPunctual = trip.tipo === 'puntual' || trip.type === 'puntual' || trip.recurring === false;
   ```

**Impacto:**
- Confusión del usuario al editar viajes
- Riesgo de cambiar el tipo de viaje accidentalmente
- Experiencia de usuario pobre

---

## Impacto

| Problema | Severidad | Usuarios Afectados |
|----------|-----------|-------------------|
| Entity ID incorrecto | Alta | Todos |
| def_total_hours float | Media | Todos con viajes |
| Segundo viaje no actualiza | Alta | Usuarios con múltiples viajes |
| emhass_index = -1 | Alta | Nuevos viajes |
| Error datetime | Crítica | Todos los viajes nuevos |
| panel.css ruta incorrecta | Media | Todos (estilos rotos) |
| Mensaje EMHASS persistente | Media | Todos (UX confusa) |
| Template keys incorrectas | Crítica | EMHASS optimización fallará |
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
