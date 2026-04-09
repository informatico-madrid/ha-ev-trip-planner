# Research: fix-emhass-sensor-attributes (Deep Dive)

**Date**: 2026-04-09
**Status**: Complete

---

## Executive Summary

El sensor EMHASS de perfil diferible está roto por **dos problemas separados** que requieren fixes distintos:

1. **Bug de dispositivo duplicado**: `EmhassDeferrableLoadSensor.device_info` usa `entry_id` en lugar de `vehicle_id` para los identificadores del dispositivo, creando dos dispositivos en Home Assistant.

2. **Bug de atributos vacíos**: Los atributos `power_profile_watts` y `deferrables_schedule` están `null` porque el flujo de datos EMHASS → coordinator → sensor se rompió al eliminar la "escritura dual" en PHASE 3.1.

**Adicionalmente**, se encontró que la lógica de negocio para el cálculo del perfil de carga (168 valores horarios) **SÍ existe** y está implementada en `calculations.py`, pero no se está ejecutando correctamente.

---

## Parte 1: Lógica de Negocio del Perfil de Carga

### ¿Qué es el `power_profile_watts`?

Es un **array de 168 valores flotantes** que representan la potencia de carga (en watts) para cada hora de la próxima semana (7 días × 24 horas = 168 horas).

- **Índice 0**: Primera hora desde el momento actual
- **Valor 0**: No se necesita cargar en esa hora
- **Valor > 0**: Potencia de carga en esa hora (ej: 3600W = 3.6kW)

### Flujo Completo de Datos

⚠️ **IMPORTANTE**: El siguiente diagrama muestra el **flujo ESPERADO/DISEÑADO**, pero actualmente NO funciona debido a bugs documentados en la Parte 2.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│              FLUJO ESPERADO DE DATOS EMHASS (ACTUALMENTE ROTO)            │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  1. CAMBIO DE SOC O VIAJES                                                │
│     ↓                                                                      │
│  2. PresenceMonitor._async_handle_soc_change()                            │
│     → Detecta cambio ≥5% en SOC                                           │
│     → Verifica: vehículo en casa Y enchufado                              │
│     ↓                                                                      │
│  3. TripManager.async_generate_power_profile()                            │
│     → Llama calculations.calculate_power_profile_from_trips()              │
│     → Genera 168 valores horarios                                         │
│     ↓                                                                      │
│  4. TripManager.async_generate_deferrables_schedule()                     │
│     → Llama calculations.generate_deferrable_schedule_from_trips()        │
│     → Genera schedule de 24 horas                                         │
│     ↓                                                                      │
│  5. EMHASSAdapter.publish_deferrable_loads() ❌ ESTE PASO NO SE EJECUTA    │
│     → Cachea: self._cached_power_profile, _cached_deferrables_schedule    │
│     → coordinator.async_request_refresh()                                  │
│     ↓                                                                      │
│  6. Coordinator._async_update_data()                                       │
│     → emhass_adapter.get_cached_optimization_results()                    │
│     → Popula coordinator.data con EMHASS data                             │
│     ↓                                                                      │
│  7. EmhassDeferrableLoadSensor (CoordinatorEntity)                        │
│     → native_value: coordinator.data["emhass_status"]                      │
│     → extra_state_attributes:                                             │
│         - power_profile_watts: coordinator.data["emhass_power_profile"]    │
│         - deferrables_schedule: coordinator.data["emhass_deferrables_schedule"]│
│         - emhass_status: coordinator.data["emhass_status"]                 │
│                                                                             │
│  ⚠️ PASO 5 ROTO: Ver Parte 2 para el bug real                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Cálculo del Perfil de 168 Valores

**Ubicación**: `custom_components/ev_trip_planner/calculations.py:639-710`

```python
def calculate_power_profile_from_trips(
    trips: List[Dict[str, Any]],
    power_kw: float,
    horizon: int = 168,  # 7 días
    reference_dt: Optional[datetime] = None,
) -> List[float]:
```

**Algoritmo**:
1. Inicializa array de 168 ceros
2. Para cada viaje con datetime y kwh:
   - Calcula horas hasta el deadline
   - Calcula energía necesaria
   - Distribuye potencia en las horas ANTES del deadline
3. Retorna array de 168 watts

**Ejemplo**: Viaje el Lunes a las 08:00, necesita 4h de carga a 3.6kW:
- Índices que se llenan: 4, 5, 6, 7 (04:00-08:00)
- Valores: 3600W en cada índice

### Cálculo de kWh Necesarios

**Ubicación**: `custom_components/ev_trip_planner/trip_manager.py:923-933`

