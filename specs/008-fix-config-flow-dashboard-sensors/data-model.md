# Data Model: Fix Config Flow Dashboard Sensors

## Entidades del Dominio

### 1. Vehicle (ConfigEntry)

Representa un vehículo configurado en el sistema.

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| vehicle_name | string | Sí | Identificador único del vehículo |
| battery_capacity | float | Sí | Capacidad de batería en kWh |
| charging_power | float | Sí | Potencia de carga en kW |
| consumption | float | Sí | Consumo en kWh/km |
| safety_margin | int | Sí | Margen de seguridad (%) |
| planning_horizon | int | No | Días de planificación |
| max_deferrable_loads | int | No | Cargas diferibles máximas |
| charging_sensor | entity_id | Sí | Sensor de carga (binary_sensor) |
| home_sensor | entity_id | No | Sensor de presencia |
| plugged_sensor | entity_id | No | Sensor de enchufe |

**Fuente**: Home Assistant ConfigEntry (custom_components/ev_trip_planner/config_flow.py)

---

### 2. Trip (Viaje)

Representa un viaje programado (recurrente o puntual).

| Campo | Tipo | Requerido | Descripción |
|-------|------|-----------|-------------|
| id | string | Sí | Identificador único del trip |
| tipo | enum | Sí | "recurring" o "punctual" |
| dia_semana | string | Sí* | Día de la semana (lunes-domingo) |
| hora | string | Sí* | Hora en formato HH:MM |
| datetime | string | Sí* | Fecha-hora ISO 8601 |
| km | float | Sí | Distancia en km |
| kwh | float | Sí | Energía necesaria en kWh |
| descripcion | string | No | Descripción del viaje |
| activo | boolean | Sí* | Para trips recurrentes |
| estado | string | Sí* | Para trips puntuales (pendiente/completado/cancelado) |

*Campo condicional según tipo de trip.

**Fuente**: TripManager (custom_components/ev_trip_planner/trip_manager.py)

---

### 3. Trip Storage (Persistencia)

Estructura almacenada en Home Assistant storage.

```json
{
  "trips": {
    "rec_20260319_7b6591f5": {
      "id": "rec_20260319_7b6591f5",
      "tipo": "recurring",
      "dia_semana": "lunes",
      "hora": "08:00",
      "km": 25.0,
      "kwh": 3.75,
      "descripcion": "Oficina ida y vuelta",
      "activo": true
    },
    "pun_20260319_07452864": {
      "id": "pun_20260319_07452864",
      "tipo": "punctual",
      "datetime": "2026-03-19T07:45",
      "km": 50.0,
      "kwh": 7.5,
      "descripcion": "Chapineria ida y vuelta",
      "estado": "pendiente"
    }
  }
}
```

---

### 4. Sensores

Entidades de Home Assistant generadas por el componente.

| Entity ID | Tipo | Descripción |
|-----------|------|-------------|
| sensor.{vehicle_id}_trips_count | sensor | Número total de trips |
| sensor.{vehicle_id}_recurring_trips_count | sensor | Número de trips recurrentes |
| sensor.{vehicle_id}_punctual_trips_count | sensor | Número de trips puntuales |
| sensor.{vehicle_id}_kwh_needed_today | sensor | kWh necesarios para hoy |
| sensor.{vehicle_id}_hours_needed_today | sensor | Horas de carga necesarias hoy |
| sensor.{vehicle_id}_next_trip | sensor | Descripción del próximo trip |
| sensor.emhass_perfil_diferible_{vehicle_id} | sensor | Perfil de carga para EMHASS |

---

### 5. Dashboard

Vista Lovelace para mostrar estado del sistema.

| Campo | Tipo | Descripción |
|-------|------|-------------|
| title | string | Título del dashboard |
| path | string | URL path del dashboard |
| views | array | Lista de vistas |

---

## Relaciones entre Entidades

```
ConfigEntry (Vehicle)
    │
    ├──► TripManager
    │       │
    │       ├──► Trip (recurring)
    │       │
    │       └──► Trip (punctual)
    │
    ├──► TripPlannerCoordinator
    │       │
    │       └──► Sensores (lectura de trips)
    │
    └──► Dashboard (importado automáticamente)
```

---

## Reglas de Validación

1. **Vehicle**:
   - `battery_capacity`: > 0 y <= 500 kWh
   - `charging_power`: > 0 y <= 350 kW
   - `consumption`: > 0 y <= 1.0 kWh/km
   - `safety_margin`: 0-100%
   - `charging_sensor`: Required, debe existir en HA

2. **Trip**:
   - `km`: >= 0
   - `kwh`: >= 0
   - Para recurrente: `dia_semana` debe ser válido, `hora` formato HH:MM
   - Para puntual: `datetime` formato ISO 8601

---

## Estado de Transiciones

### Trip Recurrente
```
activo=True <-> activo=False (pausado)
```

### Trip Puntual
```
pendiente -> completado
pendiente -> cancelado
```

---

## Notas de Implementación

- Los trips se almacenan en `hass.data[namespace]["trips"]` durante runtime
- Para persistencia entre reinicios, usar `hass.storage` en lugar de `hass.data`
- Los sensores deben leer del coordinator.data, no directamente del trip_manager
- El dashboard se importa tras completar config_flow en `_async_create_entry()`
