# Quickstart: Panel de Control de Vehículo con CRUD de Viajes

## Prerequisites

- Home Assistant Container instalado y funcionando
- EV Trip Planner ya configurado con al menos un vehículo
- Acceso a la línea de comandos del contenedor HA

## Verification Commands

### 1. Verificar que el componente está cargado

```bash
# Acceder al contenedor HA y verificar componentes
curl -H "Authorization: Bearer $HA_TOKEN" http://HA/api/components
```

Debería incluir `ev_trip_planner` en la respuesta.

### 2. Verificar que las entidades existen

```bash
# Listar estados de sensores EV Trip Planner
curl -H "Authorization: Bearer $HA_TOKEN" http://HA/api/states | grep "sensor.ev_trip_planner"
```

### 3. Verificar el panel (error vehicle_id corregido)

Abrir en navegador: `http://HA/ev-trip-planner-{vehicle_id}`

Debería mostrar el panel SIN el error "Cannot render - no vehicle_id".

### 4. Verificar dispositivo con nombre correcto

En HA: Settings → Devices → Buscar "EV Trip Planner"

Debería aparecer con nombre "EV Trip Planner {nombre_del_vehiculo}" (no el ID largo).

### 5. Verificar selector de assist_satellite

1. Ir a Settings → Integrations → EV Trip Planner
2. Añadir nueva integración
3. En paso de notificaciones, debería aparecer `assist_satellite.*`

### 6. Verificar eliminación automática de panel

1. Eliminar integración del vehículo
2. Verificar que el panel ya no aparece en el sidebar
3. Verificar que la URL del panel devuelve error 404

### 7. Verificar panel con viajes

En el panel:
- Debería mostrar los viajes programados en formato legible
- Si no hay viajes: mensaje "No hay viajes programados"
- Si hay viajes: lista con propiedades (día, hora, km, kWh, descripción)

### 8. Verificar CRUD de viajes

En el panel:
- Click en "Agregar Viaje" → Formulario de creación
- Click en editar en un viaje → Formulario de edición
- Click en eliminar → Confirmación y eliminación
- Click en pausar/reanudar → Cambio de estado

## Testing con Playwright (VERIFICACIÓN MANUAL DEL AGENTE)

```bash
# Navegar al panel
navigate to http://HA/ev-trip-planner-chispitas

# Verificar que no hay error
snapshot (verificar que no contiene "Cannot render")

# Verificar que aparecen viajes
wait for text "Viajes" or "No hay viajes"

# Verificar botones CRUD
verify button "Agregar Viaje" exists
```

## Troubleshooting

### Error "Cannot render - no vehicle_id"

1. Verificar que el panel está registrado: `curl .../api/frontend/routing`
2. Ver logs de HA: `docker logs homeassistant | grep panel`
3. Verificar que vehicle_id está en la URL correctamente

### Dispositivo con nombre incorrecto

1. Verificar que vehicle_name está en entry.data
2. Verificar que device_info usa el nombre correcto

### assist_satellite no aparece

1. Verificar que el dominio está registrado: `curl .../api/services | grep assist_satellite`
2. Verificar que la entidad existe: `curl .../api/states | grep assist_satellite`