```python
async def async_get_kwh_needed_today(self) -> float:
    today = datetime.now().date()
    total_kwh = 0.0
    
    # Viajes recurrentes activos hoy
    for trip in self._recurring_trips.values():
        if trip["activo"] and self._is_trip_today(trip, today):
            total_kwh += trip["kwh"]
    
    # Viajes puntuales pendientes hoy
    for trip in self._punctual_trips.values():
        if trip["estado"] == "pendiente" and self._is_trip_today(trip, today):
            total_kwh += trip["kwh"]
    
    return total_kwh
```

### Cálculo de Horas Necesarias

**Ubicación**: `custom_components/ev_trip_planner/trip_manager.py:935-941`

```python
async def async_get_hours_needed_today(self) -> int:
    kwh_needed = await self.async_get_kwh_needed_today()
    charging_power = self._get_charging_power()  # kW desde config
    return math.ceil(kwh_needed / charging_power) if charging_power > 0 else 0
```

**Fórmula**: `horas = ceil(kwh_needed / charging_power_kw)`

---

## Parte 2: El Bug Real - Flujo Roto

### El Bug Crítico: PresenceMonitor NO llama a EMHASSAdapter

El research original documentó un flujo de datos que es **INCORRECTO**:

```python
# LO QUE EL research DICE (INCORRECTO):
SOC Change → PresenceMonitor._async_handle_soc_change()
    → TripManager.async_generate_power_profile()
    → EMHASSAdapter.publish_deferrable_loads()
    → coordinator.async_request_refresh()
```

**LO QUE REALMENTE PASA** (VERIFICADO):

```python
# En presence_monitor.py:546-547
await self._trip_manager.async_generate_power_profile()     # ← SOLO retorna lista, NO cachea
await self._trip_manager.async_generate_deferrables_schedule()  # ← SOLO retorna lista, NO cachea
```

Estos métodos (`async_generate_power_profile()` y `async_generate_deferrables_schedule()` en trip_manager.py:1661+) **SOLO calculan y retornan valores**. No cachean nada y no llaman al EMHASSAdapter.

### El Método Correcto: `_publish_deferrable_loads()`

El flujo correcto que DEBERÍA ejecutarse es:

```python
# En trip_manager.py:155-160
TripManager._publish_deferrable_loads()
    → all_trips = await self._get_all_active_trips()
    → EMHASSAdapter.publish_deferrable_loads(all_trips)  # ← ESTE cachea los valores
        → para cada trip: async_publish_deferrable_load(trip)  # asigna índice EMHASS
        → self._cached_power_profile = [168 valores]
        → self._cached_deferrables_schedule = [...]
        → self._cached_emhass_status = {...}
        → coordinator.async_request_refresh()
```

**Nota**: El método correcto es `publish_deferrable_loads()` (plural, sin prefijo `async_` en el nombre, aunque SÍ es `async def` en línea 486).

**Pero este flujo NUNCA se llama desde PresenceMonitor.** El SOC change handler llama a los métodos que solo retornan listas, ignorando por completo el método que publica a EMHASS.

### El Bug Adicional: Confusión entre Métodos Similarmente Nombrados

Hay **TRES métodos** con nombres similares en `EMHASSAdapter`:

1. **`async_publish_all_deferrable_loads(all_trips)`** (línea 403)
   - Llamado por: `TripManager._publish_deferrable_loads()`
   - Lo que hace: Itera sobre `all_trips` y llama a `async_publish_deferrable_loads()` (singular)
   - ¿Cachea? **NO**

2. **`async_publish_deferrable_load(trip)`** (singular SIN "s", línea 274)
   - Llamado por: `async_publish_all_deferrable_loads()` para cada viaje, y también por `publish_deferrable_loads()` internamente
   - Lo que hace: Publica datos de UN viaje a EMHASS (asigna índice, calcula params)
   - ¿Cachea? **NO** - no setea `_cached_*` attributes

3. **`publish_deferrable_loads(trips, charging_power_kw=None)`** (sin prefijo async en nombre, plural, línea 486)
   - Llamado por: **NADIE actualmente** (debería ser llamado por `TripManager._publish_deferrable_loads()`)
   - Lo que hace:
     ```python
     # Calcula power profile y schedule internamente
     # Llama async_publish_deferrable_load(trip) para cada trip (líneas 565-568)
     self._cached_power_profile = power_profile
     self._cached_deferrables_schedule = deferrables_schedule
     self._cached_emhass_status = {...}
     await self.coordinator.async_request_refresh()
     ```
   - ¿Cachea? **SÍ** - este es el ÚNICO método que cachea los 168 valores

**El problema**: `TripManager._publish_deferrable_loads()` llama a `async_publish_all_deferrable_loads()`, que a su vez llama a `async_publish_deferrable_loads()` (singular), que NO cachea. El método que realmente cachea (`publish_deferrable_loads()` sin async) nunca se invoca.

