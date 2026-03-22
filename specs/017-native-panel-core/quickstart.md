# Quickstart: Panel de Control Nativo Integrado

## Prerequisites

- Home Assistant Container/Core/Supervised/OS
- EV Trip Planner instalado
- Acceso al directorio de configuración de HA

## Installation Steps

### 1. Verificar que el componente está actualizado

Tras la implementación, el panel se creará automáticamente al configurar un vehículo.

### 2. Configurar un vehículo

1. Ve a **Settings** > **Devices & Services**
2. Añade **EV Trip Planner**
3. Completa el config flow con los datos del vehículo
4. **Resultado esperado**: Aparece un nuevo panel en el sidebar

### 3. Verificar el panel

1. Busca el panel en el sidebar de Home Assistant
2. Haz clic en el panel - debe mostrar información del vehículo
3. Verifica que puedes ver: SOC, autonomía, estado de carga

## Troubleshooting

### El panel no aparece

1. Verifica los logs: `grep -i panel /config/homeassistant.log`
2. Verifica que el componente `panel_custom` está cargado:
   ```bash
   curl -s http://localhost:8123/api/states | jq '.[] | select(.entity_id == "sensor.ev_trip_planner_version")'
   ```

### Error al registrar el panel

1. Verifica que el archivo JS existe en `/config/www/ev_trip_planner/`
2. Verifica los permisos del archivo

### Múltiples vehículos

Cada vehículo tendrá su propio panel en el sidebar:
- "EV Tesla Model 3"
- "EV Nissan Leaf"

## API Reference

### Registro de panel

```python
from homeassistant.components.panel_custom import async_register_panel

await async_register_panel(
    hass,
    frontend_url_path=f"ev-trip-planner-{vehicle_id}",
    webcomponent_name="ev-trip-planner-panel",
    sidebar_title=vehicle_name,
    sidebar_icon="mdi:car-electric",
    module_url="/local/ev_trip_planner/panel.js",
    config={"vehicle_id": vehicle_id},
)
```

### Eliminación de panel

```python
from homeassistant.components import frontend

frontend.async_remove_panel(hass, f"ev-trip-planner-{vehicle_id}")
```

## Verification Commands

```bash
# Ver estados de sensores del vehículo
curl -s http://localhost:8123/api/states | jq '.[] | select(.entity_id | startswith("sensor.{vehicle_id}"))'

# Ver paneles registrados
curl -s http://localhost:8123/api/panels

# Ver servicios disponibles
curl -s http://localhost:8123/api/services | jq '.ev_trip_planner'
```
