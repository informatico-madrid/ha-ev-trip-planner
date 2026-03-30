# Epic: EMHASS Deferrable Load Integration

## Vision

Integrar los viajes del EV Trip Planner con EMHASS como cargas diferibles (deferrable loads), organizando viajes en perfiles de carga aplazable con calculo de ventanas de carga basado en SOC y propagacion de hitos SOC entre viajes consecutivos.

El sistema debe:
- Calcular ventanas de carga dinamicas basadas en cuando el coche regresa a casa
- Propagar deficits de carga entre viajes (si el viaje nocturno no puede completar la carga, el deficit se suma al viaje de la manana)
- Mostrar el schedule de carga `p_deferrable{n}` en las tarjetas de viaje
- Publicar datos a EMHASS en el formato requerido con indices correctos

---

## Success Criteria

1. Cada viaje se publica como carga diferible con indice `p_deferrable{n}` correcto
2. Las ventanas de carga se calculan desde que el coche regresa a casa hasta la siguiente salida
3. El algoritmo de hitos SOC propaga deficits entre viajes consecutivos
4. `sensor.emhass_perfil_diferible_{vehicle_id}` se actualiza cuando:
   - Se aniade/modifica/elimina un viaje
   - El sensor SOC cambia y el coche esta en casa y enchufado
5. Las tarjetas de viaje muestran el horario de carga diferible asignado
6. La automatizacion de control de carga responde al plan MPC de EMHASS

---

## Dependency Graph

```
[SOC Integration Baseline]
         |
         v
[Charging Window Calculation]
         |
         v
[SOC Milestone Algorithm]
         |
         v
[EMHASS Sensor Enhancement]
         +-----------+
         |           |
         v           v
[Trip Card     [Automation Template]
 Enhancement]        |
         |           |
         +-----+-----+
               |
               v
    [Integration with fixes]
```

---

## Spec 1: SOC Integration Baseline + Return Time Detection

### Goal (User Story)
Como sistema, necesito leer el sensor SOC del vehiculo y disparar recalkulos de carga cuando el SOC cambia mientras el coche esta en casa y enchufado. Tambien necesito registrar la hora de regreso del vehiculo para calcular la ventana de carga.

### Acceptance Criteria

1. **Given** el usuario ha configurado un sensor SOC para el vehiculo, **when** el valor del sensor cambia, **then** el sistema lee el nuevo valor

2. **Given** el coche esta en casa y enchufado, **when** el SOC cambia, **then** se dispara `async_publish_deferrable_loads()` para recalcular el perfil

3. **Given** el coche NO esta en casa o NO esta enchufado, **when** el SOC cambia, **then** NO se dispara recalkculo (ahorro de recursos)

4. **Given** el coche regresa a casa, **when** se detecta el cambio de estado (de "ausente" a "en casa"), **then**:
   - Se dispara recalculo inmediato
   - Se registra `hora_regreso` (timestamp actual)
   - Se almacena en estado persistente para uso por Spec 2

5. **Given** el usuario aniade/editar/elimina un viaje, **when** el cambio se guarda, **then** se actualiza el perfil de carga

6. **Given** el coche estaba en casa y sale (home_sensor -> "off"), **when** se detecta la salida, **then** `hora_regreso` se invalida hasta proximo regreso

### Interface Contracts

**Input**: State change from home sensor, plugged sensor, or SOC sensor

**Output**: Calls `trip_manager.async_generate_power_profile()` and `trip_manager.async_generate_deferrables_schedule()`

**State stored**:
```python
{
    "hora_regreso": datetime | None,  # Set when car returns home, None when leaves
    "soc_en_regreso": float | None,   # SOC at moment of return
}
```

**Trigger conditions**:
- `home_sensor` changes to "on" AND `plugged_sensor` is "on" → record return time
- `plugged_sensor` changes to "on" AND `home_sensor` is "on" → trigger recalc
- `soc_sensor` changes AND `home_sensor` is "on" AND `plugged_sensor` is "on" → trigger recalc

### Dependencies
None (baseline)

### Size
Small - primarily event listener setup and state comparison

---

## Spec 2: Charging Window Calculation

### Goal (User Story)
Como sistema, necesito calcular la ventana de carga disponible como el tiempo desde que el coche regresa a casa hasta que inicia el siguiente viaje.

### Acceptance Criteria