---

## Parte 4: Ventanas de Carga

### Concepto de Ventana de Carga

Una ventana de carga es el intervalo de tiempo disponible para cargar antes de un viaje:

```python
CargaVentana = {
    "ventana_horas": float,          # Horas disponibles
    "kwh_necesarios": float,         # Energía necesaria
    "horas_carga_necesarias": float, # Horas de carga necesarias
    "inicio_ventana": datetime,      # Inicio: hora_regreso o deadline-6h
    "fin_ventana": datetime,        # Fin: hora del viaje
    "es_suficiente": bool,          # ¿La ventana es suficiente?
}
```

### Algoritmo de Ventana de Carga

**Ubicación**: `custom_components/ev_trip_planner/calculations.py`

```python
def calculate_charging_window_pure(
    trip_departure_time: Optional[datetime],
    soc_actual: float,
    hora_regreso: Optional[datetime],
    charging_power_kw: float,
    energia_kwh: float,
    duration_hours: float = 6.0,
) -> Dict[str, Any]:
```

**Lógica**:
1. **Inicio**: `hora_regreso` si existe, sino `departure - 6h`
2. **Fin**: Siempre `trip_departure_time`
3. **Horas disponibles**: `fin - inicio`
4. **Horas necesarias**: `energia_kwh / charging_power_kw`
5. **¿Es suficiente?**: `ventana_horas >= horas_carga_necesarias`

---

## Parte 5: Disparadores de Actualización (SOC Changes)

### Detección de Cambios de SOC

**Ubicación**: `custom_components/ev_trip_planner/presence_monitor.py`

```python
self._soc_listener_unsub = async_track_state_change_event(
    self.hass,
    self.soc_sensor,
    self._async_handle_soc_change,
)
```

### Condiciones de Disparo

El sensor **SOLO se actualiza** cuando:
1. El SOC cambia ≥5% (debouncing)
2. El vehículo está en casa
3. El vehículo está enchufado
4. El estado NO es "unavailable", "unknown", "None", ""

### Propagación de Actualizaciones

⚠️ **FLUJO ACTUAL (ROTO):**
```
SOC Change → PresenceMonitor
    ↓
TripManager.async_generate_power_profile()     # Solo retorna lista, NO cachea
    ↓
TripManager.async_generate_deferrables_schedule()  # Solo retorna lista, NO cachea
    ↓
    ❌ FIN - Los datos se calculan pero se descartan
    ❌ No se llama a EMHASSAdapter.publish_deferrable_loads()
    ❌ No se cachea _cached_power_profile
    ❌ No se dispara coordinator.async_request_refresh()
```

**FLUJO CORRECTO (necesario implementar):**
```
SOC Change → PresenceMonitor
    ↓
TripManager._publish_deferrable_loads()
    ↓
EMHASSAdapter.publish_deferrable_loads(power_profile, deferrables_schedule)  # Este método cachea los datos
    ↓
coordinator.async_request_refresh()
    ↓
EmhassDeferrableLoadSensor (auto-update via CoordinatorEntity)
```

---

## Parte 6: El Bug - Por Qué el Sensor Está Vacío

### El Problemático PHASE 3.1

**Antes** (funcionaba):
```python
# Escritura directa al sensor
await self.hass.states.async_set(
    sensor_id,
    EMHASS_STATE_READY,
    {
        "power_profile_watts": power_profile,
        "deferrables_schedule": deferrables_schedule,
        ...
    },
)
```

**Después** (roto):
```python
# PHASE 3 REMOVED (3.1): Remove dual-writing path
coordinator = self._get_coordinator()
if coordinator is not None:
    await coordinator.async_request_refresh()
```

### Por Qué Retorna None

1. `publish_deferrable_loads()` cachea los valores en `self._cached_power_profile`
2. Llama a `coordinator.async_request_refresh()`
3. El coordinator ejecuta `_async_update_data()`
4. Llama a `emhass_adapter.get_cached_optimization_results()`
5. **Pero** los valores cacheados pueden ser `None` si:
   - `publish_deferrable_loads()` nunca se llamó
   - Se llamó pero el cache se limpió
   - Hay un problema de timing

### Análisis del Bug

**Archivo**: `custom_components/ev_trip_planner/emhass_adapter.py:159-175`

```python
def get_cached_optimization_results(self) -> Dict[str, Any]:
    return {
        "emhass_power_profile": getattr(self, "_cached_power_profile", None),
        "emhass_deferrables_schedule": getattr(
            self, "_cached_deferrables_schedule", None
        ),
        "emhass_status": getattr(self, "_cached_emhass_status", None),
    }
```

**Problema**: Si `_cached_power_profile` nunca se seteó, retorna `None`.

---

## Parte 7: El Bug - Dispositivo Duplicado

