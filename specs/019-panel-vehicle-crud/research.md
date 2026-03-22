# Research: Panel de Control de Vehículo con CRUD de Viajes

## Investigación Realizada

### 1. Error "Cannot render - no vehicle_id" en panel.js

**Ubicación**: `custom_components/ev_trip_planner/frontend/panel.js`

**Análisis del código existente**:

```javascript
// Línea 38-52: Intento de obtener vehicle_id en connectedCallback
const match = path.match(/\/ev-trip-planner-(.+)/);
if (match && match[1]) {
  this._vehicleId = match[1];
}

// Línea 70-116: hass setter
set hass(hass) {
  // Intenta obtener vehicle_id de la URL aquí también
  // Intenta de múltiples formas: split, regex, hash
}

// Línea 128-160: setConfig
setConfig(config) {
  if (config && config.vehicle_id) {
    this._vehicleId = config.vehicle_id;
  }
}
```

**Problema identificado**: El panel intenta obtener vehicle_id de varias fuentes pero hay un timing issue. El config puede llegar después del primer intento de render.

**Solución propuesta**: Modificar el flujo para:
1. Intentar obtener vehicle_id de la URL lo antes posible (ya hace esto)
2. En el método `_render()`, hacer un último intento de obtener vehicle_id de la URL ANTES de verificar si _vehicleId está definido
3. Si aún no hay vehicle_id, mostrar un error claro con la URL actual para debugging

### 2. Nombre de dispositivo incorrecto

**Ubicación**: `custom_components/ev_trip_planner/sensor.py`, método `device_info`

**Código actual**:
```python
@property
def device_info(self) -> Dict[str, Any]:
    return {
        "identifiers": {(DOMAIN, self.trip_manager.vehicle_id)},
        "name": f"EV Trip Planner {self.trip_manager.vehicle_id}",
        ...
    }
```

**Problema**: Usa `self.trip_manager.vehicle_id` que es el slug interno, no el nombre proporcionado por el usuario.

**Solución**: 
- El vehicle_name está disponible en `entry.data.get("vehicle_name")`
- Necesitamos pasar esta información al sensor o al TripManager
- Modificar device_info para usar el nombre personalizado

### 3. assist_satellite no aparece en selector

**Ubicación**: `custom_components/ev_trip_planner/config_flow.py`

**Código actual**:
```python
STEP_NOTIFICATIONS_SCHEMA = vol.Schema({
    vol.Optional(CONF_NOTIFICATION_SERVICE): selector.EntitySelector(
        selector.EntitySelectorConfig(domain="notify", ...)
    ),
})
```

**Hallazgo**: El usuario tiene un dispositivo `assist_satellite.home_assistant_voice_09e3f5_satelite_assist`

**Problema**: EntitySelector solo busca en domain="notify", pero los dispositivos assist_satellite usan el dominio "assist_satellite".

**Solución**: Modificar EntitySelector para incluir múltiples dominios:
```python
selector.EntitySelectorConfig(
    domain=["notify", "assist_satellite"],
    ...
)
```

### 4. Eliminación automática del panel

**Ubicación**: `custom_components/ev_trip_planner/__init__.py`, función `async_unload_entry`

**Código actual**:
```python
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    vehicle_id = entry.data.get("vehicle_id", "")
    ...
    if vehicle_id:
        try:
            await async_unregister_panel(hass, vehicle_id)
        except Exception as ex:
            _LOGGER.warning(...)
```

**Problema potencial**: El vehicle_id puede no estar en entry.data correctamente (veo que usa entry.data.get("vehicle_id", "") pero en la creación usa vehicle_name).

**Solución**: Verificar que se usa el vehicle_id correcto para eliminar el panel.

### 5. Panel con viajes y CRUD

**Estado actual**: El panel solo muestra sensores básicos.

**Servicios disponibles** (ya existen en __init__.py):
- `trip_create` - Crear viaje
- `trip_update` - Actualizar viaje  
- `delete_trip` - Eliminar viaje
- `pause_recurring_trip` / `resume_recurring_trip` - Pausar/Reanudar
- `complete_punctual_trip` / `cancel_punctual_trip` - Completar/Cancelar

**Solución**: Expandir panel.js para:
1. Obtener lista de viajes via API de HA o servicios
2. Mostrar viajes en formato legible
3. Crear formulario para agregar viajes
4. Crear botones de editar/eliminar para cada viaje

## Deployment Methods

| Feature | Method | Preference |
|---------|--------|------------|
| Error vehicle_id | Modificar panel.js flujo de inicialización | Primary |
| Nombre dispositivo | Modificar sensor.py device_info | Primary |
| assist_satellite | Modificar config_flow.py EntitySelector | Primary |
| Eliminación panel | Verificar async_unload_entry | Primary |
| Panel viajes+CRUD | Expandir panel.js | Primary |

## Alternativas Consideradas

1. **Para error vehicle_id**: 
   - Usar WebComponent lifecycle más cuidadosamente ✓ (elegido)
   - Pass vehicle_id via panel config (ya se hace)

2. **Para nombre dispositivo**:
   - Crear dispositivo manualmente via device_registry (más complejo)
   - Modificar device_info en sensores (más simple) ✓ (elegido)

3. **Para assist_satellite**:
   - Agregar múltiples dominios a EntitySelector ✓ (elegido)
   - Crear selector personalizado (más complejo)

4. **Para panel CRUD**:
   - Usar WebSockets para datos en tiempo real
   - Consultar servicios de HA directamente ✓ (elegido)