1. **Given** el coche esta en casa desde las 18:00 y el siguiente viaje es a las 22:00, **then** la ventana de carga es de 4 horas

2. **Given** el viaje anterior aun no ha regresado (esperando 6h), **then** la ventana NO comienza hasta que el coche regrese

3. **Given** el coche regresa a casa y el SOC cambia, **when** se recalcula la ventana, **then** el perfil de carga se actualiza inmediatamente

4. **Given** hay multiple viajes en el mismo dia, **when** se calcula la ventana, **then** cada viaje tiene su propia ventana desde que termina el anterior

5. **Given** el coche esta en casa pero NO hay viajes pendientes, **when** se genera el perfil, **then** todas las horas son 0 (sin carga)

### Interface Contracts

**Function signature**:
```python
async def calcular_ventana_carga(
    trip: Dict[str, Any],
    soc_actual: float,
    hora_regreso: datetime,
    charging_power_kw: float
) -> Dict[str, Any]:
    """
    Returns:
        {
            "ventana_horas": float,
            "kwh_necesarios": float,
            "horas_carga_necesarias": float,
            "inicio_ventana": datetime,
            "fin_ventana": datetime,
            "es_suficiente": bool
        }
    }
    """
```

### Dependencies
Spec 1: SOC Integration Baseline

### Size
Medium - window calculation logic with multiple edge cases

---

## Spec 3: SOC Milestone Algorithm

### Goal (User Story)
Como sistema, necesito propagar el deficit de carga entre viajes consecutivos para que cada viaje tenga su SOC objetivo calculado correctamente.

### Acceptance Criteria

1. **Given** un viaje de manana a las 12:00 que necesita 30% SOC y un viaje de noche a las 22:00 que necesita 80% SOC, **when** se calcula el perfil, **then**:
   - Entre viajes hay 4 horas de ventana, cargando 10% SOC/hora = +40% SOC
   - Viaje manana: necesita 30% + buffer 10% = 40% target
   - Viaje noche: 20% (llegada) + 40% (carga) = 60% pero necesita 80% → deficit 20%
   - El deficit de 20% se SUMA al viaje de manana: target manana = 40% + 20% = **60%**

2. **Given** el deficit se ha propagado, **when** se publica el perfil, **then** el viaje de manana tiene mas kWh necesarios que el viaje nocturno

3. **Given** el coche carga mas rapido que 10% SOC/hora, **when** se recalcula, **then** se usa la velocidad de carga real del usuario

4. **Given** no hay viajes previos que causen deficit, **when** se calcula, **then** solo se usa el buffer standard (ej: 10% sobre energia del viaje)

### Algorithm Details

```
Para cada viaje en orden cronologico:
    1. Calcular SOC objetivo base (energia_viaje + buffer)
    2. Calcular SOC al inicio del viaje (desde llegada anterior)
    3. Si SOC_inicio + capacidad_carga_en_ventana < SOC_objetivo:
           deficit = SOC_objetivo - (SOC_inicio + capacidad_carga_en_ventana)
           SOC_objetivo_del_siguiente_viaje += deficit
    4. Almacenar kwh_necesarios = (SOC_objetivo - SOC_inicio) * capacidad_bateria / 100
```

### Interface Contracts