### Código Problemático

**Archivo**: `custom_components/ev_trip_planner/sensor.py:176-190`

```python
@property
def device_info(self) -> Dict[str, Any]:
    vehicle_id = getattr(self.coordinator, 'vehicle_id', self._entry_id)
    
    return {
        "identifiers": {(DOMAIN, self._entry_id)},  # ← BUG
        "name": f"EV Trip Planner {vehicle_id}",
        ...
    }
```

**Comparación** con `TripPlannerSensor` (línea 118):
```python
return {
    "identifiers": {(DOMAIN, self._vehicle_id)},  # ← CORRECTO
    ...
}
```

### Resultado

Home Assistant crea **dos dispositivos**:
1. `EV Trip Planner chispitas` (con `identifiers = {(DOMAIN, "chispitas")}`)
2. `EV Trip Planner 01KNS8EEZCHZD8HZM4WGJEKPJJ` (con `identifiers = {(DOMAIN, "01KNS8EEZCHZD8HZM4WGJEKPJJ")}`)

---

## Parte 8: Estado del Sensor

### Máquina de Estados

| Estado | Condición |
|--------|-----------|
| `idle` | No se necesita energía (`kwh_needed <= 0`) |
| `ready` | Se necesita energía pero no se está cargando |
| `active` | Se necesita energía Y se está cargando |

### Atributos Requeridos

| Atributo | Tipo | Descripción |
|----------|------|-------------|
| `power_profile_watts` | `List[float]` | 168 valores horarios (watts) |
| `deferrables_schedule` | `List[Dict]` | Schedule con timestamps y potencias |
| `emhass_status` | `str` | `"idle"`, `"ready"`, o `"active"` |

---

## Recomendaciones de Fix

### Fix 1: Dispositivo Duplicado

**Archivo**: `custom_components/ev_trip_planner/sensor.py:185`

Cambiar:
```python
"identifiers": {(DOMAIN, self._entry_id)},
```

Por:
```python
"identifiers": {(DOMAIN, self._vehicle_id)},
```

Y asegurar que `self._vehicle_id` está disponible en el sensor.

### Fix 2: Atributos Vacíos

El problema es que `publish_deferrable_loads()` cachea los valores pero no están llegando al coordinator correctamente.

**Opciones**:
1. Asegurar que `_cached_power_profile` se popula antes del refresh
2. Restaurar algún mecanismo de escritura directa como fallback
3. Verificar el timing entre cacheo y refresh

### Fix 3: Inicialización

El sensor debe inicializarse con valores (incluso si son todos ceros) cuando se crea la config entry.

---

## Especificación de EMHASS

Basado en `/doc/borrador/perfildiferible.yml` y `/doc/borrador/perfildiferibletemplateejemplo.yml`:

### Formato Esperado

```yaml
state: "ready"  # o "active", "idle"

attributes:
  power_profile_watts:
    - 0      # Hora 1 (próxima hora completa)
    - 0      # Hora 2
    ...
    - 3600   # Horas de carga
    ...
    - 0      # Hora 168
  
  deferrables_schedule: |
    [
      {"date": "2026-04-09T14:00:00+02:00", "p_deferrable0": "0.0"},
      {"date": "2026-04-09T15:00:00+02:00", "p_deferrable0": "3600.0"},
      ...
    ]
  
  emhass_status: "ready"
```

---

## Ubicaciones de Código Clave

| Archivo | Líneas | Descripción |
|---------|--------|-------------|
| `sensor.py` | 176-190 | `EmhassDeferrableLoadSensor.device_info` - usa entry_id ❌ |
| `sensor.py` | 150-163 | Lee desde coordinator.data |
| `emhass_adapter.py` | 537 | Comentario: "PHASE 3 REMOVED (3.1)" |
| `emhass_adapter.py` | 485-569 | `publish_deferrable_loads()` |
| `emhass_adapter.py` | 159-175 | `get_cached_optimization_results()` |
| `coordinator.py` | 108-118 | Obtiene datos EMHASS para coordinator.data |
| `calculations.py` | 639-710 | `calculate_power_profile_from_trips()` - 168 valores |
| `calculations.py` | 848-900+ | `generate_deferrable_schedule_from_trips()` |
| `trip_manager.py` | 923-941 | `async_get_kwh_needed_today()`, `async_get_hours_needed_today()` |
| `presence_monitor.py` | SOC listener `_async_handle_soc_change()` |

---

## Feasibility

| Aspecto | Evaluación |
|---------|------------|
| **Complejidad** | Media - bugs bien identificados |
| **Riesgo** | Medio - toca lógica core de sensores |
| **Esfuerzo** | M (2-3 días) |
| **Breaking Changes** | No - solo corrección de bugs |
