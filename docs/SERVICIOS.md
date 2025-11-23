# Servicios de EV Trip Planner (HA)

Esta guía muestra ejemplos reales para llamar a los servicios del dominio `ev_trip_planner` desde Home Assistant.

Requisitos previos:
- Instalar la integración (custom component) y reiniciar Home Assistant.
- Usar un `vehicle_id` estable (minúsculas, sin espacios), por ejemplo: `chispitas` o `morgan`.
- Días de semana en español sin acentos: `lunes, martes, miercoles, jueves, viernes, sabado, domingo`.
- Fechas puntuales en ISO: `YYYY-MM-DDTHH:MM:SS`.

Verificar datos guardados:
- Ir a Herramientas de Desarrollo → Estados → buscar `input_text.ev_trip_planner_<vehicle_id>_trips`.
- El estado contiene un JSON con todos los viajes.

---

## Añadir viaje recurrente
Servicio: `ev_trip_planner.add_recurring_trip`

YAML (Herramientas de desarrollo → Servicios):
```yaml
service: ev_trip_planner.add_recurring_trip
data:
  vehicle_id: chispitas
  dia_semana: lunes
  hora: "09:00"
  km: 24
  kwh: 3.6
  descripcion: Trabajo
```

## Añadir viaje puntual
Servicio: `ev_trip_planner.add_punctual_trip`

```yaml
service: ev_trip_planner.add_punctual_trip
data:
  vehicle_id: chispitas
  datetime: "2025-11-19T15:00:00"
  km: 110
  kwh: 16.5
  descripcion: Viaje a Toledo
```

## Editar viaje
Servicio: `ev_trip_planner.edit_trip`

```yaml
service: ev_trip_planner.edit_trip
data:
  vehicle_id: chispitas
  trip_id: rec_lun_abc12345
  updates:
    hora: "10:00"
    km: 30
```

## Borrar viaje
Servicio: `ev_trip_planner.delete_trip`

```yaml
service: ev_trip_planner.delete_trip
data:
  vehicle_id: chispitas
  trip_id: rec_lun_abc12345
```

## Pausar/Reanudar viaje recurrente
Servicios: `ev_trip_planner.pause_recurring_trip` / `ev_trip_planner.resume_recurring_trip`

```yaml
service: ev_trip_planner.pause_recurring_trip
data:
  vehicle_id: chispitas
  trip_id: rec_lun_abc12345
```

```yaml
service: ev_trip_planner.resume_recurring_trip
data:
  vehicle_id: chispitas
  trip_id: rec_lun_abc12345
```

## Completar/Cancelar viaje puntual
Servicios: `ev_trip_planner.complete_punctual_trip` / `ev_trip_planner.cancel_punctual_trip`

```yaml
service: ev_trip_planner.complete_punctual_trip
data:
  vehicle_id: chispitas
  trip_id: pun_20251119_abc12345
```

```yaml
service: ev_trip_planner.cancel_punctual_trip
data:
  vehicle_id: chispitas
  trip_id: pun_20251119_abc12345
```

## Importar patrón semanal (migración desde sliders)
Servicio: `ev_trip_planner.import_from_weekly_pattern`

- `clear_existing: true` borra los viajes recurrentes existentes antes de importar.
- Estructura del `pattern`: claves con días y lista de viajes por día.

```yaml
service: ev_trip_planner.import_from_weekly_pattern
data:
  vehicle_id: chispitas
  clear_existing: true
  pattern:
    lunes:
      - hora: "09:00"
        km: 24
        kwh: 3.6
        descripcion: Trabajo
      - hora: "18:00"
        km: 24
        kwh: 3.6
        descripcion: Vuelta
    miercoles:
      - hora: "20:00"
        km: 10
        kwh: 1.5
        descripcion: Gimnasio
```

Si no quieres borrar los existentes:
```yaml
service: ev_trip_planner.import_from_weekly_pattern
data:
  vehicle_id: chispitas
  clear_existing: false
  pattern:
    viernes:
      - hora: "12:00"
        km: 50
        kwh: 7.5
        descripcion: Comida
```

---

## Verificación rápida (Templates)
En Herramientas de Desarrollo → Plantillas:

- Total de viajes:
```jinja2
{{ states('input_text.ev_trip_planner_chispitas_trips') | from_json | length }}
```

- Lista de IDs:
```jinja2
{% set trips = states('input_text.ev_trip_planner_chispitas_trips') | from_json %}
{{ trips | map(attribute='id') | list }}
```

- Recurrentes vs puntuales:
```jinja2
{% set trips = states('input_text.ev_trip_planner_chispitas_trips') | from_json %}
Recurrentes: {{ trips | selectattr('tipo','equalto','recurrente') | list | length }}
Puntuales: {{ trips | selectattr('tipo','equalto','puntual') | list | length }}
```

---

## Notas y resolución de problemas
- Si ves error de validación "Invalid day of week" usa: `lunes, martes, miercoles, jueves, viernes, sabado, domingo` (sin acentos).
- `datetime` debe ser ISO (`YYYY-MM-DDTHH:MM:SS`), por ejemplo `2025-11-19T15:00:00`.
- Los servicios crean el helper `input_text.ev_trip_planner_<vehicle_id>_trips` automáticamente si no existe.
- El contenido se guarda como JSON, visible y editable desde el propio helper si lo necesitas.
- Para dos vehículos usa distintos `vehicle_id` (ej. `chispitas` y `morgan`).