**Function signature**:
```python
async def calcular_hitos_soc(
    trips: List[Dict[str, Any]],
    soc_inicial: float,
    charging_power_kw: float,
    battery_capacity_kwh: float
) -> List[Dict[str, Any]]:
    """
    Args:
        trips: List of trip dicts sorted by departure time
        soc_inicial: Current SOC percentage (0-100)
        charging_power_kw: Charging power in kW (from vehicle config)
        battery_capacity_kwh: Battery capacity in kWh (REQUIRED - from vehicle_config)

    Returns list of trips with updated kwh requirements:
    [{
        "trip_id": str,
        "soc_objetivo": float,
        "kwh_necesarios": float,
        "deficit_acumulado": float,
        "ventana_carga": {"inicio": datetime, "fin": datetime}
    }, ...]
    """

**Data Source for battery_capacity_kwh**:
- `battery_capacity_kwh` MUST be passed from `vehicle_config` dict (retrieved from config entry data)
- Source: `entry.data.get("battery_capacity_kwh")` or `vehicle_config.get("battery_capacity_kwh")`
- Default fallback: 50.0 kWh if not configured
- This value is REQUIRED for correct kwh_necesarios calculation

### Dependencies
Spec 2: Charging Window Calculation

### Size
Medium - algorithm implementation with testing

---

## Spec 4: EMHASS Sensor Enhancement

### Goal (User Story)
Como sistema, necesito que `sensor.emhass_perfil_diferible_{vehicle_id}` tenga el formato correcto con indices `p_deferrable{n}` estables y se actualice automaticamente.

### Acceptance Criteria

1. **Given** el usuario tiene 3 viajes activos, **when** se genera el perfil, **then** el sensor tiene `p_deferrable0`, `p_deferrable1`, `p_deferrable2` con valores correctos

2. **Given** un viaje se elimina, **when** se regenera el perfil, **then**:
   - El indice del viaje eliminado se marca como "released" (soft delete)
   - El indice NO se reutiliza inmediatamente
   - Los indices de viajes activos permanecen SIN cambios
   - Solo despues de un cooldown period (configurable, default 24h) el indice puede ser reutilizado

3. **Given** el coche esta en casa y enchufado y el SOC cambia, **when** se recalcula, **then** el sensor se actualiza con el nuevo `power_profile_watts`

4. **Given** el `deferrables_schedule` se genera, **when** se mira una hora especifica, **then** se ve el valor de `p_deferrable{n}` para esa hora

5. **Given** EMHASS devuelve un plan MPC, **when** el sensor `sensor.emhass_plan_{vehicle}_mpc_congelado` se actualiza, **then** la automatizacion puede leer `p_deferrable{n}` por hora

### Index Stability (Soft Delete)

**Problem**: Released indices are immediately reused, breaking EMHASS schedule stability.

**Solution - Soft Delete Algorithm**:
```python
class EMHASSAdapter:
    def __init__(self, ...):
        self._index_map: Dict[str, int] = {}  # trip_id -> index
        self._released_indices: Dict[int, datetime] = {}  # index -> release_time
        self._index_cooldown_hours: int = 24  # configurable

    async def async_release_trip_index(self, trip_id: str):
        """Soft delete - mark index as released but don't reuse immediately."""
        if trip_id not in self._index_map:
            return

        released_index = self._index_map.pop(trip_id)
        self._released_indices[released_index] = datetime.now()
        # Don't add to available_indices yet - wait for cooldown

    def get_available_indices(self) -> List[int]:
        """Return indices that can be assigned."""
        now = datetime.now()
        # Reclaim indices past cooldown
        for index, release_time in list(self._released_indices.items()):
            if (now - release_time).total_seconds() > self._index_cooldown_hours * 3600:
                del self._released_indices[index]
                self._available_indices.append(index)
        return self._available_indices
```

**Key behavior**:
- When trip deleted: index goes to `_released_indices` with timestamp
- When new trip added: only indices NOT in `_released_indices` are considered available
- After cooldown: index moves from `_released_indices` to `_available_indices`
- EMHASS schedules remain stable because indices are not immediately reassigned

### Interface Contracts

**Sensor attributes**:
```yaml
sensor.emhass_perfil_diferible_{vehicle_id}:
  state: "ready" | "active" | "error"
  attributes:
    power_profile_watts: [0.0, 0.0, 3600.0, ...]  # 168 values
    deferrables_schedule:
      - date: "2026-03-29T14:00:00+01:00"
        p_deferrable0: "0.0"
        p_deferrable1: "3600.0"
      ...
    trips_count: 2
    vehicle_id: "coche1"
    last_update: "2026-03-29T14:00:00+01:00"
    emhass_status: "ok"
```

**Trigger recalculation on**:
- Trip added → `async_publish_new_trip_to_emhass()`
- Trip modified → `async_update_deferrable_load()`
- Trip deleted → `async_remove_deferrable_load()`
- SOC changed AND car home AND plugged → `async_generate_power_profile()`

### Dependencies
Spec 3: SOC Milestone Algorithm

### Size
Medium - sensor enhancement and integration

---

## Spec 5: Trip Card Enhancement

### Goal (User Story)
Como usuario, necesito ver en la tarjeta del viaje cual es su indice `p_deferrable{n}` y el horario de carga asignado.

### Acceptance Criteria

1. **Given** el usuario crea un viaje, **when** la tarjeta se muestra, **then** aparece el indice de carga diferible (ej: "Carga diferible: p_deferrable0")

2. **Given** el viaje tieneVentana de carga asignada, **when** se muestra la tarjeta, **then** aparece la hora de inicio y fin de la ventana (ej: "Ventana: 18:00 - 22:00")

3. **Given** el viaje tiene deficit propagado, **when** se muestra la tarjeta, **then** se indica el SOC objetivo (ej: "SOC objetivo: 60%")

4. **Given** el usuario edita el viaje, **when** se guarda, **then** la tarjeta se actualiza con el nuevo indice y ventana

5. **Given** el EMHASS no esta configurado, **when** se muestra la tarjeta, **then** no se muestra informacion de carga diferible

### Interface Contracts

**Trip card additional attributes**:
```yaml
trip_card:
  p_deferrable_index: 0
  charging_window:
    start: "18:00"
    end: "22:00"
  soc_target: 60
  kwh_for_trip: 15.0
  deficit_from_previous: 5.0
