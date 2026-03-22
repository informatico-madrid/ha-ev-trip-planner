# Data Model: Panel de Control de Vehículo con CRUD de Viajes

## Entities

### Vehicle (ConfigEntry)

El vehículo representa un coche eléctrico configurado en la integración.

| Field | Type | Description | Source |
|-------|------|-------------|--------|
| entry_id | str | Unique HA config entry ID | HA Config Entry |
| vehicle_name | str | Nombre personalizado del vehículo | User input in config flow |
| vehicle_id | str | Slug derivado del nombre (chispitas → chispitas) | Derived from vehicle_name |
| battery_capacity_kwh | float | Capacidad de batería en kWh | User input |
| charging_power_kw | float | Potencia de carga en kW | User input |
| kwh_per_km | float | Consumo por km | User input |
| safety_margin_percent | int | Margen de seguridad % | User input |
| planning_horizon_days | int | Horizonte de planificación | User input/EMHASS |
| max_deferrable_loads | int | Cargas diferibles máx | User input/EMHASS |
| charging_sensor | str | Entity ID del sensor de carga | Binary sensor |
| home_sensor | str | Entity ID del sensor de presencia | Binary sensor (optional) |
| plugged_sensor | str | Entity ID del sensor de enchufe | Binary sensor (optional) |
| notification_service | str | Servicio de notificaciones | User input (optional) |
| notification_devices | list | Dispositivos de notificación | User input (optional) |

### Sensor Entities

Sensores creados para cada vehículo:

| Entity ID Pattern | Type | Description |
|-----------------|------|-------------|
| sensor.ev_trip_planner_{vehicle_id}_trips_list | sensor | Lista combinada de viajes |
| sensor.ev_trip_planner_{vehicle_id}_recurring_trips_count | sensor | Cantidad de viajes recurrentes |
| sensor.ev_trip_planner_{vehicle_id}_punctual_trips_count | sensor | Cantidad de viajes puntuales |
| sensor.ev_trip_planner_{vehicle_id}_kwh_today | sensor | kWh necesarios hoy |
| sensor.ev_trip_planner_{vehicle_id}_hours_today | sensor | Horas de carga hoy |
| sensor.ev_trip_planner_{vehicle_id}_next_trip | sensor | Próximo viaje |
| sensor.ev_trip_planner_{vehicle_id}_next_deadline | sensor | Fecha límite próximo viaje |
| sensor.trip_{trip_id} | sensor | Sensor individual de viaje |

### Trip (Viaje)

Viaje programado, ya sea recurrente o puntual.

| Field | Type | Description | Validations |
|-------|------|-------------|-------------|
| id | str | ID único del viaje | Auto-generated |
| tipo | str | "recurrente" o "puntual" | Required |
| dia_semana | str | Día de la semana (lunes-domingo) | Required if tipo=recurrente |
| hora | str | Hora del viaje (HH:MM) | Required if tipo=recurrente |
| datetime | str | Fecha y hora exacta | Required if tipo=puntual |
| km | float | Distancia en kilómetros | Required, > 0 |
| kwh | float | Energía estimada en kWh | Required, > 0 |
| descripcion | str | Descripción/destino | Optional |
| activo | bool | Si el viaje está activo | Default true |
| estado | str | Estado del viaje (pendiente/completado/cancelado) | Only for punctual |

### Panel Configuration

Configuración pasada al panel nativo.

| Field | Type | Description |
|-------|------|-------------|
| vehicle_id | str | ID del vehículo (slug) |
| vehicle_name | str | Nombre para mostrar |
| sidebar_title | str | Título en el sidebar |
| sidebar_icon | str | Icono MDI |

## Relationships

```
ConfigEntry (Vehicle)
    │
    ├──► Sensors (many)
    │       └── device_info → Device
    │
    ├──► Trips (many)
    │       └── TripSensor (via via_device)
    │
    └──► Panel
            └── Frontend URL: /ev-trip-planner-{vehicle_id}
```

## State Transitions

### Trip States (for punctual trips)

```
pendiente → completado  (user action: complete_punctual)
pendiente → cancelado  (user action: cancel_punctual)
completado → pendiente (no transition - create new)
cancelado → pendiente  (no transition - create new)
```

### Recurring Trip States

```
activo → pausado  (user action: pause_recurring)
pausado → activo (user action: resume_recurring)
```

## API Contracts

### Services Available

Los servicios CRUD están registrados en el dominio `ev_trip_planner`:

| Service | Parameters | Description |
|---------|------------|-------------|
| trip_create | vehicle_id, type, dia_semana?, hora?, datetime?, km, kwh, descripcion | Crear viaje |
| trip_update | vehicle_id, trip_id, updates | Actualizar viaje |
| delete_trip | vehicle_id, trip_id | Eliminar viaje |
| pause_recurring_trip | vehicle_id, trip_id | Pausar viaje recurrente |
| resume_recurring_trip | vehicle_id, trip_id | Reanudar viaje recurrente |
| complete_punctual_trip | vehicle_id, trip_id | Completar viaje puntual |
| cancel_punctual_trip | vehicle_id, trip_id | Cancelar viaje puntual |
| trip_list | vehicle_id | Listar todos los viajes |
