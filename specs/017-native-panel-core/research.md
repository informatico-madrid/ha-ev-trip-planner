# Research: Panel de Control Nativo Integrado en HA Core

## PREGUNTA: ¿Se puede reutilizar el YAML de Lovelace?

**RESPUESTA: NO**

El YAML de Lovelace (`ev-trip-planner-simple.yaml`, `ev-trip-planner-full.yaml`) **NO se puede usar directamente** con `panel_custom`. El componente `panel_custom` requiere:
- Un **componente web JavaScript** (no YAML)
- Que se comunique con la API REST/WebSocket de HA
- Que renderice HTML/CSS en el navegador

## Contenido del Panel (del dashboard YAML existente)

El nuevo componente web JavaScript debe mostrar el **MISMO contenido** que los dashboards YAML actuales:

1. **Vista de Estado** (views[0]):
   - Estado de vehículos (SOC, autonomía)
   - Lista de viajes recurrentes
   - Lista de viajes puntuales
   - Cargas diferibles EMHASS
   - Estado de presencia

2. **Vista de Gestión de Viajes** (views[1]):
   - Botones para crear viajes recurrentes/puntuales
   - Botones de acciones rápidas (pausar, reanudar, eliminar, completar, cancelar)
   - Información de servicios disponibles

## Decision: Usar panel_custom.async_register_panel

**Rationale**: 
- Es la API pública recomendada por HA para crear paneles personalizados
- Funciona en todas las instalaciones de HA (Core, Container, Supervised, OS)
- No requiere Lovelace UI
- Se integra en el sidebar automáticamente
- Permite eliminar paneles con `frontend.async_remove_panel`

**Alternatives considered**:
1. Lovelace Dashboard - Descartado: requiere Lovelace UI, no funciona en Container sin storage
2. panel_custom YAML config - Descartado: requiere intervención manual
3. Frontend API de bajo nivel - Alternativo, pero panel_custom es más alto nivel

## Deployment Methods

### Método Primario: panel_custom.async_register_panel

```python
#Ubicación: homeassistant/components/panel_custom/__init__.py
from homeassistant.components.panel_custom import async_register_panel

await async_register_panel(
    hass,
    frontend_url_path=f"ev-trip-planner-{vehicle_id}",
    webcomponent_name="ev-trip-planner-panel",
    sidebar_title="Tesla Model 3",  # Nombre del vehículo
    sidebar_icon="mdi:car-electric",
    module_url="/local/ev_trip_planner/panel.js",
    config={"vehicle_id": vehicle_id},
    require_admin=False,
)
```

### Método de Eliminación: frontend.async_remove_panel

```python
# Ubicación: homeassistant/components/frontend/__init__.py
from homeassistant.components import frontend

frontend.async_remove_panel(hass, f"ev-trip-planner-{vehicle_id}")
```

### Método de Servir Archivos: hass.http.register_static_path

```python
# Registrar el archivo JavaScript del panel
hass.http.register_static_path(
    "/local/ev_trip_planner/panel.js",
    hass.config.path("custom_components/ev_trip_planner/frontend/panel.js"),
    cache_headers=True
)
```

## Findings from Source Code

### Archivo: panel_custom/__init__.py

- `async_register_panel()` - Registra un panel personalizado
- El panel se registra en `hass.data[DATA_PANELS]`
- Se emite evento `EVENT_PANELS_UPDATED` al registrar

### Archivo: frontend/__init__.py

- `async_register_built_in_panel()` - API de bajo nivel
- `async_remove_panel()` - Elimina un panel registrado
- `DATA_PANELS = "frontend_panels"` - Clave para acceder a paneles

### Referencias en otros componentes

- `dynalite/panel.py` - Ejemplo completo de panel personalizado
- `insteon/api/__init__.py` - Ejemplo de register_static_path

## Implementation Approach

1. **Modificar dashboard.py** para usar `async_register_panel` en lugar de Lovelace
2. **Añadir panel.py** con lógica de registro/eliminación de paneles
3. **Crear frontend/panel.js** - Componente web que se comunica con HA API
4. **Registrar archivos estáticos** en el setup del componente

## Testing Strategy

- Unit tests con MagicMock para hass
- Tests de integración simulando config flow
