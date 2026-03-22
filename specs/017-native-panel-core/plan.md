# Implementation Plan: Panel de Control Nativo Integrado en Home Assistant Core

**Branch**: `017-native-panel-core` | **Date**: 2026-03-21 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/017-native-panel-core/spec.md`

## Summary

Reemplazar la dependencia de Lovelace UI por `panel_custom` del core de Home Assistant para crear paneles de control nativos que aparecen en el sidebar.

**IMPORTANTE**: El YAML de Lovelace (`ev-trip-planner-simple.yaml`, `ev-trip-planner-full.yaml`) **NO se puede reutilizar directamente** para `panel_custom`. Se requiere un **nuevo componente web JavaScript** que renderice el mismo contenido.

El panel personalizado:
1. Se registra mediante `panel_custom.async_register_panel`
2. Usa un componente web JavaScript que se comunica con la API REST de HA
3. Muestra el **MISMO contenido** que los dashboards YAML existentes (estado del vehículo, viajes, CRUD, etc.)
4. Se elimina automáticamente cuando se elimina el vehículo

## Technical Context

**Language/Version**: Python 3.11+ (HA custom component) + JavaScript/TypeScript (web component)  
**Primary Dependencies**: homeassistant.core, panel_custom, frontend, hass.http.register_static_path  
**Storage**: N/A (usa la API REST de HA existente)  
**Testing**: pytest (con MagicMock para hass)  
**Target Platform**: Home Assistant (todas las instalaciones: Core, Container, Supervised, OS)  
**Project Type**: Home Assistant Custom Component Integration  
**Performance Goals**: Panel visible en <5 segundos tras config flow  
**Constraints**: Debe funcionar sin Lovelace UI, sin intervención manual  

## Constitution Check

- ✅ **Code Style**: Se usará line length 88, type hints, Google docstrings, async/await
- ✅ **Testing**: >80% coverage requerido con pytest
- ✅ **Documentation**: Conventional Commits para todos los cambios

## Available Tools for Verification

| Tool | Type | Status | Purpose |
|------|------|--------|---------|
| homeassistant-config | skill | installed | HA YAML/config validation |
| homeassistant-ops | skill | installed | HA API verification |
| homeassistant-skill | skill | installed | HA device control |
| homeassistant-best-practices | skill | installed | HA automation best practices |
| homeassistant-dashboard-designer | skill | installed | Dashboard design patterns |
| python-testing-patterns | skill | installed | pytest patterns |
| e2e-testing-patterns | skill | installed | Playwright E2E testing |

## Project Structure

### Documentation (this feature)

```
specs/017-native-panel-core/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output
└── tasks.md            # Phase 2 output
```

### Source Code (repository root)

```
custom_components/ev_trip_planner/
├── __init__.py
├── config_flow.py
├── dashboard.py         # MODIFICAR: Añadir registro de panel_custom
├── panel.py            # NUEVO: Lógica de registro de paneles
├── frontend/
│   ├── __init__.py
│   ├── panel.js       # NUEVO: Componente web del panel
│   └── panel.css      # NUEVO: Estilos del panel
├── services.yaml
└── ...
```

## Deployment Methods

### Método 1: panel_custom.async_register_panel (PRIMARIO)

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

### Método 2: frontend.async_register_built_in_panel (ALTERNATIVO)

```python
from homeassistant.components import frontend

frontend.async_register_built_in_panel(
    hass,
    component_name="custom",
    sidebar_title=vehicle_name,
    sidebar_icon="mdi:car-electric",
    frontend_url_path=f"ev-trip-planner-{vehicle_id}",
    config={"_panel_custom": {"name": "ev-trip-planner-panel"}},
)
```

### Método 3: Serving del componente web

```python
# Registrar la ruta estática para el componente web
hass.http.register_static_path(
    "/local/ev_trip_planner/panel.js",
    path_to_panel_js_file,
    cache_headers=True
)
```

### Cascada de métodos

1. Intentar `panel_custom.async_register_panel` (primario)
2. Si falla, intentar `frontend.async_register_built_in_panel` (alternativo)
3. Si ambos fallan, fallback a archivo YAML con notificación al usuario

## State Verification Plan

### ⚠️ IMPORTANT: Only 3 Verification Types (CLOSED set)

| Verification Type | When to Use | Example Command |
|------------------|-------------|----------------|
| `[VERIFY:TEST]` | Unit/integration tests | `pytest tests/ -v --cov` |
| `[VERIFY:API]` | REST API verification | `curl http://HA/api/states` + skill |
| `[VERIFY:BROWSER]` | Playwright UI automation | `npx playwright test` |

### Existence Check

- [ ] Verificar que el componente `panel_custom` está cargado en Home Assistant
- [ ] Verificar que las entidades del vehículo existen: `sensor.{vehicle_id}_*`
- [ ] Verificar que el panel está registrado: buscar en `hass.data[DATA_PANELS]`
- [ ] Verificar que el archivo JS del panel existe en `/local/`

### Effect Check

- [ ] El panel aparece en el sidebar de HA después de configurar un vehículo
- [ ] El panel carga y muestra datos correctamente
- [ ] No hay errores en los logs de HA relacionados con el panel
- [ ] Los servicios de EV Trip Planner están disponibles

## Research Notes

### Métodos encontrados en código fuente de HA

1. **panel_custom.async_register_panel** - API pública recomendada
2. **frontend.async_register_built_in_panel** - API de bajo nivel
3. **frontend.async_remove_panel** - Para eliminar paneles
4. **hass.http.register_static_path** - Para servir archivos JS/CSS

### Componentes web de referencia

- dynalite/panel.py - Ejemplo de panel personalizado
- insteon/api/__init__.py - Ejemplo de register_static_path

## Complexity Tracking

No hay violaciones de la constitución que requieran justificación. El proyecto usa la estructura existente de custom_components.

## Next Steps

1. Fase 0: Generar research.md con detalles de implementación
2. Fase 1: Generar data-model.md, quickstart.md
3. Fase 2: Generar tasks.md con tareas de implementación