```

**Data access for p_deferrable_index**:
The `TripSensor` does NOT have EMHASS index info directly. To display the index on the trip card:

Option A (via EmhassDeferrableLoadSensor):
- Read `sensor.emhass_perfil_diferible_{vehicle_id}` attributes
- The `deferrables_schedule` contains trip_id to index mapping

Option B (via EMHASSAdapter):
- `emhass_adapter.get_assigned_index(trip_id)` returns the current index
- `emhass_adapter.get_all_assigned_indices()` returns full mapping

**Implementation**: The TripCard should call `emhass_adapter.get_assigned_index(trip_id)` to resolve the index for display.

### Dependencies
Spec 4: EMHASS Sensor Enhancement

### Size
Small - UI display logic

---

## Spec 6: Automation Template

### Goal (User Story)
Como usuario, necesito una automatizacion YAML que controle la carga fisica del vehiculo segun el plan MPC de EMHASS.

### Acceptance Criteria

1. **Given** EMHASS devuelve un plan con `sensor.emhass_plan_{vehicle}_mpc_congelado`, **when** la automatizacion se ejecuta, **then** para cada hora lee el valor de `p_deferrable{n}` correspondiente

2. **Given** `p_deferrable{n}` es > 100W para la hora actual, **when** el coche esta en casa y enchufado, **then** la automatizacion inicia la carga

3. **Given** `p_deferrable{n}` es 0W para la hora actual, **when** la carga esta activa, **then** la automatizacion detiene la carga

4. **Given** el coche no esta en casa o no esta enchufado, **when** EMHASS programa carga, **then** se envia notificacion al usuario

5. **Given** el usuario activa modo manual, **when** la automatizacion se ejecuta, **then** NO interfiere con el control manual

### Interface Contracts

**Automation structure**:
```yaml
alias: "EV Trip Planner - Control Carga {vehicle_id}"
triggers:
  - minutes: "5"
    trigger: time_pattern
  - minutes: "35"
    trigger: time_pattern
conditions:
  - condition: template
    value_template: "{{ states('sensor.emhass_plan_{vehicle}_mpc_congelado') not in ['unavailable', 'unknown'] }}"
  - condition: state
    entity_id: input_boolean.carga_{vehicle}_modo_manual
    state: "off"
actions:
  - variables:
      potencia_planificada: "{{ read p_deferrable{n} for current hour }}"
      coche_en_casa: "{{ is_state(home_sensor, 'on') }}"
      coche_enchufado: "{{ is_state(plugged_sensor, 'on') }}"
  - choose:
      - conditions: [...charging start conditions...]
        sequence: [start charging]
      - conditions: [...charging stop conditions...]
        sequence: [stop charging]
