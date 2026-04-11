# Gaps y Problemas Detectados

> **⚠️ AVISO IMPORTANTE**: Los **problemas descritos** son hechos observados por el usuario.
>
> Las **hipótesis sobre causas, soluciones y diagnosis** son **teóricas** y deben verificarse mediante:
> - Análisis de logs de Home Assistant
> - Depuración en tiempo real
> - Reproducción de los problemas
> - Verificación del código en ejecución
>
> **No se deben implementar soluciones sin validar primero las hipótesis.**

## 1. Panel del sidebar no se elimina al borrar un vehículo

### Problema
Al eliminar un vehículo (config entry), el ítem del panel correspondiente en el sidebar de Home Assistant no se elimina. Solo desaparece después de un reinicio completo de Home Assistant.

### Referencias
- **Código del problema**: [custom_components/ev_trip_planner/services.py:1451-1533](../../custom_components/ev_trip_planner/services.py#L1451-L1533)
- **Código de solución similar**: [custom_components/ev_trip_planner/services.py:1440-1446](../../custom_components/ev_trip_planner/services.py#L1440-L1446)
- **Función de panel**: [custom_components/ev_trip_planner/panel.py:109-145](../../custom_components/ev_trip_planner/panel.py#L109-L145)

### Análisis de la evidencia
En Home Assistant, cuando se elimina una config entry, se sigue este flujo:
1. `async_unload(hass, entry)` → llama a `async_unload_entry_cleanup`
2. `async_remove_entry(hass, entry)` → llama a `async_remove_entry_cleanup`

**Posible problema**:  `async_remove_entry_cleanup` NO desregistra el panel, mientras que `async_unload_entry_cleanup` SÍ lo hace (línea 1444).

### Hipótesis

#### H1: Falta la llamada a `async_unregister_panel` en `async_remove_entry_cleanup`
**Probabilidad: ALTA**

`async_remove_entry_cleanup` cleanup storage y helpers pero no desregistra el panel.

**Evidencia**:
- Línea 1444 en `async_unload_entry_cleanup`: `await async_unregister_panel(hass, vehicle_id)`
- Esta línea NO existe en `async_remove_entry_cleanup`

**Posible solución**: Agregar después de línea 1495:
```python
# Remove the native panel from sidebar
try:
    from .panel import async_unregister_panel
    await async_unregister_panel(hass, vehicle_id)
except Exception as ex:
    _LOGGER.warning("Failed to unregister panel for vehicle %s: %s", vehicle_id, ex)
```

#### H2: El panel queda en caché del frontend de Home Assistant
**Probabilidad: MEDIA**

Home Assistant cachea agresivamente el estado del sidebar. Aunque `frontend.async_remove_panel` se llame, el frontend podría no actualizar su estado inmediatamente.

**Evidencia**:
- El cache-busting en línea 69-70 sugiere que ya han tenido problemas de cache
- Comentarios en línea 68-69: "Add timestamp to force JS reload (bypass HA cache)"

**Posible solución alternativa**: Podría requerir recargar la página del navegador o reiniciar el frontend.

#### H3: `async_remove_entry_cleanup` usa el `vehicle_id` incorrecto
**Probabilidad: BAJA**

En líneas 1466-1472, el `vehicle_id` se extrae de `vehicle_name_raw` que viene de `entry.data.get("vehicle_name")`. Si este valor es None, usa `entry.entry_id`.

**Evidencia**:
- El panel se registra con `vehicle_id` (línea 53 en panel.py)
- `async_unregister_panel` usa el mismo patrón para construir `frontend_url_path`

**Sin embargo**: Si el `vehicle_id` usado para unregister no coincide exactamente con el usado para register, el panel no se eliminará.

#### H4: Race condition entre unload y remove
**Probabilidad: BAJA**

Si `async_unload` y `async_remove_entry` se llaman casi simultáneamente, podría haber una condición de carrera.

**Evidencia**:
- `async_unload_entry_cleanup` desregistra el panel
- Si `async_remove_entry` se llama después, el panel ya no existe

**Sin embargo**: `async_remove_panel` ya tiene un try-except que maneja esto (línea 127-144 en panel.py).

### Próximos pasos para investigación
1. Verificar logs al eliminar un vehículo para ver si hay errores
2. Confirmar que `async_remove_entry_cleanup` se está llamando
3. Verificar el `vehicle_id` que se está usando
4. Probar agregando la llamada a `async_unregister_panel` en `async_remove_entry_cleanup`

---

## 2. Sección Vehicle Status del panel está vacía

### Problema
La sección "📊 Vehicle Status" en el panel del vehículo podría no estar mostrando ningún dato, aunque podría mostrar los sensores relacionados con el estado del vehículo: SOC, consumo, rango, estado de carga, etc.

### Referencias
- **Código del panel**: [custom_components/ev_trip_planner/frontend/panel.js:730-740](../../custom_components/ev_trip_planner/frontend/panel.js#L730-L740)
- **Agrupación de sensores**: [custom_components/ev_trip_planner/frontend/panel.js:1089-1120](../../custom_components/ev_trip_planner/frontend/panel.js#L1089-L1120)
- **Filtro de status sensors**: [custom_components/ev_trip_planner/frontend/panel.js:1125-1138](../../custom_components/ev_trip_planner/frontend/panel.js#L1125-L1138)

### Análisis de la evidencia
1. El panel renderiza la sección "Vehicle Status" solo si `statusCards` tiene contenido
2. `statusCards` se genera de `validStatusSensors` (línea 683)
3. `validStatusSensors` se filtra de `groupedSensors.status` (línea 668)
4. Un sensor se considera "status" si `_isStatusSensor()` devuelve `true`
5. Los sensores se filtran adicionalmente si su valor es `null` (línea 669-671)

### Cómo se determina qué es un "status sensor"

```javascript
_isStatusSensor(entityId) {
  const name = this._entityIdToName(entityId);
  const lowerName = name.toLowerCase();
  return (
    lowerName.includes('soc') ||
    lowerName.includes('battery_level') ||
    lowerName.includes('range') ||
    lowerName.includes('charging_status') ||
    lowerName.includes('charging') ||
    lowerName.includes('plugged') ||
    lowerName.includes('state') ||
    lowerName.includes('status')
  );
}
```

### Hipótesis

#### H1: No hay sensores configurados con los nombres esperados
**Probabilidad: BAJA - Descartada parcialmente por H4**

El usuario puede tener sensores de SOC y consumo, pero con nombres que no coinciden con los patrones de búsqueda.

**Evidencia**:
- Los patrones buscan palabras clave en inglés: 'soc', 'battery_level', 'range', 'charging'
- Si el usuario tiene sensores con nombres en español, podrían no detectarse

**Sin embargo**: Esto podría NO ser la causa raíz. Incluso con nombres en español, el problema podría ser que `_getVehicleStates()` filtra por `sensor.{vehicle_id}_*`, no por el contenido del nombre.

**Nota secundaria**: `_entityIdToName()` (línea 1168) normaliza nombres quitea prefijos y convirtiendo a formato legible. Si un sensor se llama `sensor.mi_coche_soc_level`, se convierte a "Mi Coche Soc Level", que sí contiene 'soc'.

#### H2: Los sensores existen pero tienen estado `unavailable` o `unknown`
**Probabilidad: BAJA - Descartada**

Los sensores se filtran si `this._formatSensorValue(s.entityId)` devuelve `null` (línea 669-671).

**Análisis del código** (línea 1207-1227):
```javascript
_formatSensorValue(entityId) {
  const value = state.state;
  if (value === 'unavailable' || value === 'unknown' || ...) {
    return 'N/A';  // ← Devuelve 'N/A', NO null
  }
  // ...
}
```

**Evidencia**:
- Sensores con estado 'unavailable' devuelven 'N/A', no null
- El filtro es `formattedValue !== null`
- Por lo tanto, los sensores unavailable PODRÍAN pasar el filtro

**Conclusión**: Esta NO es la causa. Los sensores unavailable se mostrarían como "N/A" en el panel.

#### H3: Los sensores podrían no estar obteniéndose correctamente
**Probabilidad: ALTA - Confirmada en H4**

El método `_getVehicleStates()` podría no estar devolviendo todos los sensores del vehículo.

**Evidencia**:
- `_getVehicleStates()` filtra por patrones de entity_id (línea 1018-1028)
- Solo devuelve entidades que empiezan con ciertos prefijos
- Los sensores de integraciones de vehículos NO siguen estos patrones

**Confirmado**: Ver análisis detallado en H4.

#### H4: `_getVehicleStates()` solo busca sensores con prefijo `vehicle_id`
**Probabilidad: MUY ALTA - Esta es la causa raíz probable**

El método `_getVehicleStates()` filtra los sensores por patrones específicos que asumen que todos los sensores del vehículo empiezan con `sensor.{vehicle_id}` o `sensor.{vehicle_id}_`.

**Código del problema** (línea 1018-1028):
```javascript
const patterns = [
  `sensor.${lowerVehicleId}`, `sensor.${lowerVehicleId}_`,
  `binary_sensor.${lowerVehicleId}`, `binary_sensor.${lowerVehicleId}_`,
  // ... otros patrones
];
```

**Evidencia**:
- Los sensores de vehículos reales vienen de integraciones (Tesla, VW, Nissan, etc.)
- Estas integraciones usan sus propios prefijos: `sensor.tesla_*`, `sensor.vwid_*`, `sensor.nissan_*`
- **NUNCA** tendrán `sensor.{vehicle_id}_*` como nombre
- Ejemplo real: `sensor.tesla_model_3_battery_level`, `sensor.vwid_id_battery_soc`

**Esto explica por qué la sección está vacía**:
1. `_getVehicleStates()` filtra `sensor.{vehicle_id}_*`
2. Los sensores reales son `sensor.tesla_*` o `sensor.vwid_*`
3. Ningún sensor pasa el filtro
4. `groupedSensors.status` está vacío
5. La sección Vehicle Status no se renderiza

**Posible solución**:
1. **Corto plazo**: Documentar que el usuario debe crear sensores plantilla que mapeen los sensores reales al formato esperado
2. **Medio plazo**: Permitir configuración de patrones de sensores adicionales en config flow
3. **Largo plazo**: Cambiar arquitectura para no depender de prefijos de entity_id

#### H5: La sección Vehicle Status podría necesitar incluir más grupos de sensores
**Probabilidad: BAJA - Descartada por H4**

Incluso si el problema H4 no existiera, hay una contradicción en el código:

**Análisis adicional**:
Mirando línea 1129, `_isStatusSensor()` busca 'soc', pero línea 1106-1107 tiene un `else if` que también busca 'soc'. Esto significa:

```javascript
// Línea 1104-1107
if (this._isStatusSensor(entityId)) {  // Busca 'soc'
  groups.status.push({ entityId, state, name, icon });
} else if (lowerName.includes('soc') || ...) {  // También busca 'soc'
  groups.battery.push({ entityId, state, name, icon });
}
```

Si `_isStatusSensor()` devuelve true para un sensor con 'soc', va a `groups.status`. Si no, el `else if` lo pone en `groups.battery`.

**Sin embargo**: Esto no es un problema porque el `if` se evalúa primero. Los sensores con 'soc' van a `status` (gracias a `_isStatusSensor()`), no a `battery`.

**Nota**: El grupo `battery` probablemente existe para sensores que no son "status" pero sí de batería, como `sensor.{vehicle_id}_battery_capacity` (capacidad total de la batería en kWh).

Si un sensor tiene 'soc' en el nombre:
- Primero se evalúa `_isStatusSensor()` que busca 'soc'
- Si es true, va a `groups.status`
- Si no, va a `groups.battery`

**Entonces los sensores de SOC DEBERÍAN aparecer en Vehicle Status**.

Posible problema:  `_isStatusSensor()` tiene condiciones OR. Si un sensor tiene 'soc' pero NO tiene las otras palabras clave ('battery_level', 'range', etc.), ¿se evalúa correctamente? (necesita verificación)

Sí, porque es OR: `lowerName.includes('soc')` es suficiente.

**Pero** wait, mirando más cuidadosamente... el problema puede ser que los sensores están en el grupo `battery` por el `else if`, pero nunca llegan al primer `if` porque `_isStatusSensor()` puede no estar funcionando como se espera.

**Investigación necesaria**:
- ¿Qué entity_ids tienen los sensores de SOC del usuario?
- ¿`_entityIdToName()` devuelve el nombre correcto?
- ¿El nombre contiene 'soc' exactamente?

#### H6: Falta integración con sensores externos del vehículo
**Probabilidad: ALTA - Relacionada con H4**

El sistema podría estar diseñado para funcionar solo con sus propios sensores (`sensor.{vehicle_id}_*`), no para mostrar sensores de integraciones de terceros.

**Evidencia**:
- El panel no tiene forma de descubrir sensores de integraciones externas
- No hay configuración para mapear sensores externos a la sección Vehicle Status
- La arquitectura asume que todos los datos vienen de sensores creados por la integración

**Ejemplo del problema**:
- Usuario tiene integración Tesla con sensores: `sensor.tesla_model_3_battery_level`, `sensor.tesla_model_3_charger_state`
- Usuario tiene integración VW con sensores: `sensor.vwid_id_soc`, `sensor.vwid_id_charging_status`
- El panel podría NO poder mostrar estos sensores porque no empiezan con `sensor.{vehicle_id}_`

**Posible solución**:
1. **Opción A - Template sensors**: Documentar que el usuario debe crear sensores plantilla:
```yaml
template:
  - sensor:
      - name: "{vehicle_id}_soc"
        unit_of_measurement: "%"
        device_class: battery
        state: "{{ states('sensor.tesla_model_3_battery_level') }}"
```

2. **Opción B - Configuración flexible**: Permitir en config flow especificar entity_ids de sensores:
```yaml
vehicle_status_sensors:
  soc: sensor.tesla_model_3_battery_level
  range: sensor.tesla_model_3_range
  charging_status: sensor.tesla_model_3_charger_state
```

3. **Opción C - Auto-detección**: Buscar todos los sensores del dispositivo del vehículo (device_id) y mostrar los relevantes.

#### H7: Los sensores de EMHASS podría no deberían estar en Vehicle Status
**Probabilidad: MEDIA**

Los sensores EMHASS (`sensor.emhass_perfil_diferible_*`) son sensores de la integración, no del vehículo físico.

**Evidencia**:
- Estos sensores podrían mostrar datos de optimización, no estado físico del vehículo
- Deberían estar en una sección separada "Energy Optimization" o "EMHASS Status"
- La sección Vehicle Status podría mostrar solo datos del vehículo físico

**Nota**: Esto podría ser más una corrección de UX que un bug. La sección actual podría estar vacía porque podría no haber sensores físicos del vehículo configurados, no porque el código esté mal.

### Próximos pasos para investigación

#### Paso 1: Verificar qué sensores están disponibles
1. Abrir el panel y ver qué aparece en "Available Sensors"
2. Anotar los entity_ids de los sensores relevantes
3. Verificar si algunos son sensores externos (Tesla, VW, etc.)

#### Paso X: Posible solución inmediata (workaround)
1. Crear sensores plantilla que mapeen sensores externos al formato `sensor.{vehicle_id}_*`
2. Documentar este proceso en la guía del usuario

#### Paso X: Posible solución a largo plazo
1. Modificar `_getVehicleStates()` para aceptar patrones de sensores configurables
2. Agregar en config flow campos para especificar entity_ids de sensores clave:
   - SOC sensor
   - Range sensor
   - Charging status sensor
   - Consumption sensor
3. Usar estos entity_ids en lugar de depender de prefijos

#### Paso 4: Mejoras de UX adicionales
1. Crear secciones separadas:
   - "Vehicle Status" - para sensores físicos del vehículo
   - "Energy Optimization" - para sensores EMHASS
   - "Trip Data" - para datos de viajes
2. Permitir al usuario personalizar qué secciones mostrar
3. Agregar indicadores visuales cuando no hay datos disponibles (no ocultar la sección)

---

## Resumen Ejecutivo: Vehicle Status Vacío

### Posible Causa Raíz (Hipótesis H4)
**H4**: `_getVehicleStates()` solo filtra sensores que empiezan con `sensor.{vehicle_id}_*`, pero los sensores reales de vehículos (Tesla, VW, etc.) usan sus propios prefijos (`sensor.tesla_*`, `sensor.vwid_*`).

### Flujo Hipotético del Problema
1. Usuario tiene integración Tesla con sensores: `sensor.tesla_model_3_battery_level`, `sensor.tesla_charger_state`
2. `_getVehicleStates()` filtra por `sensor.{vehicle_id}_*` (ej: `sensor.mi_coche_*`)
3. Ningún sensor Tesla pasa el filtro
4. `groupedSensors.status = []`
5. La sección "Vehicle Status" no se renderiza (línea 730: `${statusCards ? html`)

### Pasos para Diagnóstico

#### Preguntas clave para el usuario:
1. **¿Qué integración de vehículo usas?** (Tesla, VW, Nissan, etc.)
2. **¿Qué entity_ids tienen tus sensores de vehículo?**
   - Abrir Developer Tools > States
   - Buscar "battery", "soc", "charging"
   - Anotar los entity_ids completos
3. **¿Qué aparece en "Available Sensors" del panel?**
   - Si está vacío: ningún sensor pasó el filtro
   - Si hay sensores: verificar si son los correctos

#### Prueba de concepto:
```yaml
# Crear sensor plantilla para pruebas
template:
  - sensor:
      - name: "mi_coche_soc"
        unit_of_measurement: "%"
        device_class: battery
        state: "{{ states('sensor.tesla_model_3_battery_level') }}"
```

Si después de crear este sensor aparece en Vehicle Status, esto sugeriría que la hipótesis H4 podría ser correcta.

---

## Matriz de Posibles Soluciones

| Solución | Complejidad | Tiempo | Efectividad |
|----------|-------------|--------|-------------|
| **A. Template sensors (workaround)** | Baja | 5 min | Alta (pero manual) |
| **B. Configuración de entity_ids** | Media | 2-3 horas | Alta |
| **C. Auto-detección por device_id** | Alta | 1-2 días | Muy Alta |

### Posible Recomendación
**Posible solución**: Implementar A inmediatamente (documentación) y B a corto plazo (config flow). Solución C para futuras versiones.

---

## 3. Sección "Available Sensors" muestra mucho ruido y falta visualización del perfil EMHASS

### Problema
La sección "Available Sensors" podría mostrar muchos sensores internos/technical que no son útiles para el usuario final, y el sensor más importante (EMHASS Perfil Diferible) solo muestra "Ready" como estado, sin visualizar el gráfico de potencia que contiene en sus atributos.

**Sensores que aparecen (ejemplo real del usuario):**
- `ev_trip_planner_chispitas_return_info` → 2026.0 (ruido interno)
- `ev_trip_planner_chispitas_2_ev_trip_planner_recurring_trips_count` → 0.0 (contador interno)
- `ev_trip_planner_chispitas_2_ev_trip_planner_punctual_trips_count` → 0.0 (contador interno)
- `ev_trip_planner_chispitas_2_ev_trip_planner_trips_list` → [] (lista interna)
- `ev_trip_planner_chispitas_2_ev_trip_planner_kwh_needed_today` → 0.0 (cálculo interno)
- `ev_trip_planner_chispitas_2_ev_trip_planner_hours_needed_today` → 0.0 (cálculo interno)
- `ev_trip_planner_chispitas_2_ev_trip_planner_next_trip` → N/A (dato interno)
- `ev_trip_planner_chispitas_2_ev_trip_planner_next_deadline` → N/A (dato interno)
- **`ev_trip_planner_chispitas_2_emhass_perfil_diferible_chispitas_2`** → Ready (ESTE ES EL ÚTIL, pero solo muestra "Ready")

### Referencias
- **Código del panel**: [custom_components/ev_trip_planner/frontend/panel.js:742-752](../../custom_components/ev_trip_planner/frontend/panel.js#L742-L752)
- **Sensor EMHASS**: [custom_components/ev_trip_planner/sensor.py:127-202](../../custom_components/ev_trip_planner/sensor.py#L127-L202)
- **Definición de atributos EMHASS**: [sensor.py:176-178](../../custom_components/ev_trip_planner/sensor.py#L176-L178)

### Análisis de la evidencia
1. **Available Sensors** podría mostrar TODOS los sensores que pasan el filtro en `_getVehicleStates()`
2. No hay distinción entre sensores "internos" (technical) y "user-facing"
3. El sensor EMHASS muestra su `native_value` = "emhass_status" = "Ready"
4. Los atributos importantes (`power_profile_watts`) están ocultos

### Datos importantes del sensor EMHASS

**Código del sensor** (línea 164-178):
```python
@property
def native_value(self) -> str:
    """Return sensor value from coordinator.data."""
    if self.coordinator.data is None:
        return "unknown"
    return self.coordinator.data.get("emhass_status", "unknown")

@property
def extra_state_attributes(self) -> Dict[str, Any]:
    """Return extra state attributes from coordinator.data."""
    if self.coordinator.data is None:
        return {}
    return {
        "power_profile_watts": self.coordinator.data.get("emhass_power_profile"),
        "deferrables_schedule": self.coordinator.data.get("emhass_deferrables_schedule"),
        "emhass_status": self.coordinator.data.get("emhass_status"),
    }
```

**Lo que contiene el sensor:**
| Campo | Descripción | Valor ejemplo |
|-------|-------------|---------------|
| `native_value` | Estado del sistema EMHASS | "Ready", "Active", "Idle" |
| `power_profile_watts` | **Array de 168 valores** (7 días × 24 horas) de potencia en watts | `[0, 0, 0, 1200, 2400, 2400, ...]` |
| `deferrables_schedule` | Calendario de cargas diferibles | `{...}` |
| `emhass_status` | Estado (repetido en atributos) | "Ready" |

**Posible problema**:  El panel solo muestra "Ready", pero el valor útil es el gráfico de `power_profile_watts`.

### Hipótesis

#### H1: No hay filtro para sensores internos vs user-facing
**Probabilidad: ALTA**

El panel podría mostrar TODOS los sensores sin distinción de categoría o utilidad para el usuario.

**Evidencia**:
- `_getVehicleStates()` devuelve todos los sensores que coinciden con los patrones
- No hay filtrado por `entity_category` (diagnostic vs config)
- Los sensores con `EntityCategory.DIAGNOSTIC` se marcan en línea 83 de sensor.py, pero el panel no los filtra

**Código relevante** (sensor.py:83):
```python
self._attr_entity_category = EntityCategory.DIAGNOSTIC
```

**El panel podría**: 
1. Ocultar sensores con `entity_category = diagnostic`
2. O agruparlos en una sección "Debug/Technical"
3. O permitir al usuario elegir qué ver

#### H2: Falta visualización de gráficos para el perfil EMHASS
**Probabilidad: MUY ALTA - Esta es la causa principal**

El sensor EMHASS contiene datos valiosos (`power_profile_watts`) pero el panel no los visualiza.

**Evidencia**:
- El panel muestra el `native_value` ("Ready") que no es útil
- Los atributos con el array de 168 valores están disponibles pero ocultos
- No hay componente de gráfico en el panel

**Qué podría mostrar**: 
- Eje X: 168 horas (horizonte de planificación, típicamente 7 días)
- Eje Y: 0 a potencia máxima de carga (en kW o W)
- Gráfico de barras o líneas mostrando el perfil de carga

#### H3: Falta una sección dedicada para EMHASS
**Probabilidad: ALTA**

El sensor EMHASS está mezclado con otros sensores en "Available Sensors" cuando merece una sección propia.

**Propuesta de secciones**:
1. **Vehicle Status** - Estado físico del vehículo (SOC, rango, etc.)
2. **Energy Optimization** - Perfil EMHASS con gráfico
3. **Scheduled Trips** - Viajes programados (ya existe)
4. **Technical Sensors** - Sensores internos (ocultos por defecto)

#### H4: Sensores internos podrían estar ocultos por defecto
**Probabilidad: ALTA**

Sensores como `*_trips_count`, `*_trips_list`, `*_kwh_needed_today`, etc. son internos y no aportan valor al usuario final.

**Categorías de sensores**:
| Tipo | Entity Category | ¿Mostrar al usuario? |
|------|-----------------|---------------------|
| `emhass_perfil_diferible_*` | None | **SÍ** - con gráfico |
| Viajes programados | None | **SÍ** - ya se muestran |
| `*_trips_count` | Diagnostic | NO - interno |
| `*_trips_list` | Diagnostic | NO - interno |
| `*_kwh_needed_today` | Diagnostic | NO - interno (o opcional) |
| `*_hours_needed_today` | Diagnostic | NO - interno (o opcional) |
| `*_next_trip` | Diagnostic | NO - interno (o opcional) |
| `*_next_deadline` | Diagnostic | NO - interno (o opcional) |

### Próximos pasos para investigación

#### Paso X: Posible solución inmediata - Filtrar sensores internos
```javascript
// En _groupSensors(), agregar filtro
if (lowerName.includes('count') || 
    lowerName.includes('list') ||
    lowerName.includes('needed') ||
    lowerName.includes('next_trip') ||
    lowerName.includes('next_deadline') ||
    lowerName.includes('return_info')) {
  continue; // Skip internal sensors
}
```

#### Paso X: Posible solución a corto plazo - Sección EMHASS con gráfico
1. Crear sección "Energy Optimization" antes de "Available Sensors"
2. Usar Chart.js para visualizar `power_profile_watts`
3. Mostrar gráfico de barras con eje X (168 horas) y eje Y (potencia en W)

---

## Resumen de 3 Problemas con Hipótesis de Causas y Soluciones

| # | Problema | Posible Causa | Solución Inmediata | Solución Largo Plazo |
|---|----------|-----------|-------------------|---------------------|
| 1 | Sidebar no se elimina | Falta `async_unregister_panel` en `async_remove_entry_cleanup` | Agregar llamada en services.py:1495 | Revisar arquitectura de cleanup |
| 2 | Vehicle Status vacío | `_getVehicleStates()` filtra por `sensor.{vehicle_id}_*` | Template sensors como workaround | Configuración de entity_ids |
| 3 | Available Sensors con ruido | Sin filtro de sensores internos | Filtrar por patrón de nombre | Secciones configurables |
| 3b | EMHASS sin gráfico | Solo muestra `native_value` ("Ready") | Sección dedicada con Chart.js | Arquitectura de visualizaciones |

### Matriz de prioridades

| Problema | Impacto Usuario | Complejidad | Prioridad |
|----------|-----------------|-------------|-----------|
| #1 Sidebar bug | Media (requiere reinicio) | Baja (1 línea) | **P1 - Alta** |
| #2 Vehicle Status vacío | Alta (no ve estado del coche) | Media (config flow) | **P1 - Alta** |
| #3 Ruido en sensores | Media (info sobrecargada) | Baja (filtro JS) | **P2 - Media** |
| #3b EMHASS sin gráfico | Alta (no ve planificación) | Media (Chart.js) | **P1 - Alta** |

### Roadmap Sugerido (Sujeto a Validación de Hipótesis)

**Sprint 1 (Quick Wins - 1 semana):**
1. Fix #1: Agregar `async_unregister_panel` en `async_remove_entry_cleanup`
2. Fix #3: Filtrar sensores internos en el panel
3. Documentar workaround para #2 (template sensors)

**Sprint 2 (Visualizaciones - 2 semanas):**
1. Fix #3b: Implementar gráfico EMHASS con Chart.js
2. Crear sección "Energy Optimization" dedicada
3. Documentar configuración de sensores de vehículo

**Sprint 3 (Arquitectura - 1 mes):**
1. Fix #2 completo: Configuración de entity_ids en config flow
2. Sistema de secciones configurables
3. Modo debug para sensores técnicos

---

## 4. El flujo de opciones (options flow) solo permite editar 4 campos

### Problema
Cuando el usuario crea una integración y se equivoca al elegir un sensor (por ejemplo, el SOC sensor), al ir a "Configuración > Integraciones > EV Trip Planner > Editar", SOLO puede editar 4 campos:
- `battery_capacity_kwh`
- `charging_power_kw`
- `kwh_per_km`
- `safety_margin_percent`

Pero podría NO poder editar:
- `soc_sensor` (el sensor que eligió mal)
- `charging_sensor`
- `home_sensor`
- `plugged_sensor`
- `planning_sensor`
- Notificaciones
- Configuración EMHASS

Esto obliga al usuario a eliminar y recrear toda la integración para corregir un error en un sensor.

### Referencias
- **Config flow original**: [custom_components/ev_trip_planner/config_flow.py:251-876](../../custom_components/ev_trip_planner/config_flow.py#L251-L876)
- **Options flow limitado**: [custom_components/ev_trip_planner/config_flow.py:887-951](../../custom_components/ev_trip_planner/config_flow.py#L887-L951)

### Análisis de la evidencia

**Config flow original (5 pasos con 20+ campos):**

| Paso | Campos | Descripción |
|------|--------|-------------|
| 1. `user` | `vehicle_name` | Nombre del vehículo |
| 2. `sensors` | `battery_capacity`, `charging_power`, `consumption`, `safety_margin`, **`soc_sensor`** | Configuración básica + **SOC sensor** |
| 3. `emhass` | `planning_horizon`, `max_deferrable_loads`, `index_cooldown_hours`, `planning_sensor` | Configuración EMHASS |
| 4. `presence` | **`charging_sensor`**, **`home_sensor`**, **`plugged_sensor`** | Sensores de presencia |
| 5. `notifications` | `notification_service`, `notification_devices` | Configuración de notificaciones |

**Options flow (1 paso con solo 4 campos):**

```python
async_step_init(self, user_input: Optional[Dict[str, Any]] = None):
    # Solo muestra estos 4 campos: (podría ser)
    return self.async_show_form(
        step_id="init",
        data_schema=vol.Schema({
            vol.Required(CONF_BATTERY_CAPACITY, ...): vol.Coerce(float),
            vol.Required(CONF_CHARGING_POWER, ...): vol.Coerce(float),
            vol.Required(CONF_CONSUMPTION, ...): vol.Coerce(float),
            vol.Required(CONF_SAFETY_MARGIN, ...): vol.Coerce(int),
            # ❌ Falta soc_sensor
            # ❌ Falta charging_sensor
            # ❌ Falta home_sensor
            # ❌ Falta plugged_sensor
            # ❌ Falta planning_sensor
            # ❌ Falta notificaciones
            # ❌ Falta configuración EMHASS
        })
    )
```

### Hipótesis

#### H1: El options flow está intencionalmente limitado
**Probabilidad: MEDIA**

Puede ser una decisión de diseño para evitar que el usuario rompa la configuración cambiando sensores críticos.

**Evidencia en contra**:
- Los sensores críticos (`soc_sensor`, `charging_sensor`) son MANDATORIOS para el funcionamiento
- Si el usuario se equivoca al crearlos, podría NO haber forma de corregirlo sin borrar todo
- Esto podría ser una mala experiencia de usuario

**Si esto fue intencional**: Debería haber un mecanismo alternativo para corregir sensores, como:
- Un botón "Reconfigurar sensores" que dispara el config flow original
- O permitir editar todos los campos con una advertencia

#### H2: El options flow está incompleto (bug)
**Probabilidad: ALTA - Esta es la causa más probable**

El options flow se creó como una versión simplificada del config flow, pero se olvidó incluir los campos de sensores.

**Evidencia**:
- El options flow (líneas 887-951) solo tiene 64 líneas
- El config flow original tiene 625 líneas
- La proporción de campos es 4/20 = 20% - muy inconsistente

**Comparación de código**:
```python
# Config flow: 5 pasos completos (líneas 275-876)
async_step_user()      → vehicle_name
async_step_sensors()   → battery, charging, consumption, safety, soc_sensor
async_step_emhass()    → planning_horizon, max_loads, planning_sensor
async_step_presence()  → charging_sensor, home_sensor, plugged_sensor
async_step_notifications() → notification_service, notification_devices

# Options flow: 1 paso simplificado (líneas 894-951)
async_step_init()      → battery, charging, consumption, safety (SOLO estos 4)
```

#### H3: Falta un método `async_step_reconfigure` en options flow
**Probabilidad: ALTA**

Home Assistant permite que los options flows tengan múltiples pasos, pero este solo implementa `async_step_init`.

**Evidencia**:
- El options flow podría tener pasos como: `init`, `sensors`, `emhass`, `presence`, `notifications`
- Actualmente solo tiene `init` con 4 campos

**Posible solución**: Implementar un options flow multi-paso que permita editar todos los campos.

### Código del problema

**Líneas 887-951 (Options flow actual)**:
```python
class EVTripPlannerOptionsFlowHandler(config_entries.OptionsFlow):
    """Maneja las opciones de configuración para EV Trip Planner."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Paso inicial del flujo de opciones."""
        if user_input is not None:
            update_data = {}
            if CONF_BATTERY_CAPACITY in user_input:
                update_data[CONF_BATTERY_CAPACITY] = user_input[CONF_BATTERY_CAPACITY]
            # ... solo 4 campos

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                # ❌ Solo 4 campos de 20+ posibles
                vol.Required(CONF_BATTERY_CAPACITY, ...): vol.Coerce(float),
                vol.Required(CONF_CHARGING_POWER, ...): vol.Coerce(float),
                vol.Required(CONF_CONSUMPTION, ...): vol.Coerce(float),
                vol.Required(CONF_SAFETY_MARGIN, ...): vol.Coerce(int),
            })
        )
```

### Próximos pasos para investigación

#### Paso X: Posible solución inmediata - Agregar sensores críticos al options flow
**Prioridad: ALTA** - El usuario podría necesitar corregir errores de sensores

**Cambio mínimo necesario**:
```python
async def async_step_init(self, user_input: Optional[Dict[str, Any]] = None):
    if user_input is not None:
        update_data = {}
        # Campos existentes
        if CONF_BATTERY_CAPACITY in user_input:
            update_data[CONF_BATTERY_CAPACITY] = user_input[CONF_BATTERY_CAPACITY]
        # ... otros campos existentes
        
        # ✅ AGREGAR: Campos de sensores críticos
        if CONF_SOC_SENSOR in user_input:
            update_data[CONF_SOC_SENSOR] = user_input[CONF_SOC_SENSOR]
        if CONF_CHARGING_SENSOR in user_input:
            update_data[CONF_CHARGING_SENSOR] = user_input[CONF_CHARGING_SENSOR]
        if CONF_HOME_SENSOR in user_input:
            update_data[CONF_HOME_SENSOR] = user_input[CONF_HOME_SENSOR]
        if CONF_PLUGGED_SENSOR in user_input:
            update_data[CONF_PLUGGED_SENSOR] = user_input[CONF_PLUGGED_SENSOR]
        
        return self.async_create_entry(title="", data=update_data)
    
    # Leer valores actuales
    config_data = self._config_entry.data or {}
    
    return self.async_show_form(
        step_id="init",
        data_schema=vol.Schema({
            # Campos existentes
            vol.Required(CONF_BATTERY_CAPACITY, ...): vol.Coerce(float),
            vol.Required(CONF_CHARGING_POWER, ...): vol.Coerce(float),
            vol.Required(CONF_CONSUMPTION, ...): vol.Coerce(float),
            vol.Required(CONF_SAFETY_MARGIN, ...): vol.Coerce(int),
            
            # ✅ AGREGAR: Sensores críticos con entity selectors
            vol.Optional(
                CONF_SOC_SENSOR,
                default=config_data.get(CONF_SOC_SENSOR)
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="sensor", multiple=False)
            ),
            vol.Optional(
                CONF_CHARGING_SENSOR,
                default=config_data.get(CONF_CHARGING_SENSOR)
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["binary_sensor", "input_boolean"],
                    multiple=False
                )
            ),
            vol.Optional(
                CONF_HOME_SENSOR,
                default=config_data.get(CONF_HOME_SENSOR)
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["binary_sensor", "input_boolean"],
                    multiple=False
                )
            ),
            vol.Optional(
                CONF_PLUGGED_SENSOR,
                default=config_data.get(CONF_PLUGGED_SENSOR)
            ): selector.EntitySelector(
                selector.EntitySelectorConfig(
                    domain=["binary_sensor", "input_boolean"],
                    multiple=False
                )
            ),
        })
    )
```

#### Paso X: Posible solución a corto plazo - Multi-step options flow
Crear un options flow con múltiples pasos similar al config flow original:

```python
class EVTripPlannerOptionsFlowHandler(config_entries.OptionsFlow):
    """Manejo completo de opciones con múltiples pasos."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry
        self._data = dict(config_entry.data)

    async def async_step_init(self, user_input=None):
        """Paso 1: Opciones básicas."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_sensors()
        
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required(CONF_BATTERY_CAPACITY): vol.Coerce(float),
                vol.Required(CONF_CHARGING_POWER): vol.Coerce(float),
                vol.Required(CONF_CONSUMPTION): vol.Coerce(float),
                vol.Required(CONF_SAFETY_MARGIN): vol.Coerce(int),
            })
        )

    async def async_step_sensors(self, user_input=None):
        """Paso 2: Sensores del vehículo (aquí está soc_sensor)."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_presence()
        
        return self.async_show_form(
            step_id="sensors",
            data_schema=vol.Schema({
                vol.Optional(CONF_SOC_SENSOR): selector.EntitySelector(
                    selector.EntitySelectorConfig(domain="sensor")
                ),
            })
        )

    async def async_step_presence(self, user_input=None):
        """Paso 3: Sensores de presencia."""
        if user_input is not None:
            self._data.update(user_input)
            return await self.async_step_emhass()
        
        return self.async_show_form(
            step_id="presence",
            data_schema=vol.Schema({
                vol.Optional(CONF_CHARGING_SENSOR): selector.EntitySelector(...),
                vol.Optional(CONF_HOME_SENSOR): selector.EntitySelector(...),
                vol.Optional(CONF_PLUGGED_SENSOR): selector.EntitySelector(...),
            })
        )

    async def async_step_emhass(self, user_input=None):
        """Paso 4: Configuración EMHASS."""
        if user_input is not None:
            self._data.update(user_input)
            return self.async_create_entry(title="", data=self._data)
        
        return self.async_show_form(
            step_id="emhass",
            data_schema=vol.Schema({
                vol.Optional(CONF_PLANNING_HORIZON): vol.Coerce(int),
                vol.Optional(CONF_MAX_DEFERRABLE_LOADS): vol.Coerce(int),
                vol.Optional(CONF_PLANNING_SENSOR): selector.EntitySelector(...),
            })
        )
```

#### Paso X: Posible solución alternativa - Botón "Reconfigurar"
Agregar un botón en la UI que dispare el config flow completo:

```python
# En el panel o en services.py, agregar un servicio
async def async_reconfigure_vehicle_service(hass, call):
    """Permite reconfigurar un vehículo existente."""
    vehicle_id = call.data.get("vehicle_id")
    
    # Buscar la config entry
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.data.get(CONF_VEHICLE_NAME, "").lower().replace(" ", "_") == vehicle_id:
            # Iniciar el config flow completo en modo reconfiguración
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": config_entries.SOURCE_RECONFIGURE},
                data={"entry_id": entry.entry_id}
            )
            break
```

---

## Resumen Actualizado: 4 Problemas con Hipótesis

| # | Problema | Posible Causa | Solución Inmediata | Solución Largo Plazo |
|---|----------|-----------|-------------------|---------------------|
| 1 | Sidebar no se elimina | Falta `async_unregister_panel` en cleanup | 1 línea en services.py:1495 | Revisar arquitectura cleanup |
| 2 | Vehicle Status vacío | `_getVehicleStates()` filtra por prefijo incorrecto | Template sensors workaround | Configurar entity_ids |
| 3 | Available Sensors con ruido | Sin filtro de sensores internos | Filtrar por patrón JS | Secciones configurables |
| 3b | EMHASS sin gráfico | Solo muestra "Ready" | Chart.js + sección dedicada | Arquitectura visualizaciones |
| **4** | **Options flow incompleto** | **Solo 4 campos editables de 20+** | **Agregar sensores críticos** | **Multi-step options flow** |

### Matriz de prioridades actualizada

| Problema | Impacto | Urgencia | Complejidad | Prioridad |
|----------|---------|----------|-------------|-----------|
| #1 Sidebar bug | Media | Baja | Baja (1 línea) | **P2** |
| #2 Status vacío | Alta | Media | Media (config) | **P1** |
| #3 Ruido sensores | Media | Baja | Baja (filtro JS) | **P2** |
| #3b EMHASS gráfico | Alta | Media | Media (Chart.js) | **P1** |
| **#4 Options flow** | **ALTA** | **ALTA** | **Baja-Media** | **P0 - CRÍTICA** |

**Problema #4 es P0 porque**:
- El usuario podría NO poder corregir errores sin borrar la integración
- Esto significa perder todos los viajes configurados
- Es una barrera grave para la usabilidad
- **Posible solución**: relativamente simple (agregar entity selectors al options flow)

---

## 5. Cambio de potencia de carga no actualiza el perfil EMHASS

### Problema
Cuando el usuario cambia la `charging_power_kw` en las opciones de la integración (ej: de 11kW a 3.6kW), el sensor de planificación de carga NO se actualiza con el nuevo valor. Incluso después de eliminar y crear nuevos viajes, sigue usando el valor antiguo (11kW) en lugar del nuevo (3.6kW).

**Comportamiento esperado**: Al igual que cuando se actualiza el SOC (que dispara la recalculación), cambiar la potencia de carga debería actualizar el `power_profile_watts`.

### Referencias
- **Listener de config entry**: [custom_components/ev_trip_planner/emhass_adapter.py:1327-1344](../../custom_components/ev_trip_planner/emhass_adapter.py#L1327-L1344)
- **update_charging_power**: [emhass_adapter.py:1346-1380](../../custom_components/ev_trip_planner/emhass_adapter.py#L1346-L1380)
- **publish_deferrable_loads**: [emhass_adapter.py:488-587](../../custom_components/ev_trip_planner/emhass_adapter.py#L488-L587)

### Análisis de la Evidencia (Código Implementado)

**El flujo DEBERÍA ser**:
1. Usuario cambia `charging_power_kw` de 11 a 3.6 en options flow
2. HA dispara `config_entry.add_update_listener`
3. `_handle_config_entry_update` se ejecuta
4. `update_charging_power()` compara nuevo valor con antiguo
5. Si son diferentes, llama a `publish_deferrable_loads(trips, new_power)`
6. `publish_deferrable_loads()` recalcula `power_profile` con nuevo power
7. Coordinator refresh actualiza el sensor EMHASS

**Código implementado** (emhass_adapter.py:1334-1380):
```python
async def _handle_config_entry_update(self, hass, config_entry) -> None:
    """Handle config entry update events."""
    _LOGGER.info("Config entry updated, checking charging power")
    await self.update_charging_power()

async def update_charging_power(self) -> None:
    """Update charging power and republish sensor attributes if changed."""
    entry = self.hass.config_entries.async_get_entry(self.entry_id)
    new_power = entry.data.get("charging_power_kw")
    
    if new_power == self._charging_power_kw:
        return  # Sin cambios
    
    # Update internal power value
    self._charging_power_kw = new_power
    
    # Republish with new charging power
    await self.publish_deferrable_loads(self._published_trips, new_power)
```

### Hipótesis

#### H1: El listener podría no estar registrándose correctamente
**Probabilidad: ALTA**

El listener de config entry puede no estar registrándose en el momento correcto del ciclo de vida.

**Evidencia**:
- El listener se registra en `async_setup()` (línea 1327-1332)
- Pero el EMHASSAdapter puede no estar inicializado cuando se crea la config entry
- O el listener puede estar cayendo en algún punto

**Diagnóstico necesario**:
```python
# Agregar logs en emhass_adapter.py:async_setup()
_LOGGER.info("=== EMHASS adapter setup START ===")
_LOGGER.info("Registering config entry listener for entry_id: %s", self.entry_id)
# ... después de registrar
_LOGGER.info("Config entry listener registered successfully")
```

#### H2: self._published_trips está vacío o desactualizado
**Probabilidad: MUY ALTA**

Cuando se llama `update_charging_power()`, pasa `self._published_trips` a `publish_deferrable_loads()`. Si esta lista está vacía o tiene viajes desactualizados, el power_profile podría calcularse incorrectamente.

**Código del problema** (línea 1380):
```python
await self.publish_deferrable_loads(self._published_trips, new_power)
```

**Evidencia**:
- `self._published_trips` se popula en `publish_deferrable_loads()` línea 539
- Si el listener se dispara antes de que haya viajes, `_published_trips` está vacío
- El power_profile se calcula con una lista vacía = todos ceros

**Diagnóstico necesario**:
```python
# Agregar en update_charging_power() antes de línea 1380:
_LOGGER.info(
    "Republishing %d cached trips with new power %s kW",
    len(self._published_trips) if self._published_trips else 0,
    new_power
)
```

#### H3: El coordinator refresh no está propagando los cambios
**Probabilidad: MEDIA**

`publish_deferrable_loads()` llama a `coordinator.async_refresh()` (línea 574), pero puede que el refresh no esté actualizando los atributos del sensor.

**Evidencia**:
- El power_profile se cachea en `self._cached_power_profile` (línea 560)
- El coordinator lee desde `coordinator.data` (sensor.py línea 106)
- Si el coordinator refresh no recupera el cache actualizado, el sensor mantiene el valor viejo

**Diagnóstico necesario**:
```python
# Agregar después de coordinator.async_refresh():
_LOGGER.info(
    "Coordinator refresh completed, cached power_profile length: %d",
    len(self._cached_power_profile) if self._cached_power_profile else 0
)
```

#### H4: El power_profile podría calcularse correctamente pero no mostrarse en la UI
**Probabilidad: BAJA**

El problema puede ser que el sensor tiene los datos correctos pero el panel no los está mostrando.

**Evidencia en contra**:
- El usuario dice que revisó el "sensor de planificación de carga" y sigue con 11kW
- Esto sugiere que el problema está en los datos, no en la visualización

#### H5: El listener de config entry usa entry.data incorrecto
**Probabilidad: MEDIA**

Cuando el usuario cambia opciones en HA, los cambios pueden ir a `options` en lugar de `data`.

**Evidencia**:
- El código busca `entry.data.get("charging_power_kw")` (línea 1359)
- Pero en options flow, los cambios se guardan en `entry.options` o se mezclan con `data`
- Si el nuevo valor está en `options` pero no en `data`, el listener no lo ve

**Código problemático**:
```python
# Línea 1359
new_power = entry.data.get("charging_power_kw")  # ❌ Debería verificar también entry.options
```

**Posible solución**:
```python
new_power = entry.data.get("charging_power_kw") or entry.options.get("charging_power_kw")
```

### Próximos pasos para investigación

#### Paso 1: Verificar logs cuando cambias la potencia
1. Abrir logs de Home Assistant (Configuration > Logs)
2. Cambiar `charging_power_kw` de 11 a 3.6
3. Buscar estos mensajes:
   - `"Config entry updated, checking charging power"`
   - `"Charging power changed from X to Y kW"`
   - `"Publishing N deferrable loads"`
   - `"Triggered coordinator refresh"`

**Si NO ves estos mensajes**: El listener no se está ejecutando (H1 o H5)
**Si SÍ ves estos mensajes**: **Posible problema**: en otra parte (H2 o H3)

#### Paso X: Posible solución inmediata - Fix H5 (entry.options vs entry.data)
**Prioridad: ALTA**

Modificar `update_charging_power()` para leer de ambos:

```python
async def update_charging_power(self) -> None:
    entry = self.hass.config_entries.async_get_entry(self.entry_id)
    if not entry:
        return
    
    # ✅ FIX: Leer de data y options
    new_power = entry.data.get("charging_power_kw") or entry.options.get("charging_power_kw")
    if new_power is None:
        _LOGGER.warning("charging_power_kw not found in data or options")
        return
    
    if new_power == self._charging_power_kw:
        return
    
    _LOGGER.info("Charging power changed from %s to %s kW", self._charging_power_kw, new_power)
    self._charging_power_kw = new_power
    
    # ✅ FIX: Recargar viajes desde trip_manager en lugar de usar cache
    trip_manager = self._get_trip_manager()
    if trip_manager:
        all_trips = await trip_manager._get_all_active_trips()
        await self.publish_deferrable_loads(all_trips, new_power)
    else:
        await self.publish_deferrable_loads(self._published_trips, new_power)
```

#### Paso X: Posible solución a corto plazo - Servicio manual de recalculo
Agregar un servicio que permite forzar la recalculación:

```python
# En services.py
@SERVICE_SCHEMA.schema("ev_trip_planner.recalculate_profile")
async def async_service_recalculate_profile(service_call: ServiceCall) -> None:
    """Fuerza la recalculación del perfil de carga con la configuración actual."""
    entry_id = service_call.data.get("entry_id")
    
    # Buscar el EMHASSAdapter para este entry_id
    # Llamar a update_charging_power() para forzar recalculo
```

#### Paso 4: Verificar que _published_trips no esté vacío
Agregar validación:

```python
async def update_charging_power(self) -> None:
    # ... código existente ...
    
    # ✅ VALIDAR: Si no hay viajes cacheados, recargarlos
    if not self._published_trips:
        _LOGGER.warning(
            "No cached trips found, reloading from trip_manager before republishing"
        )
        trip_manager = self._get_trip_manager()
        if trip_manager:
            all_trips = await trip_manager._get_all_active_trips()
            self._published_trips = all_trips
    
    await self.publish_deferrable_loads(self._published_trips, new_power)
```

---

## Resumen Actualizado: 5 Problemas con Hipótesis

| # | Problema | Posible Causa | Solución Inmediata | Prioridad |
|---|----------|---------------------|-------------------|-----------|
| 1 | Sidebar no se elimina | Falta unregister en cleanup | 1 línea en services.py | P2 |
| 2 | Vehicle Status vacío | Filtra por prefijo incorrecto | Template sensors | P1 |
| 3 | Available Sensors con ruido | Sin filtro de sensores internos | Filtrar por patrón JS | P2 |
| 3b | EMHASS sin gráfico | Solo muestra "Ready" | Chart.js + sección | P1 |
| 4 | Options flow incompleto | Solo 4 campos editables | Agregar sensores críticos | **P0** |
| **5** | **Potencia no actualiza** | **entry.options vs entry.data** | **Leer de ambos + recargar viajes** | **P0 - CRÍTICA** |

**Problema #5 es P0 CRÍTICA porque**:
- Podría romper la funcionalidad principal (planificación de carga)
- El usuario podría NO poder usar la configuración correcta sin workaround complejo
- Afecta directamente la optimización de energía
- Puede causar problemas reales (cargar a 11kW cuando solo soporta 3.6kW)

---

## 6. Diseño visual del panel: colores contrastantes y fatiga visual

### Problema
El panel actual tiene un diseño visual poco armonioso con gradientes de colores muy intensos que causan fatiga visual y dificultan la lectura prolongada.

**Problemas específicos posibles**:
- Gradiente púrpura/azul saturado (#667eea → #764ba2) en el header
- Alto contraste entre elementos que cansa la vista
- Falta de coherencia en la paleta de colores
- Sobrecarga visual con múltiples colores brillantes
- Tipografía y espaciado podrían ser mejorables

### Referencias
- **Estilos hardcodeados en JS**: [custom_components/ev_trip_planner/frontend/panel.js:55-106](../../custom_components/ev_trip_planner/frontend/panel.js#L55-L106)
- **Variables CSS no usadas**: [custom_components/ev_trip_planner/frontend/panel.css:12-34](../../custom_components/ev_trip_planner/frontend/panel.css#L12-L34)
- **Estilos del panel**: [panel.css:44-100](../../custom_components/ev_trip_planner/frontend/panel.css#L44-L100)

### Análisis visual actual

**Problemas de paleta de colores:**

| Elemento | Color Actual | Problema |
|----------|-------------|----------|
| Header gradiente | `#667eea` → `#764ba2` | Sobresaturado, fatiga visual |
| Botón "Agregar" | Mismo gradiente | No hay distinción visual del header |
| Trip type | `#667eea` (azul púrpura) | Demasiado brillante |
| Status "active" | `#10b981` (verde) | Bien, pero puede saturar |
| Status "inactive" | `#ef4444` (rojo) | Alto contraste, molesto |

**Problemas de diseño posibles**:

1. **Gradient sobresaturado**: El púrpura #667eea tiene una saturación del 87% y luminosidad del 60%, lo que crea fatiga visual rápida
2. **Falta de jerarquía visual**: Header y botón usan los mismos colores, no hay distinción
3. **CSS variables definidas pero no usadas**: El archivo panel.css define variables (--panel-primary-color, etc.) pero el JS las ignora
4. **Sobrecarga de shadows**: Múltiples elementos con `box-shadow` crean ruido visual
5. **Contraste excesivo**: Texto blanco sobre gradientes oscuros puede ser difícil de leer

### Propuesta de rediseño: Paleta de colores moderna

**Nueva paleta basada en Material Design 3 y principios de accesibilidad:**

```css
/* Variables CSS actualizadas - tonos más suaves y accesibles */
:root {
  /* Primary: Tonos azules suaves en lugar de púrpura saturado */
  --evtp-primary: #3b82f6;        /* Azul Material - saturación 94% */
  --evtp-primary-light: #60a5fa; /* Azul claro - saturación 91% */
  --evtp-primary-dark: #2563eb;  /* Azul oscuro - saturación 89% */
  --evtp-primary-bg: #eff6ff;    /* Fondo muy suave */
  
  /* Secondary: Tonos verdes amigables */
  --evtp-success: #22c55e;       /* Verde esmeralda */
  --evtp-success-bg: #dcfce7;    /* Verde fondo suave */
  
  /* Semantic: Estados con colores accesibles */
  --evtp-warning: #f59e0b;       /* Ambar - más cálido que naranja */
  --evtp-warning-bg: #fef3c7;
  --evtp-error: #ef4444;         /* Rojo mantenido */
  --evtp-error-bg: #fee2e2;
  
  /* Neutral: Tonos grises armoniosos */
  --evtp-bg-primary: #ffffff;
  --evtp-bg-secondary: #f8fafc;  /* Gris azulado muy suave */
  --evtp-bg-tertiary: #f1f5f9;   /* Gris azulado medio */
  --evtp-text-primary: #0f172a;  /* Slate 900 */
  --evtp-text-secondary: #64748b; /* Slate 500 */
  --evtp-text-muted: #94a3b8;    /* Slate 400 */
  
  /* Borders y separadores */
  --evtp-border: #e2e8f0;        /* Slate 200 */
  --evtp-divider: #cbd5e1;       /* Slate 300 */
}
```

**Comparación visual:**

```
ANTES (Fatiga visual):
Header: ████████████████████████ #667eea→#764ba2 (gradiente saturado)
Botón: ████████████████████████ Mismo gradiente

DESPUÉS (Armonioso):
Header: ░░░░░░░░░░▓▓▓░░░░░░░░░░░░░ #3b82f6 sólido con sutil gradiente
Botón: ▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░░ #3b82f6 con hover #60a5fa
```

### Propuesta de rediseño: Layout y espaciado

**Problemas actuales:**
1. Header ocupa demasiado espacio visual
2. Espaciado inconsistente entre secciones
3. Falta de呼吸空间 (breathing room)
4. Cards con border-radius excesivo (12px) que se veño "cartoon"

**Propuesta de mejora:**

```css
/* Header más compacto y profesional */
.panel-header {
  background: var(--evtp-primary);
  color: white;
  padding: 12px 20px;  /* Reducido de 20px */
  border-radius: 8px 8px 0 0;  /* Solo bordes superiores redondeados */
  margin-bottom: 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);  /* Más sutil */
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.panel-header h1 {
  margin: 0;
  font-size: 18px;  /* Reducido de 24px */
  font-weight: 500;  /* Menos bold */
}

/* Cards más refinadas */
.trip-card {
  background: var(--evtp-bg-primary);
  border: 1px solid var(--evtp-border);  /* Borde sutil en lugar de shadow */
  border-radius: 6px;  /* Menos redondo, más profesional */
  padding: 16px;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.trip-card:hover {
  border-color: var(--evtp-primary-light);
  box-shadow: 0 2px 8px rgba(59, 130, 246, 0.08);  /* Shadow con color de品牌 */
}

/* Botones más accesibles */
.add-trip-btn {
  background: var(--evtp-primary);
  color: white;
  border: none;
  padding: 8px 16px;  /* Ligeramente más compacto */
  border-radius: 6px;
  font-size: 14px;
  font-weight: 500;  /* Regular en lugar de 600 */
  transition: background 0.2s;
}

.add-trip-btn:hover {
  background: var(--evtp-primary-dark);
  transform: none;  /* Eliminar translateY, causa motion sickness */
}

.add-trip-btn:focus-visible {
  outline: 2px solid var(--evtp-primary-light);
  outline-offset: 2px;
}
```

### Propuesta de rediseño: Modo oscuro/claro

**Agregar soporte para theme awareness:**

```css
/* Detectar tema de HA */
:host([data-theme="dark"]) {
  --evtp-bg-primary: #1e293b;  /* Slate 800 */
  --evtp-bg-secondary: #0f172a; /* Slate 900 */
  --evtp-text-primary: #f1f5f9;
  --evtp-text-secondary: #cbd5e1;
  --evtp-border: #334155;
}

/* Panel header adaptativo */
.panel-header {
  background: var(--evtp-primary);
  color: white;
}

/* En modo oscuro, usar gradiente más suave */
:host([data-theme="dark"]) .panel-header {
  background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%);
}
```

### Propuesta de rediseño: Tipografía

**Problemas actuales:**
1. Tamaños de fuente inconsistentes
2. Peso de fuente demasiado bold (600)
3. Falta de jerarquía tipográfica

**Propuesta:**

```css
/* Escala tipográfica coherente */
.panel-container {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  font-size: 14px;  /* Base size */
  line-height: 1.5;
}

.panel-header h1 {
  font-size: 18px;      /* H1: 18px */
  font-weight: 600;
  letter-spacing: -0.01em;
}

.section-title {
  font-size: 14px;      /* H2 equivalente */
  font-weight: 600;
  text-transform: uppercase;  /* Para distinción visual */
  letter-spacing: 0.05em;  /* Ligero espaciado */
  color: var(--evtp-text-secondary);
}

.trip-type {
  font-size: 13px;      /* Labels */
  font-weight: 500;
  color: var(--evtp-primary);
}

.trip-time, .trip-details {
  font-size: 13px;      /* Body text */
  font-weight: 400;
  color: var(--evtp-text-secondary);
}
```

### Hipótesis sobre por qué el diseño actual es problemático

#### H1: Gradiente hardcodeado ignora CSS variables
**Probabilidad: ALTA**

El código JS hardcodea el gradiente en línea 56-57, ignorando las variables CSS definidas en panel.css.

**Evidencia**:
```javascript
// panel.js línea 56 (MAL)
background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

// Debería usar:
background: var(--evtp-primary);
```

#### H2: Falta de diseño sistemático
**Probabilidad: ALTA**

No hay un design system coherente. Los colores se eligieron individualmente sin considerar:

- Contraste (WCAG AA requiere 4.5:1 mínimo)
- Armonía (colores complementarios vs análogos)
- Accesibilidad (daltónicos, protanopía)
- Contexto (uso en diferentes iluminaciones)

#### H3: Sobrecarga de efectos visuales
**Probabilidad: MEDIA**

Demasiados efectos simultáneos:
- Gradientes + shadows + transforms + transitions
- Esto crea "ruido visual" y distrae del contenido

### Próximos pasos para el rediseño

#### Paso X: Posible solución inmediata - Usar CSS variables
**Prioridad: ALTA - Quick win**

Reemplazar gradientes hardcodeados por variables CSS:

```javascript
// panel.js línea 56-57 (ANTES)
.panel-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

// DESPUÉS
.panel-header {
  background: var(--evtp-primary, #3b82f6);
}
```

#### Paso X: Posible solución a corto plazo - Paleta accesible
**Prioridad: ALTA**

Implementar nueva paleta con mejores contrastes y menos fatiga:

1. Reemplazar #667eea/#764ba2 por #3b82f6 (azul Material)
2. Añadir soporte para dark/light mode
3. Mejorar espaciado y proporciones
4. Añadir focus-visible para accesibilidad

#### Paso X: Posible solución a largo plazo - Design system completo
Crear un design system documentado con:

1. **Paleta de colores** con tokens semánticos:
   - Primary (brand color)
   - Success/Warning/Error
   - Background layers
   - Text hierarchy

2. **Escalas de espaciado**:
   - Spacing tokens (4px, 8px, 16px, 24px, 32px)
   - Consistentes en todo el panel

3. **Tipografía**:
   - Font scale (12, 13, 14, 16, 18, 20px)
   - Font weights (400, 500, 600, 700)

4. **Componentes**:
   - Button variants (primary, secondary, ghost)
   - Card variants (default, elevated, outlined)
   - Badge/status indicators

---

---

## 7. Documentación: Configurar el sensor EMHASS como carga diferible en EMHASS

### Objetivo
Documentar la notación jinja/yaml necesaria para que el sensor `sensor.emhass_perfil_diferible_{vehicle_id}` se configure automáticamente como una carga diferible en EMHASS.

**IMPORTANTE**: EMHASS es un proyecto externo [github.com/davidusb-geek/emhass](https://github.com/davidusb-geek/emhass) que optimiza el consumo energético usando MPC (Model Predictive Control). Nuestra integración publica los requisitos de carga y EMHASS responde con el horario optimizado.

### Referencias
- **Documentación EMHASS**: [README.md oficial](https://github.com/davidusb-geek/emhass)
- **Patrones de integración**: [specs/_epics/emhass-deferrable-integration/.research-emhass-patterns.md](../../specs/_epics/emhass-deferrable-integration/.research-emhass-patterns.md)
- **Parámetros EMHASS**: Líneas 40-101 del research document

### Parámetros EMHASS para cargas diferibles

#### Formato general
EMHASS usa arrays donde cada posición corresponde a una carga diferible:

```yaml
# Parámetros de entrada para EMHASS
def_total_hours: [5.56, 8.3]          # Horas totales de carga para cada carga
P_deferrable_nom: [3600, 2200]      # Potencia nominal en Watts de cada carga
def_start_timestep: [0, 20]          # Hora de inicio de ventana (0 = ASAP)
def_end_timestep: [24, 44]            # Hora máxima de carga (deadline)
```

**Regla CRÍTICA**: La posición del array debe ser COHERENTE en todos los parámetros.
- Posición 0: Primera carga diferible
- Posición 1: Segunda carga diferible
- etc.

#### Explicación de cada parámetro

**1. `def_total_hours` - Horas totales de encendido**
```yaml
def_total_hours: [5.56]  # Una carga que necesita 5.56 horas a potencia nominal
```
- **Unidades**: Horas (float)
- **Cálculo**: `energía_necesaria_kwh / P_deferrable_nom_W * 1000`
- **Ejemplo**: 20kWh / 3600W * 1000 = 5.56 horas

**2. `P_deferrable_nom` - Potencia nominal máxima**
```yaml
# Versión hardcodeada (NO recomendado)
P_deferrable_nom: [3600, 3600]  # Dos cargas de 3.6kW cada

# Versión con variables jinja (RECOMENDADO)
P_deferrable_nom: 
  - {{ potencia_carga_diferible_1 }}  # Sensor o variable HA
  - {{ potencia_carga_diferible_2 }}
```
- **Unidades**: Watts (entero o float)
- **Descripción**: Potencia máxima del cargador del vehículo
- **Ejemplo**: 3600W = 3.6kW, 2200W = 2.2kW

**3. `def_start_timestep` - Inicio de ventana de carga**
```yaml
def_start_timestep: [20, 0]  
# Carga 1: Puede empezar desde hora 20 (8 PM)
# Carga 2: Puede empezar desde hora 0 (ASAP)
```
- **Unidades**: Índice de hora (0-167 para horizonte de 7 días)
- **0**: ASAP (lo antes posible)
- **>0**: Hora específica del horizonte
- **Ejemplo práctico**: 
  - Horizonte: 168 horas (7 días × 24 horas)
  - `[20, 0]` = Carga 1 desde hora 20, Carga 2 desde hora 0

**4. `def_end_timestep` - Fin de ventana de carga**
```yaml
def_end_timestep: [44, 24]
# Carga 1: Máximo hasta hora 44 (hora 44 del horizonte)
# Carga 2: Máximo hasta hora 24
```
- **Unidades**: Índice de hora (0-167)
- **Significado**: Deadline máximo para completar la carga
- **Ejemplo**: 
  - Viaje sale a hora 44 = Carga debe completar antes
  - `[44, 24]` = Carga 1 deadline 44, Carga 2 deadline 24

**5. `P_deferrable` - Pronóstico/sugerencia de carga**
```yaml
# Array de 168 valores (7 días × 24 horas) que EMHASS optimiza
P_deferrable: 
  - 0.0
  - 0.0
  - 3600.0
  - 3600.0
  - ...
```
- **Unidades**: Watts
- **Longitud**: 168 valores (horizonte típico de EMHASS)
- **Coordina con sensores**: Debe estar sincronizado con `power_profile_watts` de nuestro sensor

### Ejemplo completo de configuración

#### Escenario: Un vehículo con dos cargas programadas

**Configuración EMHASS (configuration.yaml):**

```yaml
# EMHASS configuration.yaml
optimization:
  # Número de cargas diferibles (debe coincidir con length de arrays)
  number_of_deferrable_loads: 2
  
  # Parámetros de entrada (se actualizan vía sensor)
  # Nota: EMHASS espera estos como atributos de sensor.emhass_deferrable_load_config_0
  
  # Carga diferible 1: Viaje nocturno de lunes a martes
  # - 20 kWh necesarios
  # - Potencia: 3.6kW
  # - Ventana: Desde las 20:00 hasta las 02:00
  # - Horas totales: 20 / 3.6 = 5.56 horas
  treat_deferrable_load_as_semi_cont: [true]
  
  # Carga diferible 2: Viaje matutino de martes
  # - 15 kWh necesarios
  # - Potencia: 2.2kW (cargador más lento)
  # - Ventana: ASAP hasta las 10:00
  # - Horas totales: 15 / 2.2 = 6.82 horas
```

**Nuestro sensor podría proporcionar estos datos:**

```yaml
# Atributos de sensor.emhass_perfil_diferible_coche1
power_profile_watts: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3600, 3600, 3600, 3600, ...]
#                     ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#                     Horas 0-19            Hora 20               Horas 21-23

# EMHASS leerá esto y optimizará:
P_deferrable: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3600, 3600, 3600, 3600, ...]
#                                                                                                                                    ^^^^^^^^^^^^^^^^^^^^
#                                                                                                                    EMHASS optimiza estos valores

def_total_hours: [5.56, 6.82]     # Calculado desde viajes
P_deferrable_nom: [3600, 2200]     # Desde config entry (charging_power_kw)
def_start_timestep: [20, 0]         # Desde hora_regreso + deadline
def_end_timestep: [44, 24]           # Desde deadline de cada viaje
```

### Guía paso a paso para el usuario

#### Paso 1: Instalar EMHASS
```bash
# En Home Assistant Supervisor > Add-Ons > Add-On Store
# Buscar "EMHASS" e instalar
# O vía HACS
```

#### Paso 2: Configurar EMHASS para leer nuestro sensor

**Opción A - Usar sensores EMHASS (RECOMENDADO):**

```yaml
# configuration.yaml de EMHASS
optimization:
  number_of_deferrable_loads: 1
  
  # Usar plantilla para leer nuestro sensor
  template:
    - sensor:
        - entity_id: sensor.ev_trip_planner_mi_coche_emhass_perfil_diferible_mi_coche
      attributes:
        - attribute: power_profile_watts
          name: p_deferrable
```

**Opción B - Usar lambda (más flexible):**

```yaml
# configuration.yaml de EMHASS
deferrable_loads:
  - name: "Carga Vehículo Mi Coche"
    p_deferrable_nom: "{{ states('sensor.ev_trip_planner_mi_coche_charging_power_kw') | float(0) * 1000 }}"
    def_total_hours: "{{ states('sensor.ev_trip_planner_mi_coche_emhass_perfil_diferible_mi_coche') | state_attr('power_profile_watts') | sum / (states('sensor.ev_trip_planner_mi_coche_charging_power_kw') | float(0) * 1000) }}"
    def_start_timestep: "{{ states('sensor.ev_trip_planner_mi_coche_emhass_perfil_diferible_mi_coche') | state_attr('def_start_timestep') | first }}"
    def_end_timestep: "{{ states('sensor.ev_trip_planner_mi_coche_emhass_perfil_diferible_mi_coche') | state_attr('def_end_timestep') | last }}"
```

### Validación - Verificar que EMHASS reconoce la carga

#### Logs que indican éxito:
```
EMHASS: Loaded 1 deferrable load(s)
EMHASS: Optimizing schedule for 1 deferrable load(s)
EMHASS: MPC optimization completed
```

#### Sensores de salida de EMHASS:
- `sensor.emhass_deferrable0` - Horario optimizado para carga 0
- `sensor.emhass_plan_{vehicle}_mpc_congelado` - Plan completo MPC

### Troubleshooting común

#### Error: "Array index out of bounds"
**Causa**: Los arrays tienen diferentes longitudes.
**Posible solución**: Verificar que TODOS los arrays tengan la misma longitud.

```yaml
# ❌ MAL - arrays con longitudes diferentes
def_total_hours: [5.56, 6.82]           # 2 elementos
P_deferrable_nom: [3600]                  # 1 elemento ❌

# ✅ BIEN - arrays con misma longitud
def_total_hours: [5.56, 6.82]           # 2 elementos
P_deferrable_nom: [3600, 2200]           # 2 elementos ✅
```

#### Error: "No se actualiza la planificación"
**Causa**: EMHASS no está leyendo el sensor.
**Verificar**:
1. El sensor existe: `sensor.ev_trip_planner_{vehicle}_emhass_perfil_diferible_{vehicle}`
2. El estado es "ready" o "active"
3. `power_profile_watts` tiene datos (no null)
4. EMHASS tiene el número correcto de `number_of_deferrable_loads`

### Ejemplo real basado en nuestro código

**Del código del sensor** ([sensor.py:176-178](../../custom_components/ev_trip_planner/sensor.py#L176-L178)):

```python
# Nuestro sensor publica estos atributos:
{
    "power_profile_watts": self.coordinator.data.get("emhass_power_profile"),
    "deferrables_schedule": self.coordinator.data.get("emhass_deferrables_schedule"),
    "emhass_status": self.coordinator.data.get("emhass_status"),
}
```

**Configuración EMHASS sugerida para leer estos datos:**

```yaml
# En configuration.yaml de EMHASS
optimization:
  number_of_deferrable_loads: 1
  
  # Plantilla para extraer datos
  template:
    - sensor:
        - entity_id: sensor.ev_trip_planner_chispitas_2_emhass_perfil_diferible_chispitas_2
      attributes:
        - attribute: power_profile_watts
          name: p_deferrable
        - attribute: def_total_hours
          name: def_total_hours
          template: "{{ value | sum / 3600 | round(2) }}"
        - attribute: def_start_timestep
          name: def_start_timestep
          template: "{{ value | index_of(0) }}"
        - attribute: def_end_timestep
          name: def_end_timestep
          template: "{{ value | index_of(-1) }}"
```

### Resumen de integración

**Flujo de datos:**
```
EV Trip Planner                    EMHASS
     │                                    │
     │  1. Usuario crea viaje            │
     │  2. TripManager calcula energía  │
     │  3. EMHASSAdapter publica:      │
     │    - power_profile_watts[168]     │───→ 优化优化
     │    - def_total_hours            │
     │    - def_start_timestep        │
     │    - def_end_timestep          │
     │                                    │
     │  4. EMHASS optimiza:             │
     │    - Calcula coste energía      │
     │    - Respeta ventanas            │
     │    - Genera p_deferrable[]       │
     │                                    │
     │  5. EMHASS escribe:               │
     │    - p_deferrable0 = schedule     │
     │                                    │
     └─── 6. HA lee p_deferrable0 → Control cargador
```

**Coordenación CRÍTICA:**
- El array `power_profile_watts[168]` de nuestro sensor DEBE coincidir con `P_deferrable[168]` de EMHASS
- Nuestro sensor sugiere cuándo EMHASS puede cargar
- EMHASS podría optimizar y confirmar cuándo cargará realmente

---


| # | Problema | Tipo | Prioridad | Complejidad |
|---|----------|------|-----------|-------------|
| 1 | Sidebar no se elimina | Bug funcional | P2 | Baja (1 línea) |
| 2 | Vehicle Status vacío | Bug funcional | P1 | Media |
| 3 | Available Sensors con ruido | UX (ruido) | P2 | Baja |
| 3b | EMHASS sin gráfico | UX (falta feature) | P1 | Media |
| 4 | Options flow incompleto | UX (limitación) | **P0** | Baja-Media |
| **5** | **Potencia no actualiza** | **Bug funcional CRÍTICO** | **P0** | **Media** |
| **6** | **Diseño visual fatiga** | **UX/UI** | **P1** | **Media** |

---

---

## Problema #8: Arquitectura incorrecta del sensor EMHASS

**Descripción**: El sensor actual `EmhassDeferrableLoadSensor` agrega todos los viajes en un único `power_profile_watts`, pero EMHASS podría necesitar **perfiles diferibles separados por viaje** para optimizar cada carga independientemente.

**Referencias**:
- [sensor.py:127-202](../../custom_components/ev_trip_planner/sensor.py#L127-L202) - `EmhassDeferrableLoadSensor` actual
- [trip_manager.py:1660-1726](../../custom_components/ev_trip_planner/trip_manager.py#L1660-L1726) - `async_generate_power_profile()` calcula perfil agregado

### Análisis

#### Arquitectura actual (POSIBLEMENTE INCORRECTA)

**Problema**: Un solo sensor para todos los viajes

```python
# sensor.py:176-178
extra_state_attributes = {
    "power_profile_watts": [7200, 7200, ..., 0, ..., 7200]  # Todos los viajes mezclados
}
```

**EMHASS ve esto como 1 sola carga diferible**, cuando en realidad son 2 o más viajes con ventanas diferentes.

#### Arquitectura propuesta (POSPIBLEMENTE CORRECTA)

**Opción A: Un sensor por viaje con todos los atributos**

```python
class TripEmhassDeferrableSensor(SensorEntity):
    """Sensor individual para un viaje con todos los parámetros EMHASS."""
    
    @property
    def extra_state_attributes(self):
        trip = self._get_trip_data()
        return {
            "def_total_hours": trip["kwh"] / trip["charging_power_kw"],
            "P_deferrable_nom": trip["charging_power_kw"] * 1000,
            "def_start_timestep": trip["start_hour"],
            "def_end_timestep": trip["end_hour"],
            "power_profile_watts": self._calculate_power_profile(trip),
        }
```

**Resultado**:
- `sensor.ev_trip_planner_coche_viaje_1` - con todos los atributos
- `sensor.ev_trip_planner_coche_viaje_2` - con todos los atributos

**Configuración EMHASS**:
```yaml
optimization:
  number_of_deferrable_loads: 2  # Un sensor por viaje
  
  template:
    - sensor:
        - entity_id: sensor.ev_trip_planner_coche_viaje_1
          name: coche_chispitas_viaje_1
          attributes:
            - attribute: power_profile_watts
              name: p_deferrable
            - attribute: def_total_hours
              name: def_total_hours
            - attribute: P_deferrable_nom
              name: P_deferrable_nom
            - attribute: def_start_timestep
              name: def_start_timestep
            - attribute: def_end_timestep
              name: def_end_timestep
```

**Opción B: Múltiples sensores separados por parámetro**

```python
# 5 sensores por viaje
TripEmhassTotalHoursSensor(trip_id)      # sensor.ev_trip_planner_coche_viaje_1_total_hours
TripEmhassNominalPowerSensor(trip_id)    # sensor.ev_trip_planner_coche_viaje_1_nominal_power
TripEmhassStartTimestepSensor(trip_id)   # sensor.ev_trip_planner_coche_viaje_1_start_timestep
TripEmhassEndTimestepSensor(trip_id)     # sensor.ev_trip_planner_coche_viaje_1_end_timestep
TripEmhassPowerProfileSensor(trip_id)    # sensor.ev_trip_planner_coche_viaje_1 (power_profile en attributes)
```

**Configuración EMHASS con plantillas Jinja2** (para 2 viajes):

```yaml
# ⚡ Copiar en configuration.yaml de EMHASS
optimization:
  number_of_deferrable_loads: 2

  # Arrays de parámetros
  def_total_hours:
    - "{{ states('sensor.ev_trip_planner_coche_viaje_1_total_hours') | float(0) }}"
    - "{{ states('sensor.ev_trip_planner_coche_viaje_2_total_hours') | float(0) }}"

  P_deferrable_nom:
    - "{{ states('sensor.ev_trip_planner_coche_viaje_1_nominal_power') | int(0) }}"
    - "{{ states('sensor.ev_trip_planner_coche_viaje_2_nominal_power') | int(0) }}"

  def_start_timestep:
    - "{{ states('sensor.ev_trip_planner_coche_viaje_1_start_timestep') | int(0) }}"
    - "{{ states('sensor.ev_trip_planner_coche_viaje_2_start_timestep') | int(0) }}"

  def_end_timestep:
    - "{{ states('sensor.ev_trip_planner_coche_viaje_1_end_timestep') | int(0) }}"
    - "{{ states('sensor.ev_trip_planner_coche_viaje_2_end_timestep') | int(0) }}"

  # Perfil de potencia desde atributos
  P_deferrable:
    p_deferrable: "{{ state_attr('sensor.ev_trip_planner_coche_viaje_1', 'power_profile_watts') | default([]) }}"
    p_deferrable: "{{ state_attr('sensor.ev_trip_planner_coche_viaje_2', 'power_profile_watts') | default([]) }}"
```

### Ejemplo real: 2 viajes el mismo día

**Escenario** (sábado 12:30):
- Vehículo: `coche_chispitas` (charging_power: 3.6 kW)
- Viaje 1: Lunes 07:00, 40km, necesita 5.56 horas
- Viaje 2: Martes 18:30, 25km, necesita 3.47 horas

**Sensores creados automáticamente**:
```
sensor.ev_trip_planner_coche_chispitas_viaje_1_total_hours
sensor.ev_trip_planner_coche_chispitas_viaje_1_nominal_power
sensor.ev_trip_planner_coche_chispitas_viaje_1_start_timestep
sensor.ev_trip_planner_coche_chispitas_viaje_1_end_timestep
sensor.ev_trip_planner_coche_chispitas_viaje_1 (con power_profile_watts en attributes)

sensor.ev_trip_planner_coche_chispitas_viaje_2_total_hours
sensor.ev_trip_planner_coche_chispitas_viaje_2_nominal_power
sensor.ev_trip_planner_coche_chispitas_viaje_2_start_timestep
sensor.ev_trip_planner_coche_chispitas_viaje_2_end_timestep
sensor.ev_trip_planner_coche_chispitas_viaje_2 (con power_profile_watts en attributes)
```

**Configuración EMHASS con plantillas Jinja2 (listo para copiar)**:

```yaml
# ⚡ Copiar en configuration.yaml de EMHASS
optimization:
  number_of_deferrable_loads: 2

  def_total_hours:
    - "{{ states('sensor.ev_trip_planner_coche_chispitas_viaje_1_total_hours') | float(0) }}"
    - "{{ states('sensor.ev_trip_planner_coche_chispitas_viaje_2_total_hours') | float(0) }}"

  P_deferrable_nom:
    - "{{ states('sensor.ev_trip_planner_coche_chispitas_viaje_1_nominal_power') | int(0) }}"
    - "{{ states('sensor.ev_trip_planner_coche_chispitas_viaje_2_nominal_power') | int(0) }}"

  def_start_timestep:
    - "{{ states('sensor.ev_trip_planner_coche_chispitas_viaje_1_start_timestep') | int(0) }}"
    - "{{ states('sensor.ev_trip_planner_coche_chispitas_viaje_2_start_timestep') | int(0) }}"

  def_end_timestep:
    - "{{ states('sensor.ev_trip_planner_coche_chispitas_viaje_1_end_timestep') | int(0) }}"
    - "{{ states('sensor.ev_trip_planner_coche_chispitas_viaje_2_end_timestep') | int(0) }}"

  P_deferrable:
    p_deferrable: "{{ state_attr('sensor.ev_trip_planner_coche_chispitas_viaje_1', 'power_profile_watts') | default([]) }}"
    p_deferrable: "{{ state_attr('sensor.ev_trip_planner_coche_chispitas_viaje_2', 'power_profile_watts') | default([]) }}"
```

**Valores esperados cuando EMHASS evalúa las plantillas**:

```yaml
# EMHASS reemplaza las plantillas con estos valores:
def_total_hours: [5.56, 3.47]
P_deferrable_nom: [3600, 2200]
def_start_timestep: [23, 67]  # Lunes 07:00 = hora 23, Martes 18:30 = hora 67
def_end_timestep: [24, 68]
P_deferrable: [
  [0, 0, ..., 3600, 3600, ..., 0],  # Viaje 1: 168 horas con carga programada
  [0, 0, ..., 2200, 2200, ..., 0]   # Viaje 2: 168 horas con carga programada
]
```

### Panel de control: mostrar configuración Jinja2

**IMPORTANTE**: El panel podría mostrar el código YAML/Jinja2 **listo para copiar y pegar** en EMHASS, con las plantillas `{{ states(...) }}` ya resueltas.

**Ejemplo de lo que podría mostrar el panel** (para 2 viajes):

```yaml
# ⚡ Configuración EMHASS para copiar
number_of_deferrable_loads: 2

# Parámetros de carga diferible
def_total_hours:
  - "{{ states('sensor.ev_trip_planner_coche_viaje_1_total_hours') | float(0) }}"
  - "{{ states('sensor.ev_trip_planner_coche_viaje_2_total_hours') | float(0) }}"

P_deferrable_nom:
  - "{{ states('sensor.ev_trip_planner_coche_viaje_1_nominal_power') | int(0) }}"
  - "{{ states('sensor.ev_trip_planner_coche_viaje_2_nominal_power') | int(0) }}"

def_start_timestep:
  - "{{ states('sensor.ev_trip_planner_coche_viaje_1_start_timestep') | int(0) }}"
  - "{{ states('sensor.ev_trip_planner_coche_viaje_2_start_timestep') | int(0) }}"

def_end_timestep:
  - "{{ states('sensor.ev_trip_planner_coche_viaje_1_end_timestep') | int(0) }}"
  - "{{ states('sensor.ev_trip_planner_coche_viaje_2_end_timestep') | int(0) }}"

# Perfil de potencia (array de 168 horas)
P_deferrable:
  p_deferrable: "{{ state_attr('sensor.ev_trip_planner_coche_viaje_1', 'power_profile_watts') | default([]) }}"
  p_deferrable: "{{ state_attr('sensor.ev_trip_planner_coche_viaje_2', 'power_profile_watts') | default([]) }}"
```

**HTML del panel**:

```html
<div class="emhass-config">
  <h3>⚡ Configuración EMHASS para copiar</h3>
  <p class="hint">Copia este código y pégalo en tu configuration.yaml de EMHASS</p>
  <pre class="yaml-block"><code id="emhass-config"></code></pre>
  <button @click="${this.copyEmhassConfig()}">📋 Copiar al portapapeles</button>
</div>
```

**JavaScript para generar las plantillas dinámicamente**:

```javascript
// panel.js - Método para generar configuración Jinja2
_getEmhassConfig() {
  const trips = this._getTrips();
  const numTrips = trips.length;

  let config = `# ⚡ Configuración EMHASS - ${numTrips} viaje(s)\n`;
  config += `number_of_deferrable_loads: ${numTrips}\n\n`;

  // def_total_hours array
  config += `def_total_hours:\n`;
  trips.forEach((trip, i) => {
    const tripId = trip.id;
    config += `  - "{{ states('sensor.ev_trip_planner_${this.vehicleId}_viaje_${tripId}_total_hours') | float(0) }}"\n`;
  });

  // P_deferrable_nom array
  config += `\nP_deferrable_nom:\n`;
  trips.forEach((trip, i) => {
    const tripId = trip.id;
    config += `  - "{{ states('sensor.ev_trip_planner_${this.vehicleId}_viaje_${tripId}_nominal_power') | int(0) }}"\n`;
  });

  // def_start_timestep array
  config += `\ndef_start_timestep:\n`;
  trips.forEach((trip, i) => {
    const tripId = trip.id;
    config += `  - "{{ states('sensor.ev_trip_planner_${this.vehicleId}_viaje_${tripId}_start_timestep') | int(0) }}"\n`;
  });

  // def_end_timestep array
  config += `\ndef_end_timestep:\n`;
  trips.forEach((trip, i) => {
    const tripId = trip.id;
    config += `  - "{{ states('sensor.ev_trip_planner_${this.vehicleId}_viaje_${tripId}_end_timestep') | int(0) }}"\n`;
  });

  // P_deferrable con power_profile_watts attributes
  config += `\n# Perfil de potencia (array de 168 horas)\n`;
  config += `P_deferrable:\n`;
  trips.forEach((trip, i) => {
    const tripId = trip.id;
    config += `  p_deferrable: "{{ state_attr('sensor.ev_trip_planner_${this.vehicleId}_viaje_${tripId}', 'power_profile_watts') | default([]) }}"\n`;
  });

  return config;
}

copyEmhassConfig() {
  const config = this._getEmhassConfig();
  navigator.clipboard.writeText(config).then(() => {
    this._showNotification("Configuración copiada al portapapeles");
  });
}
```

### Impacto

**Si esta hipótesis es correcta**: Sin este cambio
- EMHASS podría estar optimizando todos los viajes como si fueran UNA sola carga
- No respeta las ventanas de tiempo individuales
- La optimización podría ser incorrecta

**Si esta hipótesis es correcta**: Con este cambio
- EMHASS optimiza cada viaje independently
- Respeta las ventanas de tiempo de cada viaje
- El usuario puede controlar qué viajes cargan primero

### Hipótesis

1. **El agregado actual rompe la optimización** (95% probable)
   - `power_profile_watts` mezcla dos viajes en un solo array
   - EMHASS no puede diferenciar qué horas pertenecen a qué viaje
   - **Evidencia**: El array actual tiene 168 horas pero mezcla ventanas no contiguas

2. **Podríamos necesitar un sensor por viaje** (99% probable)
   - EMHASS usa `number_of_deferrable_loads` para dimensionar arrays
   - Cada carga podría necesitar sus propios parámetros
   - **Evidencia**: Documentación EMHASS y explicación del usuario

3. **Opción A es más simple de implementar** (80% probable)
   - Un sensor por viaje es más fácil de mantener
   - El usuario solo configura una entity_id por viaje
   - **Evidencia**: Menor cantidad de entidades a gestionar

### Pasos para implementar

1. **Crear `TripEmhassDeferrableSensor`**:
   - Hereda de `SensorEntity`
   - Se instancia por cada viaje en `async_setup_entry`
   - Publica todos los atributos EMHASS

2. **Actualizar `sensor.py`**:
   ```python
   # En async_setup_entry
   for trip_id in trip_manager.get_all_trip_ids():
       sensor = TripEmhassDeferrableSensor(coordinator, vehicle_id, trip_id)
       entities.append(sensor)
   ```

3. **Añadir sección en panel.js**:
   - Leer todos los sensores `*_viaje_*`
   - Generar configuración YAML con plantillas
   - Mostrar en el panel con botón "Copiar"

4. **Mantener sincronización**:
   - Crear sensor cuando se crea viaje
   - Eliminar sensor cuando se elimina viaje
   - Actualizar cuando cambia el viaje

### Resumen

| Arquitectura | Sensores | Configuración EMHASS | Ventajas |
|--------------|----------|---------------------|----------|
| **Actual (posiblemente incorrecta)** | 1 sensor agregado | 1 deferrable load | ❌ No optimiza por viaje |
| **Opción A** | 1 sensor/viaje | 1 sensor/viaje | ✅ Simple, todo en attributes |
| **Opción B** | 5 sensores/viaje | 1 sensor/viaje | ❌ Demasiadas entidades |

**Posible Recomendación**: Opción A - un sensor por viaje con todos los atributos.

---

## Tabla resumen actualizada

| # | Problema | Tipo | Prioridad | Complejidad |
|---|----------|------|-----------|-------------|
| 1 | Sidebar no se elimina | Bug funcional | P2 | Baja (1 línea) |
| 2 | Vehicle Status vacío | Bug funcional | P1 | Media |
| 3 | Available Sensors con ruido | UX (ruido) | P2 | Baja |
| 3b | EMHASS sin gráfico | UX (falta feature) | P1 | Media |
| 4 | Options flow incompleto | UX (limitación) | **P0** | Baja-Media |
| **5** | **Potencia no actualiza** | **Bug funcional CRÍTICO** | **P0** | **Media** |
| **6** | **Diseño visual fatiga** | **UX/UI** | **P1** | **Media** |
| **8** | **Arquitectura EMHASS incorrecta** | **Arquitectura CRÍTICA** | **P0** | **Alta** |