```

**Requirements from EMHASS docs**:
- Lee de `sensor.emhass_plan_{vehicle}_mpc_congelado` attribute `plan_deferrable{n}_horario_mpc`
- Formato: `[{"date": "2026-03-29T14:00:00+01:00", "p_deferrable0": "0.0"}, ...]`
- `potencia_planificada > 100` = EMHASS quiere cargar
- `potencia_planificada == 0` = EMHASS NO quiere cargar

### Sensor Naming Clarification

**IMPORTANT**: There are TWO sensor naming patterns in the codebase:

1. **`sensor.emhass_plan_{vehicle}_mpc_congelado`** - Used by automation template (epic spec) and `docs/borrador/cargasAplazables.yaml`. This is a per-vehicle MPC frozen plan sensor that aggregates all deferrable loads.

2. **`sensor.emhass_deferrable{index}_schedule`** - Used by `schedule_monitor.py` for per-index schedule monitoring. Each deferrable load has its own schedule sensor.

**The automation in Spec 6 should read from `sensor.emhass_plan_{vehicle}_mpc_congelado`** which contains the aggregated schedule with all `p_deferrable{n}` values.

The `schedule_monitor.py` monitors `sensor.emhass_deferrable{index}_schedule` for individual loads - this is an alternative/additional integration point that may be used by the control strategy.

**Implementation must ensure**:
- Both sensor naming patterns are supported OR
- A mapping/alias is provided between them
- The epic automation template references the correct sensor for the implementation

### Dependencies
Spec 4: EMHASS Sensor Enhancement

### Size
Medium - automation template with edge cases

---

## Spec 7: Integration with ev-trip-planner-integration-fixes

### Goal (User Story)
Como sistema, necesito integrar los fixes de user stories US-6, US-7, US-8, US-9, US-10 del epic anterior.

### User Stories to Integrate

**US-6**: Corregir el flujo de eliminacion de vehiculos en el panel
**US-7**: Verificar que los sensores se crean correctamente al aniadir vehiculo
**US-8**: Corregir errores de sincronizacion en el dashboard
**US-9**: Verificar el estado de los trips en el panel
**US-10**: Corregir la visualizacion de notificaciones

### Acceptance Criteria

1. **Given** el usuario elimina un vehiculo, **when** se confirma la eliminacion, **then** se eliminan todos los sensores, el adaptador EMHASS y los datos asociados

2. **Given** el usuario aniade un vehiculo, **when** se completa la configuracion, **then** se crean todos los sensores necesarios incluyendo `EmhassDeferrableLoadSensor`

3. **Given** el dashboard se carga, **when** hay vehiculos configurados, **then** los datos se sincronizan correctamente desde el TripManager

4. **Given** un viaje cambia de estado, **when** el panel se actualiza, **then** el sensor correspondiente muestra el estado correcto

5. **Given** hay un error de carga, **when** se detecta, **then** se muestra una notificacion adecuada

### Interface Contracts

**Integration points**:
- `TripManager` → `EMHASSAdapter` initialization
- `TripManager.set_emhass_adapter()` called during setup
- Sensor creation/deletion synced with vehicle CRUD
- Dashboard data refresh on trip state changes

### Dependencies
Specs 1-6 (all)

### Size
Medium - integration work across components

---

## Technical Notes

### EMHASS Data Format (Reference)

```python
{
    "def_total_hours": [5.56],  # horas necesarias
    "P_deferrable_nom": [3600],  # potencia en Watts
    "def_start_timestep": [0],  # 0 = ASAP
    "def_end_timestep": [18],  # deadline hour index
    "treat_deferrable_load_as_semi_cont": [true],  # puede pausarse
    "set_deferrable_load_single_constant": [true],  # potencia constante
    "P_deferrable": [[0,0,3600,3600,...]]  # 168 valores
}
```

### Current Codebase Leverage

- `emhass_adapter.py`: Already has `publish_deferrable_loads()`, index management, error handling
- `trip_manager.py`: Already has `async_generate_power_profile()`, `async_generate_deferrables_schedule()`
- `sensor.py`: `EmhassDeferrableLoadSensor` exists but needs enhancement
- `const.py`: Has `CONF_MAX_DEFERRABLE_LOADS`, `CONF_CHARGING_POWER`, etc.

### Key Files to Modify

1. `trip_manager.py`: Add SOC-based window calculation and milestone algorithm
2. `emhass_adapter.py`: Enhance index stability and recalculation triggers
3. `sensor.py`: Add p_deferrable display to trip cards
4. `presence_monitor.py` or new file: SOC change listener
5. `docs/borrador/cargasAplazables.yaml`: Automation template reference

---

## Open Questions

1. **Velocidad de carga real**: El ejemplo usa 10% SOC/hora - debe verificarse con la configuracion real del usuario (charging_power_kw / battery_capacity_kwh)

2. **Buffer standard**: El ejemplo usa 10% buffer sobre energia del viaje - debe convertirse en configuracion (safety_margin_percent ya existe en const.py)

3. **Max deficit propagation**: Hay limite en cascade de deficits? Si hay 10 viajes consecutivos con deficit, se propaga indefinidamente?

4. **Presencia durante carga**: El calculo de ventana asume que el coche esta en casa. Si el usuario sale y regresa durante la ventana, como se maneja?
